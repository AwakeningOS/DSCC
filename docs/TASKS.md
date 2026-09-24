# Development tasks

Choose one READY task per branch. Check the matching GitHub Issue and coordinate a claim before editing. Do not start a BLOCKED task by inventing the missing backend. The task IDs remain stable even if GitHub issue numbers differ.

| ID | Task | Status | Dependencies |
|---|---|---|---|
| [T001](tasks/T001.md) | Local service and owner permissions | READY | — |
| [T002](tasks/T002.md) | Official MCP SDK and host-app integration | READY | — |
| [T003](tasks/T003.md) | WASI executor with enforceable limits | READY | — |
| [T004](tasks/T004.md) | Desktop user interface | BLOCKED | T001 |
| [T005](tasks/T005.md) | Explicit peer invitations and artifact transport | READY | — |
| [T006](tasks/T006.md) | GPU worker capability and isolation matrix | BLOCKED | T001, T003 |
| [T007](tasks/T007.md) | Research object adapters and catalog rebuild | READY | — |
| [T008](tasks/T008.md) | Reproducible shared-world example | BLOCKED | T003, T007 |
| [T009](tasks/T009.md) | Adversarial verification and release audit | READY | — |
| [T010](tasks/T010.md) | Cross-domain Exploration Atlas | READY for contracts/index | T007 coordination; T001/T002/T004/T005 for later integration |
| [T011](tasks/T011.md) | Distributed Open Model Commons execution | BLOCKED for public execution; isolated work READY | T001/T003/T005/T006/T009 for full execution |
| [T012](tasks/T012.md) | Distributed AI Research Laboratory orchestration | Local contracts/handoff IMPLEMENTED; real-model experiment READY; full autonomous distributed execution BLOCKED | T007/T010 coordination; T001/T002/T005/T009/T011 for later execution |

T001, T002, T003, T005, T007 and T009 can start from M0. Shared schema/core edits require coordination. Start the security reviewer on a different worktree from the implementer.

T010 adds the cross-domain exploration-map proposal and a dedicated implementation lane. It does not mark T007 complete or turn the synthetic contract helpers into a released retrieval feature. See [Exploration Atlas](proposals/EXPLORATION_ATLAS.ja.md).

T011 starts from the implemented local OMC contracts, block store and non-executing planner. Public model execution remains blocked on owner/service separation, isolated runtime, peer transport, GPU work and adversarial verification. See [Distributed Open Model Commons](proposals/DISTRIBUTED_OPEN_MODEL_COMMONS.ja.md).

T012 implements the local research-profile/handoff lane. Actual cross-model research-quality experiments, multi-agent orchestration and repeated model-development cycles remain open. See [Research handoff](RESEARCH_HANDOFF.md) and [Distributed AI Research Laboratory](proposals/DISTRIBUTED_AI_RESEARCH_LAB.ja.md).

## Experience and state sharing research material

[AIの経験と作業状態を共有するDSCC](proposals/EXPERIENCE_AND_STATE_SHARING.ja.md) connects trajectory intake, experience graphs, working-state snapshots, latent experience capsules and converter registries to T007/T010/T011/T012. Its [primary-source evidence ledger](proposals/experience-sharing/SOURCES_AND_EVIDENCE.ja.md) separates reported research from DSCC implementation and records compatibility, evaluation and cost boundaries.

The proposal provides six implementation lanes and sixteen local ES challenge IDs mapped to existing tasks/global G-IDs. ES IDs are proposal-local tracking labels, not new completed tasks. Select a scoped lane, coordinate its interfaces in the existing issue, and record real acceptance evidence. The document introduces no collector, cache transfer, model execution or new permission; current task states above remain unchanged.

## Latest literature scout

[2026-09-25 DSCC latest research scout](research/2026-09-25-LATEST_DSCC_PAPERS.ja.md) records sixteen recent primary papers/surveys and turns them into implementation handoffs. It includes AIDE², FML-Bench, KVShareArena, XKV, CacheBridge, Decoupled DiLoCo, P2P cache-aware routing, CacheScout, latent-cache integrity, VeriAttn, OpenPCC, agent protocol/governance studies, research-agent verification surveys and memory × search evaluation. Use the R-ID and lane tables to scope work under the existing T005/T009/T010/T011/T012 issues; do not mark any task complete from literature evidence alone.

Issues: https://github.com/AwakeningOS/DSCC/issues
