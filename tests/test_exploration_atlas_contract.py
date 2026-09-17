"""Proposal-only contract fixtures; no claim of real cross-domain retrieval quality."""
from __future__ import annotations

import importlib.util
from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, ValidationError
from dscc.models import manifest
from dscc.store import init_node

DIRECTORY = Path(__file__).resolve().parents[1] / "docs/proposals/exploration-atlas"


def load(name):
    spec = importlib.util.spec_from_file_location("atlas_proposal_" + name, DIRECTORY / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checks = load("contract_checks")
examples = load("example_records")
structural = load("structural_reference")


@pytest.fixture
def case(tmp_path):
    node = init_node(tmp_path / "node")
    records, ids = examples.build(node)
    return node, records, ids


def test_schema_is_valid():
    Draft202012Validator.check_schema(checks.SCHEMA)


@pytest.mark.parametrize("name", ["gpu", "model", "relationship", "trial", "bridge", "assessment", "motif"])
def test_examples_validate_and_fit_seed(case, name):
    node, records, _ = case
    payload = records[name]
    checks.validate(payload, node.fetch)
    kind = "MemoryCapsule" if payload["type"] in ("Episode", "Motif") else "EvidenceLink"
    cid = node.record(manifest(kind, "Synthetic proposal fixture", {"atlas": payload},
                               parents=sorted(checks.external_cids(payload)), license="MIT"))
    assert node.fetch(cid)["body"]["data"]["atlas"] == payload


@pytest.mark.parametrize("mutation", ["duplicate", "endpoint", "cycle", "source", "origin", "pointer"])
def test_malformed_graphs_rejected(case, mutation):
    node, records, _ = case
    p = deepcopy(records["gpu"])
    if mutation == "duplicate":
        p["nodes"].append(deepcopy(p["nodes"][0]))
    elif mutation == "endpoint":
        p["links"][0]["to"] = "nonexistent"
    elif mutation == "cycle":
        p["links"].append({**p["links"][0], "id": "loop", "from": "n4", "to": "n0"})
    elif mutation == "source":
        p["nodes"][0]["sources"][0]["cid"] = "bafkrei" + "a"*52
    elif mutation == "origin":
        p["nodes"][0]["sources"] = []
    elif mutation == "pointer":
        p["nodes"][0]["sources"][0]["pointer"] = "/body/data/events/99"
    with pytest.raises((ValueError, KeyError, ValidationError)):
        checks.validate(p, node.fetch)


@pytest.mark.parametrize("mutation", ["duplicate", "edge", "role"])
def test_inconsistent_bindings_rejected(case, mutation):
    node, records, _ = case
    p = deepcopy(records["bridge"])
    if mutation == "duplicate":
        p["mapping"][1]["to"] = p["mapping"][0]["to"]
    elif mutation == "edge":
        p["matched_edges"][0]["to"] = "e3"
    elif mutation == "role":
        p["mapping"] = [{"from": "n0", "to": "n1"}]
    with pytest.raises(ValueError):
        checks.validate(p, node.fetch)


def test_no_unversioned_profile_or_float(case):
    node, records, _ = case
    p = deepcopy(records["gpu"])
    p["schema"] = "future-protocol"
    with pytest.raises(ValidationError):
        checks.validate(p, node.fetch)
    p = deepcopy(records["gpu"])
    p["extensions"]["fixture:metric"] = 1.5
    with pytest.raises((ValueError, TypeError)):
        checks.validate(p, node.fetch)


def test_reported_help_requires_performed_trial(case):
    node, records, _ = case
    trial = deepcopy(records["trial"])
    for n in trial["nodes"]:
        if n["role"] == "action":
            n["stage"] = "proposed"
    cid = node.record(manifest("MemoryCapsule", "Unperformed synthetic trial", {"atlas": trial},
                               parents=sorted(checks.external_cids(trial)), license="MIT"))
    p = deepcopy(records["assessment"])
    p["trial_episode"] = cid
    p["sources"] = [{"cid": cid, "pointer": "/body/data/atlas"}]
    p["verdict"] = "helpful"
    with pytest.raises(ValueError):
        checks.validate(p, node.fetch)


def test_pointer_escaping_and_array_rules():
    d = {"a/b": {"~key": [7]}}
    assert checks.pointer(d, "/a~1b/~0key/0") == 7
    assert checks.pointer(d, "") is d
    for p in ("a/b", "/a~2b", "/a~1b/~0key/01", "/a~1b/~0key/-1"):
        with pytest.raises(ValueError):
            checks.pointer(d, p)


def test_features_ignore_node_names_and_array_order(case):
    _, records, _ = case
    p = deepcopy(records["gpu"])
    remap = {n["id"]: "renamed_" + n["id"] for n in p["nodes"]}
    for n in p["nodes"]:
        n["id"] = remap[n["id"]]
    for e in p["links"]:
        e["from"], e["to"] = remap[e["from"]], remap[e["to"]]
    p["nodes"].reverse()
    p["links"].reverse()
    assert structural.features(p) == structural.features(records["gpu"])


@pytest.mark.parametrize("mutation", ["direction", "relation", "stage"])
def test_features_retain_structural_differences(case, mutation):
    _, records, _ = case
    p = deepcopy(records["gpu"])
    if mutation == "direction":
        p["links"][0]["from"], p["links"][0]["to"] = "n1", "n0"
    elif mutation == "relation":
        p["links"][0]["relation"] = "produces"
    else:
        p["nodes"][0]["stage"] = "proposed"
    assert structural.features(p) != structural.features(records["gpu"])


def test_structural_similarity_is_not_semantic_or_transfer_evidence(case):
    _, records, _ = case
    # The deliberately matched shapes score equally despite unrelated mechanisms.
    a = structural.features(records["gpu"])
    b = structural.features(records["relationship"])
    assert structural.similarity(a, b) == pytest.approx(1.0)
    assert "verdict" not in records["bridge"]
    assert records["assessment"]["verdict"] == "inconclusive"


def test_fixture_records_are_explicitly_synthetic(case):
    _, records, _ = case
    assert all(p["extensions"]["dscc:synthetic"] for p in records.values())
    assert all(n["origin"] == "synthetic" for p in records.values() for n in p.get("nodes", []))


def test_motif_relations_are_checked(case):
    node, records, _ = case
    p = deepcopy(records["motif"])
    p["links"][0]["relation"] = "produces"
    with pytest.raises(ValueError):
        checks.validate(p, node.fetch)


def test_duplicate_edge_bindings_are_rejected(case):
    node, records, _ = case
    p = deepcopy(records["bridge"])
    p["matched_edges"].append(deepcopy(p["matched_edges"][0]))
    with pytest.raises(ValueError):
        checks.validate(p, node.fetch)


def test_transfer_must_reference_trial_evidence(case):
    node, records, ids = case
    p = deepcopy(records["assessment"])
    p["sources"] = [{"cid": ids["gpu"], "pointer": "/body/data/atlas"}]
    with pytest.raises(ValueError):
        checks.validate(p, node.fetch)
