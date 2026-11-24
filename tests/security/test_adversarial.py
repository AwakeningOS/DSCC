"""T009 adversarial verification & security regression suite.

Treats the core, IPC boundary, OMC planner/inspector, block store and catalog
as hostile-input surfaces. Covers every concrete bug found during audit plus
cryptographic, authorization, concurrency, quota and framing edge cases.
"""
from __future__ import annotations

import http.client
import json
import os
import stat
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from dscc.canonical import MAX_OBJECT_BYTES, canonical_bytes, cid_for
from dscc.catalog import CatalogIndex
from dscc.ipc import LocalIPCServer, LocalServiceClient, MAX_IPC_BODY_BYTES
from dscc.models import manifest
from dscc.omc import CAPABILITY_SCHEMA, MODEL_SCHEMA
from dscc.omc_service import OpenModelCommons
from dscc.planner import plan_inference
from dscc.store import Node, init_node

ROOT = Path(__file__).resolve().parents[1].parent


def _env() -> dict[str, str]:
    return {**os.environ, "PYTHONPATH": str(ROOT / "src")}


@pytest.mark.skipif(os.name != "posix", reason="POSIX mode bits apply on Unix")
def test_signing_key_and_token_store_have_strict_owner_only_permissions(tmp_path):
    node = init_node(tmp_path / "perm-node")
    key_mode = stat.S_IMODE((node.home / "signing.key").stat().st_mode)
    dir_mode = stat.S_IMODE(node.home.stat().st_mode)
    assert key_mode == 0o600
    assert dir_mode == 0o700

    server = LocalIPCServer(node)
    server.service.issue_bootstrap_token("owner", label="audit")
    tok_mode = stat.S_IMODE((node.home / "tokens.json").stat().st_mode)
    assert tok_mode == 0o600


@pytest.mark.skipif(os.name != "posix", reason="Symlink attack check on POSIX")
def test_symlink_attacks_on_key_and_block_store_are_rejected(tmp_path):
    node = init_node(tmp_path / "sym-node")
    secret = tmp_path / "secret.txt"
    secret.write_bytes(b"s" * 32)

    link_input = tmp_path / "link.bin"
    link_input.symlink_to(secret)
    with pytest.raises(ValueError, match="non-symlink"):
        node.blocks.add_file(link_input)

    key_path = node.home / "signing.key"
    key_path.unlink()
    key_path.symlink_to(secret)
    with pytest.raises(ValueError, match="symlink"):
        Node(node.home)


def test_verify_artifact_and_verify_lineage_detect_corrupted_parent(tmp_path):
    node = init_node(tmp_path / "lineage-node")
    grandparent = node.record(manifest("Dataset", "GP", {"values": [1, 2]}))
    parent = node.record(manifest("Claim", "P", {"note": "derived"}, parents=[grandparent]))
    child = node.record(manifest("MemoryCapsule", "C", {"note": "summary"}, parents=[parent]))

    ok = node.verify_lineage(child)
    assert ok["complete_lineage"] is True
    assert ok["verified_count"] == 3

    # Tamper with direct parent in SQLite; verify_artifact must NOT report clean.
    with node._transaction() as c:
        c.execute("UPDATE artifacts SET envelope=? WHERE cid=?", (b'{"corrupt":true}', parent))
    with pytest.raises(ValueError, match="CID mismatch"):
        node.verify_artifact(child)

    # Restore from objects/ and tamper with grandparent; verify_lineage must catch deep corruption.
    node.rebuild_from_objects()
    with node._transaction() as c:
        c.execute("UPDATE artifacts SET envelope=? WHERE cid=?", (b'{"corrupt":true}', grandparent))
    with pytest.raises(ValueError, match="CID mismatch"):
        node.verify_lineage(child)


def test_omc_planner_rejects_duplicate_capability_vram_inflation():
    block_cid = cid_for(b"w" * 16)
    model = {
        "schema": MODEL_SCHEMA, "name": "m", "revision": "1",
        "architecture": {"family": "test", "config": {}},
        "tokenizer": {"id": "tok", "revision": "1"},
        "weights": [
            {"cid": cid_for(b"a"), "bytes": 10, "format": "raw", "name": "w0"},
            {"cid": cid_for(b"b"), "bytes": 10, "format": "raw", "name": "w1"},
        ],
        "runtime": {"minimum_memory_bytes": 20, "precisions": ["fp32"], "frameworks": ["rt"]},
        "provenance": {"parent_model_cids": [], "training_run_cids": [],
                       "dataset_cids": [], "code_cids": []},
    }
    cap = {
        "schema": CAPABILITY_SCHEMA, "node_label": "single-12b-gpu",
        "devices": [{"id": "gpu0", "class": "gpu", "vendor": "v", "model": "m",
                     "usable_memory_bytes": 12, "supported_precisions": ["fp32"], "runtime_tags": ["rt"]}],
        "network": {"class": "lan", "down_mbps": 100, "up_mbps": 100, "latency_ms": 1},
        "policy": {"accepted_job_classes": ["inference"], "public_inference": False,
                   "public_training": False, "max_job_seconds": 60},
    }
    cap_cid = cid_for(b"same-cap")
    with pytest.raises(ValueError, match="duplicate capability_cid"):
        plan_inference(model, [(cap_cid, cap), (cap_cid, cap)])


def test_omc_planner_warns_when_selected_pipeline_devices_lack_declared_runtime_overhead():
    model = {
        "schema": MODEL_SCHEMA, "name": "overhead-model", "revision": "1",
        "architecture": {"family": "test", "config": {}},
        "tokenizer": {"id": "tok", "revision": "1"},
        "weights": [
            {"cid": cid_for(b"w0"), "bytes": 8, "format": "raw", "name": "w0"},
            {"cid": cid_for(b"w1"), "bytes": 8, "format": "raw", "name": "w1"},
        ],
        # Total weights = 16, but model declares minimum_memory_bytes = 22 (6 bytes runtime overhead).
        "runtime": {"minimum_memory_bytes": 22, "precisions": ["fp32"], "frameworks": ["rt"]},
        "provenance": {"parent_model_cids": [], "training_run_cids": [],
                       "dataset_cids": [], "code_cids": []},
    }
    caps = []
    for i in range(3):
        cap = {
            "schema": CAPABILITY_SCHEMA, "node_label": f"n{i}",
            "devices": [{"id": "gpu0", "class": "gpu", "vendor": "v", "model": "m",
                         "usable_memory_bytes": 8, "supported_precisions": ["fp32"], "runtime_tags": ["rt"]}],
            "network": {"class": "lan", "down_mbps": 100, "up_mbps": 100, "latency_ms": 1},
            "policy": {"accepted_job_classes": ["inference"], "public_inference": False,
                       "public_training": False, "max_job_seconds": 60},
        }
        caps.append((cid_for(f"cap-{i}".encode()), cap))
    plan = plan_inference(model, caps)
    assert plan["mode"] == "pipeline_proposal"
    assert any("headroom is insufficient" in w for w in plan["warnings"])


def test_omc_inspect_model_detects_manifest_size_lie_and_corrupted_block(tmp_path):
    node = init_node(tmp_path / "omc-lie")
    omc = OpenModelCommons(node)
    blk = node.blocks.add_bytes(b"actual-bytes")
    # Manifest claims wrong byte length (999 instead of 12).
    lying_model = {
        "schema": MODEL_SCHEMA, "name": "lying", "revision": "1",
        "architecture": {"family": "test", "config": {}},
        "tokenizer": {"id": "tok", "revision": "1"},
        "weights": [{"cid": blk["cid"], "bytes": 999, "format": "raw", "name": "w0"}],
        "runtime": {"minimum_memory_bytes": 999, "precisions": ["fp32"], "frameworks": ["rt"]},
        "provenance": {"parent_model_cids": [], "training_run_cids": [],
                       "dataset_cids": [], "code_cids": []},
    }
    res = omc.record_model(lying_model)
    assert res["complete_local_copy"] is False
    assert res["mismatched_blocks"] == [blk["cid"]]
    assert res["weight_blocks"][0]["size_matches"] is False

    # Honest manifest, then silently corrupt block contents on disk with identical byte length.
    honest_model = {**lying_model, "revision": "2",
                    "weights": [{"cid": blk["cid"], "bytes": blk["bytes"], "format": "raw", "name": "w0"}],
                    "runtime": {"minimum_memory_bytes": blk["bytes"], "precisions": ["fp32"], "frameworks": ["rt"]}}
    saved = omc.record_model(honest_model)
    assert saved["complete_local_copy"] is True
    (node.blocks.root / blk["cid"]).write_bytes(b"TAMPER-BYTES")  # same 12-byte length
    deep = omc.inspect_model(saved["cid"], verify_blocks=True)
    assert deep["complete_local_copy"] is False
    assert deep["mismatched_blocks"] == [blk["cid"]]
    assert deep["weight_blocks"][0]["digest_verified"] is False


def test_block_store_enforces_quota_under_concurrent_writes(tmp_path):
    node = init_node(tmp_path / "blk-race", block_quota_gb=1)
    # Tighten quota artificially to 100 bytes for deterministic concurrency stress.
    node.blocks.quota_bytes = 100

    def put(i: int) -> bool:
        try:
            node.blocks.add_bytes(f"payload-{i:04d}-".encode() + b"x" * 20)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=8) as pool:
        outcomes = list(pool.map(put, range(12)))
    assert any(outcomes) and not all(outcomes)
    assert node.blocks.usage_bytes() <= 100


def test_ipc_rejects_oversized_body_and_non_post_methods(tmp_path):
    node = init_node(tmp_path / "ipc-dos")
    server = LocalIPCServer(node)
    tok = server.service.issue_bootstrap_token("model")["token"]
    server.start_background()
    try:
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        try:
            conn.request("GET", "/rpc", headers={"Host": f"127.0.0.1:{server.port}"})
            assert conn.getresponse().status == 405
        finally:
            conn.close()

        # Advertise Content-Length above MAX_IPC_BODY_BYTES -> rejected immediately with 413.
        conn = http.client.HTTPConnection("127.0.0.1", server.port, timeout=5)
        try:
            conn.putrequest("POST", "/rpc")
            conn.putheader("Host", f"127.0.0.1:{server.port}")
            conn.putheader("Content-Type", "application/json")
            conn.putheader("Authorization", f"Bearer {tok}")
            conn.putheader("Content-Length", str(MAX_IPC_BODY_BYTES + 1))
            conn.endheaders()
            assert conn.getresponse().status == 413
        finally:
            conn.close()
    finally:
        server.stop()


def test_fts5_search_neutralizes_hostile_query_syntax(tmp_path):
    node = init_node(tmp_path / "fts-safe")
    node.record(manifest("Claim", "Normal entry", {"text": "control sample"}))
    index = CatalogIndex(node)
    index.rebuild()
    for hostile in ('"unterminated', 'NEAR/0 (a OR b)', "title:secret*", "' OR 1=1 --", "NOT *"):
        res = index.search(hostile)
        assert isinstance(res["hits"], list)


def test_real_subprocess_mcp_over_ipc_without_key_path(tmp_path):
    """End-to-end T001 subprocess test: MCP subprocess uses DSCC_TOKEN + --service-url only."""
    node = init_node(tmp_path / "ipc-e2e")
    server = LocalIPCServer(node)
    model_tok = server.service.issue_bootstrap_token("model", label="subproc-mcp")["token"]
    server.start_background()
    try:
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2025-11-25", "capabilities": {},
                        "clientInfo": {"name": "subproc-client", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
             "params": {"name": "record_artifact", "arguments": {
                 "kind": "MemoryCapsule", "title": "Remote-IPC note",
                 "data": {"fact": "written without touching signing.key"}
             }}},
            {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
             "params": {"name": "node_status", "arguments": {}}},
        ]
        # Point --home to a nonexistent directory to prove MCP never opens local node files!
        proc = subprocess.run(
            [sys.executable, "-m", "dscc", "--home", str(tmp_path / "nonexistent-home"),
             "mcp", "--service-url", server.url],
            input="\n".join(json.dumps(m) for m in msgs) + "\n",
            capture_output=True, text=True,
            env={**_env(), "DSCC_TOKEN": model_tok},
            timeout=15,
        )
        assert proc.returncode == 0, proc.stderr
        out = [json.loads(line) for line in proc.stdout.splitlines()]
        cid = json.loads(out[1]["result"]["content"][0]["text"])["cid"]
        status = json.loads(out[2]["result"]["content"][0]["text"])
        assert status["service_boundary"] == "authenticated-local-service"
        assert status["authenticated_scope"] == "model"
        assert node.fetch(cid)["body"]["data"]["fact"] == "written without touching signing.key"
    finally:
        server.stop()


def test_cli_cooperation_and_catalog_commands_end_to_end(tmp_path):
    node = init_node(tmp_path / "cli-e2e")
    obs = node.record(manifest("Dataset", "Missing unit note", {"value": "unknown unit"}))
    step_file = tmp_path / "step.json"
    step_file.write_text(json.dumps({
        "project": "cli-rhs",
        "contributor": {"kind": "agent", "name": "cli-test", "provider": None, "model": None, "snapshot": None},
        "step": {
            "schema": "dscc.cooperation.step/0.1",
            "episode_id": "ep-1",
            "stage": "assessment",
            "initiator": "agent_policy",
            "previous_cid": None,
            "evidence_cids": [obs],
            "details": {
                "missing": "temperature unit",
                "alternatives": ["continue", "ask_human"],
                "choice": "ask_human",
                "reason_summary": "ambiguous input",
            },
        },
    }), encoding="utf-8")
    base = [sys.executable, "-m", "dscc", "--home", str(node.home)]
    r1 = subprocess.run(base + ["cooperation-record", "--file", str(step_file)],
                        capture_output=True, text=True, env=_env(), timeout=15)
    assert r1.returncode == 0, r1.stderr
    step_cid = json.loads(r1.stdout)["cid"]

    r2 = subprocess.run(base + ["cooperation-history", step_cid],
                        capture_output=True, text=True, env=_env(), timeout=15)
    assert r2.returncode == 0, r2.stderr
    assert len(json.loads(r2.stdout)["steps"]) == 1

    r3 = subprocess.run(base + ["catalog-rebuild"],
                        capture_output=True, text=True, env=_env(), timeout=15)
    assert r3.returncode == 0, r3.stderr
    assert json.loads(r3.stdout)["search_index"]["indexed_artifacts"] == 2
