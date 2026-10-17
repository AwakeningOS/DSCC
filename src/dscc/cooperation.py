"""R-HS local cooperation trace adapter; no messaging, model calls or approvals."""
from __future__ import annotations

from typing import Any, TYPE_CHECKING

from .canonical import canonical_bytes, parse_json, validate_cid
from .research import ResearchService, parent_cids, validate_profile

if TYPE_CHECKING:
    from .store import Node

SCHEMA = "dscc.cooperation.step/0.1"
FIELDS = {
    "assessment": {"missing", "alternatives", "choice", "reason_summary"},
    "request_draft": {"recipient_label", "recipient_source", "request_text",
                      "proposed_disclosure_cids"},
    "dispatch_observation": {"delivery", "channel", "disclosed_context_cids"},
    "response_observation": {"response", "summary"},
    "verification": {"verdict", "notes"},
    "continuation": {"status", "next_action"},
}
PREDECESSORS = {
    "assessment": set(),
    "request_draft": {"assessment"},
    "dispatch_observation": {"request_draft"},
    "response_observation": {"dispatch_observation"},
    "verification": {"response_observation"},
    "continuation": {"assessment", "request_draft", "dispatch_observation",
                     "response_observation", "verification"},
}
CHOICES = {"continue", "search", "ask_human", "ask_ai", "pause"}


def _text(value: Any, name: str, limit: int = 4096) -> None:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"invalid {name}")


def _one(value: Any, choices: set[str], name: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise ValueError(f"invalid {name}")


def _cids(value: Any, name: str, maximum: int = 24) -> None:
    if not isinstance(value, list) or len(value) > maximum:
        raise ValueError(f"invalid {name}")
    for cid in value:
        validate_cid(cid)
    if len(set(value)) != len(value):
        raise ValueError(f"duplicate {name}")


def _refs(step: dict) -> list[str]:
    refs = set(step["evidence_cids"])
    if step["previous_cid"] is not None:
        refs.add(step["previous_cid"])
    if step["stage"] == "request_draft":
        refs.update(step["details"]["proposed_disclosure_cids"])
    if step["stage"] == "dispatch_observation":
        refs.update(step["details"]["disclosed_context_cids"])
    return sorted(refs)


def validate_step(step: Any) -> dict:
    """Validate a declared trace step, not truth, real contact or model agency."""
    if not isinstance(step, dict) or set(step) != {
        "schema", "episode_id", "stage", "initiator", "previous_cid", "evidence_cids", "details"
    }:
        raise ValueError("invalid cooperation fields")
    if step["schema"] != SCHEMA:
        raise ValueError("unsupported cooperation schema")
    _one(step["stage"], set(FIELDS), "stage")
    _one(step["initiator"], {"agent_policy", "human_instruction", "external_rule", "unknown"},
         "initiator")
    _text(step["episode_id"], "episode_id", 120)
    prev = step["previous_cid"]
    if prev is not None:
        validate_cid(prev)
    if (step["stage"] == "assessment") != (prev is None):
        raise ValueError("an assessment starts a new episode; later steps need a predecessor")
    _cids(step["evidence_cids"], "evidence_cids")
    d = step["details"]
    stage = step["stage"]
    if not isinstance(d, dict) or set(d) != FIELDS[stage]:
        raise ValueError("invalid stage details")
    if stage == "assessment":
        _text(d["missing"], "missing")
        _text(d["reason_summary"], "reason_summary")
        if not step["evidence_cids"]:
            raise ValueError("assessment needs original context")
        a = d["alternatives"]
        if (not isinstance(a, list) or not a or len(a) > 5
                or any(not isinstance(x, str) or x not in CHOICES for x in a)
                or len(set(a)) != len(a) or d["choice"] not in a):
            raise ValueError("invalid alternatives or choice")
    elif stage == "request_draft":
        _text(d["recipient_label"], "recipient_label", 240)
        _text(d["request_text"], "request_text")
        _one(d["recipient_source"], {"owner_listed", "unverified_external", "unknown"},
             "recipient_source")
        _cids(d["proposed_disclosure_cids"], "proposed_disclosure_cids", 16)
    elif stage == "dispatch_observation":
        _one(d["delivery"], {"sent", "not_sent", "unknown"}, "delivery")
        _text(d["channel"], "channel", 240)
        _cids(d["disclosed_context_cids"], "disclosed_context_cids", 16)
        if d["delivery"] == "sent" and not step["evidence_cids"]:
            raise ValueError("reported sending needs original observation")
        if d["delivery"] == "not_sent" and d["disclosed_context_cids"]:
            raise ValueError("not_sent cannot claim disclosed context")
    elif stage == "response_observation":
        _one(d["response"], {"answered", "partial", "declined", "no_reply", "unknown"},
             "response")
        _text(d["summary"], "summary")
        if d["response"] in {"answered", "partial", "declined"} and not step["evidence_cids"]:
            raise ValueError("a reported response needs original observation")
    elif stage == "verification":
        _one(d["verdict"], {"supported", "rejected", "unknown"}, "verdict")
        _text(d["notes"], "notes")
        if d["verdict"] != "unknown" and not step["evidence_cids"]:
            raise ValueError("verification finding needs original evidence")
    else:
        _one(d["status"], {"resumed", "paused", "stopped"}, "continuation status")
        _text(d["next_action"], "next_action")
    if len(_refs(step)) > 32:
        raise ValueError("more than 32 direct references")
    canonical_bytes(step)  # no floats, invalid Unicode or oversized metadata
    return step


def _transition(step: dict, prior: dict | None) -> None:
    if prior is None:
        if step["stage"] != "assessment":
            raise ValueError("first step must assess")
        return
    if prior["stage"] not in PREDECESSORS[step["stage"]]:
        raise ValueError("invalid phase transition")
    if step["stage"] == "request_draft" and prior["details"]["choice"] not in {
        "ask_human", "ask_ai"
    }:
        raise ValueError("request requires an explicitly selected ask action")
    if step["stage"] == "response_observation" and prior["details"]["delivery"] == "not_sent":
        raise ValueError("no response can follow not_sent")
    if step["stage"] == "verification" and prior["details"]["response"] not in {
        "answered", "partial"
    }:
        raise ValueError("no answer to verify")


def read_step(node: Node, cid: str) -> dict:
    """Read a signed local step without treating reported identity or evidence as truth."""
    body = node.fetch(cid)["body"]
    if body["kind"] != "DecisionRecord" or set(body["data"]) != {"research"}:
        raise ValueError("not a cooperation research record")
    p = validate_profile(body["data"]["research"])
    if p["type"] != "AgentContribution":
        raise ValueError("not a cooperation contribution")
    step = validate_step(p["content"].get("extensions", {}).get(SCHEMA))
    role = "context" if step["stage"] in {"assessment", "request_draft"} else "observation"
    sources = [{"cid": cid, "pointer": "", "role": role}
               for cid in sorted(step["evidence_cids"])]
    if (p["input_cids"] != _refs(step) or p["sources"] != sources
            or body["parents"] != parent_cids(p)
            or body["title"] != p["title"] or body["summary"] != p["summary"]):
        raise ValueError("cooperation references or envelope disagree")
    return {"cid": cid, "project": p["project"], "contributor": p["contributor"],
            "step": step, "contact_authorized": False, "execution_authorized": False}


def record_step(node: Node, *, project: str, contributor: dict, step: dict) -> dict:
    """Local-only record write; never sends messages or permits tool execution."""
    step = validate_step(parse_json(canonical_bytes(step)))
    prior = None
    if step["previous_cid"] is not None:
        row = read_step(node, step["previous_cid"])
        if row["project"] != project or row["step"]["episode_id"] != step["episode_id"]:
            raise ValueError("predecessor belongs to another episode or project")
        prior = row["step"]
    _transition(step, prior)
    stage = step["stage"]
    role = "context" if stage in {"assessment", "request_draft"} else "observation"
    p = {
        "schema": "dscc.research/0.1", "type": "AgentContribution", "project": project,
        "title": f"R-HS {stage}: {step['episode_id']}",
        "summary": "Local declaration; not proof of contact, agency, approval or truth.",
        "contributor": contributor, "input_cids": _refs(step),
        "sources": [{"cid": c, "pointer": "", "role": role}
                    for c in sorted(step["evidence_cids"])],
        "relations": [],
        "content": {"description": f"Cooperation trace: {stage} (data, not instructions).",
                    "extensions": {SCHEMA: step}},
    }
    result = ResearchService(node).record(p)
    return {**result, "contact_authorized": False, "side_effects": "record_only"}


def episode_history(node: Node, head_cid: str, *, max_steps: int = 64) -> list[dict]:
    """Recover a bounded sequence of local records, not an external agent runtime."""
    if type(max_steps) is not int or not 1 <= max_steps <= 256:
        raise ValueError("invalid max_steps")
    history = []
    current = validate_cid(head_cid)
    project = episode = None
    while current is not None:
        if len(history) >= max_steps:
            raise ValueError("episode history exceeds bound")
        row = read_step(node, current)
        step = row["step"]
        if project is not None and (project != row["project"] or episode != step["episode_id"]):
            raise ValueError("cross-project or cross-episode history")
        project, episode = row["project"], step["episode_id"]
        history.append(row)
        current = step["previous_cid"]
    history.reverse()
    for i, row in enumerate(history):
        _transition(row["step"], history[i-1]["step"] if i else None)
    return history
