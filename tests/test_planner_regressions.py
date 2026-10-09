"""Full validated planner regressions. All hardware claims are synthetic."""
import copy

import pytest

from dscc.canonical import canonical_bytes, cid_for
from dscc.omc import CAPABILITY_SCHEMA, MODEL_SCHEMA
from dscc.planner import plan_inference


def model_and_caps(sizes, memories):
    weights = [{"cid": cid_for(f"block-{i}".encode()), "bytes": size,
                "format": "raw-test", "name": f"w{i}"} for i, size in enumerate(sizes)]
    model = {
        "schema": MODEL_SCHEMA, "name": "packing-fixture", "revision": "1",
        "architecture": {"family": "test", "config": {}},
        "tokenizer": {"id": "test", "revision": "1"}, "weights": weights,
        "runtime": {"minimum_memory_bytes": sum(sizes), "precisions": ["fp32"],
                    "frameworks": ["test-runtime"]},
        "provenance": {"parent_model_cids": [], "training_run_cids": [],
                       "dataset_cids": [], "code_cids": []},
    }
    caps = []
    for i, memory in enumerate(memories):
        cap = {
            "schema": CAPABILITY_SCHEMA, "node_label": f"node-{i}",
            "devices": [{"id": "gpu0", "class": "gpu", "vendor": "test", "model": "virtual",
                         "usable_memory_bytes": memory, "supported_precisions": ["fp32"],
                         "runtime_tags": ["test-runtime"]}],
            "network": {"class": "lan", "down_mbps": 1, "up_mbps": 1, "latency_ms": 1},
            "policy": {"accepted_job_classes": ["inference"], "public_inference": False,
                       "public_training": False, "max_job_seconds": 60},
        }
        caps.append((cid_for(f"cap-{i}".encode()), cap))
    return model, caps


def test_planner_recovers_two_device_counterexample_without_authorization():
    model, caps = model_and_caps([14, 10, 10, 7, 7], [24, 24])
    before = copy.deepcopy((model, caps))
    plan = plan_inference(model, caps)
    assert plan["mode"] == "pipeline_proposal"
    assert [p["assigned_bytes"] for p in plan["placements"]] == [24, 24]
    assert plan["execution_authorized"] is False and plan["network_execution"] is False
    assert (model, caps) == before
    payload = {key: value for key, value in plan.items() if key != "plan_id"}
    assert plan["plan_id"] == cid_for(canonical_bytes(payload))
    assert plan == plan_inference(model, list(reversed(caps)))


def test_legacy_success_keeps_exact_plan_payload_and_id():
    model, caps = model_and_caps([8, 8], [8, 8])
    cap_ids = sorted(cid for cid, _ in caps)
    weights = sorted(w["cid"] for w in model["weights"])
    expected = {
        "schema": "dscc.omc.inference-plan/0.1", "model_name": "packing-fixture",
        "model_revision": "1", "precision": "fp32", "required_memory_bytes": 16,
        "total_weight_bytes": 16, "execution_authorized": False, "network_execution": False,
        "warnings": ["cross-capability pipeline latency is unmeasured; benchmark before execution"],
        "mode": "pipeline_proposal", "placements": [
            {"capability_cid": cap_ids[0], "device_id": "gpu0", "weight_blocks": [weights[1]], "assigned_bytes": 8},
            {"capability_cid": cap_ids[1], "device_id": "gpu0", "weight_blocks": [weights[0]], "assigned_bytes": 8},
        ],
    }
    assert plan_inference(model, caps) == {"plan_id": cid_for(canonical_bytes(expected)), **expected}


def test_unsplittable_shard_still_requests_finer_blocks():
    model, caps = model_and_caps([10, 1], [6, 6])
    with pytest.raises(ValueError, match="split weights"):
        plan_inference(model, caps)


def test_does_not_consume_gpu_excluded_by_owner_policy():
    model, caps = model_and_caps([8, 8], [8, 8])
    caps[0][1]["policy"]["accepted_job_classes"] = []
    with pytest.raises(ValueError, match="memory is insufficient"):
        plan_inference(model, caps)
