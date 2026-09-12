"""Build the exact AR1000N WTSWAM dry/rain route2 candidate."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
from typing import Any

from bg2lib import load_key, resolve_resource
from build_ar1000_wtpool_route1_candidate import (
    ROOT,
    parse_wed,
    relative,
    require,
    sha256_bytes,
    sha256_file,
    write_json,
)
from build_wtlake_timeline_batch import pvrz_metadata, tis_metadata
from workspace_paths import get_path
from water_wed import replace_overlay_resref, replace_overlay_timeline, validate_polygons


AREA = "AR1000N"
FAMILY = "swamp-wtswam"
SOURCE_OVERLAY = "WTSWAM"
DRY_OVERLAY = "WSWPIL"
DRY_PAGE = "WWPIL00"
RAIN_OVERLAY = "WSWPILR"
RAIN_PAGE = "WWPILR00"
FRAME_COUNT = 36
SOURCE_FPS = 15.0
TARGET_FPS = 30.0
MATERIAL_ID = 5
STRENGTH = 0.70
PARENT_REGISTRY = (
    ROOT / "maps/water-batches/runs/ar1000-wtpool-route2-q070-20260912-v5/registry-v3.json"
)
SWAMP_CANDIDATE = (
    ROOT
    / "maps/technical-overlays/WTSWAMR/runs/seedvr-none-apollo36-isolated-rain-20260912-v4/08_candidate"
)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"JSON absent: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def snapshot(path: Path) -> dict[str, Any]:
    require(path.is_file() and not path.is_symlink(), f"fichier absent ou non sûr: {path}")
    return {"bytes": path.stat().st_size, "sha256": sha256_file(path)}


def stock_wed() -> tuple[bytes, str]:
    bifs, resources = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in resources}
    require((AREA, 0x03E9) in index, f"{AREA}.WED absent du KEY")
    return resolve_resource(bifs, index[(AREA, 0x03E9)])


def overlay_record(resref: str, page: str, override: Path) -> dict[str, Any]:
    metadata, paths = tis_metadata(resref, override)
    require(metadata["tile_count"] == FRAME_COUNT and metadata["tile_dimension"] == 256,
            f"timeline {resref} divergente")
    require([path.name for path in paths] == [f"{resref}.TIS", f"{page}.PVRZ"],
            f"inventaire {resref} divergent")
    return {
        "slot": 1,
        "tis_resref": resref,
        "tis_sha256": metadata["sha256"],
        "tis_bytes": metadata["bytes"],
        "tile_count": metadata["tile_count"],
        "tile_dimension": metadata["tile_dimension"],
        "pages": [pvrz_metadata(override / f"{page}.PVRZ")],
    }


def execute(output: Path) -> dict[str, Any]:
    require(not output.exists(), f"run déjà présent: {output}")
    game = get_path("bg2ee_game_root")
    override = game / "override"
    parent = load_json(PARENT_REGISTRY)
    require(parent.get("schema") == "bg2-water-route2-registry-v3", "registre parent incompatible")
    require(not any(entry["wed"]["resref"] == AREA for entry in parent["entries"]),
            f"{AREA} existe déjà dans le registre")

    source_wed, archive = stock_wed()
    live_wed = override / f"{AREA}.WED"
    require(not live_wed.exists() or sha256_file(live_wed) == sha256_bytes(source_wed),
            f"{AREA}.WED live divergent du stock")
    parsed = parse_wed(source_wed, SOURCE_OVERLAY)
    require(parsed["slots"] == [AREA, SOURCE_OVERLAY, "", "", ""], "slots nocturnes divergents")
    require(parsed["base"]["width"] == 80 and parsed["base"]["height"] == 60,
            "grille nocturne divergente")
    require(parsed["coverage"] == 37 and parsed["flagged_without_secondary"] == 0,
            "couverture WTSWAM nocturne divergente")
    require(parsed["timeline_frames"] == 6 and parsed["source_speed"] == 6,
            "timeline WTSWAM stock divergente")
    polygons = validate_polygons(source_wed)
    require(polygons == {"objects": 14, "wall_polygons": 301, "object_polygons": 32},
            "géométrie AR1000N divergente")

    swamp_manifest = load_json(SWAMP_CANDIDATE / "manifest.json")
    for name in (f"{DRY_OVERLAY}.TIS", f"{DRY_PAGE}.PVRZ",
                 f"{RAIN_OVERLAY}.TIS", f"{RAIN_PAGE}.PVRZ"):
        require(swamp_manifest["files"][name] == snapshot(override / name),
                f"asset WTSWAM validé divergent: {name}")

    candidate_wed = replace_overlay_resref(
        replace_overlay_timeline(source_wed, 1, FRAME_COUNT), 1, DRY_OVERLAY
    )
    candidate_parsed = parse_wed(candidate_wed, DRY_OVERLAY)
    require(candidate_parsed["timeline_frames"] == FRAME_COUNT and
            candidate_parsed["source_speed"] == 1 and
            candidate_parsed["coverage"] == 37 and
            candidate_parsed["flagged_without_secondary"] == 0,
            "WED candidat divergent")
    require(validate_polygons(candidate_wed) == polygons, "géométrie WED modifiée")

    base_tis, _base_paths = tis_metadata(AREA, override)
    dry = overlay_record(DRY_OVERLAY, DRY_PAGE, override)
    rain = overlay_record(RAIN_OVERLAY, RAIN_PAGE, override)

    output.mkdir(parents=True)
    candidate = output / "override-candidate"
    candidate.mkdir()
    wed_path = candidate / f"{AREA}.WED"
    wed_path.write_bytes(candidate_wed)
    files = {wed_path.name: snapshot(wed_path)}
    write_json(candidate / "manifest.json", {
        "schema": "bg2-upscale-area-animation-override-assets-v1",
        "status": "completed",
        "area": AREA,
        "files": files,
        "qa_status": "pending-ingame",
    })

    common = {
        "state": "candidate-installable-pending-qa",
        "wed": {
            "resref": AREA,
            "sha256": sha256_file(wed_path),
            "grid": {"width": 80, "height": 60},
            "overlay_slots": [AREA, DRY_OVERLAY, "", "", ""],
        },
        "base_tis": base_tis,
        "approved_strength": STRENGTH,
        "overlay_coverage_cells": 37,
        "allow_stock_wed_when_override_absent": False,
        "material_id": MATERIAL_ID,
        "temporal_overlay": {
            "mode": "atlas-linear",
            "frame_count": FRAME_COUNT,
            "source_fps": SOURCE_FPS,
            "target_fps": TARGET_FPS,
            "atlas_columns": 7,
            "atlas_stride_pixels": 264,
            "atlas_padding_pixels": 4,
        },
        "qa": {
            "status": "pending-ingame",
            "reference": "AR1000N exact WTSWAM candidate using validated AR1607/AR1800 family assets",
        },
    }
    dry_entry = dict(common)
    dry_entry.update({"id": "wtswam-ar1000n-night-slot1-q070-v1", "overlay": dry})
    rain_entry = dict(common)
    rain_entry.update({"id": "wtswamr-ar1000n-night-rain-slot1-q070-v1", "overlay": rain})

    registry = dict(parent)
    registry["entries"] = [*parent["entries"], dry_entry, rain_entry]
    registry["status"] = "experimental-pending-ingame-qa"
    registry["experiment"] = {
        "scope": [AREA],
        "variant": "night",
        "family": FAMILY,
        "dry_overlay": DRY_OVERLAY,
        "rain_overlay": RAIN_OVERLAY,
        "strength": STRENGTH,
        "reason": "reuse validated non-generative WTSWAM dry/rain assets and temporal route2",
        "qa": "pending-ingame",
    }
    registry_path = output / "registry-v3.json"
    write_json(registry_path, registry)
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "schema": "bg2-ar1000n-wtswam-route2-run-v1",
        "status": "candidate-installable-pending-ingame-qa",
        "created_at_utc": now,
        "scope": {"area": AREA, "variant": "night", "family": FAMILY},
        "method": "reuse WSWPIL/WSWPILR; 36 phases/15 Hz; blend 30 FPS; material 5; q0.70",
        "source_wed": {"archive": archive, "sha256": sha256_bytes(source_wed)},
        "candidate_wed": files[wed_path.name],
        "registry": {"path": relative(registry_path), **snapshot(registry_path)},
        "entries_added": [dry_entry["id"], rain_entry["id"]],
        "tests": "not-run-user-request",
        "release": "not-requested",
    }
    write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    require(ROOT in output.parents, "output hors workspace")
    if not args.run:
        print(json.dumps({"status": "planned-not-run", "output": relative(output),
                          "area": AREA, "method": "reuse validated WTSWAM dry/rain assets"}, indent=2))
        return 0
    result = execute(output)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
