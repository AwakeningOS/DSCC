"""T001: Loopback-only authenticated local IPC server and client.

Cross-platform (Linux/macOS/Windows) using Python's standard library only:
- Refuses any bind address other than 127.0.0.1 (no public interface exposure).
- Rejects any request carrying browser Origin or Sec-Fetch-* headers (CSRF defense).
- Enforces strict Host header matching 127.0.0.1:<port> or localhost:<port> (DNS rebinding defense).
- Requires a valid scoped Bearer token on every request and enforces bounded payload sizes.
"""
from __future__ import annotations

import http.client
import json
import os
import threading
import urllib.parse
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from .canonical import MAX_BUNDLE_BYTES, parse_json
from .identity import write_private_exclusive
from .service import AuthenticationError, AuthorizationError, LocalService
from .store import Node, utc_now

MAX_IPC_BODY_BYTES = MAX_BUNDLE_BYTES + 65_536


class IPCError(RuntimeError):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status


class LocalIPCServer:
    """Authenticated HTTP/JSON-RPC local IPC bound strictly to 127.0.0.1."""

    def __init__(self, node: Node, *, host: str = "127.0.0.1", port: int = 0):
        if host != "127.0.0.1":
            raise ValueError("DSCC local IPC must bind strictly to 127.0.0.1; public interfaces are forbidden")
        if type(port) is not int or not 0 <= port <= 65535:
            raise ValueError("invalid local IPC port")
        self.node = node
        self.host = host
        self._thread: threading.Thread | None = None
        self._info_path = node.home / "service.json"
        self.service = LocalService(node, shutdown_callback=self.request_shutdown)
        self._httpd = self._build_httpd(host, port)
        self.port = int(self._httpd.server_address[1])
        self.url = f"http://127.0.0.1:{self.port}"
        self._allowed_hosts = {f"127.0.0.1:{self.port}", f"localhost:{self.port}"}

    def _build_httpd(self, host: str, port: int) -> ThreadingHTTPServer:
        parent = self

        class Handler(BaseHTTPRequestHandler):
            protocol_version = "HTTP/1.1"

            def log_message(self, format: str, *args: Any) -> None:
                # Never dump tokens, headers or research payloads to stdout/stderr.
                return

            def _send_json(self, status: int, payload: dict[str, Any]) -> None:
                body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Connection", "close")
                self.end_headers()
                self.wfile.write(body)

            def _validate_local_origin_and_host(self) -> bool:
                # Reject browser-originated requests unconditionally.
                if "Origin" in self.headers:
                    self._send_json(403, {"error": "Origin header is forbidden on local IPC"})
                    return False
                if any(k.lower().startswith("sec-fetch-") for k in self.headers.keys()):
                    self._send_json(403, {"error": "Browser fetch headers are forbidden on local IPC"})
                    return False
                host_header = (self.headers.get("Host") or "").strip().lower()
                if host_header not in parent._allowed_hosts:
                    self._send_json(403, {"error": "Invalid Host header"})
                    return False
                return True

            def _extract_token(self) -> str | None:
                auth = self.headers.get("Authorization")
                if not auth or not auth.startswith("Bearer "):
                    return None
                return auth[len("Bearer "):].strip()

            def do_GET(self) -> None:
                self._send_json(405, {"error": "Method not allowed; use authenticated POST /rpc"})

            def do_OPTIONS(self) -> None:
                self._send_json(403, {"error": "CORS preflight is not supported on local IPC"})

            def do_POST(self) -> None:
                if not self._validate_local_origin_and_host():
                    return
                if self.path != "/rpc":
                    self._send_json(404, {"error": "Unknown endpoint"})
                    return
                ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
                if ctype != "application/json":
                    self._send_json(415, {"error": "Content-Type must be application/json"})
                    return
                token = self._extract_token()
                if not token:
                    self._send_json(401, {"error": "Missing bearer token"})
                    return
                cl_raw = self.headers.get("Content-Length")
                if cl_raw is None:
                    self._send_json(411, {"error": "Content-Length is required"})
                    return
                try:
                    length = int(cl_raw)
                except ValueError:
                    self._send_json(400, {"error": "Invalid Content-Length"})
                    return
                if length < 0 or length > MAX_IPC_BODY_BYTES:
                    self._send_json(413, {"error": "Request payload exceeds IPC limit"})
                    return
                raw = self.rfile.read(length)
                if len(raw) != length:
                    self._send_json(400, {"error": "Truncated request body"})
                    return
                try:
                    req = parse_json(raw, max_bytes=MAX_IPC_BODY_BYTES)
                except ValueError as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                if (not isinstance(req, dict) or not set(req) <= {"action", "params"}
                        or not isinstance(req.get("action"), str)):
                    self._send_json(400, {"error": "RPC payload must contain 'action' and optional 'params'"})
                    return
                try:
                    result = parent.service.execute(token, req["action"], req.get("params"))
                except AuthenticationError as exc:
                    self._send_json(401, {"error": str(exc)})
                    return
                except AuthorizationError as exc:
                    self._send_json(403, {"error": str(exc)})
                    return
                except KeyError as exc:
                    self._send_json(404, {"error": str(exc).strip("'")})
                    return
                except (ValueError, TypeError) as exc:
                    self._send_json(400, {"error": str(exc)})
                    return
                except Exception:
                    self._send_json(500, {"error": "Internal service error"})
                    return
                self._send_json(200, {"ok": True, "result": result})

        class Server(ThreadingHTTPServer):
            daemon_threads = True
            allow_reuse_address = True

        return Server((host, port), Handler)

    def _write_runtime_info(self) -> None:
        info = {
            "schema": "dscc.service.runtime/0.1",
            "url": self.url,
            "pid": os.getpid(),
            "public_key": self.node.public_key,
            "started_at": utc_now(),
        }
        tmp = self.node.home / f".service.{uuid.uuid4().hex}.tmp"
        try:
            write_private_exclusive(tmp, json.dumps(info, indent=2).encode("utf-8"))
            os.replace(tmp, self._info_path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def _remove_runtime_info(self) -> None:
        try:
            if self._info_path.exists():
                self._info_path.unlink()
        except OSError:
            pass

    def start_background(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._write_runtime_info()
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            kwargs={"poll_interval": 0.05},
            daemon=True,
            name="dscc-local-ipc",
        )
        self._thread.start()

    def serve_forever(self) -> None:
        self._write_runtime_info()
        try:
            self._httpd.serve_forever(poll_interval=0.2)
        finally:
            self._remove_runtime_info()
            self._httpd.server_close()

    def request_shutdown(self) -> None:
        threading.Thread(target=self.stop, daemon=True).start()

    def stop(self) -> None:
        try:
            self._httpd.shutdown()
        finally:
            self._remove_runtime_info()
            self._httpd.server_close()
            if self._thread is not None and threading.current_thread() is not self._thread:
                self._thread.join(timeout=5)


class LocalServiceClient:
    """Authenticated local IPC client. Never reads signing.key or catalog.sqlite3."""

    def __init__(self, url: str, token: str, *, timeout: float = 15.0):
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
            raise ValueError("DSCC local IPC client accepts only http://127.0.0.1:<port> or http://localhost:<port>")
        if not isinstance(token, str) or not token:
            raise ValueError("bearer token is required")
        self.url = url.rstrip("/")
        self._host = parsed.hostname
        self._port = int(parsed.port)
        self._token = token
        self._timeout = timeout

    def call(self, action: str, params: dict[str, Any] | None = None) -> Any:
        payload = json.dumps({"action": action, "params": params or {}}, ensure_ascii=False).encode("utf-8")
        conn = http.client.HTTPConnection(self._host, self._port, timeout=self._timeout)
        try:
            conn.request(
                "POST",
                "/rpc",
                body=payload,
                headers={
                    "Host": f"{self._host}:{self._port}",
                    "Content-Type": "application/json",
                    "Content-Length": str(len(payload)),
                    "Authorization": f"Bearer {self._token}",
                },
            )
            resp = conn.getresponse()
            raw = resp.read(MAX_IPC_BODY_BYTES + 1)
        finally:
            conn.close()
        if len(raw) > MAX_IPC_BODY_BYTES:
            raise IPCError(502, "IPC response exceeds size bound")
        data = parse_json(raw, max_bytes=MAX_IPC_BODY_BYTES)
        if resp.status == 200 and isinstance(data, dict) and data.get("ok") is True:
            return data["result"]
        msg = data.get("error", f"HTTP {resp.status}") if isinstance(data, dict) else f"HTTP {resp.status}"
        if resp.status == 401:
            raise AuthenticationError(msg)
        if resp.status == 403:
            raise AuthorizationError(msg)
        if resp.status == 404:
            raise KeyError(msg)
        if resp.status == 400:
            raise ValueError(msg)
        raise IPCError(resp.status, msg)

    # Convenience methods matching MCPServer backend usage (model-safe subset + owner helpers).
    def status(self) -> dict[str, Any]:
        return self.call("node_status")

    def search(self, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        return self.call("search_assets", {"query": query, "limit": limit})["assets"]

    def fetch(self, cid: str) -> dict[str, Any]:
        return self.call("fetch_artifact", {"cid": cid})

    def record_manifest(self, kind: str, title: str, data: dict[str, Any], *,
                        summary: str = "", parents: list[str] | None = None,
                        license: str = "NOASSERTION") -> dict[str, Any]:
        return self.call("record_artifact", {
            "kind": kind, "title": title, "data": data,
            "summary": summary, "parents": parents or [], "license": license,
        })

    def verify_artifact(self, cid: str) -> dict[str, Any]:
        return self.call("verify_artifact", {"cid": cid})

    def inspect_tools(self) -> dict[str, Any]:
        return self.call("inspect_tools")

    def submit_job(self, input_cid: str, tool: str = "dscc.integer_stats.v1") -> dict[str, Any]:
        return self.call("submit_job", {"input_cid": input_cid, "tool": tool})

    def job_status(self, job_id: str) -> dict[str, Any]:
        return self.call("job_status", {"job_id": job_id})

    def resource_page(self, cursor: str | None = None) -> dict[str, Any]:
        return self.call("resource_page", {"cursor": cursor} if cursor is not None else {})

    def record_open_model(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
        return self.call("record_open_model", {"payload": payload, "license": license})

    def inspect_open_model(self, cid: str, *, verify_blocks: bool = False) -> dict[str, Any]:
        return self.call("inspect_open_model", {"cid": cid, "verify_blocks": verify_blocks})

    def record_compute_capability(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
        return self.call("record_compute_capability", {"payload": payload, "license": license})

    def record_training_run(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
        return self.call("record_training_run", {"payload": payload, "license": license})

    def plan_open_model_inference(self, model_cid: str, capability_cids: list[str],
                                  *, precision: str | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {"model_cid": model_cid, "capability_cids": capability_cids}
        if precision is not None:
            params["precision"] = precision
        return self.call("plan_open_model_inference", params)

    def record_research(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
        return self.call("record_research", {"payload": payload, "license": license})

    def get_research_handoff(self, state_cid: str) -> dict[str, Any]:
        return self.call("get_research_handoff", {"state_cid": state_cid})
