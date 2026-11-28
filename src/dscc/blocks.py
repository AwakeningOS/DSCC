"""Local content-addressed storage for large immutable binary blocks.

The seed artifact store remains optimized for small signed JSON envelopes. Model
weights and other large binaries live here and are referenced by CID from signed
manifests. This module does not provide network transport or automatic pinning.
"""
from __future__ import annotations

import contextlib
import hashlib
import os
import stat
import threading
import uuid
from pathlib import Path
from typing import Iterator

from .canonical import cid_for_digest, validate_cid
from .identity import write_private_exclusive

if os.name == "posix":
    import fcntl
else:  # pragma: no cover - Windows fallback
    fcntl = None  # type: ignore[assignment]


class BlockStore:
    def __init__(self, home: Path, quota_bytes: int):
        if type(quota_bytes) is not int or quota_bytes < 1:
            raise ValueError("block quota must be a positive integer")
        self.root = home / "blocks" / "raw"
        self.quota_bytes = quota_bytes
        self._lock = threading.RLock()
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass

    @contextlib.contextmanager
    def _write_lock(self) -> Iterator[None]:
        """Serialize block quota checks and replacements across threads and local processes."""
        lock_path = self.root / ".quota.lock"
        with self._lock:
            if fcntl is not None:
                fd = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX)
                    try:
                        yield
                    finally:
                        fcntl.flock(fd, fcntl.LOCK_UN)
                finally:
                    os.close(fd)
            else:  # pragma: no cover - Windows fallback
                yield

    def _path(self, cid: str) -> Path:
        validate_cid(cid)
        return self.root / cid

    @staticmethod
    def _open_regular_readonly(path: Path):
        if path.is_symlink():
            raise ValueError("block source must be a regular non-symlink file")
        if os.name == "posix":
            flags = os.O_RDONLY
            if hasattr(os, "O_NOFOLLOW"):
                flags |= os.O_NOFOLLOW
            try:
                fd = os.open(path, flags)
            except OSError as exc:
                raise ValueError("block source must be a regular non-symlink file") from exc
            handle = os.fdopen(fd, "rb")
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                handle.close()
                raise ValueError("block source must be a regular non-symlink file")
            return handle
        if not path.is_file():
            raise ValueError("block source must be a regular non-symlink file")
        return path.open("rb")

    @classmethod
    def _digest_file(cls, path: Path) -> tuple[bytes, int]:
        digest = hashlib.sha256()
        size = 0
        with cls._open_regular_readonly(path) as source:
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
            if path.name.startswith(".") or path.is_symlink() or not path.is_file():
                continue
            total += path.stat().st_size
        return total

    def status(self) -> dict:
        files = [
            p for p in self.root.iterdir()
            if not p.name.startswith(".") and not p.is_symlink() and p.is_file()
        ]
        return {
            "blocks": len(files),
            "block_bytes": sum(p.stat().st_size for p in files),
            "block_quota_bytes": self.quota_bytes,
        }

    def available(self, cid: str) -> bool:
        p = self._path(cid)
        return not p.is_symlink() and p.is_file()

    def size(self, cid: str) -> int:
        p = self._path(cid)
        if p.is_symlink() or not p.is_file():
            raise KeyError("block not found")
        return p.stat().st_size

    def add_bytes(self, data: bytes) -> dict:
        if not isinstance(data, bytes):
            raise ValueError("block data must be bytes")
        digest = hashlib.sha256(data).digest()
        cid = cid_for_digest(digest)
        with self._write_lock():
            destination = self._path(cid)
            if destination.exists():
                return self.verify(cid, expected_bytes=len(data))
            if self.usage_bytes() + len(data) > self.quota_bytes:
                raise ValueError("block storage quota exceeded")
            temporary = self.root / f".{uuid.uuid4().hex}.tmp"
            try:
                write_private_exclusive(temporary, data)
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
        with self._write_lock():
            destination = self._path(cid)
            if destination.exists():
                return self.verify(cid, expected_bytes=size)
            if self.usage_bytes() + size > self.quota_bytes:
                raise ValueError("block storage quota exceeded")
            temporary = self.root / f".{uuid.uuid4().hex}.tmp"
            copied_digest = hashlib.sha256()
            copied = 0
            try:
                with self._open_regular_readonly(source) as inp:
                    if os.name == "posix":
                        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                        if hasattr(os, "O_NOFOLLOW"):
                            flags |= os.O_NOFOLLOW
                        fd = os.open(temporary, flags, 0o600)
                        out = os.fdopen(fd, "wb")
                    else:
                        out = temporary.open("xb")
                    with out:
                        while True:
                            chunk = inp.read(1024 * 1024)
                            if not chunk:
                                break
                            copied += len(chunk)
                            if copied > size:
                                raise ValueError("block source changed while being imported")
                            out.write(chunk)
                            copied_digest.update(chunk)
                        out.flush()
                        if os.name == "posix":
                            os.fsync(out.fileno())
                if copied != size or copied_digest.digest() != digest:
                    raise ValueError("block source changed while being imported")
                try:
                    temporary.chmod(0o600)
                except OSError:
                    pass
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
        return {"cid": cid, "bytes": size, "verified": True}

    def verify(self, cid: str, *, expected_bytes: int | None = None) -> dict:
        path = self._path(cid)
        if path.is_symlink() or not path.is_file():
            raise KeyError("block not found")
        digest, size = self._digest_file(path)
        actual = cid_for_digest(digest)
        if actual != cid:
            raise ValueError("stored block CID mismatch")
        if expected_bytes is not None and size != expected_bytes:
            raise ValueError("stored block byte length mismatch")
        return {"cid": cid, "bytes": size, "verified": True}

    def path(self, cid: str) -> Path:
        self.verify(cid)
        return self._path(cid)
