"""Assemble the complete WTLAKE route1 + 30 FPS route2 QA candidate.

Plan-only by default. ``--run`` writes a new immutable batch without running
SeedVR, compiling the engine, installing files, or changing release content.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bg2lib import load_key, resolve_resource
from workspace_paths import get_path
from water_wed import replace_overlay_timeline


ROOT = Path(__file__).resolve().parents[2]
WED_TYPE = 0x03E9
AREAS = (
    "AR0046", "AR0046N", "AR0204", "AR0300", "AR0300N", "AR0512",
    "AR0900", "AR0900N", "AR1200", "AR1600", "AR1604", "AR1700",
    "AR1901", "AR2300",
)
REFERENCE = "AR0900"
PARENT_ENTRY_ID = "ar0900-day-wtlake-slot1-q100-v1"
ROUTE1_AREAS = {
    "AR0046", "AR0046N", "AR0204", "AR0300", "AR0300N", "AR0900N",
    "AR1200", "AR1600", "AR1700", "AR1901",
}
SOURCE_BATCH = (
    ROOT / "maps/water-batches/runs/qa-candidates-20260912-v1/batches/lake-wtlake"
)
OVERLAY_SOURCE = (
    ROOT
    / "maps/technical-overlays/WTLAKE/runs/"
      "apollo8-x4-15hz-route2-render30-q050-ar0900-20260912/04_candidate_assets"
)
ACTIVE_REGISTRY = (
    ROOT
    / "engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json"
)
SPECIAL_SOURCES = {
    "AR0204": ROOT / "maps/water-batches/runs/ar0204-ar1600-seams-wed-20260912-v1/maps/AR0204",
    "AR0512": ROOT / "maps/AR0512/runs/seedvr2-7b-int8-lab-direct-x4/05_build/x4",
    "AR0900": ROOT / (
        "maps/AR0900/runs/voie1-water-rgb-seams-x4-jour-20260912/"
        "05_build/x4-alpha128-water-seams-repaired"
    ),
    "AR1604": ROOT / "maps/AR1604/runs/seedvr2-7b-int8-lab-direct-x4/05_build",
    "AR1600": ROOT / "maps/water-batches/runs/ar0204-ar1600-seams-wed-20260912-v1/maps/AR1600",
    "AR2300": ROOT / (
        "maps/AR2300/runs/seedvr2-7b-int8-lab-batch-underdark-x4/05_build/"
        "x4-page2112-cache-safe-v1-fall6-statue-primary-alpha-v2-margin12-20260906"
    ),
}
FRAME_COUNT = 36
NATIVE_FPS = 15.0
TARGET_FPS = 30.0
TILE_DIMENSION = 256
ATLAS_COLUMNS = 7
ATLAS_PADDING = 4
ATLAS_STRIDE = TILE_DIMENSION + 2 * ATLAS_PADDING
STRENGTH = 0.70
PVR_MAGIC = 0x03525650


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT)).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"JSON absent : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def source_directory(area: str) -> Path:
    if area in SPECIAL_SOURCES:
        return SPECIAL_SOURCES[area]
    if area in ROUTE1_AREAS:
        return SOURCE_BATCH / "maps" / area
    raise KeyError(f"source non configurée : {area}")


def expected_page_name(resref: str, page: int) -> str:
    name = f"{resref[0]}{resref[2:]}{page:02d}.PVRZ".upper()
    require(len(Path(name).stem) <= 8, f"resref PVRZ trop long : {name}")
    return name


def pvrz_metadata(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    require(len(raw) > 4, f"PVRZ tronquée : {path}")
    expected = struct.unpack_from("<I", raw, 0)[0]
    decoded = zlib.decompress(raw[4:])
    require(len(decoded) == expected and len(decoded) >= 52, f"PVRZ invalide : {path}")
    header = struct.unpack_from("<13I", decoded, 0)
    require(header[0] == PVR_MAGIC, f"signature PVR invalide : {path}")
    return {
        "resref": path.stem.upper(),
        "width": header[7],
        "height": header[6],
        "bytes": len(raw),
        "sha256": sha256_bytes(raw),
    }


def tis_metadata(area: str, directory: Path) -> tuple[dict[str, Any], list[Path]]:
    tis = directory / f"{area}.TIS"
    require(tis.is_file(), f"TIS voie1 absent : {tis}")
    raw = tis.read_bytes()
    require(raw[:8] == b"TIS V1  " and len(raw) >= 24, f"TIS invalide : {tis}")
    tile_count, entry_size, header_size, tile_dimension = struct.unpack_from("<4I", raw, 8)
    require(entry_size == 12 and header_size == 24, f"TIS non PVRZ : {tis}")
    require(len(raw) == header_size + tile_count * entry_size, f"taille TIS invalide : {tis}")
    page_ids = sorted({
        struct.unpack_from("<I", raw, header_size + index * entry_size)[0]
        for index in range(tile_count)
    } - {0xFFFFFFFF})
    pages = [directory / expected_page_name(area, page) for page in page_ids]
    require(all(path.is_file() for path in pages), f"pages PVRZ incomplètes : {area}")
    return ({
        "resref": area,
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "tile_count": tile_count,
        "tile_dimension": tile_dimension,
        "pages": [pvrz_metadata(path) for path in pages],
    }, [tis, *pages])


def parse_wed(payload: bytes, area: str) -> dict[str, Any]:
    require(payload[:8] == b"WED V1.3", f"signature WED invalide : {area}")
    overlay_count, _doors, overlays_offset, secondary_offset = struct.unpack_from(
        "<4I", payload, 8
    )
    require(2 <= overlay_count <= 5, f"nombre d'overlays divergent : {area}")
    slots: list[str] = []
    headers: list[dict[str, Any]] = []
    for index in range(overlay_count):
        offset = overlays_offset + index * 24
        width, height, raw_resref, unique, movement, tilemap, lookup = struct.unpack_from(
            "<HH8sHHII", payload, offset
        )
        resref = raw_resref.rstrip(b"\0").decode("ascii")
        slots.append(resref)
        headers.append({
            "index": index, "offset": offset, "width": width, "height": height,
            "resref": resref, "unique": unique, "movement": movement,
            "tilemap": tilemap, "lookup": lookup,
        })
    matches = [item for item in headers if item["resref"] == "WTLAKE"]
    require(len(matches) == 1 and matches[0]["index"] == 1, f"slot WTLAKE divergent : {area}")
    overlay = matches[0]
    require((overlay["width"], overlay["height"]) == (1, 1), f"grille WTLAKE divergente : {area}")
    start, count, secondary, flags = struct.unpack_from("<HHHB3x", payload, overlay["tilemap"])
    lookup = list(struct.unpack_from(f"<{count}H", payload, overlay["lookup"]))
    require(start == 0 and count in {1, 6, FRAME_COUNT} and lookup == list(range(count)),
            f"timeline WTLAKE divergente : {area}")
    base = headers[0]
    coverage = 0
    for cell in range(base["width"] * base["height"]):
        tile_flags = payload[base["tilemap"] + cell * 10 + 6]
        coverage += int(bool(tile_flags & (1 << overlay["index"])))
    return {
        "overlay_count": overlay_count,
        "overlays_offset": overlays_offset,
        "secondary_offset": secondary_offset,
        "slots": slots,
        "headers": headers,
        "overlay": overlay,
        "source_frame_count": count,
        "secondary_tile": secondary,
        "overlay_flags": flags,
        "base": base,
        "coverage": coverage,
    }


def patch_wed(payload: bytes, area: str) -> bytes:
    parsed = parse_wed(payload, area)
    output = replace_overlay_timeline(payload, parsed["overlay"]["index"], FRAME_COUNT)
    result = parse_wed(output, area)
    require(result["source_frame_count"] == FRAME_COUNT, f"timeline non patchée : {area}")
    return output


def stock_weds() -> dict[str, tuple[bytes, str]]:
    bifs, resources = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in resources}
    result: dict[str, tuple[bytes, str]] = {}
    for area in AREAS:
        locator = index.get((area, WED_TYPE))
        require(locator is not None, f"WED KEY/BIF absent : {area}")
        resolved = resolve_resource(bifs, locator)
        require(resolved is not None, f"WED non résolu : {area}")
        result[area] = resolved
    return result


def live_snapshot(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"state": "absent"}
    return {"state": "present", "bytes": path.stat().st_size, "sha256": sha256_file(path)}


def overlay_metadata() -> tuple[dict[str, Any], list[Path]]:
    tis, paths = tis_metadata("WTLAKE", OVERLAY_SOURCE)
    require(tis["tile_count"] == FRAME_COUNT and tis["tile_dimension"] == TILE_DIMENSION,
            "WTLAKE 36 phases absente ou divergente")
    require(len(tis["pages"]) == 1 and tis["pages"][0]["resref"] == "WLAKE00",
            "atlas WTLAKE divergent")
    return ({
        "slot": 1,
        "tis_resref": "WTLAKE",
        "tis_sha256": tis["sha256"],
        "tis_bytes": tis["bytes"],
        "tile_count": tis["tile_count"],
        "tile_dimension": tis["tile_dimension"],
        "pages": tis["pages"],
    }, paths)


def build_plan(output: Path) -> dict[str, Any]:
    game_root = get_path("bg2ee_game_root")
    override = game_root / "override"
    require(override.is_dir(), f"override jeu absent : {override}")
    weds = stock_weds()
    overlay, overlay_paths = overlay_metadata()
    sources: list[dict[str, Any]] = []
    for area in AREAS:
        directory = source_directory(area)
        base, files = tis_metadata(area, directory)
        for source in files:
            live = override / source.name
            require(live.is_file() and sha256_file(live) == sha256_file(source),
                    f"voie1 live divergente : {area}/{source.name}")
        parsed = parse_wed(weds[area][0], area)
        require(parsed["base"]["resref"] == area, f"base TIS WED divergente : {area}")
        require(base["tile_count"] > 0 and parsed["coverage"] > 0,
                f"couverture WTLAKE vide : {area}")
        sources.append({
            "wed": area,
            "variant": "night" if area.endswith("N") else "day-or-unique",
            "route1": "repaired-candidate" if area in ROUTE1_AREAS else "already-conform",
            "base_source": relative(directory),
            "base_tis": base,
            "stock_wed": {
                "bif": weds[area][1], "bytes": len(weds[area][0]),
                "sha256": sha256_bytes(weds[area][0]),
                "source_frame_count": parsed["source_frame_count"],
                "coverage_cells": parsed["coverage"],
            },
            "live_wed_before": live_snapshot(override / f"{area}.WED"),
        })
    for path in overlay_paths:
        live = override / path.name
        require(live.is_file() and sha256_file(live) == sha256_file(path),
                f"overlay WTLAKE live divergent : {path.name}")
    return {
        "schema": "bg2-wtlake-timeline-batch-plan-v1",
        "output": str(output),
        "scope": {"family": "lake-wtlake", "targets": list(AREAS), "count": len(AREAS)},
        "parameters": {
            "seedvr": "not-run", "seedvr_color_correction_method": "none",
            "route1": "preserve-or-use-existing-alpha128-repair",
            "timeline_frames": FRAME_COUNT, "native_fps": NATIVE_FPS,
            "render_fps": TARGET_FPS, "route2_strength": STRENGTH,
            "material_id": 1,
        },
        "overlay": overlay,
        "sources": sources,
        "actions": {
            "assets": "write-candidate-only",
            "engine_build": "not-run-separate-reconstruction-choice",
            "installation": "not-run-separate-choice",
            "tests": "not-run-separate-choice",
            "release": "not-requested",
        },
    }


def operation(source: Path, name: str | None = None) -> dict[str, Any]:
    target_name = name or source.name.upper()
    return {
        "operation": "copy", "source": relative(source),
        "target": f"override/{target_name}", "name": target_name,
        "bytes": source.stat().st_size, "sha256": sha256_file(source),
    }


def execute(plan: dict[str, Any], output: Path) -> dict[str, Any]:
    require(not output.exists(), f"run déjà présent : {output}")
    output.mkdir(parents=True)
    write_json(output / "plan.json", plan)
    candidate = output / "candidate"
    candidate.mkdir()
    weds = stock_weds()
    overlay, overlay_paths = overlay_metadata()
    entries: list[dict[str, Any]] = []
    operations: list[dict[str, Any]] = []
    targets: list[dict[str, Any]] = []
    for source in plan["sources"]:
        area = source["wed"]
        wed_path = candidate / f"{area}.WED"
        wed_path.write_bytes(patch_wed(weds[area][0], area))
        patched = parse_wed(wed_path.read_bytes(), area)
        base = source["base_tis"]
        state = "approved-ingame" if area == REFERENCE else "candidate-installable-pending-qa"
        qa_status = "validated-ingame" if area == REFERENCE else "pending-ingame"
        entries.append({
            "id": PARENT_ENTRY_ID if area == REFERENCE else f"wtlake-{area.lower()}-slot1-q070-v3",
            "state": state,
            "wed": {
                "resref": area, "sha256": sha256_file(wed_path),
                "grid": {"width": patched["base"]["width"], "height": patched["base"]["height"]},
                "overlay_slots": patched["slots"],
            },
            "base_tis": base,
            "overlay": overlay,
            "approved_strength": STRENGTH,
            "overlay_coverage_cells": patched["coverage"],
            "allow_stock_wed_when_override_absent": False,
            "material_id": 1,
            "temporal_overlay": {
                "mode": "atlas-linear", "frame_count": FRAME_COUNT,
                "source_fps": NATIVE_FPS, "target_fps": TARGET_FPS,
                "atlas_columns": ATLAS_COLUMNS,
                "atlas_stride_pixels": ATLAS_STRIDE,
                "atlas_padding_pixels": ATLAS_PADDING,
            },
            "qa": {"status": qa_status, "reference": "AR0900 q=0.70"},
        })
        for path in tis_metadata(area, source_directory(area))[1]:
            operations.append(operation(path))
        operations.append(operation(wed_path))
        targets.append({
            "wed": area, "variant": source["variant"], "overlay_slot": 1,
            "overlay": "WTLAKE", "family": "lake-wtlake",
            "state": "corrected" if area == REFERENCE else "candidate-installable-pending-qa",
            "route1": source["route1"], "timeline": "36-phases-15hz-render30",
            "route2_strength": STRENGTH, "qa": qa_status,
            "installation": "reference-already-installed" if area == REFERENCE else "not-run",
            "release": "not-requested",
        })
    for path in overlay_paths:
        destination = candidate / path.name.upper()
        shutil.copy2(path, destination)
        operations.append(operation(destination))
    operations.sort(key=lambda item: item["target"])
    names = [item["target"].upper() for item in operations]
    require(len(names) == len(set(names)), "collisions d'opérations dans le lot WTLAKE")
    active = load_json(ACTIVE_REGISTRY)
    registry = {
        "schema": "bg2-water-route2-registry-v3",
        "version": 3,
        "date": datetime.now(timezone.utc).date().isoformat(),
        "parent": {"path": relative(ACTIVE_REGISTRY), "sha256": sha256_file(ACTIVE_REGISTRY)},
        "status": "experimental-pending-ingame-qa",
        "entries": entries,
        "fallback": active["fallback"],
        "experiment": {
            "scope": "all 14 WTLAKE day/night identities only",
            "strength": STRENGTH, "reference": "AR0900 validated at q=0.70",
            "unknown_or_divergent_identity": "q0-native",
        },
    }
    registry_path = output / "registry-v3-wtlake-q070.json"
    write_json(registry_path, registry)
    batch = {
        "schema": "bg2-water-qa-batch-manifest-v2",
        "family": "lake-wtlake", "status": "candidate-installable-pending-qa",
        "targets": targets, "renderer": {
            "registry": relative(registry_path), "registry_sha256": sha256_file(registry_path),
            "route2_strength": STRENGTH, "fallback": "q0-native",
            "build": "not-run",
        },
        "operations": operations,
        "preconditions": [
            "close-game", "close-InfinityLoader", "transactional-backup",
            "verify-live-before-write", "compile-registry-v3-before-install",
        ],
        "qa": "separate-per-map-and-variant",
        "installation": "not-run",
        "release": "not-requested",
    }
    batch_path = output / "batch-manifest.json"
    write_json(batch_path, batch)
    result = {
        "schema": "bg2-wtlake-timeline-batch-run-v1",
        "status": "candidate-installable-pending-qa",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "plan_sha256": sha256_file(output / "plan.json"),
        "registry": {"path": registry_path.name, "sha256": sha256_file(registry_path)},
        "batch_manifest": {"path": batch_path.name, "sha256": sha256_file(batch_path)},
        "counts": {"targets": len(targets), "entries": len(entries), "operations": len(operations)},
        "parameters": plan["parameters"],
        "tests": "not-run", "engine_build": "not-run", "installation": "not-run",
        "qa": "pending-ingame-except-AR0900-reference", "release": "not-requested",
    }
    write_json(output / "run.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    plan = build_plan(output)
    if not args.run:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(execute(plan, output), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
