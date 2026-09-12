"""Assemble immutable, installable water QA batches without installing them.

Default mode is read-only. ``--run`` creates candidates and two generated
tracked manifests. It does not mutate BG2EE, run tests, package a release or
infer QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from build_water_route1_batch import ROOT, load_json, rel, sha256_file, write_json
from workspace_paths import get_path


DEFAULT_MATRIX = ROOT / ".tmp" / "water-phase23-20260912" / "matrix.json"
DEFAULT_FAMILY = ROOT / "pipeline" / "water" / "family-policy-v1.json"
DEFAULT_ROUTE1 = (ROOT / "maps" / "water-batches" / "runs" /
                  "voie1-alpha128-x4-20260912-v3" / "repair-report.json")
DEFAULT_SEAMS = (ROOT / "maps" / "water-batches" / "runs" /
                 "voie1-secondary-alpha-seams-x4-20260912-v1" / "repair-report.json")
DEFAULT_OVERLAYS = ROOT / "releases" / "BG2-HD-Upscale" / "manifests" / "overlay-sources.json"
DEFAULT_ROUTE2 = ROOT / "pipeline" / "water" / "route2-registry-v1.json"
DEFAULT_DLL = (ROOT / "build" / "iee-water-route2-registry-v2-20260912-vs2019" /
               "Release" / "InfinityEngine-Enhancer.dll")
DEFAULT_INI = ROOT / "build" / "water-route2-ar0900-20260912-q100" / "renderer" / "InfinityEngine-Enhancer.ini"
DEFAULT_OUTPUT = ROOT / "maps" / "water-batches" / "runs" / "qa-candidates-20260912-v1"
DEFAULT_MATRIX_OUT = ROOT / "pipeline" / "water" / "manifests" / "liquid-target-matrix-v1.json"
DEFAULT_BATCH_OUT = ROOT / "pipeline" / "water" / "manifests" / "qa-batches-20260912-v1.json"


def link_or_copy(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise RuntimeError(f"cible déjà présente: {target}")
    try:
        os.link(source, target)
    except OSError:
        shutil.copy2(source, target)


def snapshot(path: Path, name: str | None = None) -> dict[str, Any]:
    return {"name": name or path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def set_ini(source: Path, target: Path, strength: str) -> None:
    text = source.read_text(encoding="utf-8-sig")
    replacements = {
        "EnableWaterEffect": "true",
        "EnableWaterOverlayRoute2": "true",
        "WaterOverlayStrength": strength,
        "EnableDebugHotkeys": "false",
        "EnableTilePageDiagnostics": "true",
    }
    for key, value in replacements.items():
        pattern = re.compile(rf"(?m)^\s*{re.escape(key)}\s*=.*$")
        if not pattern.search(text):
            raise RuntimeError(f"clé INI absente: {key}")
        text = pattern.sub(f"{key} = {value}", text)
    target.write_text(text, encoding="utf-8")


def planned_state(row: dict[str, Any], family_id: str, repaired: dict[str, Any],
                  route2_entries: list[dict[str, Any]]) -> tuple[str, list[str], float]:
    for entry in route2_entries:
        if (entry["wed"]["resref"] == row["wed"] and
                entry["overlay"]["slot"] == row["overlay_slot"] and
                entry["overlay"]["tis_resref"] == row["overlay_resref"]):
            return "corrected", ["validated-reference-route1-and-route2"], float(entry["approved_strength"])
    if row["wed"] in repaired:
        reasons = ["route1-candidate-assembled", "route2-unapproved-q0"]
        if family_id != "lake-wtlake":
            reasons.append("family-qa-required")
        return "candidate-installable-pending-qa", reasons, 0.0
    if family_id in {"lake-teal-wtlaka-d", "pool-wtpool", "swamp-wtswam"}:
        return "candidate-installable-pending-qa", ["canonical-overlay-action-assembled", "route2-unapproved-q0"], 0.0
    if family_id == "lake-wtlake":
        if row["phase3_status"] == "already-conform-structural":
            return "already-conform", ["native-composition-kept", "route2-unapproved-q0"], 0.0
        return "blocked", ["qualified-map-review-required", "route2-unapproved-q0"], 0.0
    if family_id in {"sewage-wtsew", "oil-wtoil"}:
        return "already-conform", ["stock-overlay-native-q0", "dedicated-route2-material-unapproved"], 0.0
    if family_id == "lava-wtlava-d":
        return "blocked", ["water-alpha128-forbidden", "non-periodic-overlay", "dedicated-emissive-route-required"], 0.0
    if family_id == "brown-flowing-wt5000":
        return "blocked", ["liquid-classifier-unresolved", "dedicated-material-and-family-qa-required"], 0.0
    return "blocked", ["unhandled-family-fail-closed"], 0.0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--family-policy", type=Path, default=DEFAULT_FAMILY)
    parser.add_argument("--route1-report", type=Path, default=DEFAULT_ROUTE1)
    parser.add_argument("--seam-report", type=Path, default=DEFAULT_SEAMS)
    parser.add_argument("--overlay-sources", type=Path, default=DEFAULT_OVERLAYS)
    parser.add_argument("--route2-registry", type=Path, default=DEFAULT_ROUTE2)
    parser.add_argument("--renderer-dll", type=Path, default=DEFAULT_DLL)
    parser.add_argument("--renderer-ini", type=Path, default=DEFAULT_INI)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--matrix-output", type=Path, default=DEFAULT_MATRIX_OUT)
    parser.add_argument("--batch-output", type=Path, default=DEFAULT_BATCH_OUT)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()

    matrix = load_json(args.matrix)
    family = load_json(args.family_policy)
    route1 = load_json(args.route1_report)
    seams = load_json(args.seam_report)
    overlay_sources = load_json(args.overlay_sources)
    route2 = load_json(args.route2_registry)
    if family["seedvr"]["new_processing_color_correction_method"] != "none":
        raise RuntimeError("SeedVR none requis")
    overlay_family = {overlay: item["id"] for item in family["families"] for overlay in item["overlays"]}
    family_policy = {item["id"]: item for item in family["families"]}
    source_policy = {item["resref"]: item for item in overlay_sources["policies"]}
    repaired = {row["wed"]: row for row in route1["results"] if row.get("candidate")}
    for row in seams["results"]:
        repaired[row["wed"]] = row
    final_rows = []
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in matrix:
        family_id = overlay_family[row["overlay_resref"]]
        state, reasons, strength = planned_state(row, family_id, repaired, route2["entries"])
        target = {"wed": row["wed"], "variant": row["variant"],
                  "overlay_slot": row["overlay_slot"], "overlay": row["overlay_resref"],
                  "family": family_id, "state": state, "reasons": reasons,
                  "route2_strength": strength,
                  "qa": "validated-reference" if state == "corrected" else ("not-required" if state == "already-conform" else "pending"),
                  "installation": "reference-already-installed" if state == "corrected" else "not-run",
                  "release": "not-requested"}
        final_rows.append(target)
        by_family[family_id].append(target)
    state_counts = defaultdict(int)
    for row in final_rows:
        state_counts[row["state"]] += 1
    plan = {"schema": "bg2-water-qa-batch-plan-v1", "target_rows": len(final_rows),
            "wed_count": len({row["wed"] for row in final_rows}),
            "family_count": len(by_family), "state_counts": dict(sorted(state_counts.items())),
            "seedvr_color_correction_method": "none", "installation": "not-run"}
    if not args.run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    output = args.output.resolve()
    if ROOT not in output.parents or output.exists() or args.matrix_output.exists() or args.batch_output.exists():
        raise RuntimeError("sortie déjà existante ou hors workspace")
    output.mkdir(parents=True)
    if sha256_file(args.renderer_dll) != "9823C8C8F5F5DB46523947243BEDCC8D986A6740C5F97FC91121ED6C55C608C7":
        raise RuntimeError("DLL route2 v2 divergente")
    renderer_receipts = {}
    for name, strength in (("q0-native", "0.00"), ("q1-ar0900-reference", "1.00")):
        root = output / "renderer" / name
        root.mkdir(parents=True)
        link_or_copy(args.renderer_dll, root / "InfinityEngine-Enhancer.dll")
        set_ini(args.renderer_ini, root / "InfinityEngine-Enhancer.ini", strength)
        files = [snapshot(path) for path in sorted(root.iterdir())]
        receipt = {"schema": "bg2-water-renderer-candidate-receipt-v1", "status": "assembled-not-installed",
                   "route2_default": "fail-closed-q0", "requested_strength": float(strength),
                   "files": files}
        write_json(root / "candidate-receipt.json", receipt)
        renderer_receipts[name] = {"path": rel(root), "files": files,
                                   "receipt_sha256": sha256_file(root / "candidate-receipt.json")}
    game_override = Path(get_path("bg2ee_game_root")) / "override"
    batch_summaries = []
    for family_id, targets in sorted(by_family.items()):
        root = output / "batches" / family_id
        root.mkdir(parents=True)
        map_operations = []
        for wed in sorted({row["wed"] for row in targets} & set(repaired)):
            source = ROOT / repaired[wed]["candidate"]
            destination = root / "maps" / wed
            for path in sorted(source.iterdir()):
                if path.is_file():
                    target_path = destination / path.name
                    link_or_copy(path, target_path)
                    map_operations.append({"operation": "copy", "source": rel(target_path),
                                           "target": f"override/{path.name}", **snapshot(target_path)})
        overlay_operations = []
        for overlay in family_policy[family_id]["overlays"]:
            policy = source_policy.get(overlay)
            if policy and policy["policy"] == "package":
                source_root = ROOT / policy["source_path"]
                for expected in policy["files"]:
                    source = source_root / expected["name"]
                    if snapshot(source)["sha256"] != expected["sha256"] or source.stat().st_size != expected["bytes"]:
                        raise RuntimeError(f"overlay canonique divergent: {overlay}/{source.name}")
                    destination = root / "overlays" / source.name
                    link_or_copy(source, destination)
                    overlay_operations.append({"operation": "copy", "source": rel(destination),
                                               "target": f"override/{source.name}", **snapshot(destination)})
            elif policy and policy["policy"] == "stock":
                names = {f"{overlay}.TIS"}
                for row in matrix:
                    if row["overlay_resref"] == overlay:
                        names.update(f"{page}.PVRZ" for page in row["overlay_tis"]["pages"])
                for name in sorted(names):
                    live = game_override / name
                    overlay_operations.append({"operation": "remove-if-present",
                                               "target": f"override/{name}",
                                               "expected_live": snapshot(live) if live.is_file() else None})
            else:
                overlay_operations.append({"operation": "preserve-stock", "overlay": overlay})
        manifest = {"schema": "bg2-water-qa-batch-manifest-v1", "family": family_id,
                    "material": family_policy[family_id]["material"], "targets": targets,
                    "renderer": renderer_receipts["q0-native"],
                    "operations": [*map_operations, *overlay_operations],
                    "preconditions": ["close-game", "close-InfinityLoader", "transactional-backup", "verify-live-before-write"],
                    "qa": "separate-by-map-variant-and-family", "installation": "not-run",
                    "release": "not-requested"}
        write_json(root / "batch-manifest.json", manifest)
        receipt = {"schema": "bg2-water-qa-candidate-receipt-v1", "status": "assembled-not-installed",
                   "family": family_id, "manifest_sha256": sha256_file(root / "batch-manifest.json"),
                   "physical_files": [snapshot(path, rel(path)) for path in sorted(root.rglob("*")) if path.is_file()],
                   "installation_receipt": None, "qa_decision": "pending"}
        write_json(root / "candidate-receipt.json", receipt)
        batch_summaries.append({"family": family_id, "path": rel(root), "targets": len(targets),
                                "maps": len({row["wed"] for row in targets}),
                                "copy_operations": sum(item["operation"] == "copy" for item in manifest["operations"]),
                                "remove_operations": sum(item["operation"] == "remove-if-present" for item in manifest["operations"]),
                                "manifest_sha256": sha256_file(root / "batch-manifest.json"),
                                "receipt_sha256": sha256_file(root / "candidate-receipt.json")})
    matrix_manifest = {"schema": "bg2-liquid-target-matrix-v1", "version": 1,
                       "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                       "source_matrix_sha256": sha256_file(args.matrix),
                       "counts": {"targets": len(final_rows), "weds": len({row["wed"] for row in final_rows}),
                                  "families": len(by_family), "states": dict(sorted(state_counts.items()))},
                       "targets": final_rows}
    write_json(args.matrix_output, matrix_manifest)
    batch_manifest = {"schema": "bg2-water-qa-batches-v1", "version": 1,
                      "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                      "candidate_root": rel(output), "renderer": renderer_receipts,
                      "batches": batch_summaries, "matrix": rel(args.matrix_output),
                      "matrix_sha256": sha256_file(args.matrix_output),
                      "installation": "not-run", "tests": "not-run-user-choice",
                      "release": "not-requested"}
    write_json(args.batch_output, batch_manifest)
    write_json(output / "candidate-index.json", batch_manifest)
    print(json.dumps({**plan, "candidate_root": rel(output), "batches": len(batch_summaries)},
                     indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
