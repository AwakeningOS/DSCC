"""Deterministic local planning for Open Model Commons inference.

This planner consumes signed capability records and model manifests. It creates
an execution proposal only; it neither contacts peers nor starts model code.
"""
from __future__ import annotations

from typing import Any

from .canonical import canonical_bytes, cid_for
from .omc import validate_capability, validate_model


def plan_inference(model: dict[str, Any],
                   capabilities: list[tuple[str, dict[str, Any]]],
                   precision: str | None = None) -> dict[str, Any]:
    model = validate_model(model)
    if not capabilities:
        raise ValueError("at least one compute capability is required")
    supported = model["runtime"]["precisions"]
    chosen_precision = precision or supported[0]
    if chosen_precision not in supported:
        raise ValueError("requested precision is not supported by the model")

    devices = []
    networks = {}
    for capability_cid, payload in capabilities:
        cap = validate_capability(payload)
        networks[capability_cid] = cap["network"]
        if "inference" not in cap["policy"]["accepted_job_classes"]:
            continue
        for device in cap["devices"]:
            if device["class"] != "gpu":
                continue
            if chosen_precision not in device["supported_precisions"]:
                continue
            devices.append({
                "capability_cid": capability_cid,
                "device_id": device["id"],
                "usable_memory_bytes": device["usable_memory_bytes"],
                "runtime_tags": device["runtime_tags"],
            })
    if not devices:
        raise ValueError("no compatible inference GPU was advertised")

    devices.sort(key=lambda d: (-d["usable_memory_bytes"], d["capability_cid"], d["device_id"]))
    total_weight_bytes = sum(row["bytes"] for row in model["weights"])
    required = max(total_weight_bytes, model["runtime"]["minimum_memory_bytes"])

    plan: dict[str, Any] = {
        "schema": "dscc.omc.inference-plan/0.1",
        "model_name": model["name"],
        "model_revision": model["revision"],
        "precision": chosen_precision,
        "required_memory_bytes": required,
        "total_weight_bytes": total_weight_bytes,
        "execution_authorized": False,
        "network_execution": False,
        "warnings": [],
    }

    replicas = [d for d in devices if d["usable_memory_bytes"] >= required]
    if replicas:
        selected = replicas[0]
        plan["mode"] = "single_device_replica"
        plan["placements"] = [{
            "capability_cid": selected["capability_cid"],
            "device_id": selected["device_id"],
            "weight_blocks": [w["cid"] for w in model["weights"]],
            "assigned_bytes": total_weight_bytes,
        }]
    else:
        if sum(d["usable_memory_bytes"] for d in devices) < required:
            raise ValueError("compatible advertised GPU memory is insufficient")
        remaining = {
            (d["capability_cid"], d["device_id"]): d["usable_memory_bytes"] for d in devices
        }
        placements = {
            (d["capability_cid"], d["device_id"]): [] for d in devices
        }
        assigned = {
            (d["capability_cid"], d["device_id"]): 0 for d in devices
        }
        for weight in sorted(model["weights"], key=lambda w: (-w["bytes"], w["cid"])):
            choices = [
                (capacity, key) for key, capacity in remaining.items()
                if capacity >= weight["bytes"]
            ]
            if not choices:
                raise ValueError("a model shard does not fit any compatible GPU; split weights more finely")
            _, key = max(choices, key=lambda row: (row[0], row[1]))
            placements[key].append(weight["cid"])
            assigned[key] += weight["bytes"]
            remaining[key] -= weight["bytes"]
        used = [key for key, rows in placements.items() if rows]
        if len(used) < 2:
            raise ValueError("pipeline planning expected multiple devices")
        plan["mode"] = "pipeline_proposal"
        plan["placements"] = [{
            "capability_cid": key[0],
            "device_id": key[1],
            "weight_blocks": placements[key],
            "assigned_bytes": assigned[key],
        } for key in used]
        network_classes = {networks[key[0]]["class"] for key in used}
        if len({key[0] for key in used}) > 1:
            plan["warnings"].append(
                "cross-capability pipeline latency is unmeasured; benchmark before execution"
            )
        if "unknown" in network_classes:
            plan["warnings"].append("one or more capability records have unknown network class")

    encoded = canonical_bytes(plan)
    return {"plan_id": cid_for(encoded), **plan}
