import json
from pathlib import Path
import jsonschema
from dscc.canonical import canonical_bytes,cid_for
from dscc.models import validate_manifest

ROOT=Path(__file__).resolve().parents[1]

def test_examples_match_schema_and_runtime():
    schema=json.loads((ROOT/'schemas/artifact.schema.json').read_text())
    jsonschema.Draft202012Validator.check_schema(schema)
    for p in (ROOT/'examples').glob('*.json'):
        doc=json.loads(p.read_text())
        jsonschema.validate(doc,schema)
        validate_manifest(doc)

def test_stable_vectors():
    vectors=json.loads((ROOT/'schemas/test_vectors.json').read_text())
    for row in vectors:
        actual=canonical_bytes(row['input'])
        assert actual.decode()==row['canonical_utf8']
        assert cid_for(actual)==row['cid']


def test_job_spec_matches_schema(tmp_path):
    from dscc.store import init_node
    from dscc.models import manifest
    node = init_node(tmp_path / "job-schema")
    cid = node.record(manifest("Dataset", "numbers", {"values": [1, 2, 3]}))
    job = node.submit_job(cid)
    schema = json.loads((ROOT / "schemas/job.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(job["spec"], schema)
