# Paper-to-software traceability

| Paper/brief requirement | Target module | M0 status |
|---|---|---|
| Local-first, model-independent scientific memory (§3.1, §4.3) | core store + CLI/MCP | Implemented locally; no consciousness claim. |
| Immutable artifacts + explicit derivation (§5) | signed records + parent CIDs | Implemented for bounded JSON records. Large file DAG/CAR pending. |
| Canonical profile (§5.2) | canonical.py + schema + vectors | Restricted, explicitly versioned profile; not compatible with every original manifest. |
| Mutable indexes distinct from truth (§6) | SQLite catalog | Keyword catalog implemented; reconstruction tool T007. |
| Signed history | signed event chain | Implemented locally; no external anchoring or Byzantine consensus. |
| Peer discovery, pinning, routing | transport adapter | T005; no P2P claim in M0. |
| Node owner admission + budget | job states + built-in bounds | Owner approval and input/quota bounds implemented; CPU/GPU isolation pending. |
| WASI/OCI/gVisor and GPU workers | executor adapters | T003/T006; trusted integer tool is not a sandbox. |
| V0–V4 verification | verifier interfaces | Integrity verification only; same-machine deterministic comparison in demo. |
| MCP local model connection | stdio adapter | Protocol-subset tests implemented; installed host-app tests pending. |
| RO-Crate / CWL / PROV / WorldSnapshot | scientific adapters | T007/T008. |
| Contribution credits / payments | optional economy | Design only; no financial claims or token launch. |
| Open-model distribution foundation | OMC profiles + local raw block store | Model/capability/training metadata and local block integrity implemented; no peer transfer or model execution. |
| Distributed open-model compute | planner + future runtime/transport | Non-executing local placement planning implemented; real inference/training is T011 and dependent tasks. |
| Agent cooperation in development | AGENTS + tasks + PR templates | Prepared artifacts; no background agent has been launched. |
| Distributed AI Research Laboratory final goal | long-term DSCC direction | Defined as the orchestration layer where closed AI, open AI and humans continue shared AI-research projects through artifacts; not yet implemented. |
| Cross-model research handoff | T012 | Contract/handoff work prepared; multi-agent autonomous research execution is future work. |

The repository does not silently replace the paper. The M0 seed is a concrete implementation checkpoint inside its broader direction. All later features have independent acceptance gates.

