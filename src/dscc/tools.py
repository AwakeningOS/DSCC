"""One bounded trusted built-in. This is not a third-party code sandbox."""
from __future__ import annotations

from .canonical import canonical_bytes, cid_for

TOOL_ID = "dscc.integer_stats.v1"
DESCRIPTOR = {
    "id": TOOL_ID,
    "algorithm": "For 1..10000 integers each in [-1000000000,1000000000], return count,sum,min,max.",
    "runtime": "trusted-builtin/python",
    "network": False,
    "arbitrary_code": False,
    "verification": "deterministic result; external verification is separate",
}
TOOL_DIGEST = cid_for(canonical_bytes(DESCRIPTOR))


def validate_values(data: dict) -> list[int]:
    values = data.get("values")
    if not isinstance(values, list) or not 1 <= len(values) <= 10_000:
        raise ValueError("input requires 1..10000 integer values")
    if any(type(v) is not int or abs(v) > 1_000_000_000 for v in values):
        raise ValueError("values must be bounded integers (booleans are not integers)")
    return values


def integer_stats(data: dict) -> dict[str, int]:
    values = validate_values(data)
    return {"count": len(values), "sum": sum(values), "min": min(values), "max": max(values)}
