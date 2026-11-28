"""T001: Authenticated local application service and owner/model scope boundary.

One owner-controlled service owns node state and signing keys. Clients present
scoped bearer tokens (`owner` or `model`); model tokens are rejected at the
service layer for all approval, execution, export/import, large-block upload,
catalog rebuild and token-administration actions.

Security boundary note: this service enforces capability separation over local
IPC, not OS-level process sandboxing against a compromised same-user shell.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .canonical import MAX_BUNDLE_BYTES, parse_json
from .cooperation import episode_history, record_step
from .identity import write_private_exclusive
from .models import manifest
from .omc_service import OpenModelCommons
from .research import ResearchService
from .store import Node, utc_now
from .tools import DESCRIPTOR, TOOL_DIGEST, TOOL_ID

TOKEN_SCHEMA = "dscc.tokens.seed/0.1"
SCOPES = frozenset({"owner", "model"})

MODEL_ACTIONS = frozenset({
    "node_status",
    "search_assets",
    "fetch_artifact",
    "record_artifact",
    "verify_artifact",
    "verify_lineage",
    "inspect_tools",
    "submit_job",
    "job_status",
    "resource_page",
    "record_open_model",
    "inspect_open_model",
    "record_compute_capability",
    "record_training_run",
    "plan_open_model_inference",
    "record_research",
    "get_research_handoff",
    "catalog_search",
    "catalog_neighbors",
})

OWNER_ACTIONS = frozenset({
    "approve_job",
    "run_job",
    "cancel_job",
    "recover_job",
    "list_jobs",
    "orphaned_running_jobs",
    "export_bundle",
    "import_bundle",
    "add_block",
    "verify_block",
    "audit",
    "rebuild_catalog",
    "export_rocrate",
    "export_prov",
    "record_cooperation",
    "cooperation_history",
    "issue_token",
    "revoke_token",
    "list_tokens",
    "shutdown",
})

ALL_ACTIONS = MODEL_ACTIONS | OWNER_ACTIONS


class AuthenticationError(PermissionError):
    """Raised when a bearer token is missing, malformed, unknown or revoked."""


class AuthorizationError(PermissionError):
    """Raised when a valid token lacks the scope required for an action."""


@dataclass(frozen=True)
class Principal:
    token_id: str
    scope: str
    label: str


def _hash_secret(salt_hex: str, secret: str) -> str:
    return hashlib.sha256(bytes.fromhex(salt_hex) + secret.encode("utf-8")).hexdigest()


class TokenStore:
    """Persistent hashed bearer-token registry stored with owner-only permissions."""

    def __init__(self, home: Path):
        self.path = home / "tokens.json"
        self._lock = threading.RLock()

    def _load(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": TOKEN_SCHEMA, "tokens": {}}
        if self.path.is_symlink() or not self.path.is_file():
            raise ValueError("token store must be a regular non-symlink file")
        raw = self.path.read_bytes()
        if len(raw) > 1_048_576:
            raise ValueError("token store exceeds size limit")
        doc = parse_json(raw)
        if (not isinstance(doc, dict) or doc.get("schema") != TOKEN_SCHEMA
                or not isinstance(doc.get("tokens"), dict)):
            raise ValueError("unsupported token store schema")
        return doc

    def _save(self, doc: dict[str, Any]) -> None:
        encoded = json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True).encode("utf-8")
        tmp = self.path.parent / f".tokens.{uuid.uuid4().hex}.tmp"
        try:
            write_private_exclusive(tmp, encoded)
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                tmp.unlink()

    def issue(self, scope: str, label: str = "") -> dict[str, Any]:
        if scope not in SCOPES:
            raise ValueError("token scope must be 'owner' or 'model'")
        if not isinstance(label, str) or len(label) > 128:
            raise ValueError("invalid token label")
        token_id = secrets.token_hex(8)
        secret = secrets.token_urlsafe(32)
        salt_hex = secrets.token_hex(16)
        now = utc_now()
        with self._lock:
            doc = self._load()
            if len(doc["tokens"]) >= 256:
                raise ValueError("token registry limit reached; revoke old tokens first")
            doc["tokens"][token_id] = {
                "scope": scope,
                "label": label,
                "salt": salt_hex,
                "hash": _hash_secret(salt_hex, secret),
                "created_at": now,
                "revoked_at": None,
            }
            self._save(doc)
        return {
            "token_id": token_id,
            "scope": scope,
            "label": label,
            "created_at": now,
            "token": f"dscc_{scope}_{token_id}.{secret}",
        }

    def revoke(self, token_id: str) -> dict[str, Any]:
        if not isinstance(token_id, str) or not token_id:
            raise ValueError("invalid token_id")
        with self._lock:
            doc = self._load()
            entry = doc["tokens"].get(token_id)
            if entry is None:
                raise KeyError("token not found")
            if entry["revoked_at"] is None:
                entry["revoked_at"] = utc_now()
                self._save(doc)
            return {
                "token_id": token_id,
                "scope": entry["scope"],
                "label": entry["label"],
                "revoked_at": entry["revoked_at"],
            }

    def list_metadata(self) -> list[dict[str, Any]]:
        with self._lock:
            doc = self._load()
            return [
                {
                    "token_id": tid,
                    "scope": row["scope"],
                    "label": row["label"],
                    "created_at": row["created_at"],
                    "revoked_at": row["revoked_at"],
                    "active": row["revoked_at"] is None,
                }
                for tid, row in sorted(doc["tokens"].items())
            ]

    def verify(self, raw_token: Any) -> Principal:
        if not isinstance(raw_token, str) or "." not in raw_token or len(raw_token) > 256:
            raise AuthenticationError("invalid or missing bearer token")
        prefix, secret = raw_token.split(".", 1)
        parts = prefix.split("_")
        if len(parts) != 3 or parts[0] != "dscc" or parts[1] not in SCOPES or not parts[2]:
            raise AuthenticationError("invalid bearer token format")
        claimed_scope, token_id = parts[1], parts[2]
        with self._lock:
            doc = self._load()
            entry = doc["tokens"].get(token_id)
        if entry is None:
            # Constant-time dummy work to avoid trivial existence timing leaks.
            hmac.compare_digest(_hash_secret("00" * 16, secret), "00" * 32)
            raise AuthenticationError("unknown bearer token")
        expected_hash = entry["hash"]
        actual_hash = _hash_secret(entry["salt"], secret)
        if not hmac.compare_digest(actual_hash, expected_hash):
            raise AuthenticationError("invalid bearer token")
        if entry["revoked_at"] is not None:
            raise AuthenticationError("bearer token has been revoked")
        if entry["scope"] != claimed_scope:
            raise AuthenticationError("bearer token scope mismatch")
        return Principal(token_id=token_id, scope=entry["scope"], label=entry["label"])


class LocalService:
    """Owner-owned application service mediating all local DSCC operations."""

    def __init__(self, node: Node, *, shutdown_callback=None):
        self.node = node
        self.omc = OpenModelCommons(node)
        self.research = ResearchService(node)
        self.tokens = TokenStore(node.home)
        self._shutdown_callback = shutdown_callback
        self._startup_orphaned_jobs = [j["id"] for j in self.node.orphaned_running_jobs()]

    def issue_bootstrap_token(self, scope: str, label: str = "bootstrap") -> dict[str, Any]:
        """Direct owner-side helper (not exposed over IPC without an owner token)."""
        return self.tokens.issue(scope, label=label)

    def authenticate(self, token: str) -> Principal:
        return self.tokens.verify(token)

    def _authorize(self, token: str, action: str) -> Principal:
        principal = self.authenticate(token)
        if action not in ALL_ACTIONS:
            raise ValueError(f"unknown service action: {action}")
        if action in OWNER_ACTIONS and principal.scope != "owner":
            raise AuthorizationError(f"action '{action}' requires owner scope")
        return principal

    def _catalog(self):
        from .catalog import CatalogIndex
        return CatalogIndex(self.node)

    def execute(self, token: str, action: str, params: dict[str, Any] | None = None) -> Any:
        principal = self._authorize(token, action)
        p = {} if params is None else params
        if not isinstance(p, dict):
            raise ValueError("action parameters must be an object")

        if action == "node_status":
            orphans = [j["id"] for j in self.node.orphaned_running_jobs()]
            return {
                **self.node.status(),
                "service_boundary": "authenticated-local-service",
                "authenticated_scope": principal.scope,
                "recovery_required_jobs": orphans,
                "startup_orphaned_jobs": list(self._startup_orphaned_jobs),
            }
        if action == "search_assets":
            return {"assets": self.node.search(p.get("query", ""), p.get("limit", 20))}
        if action == "fetch_artifact":
            return self.node.fetch(p["cid"])
        if action == "record_artifact":
            doc = manifest(
                p["kind"], p["title"], p["data"],
                summary=p.get("summary", ""),
                parents=p.get("parents", []),
                license=p.get("license", "NOASSERTION"),
            )
            return {"cid": self.node.record(doc), "scope": "local_only"}
        if action == "verify_artifact":
            return self.node.verify_artifact(p["cid"])
        if action == "verify_lineage":
            return self.node.verify_lineage(p["cid"], max_records=p.get("max_records", 256))
        if action == "inspect_tools":
            return {"tools": [{**DESCRIPTOR, "digest": TOOL_DIGEST}], "owner_approval_required": True}
        if action == "submit_job":
            return self.node.submit_job(p["input_cid"], p.get("tool", TOOL_ID))
        if action == "job_status":
            return self.node.job_status(p["job_id"])
        if action == "resource_page":
            return self.node.resource_page(p.get("cursor"))
        if action == "record_open_model":
            return self.omc.record_model(p["payload"], license=p.get("license", "NOASSERTION"))
        if action == "inspect_open_model":
            return self.omc.inspect_model(p["cid"], verify_blocks=bool(p.get("verify_blocks", False)))
        if action == "record_compute_capability":
            return self.omc.record_capability(p["payload"], license=p.get("license", "NOASSERTION"))
        if action == "record_training_run":
            return self.omc.record_training_run(p["payload"], license=p.get("license", "NOASSERTION"))
        if action == "plan_open_model_inference":
            return self.omc.plan_inference(
                p["model_cid"], p["capability_cids"], precision=p.get("precision")
            )
        if action == "record_research":
            return self.research.record(p["payload"], license=p.get("license", "NOASSERTION"))
        if action == "get_research_handoff":
            return self.research.handoff(p["state_cid"])
        if action == "catalog_search":
            return self._catalog().search(
                query=p.get("query", ""),
                kind=p.get("kind"),
                project=p.get("project"),
                research_type=p.get("research_type"),
                signer=p.get("signer"),
                limit=p.get("limit", 20),
            )
        if action == "catalog_neighbors":
            return self._catalog().neighbors(p["cid"])

        # Owner-only actions below (already guarded by _authorize).
        if action == "approve_job":
            return self.node.approve_job(p["job_id"])
        if action == "run_job":
            return self.node.run_job(p["job_id"])
        if action == "cancel_job":
            return self.node.cancel_job(p["job_id"])
        if action == "recover_job":
            return self.node.recover_job(p["job_id"])
        if action == "list_jobs":
            return {"jobs": self.node.list_jobs(state=p.get("state"), limit=p.get("limit", 100))}
        if action == "orphaned_running_jobs":
            return {"jobs": self.node.orphaned_running_jobs()}
        if action == "export_bundle":
            return self.node.export_bundle(p["cid"])
        if action == "import_bundle":
            bundle = p["bundle"]
            trusted_keys = p.get("trusted_keys", [])
            if not isinstance(trusted_keys, list):
                raise ValueError("trusted_keys must be a list of public keys")
            return {"cid": self.node.import_bundle(bundle, set(trusted_keys))}
        if action == "add_block":
            return self.omc.add_block(Path(p["path"]))
        if action == "verify_block":
            return self.omc.verify_block(p["cid"])
        if action == "audit":
            return self.node.audit()
        if action == "rebuild_catalog":
            db_report = self.node.rebuild_from_objects()
            index_report = self._catalog().rebuild()
            return {"database": db_report, "search_index": index_report}
        if action == "export_rocrate":
            from .adapters.export import export_rocrate_dict
            return export_rocrate_dict(self.node, p["cid"])
        if action == "export_prov":
            from .adapters.export import export_prov_json
            return export_prov_json(self.node, p["cid"])
        if action == "record_cooperation":
            return record_step(
                self.node,
                project=p["project"],
                contributor=p["contributor"],
                step=p["step"],
            )
        if action == "cooperation_history":
            return {
                "steps": episode_history(
                    self.node, p["head_cid"], max_steps=p.get("max_steps", 64)
                )
            }
        if action == "issue_token":
            return self.tokens.issue(p["scope"], label=p.get("label", ""))
        if action == "revoke_token":
            return self.tokens.revoke(p["token_id"])
        if action == "list_tokens":
            return {"tokens": self.tokens.list_metadata()}
        if action == "shutdown":
            if self._shutdown_callback is not None:
                self._shutdown_callback()
            return {"shutting_down": True}
        raise ValueError(f"unhandled action: {action}")
