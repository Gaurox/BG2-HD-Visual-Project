"""Build the AR1607/AR1800 WTSWAM x4/30 FPS route2 pilot; plan-only by default."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import struct
from typing import Any

import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from build_water_overlay_30fps_test import write_pvrz
from build_wtlake_timeline_batch import pvrz_metadata, tis_metadata
import build_wtsew_route2_pilot as common
from water_wed import replace_overlay_timeline, validate_polygons


ROOT = Path(__file__).resolve().parents[2]
AREAS = {
    "AR1607": {
        "stock_wed_sha256": "1E56ACFC14C82C5E261C04105AF209774BF8723FF1495F8A731CBADAD257AB1F",
        "route1_changed_tiles": 525,
    },
    "AR1800": {
        "stock_wed_sha256": "FAFEEA4616302F3C87E2E27485DCA5DE20D093FE6D5E1C42E810E46951E882B9",
        "route1_changed_tiles": 7,
    },
}
OVERLAY = "WTSWAM"
PAGE = "WSWAM00"
OVERLAY_SHA256 = "2516B9058CADD9286B86085ACFDFFB2355DB451829E664356BF1E3F7329DC917"
WED_TYPE = 0x03E9
TIS_TYPE = 0x03EB
SOURCE_REGISTRY = (
    ROOT
    / "maps/technical-overlays/WTSEW/runs/"
    "seedvr2-none-apollo8-x4-15hz-route2-render30-q070-ar0404-20260912/registry-v3.json"
)
SOURCE_REGISTRY_SHA256 = "34D8E6542731867C00CA074FAA1E5A9603AF441A9F7256E80DB547D561CCC5D6"
BASE_ROOT = (
    ROOT
    / "maps/water-batches/runs/qa-candidates-20260912-v1/"
    "batches/swamp-wtswam/maps"
)
STRENGTH = 0.70
MATERIAL_ID = 5


def resolved_sources() -> tuple[dict[str, tuple[bytes, str]], bytes, str]:
    bifs, resources = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in resources}
    common.require((OVERLAY, TIS_TYPE) in index, "WTSWAM.TIS absent du KEY")
    legacy, count, entry_size, overlay_archive = resolve_tileset_resource(
        bifs, index[OVERLAY, TIS_TYPE]
    )
    common.require(
        count == common.SOURCE_FRAMES and entry_size == common.LEGACY_ENTRY_SIZE,
        "WTSWAM stock n'est pas le TIS palette 6x64 attendu",
    )
    common.require(common.sha256_bytes(legacy) == OVERLAY_SHA256, "WTSWAM stock divergent")
    weds: dict[str, tuple[bytes, str]] = {}
    for area, expected in AREAS.items():
        common.require((area, WED_TYPE) in index, f"{area}.WED absent du KEY")
        wed, archive = resolve_resource(bifs, index[area, WED_TYPE])
        common.require(
            common.sha256_bytes(wed) == expected["stock_wed_sha256"],
            f"{area}.WED stock divergent",
        )
        weds[area] = (wed, archive)
    return weds, legacy, overlay_archive


def parse_wed(payload: bytes, area: str) -> dict[str, Any]:
    common.require(payload[:8] == b"WED V1.3", f"signature WED invalide : {area}")
    layers, _objects, headers = struct.unpack_from("<3I", payload, 8)
    common.require(2 <= layers <= 5, f"nombre de couches WED invalide : {area}")
    parsed: list[dict[str, Any]] = []
    for index in range(layers):
        offset = headers + index * 24
        width, height, raw_name, unique, movement, tilemap, lookup = struct.unpack_from(
            "<HH8sHHII", payload, offset
        )
        parsed.append(
            {
                "slot": index,
                "width": width,
                "height": height,
                "name": raw_name.rstrip(b"\0").decode("ascii").upper(),
                "unique": unique,
                "movement": movement,
                "tilemap": tilemap,
                "lookup": lookup,
            }
        )
    overlay = parsed[1]
    common.require(
        (overlay["name"], overlay["width"], overlay["height"])
        == (OVERLAY, 1, 1),
        f"{area}/WTSWAM slot1 divergent",
    )
    start, count, secondary, flags, speed = struct.unpack_from(
        "<HHHBB", payload, overlay["tilemap"]
    )
    timeline = list(struct.unpack_from(f"<{count}H", payload, overlay["lookup"]))
    common.require(
        (start, count, secondary, flags, speed, timeline)
        == (0, common.SOURCE_FRAMES, 0xFFFF, 0, 6, list(range(common.SOURCE_FRAMES))),
        f"timeline WTSWAM stock divergente : {area}",
    )
    base = parsed[0]
    coverage = sum(
        bool(payload[base["tilemap"] + cell * 10 + 6] & (1 << overlay["slot"]))
        for cell in range(base["width"] * base["height"])
    )
    return {
        "layers": layers,
        "slots": [entry["name"] for entry in parsed],
        "grid": [base["width"], base["height"]],
        "coverage": coverage,
        "geometry": validate_polygons(payload),
    }


def build_plan(output: Path) -> dict[str, Any]:
    common.require(
        SOURCE_REGISTRY.is_file()
        and common.sha256_file(SOURCE_REGISTRY) == SOURCE_REGISTRY_SHA256,
        "registre source absent ou divergent",
    )
    registry = json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8"))
    checked = common.verify_live_registry(registry)
    weds, legacy, overlay_archive = resolved_sources()
    target_rows = []
    for area, (wed, archive) in weds.items():
        parsed = parse_wed(wed, area)
        base_source = BASE_ROOT / area
        base, base_paths = tis_metadata(area, base_source)
        override = common.get_path("bg2ee_game_root") / "override"
        for source in base_paths:
            live = override / source.name
            common.require(
                live.is_file() and common.sha256_file(live) == common.sha256_file(source),
                f"voie1 {area} live divergente : {source.name}",
            )
        target_rows.append(
            {
                "area": area,
                "variant": "day-or-unique",
                "stock_wed_archive": archive,
                "stock_wed_sha256": common.sha256_bytes(wed),
                "grid": parsed["grid"],
                "overlay_slots": parsed["slots"],
                "coverage_cells": parsed["coverage"],
                "geometry": parsed["geometry"],
                "route1": {
                    "state": "already-installed",
                    "changed_tiles": AREAS[area]["route1_changed_tiles"],
                    "source": common.relative(base_source),
                    "base_tis": base,
                },
            }
        )
    return {
        "schema": "bg2-wtswam-route2-pilot-plan-v1",
        "output": str(output),
        "scope": {
            "areas": list(AREAS),
            "overlay": OVERLAY,
            "family": "swamp-wtswam",
            "targets": target_rows,
        },
        "stock_overlay": {
            "archive": overlay_archive,
            "sha256": common.sha256_bytes(legacy),
            "frames": common.SOURCE_FRAMES,
            "frame_size": [64, 64],
            "speed": 6,
        },
        "upscale": {
            "model": "seedvr2_7b_int8_convrot.safetensors",
            "scale": 4,
            "color_correction_method": "none",
            "periodic_context": "3x3",
        },
        "timeline": {
            "source_fps": common.SOURCE_FPS,
            "native_fps": common.NATIVE_FPS,
            "target_fps": common.TARGET_FPS,
            "frames": common.FRAME_COUNT,
            "interpolator": "apo-8",
            "runtime_blend": "linear",
        },
        "route2": {
            "strength": STRENGTH,
            "material": "swamp",
            "material_id": MATERIAL_ID,
            "fallback": "q0-native",
        },
        "source_registry": common.relative(SOURCE_REGISTRY),
        "source_registry_sha256": SOURCE_REGISTRY_SHA256,
        "verified_live_registry_files": checked,
        "tests": "not-run",
        "installation": "not-run",
        "release": "not-requested",
    }


def build_overlay(frames: list[Path], output: Path) -> tuple[Path, Path]:
    output.mkdir()
    canvas = np.zeros((common.PAGE_SIZE, common.PAGE_SIZE, 4), dtype=np.uint8)
    entries = []
    for index, path in enumerate(frames):
        row, column = divmod(index, common.ATLAS_COLUMNS)
        x = column * common.ATLAS_STRIDE + common.PAD
        y = row * common.ATLAS_STRIDE + common.PAD
        with Image.open(path) as image:
            frame = np.asarray(image.convert("RGBA"), dtype=np.uint8)
        canvas[y : y + common.TILE_SIZE, x : x + common.TILE_SIZE] = frame
        canvas[y - common.PAD : y, x : x + common.TILE_SIZE] = frame[:1]
        canvas[
            y + common.TILE_SIZE : y + common.TILE_SIZE + common.PAD,
            x : x + common.TILE_SIZE,
        ] = frame[-1:]
        canvas[
            y - common.PAD : y + common.TILE_SIZE + common.PAD,
            x - common.PAD : x,
        ] = canvas[y - common.PAD : y + common.TILE_SIZE + common.PAD, x : x + 1]
        canvas[
            y - common.PAD : y + common.TILE_SIZE + common.PAD,
            x + common.TILE_SIZE : x + common.TILE_SIZE + common.PAD,
        ] = canvas[
            y - common.PAD : y + common.TILE_SIZE + common.PAD,
            x + common.TILE_SIZE - 1 : x + common.TILE_SIZE,
        ]
        entries.append((0, x, y))
    pvrz = output / f"{PAGE}.PVRZ"
    write_pvrz(Image.fromarray(canvas, mode="RGBA"), pvrz)
    tis = bytearray(b"TIS V1  ")
    tis += struct.pack("<IIII", common.FRAME_COUNT, 12, 24, common.TILE_SIZE)
    for entry in entries:
        tis += struct.pack("<3I", *entry)
    tis_path = output / f"{OVERLAY}.TIS"
    tis_path.write_bytes(tis)
    return tis_path, pvrz


def build_registry(
    plan: dict[str, Any], wed_paths: dict[str, Path], tis: Path, pvrz: Path, output: Path
) -> Path:
    registry = copy.deepcopy(json.loads(SOURCE_REGISTRY.read_text(encoding="utf-8")))
    existing = {entry["wed"]["resref"] for entry in registry["entries"]}
    common.require(not (existing & set(AREAS)), "pilote WTSWAM déjà présent dans le registre")
    overlay = {
        "slot": 1,
        "tis_resref": OVERLAY,
        "tis_sha256": common.sha256_file(tis),
        "tis_bytes": tis.stat().st_size,
        "tile_count": common.FRAME_COUNT,
        "tile_dimension": common.TILE_SIZE,
        "pages": [pvrz_metadata(pvrz)],
    }
    targets = {row["area"]: row for row in plan["scope"]["targets"]}
    for area in AREAS:
        row = targets[area]
        registry["entries"].append(
            {
                "id": f"wtswam-{area.lower()}-slot1-q070-v3",
                "state": "candidate-installable-pending-qa",
                "wed": {
                    "resref": area,
                    "sha256": common.sha256_file(wed_paths[area]),
                    "grid": {"width": row["grid"][0], "height": row["grid"][1]},
                    "overlay_slots": row["overlay_slots"],
                },
                "base_tis": row["route1"]["base_tis"],
                "overlay": copy.deepcopy(overlay),
                "approved_strength": STRENGTH,
                "overlay_coverage_cells": row["coverage_cells"],
                "allow_stock_wed_when_override_absent": False,
                "material_id": MATERIAL_ID,
                "temporal_overlay": {
                    "mode": "atlas-linear",
                    "frame_count": common.FRAME_COUNT,
                    "source_fps": common.NATIVE_FPS,
                    "target_fps": common.TARGET_FPS,
                    "atlas_columns": common.ATLAS_COLUMNS,
                    "atlas_stride_pixels": common.ATLAS_STRIDE,
                    "atlas_padding_pixels": common.PAD,
                },
                "qa": {
                    "status": "pending-ingame",
                    "reference": f"{area} WTSWAM q=0.70 pilot",
                },
            }
        )
    registry["status"] = "experimental-pending-ingame-qa"
    registry["experiment"] = {
        "scope": list(AREAS),
        "family": "swamp-wtswam",
        "previous_registry": common.relative(SOURCE_REGISTRY),
        "previous_registry_sha256": SOURCE_REGISTRY_SHA256,
        "untargeted_entries": "unchanged",
        "tests": "not-run-user-choice",
    }
    destination = output / "registry-v3.json"
    common.write_json(destination, registry)
    return destination


def execute(plan: dict[str, Any], output: Path) -> dict[str, Any]:
    common.require(not output.exists(), f"run déjà présent : {output}")
    output.mkdir(parents=True)
    common.write_json(output / "plan.json", plan)
    weds, legacy, _overlay_archive = resolved_sources()
    rgb_dir, alpha_dir = common.prepare_periodic_inputs(
        common.decode_legacy_frames(legacy), output
    )
    anchors, seedvr = common.upscale_anchors(rgb_dir, alpha_dir, output)
    frames, apollo = common.interpolate(anchors, output)
    tis, pvrz = build_overlay(frames, output / "07_overlay_x4")
    candidate = output / "08_candidate"
    candidate.mkdir()
    wed_paths: dict[str, Path] = {}
    for area, (wed, _archive) in weds.items():
        path = candidate / f"{area}.WED"
        path.write_bytes(replace_overlay_timeline(wed, 1, common.FRAME_COUNT))
        common.require(
            validate_polygons(path.read_bytes()) == validate_polygons(wed),
            f"géométrie WED candidate divergente : {area}",
        )
        wed_paths[area] = path
    shutil.copy2(tis, candidate / tis.name)
    shutil.copy2(pvrz, candidate / pvrz.name)
    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": common.sha256_file(path).lower()}
        for path in sorted(candidate.iterdir())
        if path.is_file()
    }
    common.write_json(
        candidate / "manifest.json",
        {
            "schema": "bg2-upscale-area-animation-override-assets-v1",
            "status": "completed",
            "area": "AR1607-AR1800",
            "purpose": "WTSWAM x4 36-phase 15 Hz plus route2 30 FPS swamp pilot q0.70",
            "qa_status": "pending-ingame",
            "files": files,
            "timeline": list(range(common.FRAME_COUNT)),
            "animation_speed_divisor": 1,
            "rollback": "Restore-AreaOverrideAssets.ps1 with generated install backup",
        },
    )
    registry = build_registry(plan, wed_paths, candidate / tis.name, candidate / pvrz.name, output)
    result = {
        "schema": "bg2-wtswam-route2-pilot-run-v1",
        "status": "candidate-installable-pending-qa",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": common.sha256_file(output / "plan.json"),
        "seedvr": seedvr,
        "apollo": apollo,
        "candidate": common.relative(candidate),
        "candidate_manifest_sha256": common.sha256_file(candidate / "manifest.json"),
        "registry": common.relative(registry),
        "registry_sha256": common.sha256_file(registry),
        "route2_strength": STRENGTH,
        "tests": "not-run-user-choice",
        "installation": "not-run",
        "qa": "pending-ingame",
        "release": "not-requested",
    }
    common.write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    plan = build_plan(output)
    if not args.run:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return 0
    print(json.dumps(execute(plan, output), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
