"""One-PC handoff demo. Transfer is an explicit file bundle, not P2P."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from .models import manifest
from .store import init_node


def run_demo() -> dict:
    with tempfile.TemporaryDirectory(prefix="dscc-demo-") as temp:
        root = Path(temp)
        a, b, c = [init_node(root / name) for name in ("a-proposer", "b-worker", "c-reader")]
        input_cid = a.record(manifest("Dataset", "Materials sample measurements", {
            "values": [4, 7, 7, 10], "units": "arbitrary demonstration units",
            "note": "Synthetic integer data; no materials-science claim.",
        }, summary="materials example input", license="CC0-1.0"))
        bundle_ab = root / "a-to-b.json"
        bundle_ab.write_text(json.dumps(a.export_bundle(input_cid)), encoding="utf-8")
        b.import_bundle(json.loads(bundle_ab.read_text()), {a.public_key})
        job = b.submit_job(input_cid)
        assert job["state"] == "pending"
        b.approve_job(job["id"])
        complete = b.run_job(job["id"])
        output_cid = complete["output_cid"]
        bundle_bc = root / "b-to-c.json"
        bundle_bc.write_text(json.dumps(b.export_bundle(output_cid)), encoding="utf-8")
        c.import_bundle(json.loads(bundle_bc.read_text()), {a.public_key, b.public_key})
        fetched = c.fetch(output_cid)
        expected = {"count": 4, "sum": 28, "min": 4, "max": 10}
        assert fetched["body"]["data"]["result"] == expected
        # Re-open the reader: continuity is on disk, not tied to a model process.
        reopened = init_node(root / "c-reader")
        assert reopened.fetch(input_cid)["body"]["data"]["values"] == [4, 7, 7, 10]
        assert reopened.search("Integer analysis")
        verification = reopened.verify_artifact(output_cid)
        assert verification["signature_valid"] and verification["missing_parents"] == []
        for node in (a, b, c):
            assert node.audit()["valid"]
        return {"success": True, "logical_nodes": 3, "physical_hosts": 1,
                "transport": "explicit JSON file bundles", "p2p_tested": False,
                "gpu_tested": False, "host_app_tested": False,
                "input_cid": input_cid, "output_cid": output_cid,
                "result": expected, "reader_artifacts": reopened.status()["artifacts"],
                "integrity_check": verification, "temporary_files_removed_on_exit": True}
