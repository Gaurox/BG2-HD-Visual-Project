"""Move conservatively obsolete animation artifacts to a configured external archive.

The command is plan-only unless ``--run`` is supplied. It never deletes data:
whole directories are renamed to the external archive on the same volume, and a
portable receipt records their pre/post-move inventories.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

from workspace_paths import get_path


ROOT = Path(__file__).resolve().parents[2]
PACK_ROOT = ROOT / "animations/packs-par-zone"
RETENTION = ROOT / "animations/index/post-p3-pack-retention-20260902.json"
CLEANUP_SCRIPT = ROOT / "pipeline/scripts/audit_animation_pack_cleanup.py"
RECEIPT = ROOT / "docs/workspace-archive-manifest-animation-20260907.json"
ARCHIVE_RELATIVE = Path("animations/cleanup-20260907")
EXPECTED_PACK_COUNT = 128
FAILED_RUNS = (
    Path("animations/runs/ar0700-all-bam-seedvr7b-lab-x4"),
    Path("animations/batches/ar0904-taloscircle-spatial-x4-20260906"),
    Path("animations/batches/ar0904-taloscircle-spatial-x4-20260906-r2"),
)
CURRENT_REFERENCE_FILES = (
    ROOT / "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json",
    ROOT / "asset-tracking/registry.json",
)
RETAINED_CLASSES = {
    "release-source",
    "qa-lineage",
    "retained-qa-evidence",
    "pending-qa-processing-evidence",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def atomic_write(path: Path, value: Any) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(json_bytes(value))
    os.replace(temporary, path)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def constants_from_cleanup_script() -> dict[str, dict[str, str]]:
    tree = ast.parse(CLEANUP_SCRIPT.read_text(encoding="utf-8-sig"))
    values: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "KEEP_ACTIVE"
        ):
            values[node.target.id] = ast.literal_eval(node.value)
    if "KEEP_ACTIVE" not in values:
        raise RuntimeError("KEEP_ACTIVE is unavailable in the P3 cleanup audit")
    return values


def authority_text() -> str:
    files = list(CURRENT_REFERENCE_FILES)
    index_root = ROOT / "animations/index"
    for path in index_root.rglob("*"):
        if not path.is_file():
            continue
        if (
            "qa-decisions" in path.parts
            or "selections" in path.parts
            or path.name in {"index.json", "animations.csv"}
        ):
            files.append(path)
    return "\n".join(
        path.read_text(encoding="utf-8-sig", errors="ignore")
        for path in files
        if path.is_file()
    )


def classify_packs() -> tuple[list[Path], list[Path]]:
    roots = sorted((path for path in PACK_ROOT.iterdir() if path.is_dir()), key=lambda p: p.name)
    retention = read_json(RETENTION)
    special = {
        str(entry["name"])
        for entry in retention.get("packs", [])
        if str(entry.get("classification", "")) in RETAINED_CLASSES
    }
    manifestless = {path.name for path in roots if not (path / "manifest.json").is_file()}
    text = authority_text()
    referenced = {path.name for path in roots if path.name in text}
    keep = (
        set(constants_from_cleanup_script()["KEEP_ACTIVE"])
        | special
        | manifestless
        | referenced
    )
    kept = [path for path in roots if path.name in keep]
    movable = [path for path in roots if path.name not in keep]
    if len(roots) != 174 or len(kept) != 46 or len(movable) != EXPECTED_PACK_COUNT:
        raise RuntimeError(
            "pack inventory changed since the reviewed analysis: "
            f"total={len(roots)}, keep={len(kept)}, move={len(movable)}"
        )
    missing_manifests = [path.name for path in movable if not (path / "manifest.json").is_file()]
    if missing_manifests:
        raise RuntimeError(f"movable packs without root manifest: {missing_manifests}")
    return kept, movable


def inventory(path: Path) -> dict[str, Any]:
    files = [item for item in path.rglob("*") if item.is_file()]
    manifest = path / "manifest.json"
    return {
        "file_count": len(files),
        "bytes": sum(item.stat().st_size for item in files),
        "manifest_sha256": sha256_file(manifest) if manifest.is_file() else None,
    }


def portable_source(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def target_for(source: Path, archive_root: Path) -> Path:
    relative = source.relative_to(ROOT / "animations")
    return archive_root / ARCHIVE_RELATIVE / relative


def operation(source: Path, archive_root: Path) -> dict[str, Any]:
    target = target_for(source, archive_root)
    return {
        "source": portable_source(source),
        "target": (
            "config://animation_artifacts_archive/"
            + target.relative_to(archive_root).as_posix()
        ),
        **inventory(source),
        "state": "planned",
    }


def validate_destination(archive_root: Path) -> None:
    root_resolved = ROOT.resolve()
    archive_resolved = archive_root.resolve()
    if archive_resolved == root_resolved or root_resolved in archive_resolved.parents:
        raise RuntimeError(f"archive destination is inside the project: {archive_root}")
    if archive_resolved.anchor.casefold() != root_resolved.anchor.casefold():
        raise RuntimeError("archive must be on the same volume for rename-only moves")
    target_root = archive_root / ARCHIVE_RELATIVE
    if target_root.exists():
        raise RuntimeError(f"archive batch already exists: {target_root}")


def build_plan(archive_root: Path) -> tuple[list[Path], dict[str, Any]]:
    kept, packs = classify_packs()
    failed = [ROOT / path for path in FAILED_RUNS]
    for path in failed:
        if not path.is_dir():
            raise RuntimeError(f"failed run is unavailable: {portable_source(path)}")
        manifest = read_json(path / "manifest.json")
        if manifest.get("status") != "failed":
            raise RuntimeError(f"run is no longer failed: {portable_source(path)}")
    sources = [*packs, *failed]
    operations = [operation(path, archive_root) for path in sources]
    plan = {
        "schema": "bg2-upscale-animation-external-archive-v1",
        "captured_utc": datetime.now(timezone.utc).isoformat(),
        "authority_policy": (
            "Physical lifecycle receipt only. Archived data grants no production, QA, "
            "installation, selection or release status. Restore only an explicitly needed root."
        ),
        "archive_root": "config://animation_artifacts_archive",
        "archive_batch": ARCHIVE_RELATIVE.as_posix(),
        "selection": {
            "reviewed_pack_inventory_count": 174,
            "kept_pack_count": len(kept),
            "moved_pack_count": len(packs),
            "moved_failed_run_count": len(failed),
            "completed_unique_unselected_runs_left_in_project": 85,
        },
        "summary": {
            "operation_count": len(operations),
            "file_count": sum(int(item["file_count"]) for item in operations),
            "bytes": sum(int(item["bytes"]) for item in operations),
        },
        "operations": operations,
    }
    return sources, plan


def run_archive(archive_root: Path, sources: list[Path], receipt: dict[str, Any]) -> None:
    batch = archive_root / ARCHIVE_RELATIVE
    batch.mkdir(parents=True, exist_ok=False)
    journal = batch / "archive-manifest.json"
    atomic_write(journal, receipt)
    for source, entry in zip(sources, receipt["operations"], strict=True):
        target = target_for(source, archive_root)
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
        actual = inventory(target)
        expected = {key: entry[key] for key in ("file_count", "bytes", "manifest_sha256")}
        if actual != expected:
            raise RuntimeError(f"post-move inventory mismatch: {entry['source']}")
        entry["state"] = "archived"
        atomic_write(journal, receipt)
    receipt["completed_utc"] = datetime.now(timezone.utc).isoformat()
    receipt["status"] = "complete"
    atomic_write(journal, receipt)
    RECEIPT.write_bytes(json_bytes(receipt))


def check_archive(archive_root: Path) -> list[str]:
    errors: list[str] = []
    if not RECEIPT.is_file():
        return [f"missing receipt: {RECEIPT.relative_to(ROOT).as_posix()}"]
    receipt = read_json(RECEIPT)
    if receipt.get("status") != "complete":
        errors.append("tracked archive receipt is not complete")
    external_receipt = archive_root / ARCHIVE_RELATIVE / "archive-manifest.json"
    if not external_receipt.is_file():
        errors.append("external archive receipt is missing")
    elif external_receipt.read_bytes() != RECEIPT.read_bytes():
        errors.append("tracked and external archive receipts differ")
    for entry in receipt.get("operations", []):
        source = ROOT / str(entry["source"])
        relative_target = str(entry["target"]).removeprefix(
            "config://animation_artifacts_archive/"
        )
        target = archive_root / relative_target
        if source.exists():
            errors.append(f"archived source returned: {entry['source']}")
            continue
        if not target.is_dir():
            errors.append(f"archive target is missing: {entry['target']}")
            continue
        actual = inventory(target)
        expected = {key: entry[key] for key in ("file_count", "bytes", "manifest_sha256")}
        if actual != expected:
            errors.append(f"archive inventory changed: {entry['target']}")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--run", action="store_true", help="Perform the reviewed moves.")
    mode.add_argument("--check", action="store_true", help="Verify the completed external archive.")
    args = parser.parse_args(argv)
    try:
        archive_root = get_path("animation_artifacts_archive", required=True)
        if args.check:
            errors = check_archive(archive_root)
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
            if errors:
                return 1
            receipt = read_json(RECEIPT)
            print(
                "animation external archive: OK; "
                f"{receipt['summary']['operation_count']} roots, "
                f"{receipt['summary']['bytes']} bytes"
            )
            return 0
        validate_destination(archive_root)
        sources, receipt = build_plan(archive_root)
        summary = receipt["summary"]
        print(
            f"animation archive plan: {summary['operation_count']} roots, "
            f"{summary['file_count']} files, {summary['bytes']} bytes"
        )
        if not args.run:
            print("plan only; pass --run to move the roots")
            return 0
        run_archive(archive_root, sources, receipt)
        print(f"animation archive complete: {summary['bytes']} bytes moved")
        return 0
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
