# Implementation status

Software version: **0.0.1**, development foundation. This is separate from concept-paper version 0.1.

## Implemented

The Python package offers local node initialization, Ed25519 signing, small content-addressed research records, parent-linked provenance, transactional persistence, keyword search, explicit trusted-key bundle exchange and a signed local event chain. One bounded installed integer-analysis function demonstrates owner approval, execution, a persisted result and reuse from another node directory. The MCP stdio adapter exposes eight tools and artifact resources. It has protocol/subprocess tests, but is a small subset implementation.

The source tree includes an English README, Japanese product design and start guide, source-paper references, protocol/schema contracts, ADRs, a multi-agent contribution process, nine dependency-linked development tasks, GitHub issue/PR templates, a CI workflow and owner-run publishing helpers. The public repository is https://github.com/AwakeningOS/DSCC .

## Not yet implemented or established

| Area | Current boundary | Next task |
|---|---|---|
| Desktop app | CLI/MCP core only; no native UI or installer | T001 / T004 |
| Host integration | Configuration fragments and stdio tests; actual LM Studio/Codex hosts untested | T002 |
| P2P | Explicit file-bundle exchange; no peers, DHT, relay, NAT traversal, IPFS daemon or remote scheduling | T005 |
| Scientific runtime | One trusted built-in, no arbitrary-code execution or WASI/OCI isolation | T003 |
| GPU | No GPU worker or VRAM sharing | T006 |
| Research objects | Versioned small-record seed; full original schemas/RO-Crate/CWL mapping pending | T007 |
| Shared worlds | Object label only; no simulator/executable world integrated | T008 |
| Security | Local defensive checks; no independent audit or hostile-network certification | T009 |
| Economic layer | No cash, transferable credits or resource marketplace | Later architecture work |
| Self-improvement | Research-history storage possible; no unattended model training or propagation | Later explicitly authorized workflows |

`reports/validation.md` and machine-readable reports describe only commands actually run. A committed CI workflow is not evidence of a successful GitHub Actions run; consult the Actions results for the relevant commit. Passing local tests is not a security proof or a performance benchmark.

## Useful first collaboration

T001 separates the owner-controlled service from adapters. T002 verifies SDK-backed MCP behavior with actual applications. T003 builds the first truly isolated scientific runtime. T005 adds deliberate peer invitations and transport. Each is a separate implementation lane with a documented interface. T009 can independently review them. A task claim/PR coordinates agents; nothing in this repository starts agents on its own.
