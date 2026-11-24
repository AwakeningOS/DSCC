"""T007: Explicit adapter between DSCC concept-paper Artifact schema and seed profile.

Follows `docs/reference/original_schemas/dscc_artifact.schema.json`.
Preserves provenance, license, authors, payloads and objectType distinctions
(especially keeping Claim/hypotheses distinct from ExperimentRun/observations)
without executing any imported artifact.
"""
from __future__ import annotations

from typing import Any

from ..canonical import canonical_bytes, parse_json, validate_cid
from ..models import KINDS, manifest

PAPER_SCHEMA_VERSION = "0.1"
PAPER_WRAPPER_KEY = "paper_artifact"
PAPER_WRAPPER_SCHEMA = "dscc.paper.artifact/0.1"

REQUIRED_FIELDS = frozenset({
    "schemaVersion", "objectType", "title", "authors", "license", "payloads", "provenance",
})
ALLOWED_FIELDS = REQUIRED_FIELDS | frozenset({
    "description", "created", "toolchain", "verification", "sensitivity", "retention", "extensions",
})
VERIFICATION_CLASSES = frozenset({"V0", "V1", "V2", "V3", "V4"})
SENSITIVITIES = frozenset({"public", "restricted", "confidential", "secret"})
RETENTIONS = frozenset({"ephemeral", "project", "archival", "critical", "restricted"})


def _str(val: Any, name: str, *, nonempty: bool = False, max_len: int = 4096) -> str:
    if not isinstance(val, str) or len(val) > max_len or (nonempty and not val.strip()):
        raise ValueError(f"invalid paper artifact {name}")
    return val


def validate_paper_artifact(doc: Any) -> dict[str, Any]:
    """Validate an object against the concept-paper DSCC Artifact manifest contract."""
    if not isinstance(doc, dict):
        raise ValueError("paper artifact must be a JSON object")
    keys = set(doc)
    missing = REQUIRED_FIELDS - keys
    if missing:
        raise ValueError(f"paper artifact missing required fields: {sorted(missing)}")
    unknown = keys - ALLOWED_FIELDS
    if unknown:
        raise ValueError(f"paper artifact contains unknown fields: {sorted(unknown)}")
    if doc["schemaVersion"] != PAPER_SCHEMA_VERSION:
        raise ValueError("unsupported paper artifact schemaVersion")
    if not isinstance(doc["objectType"], str) or doc["objectType"] not in KINDS:
        raise ValueError("unsupported paper artifact objectType")
    _str(doc["title"], "title", nonempty=True, max_len=240)
    if "description" in doc:
        _str(doc["description"], "description", max_len=4096)
    _str(doc["license"], "license", nonempty=True, max_len=128)
    if "created" in doc:
        _str(doc["created"], "created", nonempty=True, max_len=128)

    authors = doc["authors"]
    if not isinstance(authors, list) or len(authors) > 128:
        raise ValueError("invalid paper artifact authors")
    for author in authors:
        if not isinstance(author, dict) or "id" not in author or not set(author) <= {"id", "role", "signature"}:
            raise ValueError("invalid paper artifact author entry")
        _str(author["id"], "author.id", nonempty=True, max_len=512)
        for opt in ("role", "signature"):
            if opt in author:
                _str(author[opt], f"author.{opt}", max_len=1024)

    payloads = doc["payloads"]
    if not isinstance(payloads, list) or len(payloads) > 256:
        raise ValueError("invalid paper artifact payloads")
    for item in payloads:
        if (not isinstance(item, dict) or not {"role", "cid"} <= set(item)
                or not set(item) <= {"role", "cid", "mediaType", "size", "encryption"}):
            raise ValueError("invalid paper artifact payload entry")
        _str(item["role"], "payload.role", nonempty=True, max_len=128)
        _str(item["cid"], "payload.cid", nonempty=True, max_len=256)
        if "mediaType" in item:
            _str(item["mediaType"], "payload.mediaType", max_len=256)
        if "size" in item and (type(item["size"]) is not int or item["size"] < 0):
            raise ValueError("invalid paper artifact payload.size")
        if "encryption" in item and not isinstance(item["encryption"], dict):
            raise ValueError("invalid paper artifact payload.encryption")

    prov = doc["provenance"]
    if not isinstance(prov, dict):
        raise ValueError("paper artifact provenance must be an object")
    for list_field in ("used", "wasDerivedFrom", "wasAssociatedWith"):
        if list_field in prov:
            val = prov[list_field]
            if not isinstance(val, list) or len(val) > 256 or any(not isinstance(x, str) or not x for x in val):
                raise ValueError(f"invalid provenance.{list_field}")
    if "wasGeneratedBy" in prov:
        _str(prov["wasGeneratedBy"], "provenance.wasGeneratedBy", nonempty=True, max_len=512)

    if "toolchain" in doc:
        tc = doc["toolchain"]
        if not isinstance(tc, list) or len(tc) > 64:
            raise ValueError("invalid paper artifact toolchain")
        for row in tc:
            if not isinstance(row, dict) or not set(row) <= {"cid", "ociDigest", "signature", "attestation"}:
                raise ValueError("invalid toolchain entry")
            for k, v in row.items():
                _str(v, f"toolchain.{k}", max_len=1024)

    if "verification" in doc:
        ver = doc["verification"]
        if not isinstance(ver, dict) or not set(ver) <= {"class", "policyCid", "receipts"}:
            raise ValueError("invalid paper artifact verification")
        if "class" in ver and ver["class"] not in VERIFICATION_CLASSES:
            raise ValueError("invalid verification.class")
        if "policyCid" in ver:
            _str(ver["policyCid"], "verification.policyCid", nonempty=True, max_len=256)
        if "receipts" in ver:
            rc = ver["receipts"]
            if not isinstance(rc, list) or any(not isinstance(x, str) or not x for x in rc):
                raise ValueError("invalid verification.receipts")

    if "sensitivity" in doc and doc["sensitivity"] not in SENSITIVITIES:
        raise ValueError("invalid paper artifact sensitivity")
    if "retention" in doc and doc["retention"] not in RETENTIONS:
        raise ValueError("invalid paper artifact retention")
    if "extensions" in doc and not isinstance(doc["extensions"], dict):
        raise ValueError("paper artifact extensions must be an object")

    canonical_bytes(doc)
    return doc


def _extract_parent_cids(prov: dict[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("wasDerivedFrom", "used"):
        for candidate in prov.get(key, []):
            try:
                refs.append(validate_cid(candidate))
            except ValueError:
                pass
    gen = prov.get("wasGeneratedBy")
    if isinstance(gen, str):
        try:
            refs.append(validate_cid(gen))
        except ValueError:
            pass
    unique = sorted(set(refs))
    if len(unique) > 32:
        raise ValueError("paper artifact provenance CID references exceed seed parent limit of 32")
    return unique


def paper_to_seed(paper_doc: dict[str, Any], *, parents: list[str] | None = None) -> dict[str, Any]:
    """Convert a concept-paper Artifact manifest into a DSCC seed manifest without data loss."""
    validated = validate_paper_artifact(parse_json(canonical_bytes(paper_doc)))
    derived_parents = _extract_parent_cids(validated["provenance"])
    merged_parents = sorted(set(derived_parents) | set(parents or []))
    return manifest(
        kind=validated["objectType"],
        title=validated["title"],
        data={
            PAPER_WRAPPER_KEY: {
                "adapter_schema": PAPER_WRAPPER_SCHEMA,
                "original_manifest": validated,
            }
        },
        summary=validated.get("description", ""),
        parents=merged_parents,
        license=validated["license"],
    )


def seed_to_paper(seed_doc_or_envelope: dict[str, Any]) -> dict[str, Any]:
    """Recover a concept-paper Artifact manifest from a seed body or signed envelope."""
    body = seed_doc_or_envelope["body"] if "body" in seed_doc_or_envelope else seed_doc_or_envelope
    if not isinstance(body, dict) or "data" not in body or not isinstance(body["data"], dict):
        raise ValueError("expected a DSCC seed artifact manifest or envelope")
    wrapper = body["data"].get(PAPER_WRAPPER_KEY)
    if (not isinstance(wrapper, dict)
            or wrapper.get("adapter_schema") != PAPER_WRAPPER_SCHEMA
            or "original_manifest" not in wrapper):
        raise ValueError("artifact does not contain an adapted concept-paper manifest")
    paper_doc = validate_paper_artifact(wrapper["original_manifest"])
    if (paper_doc["objectType"] != body.get("kind")
            or paper_doc["title"] != body.get("title")
            or paper_doc["license"] != body.get("license")):
        raise ValueError("adapted paper manifest disagrees with outer seed artifact fields")
    return parse_json(canonical_bytes(paper_doc))
