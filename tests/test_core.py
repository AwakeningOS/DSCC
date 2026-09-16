from __future__ import annotations

import copy
from concurrent.futures import ThreadPoolExecutor

import pytest

from dscc.canonical import canonical_bytes, cid_for, parse_json, validate_cid
from dscc.identity import verify
from dscc.models import manifest
from dscc.store import Node, init_node
from dscc.tools import TOOL_ID


@pytest.fixture
def node(tmp_path):
    return init_node(tmp_path / "node")


def data(node, title="sample"):
    return node.record(manifest("Dataset", title, {"values": [3, 4, 9]}))


def test_canonical_key_order_and_known_cid():
    assert canonical_bytes({"b": 2, "a": 1}) == b'{"a":1,"b":2}'
    assert cid_for(b"") == "bafkreihdwdcefgh4dqkjv67uzcmw7ojee6xedzdetojuzjevtenxquvyku"
    assert validate_cid(cid_for(b"test")) == cid_for(b"test")


def test_utf16_key_order():
    assert canonical_bytes({"\ue000": 1, "\U00010000": 2}).decode() == '{"\U00010000":2,"\ue000":1}'


@pytest.mark.parametrize("value", [1.2, float("nan"), float("inf"), 2**53, -(2**53),
                                    {1: "bad"}, {"x": "e\u0301"}, "\ud800", (1, 2)])
def test_reject_nonportable_metadata(value):
    with pytest.raises(ValueError):
        canonical_bytes(value)


def test_depth_bound():
    value = 0
    for _ in range(40):
        value = [value]
    with pytest.raises(ValueError):
        canonical_bytes(value)


@pytest.mark.parametrize("raw", [b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff', b'{broken'])
def test_strict_json(raw):
    with pytest.raises(ValueError):
        parse_json(raw)


def test_byte_limit():
    with pytest.raises(ValueError):
        parse_json(b'"abcd"', max_bytes=3)


@pytest.mark.parametrize("cid", ["../signing.key", "http://localhost/", "Qm123", "", "b" + "a"*58, None])
def test_bad_cids(cid):
    with pytest.raises(ValueError):
        validate_cid(cid)


def test_record_is_idempotent_and_survives_reopen(node):
    doc = manifest("MemoryCapsule", "materials notes", {"observation": "Keep the failed condition."})
    cid = node.record(doc)
    assert node.record(doc) == cid
    other = Node(node.home)
    assert other.fetch(cid)["body"] == doc
    assert other.search("materials")[0]["cid"] == cid
    assert other.status()["artifacts"] == 1
    assert other.audit()["events"] == 1


def test_parent_lineage(node):
    first = data(node)
    second = node.record(manifest("Claim", "result", {"claim": "test only"}, parents=[first]))
    assert node.fetch(second)["body"]["parents"] == [first]
    assert node.verify_artifact(second)["scientific_correctness"] == "not_assessed"


def test_missing_parent_rejected_atomically(node):
    with pytest.raises(KeyError):
        node.record(manifest("Claim", "missing", {}, parents=[cid_for(b"absent")]))
    assert node.status()["artifacts"] == 0
    assert node.audit()["events"] == 0


def test_duplicate_parent_rejected(node):
    cid = data(node)
    with pytest.raises(ValueError):
        node.record(manifest("Claim", "duplicate", {}, parents=[cid, cid]))


def test_unknown_fields_rejected(node):
    doc = manifest("Claim", "x", {})
    doc["shell"] = "echo fail"
    with pytest.raises(ValueError):
        node.record(doc)


def test_corrupt_artifact_detected(node):
    cid = data(node)
    with node._transaction() as c:
        c.execute("UPDATE artifacts SET envelope=? WHERE cid=?", (b"{}", cid))
    with pytest.raises(ValueError, match="CID mismatch"):
        node.fetch(cid)


def test_signature_cannot_be_reused_for_changed_body(node):
    cid = data(node)
    env = node.export_bundle(cid)["artifacts"][0]["envelope"]
    env["body"]["title"] = "Changed"
    with pytest.raises(ValueError, match="signature"):
        verify(env, "artifact")


def test_signature_domain_separation(node):
    cid = data(node)
    env = node.export_bundle(cid)["artifacts"][0]["envelope"]
    with pytest.raises(ValueError, match="signature"):
        verify(env, "event")


def test_bundle_trust_and_lineage(node, tmp_path):
    first = data(node)
    second = node.record(manifest("MemoryCapsule", "handoff", {}, parents=[first]))
    target = init_node(tmp_path / "target")
    bundle = node.export_bundle(second)
    with pytest.raises(ValueError, match="untrusted"):
        target.import_bundle(bundle, set())
    assert target.status()["artifacts"] == 0
    assert target.import_bundle(bundle, {node.public_key}) == second
    assert target.fetch(second)["body"]["parents"] == [first]
    assert target.fetch(first)["public_key"] == node.public_key
    assert target.import_bundle(bundle, {node.public_key}) == second
    assert target.status()["artifacts"] == 2


def test_bundle_tamper_rejected_before_writes(node, tmp_path):
    cid = data(node)
    bundle = node.export_bundle(cid)
    bundle["artifacts"][0]["envelope"]["body"]["data"]["values"] = [99]
    target = init_node(tmp_path / "target")
    with pytest.raises(ValueError):
        target.import_bundle(bundle, {node.public_key})
    assert target.status()["artifacts"] == 0


def test_bundle_unrelated_payload_rejected(node, tmp_path):
    cid = data(node)
    other = data(node, "unrelated")
    bundle = node.export_bundle(cid)
    bundle["artifacts"] += node.export_bundle(other)["artifacts"]
    target = init_node(tmp_path / "target")
    with pytest.raises(ValueError, match="unrelated"):
        target.import_bundle(bundle, {node.public_key})
    assert target.status()["artifacts"] == 0


def test_bundle_missing_dependency(node, tmp_path):
    cid = data(node)
    child = node.record(manifest("Claim", "child", {}, parents=[cid]))
    bundle = node.export_bundle(child)
    bundle["artifacts"] = [x for x in bundle["artifacts"] if x["cid"] == child]
    with pytest.raises(ValueError, match="closure"):
        init_node(tmp_path / "target").import_bundle(bundle, {node.public_key})


def test_bundle_duplicate_rejected(node, tmp_path):
    cid = data(node)
    bundle = node.export_bundle(cid)
    bundle["artifacts"] *= 2
    with pytest.raises(ValueError, match="duplicate"):
        init_node(tmp_path / "target").import_bundle(bundle, {node.public_key})


def test_quota_rolls_back_artifact_and_event(tmp_path):
    n = init_node(tmp_path / "small", quota_mb=1)
    n.record(manifest("MemoryCapsule", "large", {"text": "x"*800_000}))
    before = n.status()
    head = n.audit()["head"]
    with pytest.raises(ValueError, match="quota"):
        n.record(manifest("MemoryCapsule", "too large", {"text": "y"*300_000}))
    assert n.status() == before
    assert n.audit()["head"] == head


def test_concurrent_writers_preserve_event_chain(node):
    def write(i):
        return node.record(manifest("Claim", f"concurrent {i}", {"index": i}))
    with ThreadPoolExecutor(max_workers=6) as pool:
        ids = list(pool.map(write, range(30)))
    assert len(set(ids)) == 30
    assert node.status()["artifacts"] == 30
    assert node.audit()["events"] == 30


def test_audit_tamper_detected(node):
    data(node)
    with node._transaction() as c:
        c.execute("UPDATE events SET envelope=? WHERE seq=1", (b"{}",))
    with pytest.raises(ValueError):
        node.audit()


def test_job_requires_approval_then_persists_result(node):
    cid = data(node)
    j = node.submit_job(cid)
    assert j["state"] == "pending"
    with pytest.raises(ValueError):
        node.run_job(j["id"])
    node.approve_job(j["id"])
    complete = node.run_job(j["id"])
    assert complete["state"] == "succeeded"
    out = node.fetch(complete["output_cid"])["body"]
    assert out["data"]["result"] == {"count": 3, "sum": 16, "min": 3, "max": 9}
    assert out["parents"] == [cid]
    assert out["data"]["independent_scientific_verification"] is False
    with pytest.raises(ValueError):
        node.run_job(j["id"])
    assert node.audit()["valid"]


def test_cancel_and_recover(node):
    cid = data(node)
    j = node.submit_job(cid)
    assert node.cancel_job(j["id"])["state"] == "cancelled"
    with pytest.raises(ValueError):
        node.approve_job(j["id"])
    k = node.submit_job(cid)
    node.approve_job(k["id"])
    node._transition(k["id"], ("approved",), "running")
    assert node.recover_job(k["id"])["state"] == "failed"


@pytest.mark.parametrize("values", [[], [True], [1.0], [10**10], ["4"], list(range(10001))],
                         ids=["empty", "bool", "float", "out-of-range", "string", "oversized"])
def test_tool_input_admission(node, values):
    if len(values) == 1 and type(values[0]) is float:
        with pytest.raises(ValueError):
            manifest("Dataset", "bad", {"values": values})
        return
    cid = node.record(manifest("Dataset", "bad", {"values": values}))
    with pytest.raises(ValueError):
        node.submit_job(cid)


def test_unknown_tool_cannot_execute(node):
    with pytest.raises(ValueError, match="allowlist"):
        node.submit_job(data(node), "shell")


def test_job_spec_tampering_detected(node):
    j = node.submit_job(data(node))
    with node._transaction() as c:
        c.execute("UPDATE jobs SET spec=? WHERE id=?", (b"{}", j["id"]))
    with pytest.raises(ValueError, match="integrity"):
        node.approve_job(j["id"])


def test_sql_search_is_literal(node):
    data(node, "materials 100%")
    data(node, "different")
    assert len(node.search("%")) == 1
    assert node.search("' OR 1=1 --") == []


def test_identity_is_not_replaced_on_reinit(node):
    assert init_node(node.home).public_key == node.public_key


def test_incomplete_node_is_not_reinitialized(tmp_path):
    home = tmp_path / "broken"; home.mkdir()
    (home / "signing.key").write_bytes(b"x"*32)
    with pytest.raises(ValueError, match="incomplete"):
        init_node(home)


def test_full_length_input_title_can_produce_output(node):
    cid = data(node, "x" * 240)
    job = node.submit_job(cid)
    node.approve_job(job["id"])
    result = node.run_job(job["id"])
    assert result["state"] == "succeeded"
    assert len(node.fetch(result["output_cid"])["body"]["title"]) == 240
