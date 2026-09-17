"""Executable proposal checks, NOT the application's admission/ACL implementation."""
from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from typing import Callable

from jsonschema import Draft202012Validator
from dscc.canonical import canonical_bytes, validate_cid

SCHEMA = json.loads(Path(__file__).with_name("atlas.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
Fetch = Callable[[str], dict]


def sources(payload: dict) -> list[dict]:
    result = list(payload.get("sources", []))
    for item in payload.get("nodes", []) + payload.get("links", []):
        result.extend(item["sources"])
    return result


def external_cids(payload: dict) -> set[str]:
    result = {r["cid"] for r in sources(payload)}
    for field in ("source_episode", "target_episode", "bridge", "trial_episode"):
        if field in payload:
            result.add(payload[field])
    result.update(m["episode"] for m in payload.get("members", []))
    result.update(payload.get("counterexamples", []))
    return result


def pointer(document: object, path: str) -> object:
    """Resolve RFC 6901 pointers without eval, filesystem or network access."""
    if path == "":
        return document
    if not path.startswith("/"):
        raise ValueError("invalid pointer")
    current = document
    for encoded in path[1:].split("/"):
        import re
        if re.search(r"~(?![01])", encoded):
            raise ValueError("invalid pointer escape")
        token = encoded.replace("~1", "/").replace("~0", "~")
        try:
            if isinstance(current, list):
                if not re.fullmatch(r"0|[1-9][0-9]*", token):
                    raise ValueError("invalid array index")
                current = current[int(token)]
            elif isinstance(current, dict):
                current = current[token]
            else:
                raise ValueError("pointer enters a scalar")
        except (KeyError, IndexError) as exc:
            raise ValueError("missing source location") from exc
    return current


def graph(payload: dict) -> tuple[dict, dict]:
    nodes = {n["id"]: n for n in payload["nodes"]}
    edges = {e["id"]: e for e in payload["links"]}
    if len(nodes) != len(payload["nodes"]) or len(edges) != len(payload["links"]):
        raise ValueError("duplicate local ID")
    adjacency = {n: [] for n in nodes}
    degree = {n: 0 for n in nodes}
    for item in payload["nodes"] + payload["links"]:
        if item["origin"] != "unknown" and not item["sources"]:
            raise ValueError("origin requires a source locator")
    for e in edges.values():
        if e["from"] not in nodes or e["to"] not in nodes:
            raise ValueError("missing graph endpoint")
        if e["relation"] == "precedes":
            adjacency[e["from"]].append(e["to"])
            degree[e["to"]] += 1
    queue = deque(n for n in nodes if degree[n] == 0)
    visited = 0
    while queue:
        n = queue.popleft()
        visited += 1
        for child in adjacency[n]:
            degree[child] -= 1
            if degree[child] == 0:
                queue.append(child)
    if visited != len(nodes):
        raise ValueError("precedes must be acyclic")
    return nodes, edges


def bindings(mapping: list[dict], left: dict, right: dict) -> dict[str, str]:
    result = {r["from"]: r["to"] for r in mapping}
    if len(result) != len(mapping) or len(set(result.values())) != len(result):
        raise ValueError("bindings must be one-to-one")
    for a, b in result.items():
        if a not in left or b not in right:
            raise ValueError("missing mapped node")
        if left[a]["role"] != right[b]["role"]:
            raise ValueError("default profile requires compatible roles")
    return result


def atlas(fetch: Fetch, cid: str, expected: str) -> dict:
    validate_cid(cid)
    try:
        payload = fetch(cid)["body"]["data"]["atlas"]
    except KeyError as exc:
        raise ValueError("expected atlas artifact") from exc
    VALIDATOR.validate(payload)
    if payload["type"] != expected:
        raise ValueError("wrong referenced object type")
    return payload


def validate(payload: dict, fetch: Fetch) -> None:
    """Check shape, seed compatibility and direct references; not scientific truth."""
    VALIDATOR.validate(payload)
    canonical_bytes(payload)  # Preserves the seed's numerical/Unicode constraints.
    for cid in external_cids(payload):
        validate_cid(cid)
        fetch(cid)  # Caller must supply the existing integrity-checked store.
    for r in sources(payload):
        pointer(fetch(r["cid"]), r["pointer"])
    kind = payload["type"]
    if kind in ("Episode", "Motif"):
        left, _ = graph(payload)
    if kind == "Bridge":
        a = atlas(fetch, payload["source_episode"], "Episode")
        b = atlas(fetch, payload["target_episode"], "Episode")
        an, ae = graph(a)
        bn, be = graph(b)
        mapping = bindings(payload["mapping"], an, bn)
        matches = payload["matched_edges"]
        if (len({p["from"] for p in matches}) != len(matches)
                or len({p["to"] for p in matches}) != len(matches)):
            raise ValueError("edge bindings must be one-to-one")
        for pair in matches:
            if pair["from"] not in ae or pair["to"] not in be:
                raise ValueError("missing mapped edge")
            x, y = ae[pair["from"]], be[pair["to"]]
            if (x["relation"] != y["relation"]
                    or mapping.get(x["from"]) != y["from"]
                    or mapping.get(x["to"]) != y["to"]):
                raise ValueError("edge correspondence is inconsistent")
    elif kind == "TransferAssessment":
        atlas(fetch, payload["bridge"], "Bridge")
        trial = atlas(fetch, payload["trial_episode"], "Episode")
        graph(trial)
        if not any(r["cid"] == payload["trial_episode"] for r in payload["sources"]):
            raise ValueError("assessment must reference its trial evidence")
        if payload["verdict"] in ("helpful", "not_helpful"):
            if not any(n["role"] == "action" and n["stage"] == "performed" for n in trial["nodes"]):
                raise ValueError("reported outcome needs a performed trial")
    elif kind == "Motif":
        for member in payload["members"]:
            other, other_edges = graph(atlas(fetch, member["episode"], "Episode"))
            mapping = bindings(member["mapping"], left, other)
            if set(mapping) != set(left):
                raise ValueError("motif member must map every pattern node")
            available = {(e["from"], e["relation"], e["to"]) for e in other_edges.values()}
            for e in payload["links"]:
                if (mapping[e["from"]], e["relation"], mapping[e["to"]]) not in available:
                    raise ValueError("motif member does not preserve a relation")
        for cid in payload["counterexamples"]:
            atlas(fetch, cid, "Episode")
