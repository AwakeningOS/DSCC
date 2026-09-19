#!/usr/bin/env python3
"""Validate source-package structure, retained-source digests and JSON contracts."""
from __future__ import annotations

import ast
import hashlib
import json
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> None:
    import jsonschema
    from dscc.canonical import canonical_bytes, cid_for
    from dscc.models import validate_manifest

    required = ["README.md", "AGENTS.md", "LICENSE", "SECURITY.md", "CITATION.cff",
                "docs/START_HERE.ja.md", "docs/STATUS.md", "docs/ARCHITECTURE.ja.md",
                "docs/PROTOCOL.md", "docs/TASKS.md", "docs/INTEGRATIONS.ja.md",
                "docs/GITHUB_SETUP.ja.md", "docs/SOURCE_TRACEABILITY.md",
                "docs/GLOBAL_SCALE_CHALLENGES.ja.md",
                "docs/proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md",
                "docs/adr/0004-open-model-commons-foundation.md"]
    for name in required:
        assert (ROOT / name).is_file(), f"missing {name}"
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["name"] == "dscc-desktop"
    python_files = list((ROOT / "src").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")) + list((ROOT / "tests").glob("*.py"))
    for path in python_files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path.relative_to(ROOT)))
    schemas = list((ROOT / "schemas").glob("*.schema.json"))
    for path in schemas:
        jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))
    artifact_schema = json.loads((ROOT / "schemas/artifact.schema.json").read_text(encoding="utf-8"))
    for path in (ROOT / "examples").glob("*.json"):
        doc = json.loads(path.read_text(encoding="utf-8"))
        jsonschema.validate(doc, artifact_schema)
        validate_manifest(doc)
    for row in json.loads((ROOT / "schemas/test_vectors.json").read_text(encoding="utf-8")):
        raw = canonical_bytes(row["input"])
        assert raw.decode("utf-8") == row["canonical_utf8"]
        assert cid_for(raw) == row["cid"]
    count = 0
    for line in (ROOT / "docs/reference/SHA256SUMS.txt").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, name = line.split(maxsplit=1)
        path = ROOT / name.strip().lstrip("*")
        assert path.resolve().is_relative_to((ROOT / "docs/reference").resolve())
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, f"retained source changed: {name}"
        count += 1
    issues = json.loads((ROOT / "docs/issues.json").read_text(encoding="utf-8"))
    print(json.dumps({"ok": True, "python_files_parsed": len(python_files),
                      "json_schemas_checked": len(schemas), "retained_source_checksums": count,
                      "prepared_issue_count": len(issues)}, indent=2))


if __name__ == "__main__":
    main()
