"""Versioned Open Model Commons payload contracts.

These payloads are wrapped in existing DSCC seed artifact kinds so old signed
records and CIDs remain valid. The profiles describe models, capabilities and
training observations; they do not execute models or advertise network peers.
"""
from __future__ import annotations

from typing import Any

from .canonical import canonical_bytes, validate_cid
from .models import manifest

MODEL_SCHEMA = "dscc.omc.model/0.1"
CAPABILITY_SCHEMA = "dscc.omc.capability/0.1"
TRAINING_SCHEMA = "dscc.omc.training-run/0.1"

MODEL_KEY = "omc_model"
CAPABILITY_KEY = "omc_capability"
TRAINING_KEY = "omc_training_run"

PRECISIONS = {"fp32", "fp16", "bf16", "int8", "int4", "other"}
DEVICE_CLASSES = {"gpu", "cpu", "storage", "relay"}
TRAINING_STATES = {"planned", "running", "succeeded", "failed", "interrupted"}


def _exact(doc: Any, fields: set[str], name: str) -> dict[str, Any]:
    if not isinstance(doc, dict) or set(doc) != fields:
        raise ValueError(f"{name} fields do not match the profile")
    return doc


def _text(value: Any, name: str, maximum: int = 512, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not empty and not value) or len(value) > maximum:
        raise ValueError(f"invalid {name}")
    return value


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"invalid {name}")
    return value


def _string_list(value: Any, name: str, *, allowed: set[str] | None = None,
                 maximum: int = 128) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"invalid {name}")
    if any(not isinstance(x, str) or not x for x in value):
        raise ValueError(f"invalid {name}")
    if len(set(value)) != len(value):
        raise ValueError(f"duplicate value in {name}")
    if allowed is not None and any(x not in allowed for x in value):
        raise ValueError(f"unsupported value in {name}")
    return value


def _cid_list(value: Any, name: str, maximum: int = 128) -> list[str]:
    rows = _string_list(value, name, maximum=maximum)
    for cid in rows:
        validate_cid(cid)
    return rows


def validate_model(payload: Any) -> dict[str, Any]:
    p = _exact(payload, {
        "schema", "name", "revision", "architecture", "tokenizer",
        "weights", "runtime", "provenance"
    }, "model")
    if p["schema"] != MODEL_SCHEMA:
        raise ValueError("unsupported model profile")
    _text(p["name"], "model name", 240)
    _text(p["revision"], "model revision", 128)
    architecture = _exact(p["architecture"], {"family", "config"}, "architecture")
    _text(architecture["family"], "architecture family", 128)
    if not isinstance(architecture["config"], dict):
        raise ValueError("architecture config must be an object")
    tokenizer = _exact(p["tokenizer"], {"id", "revision"}, "tokenizer")
    _text(tokenizer["id"], "tokenizer id", 240)
    _text(tokenizer["revision"], "tokenizer revision", 128)
    weights = p["weights"]
    if not isinstance(weights, list) or not 1 <= len(weights) <= 4096:
        raise ValueError("model requires 1..4096 weight blocks")
    seen = set()
    for row in weights:
        _exact(row, {"cid", "bytes", "format", "name"}, "weight block")
        cid = validate_cid(row["cid"])
        if cid in seen:
            raise ValueError("duplicate weight block CID")
        seen.add(cid)
        _integer(row["bytes"], "weight block bytes", 1)
        _text(row["format"], "weight format", 64)
        _text(row["name"], "weight block name", 240)
    runtime = _exact(p["runtime"], {
        "minimum_memory_bytes", "precisions", "frameworks"
    }, "runtime")
    _integer(runtime["minimum_memory_bytes"], "minimum memory bytes", 1)
    _string_list(runtime["precisions"], "precisions", allowed=PRECISIONS)
    if not runtime["precisions"]:
        raise ValueError("at least one precision is required")
    _string_list(runtime["frameworks"], "frameworks")
    if not runtime["frameworks"]:
        raise ValueError("at least one framework is required")
    provenance = _exact(p["provenance"], {
        "parent_model_cids", "training_run_cids", "dataset_cids", "code_cids"
    }, "model provenance")
    for field in provenance:
        _cid_list(provenance[field], field)
    canonical_bytes(p)
    return p


def model_parent_cids(payload: dict[str, Any]) -> list[str]:
    p = validate_model(payload)
    refs = []
    for field in ("parent_model_cids", "training_run_cids", "dataset_cids", "code_cids"):
        refs.extend(p["provenance"][field])
    return list(dict.fromkeys(refs))


def model_artifact(payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
    p = validate_model(payload)
    return manifest(
        "MemoryCapsule",
        f"Open model: {p['name']} @ {p['revision']}"[:240],
        {MODEL_KEY: p},
        summary="Versioned Open Model Commons model manifest; weight blocks are external immutable CIDs.",
        parents=model_parent_cids(p),
        license=license,
    )


def validate_capability(payload: Any) -> dict[str, Any]:
    p = _exact(payload, {"schema", "node_label", "devices", "network", "policy"},
               "compute capability")
    if p["schema"] != CAPABILITY_SCHEMA:
        raise ValueError("unsupported capability profile")
    _text(p["node_label"], "node label", 240)
    devices = p["devices"]
    if not isinstance(devices, list) or not 1 <= len(devices) <= 128:
        raise ValueError("capability requires 1..128 devices")
    device_ids = set()
    for device in devices:
        _exact(device, {
            "id", "class", "vendor", "model", "usable_memory_bytes",
            "supported_precisions", "runtime_tags"
        }, "device")
        ident = _text(device["id"], "device id", 128)
        if ident in device_ids:
            raise ValueError("duplicate device id")
        device_ids.add(ident)
        if device["class"] not in DEVICE_CLASSES:
            raise ValueError("unsupported device class")
        _text(device["vendor"], "device vendor", 128)
        _text(device["model"], "device model", 240)
        _integer(device["usable_memory_bytes"], "usable memory bytes", 0)
        _string_list(device["supported_precisions"], "supported precisions",
                     allowed=PRECISIONS)
        _string_list(device["runtime_tags"], "runtime tags")
    network = _exact(p["network"], {
        "class", "down_mbps", "up_mbps", "latency_ms"
    }, "network")
    _text(network["class"], "network class", 64)
    for field in ("down_mbps", "up_mbps", "latency_ms"):
        _integer(network[field], field, 0)
    policy = _exact(p["policy"], {
        "accepted_job_classes", "public_inference", "public_training",
        "max_job_seconds"
    }, "capability policy")
    _string_list(policy["accepted_job_classes"], "accepted job classes")
    if type(policy["public_inference"]) is not bool or type(policy["public_training"]) is not bool:
        raise ValueError("public flags must be booleans")
    _integer(policy["max_job_seconds"], "max job seconds", 1)
    canonical_bytes(p)
    return p


def capability_artifact(payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
    p = validate_capability(payload)
    return manifest(
        "PolicyProfile",
        f"Compute capability: {p['node_label']}"[:240],
        {CAPABILITY_KEY: p},
        summary="Owner-signed local compute capability advertisement; not a remote availability guarantee.",
        license=license,
    )


def validate_training_run(payload: Any) -> dict[str, Any]:
    p = _exact(payload, {
        "schema", "parent_model_cid", "dataset_cids", "code_cids",
        "capability_cids", "method", "token_count", "state", "metrics",
        "checkpoint_blocks"
    }, "training run")
    if p["schema"] != TRAINING_SCHEMA:
        raise ValueError("unsupported training-run profile")
    validate_cid(p["parent_model_cid"])
    for field in ("dataset_cids", "code_cids", "capability_cids"):
        _cid_list(p[field], field)
    _text(p["method"], "training method", 240)
    _integer(p["token_count"], "token count", 0)
    if p["state"] not in TRAINING_STATES:
        raise ValueError("unsupported training state")
    if not isinstance(p["metrics"], dict):
        raise ValueError("training metrics must be an object")
    blocks = p["checkpoint_blocks"]
    if not isinstance(blocks, list) or len(blocks) > 4096:
        raise ValueError("invalid checkpoint block list")
    seen = set()
    for row in blocks:
        _exact(row, {"cid", "bytes", "name"}, "checkpoint block")
        cid = validate_cid(row["cid"])
        if cid in seen:
            raise ValueError("duplicate checkpoint block CID")
        seen.add(cid)
        _integer(row["bytes"], "checkpoint bytes", 1)
        _text(row["name"], "checkpoint block name", 240)
    canonical_bytes(p)
    return p


def training_parent_cids(payload: dict[str, Any]) -> list[str]:
    p = validate_training_run(payload)
    refs = [p["parent_model_cid"]]
    for field in ("dataset_cids", "code_cids", "capability_cids"):
        refs.extend(p[field])
    return list(dict.fromkeys(refs))


def training_run_artifact(payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict[str, Any]:
    p = validate_training_run(payload)
    return manifest(
        "ExperimentRun",
        f"Open-model training run: {p['method']}"[:240],
        {TRAINING_KEY: p},
        summary="Recorded Open Model Commons training observation; recording does not execute training.",
        parents=training_parent_cids(p),
        license=license,
    )
