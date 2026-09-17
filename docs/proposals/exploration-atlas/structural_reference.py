"""Small deterministic structural-feature oracle; not a semantic retrieval engine."""
from __future__ import annotations

import hashlib
import json
import math
from collections import Counter


def digest(value):
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def features(episode: dict, rounds: int = 2) -> Counter:
    if type(rounds) is not int or rounds < 0:
        raise ValueError("rounds must be a nonnegative integer")
    nodes = episode["nodes"]
    labels = {n["id"]: digest([n["role"], n["stage"], n["origin"]]) for n in nodes}
    if len(labels) != len(nodes):
        raise ValueError("duplicate node ID")
    incoming, outgoing = {n: [] for n in labels}, {n: [] for n in labels}
    for edge in episode["links"]:
        a, b = edge["from"], edge["to"]
        if a not in labels or b not in labels:
            raise ValueError("missing endpoint")
        outgoing[a].append((edge["relation"], b))
        incoming[b].append((edge["relation"], a))
    counts = Counter()
    for step in range(rounds + 1):
        counts.update((step, label) for label in labels.values())
        if step < rounds:
            labels = {n: digest([labels[n],
                                sorted([rel, labels[a]] for rel, a in incoming[n]),
                                sorted([rel, labels[b]] for rel, b in outgoing[n])])
                      for n in labels}
    return counts


def similarity(a: Counter, b: Counter) -> float:
    denominator = math.sqrt(sum(x*x for x in a.values()) * sum(x*x for x in b.values()))
    if denominator == 0:
        return 0.0
    return sum(x*b.get(k, 0) for k, x in a.items()) / denominator
