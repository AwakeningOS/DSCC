"""Capacity-only packing for the non-executing OMC planner.

Keep the legacy greedy placement when it succeeds. Retry from the original
capacities with best-fit, then bounded, iterative backtracking. A search-budget
failure is deliberately different from a proof of infeasibility. This module
makes no claim about tensor dependencies or actual runtime memory requirements.
"""
from __future__ import annotations

from collections.abc import Iterator

DeviceKey = tuple[str, str]
DEFAULT_SEARCH_STATES = 10_000


def pack_weight_blocks(
    weights: list[tuple[str, int]],
    capacities: dict[DeviceKey, int],
    *,
    max_search_states: int = DEFAULT_SEARCH_STATES,
) -> dict[DeviceKey, list[str]]:
    """Pack validated positive-size blocks into nonnegative device capacities.

    Callers validate model/device profiles. Inputs are never modified. A budget
    counts attempted backtracking assignments, not seconds or a RAM quota.
    Equal residual capacities are interchangeable ONLY for this capacity-only
    subproblem; future topology/runtime constraints need a different solver.
    """
    if type(max_search_states) is not int or max_search_states < 0:
        raise ValueError("max_search_states must be a nonnegative integer")
    ordered = sorted(weights, key=lambda row: (-row[1], row[0]))
    if not ordered:
        return {key: [] for key in capacities}
    if not capacities or ordered[0][1] > max(capacities.values()):
        raise ValueError("a model shard exceeds every compatible GPU; split weights more finely")
    if sum(size for _, size in ordered) > sum(capacities.values()):
        raise ValueError("compatible advertised GPU memory is insufficient")

    # The first pass has exactly the old tie-breaking and placements.
    for best_fit in (False, True):
        remaining = dict(capacities)
        result: dict[DeviceKey, list[str]] = {key: [] for key in capacities}
        for cid, size in ordered:
            choices = [key for key in capacities if remaining[key] >= size]
            if not choices:
                break
            if best_fit:
                key = min(choices, key=lambda k: (remaining[k], k))
            else:
                key = max(choices, key=lambda k: (remaining[k], k))
            result[key].append(cid)
            remaining[key] -= size
        else:
            return result

    remaining = dict(capacities)
    result = {key: [] for key in capacities}
    selected: list[DeviceKey] = []
    examined = 0

    def choices_at(index: int) -> Iterator[DeviceKey]:
        size = ordered[index][1]
        seen: set[int] = set()
        # Materialized at entry, when the parent state is fixed. Backtracking
        # restores that state before this iterator is resumed.
        choices = sorted((key for key in capacities if remaining[key] >= size),
                         key=lambda k: (remaining[k], k))
        for key in choices:
            capacity = remaining[key]
            if capacity not in seen:
                seen.add(capacity)
                yield key

    # Explicit stack supports the seed's 4096 blocks without recursion limits.
    stack = [choices_at(0)]
    while stack:
        index = len(selected)
        key = next(stack[-1], None)
        if key is None:
            stack.pop()
            if selected:
                previous = selected.pop()
                _, size = ordered[len(selected)]
                result[previous].pop()
                remaining[previous] += size
            continue
        if examined >= max_search_states:
            raise ValueError("placement search budget exhausted; feasibility is unknown")
        examined += 1
        cid, size = ordered[index]
        remaining[key] -= size
        result[key].append(cid)
        selected.append(key)
        if len(selected) == len(ordered):
            return result
        stack.append(choices_at(index + 1))

    raise ValueError("no capacity-feasible placement of whole weight blocks exists; split weights more finely")
