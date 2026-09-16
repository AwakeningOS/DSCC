"""Owner CLI. MCP does not expose approve/run/export/import operations."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .canonical import MAX_BUNDLE_BYTES, MAX_OBJECT_BYTES, canonical_bytes, parse_json
from .demo import run_demo
from .mcp_server import MCPServer
from .store import Node, _bounded_file, init_node


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="dscc", description="DSCC local research foundation")
    p.add_argument("--home", type=Path, default=Path(os.environ.get("DSCC_HOME", "~/.dscc")))
    s = p.add_subparsers(dest="command", required=True)
    i = s.add_parser("init"); i.add_argument("--quota-mb", type=int, default=128)
    r = s.add_parser("record"); r.add_argument("--file", type=Path, required=True)
    q = s.add_parser("search"); q.add_argument("query", nargs="?", default=""); q.add_argument("--limit", type=int, default=20)
    for name in ("fetch", "verify"):
        x = s.add_parser(name); x.add_argument("cid")
    for name in ("status", "audit", "mcp", "demo"):
        s.add_parser(name)
    j = s.add_parser("submit-job"); j.add_argument("--input-cid", required=True)
    for name in ("job-status", "approve-job", "run-job", "cancel-job", "recover-job"):
        x = s.add_parser(name); x.add_argument("job_id")
    e = s.add_parser("export", help="Export selected artifact and all ancestors; inspect before sharing")
    e.add_argument("cid"); e.add_argument("--out", type=Path, required=True)
    i = s.add_parser("import", help="Import data without executing it; explicit trusted signer keys required")
    i.add_argument("--file", type=Path, required=True)
    i.add_argument("--trust-key", action="append", default=[])
    return p


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    try:
        if a.command == "init":
            result = init_node(a.home, a.quota_mb).status()
        elif a.command == "demo":
            result = run_demo()
        else:
            node = Node(a.home)
            if a.command == "mcp":
                MCPServer(node).serve()
                return 0
            if a.command == "record":
                result = {"cid": node.record(parse_json(_bounded_file(a.file, MAX_OBJECT_BYTES)))}
            elif a.command == "search":
                result = node.search(a.query, a.limit)
            elif a.command == "fetch":
                result = node.fetch(a.cid)
            elif a.command == "verify":
                result = node.verify_artifact(a.cid)
            elif a.command == "status":
                result = node.status()
            elif a.command == "audit":
                result = node.audit()
            elif a.command == "submit-job":
                result = node.submit_job(a.input_cid)
            elif a.command == "export":
                bundle = node.export_bundle(a.cid)
                with a.out.open("xb") as f:
                    f.write(canonical_bytes(bundle))
                result = {"exported": str(a.out), "artifacts": len(bundle["artifacts"]),
                          "warning": "Includes the selected artifact and its complete ancestor closure."}
            elif a.command == "import":
                bundle = parse_json(_bounded_file(a.file, MAX_BUNDLE_BYTES), max_bytes=MAX_BUNDLE_BYTES)
                result = {"cid": node.import_bundle(bundle, set(a.trust_key))}
            else:
                method = {"job-status": node.job_status, "approve-job": node.approve_job,
                          "run-job": node.run_job, "cancel-job": node.cancel_job,
                          "recover-job": node.recover_job}[a.command]
                result = method(a.job_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"DSCC: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
