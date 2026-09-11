"""Persistent file-identity proofs for the creature sprite catalog."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import time
import zlib
from pathlib import Path
from typing import Any, Callable, Iterable


CACHE_SCHEMA = "bg2-upscale-catalog-verification-cache-v1"
SHA256_PATTERN = re.compile(r"[0-9A-F]{64}")
WINDOWS_EPOCH_TICKS = 621_355_968_000_000_000


class VerificationMismatch(RuntimeError):
    """A current file differs from its sealed expected identity."""


def file_signature(path: Path) -> dict[str, int]:
    value = path.stat()
    if not stat.S_ISREG(value.st_mode):
        raise VerificationMismatch(f"not a regular file: {path}")
    return {
        "size": int(value.st_size),
        "mtime_ns": int(value.st_mtime_ns),
        "ctime_ns": int(value.st_ctime_ns),
        "device": int(value.st_dev),
        "inode": int(value.st_ino),
    }


def windows_last_write_ticks(signature: dict[str, int]) -> int:
    return WINDOWS_EPOCH_TICKS + int(signature["mtime_ns"]) // 100


def _stable_fingerprint(path: Path, include_crc32: bool) -> dict[str, Any]:
    digest = hashlib.sha256()
    checksum = 0
    byte_count = 0
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise VerificationMismatch(f"not a regular file: {path}")
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            if include_crc32:
                checksum = zlib.crc32(chunk, checksum)
            byte_count += len(chunk)
        after = os.fstat(stream.fileno())
    current = path.stat()
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if (
        any(getattr(before, name) != getattr(after, name) for name in fields)
        or not os.path.samestat(after, current)
        or any(getattr(after, name) != getattr(current, name) for name in fields)
        or byte_count != after.st_size
    ):
        raise VerificationMismatch(f"file changed while hashing: {path}")
    result: dict[str, Any] = {
        "signature": file_signature(path),
        "sha256": digest.hexdigest().upper(),
    }
    if include_crc32:
        result["crc32"] = checksum & 0xFFFFFFFF
    return result


class VerificationCache:
    """Reuse hashes only while the complete filesystem identity is unchanged."""

    def __init__(self, path: Path, *, full_verify: bool = False) -> None:
        self.path = path
        self.full_verify = full_verify
        self.started = time.perf_counter()
        self.entries: dict[str, dict[str, Any]] = {}
        self.trees: dict[str, dict[str, Any]] = {}
        self._memo: dict[str, dict[str, Any]] = {}
        self._dirty = False
        self.cache_load_error: str | None = None
        self.files_considered = 0
        self.files_hashed = 0
        self.bytes_hashed = 0
        self.proofs_reused = 0
        self.proofs_recorded = 0
        self.invalidated: set[str] = set()
        self._load()

    @staticmethod
    def _key(path: Path) -> str:
        return os.path.normcase(os.path.abspath(path))

    def _load(self) -> None:
        if not self.path.is_file():
            return
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
            if (
                not isinstance(value, dict)
                or value.get("schema") != CACHE_SCHEMA
                or not isinstance(value.get("files"), dict)
                or not isinstance(value.get("trees", {}), dict)
            ):
                raise ValueError("unsupported cache schema")
            self.entries = value["files"]
            self.trees = value.get("trees", {})
        except (OSError, UnicodeError, ValueError, TypeError) as error:
            # An unreadable cache is never trusted; verification falls back to hashing.
            self.cache_load_error = str(error)
            self.entries = {}
            self.trees = {}

    def verify_file(
        self,
        path: Path,
        expected_sha256: str,
        *,
        scope: str,
        expected_crc32: int | None = None,
        expected_bytes: int | None = None,
    ) -> dict[str, Any]:
        expected_sha256 = str(expected_sha256).upper()
        if SHA256_PATTERN.fullmatch(expected_sha256) is None:
            raise VerificationMismatch(f"invalid expected SHA-256 for {path}")
        key = self._key(path)
        self.files_considered += 1
        try:
            signature = file_signature(path)
        except OSError as error:
            self.invalidated.add(scope)
            raise VerificationMismatch(f"missing dependency: {path}: {error}") from error
        cached = self._memo.get(key) or self.entries.get(key)
        reusable = bool(
            not self.full_verify
            and isinstance(cached, dict)
            and cached.get("signature") == signature
            and cached.get("sha256") == expected_sha256
            and (expected_crc32 is None or cached.get("crc32") == expected_crc32)
        )
        if reusable:
            record = dict(cached)
            self.proofs_reused += 1
        else:
            if isinstance(cached, dict):
                self.invalidated.add(scope)
            record = _stable_fingerprint(path, expected_crc32 is not None)
            self.files_hashed += 1
            self.bytes_hashed += int(record["signature"]["size"])
            if record["sha256"] != expected_sha256:
                self.invalidated.add(scope)
                raise VerificationMismatch(
                    f"SHA-256 mismatch for {path}: {record['sha256']} != {expected_sha256}"
                )
            if expected_crc32 is not None and record.get("crc32") != expected_crc32:
                self.invalidated.add(scope)
                raise VerificationMismatch(f"CRC32 mismatch for {path}")
            record["path"] = str(path.resolve())
            self.entries[key] = record
            self._dirty = True
            self.proofs_recorded += 1
        if expected_bytes is not None and signature["size"] != int(expected_bytes):
            self.invalidated.add(scope)
            raise VerificationMismatch(f"size mismatch for {path}")
        self._memo[key] = record
        return record

    def fingerprint_file(
        self, path: Path, *, scope: str, include_crc32: bool = False
    ) -> dict[str, Any]:
        """Return the current fingerprint, reusing it only for the same identity."""

        key = self._key(path)
        self.files_considered += 1
        try:
            signature = file_signature(path)
        except OSError as error:
            self.invalidated.add(scope)
            raise VerificationMismatch(f"missing dependency: {path}: {error}") from error
        cached = self._memo.get(key) or self.entries.get(key)
        if (
            not self.full_verify
            and isinstance(cached, dict)
            and cached.get("signature") == signature
            and (not include_crc32 or isinstance(cached.get("crc32"), int))
        ):
            record = dict(cached)
            self.proofs_reused += 1
        else:
            if isinstance(cached, dict):
                self.invalidated.add(scope)
            record = _stable_fingerprint(path, include_crc32)
            record["path"] = str(path.resolve())
            self.entries[key] = record
            self._dirty = True
            self.files_hashed += 1
            self.bytes_hashed += int(record["signature"]["size"])
            self.proofs_recorded += 1
        self._memo[key] = record
        return record

    def record_verified(
        self,
        path: Path,
        expected_sha256: str,
        *,
        expected_crc32: int | None = None,
    ) -> dict[str, Any]:
        """Persist metadata after an exhaustive verifier already read the file."""

        expected_sha256 = str(expected_sha256).upper()
        if SHA256_PATTERN.fullmatch(expected_sha256) is None:
            raise VerificationMismatch(f"invalid verified SHA-256 for {path}")
        signature = file_signature(path)
        record: dict[str, Any] = {
            "path": str(path.resolve()),
            "signature": signature,
            "sha256": expected_sha256,
        }
        if expected_crc32 is not None:
            record["crc32"] = int(expected_crc32)
        key = self._key(path)
        self.entries[key] = record
        self._memo[key] = record
        self._dirty = True
        self.proofs_recorded += 1
        return record

    def verify_tree(
        self,
        name: str,
        paths: Iterable[Path],
        expected_sha256: str,
        hash_tree: Callable[[], str],
        *,
        scope: str,
    ) -> None:
        expected_sha256 = str(expected_sha256).upper()
        ordered = list(paths)
        signatures = [
            {"path": str(path.resolve()), "signature": file_signature(path)}
            for path in ordered
        ]
        cached = self.trees.get(name)
        if (
            not self.full_verify
            and isinstance(cached, dict)
            and cached.get("sha256") == expected_sha256
            and cached.get("files") == signatures
        ):
            self.proofs_reused += 1
            self.files_considered += len(ordered)
            return
        if isinstance(cached, dict):
            self.invalidated.add(scope)
        actual = hash_tree().upper()
        self.files_considered += len(ordered)
        self.files_hashed += len(ordered)
        self.bytes_hashed += sum(item["signature"]["size"] for item in signatures)
        if actual != expected_sha256:
            self.invalidated.add(scope)
            raise VerificationMismatch(
                f"tree SHA-256 mismatch for {name}: {actual} != {expected_sha256}"
            )
        self.trees[name] = {"sha256": actual, "files": signatures}
        self._dirty = True
        self.proofs_recorded += 1

    def record_verified_tree(
        self, name: str, paths: Iterable[Path], expected_sha256: str
    ) -> None:
        self.trees[name] = {
            "sha256": str(expected_sha256).upper(),
            "files": [
                {"path": str(path.resolve()), "signature": file_signature(path)}
                for path in paths
            ],
        }
        self._dirty = True
        self.proofs_recorded += 1

    def export_file(self, path: Path) -> dict[str, Any]:
        key = self._key(path)
        record = self._memo.get(key) or self.entries.get(key)
        if not isinstance(record, dict):
            raise VerificationMismatch(f"no verified proof for {path}")
        return {
            "path": str(path.resolve()),
            "sha256": record["sha256"],
            "crc32": record.get("crc32"),
            "bytes": int(record["signature"]["size"]),
            "last_write_utc_ticks": windows_last_write_ticks(record["signature"]),
        }

    def save(self) -> None:
        if not self._dirty:
            return
        self.path.parent.mkdir(parents=True, exist_ok=True)
        value = {"schema": CACHE_SCHEMA, "files": self.entries, "trees": self.trees}
        temporary = self.path.with_name(f".{self.path.name}.{os.getpid()}.tmp")
        temporary.write_text(
            json.dumps(value, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, self.path)
        self._dirty = False

    def summary(self, *, mode: str | None = None) -> dict[str, Any]:
        return {
            "mode": mode or ("full" if self.full_verify else "incremental"),
            "proofs_reused": self.proofs_reused,
            "proofs_recorded": self.proofs_recorded,
            "files_considered": self.files_considered,
            "files_hashed": self.files_hashed,
            "bytes_hashed": self.bytes_hashed,
            "elements_invalidated": sorted(self.invalidated),
            "verification_seconds": round(time.perf_counter() - self.started, 3),
            "cache_load_error": self.cache_load_error,
        }
