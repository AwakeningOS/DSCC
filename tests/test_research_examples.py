"""Specialized research examples retain both profile and seed-envelope checks."""
import json
from pathlib import Path

import jsonschema

from dscc.research import ResearchService, research_artifact, validate_profile
from dscc.models import validate_manifest
from dscc.store import init_node

ROOT = Path(__file__).resolve().parents[1]


def test_research_examples_match_profile_and_seed(tmp_path):
    schema = json.loads((ROOT / "schemas/artifact.schema.json").read_text(encoding="utf-8"))
    paths = list((ROOT / "examples/research").glob("*.json"))
    assert paths
    node = init_node(tmp_path / "node")
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        validate_profile(payload)
        wrapped = research_artifact(payload)
        jsonschema.validate(wrapped, schema)
        validate_manifest(wrapped)
        result = ResearchService(node).record(payload)
        if payload["type"] == "ResearchState":
            assert ResearchService(node).handoff(result["cid"])["state"] == payload
