# Open Model Commons foundation validation

Software version: **0.1.0a1**  
Scope: PR #15, local Open Model Commons foundation only.

## Hosted CI

GitHub Actions run **#63** executed the repository workflow on the PR head before merge.

| OS | Python | pytest | demo | repository check |
|---|---:|---|---|---|
| Ubuntu | 3.11 | 108 passed | success | success |
| Ubuntu | 3.13 | 108 passed | success | success |
| Windows | 3.11 | 108 passed | success | success |
| Windows | 3.13 | 108 passed | success | success |

Observed pytest durations were approximately 2.91 s, 3.97 s, 17.66 s and 39.26 s across the four matrix jobs. These timings are CI observations, not product performance benchmarks.

The repository check reported 23 Python files parsed, 5 JSON Schemas checked and all retained reference checksums valid on the sampled Ubuntu 3.13 job.

## What the tests establish

The suite covers the prior seed behavior plus:

- streaming-compatible CID construction for large raw blocks;
- local large-block import, deduplication and tamper detection;
- versioned OMC model/capability/training-run validation;
- signed provenance wrapping without changing existing artifact kinds;
- local model weight-block availability reporting;
- single-device inference placement proposals;
- multi-device shard placement proposals;
- rejection of an unsplittable shard;
- training-run lineage and checkpoint references;
- MCP recording/inspection/planning while keeping execution authority absent;
- existing CLI/MCP, bundle, signature, quota, concurrency, demo and Exploration Atlas contract regressions.

## What the tests do not establish

No CI job used a real GPU, loaded an LLM, opened a P2P connection or performed model inference/training. The new planner consumes recorded capabilities and emits a plan with `execution_authorized: false` and `network_execution: false`.

The large-block store is local only. Artifact bundle tests do not transfer weight blocks. There is no runtime sandbox for model code, no GPU isolation, no remote capability attestation, no WAN scheduler, no distributed optimizer, no inference privacy guarantee and no adversarial worker verification.

Those capabilities remain gated by T001/T003/T005/T006/T009/T011 and the global-scale challenge registry.
