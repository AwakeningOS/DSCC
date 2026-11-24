"""T007: W3C PROV-JSON and RO-Crate 1.1 exporters preserving original signed bytes.

Export never alters signed envelopes, never claims scientific truth, and never
executes artifact contents.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from ..canonical import canonical_bytes, cid_for, parse_json, validate_cid
from ..identity import verify
from ..models import validate_manifest
from ..store import Node

PROV_NS = "http://www.w3.org/ns/prov#"
DSCC_NS = "https://dscc.invalid/ns/0.1#"


def export_prov_json(node: Node, root_cid: str) -> dict[str, Any]:
    """Export an artifact's verified ancestor closure as a W3C PROV-JSON document."""
    bundle = node.export_bundle(root_cid)
    entities: dict[str, dict[str, Any]] = {}
    activities: dict[str, dict[str, Any]] = {}
    agents: dict[str, dict[str, Any]] = {}
    was_derived_from: dict[str, dict[str, Any]] = {}
    was_attributed_to: dict[str, dict[str, Any]] = {}
    was_generated_by: dict[str, dict[str, Any]] = {}
    used: dict[str, dict[str, Any]] = {}

    for row in bundle["artifacts"]:
        cid = row["cid"]
        env = row["envelope"]
        body = env["body"]
        signer = env["public_key"]
        eid = f"dscc:artifact/{cid}"
        aid = f"dscc:signer/{signer}"

        agents.setdefault(aid, {
            "prov:type": "dscc:SigningKey",
            "dscc:publicKeyHex": signer,
            "dscc:identityNote": "Authenticates signing key only; not a verified legal identity.",
        })

        kind = body["kind"]
        entities[eid] = {
            "prov:type": f"dscc:{kind}",
            "prov:label": body["title"],
            "dscc:cid": cid,
            "dscc:schema": body["schema"],
            "dscc:license": body["license"],
            "dscc:epistemicClass": "hypothesis" if kind == "Claim" else (
                "execution_observation" if kind == "ExperimentRun" else "research_artifact"
            ),
            "dscc:scientificCorrectness": "not_assessed",
        }
        was_attributed_to[f"_:attr_{cid}"] = {"prov:entity": eid, "prov:agent": aid}

        for idx, parent_cid in enumerate(body["parents"]):
            was_derived_from[f"_:der_{cid}_{idx}"] = {
                "prov:generatedEntity": eid,
                "prov:usedEntity": f"dscc:artifact/{parent_cid}",
            }

        if kind == "ExperimentRun":
            act_id = f"dscc:activity/{cid}"
            activities[act_id] = {
                "prov:type": "dscc:ExperimentExecution",
                "dscc:tool": str(body["data"].get("tool", "declared-external")),
                "dscc:independentVerification": bool(
                    body["data"].get("independent_scientific_verification", False)
                ),
            }
            was_generated_by[f"_:gen_{cid}"] = {"prov:entity": eid, "prov:activity": act_id}
            for idx, parent_cid in enumerate(body["parents"]):
                used[f"_:use_{cid}_{idx}"] = {
                    "prov:activity": act_id,
                    "prov:entity": f"dscc:artifact/{parent_cid}",
                }

    return {
        "prefix": {
            "prov": PROV_NS,
            "dscc": DSCC_NS,
        },
        "dscc:rootCid": root_cid,
        "entity": entities,
        "activity": activities,
        "agent": agents,
        "wasDerivedFrom": was_derived_from,
        "wasAttributedTo": was_attributed_to,
        "wasGeneratedBy": was_generated_by,
        "used": used,
    }


def export_rocrate_dict(node: Node, root_cid: str) -> dict[str, Any]:
    """Build RO-Crate 1.1 metadata JSON plus exact signed envelope bytes (in memory)."""
    bundle = node.export_bundle(root_cid)
    root_env = next(row["envelope"] for row in bundle["artifacts"] if row["cid"] == root_cid)
    root_body = root_env["body"]

    graph: list[dict[str, Any]] = [
        {
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "about": {"@id": "./"},
            "conformsTo": {"@id": "https://w3id.org/ro/crate/1.1"},
        },
        {
            "@id": "./",
            "@type": "Dataset",
            "name": root_body["title"],
            "description": root_body["summary"] or "DSCC signed research-artifact closure.",
            "license": root_body["license"],
            "hasPart": [{"@id": f"envelopes/{row['cid']}.json"} for row in bundle["artifacts"]],
            "dscc:rootCid": root_cid,
            "dscc:scientificCorrectness": "not_assessed",
        },
    ]

    envelopes_bytes: dict[str, bytes] = {}
    seen_signers: set[str] = set()
    for row in bundle["artifacts"]:
        cid = row["cid"]
        env = row["envelope"]
        raw = canonical_bytes(env)
        envelopes_bytes[f"envelopes/{cid}.json"] = raw
        body = env["body"]
        signer = env["public_key"]
        signer_id = f"#signer-{signer}"
        if signer not in seen_signers:
            seen_signers.add(signer)
            graph.append({
                "@id": signer_id,
                "@type": "Thing",
                "name": f"DSCC Ed25519 signing key {signer[:16]}...",
                "identifier": signer,
            })
        graph.append({
            "@id": f"envelopes/{cid}.json",
            "@type": ["File", f"dscc:{body['kind']}"],
            "name": body["title"],
            "description": body["summary"],
            "encodingFormat": "application/json",
            "contentSize": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "license": body["license"],
            "author": {"@id": signer_id},
            "dscc:cid": cid,
            "dscc:kind": body["kind"],
            "dscc:parents": [{"@id": f"envelopes/{p}.json"} for p in body["parents"]],
        })

    metadata = {
        "@context": [
            "https://w3id.org/ro/crate/1.1/context",
            {"dscc": DSCC_NS},
        ],
        "@graph": graph,
    }
    return {
        "schema": "dscc.rocrate.export/0.1",
        "root_cid": root_cid,
        "artifact_count": len(bundle["artifacts"]),
        "metadata": metadata,
        "files": {path: raw.decode("utf-8") for path, raw in envelopes_bytes.items()},
    }


def export_rocrate_dir(node: Node, root_cid: str, output_dir: Path) -> dict[str, Any]:
    """Write a complete RO-Crate 1.1 directory with untouched signed envelope files."""
    output_dir = output_dir.expanduser().resolve()
    if output_dir.exists():
        raise ValueError("RO-Crate output directory already exists; refusing to overwrite")
    crate = export_rocrate_dict(node, root_cid)
    envelopes_dir = output_dir / "envelopes"
    envelopes_dir.mkdir(parents=True, exist_ok=False)
    for rel_path, content in crate["files"].items():
        target = output_dir / rel_path
        target.write_bytes(content.encode("utf-8"))
    meta_path = output_dir / "ro-crate-metadata.json"
    meta_path.write_text(json.dumps(crate["metadata"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "exported_dir": str(output_dir),
        "root_cid": root_cid,
        "artifact_count": crate["artifact_count"],
        "large_blocks_included": False,
    }


def verify_rocrate_dir(crate_dir: Path) -> dict[str, Any]:
    """Verify every signed envelope file inside an exported RO-Crate directory."""
    crate_dir = crate_dir.expanduser().resolve()
    meta_path = crate_dir / "ro-crate-metadata.json"
    meta = parse_json(meta_path.read_bytes(), max_bytes=8_388_608)
    graph = meta.get("@graph", [])
    root_entry = next((row for row in graph if row.get("@id") == "./"), None)
    if root_entry is None:
        raise ValueError("RO-Crate missing root dataset entry")
    verified_cids: list[str] = []
    for row in graph:
        rel = row.get("@id", "")
        if not rel.startswith("envelopes/") or not rel.endswith(".json"):
            continue
        expected_cid = validate_cid(row["dscc:cid"])
        raw = (crate_dir / rel).read_bytes()
        if hashlib.sha256(raw).hexdigest() != row["sha256"]:
            raise ValueError(f"RO-Crate sha256 mismatch for {rel}")
        if cid_for(raw) != expected_cid:
            raise ValueError(f"RO-Crate CID mismatch for {rel}")
        env = parse_json(raw)
        if canonical_bytes(env) != raw:
            raise ValueError(f"RO-Crate non-canonical envelope for {rel}")
        validate_manifest(verify(env, "artifact"))
        verified_cids.append(expected_cid)
    return {
        "valid": True,
        "root_cid": validate_cid(root_entry["dscc:rootCid"]),
        "verified_envelopes": len(verified_cids),
        "scientific_correctness": "not_assessed",
    }
