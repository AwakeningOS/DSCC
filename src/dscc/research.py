"""T012: source-linked research profiles and local, explicit-state handoff.

Profiles are wrapped in existing seed artifacts. Attribution and scientific
claims are recorded assertions; signatures authenticate the node key only.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, TYPE_CHECKING

from .canonical import canonical_bytes, cid_for, parse_json, validate_cid
from .models import manifest

if TYPE_CHECKING:
    from .store import Node

SCHEMA = "dscc.research/0.1"
KEY = "research"
KINDS = {
    "ResearchQuestion": "Task",
    "LiteratureReview": "MemoryCapsule",
    "Hypothesis": "Claim",
    "ExperimentPlan": "Workflow",
    "EvaluationRun": "ExperimentRun",
    "FailureReport": "MemoryCapsule",
    "OpenQuestion": "Task",
    "ResearchState": "MemoryCapsule",
    "AgentContribution": "DecisionRecord",
}
# Field roles define the normative content contract and declared CID references.
FIELDS = {
    "ResearchQuestion": {"question": "text", "evaluation_criteria": "texts"},
    "LiteratureReview": {"known_results": "texts", "open_questions": "texts"},
    "Hypothesis": {"statement": "text", "rationale": "text"},
    "ExperimentPlan": {"question_cid": "cid", "procedure": "text", "evaluation_criteria": "texts"},
    "EvaluationRun": {"plan_cid": "cid", "observations": "object", "interpretation": "text"},
    "FailureReport": {"attempted": "text", "observed": "text", "remaining_questions": "texts"},
    "OpenQuestion": {"question": "text"},
    "ResearchState": {"objective": "text", "finding_cids": "cids", "open_question_cids": "cids",
                      "next_actions": "texts", "resume_cids": "cids"},
    "AgentContribution": {"description": "text"},
}
SOURCE_ROLES = {"primary_literature", "observation", "code", "configuration", "data", "context"}
RELATIONS = {"supports", "contradicts", "supersedes", "replicates"}


def _exact(value: Any, keys: set[str], name: str) -> dict:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError(f"{name} fields do not match the research profile")
    return value


def _text(value: Any, name: str, maximum: int = 16384, *, empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > maximum or (not empty and not value.strip()):
        raise ValueError(f"invalid {name}")
    return value


def _strings(value: Any, name: str, *, cids: bool = False) -> list:
    if not isinstance(value, list) or len(value) > 128:
        raise ValueError(f"invalid {name}")
    for item in value:
        validate_cid(item) if cids else _text(item, name)
    if cids and len(set(value)) != len(value):
        raise ValueError(f"duplicate CID in {name}")
    return value


def pointer_tokens(pointer: Any) -> list[str]:
    """RFC 6901 string representation; relative/URI-fragment pointers are rejected."""
    _text(pointer, "JSON Pointer", 4096, empty=True)
    if pointer == "":
        return []
    if not pointer.startswith("/") or re.search(r"~(?![01])", pointer):
        raise ValueError("invalid JSON Pointer")
    return [token.replace("~1", "/").replace("~0", "~") for token in pointer[1:].split("/")]


def resolve_pointer(envelope: Any, pointer: str) -> Any:
    value = envelope
    for token in pointer_tokens(pointer):
        if isinstance(value, dict) and token in value:
            value = value[token]
        elif isinstance(value, list) and re.fullmatch(r"0|[1-9][0-9]*", token):
            # Bound before int conversion (including Python's integer-string limit).
            if len(token) > len(str(len(value))) or int(token) >= len(value):
                raise ValueError("source JSON Pointer does not resolve")
            value = value[int(token)]
        else:
            raise ValueError("source JSON Pointer does not resolve")
    return value


def validate_profile(payload: Any) -> dict:
    p = _exact(payload, {"schema", "type", "project", "title", "summary", "contributor",
                         "input_cids", "sources", "relations", "content"}, "research")
    if p["schema"] != SCHEMA or not isinstance(p["type"], str) or p["type"] not in KINDS:
        raise ValueError("unsupported research schema or type")
    _text(p["project"], "project", 240)
    _text(p["title"], "title", 240)
    _text(p["summary"], "summary", 4096, empty=True)
    actor = _exact(p["contributor"], {"kind", "name", "provider", "model", "snapshot"}, "contributor")
    if not isinstance(actor["kind"], str) or actor["kind"] not in {"human", "agent", "unknown"}:
        raise ValueError("invalid contributor kind")
    _text(actor["name"], "contributor name", 240)
    for field in ("provider", "model", "snapshot"):
        if actor[field] is not None:
            _text(actor[field], field, 512)
    _strings(p["input_cids"], "input_cids", cids=True)
    if not isinstance(p["sources"], list) or len(p["sources"]) > 128:
        raise ValueError("invalid sources")
    for source in p["sources"]:
        _exact(source, {"cid", "pointer", "role"}, "source")
        validate_cid(source["cid"])
        pointer_tokens(source["pointer"])
        if not isinstance(source["role"], str) or source["role"] not in SOURCE_ROLES:
            raise ValueError("invalid source role")
    if not isinstance(p["relations"], list) or len(p["relations"]) > 128:
        raise ValueError("invalid relations")
    for relation in p["relations"]:
        _exact(relation, {"type", "target_cid", "rationale"}, "relation")
        if not isinstance(relation["type"], str) or relation["type"] not in RELATIONS:
            raise ValueError("unsupported research relation")
        validate_cid(relation["target_cid"])
        _text(relation["rationale"], "relation rationale")
    content = p["content"]
    fields = FIELDS[p["type"]]
    if (not isinstance(content, dict) or not set(fields) <= set(content)
            or set(content) - set(fields) - {"extensions"}):
        raise ValueError("content fields do not match the research type")
    for field, role in fields.items():
        value = content[field]
        if role == "text":
            _text(value, field)
        elif role == "texts":
            _strings(value, field)
        elif role == "cid":
            validate_cid(value)
        elif role == "cids":
            _strings(value, field, cids=True)
        elif not isinstance(value, dict):
            raise ValueError(f"{field} must be an object")
    if "extensions" in content and not isinstance(content["extensions"], dict):
        raise ValueError("extensions must be an object")
    roles = {s["role"] for s in p["sources"]}
    if p["type"] == "LiteratureReview" and content["known_results"] and "primary_literature" not in roles:
        raise ValueError("known literature results require a primary_literature source")
    if p["type"] in {"EvaluationRun", "FailureReport"} and "observation" not in roles:
        raise ValueError("reported results require an observation source")
    if "evaluation_criteria" in content and not content["evaluation_criteria"]:
        raise ValueError("evaluation_criteria must not be empty")
    canonical_bytes(p)
    return p


def parent_cids(payload: dict) -> list[str]:
    p = validate_profile(payload)
    refs = list(p["input_cids"])
    refs.extend(s["cid"] for s in p["sources"])
    refs.extend(r["target_cid"] for r in p["relations"])
    for field, role in FIELDS[p["type"]].items():
        if role == "cid":
            refs.append(p["content"][field])
        elif role == "cids":
            refs.extend(p["content"][field])
    result = sorted(set(refs))
    if len(result) > 32:
        raise ValueError("research references exceed the seed parent limit of 32; link intermediate records")
    return result


def research_artifact(payload: dict, *, license: str = "NOASSERTION") -> dict:
    p = validate_profile(payload)
    return manifest(KINDS[p["type"]], p["title"], {KEY: p}, summary=p["summary"],
                    parents=parent_cids(p), license=license)


def _profile_from(envelope: dict) -> dict:
    body = envelope["body"]
    if set(body["data"]) != {KEY}:
        raise ValueError("artifact is not a research profile")
    p = validate_profile(body["data"][KEY])
    if (body["kind"] != KINDS[p["type"]] or body["title"] != p["title"]
            or body["summary"] != p["summary"] or body["parents"] != parent_cids(p)):
        raise ValueError("research envelope does not match declared profile and references")
    return p


def _check_links(p: dict, envelopes: dict[str, dict]) -> None:
    for source in p["sources"]:
        resolve_pointer(envelopes[source["cid"]], source["pointer"])
    expectations = []
    if p["type"] == "ExperimentPlan":
        expectations.append((p["content"]["question_cid"], {"ResearchQuestion", "OpenQuestion"}))
    elif p["type"] == "EvaluationRun":
        expectations.append((p["content"]["plan_cid"], {"ExperimentPlan"}))
    elif p["type"] == "ResearchState":
        expectations.extend((cid, {"ResearchQuestion", "OpenQuestion"})
                            for cid in p["content"]["open_question_cids"])
    for cid, types in expectations:
        target = _profile_from(envelopes[cid])
        if target["type"] not in types:
            raise ValueError("research reference has an incompatible type")
    for relation in p["relations"]:
        if relation["type"] == "supersedes":
            target = _profile_from(envelopes[relation["target_cid"]])
            if (target["type"], target["project"]) != (p["type"], p["project"]):
                raise ValueError("supersedes requires the same research type and project")


def work_fingerprint(payload: dict) -> str:
    """Exact declared-work match only, not semantic duplicate detection."""
    p = validate_profile(payload)
    return cid_for(canonical_bytes({k: p[k] for k in
                                   ("schema", "type", "project", "input_cids", "sources", "content")}))


class ResearchService:
    def __init__(self, node: Node):
        self.node = node

    def record(self, payload: dict, *, license: str = "NOASSERTION") -> dict:
        # Copy canonical input so a caller cannot mutate it between checks/signing.
        p = validate_profile(parse_json(canonical_bytes(payload)))
        doc = research_artifact(p, license=license)
        envelopes = {}
        for parent in doc["parents"]:
            fetched = self.node.fetch(parent)
            # Pointers address signed envelopes, never fetch-only metadata.
            envelopes[parent] = {key: fetched[key] for key in ("body", "public_key", "signature")}
        _check_links(p, envelopes)
        cid = self.node.record(doc)
        return {"cid": cid, "type": p["type"], "scope": "local_only",
                "work_fingerprint": work_fingerprint(p), "execution_authorized": False}

    def handoff(self, state_cid: str) -> dict:
        """Read an explicit state and its complete verified ancestor closure.

        Uses the existing bounded export traversal, but neither writes a bundle
        file nor publishes data. A new participant imports through the owner CLI.
        No wall-clock ordering or automatic promotion of claims is performed.
        """
        bundle = self.node.export_bundle(state_cid)
        envelopes = {row["cid"]: row["envelope"] for row in bundle["artifacts"]}
        state = _profile_from(envelopes[state_cid])
        if state["type"] != "ResearchState":
            raise ValueError("handoff root must be a ResearchState")
        records, relations = [], []
        groups: dict[str, list[str]] = defaultdict(list)
        for cid, envelope in sorted(envelopes.items()):
            if KEY not in envelope["body"]["data"]:
                continue
            p = _profile_from(envelope)
            _check_links(p, envelopes)
            fingerprint = work_fingerprint(p)
            groups[fingerprint].append(cid)
            records.append({"cid": cid, "type": p["type"], "project": p["project"],
                            "contributor": p["contributor"], "work_fingerprint": fingerprint})
            relations.extend({"asserted_by_cid": cid, **r} for r in p["relations"])
        return {
            "schema": "dscc.research.handoff/0.1", "state_cid": state_cid,
            "project": state["project"], "state": state, "records": records,
            "artifacts": bundle["artifacts"], "relations": relations,
            "contradictions": [r for r in relations if r["type"] == "contradicts"],
            "supersession_assertions": [r for r in relations if r["type"] == "supersedes"],
            "repeated_work_candidates": [{"work_fingerprint": key, "cids": cids}
                                         for key, cids in sorted(groups.items()) if len(cids) > 1],
            "complete_ancestor_closure": True, "large_blocks_included": False,
            "content_trust": "untrusted_research_data", "scientific_correctness": "not_assessed",
            "execution_authorized": False, "published": False,
        }
