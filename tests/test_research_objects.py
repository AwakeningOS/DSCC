"""T007 acceptance tests: rebuildable FTS5/graph catalog, paper schema round-trip, PROV & RO-Crate."""
from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

from dscc.adapters import (
    export_prov_json,
    export_rocrate_dir,
    paper_to_seed,
    seed_to_paper,
    validate_paper_artifact,
    verify_rocrate_dir,
)
from dscc.canonical import canonical_bytes, cid_for
from dscc.catalog import CatalogIndex
from dscc.models import manifest
from dscc.research import ResearchService, SCHEMA as RESEARCH_SCHEMA
from dscc.store import Node, init_node

ROOT = Path(__file__).resolve().parents[1]


def _paper_claim(parent_cid: str | None = None) -> dict:
    prov = {"wasAssociatedWith": ["agent:researcher-1"]}
    if parent_cid is not None:
        prov["wasDerivedFrom"] = [parent_cid]
    return {
        "schemaVersion": "0.1",
        "objectType": "Claim",
        "title": "Hypothesized thermal stability trend",
        "description": "Unverified hypothesis derived from initial synthetic dataset.",
        "authors": [{"id": "did:example:author-1", "role": "proposer"}],
        "created": "2026-10-17T00:00:00Z",
        "license": "CC-BY-4.0",
        "payloads": [{"role": "statement", "cid": cid_for(b"hypothesis-body"), "mediaType": "text/plain", "size": 15}],
        "provenance": prov,
        "verification": {"class": "V3", "receipts": []},
        "sensitivity": "public",
        "retention": "archival",
    }


def test_paper_artifact_validates_against_original_schema_and_round_trips(tmp_path):
    orig_schema = json.loads(
        (ROOT / "docs/reference/original_schemas/dscc_artifact.schema.json").read_text(encoding="utf-8")
    )
    node = init_node(tmp_path / "paper-node")
    ds_cid = node.record(manifest("Dataset", "Observed baseline", {"values": [1, 2, 3]}, license="CC0-1.0"))

    claim_doc = _paper_claim(parent_cid=ds_cid)
    jsonschema.validate(claim_doc, orig_schema)
    validate_paper_artifact(claim_doc)

    seed = paper_to_seed(claim_doc)
    assert seed["kind"] == "Claim"
    assert seed["license"] == "CC-BY-4.0"
    assert seed["parents"] == [ds_cid]

    cid = node.record(seed)
    fetched = node.fetch(cid)
    recovered = seed_to_paper(fetched)
    assert recovered == claim_doc
    # Hypothesis remains distinct from ExperimentRun.
    assert fetched["body"]["kind"] == "Claim"
    assert node.status()["jobs"] == 0


@pytest.mark.parametrize("mutation", [
    lambda d: d.pop("license"),
    lambda d: d.update(schemaVersion="9.9"),
    lambda d: d.update(objectType="ArbitraryExecutable"),
    lambda d: d.update(extra_unexpected="bad"),
    lambda d: d.update(verification={"class": "V99"}),
    lambda d: d.update(extensions={"float_not_allowed": 1.25}),
])
def test_malformed_paper_schema_fails(mutation):
    doc = _paper_claim()
    mutation(doc)
    with pytest.raises(ValueError):
        paper_to_seed(doc)


def test_catalog_db_and_search_index_rebuild_after_deletion(tmp_path):
    node = init_node(tmp_path / "rebuild-node")
    ds_cid = node.record(manifest(
        "Dataset", "Cryogenic benchmark",
        {"notes": "superconducting niobium cavity measurements", "values": [4, 5, 6]},
        license="CC0-1.0",
    ))
    claim_cid = node.record(manifest(
        "Claim", "Niobium loss conjecture",
        {"hypothesis": "annealing reduces surface resistance"},
        parents=[ds_cid],
        license="CC-BY-4.0",
    ))
    before_bytes = canonical_bytes(node.fetch(claim_cid)["body"])
    before_sig = node.fetch(claim_cid)["signature"]

    index = CatalogIndex(node)
    report = index.rebuild()
    assert report["indexed_artifacts"] == 2
    assert report["edges"] == 1

    # Full-text search matches across title + body data simultaneously.
    hits = index.search("niobium annealing")
    assert hits["count"] == 1
    assert hits["hits"][0]["cid"] == claim_cid
    assert index.search("superconducting annealing")["count"] == 0  # split across two records
    assert index.search("superconducting")["hits"][0]["cid"] == ds_cid
    assert index.search("annealing", kind="Claim")["hits"][0]["cid"] == claim_cid
    assert index.neighbors(ds_cid)["children"] == [claim_cid]
    assert index.neighbors(claim_cid)["parents"] == [ds_cid]

    # Delete BOTH catalog.sqlite3 and index.sqlite3 completely; rebuild strictly from objects/.
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(node.db) + suffix)
        if p.exists():
            p.unlink()
    index.path.unlink()

    reopened = Node(node.home)
    assert reopened.status()["artifacts"] == 0

    rebuilt_db = reopened.rebuild_from_objects()
    assert rebuilt_db["artifacts"] == 2
    assert rebuilt_db["events"] == 2
    assert reopened.audit()["valid"] is True

    # Signed bytes and signatures are 100% preserved.
    assert canonical_bytes(reopened.fetch(claim_cid)["body"]) == before_bytes
    assert reopened.fetch(claim_cid)["signature"] == before_sig

    rebuilt_idx = CatalogIndex(reopened).rebuild()
    assert rebuilt_idx["indexed_artifacts"] == 2
    assert CatalogIndex(reopened).search("annealing")["hits"][0]["cid"] == claim_cid


def test_failed_index_rebuild_preserves_prior_working_generation(tmp_path):
    node = init_node(tmp_path / "atomic-idx")
    cid = node.record(manifest("Dataset", "Stable asset", {"keyword": "vanadium"}))
    index = CatalogIndex(node)
    index.rebuild()
    assert index.search("vanadium")["count"] == 1

    # Corrupt an immutable object file on disk; rebuild must fail closed and keep old index usable.
    (node.objects_artifacts_dir / cid).write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="CID mismatch"):
        index.rebuild(materialize_missing=False)
    assert index.search("vanadium")["count"] == 1


def test_prov_json_and_rocrate_export_preserve_signed_bytes_and_distinguish_claim_vs_run(tmp_path):
    node = init_node(tmp_path / "export-node")
    ds_cid = node.record(manifest("Dataset", "Inputs", {"values": [10, 20, 30]}, license="CC0-1.0"))
    hyp_cid = node.record(manifest(
        "Claim", "Sum exceeds 50", {"statement": "synthetic hypothesis"}, parents=[ds_cid], license="CC-BY-4.0"
    ))
    job = node.submit_job(ds_cid)
    node.approve_job(job["id"])
    run_cid = node.run_job(job["id"])["output_cid"]

    # Link both hypothesis and observation into a ResearchState via ResearchService.
    svc = ResearchService(node)
    state_cid = svc.record({
        "schema": RESEARCH_SCHEMA,
        "type": "ResearchState",
        "project": "export-demo",
        "title": "Combined state",
        "summary": "Tracks hypothesis and run separately.",
        "contributor": {"kind": "human", "name": "owner", "provider": None, "model": None, "snapshot": None},
        "input_cids": [hyp_cid, run_cid],
        "sources": [],
        "relations": [],
        "content": {
            "objective": "Verify PROV and RO-Crate exports.",
            "finding_cids": [hyp_cid, run_cid],
            "open_question_cids": [],
            "next_actions": ["Audit exported crate."],
            "resume_cids": [ds_cid],
        },
    })["cid"]

    prov = export_prov_json(node, state_cid)
    assert prov["entity"][f"dscc:artifact/{hyp_cid}"]["dscc:epistemicClass"] == "hypothesis"
    assert prov["entity"][f"dscc:artifact/{run_cid}"]["dscc:epistemicClass"] == "execution_observation"
    assert f"dscc:activity/{run_cid}" in prov["activity"]
    assert f"dscc:activity/{hyp_cid}" not in prov["activity"]
    assert f"dscc:signer/{node.public_key}" in prov["agent"]

    crate_dir = tmp_path / "exported-crate"
    summary = export_rocrate_dir(node, state_cid, crate_dir)
    assert summary["artifact_count"] == 4
    verified = verify_rocrate_dir(crate_dir)
    assert verified["valid"] is True
    assert verified["verified_envelopes"] == 4

    # Exported envelope bytes match the signed bytes stored on the node bit-for-bit.
    orig_env = node.export_bundle(state_cid)["artifacts"]
    for row in orig_env:
        exported_bytes = (crate_dir / "envelopes" / f"{row['cid']}.json").read_bytes()
        assert exported_bytes == canonical_bytes(row["envelope"])

    # Tampering with an exported envelope is caught immediately.
    tamper_target = crate_dir / "envelopes" / f"{hyp_cid}.json"
    tamper_target.write_bytes(b'{"tampered":true}')
    with pytest.raises(ValueError, match="sha256 mismatch"):
        verify_rocrate_dir(crate_dir)
