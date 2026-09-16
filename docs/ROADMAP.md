# Roadmap and release gates

Dates are intentionally not promised. Move forward when acceptance criteria pass.

| Milestone | Deliverable | Gate |
|---|---|---|
| M0 — local foundation | Signed research records, lineage, bounded storage, CLI, MCP subset, explicit bundle exchange, built-in job | Unit/negative/concurrency tests and three-logical-node demo. This repository implements M0 only. |
| M1 — daily local application | Official SDK MCP adapter, authenticated local daemon, desktop UI, preview-based folder intake | LM Studio and Codex manual smoke tests; no host config overwrite; cancellation and key/permission tests. |
| M2 — real shared execution | WASI sandbox, job leases, checkpoint-safe cancellation, V0/V1 verification | Adversarial filesystem/network/resource tests; worker crash/recovery; independent executor verification. |
| M3 — opt-in peer federation | Kubo/libp2p asset transport, identity pinning, LAN/manual invitations, rebuildable discovery | Real two-PC tests; peer stop/rejoin; corrupt block; private asset denial; no central scheduler requirement. |
| M4 — GPU workers | Device capability inventory, supported runtime matrix, owner quotas/time windows | Actual GPUs, measured throughput and memory, thermal/power observation, cancellation, isolation review. |
| M5 — research worlds and methods | CWL/RO-Crate/PROV adapters, world forks, reusable exploration methods | Independent rerun and model-switch handoff on a real scientific workload. |
| M6 — public federation | Multiple discovery/relay providers, abuse controls, signed updates and OS installers | Cross-NAT field tests; supply-chain review; resource accounting and adversarial participation. |
| M7 — optional economy and model research | Contribution receipts; budgeted model-research workflows | Independent security, financial and governance review; no automatic transfer of privileges to improved agents. |

M3 may advance in parallel with M1, while arbitrary remote execution remains gated by M2. GPU and WAN training are separate capabilities, not a single switch. Storage-only users are legitimate participants. The complete product is not defined by this starter's small demo workload.
