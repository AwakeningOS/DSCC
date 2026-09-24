"""Research-specific stdio persistence and signed-source boundary regressions."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from dscc.models import manifest
from dscc.research import SCHEMA, ResearchService
from dscc.store import init_node


def initial_state():
    return {
        "schema": SCHEMA, "type": "ResearchState", "project": "synthetic-stdio",
        "title": "Synthetic state", "summary": "No real model was called.",
        "contributor": {"kind": "unknown", "name": "test fixture", "provider": None,
                        "model": None, "snapshot": None},
        "input_cids": [], "sources": [], "relations": [],
        "content": {"objective": "Resume a synthetic fixture.", "finding_cids": [],
                    "open_question_cids": [], "next_actions": ["Inspect original evidence."], "resume_cids": []},
    }


def session(home, name, arguments):
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2025-11-25", "capabilities": {},
            "clientInfo": {"name": "synthetic-client", "version": "1"}}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": name, "arguments": arguments}},
    ]
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}
    run = subprocess.run([sys.executable, "-m", "dscc", "--home", str(home), "mcp"],
                         input="\n".join(json.dumps(m) for m in messages) + "\n",
                         capture_output=True, text=True, env=env, timeout=20)
    assert run.returncode == 0, run.stderr
    rows = [json.loads(line) for line in run.stdout.splitlines()]
    assert len(rows) == 2 and rows[-1]["result"]["isError"] is False
    return json.loads(rows[-1]["result"]["content"][0]["text"])


def test_research_handoff_between_real_stdio_processes(tmp_path):
    node = init_node(tmp_path / "node")
    result = session(node.home, "record_research", {"payload": initial_state()})
    handoff = session(node.home, "get_research_handoff", {"state_cid": result["cid"]})
    assert handoff["state"] == initial_state()
    assert handoff["complete_ancestor_closure"] is True
    assert handoff["execution_authorized"] is False


@pytest.mark.parametrize("pointer", ["/cid", "/content_trust"])
def test_source_cannot_reference_unsigned_fetch_metadata(tmp_path, pointer):
    node = init_node(tmp_path / "node")
    raw = node.record(manifest("Dataset", "Fixture", {"value": 1}))
    p = initial_state()
    p["sources"] = [{"cid": raw, "pointer": pointer, "role": "context"}]
    with pytest.raises(ValueError, match="does not resolve"):
        ResearchService(node).record(p)
    assert node.status()["artifacts"] == 1
