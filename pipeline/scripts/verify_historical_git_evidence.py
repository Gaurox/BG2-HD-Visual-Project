"""Verify a sealed QA evidence hash against an explicitly pinned Git blob."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "animations/index/qa-evidence-migrations.json"


def read_migrations(path: Path = MIGRATIONS) -> list[dict[str, str]]:
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "bg2-upscale-animation-qa-evidence-migrations-v1":
        raise ValueError("unsupported animation QA evidence migration schema")
    return list(data.get("migrations", []))


def reference_label(entry: dict[str, str]) -> str:
    """Return the immutable source label recorded for a compatibility entry."""
    if "snapshot_path" in entry:
        return f"{entry['snapshot_path']} (recovered Git blob {entry['git_blob']})"
    return f"{entry['git_commit']}:{entry['path']}"


def verify_reference(
    relative_path: str,
    expected_sha256: str,
    *,
    root: Path = ROOT,
    migrations_path: Path = MIGRATIONS,
) -> dict[str, str] | None:
    normalized_path = relative_path.replace("\\", "/").lstrip("./")
    normalized_hash = expected_sha256.upper()
    matches = [
        entry
        for entry in read_migrations(migrations_path)
        if entry.get("path") == normalized_path
        and str(entry.get("sha256", "")).upper() == normalized_hash
    ]
    if len(matches) != 1:
        return None
    entry = matches[0]
    snapshot_path = entry.get("snapshot_path")
    try:
        if snapshot_path:
            snapshot = (root / snapshot_path).resolve()
            snapshot.relative_to(root.resolve())
            if not snapshot.is_file():
                return None
            content = snapshot.read_bytes()
            blob = subprocess.run(
                ["git", "hash-object", "--stdin"],
                cwd=root,
                check=True,
                input=content,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.decode("ascii").strip()
        else:
            revision = f"{entry['git_commit']}:{entry['path']}"
            blob = subprocess.run(
                ["git", "rev-parse", revision],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            ).stdout.strip()
            content = subprocess.run(
                ["git", "show", revision],
                cwd=root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout
    except (OSError, ValueError, subprocess.CalledProcessError):
        return None
    if blob != entry["git_blob"]:
        return None
    if hashlib.sha256(content).hexdigest().upper() != normalized_hash:
        return None
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--path", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    entry = verify_reference(args.path, args.sha256)
    if entry is None:
        return 1
    if not args.quiet:
        print(f"verified historical Git evidence: {reference_label(entry)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
