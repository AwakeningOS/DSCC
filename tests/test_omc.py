from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from dscc.canonical import cid_for
from dscc.omc import (
    CAPABILITY_SCHEMA, MODEL_SCHEMA, TRAINING_SCHEMA,
    validate_capability, validate_model, validate_training_run,
)
from dscc.omc_service import OpenModelCommons
from dscc.store import init_node

ROOT = Path(__file__).resolve().parents[1]


def model_payload(blocks, *, minimum_memory_bytes=None):
    total = sum(size for _, size, _ in blocks)
    return {
        "schema": MODEL_SCHEMA,
        "name": "tiny-open-model",
        "revision": "r1",
        "architecture": {
            "family": "transformer-decoder",
            "config": {"layers": 2, "hidden_size": 64},
        },
        "tokenizer": {"id": "tiny-tokenizer", "revision": "1"},
        "weights": [
            {"cid": cid, "bytes": size, "format": "raw-test", "name": name}
            for cid, size, name in blocks
        ],
        "runtime": {
            "minimum_memory_bytes": minimum_memory_bytes or total,
            "precisions": ["fp32"],
            "frameworks": ["test-runtime"],
        },
        "provenance": {
            "parent_model_cids": [],
            "training_run_cids": [],
            "dataset_cids": [],
            "code_cids": [],
        },
    }


def capability(label, memory, *, device_id="gpu0", network_class="lan"):
    return {
        "schema": CAPABILITY_SCHEMA,
        "node_label": label,
        "devices": [{
            "id": device_id,
            "class": "gpu",
            "vendor": "test",
            "model": "virtual",
            "usable_memory_bytes": memory,
            "supported_precisions": ["fp32"],
            "runtime_tags": ["test-runtime"],
        }],
        "network": {
            "class": network_class,
            "down_mbps": 1000,
            "up_mbps": 1000,
            "latency_ms": 1,
        },
        "policy": {
            "accepted_job_classes": ["inference", "training"],
            "public_inference": False,
            "public_training": False,
            "max_job_seconds": 3600,
        },
    }


def test_omc_examples_match_json_schema_and_runtime():
    pairs = [
        ("omc_model.schema.json", "model_profile.json", validate_model),
        ("omc_capability.schema.json", "capability_profile.json", validate_capability),
    ]
    for schema_name, example_name, validator in pairs:
        schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
        example = json.loads((ROOT / "examples" / "omc" / example_name).read_text(encoding="utf-8"))
        jsonschema.validate(example, schema)
        validator(example)


def test_large_block_store_is_content_addressed_and_detects_tamper(tmp_path):
    node = init_node(tmp_path / "node", block_quota_gb=1)
    omc = OpenModelCommons(node)
    source = tmp_path / "weights.bin"
    source.write_bytes(b"open-model-weights")
    first = omc.add_block(source)
    second = omc.add_block(source)
    assert first == second
    assert first["cid"] == cid_for(b"open-model-weights")
    assert node.status()["blocks"] == 1

    stored = node.blocks.root / first["cid"]
    stored.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="CID mismatch"):
        omc.verify_block(first["cid"])


def test_model_manifest_tracks_local_block_availability(tmp_path):
    node = init_node(tmp_path / "node", block_quota_gb=1)
    omc = OpenModelCommons(node)
    block = node.blocks.add_bytes(b"weights")
    payload = model_payload([(block["cid"], block["bytes"], "weights.bin")])
    saved = omc.record_model(payload, license="Apache-2.0")
    assert saved["complete_local_copy"] is True
    assert saved["execution_available"] is False
    assert saved["weight_blocks"][0]["available_local"] is True

    missing = model_payload([(cid_for(b"not-here"), 8, "missing.bin")])
    remote = omc.record_model(missing)
    assert remote["complete_local_copy"] is False
    assert remote["missing_blocks"] == [cid_for(b"not-here")]


def test_single_device_inference_plan_never_executes(tmp_path):
    node = init_node(tmp_path / "node")
    omc = OpenModelCommons(node)
    block = node.blocks.add_bytes(b"12345678")
    model = omc.record_model(model_payload([(block["cid"], 8, "w0")], minimum_memory_bytes=16))
    cap = omc.record_capability(capability("large", 64))
    plan = omc.plan_inference(model["cid"], [cap["cid"]])
    assert plan["mode"] == "single_device_replica"
    assert plan["execution_authorized"] is False
    assert plan["network_execution"] is False
    assert plan["placements"][0]["weight_blocks"] == [block["cid"]]


def test_pipeline_plan_uses_independent_weight_shards(tmp_path):
    node = init_node(tmp_path / "node")
    omc = OpenModelCommons(node)
    a = node.blocks.add_bytes(b"aaaaaaaa")
    b = node.blocks.add_bytes(b"bbbbbbbb")
    model = omc.record_model(model_payload([
        (a["cid"], 8, "a"), (b["cid"], 8, "b")
    ], minimum_memory_bytes=16))
    c1 = omc.record_capability(capability("n1", 8))
    c2 = omc.record_capability(capability("n2", 8))
    plan = omc.plan_inference(model["cid"], [c1["cid"], c2["cid"]])
    assert plan["mode"] == "pipeline_proposal"
    assert len(plan["placements"]) == 2
    assert {x for p in plan["placements"] for x in p["weight_blocks"]} == {a["cid"], b["cid"]}
    assert any("latency" in warning for warning in plan["warnings"])


def test_pipeline_rejects_unsplittable_shard(tmp_path):
    node = init_node(tmp_path / "node")
    omc = OpenModelCommons(node)
    big = cid_for(b"0123456789")
    small = cid_for(b"x")
    model = omc.record_model(model_payload([
        (big, 10, "big"), (small, 1, "small")
    ], minimum_memory_bytes=11))
    c1 = omc.record_capability(capability("n1", 6))
    c2 = omc.record_capability(capability("n2", 6))
    with pytest.raises(ValueError, match="split weights"):
        omc.plan_inference(model["cid"], [c1["cid"], c2["cid"]])


def test_training_run_preserves_model_and_capability_lineage(tmp_path):
    node = init_node(tmp_path / "node")
    omc = OpenModelCommons(node)
    block = node.blocks.add_bytes(b"weights")
    model = omc.record_model(model_payload([(block["cid"], block["bytes"], "weights")]))
    cap = omc.record_capability(capability("trainer", 1024))
    run = {
        "schema": TRAINING_SCHEMA,
        "parent_model_cid": model["cid"],
        "dataset_cids": [],
        "code_cids": [],
        "capability_cids": [cap["cid"]],
        "method": "synthetic local-step training record",
        "token_count": 100,
        "state": "succeeded",
        "metrics": {"loss": "1.23"},
        "checkpoint_blocks": [
            {"cid": block["cid"], "bytes": block["bytes"], "name": "checkpoint.bin"}
        ],
    }
    saved = omc.record_training_run(run)
    body = node.fetch(saved["cid"])["body"]
    assert body["parents"] == [model["cid"], cap["cid"]]
    assert saved["executed_by_dscc"] is False
    assert saved["missing_checkpoint_blocks"] == []


@pytest.mark.parametrize("mutation", ["float", "precision", "duplicate-device"])
def test_profile_validation_rejects_nonportable_or_inconsistent_data(mutation):
    payload = capability("n", 100)
    if mutation == "float":
        payload["network"]["latency_ms"] = 1.5
    elif mutation == "precision":
        payload["devices"][0]["supported_precisions"] = ["mystery"]
    else:
        payload["devices"].append(dict(payload["devices"][0]))
    with pytest.raises(ValueError):
        validate_capability(payload)
