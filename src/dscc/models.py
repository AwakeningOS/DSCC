"""Versioned seed records. They do not claim full paper-schema compatibility."""
from __future__ import annotations

from typing import Any
from .canonical import MAX_OBJECT_BYTES, canonical_bytes, validate_cid

SCHEMA = "dscc.artifact.seed/0.1"
KINDS = (
    "Dataset", "Tool", "Workflow", "ExperimentRun", "Claim", "EvidenceLink",
    "WorldSnapshot", "Task", "DecisionRecord", "MemoryCapsule",
    "VerificationReceipt", "CreditReceipt", "IndexRecord", "PolicyProfile",
)


def validate_manifest(doc: Any) -> dict[str, Any]:
    if not isinstance(doc, dict):
        raise ValueError("artifact manifest must be an object")
    expected = {"schema", "kind", "title", "summary", "data", "parents", "license"}
    if set(doc) != expected:
        raise ValueError("artifact manifest fields do not match seed schema")
    if doc["schema"] != SCHEMA or doc["kind"] not in KINDS:
        raise ValueError("unsupported artifact schema or kind")
    for key, maximum, minimum in (("title", 240, 1), ("summary", 4096, 0), ("license", 128, 1)):
        if not isinstance(doc[key], str) or not minimum <= len(doc[key]) <= maximum:
            raise ValueError(f"invalid {key}")
    if not isinstance(doc["data"], dict):
        raise ValueError("artifact data must be an object")
    parents = doc["parents"]
    if not isinstance(parents, list) or len(parents) > 32:
        raise ValueError("parents must be a list of at most 32 CIDs")
    for cid in parents:
        validate_cid(cid)
    if len(set(parents)) != len(parents):
        raise ValueError("duplicate parent CID")
    if len(canonical_bytes(doc)) > MAX_OBJECT_BYTES - 1024:
        raise ValueError("artifact exceeds size limit")
    return doc


def manifest(kind: str, title: str, data: dict[str, Any], *, summary: str = "",
             parents: list[str] | None = None, license: str = "NOASSERTION") -> dict[str, Any]:
    return validate_manifest({
        "schema": SCHEMA, "kind": kind, "title": title, "summary": summary,
        "data": data, "parents": parents or [], "license": license,
    })
