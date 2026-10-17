# DSCC research index

Research references and implementation handoffs are dated evidence snapshots, not automatically implemented capabilities. Read the root [README](../../README.md) for DSCC's purpose, [STATUS](../STATUS.md) for actual capabilities and [TASKS](../TASKS.md) before editing code.

## Living research tracks

| Track | Research question and continuation |
|---|---|
| [R-HS — Collaborative autonomy and help-seeking emergence](help-seeking/README.md) | Can agents recognize what they lack and proactively request appropriate cooperation while respecting their partners' expertise, limits, burden and consent? The [agenda](help-seeking/RESEARCH_AGENDA.ja.md) defines eight questions and twelve unexecuted acceptance conditions; the [evidence ledger](help-seeking/SOURCES_AND_EVIDENCE.ja.md) separates direct training, auxiliary abilities and generalization. Continue in [Issue #28](https://github.com/AwakeningOS/DSCC/issues/28). |

A research track is a continuing question, not a new implemented runtime or a claim that its field was invented by DSCC. Literature refresh and measured results update the track through explicit reviews.

## 2026-10-17 local cooperation trace

The [R-HS primary-source review and partial L2 adapter handoff](help-seeking/2026-10-17-COOPERATION_TRACE_HANDOFF.ja.md) connects KL-PBD, CTXGAP, ASPI and the Swarmchasers case to six signed local episode stages and synthetic recovery tests. Local record continuity is not a trained help-seeking policy, actual third-party contact or security certification.

## Current reading path

| Material | What to use it for |
|---|---|
| [2026-10-14 Agentic LLMs text-based review](2026-10-14-AGENTIC_LLMS_REVIEW.ja.md) | Portable harness, memory/retrieval and evaluation choices; [implementation handoff](agentic-llms-2026-10-14/IMPLEMENTATION_HANDOFF.ja.md) maps five lanes and twelve proposed acceptance conditions to existing contracts; [source ledger](agentic-llms-2026-10-14/SOURCES_AND_LIMITS.ja.md) distinguishes the supplied textbook, five primary-source checks and DSCC proposals |
| [2026-10-13 Anthropic edge inference and handoff analysis](2026-10-13-ANTHROPIC_EDGE_HANDOFF.ja.md) | Low-RAM/CPU participation, runtime setup recipes, pipeline recovery, grounded agent replacement and twelve acceptance tests; [source scope and limitations](anthropic-2026-10-13/SOURCES_AND_LIMITS.ja.md) separate observations from proposed DSCC integration |
| [2026-10-09 research and implementation update](2026-10-09-RESEARCH_UPDATE.ja.md) | Five October reports plus September RRSI/GeoMesh; source-access depth, cooperative training, experience usefulness, harness tests and concrete acceptance conditions |
| [Distributed AI architecture research notes](DSCC_2026_Distributed_AI_Architecture.md) | INTELLECT-1 prior art and the 2026-10-07 trusted-volunteer → open-cooperative → permissionless roadmap |
| [2026-10-01 enabling technologies](2026-10-01-ENABLING_TECHNOLOGIES.ja.md) | Runtime, discovery, data sharing and hardware-fabric candidates; dated implementation claims need checking before adoption |
| [2026-09-25 paper scout](2026-09-25-LATEST_DSCC_PAPERS.ja.md) | Earlier sixteen-paper handoff; preserve its original date and recheck individual primary sources |
| [Experience and state sharing](../proposals/EXPERIENCE_AND_STATE_SHARING.ja.md) | Model-independent evidence/trajectories versus working-state snapshots, latent capsules and converters |
| [Experience-sharing evidence ledger](../proposals/experience-sharing/SOURCES_AND_EVIDENCE.ja.md) | Earlier source scope and compatibility limits |

## What counts as an update

Record whether an item was discovered, its primary abstract read, its full text reviewed, its code inspected, or its experiment reproduced. These are separate evidence levels. A code URL in an abstract is not a tested implementation. A published improvement is not a DSCC benchmark result. A source fetch failure means the source was not available in that review; it does not establish that the paper or code does not exist.

Do not label older newly discovered work as newly published. Keep first-publication and checked-on dates separate. Record source revision, model/task/data scope, measured versus projected results, negative results, license and the remaining DSCC question. Preserve original research material; correct or supplement it through explicit dated updates rather than quietly rewriting history.

Concrete implementation work should cite an existing task and record its acceptance evidence. The [capacity-only planner correction](../PLANNER.md) is implemented; the papers above do not turn the planner into a GPU runtime or distributed trainer.
