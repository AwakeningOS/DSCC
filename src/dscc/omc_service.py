"""Application facade for the local Open Model Commons foundation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .omc import (
    CAPABILITY_KEY, MODEL_KEY, TRAINING_KEY,
    capability_artifact, model_artifact, training_run_artifact,
    validate_capability, validate_model, validate_training_run,
)
from .planner import plan_inference


class OpenModelCommons:
    def __init__(self, node):
        self.node = node
        self.blocks = node.blocks

    def add_block(self, path: Path) -> dict:
        return self.blocks.add_file(path)

    def verify_block(self, cid: str) -> dict:
        return self.blocks.verify(cid)

    def record_model(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict:
        cid = self.node.record(model_artifact(payload, license=license))
        return self.inspect_model(cid)

    def _model_payload(self, cid: str) -> dict[str, Any]:
        body = self.node.fetch(cid)["body"]
        if body["kind"] != "MemoryCapsule" or set(body["data"]) != {MODEL_KEY}:
            raise ValueError("artifact is not an Open Model Commons model manifest")
        return validate_model(body["data"][MODEL_KEY])

    def inspect_model(self, cid: str) -> dict:
        payload = self._model_payload(cid)
        blocks = []
        missing = []
        for row in payload["weights"]:
            available = self.blocks.available(row["cid"])
            blocks.append({**row, "available_local": available})
            if not available:
                missing.append(row["cid"])
        return {
            "cid": cid,
            "profile": payload["schema"],
            "name": payload["name"],
            "revision": payload["revision"],
            "model": payload,
            "weight_blocks": blocks,
            "missing_blocks": missing,
            "complete_local_copy": not missing,
            "execution_available": False,
        }

    def record_capability(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict:
        validate_capability(payload)
        cid = self.node.record(capability_artifact(payload, license=license))
        return {"cid": cid, "capability": payload, "published": False}

    def _capability_payload(self, cid: str) -> dict[str, Any]:
        body = self.node.fetch(cid)["body"]
        if body["kind"] != "PolicyProfile" or set(body["data"]) != {CAPABILITY_KEY}:
            raise ValueError("artifact is not an Open Model Commons capability record")
        return validate_capability(body["data"][CAPABILITY_KEY])

    def record_training_run(self, payload: dict[str, Any], *, license: str = "NOASSERTION") -> dict:
        validate_training_run(payload)
        cid = self.node.record(training_run_artifact(payload, license=license))
        missing = [row["cid"] for row in payload["checkpoint_blocks"]
                   if not self.blocks.available(row["cid"])]
        return {
            "cid": cid,
            "training_run": payload,
            "missing_checkpoint_blocks": missing,
            "executed_by_dscc": False,
        }

    def training_run(self, cid: str) -> dict[str, Any]:
        body = self.node.fetch(cid)["body"]
        if body["kind"] != "ExperimentRun" or set(body["data"]) != {TRAINING_KEY}:
            raise ValueError("artifact is not an Open Model Commons training run")
        return validate_training_run(body["data"][TRAINING_KEY])

    def plan_inference(self, model_cid: str, capability_cids: list[str],
                       precision: str | None = None) -> dict:
        model = self._model_payload(model_cid)
        capabilities = [(cid, self._capability_payload(cid)) for cid in capability_cids]
        result = plan_inference(model, capabilities, precision)
        return {
            "model_cid": model_cid,
            "capability_cids": capability_cids,
            **result,
        }
