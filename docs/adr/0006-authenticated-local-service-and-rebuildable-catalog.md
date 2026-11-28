# ADR-0006 — Authenticated local service, immutable object separation, and core security hardening

Status: adopted on branch `feat/t001-t007-t009-hardening`.

## Context

In the M0 seed (`0.1.0a1`), three structural gaps blocked progression toward daily local use (M1) and later distributed execution:

1. **Direct key/DB access in MCP (T001):** MCP adapters opened `Node(home)` directly, loading `signing.key` and `catalog.sqlite3` into the model-facing process. Separation between owner authority and model requests existed only by omitting tools from the MCP surface.
2. **Conflated source bytes and index DB (T007):** `docs/ARCHITECTURE.ja.md` specifies that the catalog is a disposable, rebuildable index rather than the canonical source, yet `catalog.sqlite3` was the sole persistence location for signed envelopes. Deleting `catalog.sqlite3` permanently destroyed all artifacts and events.
3. **Audited implementation defects (T009):**
   - `generate_key` and temporary block writes created files before calling `chmod(0o600)` (TOCTOU race window).
   - Concurrent `BlockStore` writes raced on quota accounting.
   - `verify_artifact` checked direct parent existence (`SELECT 1`) without cryptographically verifying parent envelopes.
   - `OpenModelCommons.inspect_model` checked only local file presence without verifying declared byte lengths or optional SHA-256 digests.
   - `plan_inference` did not reject duplicate `capability_cid` inputs (allowing aggregate VRAM inflation) and did not warn when selected pipeline devices had less aggregate memory than declared `minimum_memory_bytes`.

## Decision

1. **Preserve all existing signed bytes, CIDv1 identifiers, signature domains, schemas and 15 MCP tool contracts unchanged.**
2. **Authenticated local service and loopback IPC (T001):**
   - Introduce `src/dscc/service.py` (`TokenStore`, `LocalService`) enforcing scoped bearer tokens (`owner` vs `model`) hashed with per-token random salt and verified in constant time. Plaintext tokens are never persisted.
   - Introduce `src/dscc/ipc.py` (`LocalIPCServer`, `LocalServiceClient`) using Python standard library HTTP/1.1 strictly bound to `127.0.0.1` (refusing any non-loopback host), rejecting requests with `Origin` or `Sec-Fetch-*` headers, enforcing strict `Host` matching (`127.0.0.1:<port>` / `localhost:<port>`), and bounding body sizes before reading.
   - Allow `MCPServer` and `dscc mcp --service-url` (reading the token from an environment variable, never CLI argv) to operate purely over `LocalServiceClient` without touching `signing.key` or `catalog.sqlite3`.
   - Explicitly surface orphaned `running` jobs on service startup without silently auto-failing or re-running them.
3. **Immutable object store, rebuildable FTS5/graph index, and research-object adapters (T007):**
   - Persist signed canonical artifact envelopes under `objects/artifacts/<cid>` and signed events under `objects/events/<seq>-<cid>` after SQLite transaction commits (thread-local staging avoids corrupting files on rollback).
   - Provide `Node.rebuild_from_objects()` and `CatalogIndex` (`src/dscc/catalog.py`, `index.sqlite3`) with atomic temp-file rebuilds, FTS5 full-text search (safe token quoting), structured filters and parent/child/relation graph lookups. A corrupted object fails closed and preserves any prior working index generation.
   - Provide `src/dscc/adapters/paper.py` (concept-paper `dscc_artifact.schema.json` <-> seed lossless round-trip preserving `Claim` vs `ExperimentRun` distinction) and `src/dscc/adapters/export.py` (W3C PROV-JSON and RO-Crate 1.1 exporters leaving signed envelope bytes untouched).
4. **Core hardening (T009):**
   - Atomic `0o600` exclusive file creation on POSIX (`os.open(..., 0o600)` + `O_NOFOLLOW`), SQLite WAL mode, cross-thread/process block quota lock, cryptographic parent verification in `verify_artifact` and `verify_lineage`, OMC block size/digest inspection and duplicate capability rejection.

## Consequences and remaining limits

- Existing nodes without `objects/` remain compatible and can populate immutable object files via `materialize_objects()`.
- **Non-goals / residual limits:** Loopback IPC under the same OS user is a capability boundary for well-behaved clients, **not** an OS sandbox against a compromised process running as the same OS user with unrestricted filesystem access. Separate OS user accounts, OS keychain integration, official MCP SDK migration (T002), WASI sandboxing (T003), real P2P networking (T005), GPU execution (T006/T011) and Windows CI verification remain separate work.
