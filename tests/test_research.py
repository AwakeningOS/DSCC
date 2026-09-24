"""T012 contract/integration tests; all agent and research examples are synthetic."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dscc.canonical import canonical_bytes, cid_for
from dscc.mcp_server import MCPServer
from dscc.models import manifest
from dscc.research import (
    FIELDS, KINDS, SCHEMA, ResearchService, parent_cids, research_artifact,
    resolve_pointer, validate_profile,
)
from dscc.store import Node, init_node

ROOT = Path(__file__).resolve().parents[1]


def profile(kind, content, *, inputs=None, sources=None, relations=None, name="synthetic-agent-A"):
    return {
        "schema": SCHEMA, "type": kind, "project": "synthetic-handoff-test",
        "title": kind, "summary": "Synthetic contract fixture; no real model was called.",
        "contributor": {"kind": "agent", "name": name, "provider": None,
                        "model": None, "snapshot": None},
        "input_cids": inputs or [], "sources": sources or [], "relations": relations or [],
        "content": content,
    }


def question():
    return profile("ResearchQuestion", {"question": "Can the synthetic task be resumed?",
                                        "evaluation_criteria": ["All original inputs are available."]})


def state(*, findings=None, questions=None, resume=None, inputs=None, relations=None):
    return profile("ResearchState", {"objective": "Continue the synthetic research task.",
                                    "finding_cids": findings or [],
                                    "open_question_cids": questions or [],
                                    "next_actions": ["Review the original evidence before the next trial."],
                                    "resume_cids": resume or []}, inputs=inputs, relations=relations)


def source(cid, role="observation", pointer="/body/data/value"):
    return {"cid": cid, "pointer": pointer, "role": role}


@pytest.fixture
def node(tmp_path):
    return init_node(tmp_path / "node")


def test_cross_node_reopen_and_research_continuity(tmp_path):
    a, b, c = [init_node(tmp_path / name) for name in ("a", "b", "c")]
    sa = ResearchService(a)
    raw = a.record(manifest("Dataset", "Synthetic primary-source fixture", {
        "value": "Fixture known result, not an actual literature claim.", "url": "https://example.org/fixture"}))
    raw_bytes = canonical_bytes(a.fetch(raw)["body"])
    q = sa.record(question())["cid"]
    review = sa.record(profile("LiteratureReview", {
        "known_results": ["The fixture states a known result."], "open_questions": ["Does it transfer?"]
    }, sources=[source(raw, "primary_literature")]))["cid"]
    hypothesis = sa.record(profile("Hypothesis", {
        "statement": "The fixture may transfer.", "rationale": "A test is still required."
    }, inputs=[review]))["cid"]
    initial = sa.record(state(findings=[review, hypothesis], questions=[q], resume=[raw]))["cid"]
    b.import_bundle(a.export_bundle(initial), {a.public_key})
    sb = ResearchService(Node(b.home))
    plan = sb.record(profile("ExperimentPlan", {
        "question_cid": q, "procedure": "Execute the synthetic check.",
        "evaluation_criteria": ["Record the synthetic observation."]
    }, inputs=[initial], name="synthetic-agent-B"))["cid"]
    observed = b.record(manifest("Dataset", "Synthetic trial log", {"value": {"passed": False}}))
    evaluation = sb.record(profile("EvaluationRun", {
        "plan_cid": plan, "observations": {"passed": False}, "interpretation": "The synthetic trial failed."
    }, sources=[source(observed)], relations=[{
        "type": "contradicts", "target_cid": hypothesis, "rationale": "Fixture counter-observation."
    }], name="synthetic-agent-B"))["cid"]
    failure = sb.record(profile("FailureReport", {
        "attempted": "Synthetic transfer", "observed": "The fixture failed.",
        "remaining_questions": ["Which assumption was wrong?"]
    }, inputs=[evaluation], sources=[source(observed)]))["cid"]
    open_q = sb.record(profile("OpenQuestion", {"question": "Which assumption should be revised?"},
                               inputs=[failure]))["cid"]
    final = sb.record(state(findings=[review, hypothesis, evaluation, failure], questions=[open_q],
                            resume=[plan, observed], inputs=[initial], relations=[{
        "type": "supersedes", "target_cid": initial, "rationale": "New synthetic trial is recorded."
    }]))["cid"]
    c.import_bundle(b.export_bundle(final), {a.public_key, b.public_key})
    output = ResearchService(Node(c.home)).handoff(final)
    assert output["state_cid"] == final
    assert output["complete_ancestor_closure"] is True
    assert output["scientific_correctness"] == "not_assessed"
    assert output["execution_authorized"] is False and output["published"] is False
    assert output["large_blocks_included"] is False
    assert output["contradictions"][0]["target_cid"] == hypothesis
    assert output["supersession_assertions"][0]["target_cid"] == initial
    types = {row["cid"]: row["type"] for row in output["records"]}
    assert types[hypothesis] == "Hypothesis" and types[evaluation] == "EvaluationRun"
    assert types[initial] == "ResearchState"
    assert canonical_bytes(c.fetch(raw)["body"]) == raw_bytes
    assert c.fetch(raw)["signature"] == a.fetch(raw)["signature"]
    assert c.audit()["valid"]


@pytest.mark.parametrize("kind", list(KINDS))
def test_all_profile_types_validate_and_keep_seed_kinds(kind):
    cid = cid_for(b"fixture")
    content = {field: {"text": "Fixture", "texts": ["Fixture"], "cid": cid,
                       "cids": [cid], "object": {"value": "0.5"}}[role]
               for field, role in FIELDS[kind].items()}
    p = profile(kind, content, sources=[source(cid), source(cid, "primary_literature")])
    doc = research_artifact(p)
    assert doc["kind"] == KINDS[kind]
    assert doc["data"]["research"] == p
    assert doc["parents"] == [cid]


@pytest.mark.parametrize("pointer,expected", [("", {"a/b": {"~": [3]}}), ("/a~1b/~0/0", 3)])
def test_json_pointer_escaping(pointer, expected):
    assert resolve_pointer({"a/b": {"~": [3]}}, pointer) == expected


@pytest.mark.parametrize("pointer", ["#fragment", "a", "/~", "/~2", "/values/-", "/values/01",
                                     "/values/1", "/values/" + "9" * 1000, "/absent"])
def test_bad_pointers_are_rejected(pointer):
    with pytest.raises(ValueError):
        resolve_pointer({"values": [1]}, pointer)


@pytest.mark.parametrize("mutation", [
    lambda p: p.update(schema="unknown/1"),
    lambda p: p.update(type=[]),
    lambda p: p.update(project=" "),
    lambda p: p.update(secret="not a supported field"),
    lambda p: p["content"].update(unexpected=True),
    lambda p: p["content"].update(evaluation_criteria=[]),
    lambda p: p["contributor"].update(kind=[]),
    lambda p: p["contributor"].update(model=42),
    lambda p: p.update(input_cids=["not-a-cid"]),
    lambda p: p["content"].update(extensions={"measurement": 0.5}),
])
def test_profile_rejects_invalid_inputs(mutation):
    p = question()
    mutation(p)
    with pytest.raises(ValueError):
        validate_profile(p)


def test_unknown_metadata_remains_explicit_and_extensions_are_preserved(node):
    p = question()
    p["contributor"].update(kind="unknown", name="unidentified contributor")
    p["content"]["extensions"] = {"example.org/domain": {"raw": "keep this", "metric": "0.5"}}
    original = copy.deepcopy(p)
    cid = ResearchService(node).record(p)["cid"]
    assert p == original
    assert node.fetch(cid)["body"]["data"]["research"] == p


@pytest.mark.parametrize("kind,content", [
    ("LiteratureReview", {"known_results": ["Known"], "open_questions": []}),
    ("EvaluationRun", {"plan_cid": cid_for(b"plan"), "observations": {}, "interpretation": "Test"}),
    ("FailureReport", {"attempted": "Test", "observed": "Failed", "remaining_questions": []}),
])
def test_evidence_is_required(kind, content):
    with pytest.raises(ValueError):
        validate_profile(profile(kind, content))


def test_missing_reference_and_bad_pointer_do_not_write(node):
    svc = ResearchService(node)
    before = node.status()["artifacts"]
    with pytest.raises(KeyError):
        svc.record(profile("AgentContribution", {"description": "Missing input"},
                           inputs=[cid_for(b"missing")]))
    assert node.status()["artifacts"] == before
    raw = node.record(manifest("Dataset", "Fixture", {"value": 1}))
    with pytest.raises(ValueError, match="does not resolve"):
        svc.record(profile("AgentContribution", {"description": "Bad pointer"},
                           sources=[source(raw, pointer="/body/data/absent")]))
    assert node.status()["artifacts"] == before + 1


def test_wrong_typed_references_and_supersession_are_rejected(node):
    svc = ResearchService(node)
    h = svc.record(profile("Hypothesis", {"statement": "Maybe", "rationale": "Unknown"}))["cid"]
    with pytest.raises(ValueError, match="incompatible type"):
        svc.record(state(questions=[h]))
    with pytest.raises(ValueError, match="same research type and project"):
        svc.record(state(relations=[{"type": "supersedes", "target_cid": h, "rationale": "Wrong type"}]))
    initial = svc.record(state())["cid"]
    other = state(relations=[{"type": "supersedes", "target_cid": initial, "rationale": "Wrong project"}])
    other["project"] = "other-project"
    with pytest.raises(ValueError, match="same research type and project"):
        svc.record(other)
    with pytest.raises(ValueError, match="root must be"):
        svc.handoff(h)


def test_all_declared_references_become_parents():
    a, b, c, d = [cid_for(x.encode()) for x in "abcd"]
    p = state(findings=[a], questions=[b], resume=[c], inputs=[a], relations=[{
        "type": "supports", "target_cid": d, "rationale": "Fixture"
    }])
    p["sources"] = [source(c)]
    assert parent_cids(p) == sorted([a, b, c, d])
    p["input_cids"] = [cid_for(str(i).encode()) for i in range(33)]
    with pytest.raises(ValueError, match="parent limit"):
        parent_cids(p)


def test_repeated_work_candidates_and_unrelated_records(node):
    svc = ResearchService(node)
    content = {"statement": "Same exact declared work", "rationale": "Fixture"}
    a = svc.record(profile("Hypothesis", content))["cid"]
    b = svc.record(profile("Hypothesis", content, name="synthetic-agent-B"))["cid"]
    unrelated = svc.record(question())["cid"]
    root = svc.record(state(findings=[a, b]))["cid"]
    report = svc.handoff(root)
    assert report["repeated_work_candidates"][0]["cids"] == sorted([a, b])
    assert unrelated not in {row["cid"] for row in report["artifacts"]}
    assert report == svc.handoff(root)


@pytest.mark.parametrize("corruption", ["parents", "kind", "pointer"])
def test_generic_record_cannot_bypass_handoff_validation(node, corruption):
    raw = node.record(manifest("Dataset", "Fixture", {"value": 1}))
    p = profile("AgentContribution", {"description": "Fixture"}, sources=[source(raw)])
    if corruption == "pointer":
        p["sources"][0]["pointer"] = "/body/data/missing"
    doc = research_artifact(p)
    if corruption == "parents":
        doc["parents"] = []
    elif corruption == "kind":
        doc["kind"] = "Dataset"
    malformed = node.record(doc)
    root = ResearchService(node).record(state(findings=[malformed]))["cid"]
    with pytest.raises(ValueError):
        ResearchService(node).handoff(root)


def test_source_tampering_is_detected(node):
    raw = node.record(manifest("Dataset", "Fixture", {"value": 1}))
    svc = ResearchService(node)
    root = svc.record(state(resume=[raw]))["cid"]
    with node._connection() as c:
        c.execute("UPDATE artifacts SET envelope=? WHERE cid=?", (b"{}", raw))
    with pytest.raises(ValueError, match="CID mismatch"):
        svc.handoff(root)


def test_mcp_research_tools_preserve_owner_boundaries(node):
    server = MCPServer(node)
    for message in [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "fixture", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
    ]:
        server.dispatch(message)
    def call(name, arguments):
        return server.dispatch({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
                                "params": {"name": name, "arguments": arguments}})
    result = call("record_research", {"payload": state()})["result"]
    assert result["isError"] is False
    cid = json.loads(result["content"][0]["text"])["cid"]
    output = call("get_research_handoff", {"state_cid": cid})["result"]
    assert json.loads(output["content"][0]["text"])["execution_authorized"] is False
    assert call("record_research", {"payload": state(), "approve": True})["result"]["isError"] is True
    assert call("run_job", {"job_id": "not authorized"})["error"]["code"] == -32602
    assert node.status()["jobs"] == 0


def test_cli_research_record_and_handoff(node, tmp_path):
    path = tmp_path / "state.json"
    path.write_text(json.dumps(state()), encoding="utf-8")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    command = [sys.executable, "-m", "dscc", "--home", str(node.home)]
    result = subprocess.run(command + ["research-record", "--file", str(path)],
                            capture_output=True, text=True, env=env, timeout=20)
    assert result.returncode == 0, result.stderr
    cid = json.loads(result.stdout)["cid"]
    resumed = subprocess.run(command + ["research-handoff", cid], capture_output=True,
                             text=True, env=env, timeout=20)
    assert resumed.returncode == 0, resumed.stderr
    assert json.loads(resumed.stdout)["state_cid"] == cid
