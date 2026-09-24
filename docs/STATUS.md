# Implementation status

Software version: **0.1.0a1**, development foundation. This is separate from concept-paper version 0.1.

## Implemented

The Python package offers local node initialization, Ed25519 signing, small content-addressed research records, parent-linked provenance, transactional persistence, keyword search, explicit trusted-key bundle exchange and a signed local event chain. One bounded installed integer-analysis function demonstrates owner approval, execution, a persisted result and reuse from another node directory. The Open Model Commons foundation adds a separate CID-addressed local large-block store, versioned model/capability/training-run profiles, local model-completeness inspection and a non-executing heterogeneous inference placement planner. The MCP stdio adapter exposes fifteen tools and artifact resources. It has protocol/subprocess tests, but remains a local subset implementation.

T012's local contract lane adds nine versioned research profiles, signed-source CID/JSON Pointer checks, explicit-state ancestor handoff, declared contradiction/supersession links, exact repeated-work candidates, and CLI/MCP adapters. Original records and types remain available across local node/process handoff. See [Research handoff](RESEARCH_HANDOFF.md) and ADR-0005. Synthetic contract tests are not a real multi-provider research-quality experiment.

The source tree includes an English README, Japanese product design and start guide, source-paper references, protocol/schema contracts, ADRs, a multi-agent contribution process, twelve dependency-linked development tasks, GitHub issue/PR templates, a CI workflow and owner-run publishing helpers. The public repository is https://github.com/AwakeningOS/DSCC .

## Not yet implemented or established

| Area | Current boundary | Next task |
|---|---|---|
| Desktop app | CLI/MCP core only; no native UI or installer | T001 / T004 |
| Host integration | Configuration fragments and stdio tests; actual LM Studio/Codex hosts untested | T002 |
| P2P | Explicit file-bundle exchange; no peers, DHT, relay, NAT traversal, IPFS daemon or remote scheduling | T005 |
| Scientific runtime | One trusted built-in, no arbitrary-code execution or WASI/OCI isolation | T003 |
| GPU | Capability records and planning only; no GPU discovery, allocation, model execution or VRAM sharing | T006 / T011 |
| Research objects | Versioned small-record seed and T012 profiles; full original schemas/RO-Crate/CWL mapping pending | T007 |
| Shared worlds | Object label only; no simulator/executable world integrated | T008 |
| Security | Local defensive checks; no independent audit or hostile-network certification | T009 |
| Economic layer | No cash, transferable credits or resource marketplace | Later architecture work |
| Open Model Commons execution | Model/block/capability/training metadata and planning only; no distributed inference or training | T011 |
| Distributed AI Research Laboratory | Local research-state profiles/handoff implemented; real cross-model research-quality experiment, multi-agent orchestration and continuous research loop pending | T012 |
| Self-improvement | Research-history storage possible; no unattended model training or repeated autonomous model-development loop | T012 / later execution lanes |

`reports/validation.md` and `reports/omc_foundation_validation.md` describe their historical commands. Subsequent PR/Actions results supply commit-specific validation; older test counts are not current-suite claims. A committed CI workflow is not evidence of a successful GitHub Actions run. Passing tests is not a security proof or a performance benchmark.

## Useful first collaboration

T001 separates the owner-controlled service from adapters. T002 verifies SDK-backed MCP behavior with actual applications. T003 builds the first truly isolated scientific runtime. T005 adds deliberate peer invitations and transport. T011 builds real model-block transport and open-model execution. T012 now provides local contracts for cross-model/human research handoff; actual provider experiments and orchestration remain work above those contracts. Each is a separate implementation lane with a documented interface. T009 can independently review them. A task claim/PR coordinates agents; nothing in this repository starts agents on its own.
