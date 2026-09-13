"""Audit the exhaustive one-map-at-a-time ingame liquid QA tracker."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACKING = ROOT / "pipeline" / "water" / "ingame-map-tracking-v1.json"
DEFAULT_MATRIX = ROOT / "pipeline" / "water" / "manifests" / "liquid-target-matrix-v1.json"
DEFAULT_RELEASE = ROOT / "pipeline" / "water" / "release-tracking-v1.json"
SHA_RE = re.compile(r"^[A-F0-9]{64}$")
AREA_RE = re.compile(r"^(AR|OH)[0-9]{4}$")
WED_RE = re.compile(r"^(AR|OH)[0-9]{4}N?$")
VALIDATED_QA = {"validated-ingame", "validated-current-fallback"}
BLOCKED_QA = {"blocked-family-qa", "blocked-preparation"}
WORK_STATES = {"queued", "active", "blocked", "done"}
PREPARATION_STATES = {"candidate-available", "native-baseline", "installed", "blocked"}
QA_STATES = VALIDATED_QA | BLOCKED_QA | {
    "session-accepted-variant-unresolved",
    "pending-ingame",
}
INSTALLATION_STATES = {"installed", "not-run"}


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _workspace_path(root: Path, raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        errors.append(f"{label}: path must be a non-empty workspace-relative string")
        return None
    path = (root / raw).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes workspace: {raw}")
        return None
    return path


def _matrix_maps(matrix: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for target in matrix.get("targets", []):
        grouped[str(target.get("wed", ""))].append(target)
    for targets in grouped.values():
        targets.sort(key=lambda item: (int(item.get("overlay_slot", 0)), str(item.get("overlay", ""))))
    return dict(sorted(grouped.items()))


def _expected_overlays(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "slot": row.get("overlay_slot"),
            "resref": row.get("overlay"),
            "family": row.get("family"),
            "candidate_state": row.get("state"),
            "route2_strength": row.get("route2_strength"),
            "reasons": row.get("reasons", []),
        }
        for row in rows
    ]


def validate_tracking(
    data: dict[str, Any],
    matrix: dict[str, Any],
    release: dict[str, Any],
    root: Path = ROOT,
    *,
    verify_files: bool = True,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if data.get("schema") != "bg2-water-ingame-map-tracking-v1" or data.get("version") != 1:
        errors.append("unsupported tracking schema/version")
    if matrix.get("schema") != "bg2-liquid-target-matrix-v1" or matrix.get("version") != 1:
        errors.append("unsupported liquid matrix schema/version")

    expected = _matrix_maps(matrix)
    matrix_targets = matrix.get("targets", [])
    expected_nights = sorted(
        wed for wed, rows in expected.items() if rows and rows[0].get("variant") == "night"
    )
    inventory = data.get("inventory", {})
    matrix_path = _workspace_path(root, inventory.get("path"), "inventory", errors)
    declared_hash = inventory.get("sha256")
    if not isinstance(declared_hash, str) or not SHA_RE.fullmatch(declared_hash):
        errors.append("inventory: invalid SHA-256")
    if verify_files and matrix_path is not None:
        if not matrix_path.is_file():
            errors.append(f"inventory: missing matrix: {inventory.get('path')}")
        elif isinstance(declared_hash, str) and sha256(matrix_path) != declared_hash:
            errors.append("inventory: matrix hash mismatch")
    if inventory.get("expected_maps") != len(expected):
        errors.append("inventory: expected_maps disagrees with matrix")
    if inventory.get("expected_overlay_targets") != len(matrix_targets):
        errors.append("inventory: expected_overlay_targets disagrees with matrix")
    if inventory.get("night_weds") != expected_nights:
        errors.append("inventory: night_weds disagrees with matrix")

    release_targets = {
        str(target.get("id")): target
        for target in release.get("targets", [])
        if isinstance(target, dict) and target.get("id")
    }
    evidence_ids = {
        str(item.get("id"))
        for item in release.get("evidence", [])
        if isinstance(item, dict) and item.get("id")
    }
    maps = data.get("maps", [])
    if not isinstance(maps, list) or not maps:
        errors.append("maps must be a non-empty list")
        maps = []
    map_ids = [str(item.get("id", "")) for item in maps if isinstance(item, dict)]
    weds = [str(item.get("wed", "")) for item in maps if isinstance(item, dict)]
    for value, count in Counter(map_ids).items():
        if count > 1:
            errors.append(f"duplicate map id: {value}")
    for value, count in Counter(weds).items():
        if count > 1:
            errors.append(f"duplicate map WED: {value}")
    actual_weds = set(weds)
    for wed in sorted(set(expected) - actual_weds):
        errors.append(f"missing map from tracking: {wed}")
    for wed in sorted(actual_weds - set(expected)):
        errors.append(f"map absent from liquid matrix: {wed}")
    if weds != sorted(weds):
        errors.append("maps must be sorted by WED")

    area_rows: dict[str, dict[str, str]] = {}
    if verify_files:
        with (root / "areas.csv").open("r", encoding="utf-8-sig", newline="") as stream:
            area_rows = {row["area_id"].upper(): row for row in csv.DictReader(stream)}

    work_counts: Counter[str] = Counter()
    qa_counts: Counter[str] = Counter()
    active_ids: list[str] = []
    referenced_release_ids: list[str] = []
    overlay_count = 0
    for index, item in enumerate(maps):
        if not isinstance(item, dict):
            errors.append(f"map[{index}]: must be an object")
            continue
        wed = str(item.get("wed", ""))
        label = str(item.get("id", f"#{index}"))
        variant = item.get("variant")
        area_id = str(item.get("area_id", ""))
        if not WED_RE.fullmatch(wed) or not AREA_RE.fullmatch(area_id):
            errors.append(f"map[{label}]: invalid area/WED")
        if item.get("id") != f"liquid-map:{wed}":
            errors.append(f"map[{label}]: id must derive from WED")
        expected_area = wed[:-1] if variant == "night" else wed
        if area_id != expected_area:
            errors.append(f"map[{label}]: area_id/variant mismatch")
        rows = expected.get(wed, [])
        if rows and any(row.get("variant") != variant for row in rows):
            errors.append(f"map[{label}]: variant disagrees with matrix")
        overlays = item.get("overlays", [])
        if overlays != _expected_overlays(rows):
            errors.append(f"map[{label}]: overlays disagree with matrix")
        overlay_count += len(overlays) if isinstance(overlays, list) else 0

        if verify_files:
            if area_id not in area_rows:
                errors.append(f"map[{label}]: area absent from areas.csv")
            elif variant == "night" and area_rows[area_id].get("has_night_variant") != "yes":
                errors.append(f"map[{label}]: night variant absent from areas.csv")

        for target_id in item.get("release_target_ids", []):
            referenced_release_ids.append(target_id)
            target = release_targets.get(target_id)
            if target is None:
                errors.append(f"map[{label}]: unknown release target: {target_id}")
            elif target.get("wed") != wed:
                errors.append(f"map[{label}]: release target belongs to another WED: {target_id}")
        for evidence_id in item.get("qa_evidence_ids", []):
            if evidence_id not in evidence_ids:
                errors.append(f"map[{label}]: unknown QA evidence: {evidence_id}")

        work_state = str(item.get("work_state", ""))
        qa_state = str(item.get("qa_state", ""))
        blockers = item.get("blockers", [])
        if work_state not in WORK_STATES:
            errors.append(f"map[{label}]: invalid work state")
        if item.get("preparation_state") not in PREPARATION_STATES:
            errors.append(f"map[{label}]: invalid preparation state")
        if qa_state not in QA_STATES:
            errors.append(f"map[{label}]: invalid QA state")
        if item.get("installation_state") not in INSTALLATION_STATES:
            errors.append(f"map[{label}]: invalid installation state")
        work_counts[work_state] += 1
        qa_counts[qa_state] += 1
        if work_state == "active":
            active_ids.append(label)
        if work_state == "done" and (qa_state not in VALIDATED_QA or blockers):
            errors.append(f"map[{label}]: done requires validated QA and no blocker")
        if work_state in {"queued", "active"} and (
            item.get("preparation_state") == "blocked" or qa_state in BLOCKED_QA
        ):
            errors.append(f"map[{label}]: blocked map cannot be queued/active")
        if work_state == "blocked" and not blockers:
            errors.append(f"map[{label}]: blocked map lacks blockers")

    for target_id, count in Counter(referenced_release_ids).items():
        if count > 1:
            errors.append(f"release target referenced more than once: {target_id}")
    expected_release_ids = {
        target_id
        for target_id, target in release_targets.items()
        if target.get("wed") in expected
    }
    for target_id in sorted(expected_release_ids - set(referenced_release_ids)):
        errors.append(f"release target absent from map tracking: {target_id}")

    workflow = data.get("workflow", {})
    if workflow.get("mode") != "one-map-at-a-time":
        errors.append("workflow: unsupported mode")
    active_map_id = workflow.get("active_map_id")
    expected_active = [] if active_map_id is None else [active_map_id]
    if active_ids != expected_active:
        errors.append("workflow: active_map_id must identify the single active map")

    actual_counts = {
        "maps": len(maps),
        "overlay_targets": overlay_count,
        "night_maps": sum(1 for item in maps if isinstance(item, dict) and item.get("variant") == "night"),
        "work_states": dict(sorted(work_counts.items())),
        "qa_states": dict(sorted(qa_counts.items())),
    }
    summary = dict(actual_counts)
    summary["active_map_id"] = active_map_id
    summary["complete_inventory"] = set(expected) == actual_weds and overlay_count == len(matrix_targets)
    return errors, summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracking", type=Path, default=DEFAULT_TRACKING)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    paths = []
    for path in (args.tracking, args.matrix, args.release):
        paths.append(path if path.is_absolute() else ROOT / path)
    try:
        data, matrix, release = (load_json(path) for path in paths)
        errors, summary = validate_tracking(data, matrix, release)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors, summary = [str(error)], {}
    result = {"valid": not errors, "summary": summary, "errors": errors}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("WATER_INGAME_TRACKING=" + ("VALID" if not errors else "INVALID"))
        if summary:
            print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
        for error in errors:
            print(f"ERROR: {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
