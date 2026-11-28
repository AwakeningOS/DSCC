# DSCC Local Security Threat Model & Audit Status (T009)

This document tracks concrete local security boundaries, audited findings, enforced controls, and residual limits in the current implementation. The original concept-paper threat model remains untouched in `docs/reference/threat_model.md`.

## 1. Security boundaries verified in current code

| Surface | Threat | Enforced control | Regression coverage |
|---|---|---|---|
| Key & token persistence | World-readable creation race (TOCTOU) or symlink swap | Atomic POSIX `O_CREAT \| O_EXCL \| O_NOFOLLOW` with `0o600`; symlink & non-regular file rejection; salted SHA-256 token hashes with constant-time compare | `tests/security/test_adversarial.py` |
| Local IPC (`127.0.0.1`) | Public network exposure, browser CSRF, DNS rebinding, body DoS | Hard bind check (`host == "127.0.0.1"`), unconditional HTTP 403 on `Origin` or `Sec-Fetch-*`, strict `Host` header check, pre-read `Content-Length` cap (`MAX_IPC_BODY_BYTES`) | `tests/test_service.py`, `tests/security/test_adversarial.py` |
| Owner vs model scope | Model client approving/running jobs, exporting bundles, uploading blocks or issuing tokens | Service-layer allowlist (`MODEL_ACTIONS` vs `OWNER_ACTIONS`); HTTP 403 `AuthorizationError` on every owner action with a `model` token; MCP subprocess operates without `--home` key access | `tests/test_service.py`, `tests/security/test_adversarial.py` |
| Artifact & lineage integrity | Tampered SQLite rows, forged parent links, corrupt parent envelope | Canonical JSON + CIDv1/sha2-256 + domain-separated Ed25519 check on every read; `verify_artifact` cryptographically verifies direct parents; `verify_lineage` verifies full ancestor closure | `tests/test_core.py`, `tests/security/test_adversarial.py` |
| Rebuildable catalog & FTS5 | Index loss/corruption, FTS5 query-syntax injection | Immutable signed envelopes under `objects/`; atomic temp-file rebuild fails closed without clobbering prior working index; raw user tokens quoted before FTS5 `MATCH` | `tests/test_research_objects.py`, `tests/security/test_adversarial.py` |
| Large block store & OMC | Concurrent quota bypass, symlink read, manifest size lie, duplicate capability VRAM inflation | Thread + POSIX `flock` serialization around quota/replace; `O_NOFOLLOW` regular-file read; `inspect_model` size check + optional SHA-256 check; duplicate `capability_cid` rejection; pipeline runtime-headroom warning | `tests/test_omc.py`, `tests/security/test_adversarial.py` |

## 2. Explicit non-claims and residual risks

- **Integrity is not scientific truth:** A valid CID and Ed25519 signature prove byte integrity and key possession only.
- **Same-user OS trust boundary:** When an AI agent runs with unrestricted shell access under the same OS user account as the DSCC owner, it can bypass local IPC boundaries directly through the OS filesystem. Separate OS worker accounts and OS keychain storage remain follow-up work.
- **No hostile-code sandbox yet:** Local job execution remains restricted to one trusted deterministic built-in (`dscc.integer_stats.v1`). Arbitrary code execution requires T003 (WASI/OCI isolation).
- **No external event anchoring:** Local event-chain `audit()` verifies retained history consistency but cannot detect tail truncation without an externally anchored head.
- **Cross-platform verification gap:** Current adversarial test run was executed on Linux (Python 3.14.4). Windows CI behavior (especially `fcntl` fallback and ACL permissions) requires Windows runner verification.
