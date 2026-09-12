"""Build the exact AR1000-day WTPOOL2 route2 registry candidate.

Plan-only by default. ``--run`` creates a new immutable run. It does not
compile or install the renderer and never touches release content.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from build_ar1000_wtpool_route1_candidate import ROOT, parse_wed, relative, require, sha256_file, write_json
from build_wtlake_timeline_batch import pvrz_metadata, tis_metadata
from workspace_paths import get_path


AREA = "AR1000"
FAMILY = "pool-wtpool"
OVERLAY = "WTPOOL2"
PAGE = "WPOOL200"
STRENGTH = 0.70
MATERIAL_ID = 1
FRAME_COUNT = 36
SOURCE_FPS = 15.0
TARGET_FPS = 30.0
ATLAS_COLUMNS = 7
ATLAS_PADDING = 4
ATLAS_STRIDE = 264
PARENT_REGISTRY = ROOT / "maps/water-batches/runs/ar0300n-reflections-alpha160-20260912-v10/registry-v3.json"
ROUTE1_PLAN = ROOT / "maps/water-batches/runs/ar1000-wtpool-route1-20260912-v1/plan.json"
ASSET_RUN = ROOT / "maps/water-batches/runs/ar1000-wtpool-periodic-bilinear-20260912-v3"


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"JSON absent: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def snapshot(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"fichier absent ou non sûr: {path}")
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}


def create_plan(output: Path) -> dict[str, Any]:
    parent = load_json(PARENT_REGISTRY)
    route1 = load_json(ROUTE1_PLAN)
    asset_manifest = load_json(ASSET_RUN / "candidate/manifest.json")
    game = get_path("bg2ee_game_root")
    override = game / "override"
    require(parent["schema"] == "bg2-water-route2-registry-v3", "registre parent incompatible")
    require(not any(entry["wed"]["resref"] == AREA for entry in parent["entries"]),
            "AR1000 existe déjà dans le registre parent")
    require(asset_manifest["files"]["AR1000.WED"] == snapshot(override / "AR1000.WED"),
            "WED AR1000 live divergent du candidat v3")
    require(asset_manifest["files"][f"{OVERLAY}.TIS"] == snapshot(override / f"{OVERLAY}.TIS"),
            "TIS WTPOOL2 live divergent du candidat v3")
    require(asset_manifest["files"][f"{PAGE}.PVRZ"] == snapshot(override / f"{PAGE}.PVRZ"),
            "page WTPOOL2 live divergente du candidat v3")
    base = route1["route1"]["base_tis"]
    require(snapshot(override / "AR1000.TIS") == {"bytes": base["bytes"], "sha256": base["sha256"]},
            "base AR1000.TIS live divergente")
    for page in base["pages"]:
        require(snapshot(override / f"{page['resref']}.PVRZ") ==
                {"bytes": page["bytes"], "sha256": page["sha256"]},
                f"page base live divergente: {page['resref']}")
    wed = override / "AR1000.WED"
    parsed = parse_wed(wed.read_bytes(), OVERLAY)
    overlay_meta, overlay_paths = tis_metadata(OVERLAY, override)
    require(parsed["slots"] == ["AR1000", OVERLAY, "", "", ""], "slots WED divergents")
    require(parsed["base"]["width"] == 80 and parsed["base"]["height"] == 60,
            "grille WED divergente")
    require(parsed["coverage"] == 37 and parsed["flagged_without_secondary"] == 0,
            "couverture WTPOOL2 divergente")
    require(parsed["timeline_frames"] == FRAME_COUNT and parsed["source_speed"] == 1,
            "timeline WED divergente")
    require(overlay_meta["tile_count"] == FRAME_COUNT and overlay_meta["tile_dimension"] == 256,
            "timeline TIS divergente")
    require([path.name for path in overlay_paths] == [f"{OVERLAY}.TIS", f"{PAGE}.PVRZ"],
            "inventaire overlay divergent")
    return {
        "schema": "bg2-ar1000-wtpool-route2-plan-v1",
        "status": "planned-not-run",
        "scope": {"area": AREA, "variant": "day", "night": "excluded", "family": FAMILY},
        "output": relative(output),
        "trigger": "route1-v3 accepted without grid but rejected as visually frozen",
        "source": {
            "asset_run": relative(ASSET_RUN),
            "asset_manifest_sha256": sha256_file(ASSET_RUN / "candidate/manifest.json"),
            "parent_registry": relative(PARENT_REGISTRY),
            "parent_registry_sha256": sha256_file(PARENT_REGISTRY),
        },
        "parameters": {
            "timeline_frames": FRAME_COUNT,
            "source_fps": SOURCE_FPS,
            "renderer_fps": TARGET_FPS,
            "route2_strength": STRENGTH,
            "material_id": MATERIAL_ID,
            "atlas_columns": ATLAS_COLUMNS,
            "atlas_stride_pixels": ATLAS_STRIDE,
            "atlas_padding_pixels": ATLAS_PADDING,
        },
        "preconditions": {
            "route1": "spatial appearance accepted by user; no repeated grid",
            "route2": "necessary after user reports static water at q0",
            "family": "pool-specific exact AR1000-day candidate; no generalization",
        },
        "tests": "none-user-choice",
        "release": "not-requested",
    }


def execute(plan: dict[str, Any], output: Path) -> dict[str, Any]:
    require(not output.exists(), f"immutable run already exists: {output}")
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    parent = load_json(PARENT_REGISTRY)
    route1 = load_json(ROUTE1_PLAN)
    override = get_path("bg2ee_game_root") / "override"
    wed_path = override / "AR1000.WED"
    parsed = parse_wed(wed_path.read_bytes(), OVERLAY)
    overlay_meta, _paths = tis_metadata(OVERLAY, override)
    overlay_page = pvrz_metadata(override / f"{PAGE}.PVRZ")
    entry = {
        "id": "wtpool-ar1000-day-slot1-q070-v12",
        "state": "candidate-installable-pending-qa",
        "wed": {
            "resref": AREA,
            "sha256": sha256_file(wed_path),
            "grid": {"width": parsed["base"]["width"], "height": parsed["base"]["height"]},
            "overlay_slots": parsed["slots"],
        },
        "base_tis": route1["route1"]["base_tis"],
        "overlay": {
            "slot": 1,
            "tis_resref": OVERLAY,
            "tis_sha256": overlay_meta["sha256"],
            "tis_bytes": overlay_meta["bytes"],
            "tile_count": overlay_meta["tile_count"],
            "tile_dimension": overlay_meta["tile_dimension"],
            "pages": [overlay_page],
        },
        "approved_strength": STRENGTH,
        "overlay_coverage_cells": parsed["coverage"],
        "allow_stock_wed_when_override_absent": False,
        "material_id": MATERIAL_ID,
        "temporal_overlay": {
            "mode": "atlas-linear",
            "frame_count": FRAME_COUNT,
            "source_fps": SOURCE_FPS,
            "target_fps": TARGET_FPS,
            "atlas_columns": ATLAS_COLUMNS,
            "atlas_stride_pixels": ATLAS_STRIDE,
            "atlas_padding_pixels": ATLAS_PADDING,
        },
        "qa": {
            "status": "pending-ingame",
            "reference": "pool-wtpool candidate derived from validated water parameters; AR1000 day only",
        },
    }
    registry = dict(parent)
    # Registry-v3 is deliberately flat: the generator accepts only the active
    # v2 authority as its structural parent. Keep the cumulative v10 provenance
    # in the experiment metadata instead of creating an unsupported v3 chain.
    registry["parent"] = parent["parent"]
    registry["entries"] = [*parent["entries"], entry]
    registry["status"] = "experimental-pending-ingame-qa"
    registry["experiment"] = {
        "scope": [AREA],
        "variant": "day",
        "night": "excluded",
        "family": FAMILY,
        "strength": STRENGTH,
        "parent_candidate": {
            "path": relative(PARENT_REGISTRY),
            "sha256": sha256_file(PARENT_REGISTRY),
            "bytes": PARENT_REGISTRY.stat().st_size,
        },
        "reason": "route1 v3 removed SeedVR grid but q0 appeared static; apply 36-phase 15 Hz plus renderer blend 30 FPS and current q0.70",
        "unknown_or_divergent_identity": "q0-native",
        "qa": "pending-ingame",
    }
    registry_path = output / "registry-v3.json"
    write_json(registry_path, registry)
    manifest = {
        "schema": "bg2-water-route2-candidate-manifest-v1",
        "status": "candidate-installable-pending-ingame-qa",
        "scope": plan["scope"],
        "registry": {"path": relative(registry_path), **snapshot(registry_path)},
        "entry_id": entry["id"],
        "parameters": plan["parameters"],
        "assets": {
            "AR1000.WED": snapshot(override / "AR1000.WED"),
            f"{OVERLAY}.TIS": snapshot(override / f"{OVERLAY}.TIS"),
            f"{PAGE}.PVRZ": snapshot(override / f"{PAGE}.PVRZ"),
        },
        "engine_build": "not-run",
        "installation": "not-run",
        "qa": "pending-ingame",
        "tests": "none-user-choice",
        "release": "not-requested",
    }
    write_json(output / "candidate-manifest.json", manifest)
    result = {
        "schema": "bg2-ar1000-wtpool-route2-run-v1",
        "status": "candidate-installable-pending-ingame-qa",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan": {"path": "plan.json", **snapshot(output / "plan.json")},
        "registry": {"path": "registry-v3.json", **snapshot(registry_path)},
        "candidate_manifest": {"path": "candidate-manifest.json", **snapshot(output / "candidate-manifest.json")},
        "entries": len(registry["entries"]),
        "tests": "none-user-choice",
        "release": "not-requested",
    }
    write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    require(ROOT == output or ROOT in output.parents, "output must remain inside workspace")
    plan = create_plan(output)
    result = execute(plan, output) if args.run else plan
    print(json.dumps(result, indent=2, ensure_ascii=False) if args.json else result["status"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
