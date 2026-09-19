"""Restricted JCS-compatible metadata and CIDv1/raw/sha2-256 identifiers.

Floats are deliberately not supported in this seed *metadata codec*. Binary
scientific data and complete JCS support are separate, versioned extensions.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
import unicodedata
from typing import Any

MAX_SAFE_INT = 2**53 - 1
MAX_OBJECT_BYTES = 1_048_576
MAX_BUNDLE_BYTES = 8_388_608
CID_RE = re.compile(r"^b[a-z2-7]{58}$")
PREFIX = bytes((1, 0x55, 0x12, 32))


def _validate(value: Any, depth: int = 0) -> Any:
    if depth > 32:
        raise ValueError("JSON nesting exceeds 32")
    if value is None or isinstance(value, bool):
        return value
    if type(value) is int:
        if abs(value) > MAX_SAFE_INT:
            raise ValueError("integer exceeds the interoperable safe range")
        return value
    if isinstance(value, str):
        if unicodedata.normalize("NFC", value) != value:
            raise ValueError("metadata strings must already be NFC-normalized")
        try:
            value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("lone surrogate in metadata") from exc
        return value
    if isinstance(value, list):
        return [_validate(x, depth + 1) for x in value]
    if isinstance(value, dict):
        if any(not isinstance(k, str) for k in value):
            raise ValueError("JSON object keys must be strings")
        for key in value:
            _validate(key, depth + 1)
        # RFC 8785 key ordering is based on UTF-16 code units, not codepoints.
        keys = sorted(value, key=lambda k: k.encode("utf-16be"))
        return {k: _validate(value[k], depth + 1) for k in keys}
    raise ValueError("unsupported metadata type; encode decimal metrics as strings with units")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        _validate(value), ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _constant(_: str) -> Any:
    raise ValueError("non-finite JSON number")


def parse_json(data: bytes | str, *, max_bytes: int = MAX_OBJECT_BYTES) -> Any:
    raw = data.encode("utf-8") if isinstance(data, str) else data
    if len(raw) > max_bytes:
        raise ValueError("JSON document exceeds byte limit")
    try:
        return json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid JSON document") from exc


def cid_for_digest(digest: bytes) -> str:
    if not isinstance(digest, bytes) or len(digest) != 32:
        raise ValueError("sha2-256 digest must be exactly 32 bytes")
    raw = PREFIX + digest
    return "b" + base64.b32encode(raw).decode("ascii").lower().rstrip("=")


def cid_for(data: bytes) -> str:
    return cid_for_digest(hashlib.sha256(data).digest())


def validate_cid(cid: str) -> str:
    if not isinstance(cid, str) or not CID_RE.fullmatch(cid):
        raise ValueError("expected a canonical CIDv1/raw/sha2-256 identifier")
    try:
        body = cid[1:]
        raw = base64.b32decode(body.upper() + "=" * ((-len(body)) % 8))
    except (ValueError, base64.binascii.Error) as exc:
        raise ValueError("invalid CID encoding") from exc
    if len(raw) != 36 or raw[:4] != PREFIX:
        raise ValueError("unsupported CID profile")
    canonical = "b" + base64.b32encode(raw).decode("ascii").lower().rstrip("=")
    if canonical != cid:
        raise ValueError("non-canonical CID")
    return cid
