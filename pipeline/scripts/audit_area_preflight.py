"""Classify one area before any upscale and route it to the required pipelines.

The report is deliberately descriptive: it never modifies game assets or
source renders.  A non-empty ``blockers`` list is a stop condition.

    python audit_area_preflight.py AR1000 runs/my-run/00_preflight/AR1000-preflight.json
"""

from __future__ import annotations

import argparse
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from bg2lib import GAME_DIR, load_key, resolve_resource, resolve_tileset_resource
from mos_decode import decode_pvrz_page


WED_TYPE, TIS_TYPE, PVRZ_TYPE = 0x03E9, 0x03EB, 0x0404
TILE_SIZE = 64
WATER_PREFIXES = ("WTWAVE", "WTRIV", "WTPOOL", "WTLAK", "WTFALL", "WTURN", "YSPOOL", "YSRIV", "YSWAVE", "WTSWAM", "WTSEW", "WTOIL", "WTLAV")
# These generic six-frame overlays stay at x1: an x2 override breaks the map
# and automap rendering paths into visible repeated cells.  Their ARxxxx base
# tiles nevertheless follow the normal liquid-alpha repair path.
STOCK_OVERLAYS = {"WTSWAM", "WTSEW", "WTOIL", "WTLAVA", "WTLAVB", "WTLAVC", "WTLAVD"}
RULESET_VERSION = 5


def is_liquid(resref: str) -> bool:
    return resref.upper().startswith(WATER_PREFIXES)


def is_other_liquid(resref: str) -> bool:
    upper = resref.upper()
    return upper.startswith(("WT", "YS")) and not is_liquid(upper)


def pvrz_prefix(resref: str) -> str:
    return resref[0] + resref[2:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", help="resref de jour, par exemple AR1000 (sans le suffixe N)")
    parser.add_argument("output", type=Path, help="rapport JSON de destination")
    return parser.parse_args()


def alpha_family(alpha: np.ndarray) -> str:
    minimum, maximum = int(alpha.min()), int(alpha.max())
    if minimum == maximum == 255:
        return "opaque"
    if minimum == maximum == 0:
        return "transparent"
    if minimum == 0 and maximum == 255 and np.isin(alpha, (0, 255)).all():
        return "binary-mask"
    return "graded-mask"


def inspect_wed(
    resref: str,
    bif_entries: list[str],
    weds: dict[str, int],
    tiss: dict[str, int],
    pvrzs: dict[str, int],
) -> dict:
    raw, _ = resolve_resource(bif_entries, weds[resref])
    overlay_count, _, overlays_offset = struct.unpack_from("<III", raw, 8)
    width, height = struct.unpack_from("<HH", raw, overlays_offset)
    tilemap_offset, lookup_offset = struct.unpack_from("<II", raw, overlays_offset + 0x10)
    base_tileset = raw[overlays_offset + 4:overlays_offset + 12].split(b"\0")[0].decode("ascii").upper()
    if base_tileset not in tiss:
        raise RuntimeError(f"{resref}: TIS de base introuvable : {base_tileset}")

    layers = []
    liquid_bits = 0
    for index in range(overlay_count):
        offset = overlays_offset + index * 24
        layer_ref = raw[offset + 4:offset + 12].split(b"\0")[0].decode("ascii").upper()
        liquid_kind = "water" if index > 0 and is_liquid(layer_ref) else (
            "other-liquid" if index > 0 and is_other_liquid(layer_ref) else None
        )
        if liquid_kind == "water":
            liquid_bits |= 1 << index
        layers.append({"index": index, "resref": layer_ref, "liquid_kind": liquid_kind})

    tis_data, tile_count, entry_size, _ = resolve_tileset_resource(bif_entries, tiss[base_tileset])
    entries = [struct.unpack_from("<3I", tis_data, index * 12) for index in range(tile_count)] if entry_size == 12 else []
    primary_ids: set[int] = set()
    secondary_ids: set[int] = set()
    invalid_secondary: list[dict] = []
    primary_uses: dict[int, list[tuple[int, int]]] = defaultdict(list)
    liquid_cells = 0
    liquid_without_secondary = 0
    for cell in range(width * height):
        start, _count, secondary, flags = struct.unpack_from("<HHHB3x", raw, tilemap_offset + cell * 10)
        primary = struct.unpack_from("<H", raw, lookup_offset + start * 2)[0]
        primary_ids.add(primary)
        primary_uses[primary].append((flags, secondary))
        if secondary != 0xFFFF:
            if secondary >= tile_count:
                invalid_secondary.append({"cell": [cell % width, cell // width], "tile_id": secondary})
            else:
                secondary_ids.add(secondary)
        if flags & liquid_bits:
            liquid_cells += 1
            if secondary == 0xFFFF:
                liquid_without_secondary += 1

    alpha_by_page: dict[int, np.ndarray] = {}

    def source_alpha(tile_id: int) -> np.ndarray:
        page, x, y = entries[tile_id]
        if page == 0xFFFFFFFF:
            return np.zeros((TILE_SIZE, TILE_SIZE), dtype=np.uint8)
        if page not in alpha_by_page:
            page_ref = f"{pvrz_prefix(base_tileset)}{page:02d}".upper()
            if page_ref not in pvrzs:
                raise RuntimeError(f"{resref}: page PVRZ introuvable : {page_ref}")
            page_raw, _ = resolve_resource(bif_entries, pvrzs[page_ref])
            alpha_by_page[page] = np.asarray(decode_pvrz_page(page_raw).getchannel("A"))
        return alpha_by_page[page][y:y + TILE_SIZE, x:x + TILE_SIZE]

    def alpha_summary(tile_ids: set[int]) -> dict:
        if entry_size != 12:
            return {"available": False, "reason": f"legacy TIS ({entry_size} octets/tuile)"}
        drawable = {tile_id for tile_id in tile_ids if entries[tile_id][0] != 0xFFFFFFFF}
        black_tiles = len(tile_ids) - len(drawable)
        families = Counter(alpha_family(source_alpha(tile_id)) for tile_id in drawable)
        masked = families["transparent"] + families["binary-mask"] + families["graded-mask"]
        return {
            "available": True,
            "unique_tiles": len(tile_ids),
            "drawable_tile_ids": len(drawable),
            "black_sentinel_tile_ids": black_tiles,
            "families": dict(sorted(families.items())),
            "has_mask": bool(masked),
            "masked_tile_ids": masked,
        }

    water_only_base = [
        tile_id for tile_id, uses in primary_uses.items()
        if all(flags & liquid_bits and secondary == 0xFFFF for flags, secondary in uses)
    ]
    static_water_base = []
    if entry_size == 12:
        static_water_base = [
            tile_id for tile_id in water_only_base
            if alpha_family(source_alpha(tile_id)) == "opaque"
        ]
    liquid_black_sentinels = [
        tile_id for tile_id in water_only_base if entries[tile_id][0] == 0xFFFFFFFF
    ]

    overlay_reuse = []
    override_dir = Path(GAME_DIR) / "override"
    for layer in layers:
        if layer["liquid_kind"] != "water":
            continue
        overlay_ref = layer["resref"]
        prefix = pvrz_prefix(overlay_ref)
        tis_override = override_dir / f"{overlay_ref}.TIS"
        pvrz_overrides = sorted(override_dir.glob(f"{prefix}??.PVRZ"))
        stock_overlay = overlay_ref in STOCK_OVERLAYS
        overlay_reuse.append({
            "resref": overlay_ref,
            "override_tis_present": tis_override.is_file(),
            "override_pvrz_present": bool(pvrz_overrides),
            "overlay_policy": "keep-stock" if stock_overlay else "reuse-existing-override",
            "reuse_existing_override": (not stock_overlay) and tis_override.is_file() and bool(pvrz_overrides),
        })

    return {
        "wed": resref,
        "grid_cells": {"width": width, "height": height},
        "base_tileset": base_tileset,
        "base_tis": {"tile_count": tile_count, "entry_size": entry_size},
        "layers": layers,
        "primary": {"unique_tile_ids": len(primary_ids), "alpha": alpha_summary(primary_ids)},
        "secondary": {
            "cells": sum(1 for uses in primary_uses.values() for _flags, sec in uses if sec != 0xFFFF),
            "unique_tile_ids": len(secondary_ids),
            "invalid_references": invalid_secondary,
            "alpha": alpha_summary(secondary_ids),
        },
        "water": {
            "present": bool(liquid_bits),
            "flag_bits": liquid_bits,
            "flagged_cells": liquid_cells,
            "flagged_cells_without_secondary": liquid_without_secondary,
            "fully_opaque_static_base_tile_ids": len(static_water_base),
            "black_sentinel_liquid_base_tile_ids": len(liquid_black_sentinels),
            "overlay_reuse": overlay_reuse,
        },
        "other_liquid_layers": [layer["resref"] for layer in layers if layer["liquid_kind"] == "other-liquid"],
    }


def main() -> None:
    args = parse_args()
    area = args.area.upper()
    if area.endswith("N"):
        raise SystemExit("indiquer le resref de jour sans suffixe N, par exemple AR1000")
    bif_entries, resources = load_key()
    weds = {name.upper(): entry for name, kind, entry in resources if kind == WED_TYPE}
    tiss = {name.upper(): entry for name, kind, entry in resources if kind == TIS_TYPE}
    pvrzs = {name.upper(): entry for name, kind, entry in resources if kind == PVRZ_TYPE}
    if area not in weds:
        raise SystemExit(f"WED de jour introuvable : {area}")

    day = inspect_wed(area, bif_entries, weds, tiss, pvrzs)
    night_ref = f"{area}N"
    night = inspect_wed(night_ref, bif_entries, weds, tiss, pvrzs) if night_ref in weds else None
    blockers: list[str] = []
    routes = [{"id": "core-upscale", "document": "pipeline/UPSCALE_MAP_PIPELINE.md", "status": "required"}]

    for label, variant in (("day", day), ("night", night)):
        if variant is None:
            continue
        if variant["secondary"]["invalid_references"] and variant["secondary"]["unique_tile_ids"]:
            blockers.append(f"{label}: références secondaires invalides")
        alpha_present = variant["primary"]["alpha"].get("has_mask") or variant["secondary"]["alpha"].get("has_mask")
        if alpha_present:
            routes.append({"id": f"alpha-{label}", "document": "pipeline/ALPHA_MAP_PIPELINE.md", "status": "required"})
        if variant["secondary"]["cells"]:
            routes.append({"id": f"secondary-{label}", "document": "pipeline/SECONDARY_TILE_PIPELINE.md", "status": "required"})
        if variant["water"]["present"]:
            routes.append({"id": f"water-{label}", "document": "pipeline/WATER_MAP_PIPELINE.md", "status": "required"})
            missing = [
                item["resref"] for item in variant["water"]["overlay_reuse"]
                if item["overlay_policy"] == "reuse-existing-override" and not item["reuse_existing_override"]
            ]
            if missing:
                blockers.append(f"{label}: overlay liquide x2 absent : {', '.join(missing)}")
        if variant["other_liquid_layers"]:
            unvalidated = list(variant["other_liquid_layers"])
            routes.append({
                "id": f"other-liquid-{label}",
                "document": "pipeline/OTHER_LIQUID_MAP_PIPELINE.md",
                "status": "validation-required" if unvalidated else "required",
            })
            if unvalidated:
                blockers.append(f"{label}: liquide non classé : {', '.join(unvalidated)}")

    if night is not None:
        routes.append({"id": "day-night", "document": "pipeline/DAY_NIGHT_MAP_PIPELINE.md", "status": "required"})

    report = {
        "schema": "bg2-upscale-area-preflight",
        "ruleset_version": RULESET_VERSION,
        "area": area,
        "day": day,
        "night": night,
        "routes": routes,
        "blockers": blockers,
        "next_command": "python pipeline/scripts/validate_x1_masters.py --area " + area if not blockers else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
