"""Transactional local store, explicit exchange, and owner-approved jobs."""
from __future__ import annotations

import contextlib
import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .blocks import BlockStore
from .canonical import (MAX_BUNDLE_BYTES, MAX_OBJECT_BYTES, canonical_bytes, cid_for,
                        parse_json, validate_cid)
from .identity import KEY_RE, generate_key, load_key, public_hex, sign, verify, write_private_exclusive
from .models import manifest, validate_manifest
from .tools import TOOL_DIGEST, TOOL_ID, integer_stats, validate_values

MAX_RECORDS = 10_000
MAX_JOBS = 10_000
BUNDLE_SCHEMA = "dscc.bundle.seed/0.1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _bounded_file(path: Path, limit: int) -> bytes:
    with path.open("rb") as f:
        raw = f.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("file exceeds size limit")
    return raw


def init_node(home: Path, quota_mb: int = 128, block_quota_gb: int = 16) -> "Node":
    home = home.expanduser().resolve()
    if not 1 <= quota_mb <= 1024 * 1024:
        raise ValueError("quota_mb must be between 1 and 1048576")
    if not 1 <= block_quota_gb <= 1024 * 1024:
        raise ValueError("block_quota_gb must be between 1 and 1048576")
    if (home / "config.json").exists():
        return Node(home)
    if (home / "signing.key").exists() or (home / "catalog.sqlite3").exists():
        raise ValueError("incomplete existing node; refusing to replace identity")
    home.mkdir(parents=True, exist_ok=True, mode=0o700)
    home.chmod(0o700)
    generate_key(home / "signing.key")
    config = {
        "schema": "dscc.node.seed/0.1",
        "storage_quota_bytes": quota_mb * 1024 * 1024,
        "block_quota_bytes": block_quota_gb * 1024 * 1024 * 1024,
    }
    with (home / "config.json").open("x", encoding="utf-8") as f:
        json.dump(config, f, indent=2)
    return Node(home)


class Node:
    def __init__(self, home: Path):
        self.home = home.expanduser().resolve()
        config = parse_json(_bounded_file(self.home / "config.json", 16_384))
        if not isinstance(config, dict) or config.get("schema") != "dscc.node.seed/0.1":
            raise ValueError("unsupported node configuration")
        self.quota = config.get("storage_quota_bytes")
        if type(self.quota) is not int or not 1_048_576 <= self.quota <= 2**40:
            raise ValueError("invalid storage quota")
        self.block_quota = config.get("block_quota_bytes", self.quota)
        if type(self.block_quota) is not int or not 1_048_576 <= self.block_quota <= 2**60:
            raise ValueError("invalid block storage quota")
        self.blocks = BlockStore(self.home, self.block_quota)
        self._local = threading.local()
        self.objects_artifacts_dir = self.home / "objects" / "artifacts"
        self.objects_events_dir = self.home / "objects" / "events"
        for directory in (self.objects_artifacts_dir, self.objects_events_dir):
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            try:
                directory.chmod(0o700)
            except OSError:
                pass
        self.key = load_key(self.home / "signing.key")
        self.public_key = public_hex(self.key)
        self.db = self.home / "catalog.sqlite3"
        with self._connection() as c:
            version = c.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError("unsupported database schema; migration required")
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=FULL")
            c.executescript("""
              CREATE TABLE IF NOT EXISTS artifacts (
                cid TEXT PRIMARY KEY, envelope BLOB NOT NULL,
                kind TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL,
                stored_at TEXT NOT NULL
              );
              CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY, cid TEXT UNIQUE NOT NULL, envelope BLOB NOT NULL
              );
              CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY, spec BLOB NOT NULL, spec_cid TEXT NOT NULL,
                state TEXT NOT NULL CHECK(state IN ('pending','approved','running','succeeded','failed','cancelled')),
                output_cid TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
              );
              PRAGMA user_version=1;
            """)
        try:
            self.db.chmod(0o600)
        except OSError:
            pass

    def _persist_immutable_object(self, directory: Path, name: str, raw: bytes) -> None:
        target = directory / name
        if target.exists():
            if target.is_symlink() or not target.is_file():
                raise ValueError("immutable object path is not a regular file")
            if target.read_bytes() != raw:
                raise ValueError("immutable object content differs on disk")
            return
        tmp = directory / f".{uuid.uuid4().hex}.tmp"
        try:
            write_private_exclusive(tmp, raw)
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()

    @contextlib.contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self.db, timeout=20, isolation_level=None)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA foreign_keys=ON")
        c.execute("PRAGMA busy_timeout=20000")
        try:
            yield c
        finally:
            c.close()

    @contextlib.contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        pending_objects: list[tuple[Path, str, bytes]] = []
        with self._connection() as c:
            c.execute("BEGIN IMMEDIATE")
            self._local.pending_objects = pending_objects
            try:
                yield c
                c.execute("COMMIT")
            except BaseException:
                c.execute("ROLLBACK")
                raise
            finally:
                self._local.pending_objects = None
        for directory, name, raw in pending_objects:
            self._persist_immutable_object(directory, name, raw)

    def _stage_object(self, directory: Path, name: str, raw: bytes) -> None:
        pending = getattr(self._local, "pending_objects", None)
        if pending is not None:
            pending.append((directory, name, raw))
        else:
            self._persist_immutable_object(directory, name, raw)

    def _usage(self, c: sqlite3.Connection) -> int:
        # Logical payload budget, NOT a hard limit on SQLite pages, OS disk or RAM.
        return sum(c.execute(f"SELECT COALESCE(SUM(LENGTH({field})),0) FROM {table}").fetchone()[0]
                   for table, field in (("artifacts", "envelope"), ("events", "envelope"), ("jobs", "spec")))

    def _budget(self, c: sqlite3.Connection, extra: int) -> None:
        if self._usage(c) + extra > self.quota:
            raise ValueError("logical storage quota exceeded")

    def _event(self, c: sqlite3.Connection, name: str, data: dict[str, Any]) -> str:
        previous = c.execute("SELECT seq,cid FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        body = {"schema": "dscc.event.seed/0.1", "seq": previous["seq"] + 1 if previous else 1,
                "previous": previous["cid"] if previous else None, "at": utc_now(),
                "event": name, "data": data}
        encoded = canonical_bytes(sign(body, self.key, "event"))
        self._budget(c, len(encoded))
        cid = cid_for(encoded)
        c.execute("INSERT INTO events VALUES (?,?,?)", (body["seq"], cid, encoded))
        self._stage_object(self.objects_events_dir, f"{body['seq']:012d}-{cid}", encoded)
        return cid

    def _get(self, c: sqlite3.Connection, cid: str) -> dict[str, Any]:
        validate_cid(cid)
        row = c.execute("SELECT envelope FROM artifacts WHERE cid=?", (cid,)).fetchone()
        if row is None:
            raise KeyError("artifact not found")
        raw = bytes(row["envelope"])
        if cid_for(raw) != cid:
            raise ValueError("stored artifact CID mismatch")
        envelope = parse_json(raw)
        if canonical_bytes(envelope) != raw:
            raise ValueError("non-canonical stored artifact")
        validate_manifest(verify(envelope, "artifact"))
        return envelope

    def fetch(self, cid: str) -> dict[str, Any]:
        with self._connection() as c:
            return {"cid": cid, **self._get(c, cid), "content_trust": "untrusted_research_data"}

    def _insert(self, c: sqlite3.Connection, envelope: dict[str, Any]) -> str:
        doc = validate_manifest(verify(envelope, "artifact"))
        raw = canonical_bytes(envelope)
        if len(raw) > MAX_OBJECT_BYTES:
            raise ValueError("signed artifact exceeds block size limit")
        cid = cid_for(raw)
        existing = c.execute("SELECT envelope FROM artifacts WHERE cid=?", (cid,)).fetchone()
        if existing is not None:
            if bytes(existing["envelope"]) != raw:
                raise ValueError("stored content differs for this CID")
            return cid
        if c.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0] >= MAX_RECORDS:
            raise ValueError("artifact count limit reached")
        for parent in doc["parents"]:
            self._get(c, parent)
        self._budget(c, len(raw))
        c.execute("INSERT INTO artifacts VALUES (?,?,?,?,?,?)", (
            cid, raw, doc["kind"], doc["title"], doc["summary"], utc_now()))
        self._stage_object(self.objects_artifacts_dir, cid, raw)
        self._event(c, "artifact.stored", {"cid": cid, "signer": envelope["public_key"]})
        return cid

    def record(self, doc: dict[str, Any]) -> str:
        validate_manifest(doc)
        envelope = sign(doc, self.key, "artifact")
        with self._transaction() as c:
            return self._insert(c, envelope)

    def search(self, query: str = "", limit: int = 20) -> list[dict[str, Any]]:
        if not isinstance(query, str) or len(query) > 500 or type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("invalid query or limit")
        # A rebuildable metadata index. Search hits are verified on fetch.
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        with self._connection() as c:
            rows = c.execute("""SELECT cid,kind,title,summary,stored_at FROM artifacts
              WHERE title LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\'
              ORDER BY stored_at DESC,cid LIMIT ?""", (f"%{escaped}%", f"%{escaped}%", limit)).fetchall()
            return [dict(row) for row in rows]

    def resource_page(self, cursor: str | None = None) -> dict[str, Any]:
        """CID-ordered pagination; not a snapshot across concurrent insertions."""
        if cursor is not None:
            validate_cid(cursor)
        with self._connection() as c:
            rows = c.execute("SELECT cid,kind,title,summary FROM artifacts WHERE cid > ? ORDER BY cid LIMIT 101",
                             (cursor or "",)).fetchall()
            page = {"assets": [dict(row) for row in rows[:100]]}
            if len(rows) > 100:
                page["nextCursor"] = rows[99]["cid"]
            return page

    def status(self) -> dict[str, Any]:
        with self._connection() as c:
            return {
                "version": "0.1.0a1",
                "public_key": self.public_key,
                "artifacts": c.execute("SELECT COUNT(*) FROM artifacts").fetchone()[0],
                "jobs": c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0],
                "logical_bytes": self._usage(c),
                "logical_quota_bytes": self.quota,
                **self.blocks.status(),
                "open_model_commons": {
                    "model_manifests": True,
                    "large_local_blocks": True,
                    "capability_records": True,
                    "inference_planning": True,
                    "distributed_inference_execution": False,
                    "distributed_training_execution": False,
                },
                "p2p": False,
                "gpu_execution": False,
                "arbitrary_code": False,
                "runtime": "trusted-builtin-only",
                "sharing": "explicit-file-export-only",
            }

    def verify_artifact(self, cid: str) -> dict[str, Any]:
        with self._connection() as c:
            e = self._get(c, cid)
            missing = []
            for p in e["body"]["parents"]:
                try:
                    self._get(c, p)
                except KeyError:
                    missing.append(p)
            return {"cid": cid, "content_integrity": True, "signature_valid": True,
                    "signer": e["public_key"], "missing_parents": missing,
                    "scientific_correctness": "not_assessed"}

    def verify_lineage(self, root_cid: str, *, max_records: int = 256) -> dict[str, Any]:
        """Verify an artifact and every transitive parent envelope cryptographically."""
        validate_cid(root_cid)
        todo = [root_cid]
        verified: dict[str, str] = {}
        missing: list[str] = []
        with self._connection() as c:
            while todo:
                cid = todo.pop()
                if cid in verified:
                    continue
                if len(verified) >= max_records:
                    raise ValueError(f"lineage exceeds verification bound of {max_records} records")
                try:
                    env = self._get(c, cid)
                except KeyError:
                    if cid == root_cid:
                        raise
                    if cid not in missing:
                        missing.append(cid)
                    continue
                verified[cid] = env["public_key"]
                todo.extend(env["body"]["parents"])
        return {
            "root_cid": root_cid,
            "verified_count": len(verified),
            "signers": sorted(set(verified.values())),
            "missing_ancestors": sorted(missing),
            "complete_lineage": not missing,
            "scientific_correctness": "not_assessed",
        }

    def materialize_objects(self) -> dict[str, int]:
        """Export any DB-stored immutable envelopes/events missing from objects/."""
        written_artifacts = 0
        written_events = 0
        with self._connection() as c:
            for row in c.execute("SELECT cid, envelope FROM artifacts ORDER BY cid").fetchall():
                cid = row["cid"]
                self._get(c, cid)
                target = self.objects_artifacts_dir / cid
                if not target.exists():
                    self._persist_immutable_object(self.objects_artifacts_dir, cid, bytes(row["envelope"]))
                    written_artifacts += 1
            for row in c.execute("SELECT seq, cid, envelope FROM events ORDER BY seq").fetchall():
                name = f"{row['seq']:012d}-{row['cid']}"
                target = self.objects_events_dir / name
                if not target.exists():
                    self._persist_immutable_object(self.objects_events_dir, name, bytes(row["envelope"]))
                    written_events += 1
        return {"written_artifacts": written_artifacts, "written_events": written_events}

    def rebuild_from_objects(self) -> dict[str, Any]:
        """Rebuild catalog.sqlite3 atomically from verified immutable files in objects/.

        Preserves existing job rows if catalog.sqlite3 is readable, verifies every
        artifact CID/canonical JSON/Ed25519 signature/DAG acyclicity and event chain,
        and leaves the previous database untouched on any failure.
        """
        artifacts: dict[str, tuple[bytes, dict[str, Any]]] = {}
        for path in sorted(self.objects_artifacts_dir.iterdir()):
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
            artifacts[cid] = (raw, doc)

        if len(artifacts) > MAX_RECORDS:
            raise ValueError("artifact count limit reached")

        # Validate parent completeness and DAG acyclicity before replacing catalog DB.
        ordered: list[str] = []
        remaining = dict(artifacts)
        while remaining:
            ready = sorted(
                cid for cid, (_, doc) in remaining.items()
                if all(p in artifacts and p not in remaining for p in doc["parents"])
            )
            if not ready:
                missing_parents = sorted({
                    p for _, (_, doc) in remaining.items()
                    for p in doc["parents"] if p not in artifacts
                })
                if missing_parents:
                    raise ValueError(f"object store missing parent artifacts: {missing_parents[0]}")
                raise ValueError("cyclic artifact dependencies in object store")
            for cid in ready:
                ordered.append(cid)
                remaining.pop(cid)

        events: list[tuple[int, str, bytes]] = []
        previous: str | None = None
        event_files = sorted(
            p for p in self.objects_events_dir.iterdir() if not p.name.startswith(".")
        )
        for expected_seq, path in enumerate(event_files, 1):
            if path.is_symlink() or not path.is_file():
                raise ValueError(f"non-regular file in event object store: {path.name}")
            raw = _bounded_file(path, MAX_OBJECT_BYTES)
            env = parse_json(raw)
            if canonical_bytes(env) != raw:
                raise ValueError("non-canonical event object")
            body = verify(env, "event")
            ev_cid = cid_for(raw)
            if (body.get("seq") != expected_seq or body.get("previous") != previous
                    or env["public_key"] != self.public_key
                    or path.name != f"{expected_seq:012d}-{ev_cid}"):
                raise ValueError("object store event chain verification failed")
            events.append((expected_seq, ev_cid, raw))
            previous = ev_cid

        preserved_jobs: list[tuple[Any, ...]] = []
        if self.db.is_file():
            try:
                with self._connection() as existing_conn:
                    for row in existing_conn.execute(
                        "SELECT id, spec, spec_cid, state, output_cid, error, created_at, updated_at FROM jobs"
                    ).fetchall():
                        preserved_jobs.append(tuple(row))
            except sqlite3.DatabaseError:
                preserved_jobs = []

        tmp_db = self.home / f".catalog.rebuild.{uuid.uuid4().hex}.sqlite3"
        try:
            conn = sqlite3.connect(tmp_db, timeout=20, isolation_level=None)
            try:
                conn.execute("PRAGMA foreign_keys=ON")
                conn.execute("PRAGMA journal_mode=DELETE")
                conn.execute("PRAGMA synchronous=FULL")
                conn.executescript("""
                  CREATE TABLE artifacts (
                    cid TEXT PRIMARY KEY, envelope BLOB NOT NULL,
                    kind TEXT NOT NULL, title TEXT NOT NULL, summary TEXT NOT NULL,
                    stored_at TEXT NOT NULL
                  );
                  CREATE TABLE events (
                    seq INTEGER PRIMARY KEY, cid TEXT UNIQUE NOT NULL, envelope BLOB NOT NULL
                  );
                  CREATE TABLE jobs (
                    id TEXT PRIMARY KEY, spec BLOB NOT NULL, spec_cid TEXT NOT NULL,
                    state TEXT NOT NULL CHECK(state IN ('pending','approved','running','succeeded','failed','cancelled')),
                    output_cid TEXT, error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
                  );
                  PRAGMA user_version=1;
                """)
                conn.execute("BEGIN IMMEDIATE")
                now = utc_now()
                for cid in ordered:
                    raw, doc = artifacts[cid]
                    conn.execute(
                        "INSERT INTO artifacts VALUES (?,?,?,?,?,?)",
                        (cid, raw, doc["kind"], doc["title"], doc["summary"], now),
                    )
                for seq, ev_cid, raw in events:
                    conn.execute("INSERT INTO events VALUES (?,?,?)", (seq, ev_cid, raw))
                for job_row in preserved_jobs:
                    conn.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)", job_row)
                conn.execute("COMMIT")
            finally:
                conn.close()
            try:
                tmp_db.chmod(0o600)
            except OSError:
                pass
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(self.db) + suffix)
                if sidecar.exists():
                    try:
                        sidecar.unlink()
                    except OSError:
                        pass
            os.replace(tmp_db, self.db)
            with self._connection() as c:
                c.execute("PRAGMA journal_mode=WAL")
                c.execute("PRAGMA synchronous=FULL")
        finally:
            if tmp_db.exists():
                tmp_db.unlink()
        return {
            "rebuilt": True,
            "artifacts": len(ordered),
            "events": len(events),
            "preserved_jobs": len(preserved_jobs),
            "event_head": previous,
        }

    def audit(self) -> dict[str, Any]:
        with self._connection() as c:
            rows = c.execute("SELECT * FROM events ORDER BY seq").fetchall()
            previous = None
            for expected, row in enumerate(rows, 1):
                raw = bytes(row["envelope"])
                env = parse_json(raw)
                body = verify(env, "event")
                if (row["seq"] != expected or body.get("seq") != expected
                        or body.get("previous") != previous or cid_for(raw) != row["cid"]
                        or env["public_key"] != self.public_key or canonical_bytes(env) != raw):
                    raise ValueError("local event chain verification failed")
                previous = row["cid"]
            return {"valid": True, "events": len(rows), "head": previous,
                    "externally_anchored": False, "tail_deletion_detection": False}

    def export_bundle(self, root_cid: str) -> dict[str, Any]:
        validate_cid(root_cid)
        # Explicitly exports the selected record AND its ancestor closure.
        todo, seen = [root_cid], {}
        with self._connection() as c:
            while todo:
                cid = todo.pop()
                if cid in seen:
                    continue
                if len(seen) >= 256:
                    raise ValueError("bundle ancestor closure exceeds 256 records")
                e = self._get(c, cid)
                seen[cid] = {"cid": cid, "envelope": e}
                todo.extend(e["body"]["parents"])
        bundle = {"schema": BUNDLE_SCHEMA, "root": root_cid,
                  "artifacts": [seen[cid] for cid in sorted(seen)]}
        if len(canonical_bytes(bundle)) > MAX_BUNDLE_BYTES:
            raise ValueError("bundle exceeds size limit")
        return bundle

    def import_bundle(self, bundle: Any, trusted_keys: set[str]) -> str:
        if (not isinstance(bundle, dict) or set(bundle) != {"schema", "root", "artifacts"}
                or bundle["schema"] != BUNDLE_SCHEMA):
            raise ValueError("unsupported bundle schema")
        if len(canonical_bytes(bundle)) > MAX_BUNDLE_BYTES:
            raise ValueError("bundle exceeds size limit")
        validate_cid(bundle["root"])
        if any(not isinstance(k, str) or not KEY_RE.fullmatch(k) for k in trusted_keys):
            raise ValueError("invalid trusted signing key")
        items = bundle["artifacts"]
        if not isinstance(items, list) or not 1 <= len(items) <= 256:
            raise ValueError("invalid bundle record count")
        pending: dict[str, dict[str, Any]] = {}
        for item in items:
            if not isinstance(item, dict) or set(item) != {"cid", "envelope"}:
                raise ValueError("invalid bundle item")
            cid = validate_cid(item["cid"])
            env = item["envelope"]
            validate_manifest(verify(env, "artifact"))
            if env["public_key"] not in trusted_keys | {self.public_key}:
                raise ValueError("untrusted signer; owner must explicitly trust the key")
            if cid_for(canonical_bytes(env)) != cid:
                raise ValueError("bundle CID mismatch")
            if cid in pending:
                raise ValueError("duplicate bundle CID")
            pending[cid] = env
        if bundle["root"] not in pending:
            raise ValueError("bundle root is missing")
        # Accept exactly the root closure; no concealed unrelated extra records.
        closure, todo = set(), [bundle["root"]]
        while todo:
            cid = todo.pop()
            if cid in closure:
                continue
            if cid not in pending:
                raise ValueError("bundle is not a complete ancestor closure")
            closure.add(cid)
            todo.extend(pending[cid]["body"]["parents"])
        if closure != set(pending):
            raise ValueError("bundle contains unrelated records")
        with self._transaction() as c:
            while pending:
                ready = [cid for cid, env in pending.items()
                         if all(p not in pending for p in env["body"]["parents"])]
                if not ready:
                    raise ValueError("cyclic bundle dependencies")
                for cid in ready:
                    self._insert(c, pending.pop(cid))
        return bundle["root"]

    def submit_job(self, input_cid: str, tool: str = TOOL_ID) -> dict[str, Any]:
        validate_cid(input_cid)
        if tool != TOOL_ID:
            raise ValueError("tool is not in the installed built-in allowlist")
        with self._transaction() as c:
            doc = self._get(c, input_cid)["body"]
            if doc["kind"] != "Dataset":
                raise ValueError("job input must be a Dataset artifact")
            validate_values(doc["data"])  # Validate shape/range before approval, without computing the result.
            if c.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] >= MAX_JOBS:
                raise ValueError("job count limit reached")
            spec = {"schema": "dscc.job.seed/0.1", "input_cid": input_cid,
                    "tool": tool, "tool_digest": TOOL_DIGEST}
            encoded = canonical_bytes(spec)
            self._budget(c, len(encoded))
            job_id, now = str(uuid.uuid4()), utc_now()
            c.execute("INSERT INTO jobs VALUES (?,?,?,?,?,?,?,?)", (
                job_id, encoded, cid_for(encoded), "pending", None, None, now, now))
            self._event(c, "job.submitted", {"job_id": job_id, "spec_cid": cid_for(encoded)})
        return self.job_status(job_id)

    def _job(self, c: sqlite3.Connection, job_id: str) -> sqlite3.Row:
        try:
            if str(uuid.UUID(job_id)) != job_id:
                raise ValueError("non-canonical job id")
        except (ValueError, AttributeError, TypeError) as exc:
            raise ValueError("invalid job id") from exc
        row = c.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()
        if row is None:
            raise KeyError("job not found")
        raw = bytes(row["spec"])
        if cid_for(raw) != row["spec_cid"]:
            raise ValueError("job specification integrity failure")
        spec = parse_json(raw)
        if (canonical_bytes(spec) != raw or spec.get("tool") != TOOL_ID
                or spec.get("tool_digest") != TOOL_DIGEST):
            raise ValueError("job tool contract changed")
        return row

    def job_status(self, job_id: str) -> dict[str, Any]:
        with self._connection() as c:
            row = dict(self._job(c, job_id))
            row["spec"] = parse_json(bytes(row["spec"]))
            return row

    def list_jobs(self, *, state: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        allowed_states = {"pending", "approved", "running", "succeeded", "failed", "cancelled"}
        if state is not None and state not in allowed_states:
            raise ValueError("invalid job state filter")
        if type(limit) is not int or not 1 <= limit <= 1000:
            raise ValueError("invalid limit")
        with self._connection() as c:
            if state is None:
                rows = c.execute(
                    "SELECT id FROM jobs ORDER BY created_at DESC, id LIMIT ?", (limit,)
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT id FROM jobs WHERE state=? ORDER BY created_at DESC, id LIMIT ?",
                    (state, limit),
                ).fetchall()
            result = []
            for r in rows:
                row = dict(self._job(c, r["id"]))
                row["spec"] = parse_json(bytes(row["spec"]))
                result.append(row)
            return result

    def orphaned_running_jobs(self) -> list[dict[str, Any]]:
        """Explicitly report jobs left in 'running' state for owner crash recovery."""
        return self.list_jobs(state="running")

    def _transition(self, job_id: str, allowed: tuple[str, ...], target: str) -> None:
        with self._transaction() as c:
            row = self._job(c, job_id)
            if row["state"] not in allowed:
                raise ValueError(f"cannot transition job from {row['state']} to {target}")
            c.execute("UPDATE jobs SET state=?,updated_at=? WHERE id=?", (target, utc_now(), job_id))
            self._event(c, f"job.{target}", {"job_id": job_id})

    def approve_job(self, job_id: str) -> dict[str, Any]:
        self._transition(job_id, ("pending",), "approved")
        return self.job_status(job_id)

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        self._transition(job_id, ("pending", "approved"), "cancelled")
        return self.job_status(job_id)

    def recover_job(self, job_id: str) -> dict[str, Any]:
        # Owner action after confirming no worker still owns this local job.
        self._transition(job_id, ("running",), "failed")
        return self.job_status(job_id)

    def run_job(self, job_id: str) -> dict[str, Any]:
        self._transition(job_id, ("approved",), "running")
        try:
            spec = self.job_status(job_id)["spec"]
            source = self.fetch(spec["input_cid"])["body"]
            result = integer_stats(source["data"])
            output = manifest("ExperimentRun", f"Integer analysis: {source['title']}"[:240], {
                "tool": TOOL_ID, "tool_digest": TOOL_DIGEST, "input_cid": spec["input_cid"],
                "result": result, "execution": "local-trusted-builtin",
                "independent_scientific_verification": False,
            }, summary="Deterministic count, sum, minimum and maximum of a bounded integer dataset.",
               parents=[spec["input_cid"]])
            with self._transaction() as c:
                row = self._job(c, job_id)
                if row["state"] != "running":
                    raise ValueError("job was changed before result commit")
                out_cid = self._insert(c, sign(output, self.key, "artifact"))
                c.execute("UPDATE jobs SET state='succeeded',output_cid=?,updated_at=? WHERE id=?",
                          (out_cid, utc_now(), job_id))
                self._event(c, "job.succeeded", {"job_id": job_id, "output_cid": out_cid})
        except Exception as exc:
            try:
                with self._transaction() as c:
                    row = self._job(c, job_id)
                    if row["state"] == "running":
                        # Bounded error category, without dumping arbitrary inputs or file contents.
                        c.execute("UPDATE jobs SET state='failed',error=?,updated_at=? WHERE id=?",
                                  (type(exc).__name__, utc_now(), job_id))
                        self._event(c, "job.failed", {"job_id": job_id, "error": type(exc).__name__})
            except Exception:
                # If storage is exhausted, restore capacity before owner recovery can commit.
                pass
            raise
        return self.job_status(job_id)
