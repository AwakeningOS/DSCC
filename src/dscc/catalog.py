"""T007: Disposable, atomically rebuildable FTS5 and provenance-graph catalog index.

The index lives in `index.sqlite3` and is strictly a rebuildable hint layer derived
exclusively from verified immutable signed envelopes in `objects/artifacts/`.
Deleting or corrupting `index.sqlite3` loses zero source records; `rebuild()`
verifies every signed envelope and swaps the rebuilt index atomically so a
failed rebuild never clobbers the prior working generation.
"""
from __future__ import annotations

import contextlib
import os
import re
import sqlite3
import uuid
from pathlib import Path
from typing import Any, Iterator

from .canonical import MAX_OBJECT_BYTES, canonical_bytes, cid_for, parse_json, validate_cid
from .identity import KEY_RE, verify
from .models import KINDS, validate_manifest
from .research import KEY as RESEARCH_KEY, validate_profile, work_fingerprint
from .store import Node, _bounded_file

_TOKEN_RE = re.compile(r"[^\W_]+", re.UNICODE)


def _flatten_strings(value: Any, out: list[str], *, limit: int = 65_536) -> None:
    if sum(len(x) for x in out) >= limit:
        return
    if isinstance(value, str):
        if value.strip():
            out.append(value)
    elif isinstance(value, list):
        for item in value:
            _flatten_strings(item, out, limit=limit)
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str):
                out.append(k)
            _flatten_strings(v, out, limit=limit)


def _safe_fts_query(query: str) -> str:
    """Convert raw user text into safe quoted FTS5 tokens (prevents syntax injection)."""
    tokens = _TOKEN_RE.findall(query)
    if not tokens:
        return ""
    return " AND ".join('"' + tok.replace('"', '""') + '"' for tok in tokens[:32])


class CatalogIndex:
    """Rebuildable full-text + structured + provenance-graph search index."""

    def __init__(self, node: Node):
        self.node = node
        self.path = node.home / "index.sqlite3"

    @contextlib.contextmanager
    def _connect(self, db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
        target = db_path or self.path
        conn = sqlite3.connect(target, timeout=20, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout=20000")
        try:
            yield conn
        finally:
            conn.close()

    @staticmethod
    def _init_schema(conn: sqlite3.Connection) -> bool:
        conn.executescript("""
          CREATE TABLE records (
            cid TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            summary TEXT NOT NULL,
            license TEXT NOT NULL,
            signer TEXT NOT NULL,
            project TEXT,
            research_type TEXT,
            work_fingerprint TEXT,
            data_text TEXT NOT NULL
          );
          CREATE INDEX idx_records_kind ON records(kind);
          CREATE INDEX idx_records_signer ON records(signer);
          CREATE INDEX idx_records_project ON records(project);
          CREATE INDEX idx_records_research_type ON records(research_type);

          CREATE TABLE edges (
            parent_cid TEXT NOT NULL,
            child_cid TEXT NOT NULL,
            PRIMARY KEY (parent_cid, child_cid)
          );
          CREATE INDEX idx_edges_child ON edges(child_cid);

          CREATE TABLE relations (
            source_cid TEXT NOT NULL,
            relation_type TEXT NOT NULL,
            target_cid TEXT NOT NULL,
            rationale TEXT NOT NULL
          );
          CREATE INDEX idx_relations_source ON relations(source_cid);
          CREATE INDEX idx_relations_target ON relations(target_cid);

          CREATE TABLE meta (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
          );
        """)
        fts_enabled = False
        try:
            conn.execute("""
              CREATE VIRTUAL TABLE records_fts USING fts5(
                cid UNINDEXED,
                title,
                summary,
                data_text,
                tokenize='unicode61'
              )
            """)
            fts_enabled = True
        except sqlite3.OperationalError:  # pragma: no cover - SQLite built without FTS5
            fts_enabled = False
        conn.execute("INSERT INTO meta VALUES ('schema', 'dscc.catalog.index/0.1')")
        conn.execute("INSERT INTO meta VALUES ('fts5', ?)", ("1" if fts_enabled else "0",))
        return fts_enabled

    def rebuild(self, *, materialize_missing: bool = True) -> dict[str, Any]:
        """Atomically rebuild `index.sqlite3` solely from verified immutable objects.

        If any object file is corrupted or non-canonical, raises ValueError and
        keeps any previous working index file completely intact.
        """
        if materialize_missing:
            try:
                self.node.materialize_objects()
            except (sqlite3.DatabaseError, OSError):
                # Catalog DB may have been deleted; proceed strictly from objects/.
                pass

        verified_rows: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        for path in sorted(self.node.objects_artifacts_dir.iterdir()):
            if path.name.startswith("."):
                continue
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"non-regular file in artifact object store: {path.name}")
            cid = validate_cid(path.name)
            raw = _bounded_file(path, MAX_OBJECT_BYTES)
            if cid_for(raw) != cid:
                raise ValueError(f"object store artifact CID mismatch: {cid}")
            env = parse_json(raw)
            if canonical_bytes(env) != raw:
                raise ValueError(f"non-canonical object store artifact: {cid}")
            doc = validate_manifest(verify(env, "artifact"))
            verified_rows.append((cid, env, doc))

        tmp = self.node.home / f".index.rebuild.{uuid.uuid4().hex}.sqlite3"
        edge_count = 0
        relation_count = 0
        try:
            with self._connect(tmp) as conn:
                conn.execute("PRAGMA journal_mode=DELETE")
                conn.execute("PRAGMA synchronous=FULL")
                fts_enabled = self._init_schema(conn)
                conn.execute("BEGIN IMMEDIATE")
                for cid, env, doc in verified_rows:
                    project = None
                    research_type = None
                    fp = None
                    research_relations: list[dict[str, Any]] = []
                    if RESEARCH_KEY in doc["data"] and set(doc["data"]) == {RESEARCH_KEY}:
                        try:
                            rp = validate_profile(doc["data"][RESEARCH_KEY])
                            project = rp["project"]
                            research_type = rp["type"]
                            fp = work_fingerprint(rp)
                            research_relations = rp["relations"]
                        except ValueError:
                            pass
                    fragments: list[str] = []
                    _flatten_strings(doc["data"], fragments)
                    data_text = " ".join(fragments)[:65_536]
                    conn.execute(
                        "INSERT INTO records VALUES (?,?,?,?,?,?,?,?,?,?)",
                        (
                            cid, doc["kind"], doc["title"], doc["summary"],
                            doc["license"], env["public_key"], project,
                            research_type, fp, data_text,
                        ),
                    )
                    if fts_enabled:
                        conn.execute(
                            "INSERT INTO records_fts VALUES (?,?,?,?)",
                            (cid, doc["title"], doc["summary"], data_text),
                        )
                    for parent in doc["parents"]:
                        conn.execute("INSERT OR IGNORE INTO edges VALUES (?,?)", (parent, cid))
                        edge_count += 1
                    for rel in research_relations:
                        conn.execute(
                            "INSERT INTO relations VALUES (?,?,?,?)",
                            (cid, rel["type"], rel["target_cid"], rel["rationale"]),
                        )
                        relation_count += 1
                conn.execute("COMMIT")
            try:
                tmp.chmod(0o600)
            except OSError:
                pass
            os.replace(tmp, self.path)
        finally:
            if tmp.exists():
                tmp.unlink()
        return {
            "rebuilt": True,
            "indexed_artifacts": len(verified_rows),
            "edges": edge_count,
            "relations": relation_count,
            "fts5": fts_enabled,
        }

    def _ensure_ready(self) -> None:
        if not self.path.is_file():
            self.rebuild()

    def search(
        self,
        query: str = "",
        *,
        kind: str | None = None,
        project: str | None = None,
        research_type: str | None = None,
        signer: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        if not isinstance(query, str) or len(query) > 500:
            raise ValueError("invalid query")
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid limit")
        if kind is not None and kind not in KINDS:
            raise ValueError("unsupported artifact kind filter")
        if signer is not None and (not isinstance(signer, str) or not KEY_RE.fullmatch(signer)):
            raise ValueError("invalid signer public key filter")
        if project is not None and (not isinstance(project, str) or len(project) > 240):
            raise ValueError("invalid project filter")
        if research_type is not None and (not isinstance(research_type, str) or len(research_type) > 64):
            raise ValueError("invalid research_type filter")

        self._ensure_ready()
        clauses: list[str] = []
        params: list[Any] = []
        if kind is not None:
            clauses.append("r.kind = ?")
            params.append(kind)
        if project is not None:
            clauses.append("r.project = ?")
            params.append(project)
        if research_type is not None:
            clauses.append("r.research_type = ?")
            params.append(research_type)
        if signer is not None:
            clauses.append("r.signer = ?")
            params.append(signer)

        with self._connect() as conn:
            fts_row = conn.execute("SELECT value FROM meta WHERE key='fts5'").fetchone()
            use_fts = bool(fts_row and fts_row["value"] == "1")
            fts_expr = _safe_fts_query(query) if query.strip() else ""

            if fts_expr and use_fts:
                where = (" AND " + " AND ".join(clauses)) if clauses else ""
                sql = f"""
                  SELECT r.cid, r.kind, r.title, r.summary, r.license, r.signer,
                         r.project, r.research_type, r.work_fingerprint
                  FROM records_fts f
                  JOIN records r ON r.cid = f.cid
                  WHERE records_fts MATCH ? {where}
                  ORDER BY bm25(records_fts), r.cid
                  LIMIT ?
                """
                rows = conn.execute(sql, [fts_expr, *params, limit]).fetchall()
            else:
                if query:
                    escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
                    like = f"%{escaped}%"
                    clauses.append(
                        "(r.title LIKE ? ESCAPE '\\' OR r.summary LIKE ? ESCAPE '\\' "
                        "OR r.data_text LIKE ? ESCAPE '\\')"
                    )
                    params.extend([like, like, like])
                where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
                sql = f"""
                  SELECT r.cid, r.kind, r.title, r.summary, r.license, r.signer,
                         r.project, r.research_type, r.work_fingerprint
                  FROM records r
                  {where}
                  ORDER BY r.cid
                  LIMIT ?
                """
                rows = conn.execute(sql, [*params, limit]).fetchall()

        return {
            "hits": [{**dict(row), "index_hint": True} for row in rows],
            "count": len(rows),
            "verified_on_fetch_required": True,
        }

    def neighbors(self, cid: str) -> dict[str, Any]:
        validate_cid(cid)
        self._ensure_ready()
        with self._connect() as conn:
            row = conn.execute("SELECT cid FROM records WHERE cid=?", (cid,)).fetchone()
            if row is None:
                raise KeyError("artifact not found in catalog index")
            parents = [
                r["parent_cid"]
                for r in conn.execute(
                    "SELECT parent_cid FROM edges WHERE child_cid=? ORDER BY parent_cid", (cid,)
                ).fetchall()
            ]
            children = [
                r["child_cid"]
                for r in conn.execute(
                    "SELECT child_cid FROM edges WHERE parent_cid=? ORDER BY child_cid", (cid,)
                ).fetchall()
            ]
            outgoing = [
                dict(r)
                for r in conn.execute(
                    "SELECT relation_type, target_cid, rationale FROM relations "
                    "WHERE source_cid=? ORDER BY relation_type, target_cid",
                    (cid,),
                ).fetchall()
            ]
            incoming = [
                dict(r)
                for r in conn.execute(
                    "SELECT source_cid, relation_type, rationale FROM relations "
                    "WHERE target_cid=? ORDER BY relation_type, source_cid",
                    (cid,),
                ).fetchall()
            ]
        return {
            "cid": cid,
            "parents": parents,
            "children": children,
            "outgoing_relations": outgoing,
            "incoming_relations": incoming,
            "index_hint": True,
        }
