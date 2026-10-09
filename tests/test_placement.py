"""Capacity-packing regression tests, not GPU/runtime performance evidence."""
import copy
import itertools

import pytest

from dscc._placement import pack_weight_blocks


def inputs(sizes, capacities):
    return ([(f"w{i}", size) for i, size in enumerate(sizes)],
            {("cap", str(i)): size for i, size in enumerate(capacities)})


def assert_valid(weights, capacities, result):
    sizes = dict(weights)
    found = [cid for cids in result.values() for cid in cids]
    assert sorted(found) == sorted(sizes)
    assert len(found) == len(set(found))
    for key, cids in result.items():
        assert sum(sizes[cid] for cid in cids) <= capacities[key]


def brute_feasible(sizes, capacities):
    # Independent tiny oracle: enumerate every assignment, no greedy/pruning.
    for assignment in itertools.product(range(len(capacities)), repeat=len(sizes)):
        used = [0] * len(capacities)
        for size, device in zip(sizes, assignment):
            used[device] += size
        if all(a <= b for a, b in zip(used, capacities)):
            return True
    return False


def test_known_two_gpu_counterexample():
    w, c = inputs([14, 10, 10, 7, 7], [24, 24])
    before = copy.deepcopy((w, c))
    result = pack_weight_blocks(w, c)
    assert_valid(w, c, result)
    assert sorted(sum(dict(w)[cid] for cid in ids) for ids in result.values()) == [24, 24]
    assert (w, c) == before


def test_backtracking_recovers_after_both_greedy_passes_fail():
    w, c = inputs([3, 1, 8, 3, 10, 9, 7], [12, 10, 10, 9])
    # Budget zero proves this case reaches backtracking, not a greedy success.
    with pytest.raises(ValueError, match="budget exhausted; feasibility is unknown"):
        pack_weight_blocks(w, c, max_search_states=0)
    assert_valid(w, c, pack_weight_blocks(w, c))


def test_existing_greedy_output_is_unchanged():
    w, c = inputs([8, 8], [8, 8])
    assert pack_weight_blocks(w, c, max_search_states=0) == {
        ("cap", "0"): ["w1"], ("cap", "1"): ["w0"]}


def test_input_order_does_not_change_assignment():
    w, c = inputs([3, 1, 8, 3, 10, 9, 7], [12, 10, 10, 9])
    assert pack_weight_blocks(w, c) == pack_weight_blocks(list(reversed(w)), dict(reversed(list(c.items()))))


@pytest.mark.parametrize("sizes,caps,message", [
    ([10, 1], [6, 6], "shard exceeds every compatible GPU"),
    ([6, 6, 6], [10, 10], "no capacity-feasible placement"),
    ([6, 6], [5, 5, 1], "shard exceeds every compatible GPU"),
    ([4, 4, 4], [5, 5], "memory is insufficient"),
])
def test_infeasible_instances_have_specific_failures(sizes, caps, message):
    w, c = inputs(sizes, caps)
    before = copy.deepcopy((w, c))
    with pytest.raises(ValueError, match=message):
        pack_weight_blocks(w, c)
    assert (w, c) == before


@pytest.mark.parametrize("budget", [-1, True, 1.5])
def test_search_budget_validation(budget):
    w, c = inputs([1], [1])
    with pytest.raises(ValueError, match="nonnegative integer"):
        pack_weight_blocks(w, c, max_search_states=budget)


def test_deep_backtracking_uses_no_python_recursion():
    # Small shards do not repair the indivisible large-block prefix. Both
    # heuristics fail before reaching the 1500 one-byte shards.
    w, c = inputs([30, 10, 80, 30, 100, 90, 70] + [1] * 1500,
                  [120, 100, 100, 90] + [1] * 1500)
    with pytest.raises(ValueError, match="budget exhausted"):
        pack_weight_blocks(w, c, max_search_states=0)
    assert_valid(w, c, pack_weight_blocks(w, c))


def test_exhaustive_small_instances_against_independent_oracle():
    for n in range(1, 6):
        for sizes in itertools.combinations_with_replacement(range(1, 5), n):
            for caps in itertools.combinations_with_replacement(range(1, 8), 2):
                w, c = inputs(sizes, caps)
                expected = brute_feasible(sizes, caps)
                try:
                    packed = pack_weight_blocks(w, c)
                except ValueError as exc:
                    assert "budget" not in str(exc)
                    assert not expected, (sizes, caps)
                else:
                    assert expected, (sizes, caps)
                    assert_valid(w, c, packed)
