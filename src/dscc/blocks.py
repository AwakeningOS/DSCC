"""Local content-addressed storage for large immutable binary blocks.

The seed artifact store remains optimized for small signed JSON envelopes. Model
weights and other large binaries live here and are referenced by CID from signed
manifests. This module does not provide network transport or automatic pinning.
"""
from __future__ import annotations

import hashlib
import os
import uuid
from pathlib import Path

from .canonical import cid_for_digest, validate_cid


class BlockStore:
    def __init__(self, home: Path, quota_bytes: int):
        if type(quota_bytes) is not int or quota_bytes < 1:
            raise ValueError("block quota must be a positive integer")
        self.root = home / "blocks" / "raw"
        self.quota_bytes = quota_bytes
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    def _path(self, cid: str) -> Path:
        validate_cid(cid)
        return self.root / cid

    @staticmethod
    def _digest_file(path: Path) -> tuple[bytes, int]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as source:
            while True:
                chunk = source.read(1024 * 1024)
                if not chunk:
                    break
                digest.update(chunk)
                size += len(chunk)
        return digest.digest(), size

    def usage_bytes(self) -> int:
        total = 0
        for path in self.root.iterdir():
            if path.name.startswith(".") or not path.is_file():
                continue
            total += path.stat().st_size
        return total

    def status(self) -> dict:
        files = [p for p in self.root.iterdir() if p.is_file() and not p.name.startswith(".")]
        return {
            "blocks": len(files),
            "block_bytes": sum(p.stat().st_size for p in files),
            "block_quota_bytes": self.quota_bytes,
        }

    def available(self, cid: str) -> bool:
        return self._path(cid).is_file()

    def add_bytes(self, data: bytes) -> dict:
        if not isinstance(data, bytes):
            raise ValueError("block data must be bytes")
        digest = hashlib.sha256(data).digest()
        cid = cid_for_digest(digest)
        destination = self._path(cid)
        if destination.exists():
            return self.verify(cid)
        if self.usage_bytes() + len(data) > self.quota_bytes:
            raise ValueError("block storage quota exceeded")
        temporary = self.root / f".{uuid.uuid4().hex}.tmp"
        try:
            with temporary.open("xb") as target:
                target.write(data)
            temporary.chmod(0o600)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {"cid": cid, "bytes": len(data), "verified": True}

    def add_file(self, source: Path) -> dict:
        source = source.expanduser()
        if source.is_symlink() or not source.is_file():
            raise ValueError("block source must be a regular non-symlink file")
        source = source.resolve()
        digest, size = self._digest_file(source)
        cid = cid_for_digest(digest)
        destination = self._path(cid)
        if destination.exists():
            return self.verify(cid)
        if self.usage_bytes() + size > self.quota_bytes:
            raise ValueError("block storage quota exceeded")
        temporary = self.root / f".{uuid.uuid4().hex}.tmp"
        copied_digest = hashlib.sha256()
        copied = 0
        try:
            with source.open("rb") as inp, temporary.open("xb") as out:
                while True:
                    chunk = inp.read(1024 * 1024)
                    if not chunk:
                        break
                    out.write(chunk)
                    copied_digest.update(chunk)
                    copied += len(chunk)
            if copied != size or copied_digest.digest() != digest:
                raise ValueError("block source changed while being imported")
            temporary.chmod(0o600)
            os.replace(temporary, destination)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {"cid": cid, "bytes": size, "verified": True}

    def verify(self, cid: str) -> dict:
        path = self._path(cid)
        if not path.is_file():
            raise KeyError("block not found")
        digest, size = self._digest_file(path)
        actual = cid_for_digest(digest)
        if actual != cid:
            raise ValueError("stored block CID mismatch")
        return {"cid": cid, "bytes": size, "verified": True}

    def path(self, cid: str) -> Path:
        self.verify(cid)
        return self._path(cid)
