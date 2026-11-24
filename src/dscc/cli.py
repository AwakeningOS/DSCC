"""Owner CLI. MCP does not expose approve/run/export/import or block-upload operations."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .adapters import export_prov_json, export_rocrate_dir, paper_to_seed
from .canonical import MAX_BUNDLE_BYTES, MAX_OBJECT_BYTES, canonical_bytes, parse_json
from .catalog import CatalogIndex
from .cooperation import episode_history, record_step
from .demo import run_demo
from .ipc import LocalIPCServer, LocalServiceClient
from .mcp_server import MCPServer
from .omc_service import OpenModelCommons
from .research import ResearchService
from .service import TokenStore
from .store import Node, _bounded_file, init_node


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="dscc",
        description="DSCC local research and Open Model Commons foundation",
    )
    p.add_argument("--home", type=Path, default=Path(os.environ.get("DSCC_HOME", "~/.dscc")))
    s = p.add_subparsers(dest="command", required=True)

    i = s.add_parser("init")
    i.add_argument("--quota-mb", type=int, default=128)
    i.add_argument("--block-quota-gb", type=int, default=16)

    r = s.add_parser("record")
    r.add_argument("--file", type=Path, required=True)

    q = s.add_parser("search")
    q.add_argument("query", nargs="?", default="")
    q.add_argument("--limit", type=int, default=20)

    for name in ("fetch", "verify", "verify-lineage"):
        x = s.add_parser(name)
        x.add_argument("cid")

    for name in ("status", "audit", "demo", "catalog-rebuild", "token-list"):
        s.add_parser(name)

    m = s.add_parser("mcp", help="Run stdio MCP server (local node or authenticated local IPC service)")
    m.add_argument("--service-url", help="Connect to an authenticated local IPC service (http://127.0.0.1:<port>)")
    m.add_argument("--token-env", default="DSCC_TOKEN", help="Environment variable holding the bearer token")

    sv = s.add_parser("serve", help="Run owner-controlled authenticated local IPC service on 127.0.0.1 only")
    sv.add_argument("--port", type=int, default=0)

    ti = s.add_parser("token-issue", help="Owner-only: issue a scoped bearer token (owner or model)")
    ti.add_argument("--scope", choices=("owner", "model"), required=True)
    ti.add_argument("--label", default="")

    tr = s.add_parser("token-revoke", help="Owner-only: revoke an issued bearer token by token_id")
    tr.add_argument("token_id")

    cs = s.add_parser("catalog-search", help="Search the rebuildable FTS5 and structured metadata index")
    cs.add_argument("query", nargs="?", default="")
    cs.add_argument("--kind")
    cs.add_argument("--project")
    cs.add_argument("--research-type")
    cs.add_argument("--signer")
    cs.add_argument("--limit", type=int, default=20)

    cn = s.add_parser("catalog-neighbors", help="Inspect parents, children and research relations in the index")
    cn.add_argument("cid")

    ep = s.add_parser("export-prov", help="Export an artifact closure as W3C PROV-JSON")
    ep.add_argument("cid")
    ep.add_argument("--out", type=Path)

    er = s.add_parser("export-rocrate", help="Export an artifact closure as an RO-Crate 1.1 directory")
    er.add_argument("cid")
    er.add_argument("--out-dir", type=Path, required=True)

    ip = s.add_parser("import-paper", help="Record a concept-paper Artifact manifest as a DSCC seed record")
    ip.add_argument("--file", type=Path, required=True)

    cr = s.add_parser("cooperation-record", help="Record a local R-HS cooperation step (no external messaging)")
    cr.add_argument("--file", type=Path, required=True)

    ch = s.add_parser("cooperation-history", help="Inspect a local R-HS cooperation episode chain")
    ch.add_argument("head_cid")
    ch.add_argument("--max-steps", type=int, default=64)

    j = s.add_parser("submit-job")
    j.add_argument("--input-cid", required=True)

    for name in ("job-status", "approve-job", "run-job", "cancel-job", "recover-job"):
        x = s.add_parser(name)
        x.add_argument("job_id")

    e = s.add_parser("export", help="Export selected artifact and all ancestors; inspect before sharing")
    e.add_argument("cid")
    e.add_argument("--out", type=Path, required=True)

    i = s.add_parser("import", help="Import data without executing it; explicit trusted signer keys required")
    i.add_argument("--file", type=Path, required=True)
    i.add_argument("--trust-key", action="append", default=[])

    b = s.add_parser("block-add", help="Owner-only import of a large immutable local block")
    b.add_argument("--file", type=Path, required=True)
    b = s.add_parser("block-verify")
    b.add_argument("cid")

    for name in ("model-record", "capability-record", "training-record", "research-record"):
        x = s.add_parser(name)
        x.add_argument("--file", type=Path, required=True)
        x.add_argument("--license", default="NOASSERTION")

    x = s.add_parser("research-handoff", help="Read an explicit research state and its verified ancestors")
    x.add_argument("state_cid")

    x = s.add_parser("model-inspect")
    x.add_argument("cid")

    x = s.add_parser("plan-inference")
    x.add_argument("--model-cid", required=True)
    x.add_argument("--capability-cid", action="append", required=True)
    x.add_argument("--precision")

    return p


def _profile(path: Path) -> dict:
    value = parse_json(_bounded_file(path, MAX_OBJECT_BYTES))
    if not isinstance(value, dict):
        raise ValueError("profile file must contain a JSON object")
    return value


def main(argv: list[str] | None = None) -> int:
    a = parser().parse_args(argv)
    try:
        if a.command == "init":
            result = init_node(a.home, a.quota_mb, a.block_quota_gb).status()
        elif a.command == "demo":
            result = run_demo()
        elif a.command == "mcp" and a.service_url:
            token = os.environ.get(a.token_env, "")
            if not token:
                raise ValueError(f"bearer token environment variable '{a.token_env}' is empty")
            MCPServer(LocalServiceClient(a.service_url, token)).serve()
            return 0
        else:
            node = Node(a.home)
            omc = OpenModelCommons(node)
            if a.command == "mcp":
                MCPServer(node).serve()
                return 0
            if a.command == "serve":
                server = LocalIPCServer(node, host="127.0.0.1", port=a.port)
                print(json.dumps({
                    "listening": server.url,
                    "public_key": node.public_key,
                    "loopback_only": True,
                }, ensure_ascii=False), flush=True)
                server.serve_forever()
                return 0
            if a.command == "token-issue":
                result = TokenStore(node.home).issue(a.scope, label=a.label)
            elif a.command == "token-revoke":
                result = TokenStore(node.home).revoke(a.token_id)
            elif a.command == "token-list":
                result = {"tokens": TokenStore(node.home).list_metadata()}
            elif a.command == "record":
                result = {"cid": node.record(_profile(a.file))}
            elif a.command == "search":
                result = node.search(a.query, a.limit)
            elif a.command == "fetch":
                result = node.fetch(a.cid)
            elif a.command == "verify":
                result = node.verify_artifact(a.cid)
            elif a.command == "verify-lineage":
                result = node.verify_lineage(a.cid)
            elif a.command == "catalog-rebuild":
                result = {
                    "database": node.rebuild_from_objects(),
                    "search_index": CatalogIndex(node).rebuild(),
                }
            elif a.command == "catalog-search":
                result = CatalogIndex(node).search(
                    query=a.query, kind=a.kind, project=a.project,
                    research_type=a.research_type, signer=a.signer, limit=a.limit,
                )
            elif a.command == "catalog-neighbors":
                result = CatalogIndex(node).neighbors(a.cid)
            elif a.command == "export-prov":
                prov = export_prov_json(node, a.cid)
                if a.out is not None:
                    with a.out.open("xb") as target:
                        target.write((json.dumps(prov, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
                    result = {"exported": str(a.out), "root_cid": a.cid}
                else:
                    result = prov
            elif a.command == "export-rocrate":
                result = export_rocrate_dir(node, a.cid, a.out_dir)
            elif a.command == "import-paper":
                seed_doc = paper_to_seed(_profile(a.file))
                result = {"cid": node.record(seed_doc), "kind": seed_doc["kind"], "executed": False}
            elif a.command == "cooperation-record":
                payload = _profile(a.file)
                if not set(payload) == {"project", "contributor", "step"}:
                    raise ValueError("cooperation input must contain project, contributor and step")
                result = record_step(
                    node,
                    project=payload["project"],
                    contributor=payload["contributor"],
                    step=payload["step"],
                )
            elif a.command == "cooperation-history":
                result = {"steps": episode_history(node, a.head_cid, max_steps=a.max_steps)}
            elif a.command == "status":
                result = node.status()
            elif a.command == "audit":
                result = node.audit()
            elif a.command == "submit-job":
                result = node.submit_job(a.input_cid)
            elif a.command == "block-add":
                result = omc.add_block(a.file)
            elif a.command == "block-verify":
                result = omc.verify_block(a.cid)
            elif a.command == "model-record":
                result = omc.record_model(_profile(a.file), license=a.license)
            elif a.command == "capability-record":
                result = omc.record_capability(_profile(a.file), license=a.license)
            elif a.command == "training-record":
                result = omc.record_training_run(_profile(a.file), license=a.license)
            elif a.command == "research-record":
                result = ResearchService(node).record(_profile(a.file), license=a.license)
            elif a.command == "research-handoff":
                result = ResearchService(node).handoff(a.state_cid)
            elif a.command == "model-inspect":
                result = omc.inspect_model(a.cid)
            elif a.command == "plan-inference":
                result = omc.plan_inference(
                    a.model_cid, a.capability_cid, precision=a.precision
                )
            elif a.command == "export":
                bundle = node.export_bundle(a.cid)
                with a.out.open("xb") as target:
                    target.write(canonical_bytes(bundle))
                result = {
                    "exported": str(a.out),
                    "artifacts": len(bundle["artifacts"]),
                    "warning": (
                        "Includes the selected artifact and its complete ancestor closure. "
                        "Large OMC blocks are referenced by CID and are not embedded in this seed bundle."
                    ),
                }
            elif a.command == "import":
                bundle = parse_json(
                    _bounded_file(a.file, MAX_BUNDLE_BYTES), max_bytes=MAX_BUNDLE_BYTES
                )
                result = {"cid": node.import_bundle(bundle, set(a.trust_key))}
            else:
                method = {
                    "job-status": node.job_status,
                    "approve-job": node.approve_job,
                    "run-job": node.run_job,
                    "cancel-job": node.cancel_job,
                    "recover-job": node.recover_job,
                }[a.command]
                result = method(a.job_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as exc:
        print(f"DSCC: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
