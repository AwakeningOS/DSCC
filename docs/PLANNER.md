# Local OMC placement: capacity packing and its limits

This is a correction of T011's existing non-executing planner, not a GPU runtime or distributed-training scheduler. It does not change the seed/plan schema, signed artifact bytes, owner permissions, or model files.

## Why greedy failure is not impossibility

Two devices with 24 units of usable capacity can hold blocks of sizes 14, 10, 10, 7, 7: one holds 14+10, the other 10+7+7. The previous largest-free-capacity heuristic instead leaves free capacities 4 and 3 before the final 7-unit block. Its failure therefore cannot justify a claim that finer shards are necessary.

The planner now preserves successful legacy greedy outputs, retries from the original capacities using best-fit decreasing, and then uses deterministic iterative backtracking if both heuristics fail. It skips equivalent residual capacities only because this subproblem has capacity constraints alone. New topology, layer-order, runtime or ownership constraints must not silently reuse that equivalence rule.

The helper tests include a feasible case where both greedy passes fail, an independent exhaustive tiny assignment oracle, deterministic tie-breaking, input immutability, and a depth beyond Python's usual recursion limit. The public planner tests cover its validated inputs, unchanged successful plan bytes/IDs, and its non-execution flags.

## Distinguish the outcomes

- A block larger than every compatible device or a total larger than available capacity is immediately infeasible under the advertised capacity constraints.
- Exhausting all branches proves that the whole blocks cannot be packed under those constraints.
- Exhausting the default 10,000 attempted backtracking assignments means **feasibility is unknown**. It is not a proof that the model cannot fit. This deterministic search budget is not a wall-clock or hard memory quota.

The standard library implementation is a bin-packing feasibility correction, not a new scheduling algorithm or a claim of optimal cost. No external solver dependency is added. Successful legacy placements keep the same ordering and plan ID; inputs that previously failed may now return a proposal.

## What a returned plan still does not establish

Packing serialized weight blocks is not equivalent to constructing a valid tensor/pipeline-parallel execution graph. Runtime-specific weight layouts, KV/activation/optimizer memory, per-device overhead, common distributed runtimes, topology, current availability, and aliases for the same physical device need later scheduling/runtime contracts. Aggregate minimum memory is not proof that each stage has enough runtime memory. Capabilities are declarations, not hardware attestations.

`execution_authorized` and `network_execution` remain false. No model is downloaded, loaded, executed, or trained by this planner. See [T011](tasks/T011.md) and [the seed protocol](PROTOCOL.md).

## Reproduce

```sh
python -m pytest -q tests/test_placement.py tests/test_planner_regressions.py tests/test_omc.py
python -m pytest -q
python -m dscc demo
python scripts/check_repository.py
```

Commit-specific observed validation belongs in the associated PR. Small-instance oracle checks are correctness tests, not GPU performance measurements.
