"""Audit water release preparation and explicitly authorized integrations."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TRACKING = ROOT / "pipeline" / "water" / "release-tracking-v1.json"
SHA_RE = re.compile(r"^[A-F0-9]{64}$")
AREA_RE = re.compile(r"^(AR|OH)[0-9]{4}$")
WED_RE = re.compile(r"^(AR|OH)[0-9]{4}N?$")
QA_STATES = {
    "validated-ingame",
    "validated-current-fallback",
    "session-accepted-variant-unresolved",
    "pending-ingame",
    "blocked-family-qa",
}
VALIDATED_QA = {"validated-ingame", "validated-current-fallback"}
MATERIALS = {
    "lake-wtlake": 1,
    "pool-wtpool": 1,
    "sewage-wtsew": 4,
    "swamp-wtswam": 5,
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("tracking root must be an object")
    return value


def _duplicates(values: list[str]) -> list[str]:
    return sorted(value for value, count in Counter(values).items() if count > 1)


def _workspace_path(root: Path, raw: Any, label: str, errors: list[str]) -> Path | None:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute():
        errors.append(f"{label}: path must be a non-empty workspace-relative string")
        return None
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        errors.append(f"{label}: path escapes workspace: {raw}")
        return None
    return candidate


def _verify_file(
    root: Path,
    item: dict[str, Any],
    label: str,
    errors: list[str],
    verify_files: bool,
) -> None:
    path = _workspace_path(root, item.get("path"), label, errors)
    expected = item.get("sha256")
    if not isinstance(expected, str) or not SHA_RE.fullmatch(expected):
        errors.append(f"{label}: invalid SHA-256")
    if not verify_files or path is None:
        return
    if not path.is_file():
        errors.append(f"{label}: missing file: {item.get('path')}")
        return
    if "bytes" in item and path.stat().st_size != item["bytes"]:
        errors.append(f"{label}: byte count mismatch: {item.get('path')}")
    if isinstance(expected, str) and SHA_RE.fullmatch(expected) and sha256(path) != expected:
        errors.append(f"{label}: hash mismatch: {item.get('path')}")


def validate_tracking(
    data: dict[str, Any],
    root: Path = ROOT,
    *,
    verify_files: bool = True,
    verify_git: bool = True,
) -> tuple[list[str], dict[str, Any]]:
    errors: list[str] = []
    if data.get("schema") != "bg2-water-release-tracking-v1" or data.get("version") != 1:
        errors.append("unsupported schema/version")

    boundary = data.get("release_boundary", {})
    authorization = boundary.get("authorization")
    release_authorized = bool(
        isinstance(authorization, str)
        and re.fullmatch(r"explicit-user-request-[0-9]{4}-[0-9]{2}-[0-9]{2}", authorization)
    )
    if authorization not in {"not-requested"} and not release_authorized:
        errors.append("invalid release authorization record")
    expected_modified = release_authorized
    if boundary.get("release_manifests_modified") is not expected_modified:
        errors.append("release_manifests_modified disagrees with release authorization")

    evidence = data.get("evidence", [])
    if not isinstance(evidence, list) or not evidence:
        errors.append("evidence must be a non-empty list")
        evidence = []
    evidence_ids = [str(item.get("id", "")) for item in evidence if isinstance(item, dict)]
    for duplicate in _duplicates(evidence_ids):
        errors.append(f"duplicate evidence id: {duplicate}")
    evidence_by_id = {
        str(item.get("id")): item for item in evidence if isinstance(item, dict) and item.get("id")
    }
    for evidence_id, item in evidence_by_id.items():
        _verify_file(root, item, f"evidence[{evidence_id}]", errors, verify_files)

    artifact_sets = data.get("artifact_sets", [])
    if not isinstance(artifact_sets, list) or not artifact_sets:
        errors.append("artifact_sets must be a non-empty list")
        artifact_sets = []
    artifact_ids = [str(item.get("id", "")) for item in artifact_sets if isinstance(item, dict)]
    for duplicate in _duplicates(artifact_ids):
        errors.append(f"duplicate artifact set id: {duplicate}")
    artifact_by_id = {
        str(item.get("id")): item
        for item in artifact_sets
        if isinstance(item, dict) and item.get("id")
    }
    for artifact_id, item in artifact_by_id.items():
        for evidence_id in item.get("evidence_ids", []):
            if evidence_id not in evidence_by_id:
                errors.append(f"artifact[{artifact_id}]: unknown evidence: {evidence_id}")
        roots = item.get("payload_roots", [])
        if not isinstance(roots, list) or not roots:
            errors.append(f"artifact[{artifact_id}]: missing payload roots")
        for index, raw in enumerate(roots if isinstance(roots, list) else []):
            path = _workspace_path(root, raw, f"artifact[{artifact_id}].payload[{index}]", errors)
            if verify_files and path is not None and not path.is_dir():
                errors.append(f"artifact[{artifact_id}]: missing payload root: {raw}")

    runtime = data.get("runtime", {})
    registry_id = runtime.get("registry_evidence_id")
    if registry_id not in evidence_by_id:
        errors.append(f"runtime: unknown registry evidence: {registry_id}")
    elif evidence_by_id[registry_id].get("kind") != "route2-registry":
        errors.append("runtime registry evidence has wrong kind")
    for key in ("dll", "ini"):
        item = runtime.get(key)
        if not isinstance(item, dict):
            errors.append(f"runtime.{key}: missing file record")
        else:
            _verify_file(root, item, f"runtime.{key}", errors, verify_files)
    for key in ("shaders", "textures"):
        items = runtime.get(key, [])
        if not isinstance(items, list):
            errors.append(f"runtime.{key}: must be a list")
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"runtime.{key}[{index}]: must be an object")
            else:
                _verify_file(root, item, f"runtime.{key}[{index}]", errors, verify_files)
    commit = runtime.get("source_commit")
    if not isinstance(commit, str) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        errors.append("runtime.source_commit: invalid full commit id")
    elif verify_git:
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
            cwd=root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        if result.returncode != 0:
            errors.append(f"runtime.source_commit: commit unavailable: {commit}")

    areas_path = root / "areas.csv"
    area_rows: dict[str, dict[str, str]] = {}
    if verify_files:
        if not areas_path.is_file():
            errors.append("areas.csv missing")
        else:
            with areas_path.open("r", encoding="utf-8-sig", newline="") as stream:
                area_rows = {row["area_id"].upper(): row for row in csv.DictReader(stream)}

    targets = data.get("targets", [])
    if not isinstance(targets, list) or not targets:
        errors.append("targets must be a non-empty list")
        targets = []
    target_ids = [str(item.get("id", "")) for item in targets if isinstance(item, dict)]
    for duplicate in _duplicates(target_ids):
        errors.append(f"duplicate target id: {duplicate}")
    identities: list[str] = []
    qa_counts: Counter[str] = Counter()
    blocker_count = 0
    for index, target in enumerate(targets):
        if not isinstance(target, dict):
            errors.append(f"target[{index}]: must be an object")
            continue
        target_id = str(target.get("id", f"#{index}"))
        area_id = str(target.get("area_id", "")).upper()
        wed = str(target.get("wed", "")).upper()
        variant = target.get("variant")
        identity = f"{wed}:{target.get('overlay', '')}"
        identities.append(identity)
        if not AREA_RE.fullmatch(area_id) or not WED_RE.fullmatch(wed):
            errors.append(f"target[{target_id}]: invalid area/WED")
        if variant == "night" and wed != area_id + "N":
            errors.append(f"target[{target_id}]: night WED must equal area_id + N")
        if variant == "day-or-unique" and wed != area_id:
            errors.append(f"target[{target_id}]: day/unique WED must equal area_id")
        family = target.get("family")
        if family not in MATERIALS or target.get("material_id") != MATERIALS.get(family):
            errors.append(f"target[{target_id}]: family/material mismatch")
        strength = target.get("route2_strength")
        if not isinstance(strength, (int, float)) or not 0 <= float(strength) <= 1:
            errors.append(f"target[{target_id}]: invalid route2 strength")
        qa_state = target.get("qa_state")
        qa_counts[str(qa_state)] += 1
        if qa_state not in QA_STATES:
            errors.append(f"target[{target_id}]: invalid QA state")
        qa_id = target.get("qa_evidence_id")
        if qa_state in VALIDATED_QA:
            if qa_id not in evidence_by_id:
                errors.append(f"target[{target_id}]: validated QA lacks evidence")
            elif evidence_by_id[qa_id].get("kind") != "qa-decision":
                errors.append(f"target[{target_id}]: QA evidence has wrong kind")
        for artifact_id in target.get("artifact_set_ids", []):
            if artifact_id not in artifact_by_id:
                errors.append(f"target[{target_id}]: unknown artifact set: {artifact_id}")
        blockers = target.get("blockers", [])
        if not isinstance(blockers, list):
            errors.append(f"target[{target_id}]: blockers must be a list")
        else:
            blocker_count += len(blockers)
        release_state = target.get("release_state")
        if release_state not in {"not-evaluated", "integrated"}:
            errors.append(f"target[{target_id}]: tracking cannot approve release")
        elif release_state == "integrated":
            if not release_authorized:
                errors.append(f"target[{target_id}]: integration lacks release authorization")
            if qa_state not in VALIDATED_QA or not isinstance(blockers, list) or blockers:
                errors.append(f"target[{target_id}]: integrated target is not fully validated")
        if verify_files and area_id in area_rows and qa_state in VALIDATED_QA:
            field = "status_nuit" if variant == "night" else "status"
            if area_rows[area_id].get(field) != "validated-installed":
                errors.append(f"target[{target_id}]: areas.csv {field} is not validated-installed")
        elif verify_files and area_id not in area_rows:
            errors.append(f"target[{target_id}]: area absent from areas.csv")
    for duplicate in _duplicates(identities):
        errors.append(f"duplicate target identity: {duplicate}")

    runtime_blockers = runtime.get("release_blockers", [])
    if not isinstance(runtime_blockers, list):
        errors.append("runtime.release_blockers must be a list")
        runtime_blockers = []
    technical_ready = (
        all(target.get("qa_state") in VALIDATED_QA for target in targets if isinstance(target, dict))
        and blocker_count == 0
        and not runtime_blockers
    )
    summary = {
        "evidence": len(evidence_by_id),
        "artifact_sets": len(artifact_by_id),
        "targets": len(targets),
        "qa_states": dict(sorted(qa_counts.items())),
        "target_blockers": blocker_count,
        "runtime_blockers": len(runtime_blockers),
        "release_authorized": release_authorized,
        "release_candidate_ready": technical_ready,
    }
    return errors, summary


def release_gate_reasons(data: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    for target in data.get("targets", []):
        if target.get("qa_state") not in VALIDATED_QA:
            reasons.append(f"{target.get('id')}:qa={target.get('qa_state')}")
        for blocker in target.get("blockers", []):
            reasons.append(f"{target.get('id')}:{blocker}")
    for blocker in data.get("runtime", {}).get("release_blockers", []):
        reasons.append(f"runtime:{blocker}")
    return reasons


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tracking", type=Path, default=DEFAULT_TRACKING)
    parser.add_argument("--release-gate", action="store_true", help="fail until all tracked targets and runtime are release-ready")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args(argv)
    tracking = args.tracking if args.tracking.is_absolute() else ROOT / args.tracking
    try:
        data = load_json(tracking)
        errors, summary = validate_tracking(data)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        errors, summary = [str(error)], {}
        data = {}
    gate_reasons = release_gate_reasons(data) if args.release_gate and not errors else []
    result = {"valid": not errors, "summary": summary, "errors": errors, "release_gate_reasons": gate_reasons}
    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("WATER_RELEASE_TRACKING=" + ("VALID" if not errors else "INVALID"))
        if summary:
            print(json.dumps(summary, sort_keys=True, ensure_ascii=False))
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        for reason in gate_reasons:
            print(f"GATE: {reason}")
    return 1 if errors or gate_reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
