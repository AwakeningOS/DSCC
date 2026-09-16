"""Domain-separated Ed25519 signing. No key is exposed through MCP."""
from __future__ import annotations

import base64
import re
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .canonical import canonical_bytes

KEY_RE = re.compile(r"^[0-9a-f]{64}$")
DOMAINS = {"artifact": b"DSCC-ARTIFACT-SEED-v1\x00", "event": b"DSCC-EVENT-SEED-v1\x00"}


def public_hex(key: Ed25519PrivateKey) -> str:
    return key.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    ).hex()


def generate_key(path: Path) -> None:
    key = Ed25519PrivateKey.generate()
    raw = key.private_bytes(serialization.Encoding.Raw, serialization.PrivateFormat.Raw,
                            serialization.NoEncryption())
    with path.open("xb") as f:
        f.write(raw)
    path.chmod(0o600)


def load_key(path: Path) -> Ed25519PrivateKey:
    if path.is_symlink():
        raise ValueError("node signing key must not be a symlink")
    raw = path.read_bytes()
    if len(raw) != 32:
        raise ValueError("invalid node signing key")
    return Ed25519PrivateKey.from_private_bytes(raw)


def sign(body: dict[str, Any], key: Ed25519PrivateKey, domain: str) -> dict[str, Any]:
    message = DOMAINS[domain] + canonical_bytes(body)
    return {"body": body, "public_key": public_hex(key),
            "signature": base64.b64encode(key.sign(message)).decode("ascii")}


def verify(envelope: Any, domain: str) -> dict[str, Any]:
    if not isinstance(envelope, dict) or set(envelope) != {"body", "public_key", "signature"}:
        raise ValueError("invalid signed envelope")
    pub = envelope["public_key"]
    if not isinstance(pub, str) or not KEY_RE.fullmatch(pub):
        raise ValueError("invalid public key")
    if not isinstance(envelope["signature"], str) or len(envelope["signature"]) != 88:
        raise ValueError("invalid signature encoding")
    if not isinstance(envelope["body"], dict):
        raise ValueError("signed body must be an object")
    try:
        sig = base64.b64decode(envelope["signature"], validate=True)
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(pub)).verify(
            sig, DOMAINS[domain] + canonical_bytes(envelope["body"])
        )
    except (InvalidSignature, ValueError, base64.binascii.Error) as exc:
        raise ValueError("signature verification failed") from exc
    return envelope["body"]
