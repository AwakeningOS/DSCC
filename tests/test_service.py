"""T001 acceptance tests: authenticated local service, loopback IPC and scope boundary."""
from __future__ import annotations

import http.client
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from dscc.canonical import canonical_bytes
from dscc.ipc import LocalIPCServer, LocalServiceClient
from dscc.mcp_server import MCPServer
from dscc.models import manifest
from dscc.service import AuthenticationError, AuthorizationError, OWNER_ACTIONS
from dscc.store import Node, init_node

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def running_service(tmp_path):
    node = init_node(tmp_path / "svc-node")
    server = LocalIPCServer(node)
    owner_tok = server.service.issue_bootstrap_token("owner", label="owner-cli")["token"]
    model_tok_a = server.service.issue_bootstrap_token("model", label="client-a")["token"]
    model_tok_b = server.service.issue_bootstrap_token("model", label="client-b")["token"]
    server.start_background()
    try:
        yield server, node, owner_tok, model_tok_a, model_tok_b
    finally:
        server.stop()


def test_public_bind_address_is_rejected(tmp_path):
    node = init_node(tmp_path / "no-public")
    for bad_host in ("0.0.0.0", "::", "192.168.1.10", "localhost"):
        with pytest.raises(ValueError, match="127.0.0.1"):
            LocalIPCServer(node, host=bad_host)


def test_client_rejects_remote_url():
    for bad_url in ("https://example.com:8443", "http://192.168.1.5:8000", "http://127.0.0.1"):
        with pytest.raises(ValueError):
            LocalServiceClient(bad_url, "tok")


def test_two_model_clients_share_assets_and_preserve_signed_cids(running_service):
    server, node, owner_tok, tok_a, tok_b = running_service
    client_a = LocalServiceClient(server.url, tok_a)
    client_b = LocalServiceClient(server.url, tok_b)

    doc = manifest("Dataset", "Shared values", {"values": [2, 5, 9]})
    recorded = client_a.record_manifest("Dataset", "Shared values", {"values": [2, 5, 9]})
    cid = recorded["cid"]

    fetched_b = client_b.fetch(cid)
    assert fetched_b["cid"] == cid
    assert fetched_b["body"] == doc
    assert fetched_b["public_key"] == node.public_key
    assert canonical_bytes(fetched_b["body"]) == canonical_bytes(node.fetch(cid)["body"])
    assert client_b.search("Shared values")[0]["cid"] == cid

    # Token file never stores plaintext tokens.
    raw_token_file = (node.home / "tokens.json").read_text(encoding="utf-8")
    assert tok_a not in raw_token_file
    assert owner_tok not in raw_token_file


def test_model_token_cannot_invoke_any_owner_action(running_service):
    server, node, owner_tok, tok_a, _ = running_service
    model_client = LocalServiceClient(server.url, tok_a)
    owner_client = LocalServiceClient(server.url, owner_tok)

    cid = model_client.record_manifest("Dataset", "Job input", {"values": [1, 2, 3]})["cid"]
    job = model_client.submit_job(cid)
    assert job["state"] == "pending"

    for action in sorted(OWNER_ACTIONS):
        with pytest.raises(AuthorizationError):
            model_client.call(action, {"job_id": job["id"], "cid": cid})

    # Owner approves and runs cleanly.
    approved = owner_client.call("approve_job", {"job_id": job["id"]})
    assert approved["state"] == "approved"
    done = owner_client.call("run_job", {"job_id": job["id"]})
    assert done["state"] == "succeeded"
    assert model_client.fetch(done["output_cid"])["body"]["data"]["result"] == {
        "count": 3, "sum": 6, "min": 1, "max": 3,
    }


def test_invalid_revoked_and_missing_credentials_rejected(running_service):
    server, _, owner_tok, _, _ = running_service
    owner_client = LocalServiceClient(server.url, owner_tok)

    issued = owner_client.call("issue_token", {"scope": "model", "label": "ephemeral"})
    ephemeral_client = LocalServiceClient(server.url, issued["token"])
    assert ephemeral_client.status()["authenticated_scope"] == "model"

    owner_client.call("revoke_token", {"token_id": issued["token_id"]})
    with pytest.raises(AuthenticationError):
        ephemeral_client.status()

    for bad_token in ("invalid", "dscc_owner_deadbeef.wrong", "dscc_model_" + issued["token_id"] + ".tampered"):
        with pytest.raises(AuthenticationError):
            LocalServiceClient(server.url, bad_token).status()


def test_origin_sec_fetch_and_host_rebinding_rejected(running_service):
    server, _, _, tok_a, _ = running_service
    body = json.dumps({"action": "node_status", "params": {}}).encode("utf-8")

    def raw_post(headers: dict[str, str], path: str = "/rpc") -> int:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        try:
            conn.request("POST", path, body=body, headers=headers)
            return conn.getresponse().status
        finally:
            conn.close()

    base = {
        "Host": f"127.0.0.1:{server.port}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Authorization": f"Bearer {tok_a}",
    }
    assert raw_post(base) == 200
    assert raw_post({**base, "Origin": "https://evil.example"}) == 403
    assert raw_post({**base, "Origin": "null"}) == 403
    assert raw_post({**base, "Sec-Fetch-Site": "cross-site"}) == 403
    assert raw_post({**base, "Host": "evil.example:80"}) == 403
    assert raw_post({k: v for k, v in base.items() if k != "Authorization"}) == 401
    assert raw_post({**base, "Content-Type": "text/plain"}) == 415
    assert raw_post(base, path="/admin") == 404


def test_explicit_crash_recovery_detection_on_restart(tmp_path):
    node = init_node(tmp_path / "crash")
    cid = node.record(manifest("Dataset", "Crash fixture", {"values": [10, 20]}))
    job = node.submit_job(cid)
    node.approve_job(job["id"])
    # Simulate an abrupt worker crash leaving the job in 'running'.
    node._transition(job["id"], ("approved",), "running")

    server = LocalIPCServer(Node(node.home))
    owner_tok = server.service.issue_bootstrap_token("owner")["token"]
    server.start_background()
    try:
        owner = LocalServiceClient(server.url, owner_tok)
        status = owner.status()
        assert job["id"] in status["startup_orphaned_jobs"]
        assert job["id"] in status["recovery_required_jobs"]
        # Service did NOT silently auto-succeed or auto-fail the crashed job.
        assert owner.job_status(job["id"])["state"] == "running"
        recovered = owner.call("recover_job", {"job_id": job["id"]})
        assert recovered["state"] == "failed"
        assert owner.status()["recovery_required_jobs"] == []
    finally:
        server.stop()


def test_mcp_clients_over_authenticated_ipc_without_key_access(running_service):
    server, _, _, tok_a, tok_b = running_service
    mcp_a = MCPServer(LocalServiceClient(server.url, tok_a))
    mcp_b = MCPServer(LocalServiceClient(server.url, tok_b))

    for srv, name in ((mcp_a, "agent-A"), (mcp_b, "agent-B")):
        srv.dispatch({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": name, "version": "1"}},
        })
        srv.dispatch({"jsonrpc": "2.0", "method": "notifications/initialized"})

    assert mcp_a.node is None and mcp_b.node is None
    wrote = mcp_a.dispatch({
        "jsonrpc": "2.0", "id": 2, "method": "tools/call",
        "params": {"name": "record_artifact", "arguments": {
            "kind": "MemoryCapsule", "title": "IPC handoff", "data": {"note": "shared via service"}
        }},
    })
    assert wrote["result"]["isError"] is False
    cid = json.loads(wrote["result"]["content"][0]["text"])["cid"]

    read_b = mcp_b.dispatch({
        "jsonrpc": "2.0", "id": 3, "method": "resources/read",
        "params": {"uri": f"dscc://artifact/{cid}"},
    })
    payload = json.loads(read_b["result"]["contents"][0]["text"])
    assert payload["body"]["data"]["note"] == "shared via service"
