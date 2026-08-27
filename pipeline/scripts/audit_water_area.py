"""Audit the water composition of an Infinity Engine area without changing assets.

The JSON report is the entry point for the water-map pipeline.  It identifies
the WED liquid layers, confirms whether their already-upscaled override is
present, and counts fully opaque base tiles that would hide the animated
underlay as static square blocks.

    python audit_water_area.py AR0900 output-water-audit.json
"""

from __future__ import annotations

import argparse
import json
import struct
from collections import defaultdict
from pathlib import Path

from bg2lib import GAME_DIR, load_key, resolve_resource, resolve_tileset_resource
from mos_decode import decode_pvrz_page


WED_TYPE, TIS_TYPE, PVRZ_TYPE = 0x03E9, 0x03EB, 0x0404
TILE_SIZE = 64
WATER_PREFIXES = ("WTWAVE", "WTRIV", "WTPOOL", "WTLAK", "WTFALL", "WTURN", "YSPOOL", "YSRIV", "YSWAVE", "WTSWAM", "WTSEW", "WTOIL", "WTLAV")
# These generic six-frame overlays are engine-owned; only their ARxxxx base
# tiles are rebuilt.  Installing an override for the overlay itself creates
# visible repeated cells in map and automap paths.
STOCK_OVERLAYS = {"WTSWAM", "WTSEW", "WTOIL", "WTLAVA", "WTLAVB", "WTLAVC", "WTLAVD"}


def is_liquid(resref: str) -> bool:
    return resref.upper().startswith(WATER_PREFIXES)


def pvrz_prefix(resref: str) -> str:
    """Infinity PVRZ convention: ``AR0900`` -> ``A0900``."""
    return resref[0] + resref[2:]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area", help="resref WED/ARE, for example AR0900")
    parser.add_argument("output", type=Path, help="JSON report destination")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    area = args.area.upper()
    bif_entries, resources = load_key()
    weds = {name.upper(): entry for name, kind, entry in resources if kind == WED_TYPE}
    tiss = {name.upper(): entry for name, kind, entry in resources if kind == TIS_TYPE}
    pvrzs = {name.upper(): entry for name, kind, entry in resources if kind == PVRZ_TYPE}
    if area not in weds:
        raise SystemExit(f"WED introuvable : {area}")

    wed, _ = resolve_resource(bif_entries, weds[area])
    layer_count, _, overlays_offset = struct.unpack_from("<III", wed, 8)
    width, height = struct.unpack_from("<HH", wed, overlays_offset)
    tilemap_offset, lookup_offset = struct.unpack_from("<II", wed, overlays_offset + 0x10)
    base_resref = wed[overlays_offset + 4:overlays_offset + 12].split(b"\0")[0].decode("ascii").upper()

    layers = []
    liquid_bits = 0
    for index in range(layer_count):
        offset = overlays_offset + index * 24
        resref = wed[offset + 4:offset + 12].split(b"\0")[0].decode("ascii").upper()
        liquid = index > 0 and is_liquid(resref)
        if liquid:
            liquid_bits |= 1 << index
        layers.append({"index": index, "resref": resref, "liquid": liquid})

    base_data, tile_count, entry_size, _ = resolve_tileset_resource(bif_entries, tiss[base_resref])
    if entry_size != 12:
        raise SystemExit(f"{area}: base TIS {base_resref} non PVRZ ({entry_size} octets/tuile)")
    entries = [struct.unpack_from("<3I", base_data, index * 12) for index in range(tile_count)]

    primary_uses: dict[int, list[tuple[int, int]]] = defaultdict(list)
    water_cells = 0
    cells_without_secondary = 0
    for cell in range(width * height):
        start, _count, secondary, flags = struct.unpack_from("<HHHB3x", wed, tilemap_offset + cell * 10)
        primary = struct.unpack_from("<H", wed, lookup_offset + start * 2)[0]
        primary_uses[primary].append((flags, secondary))
        if flags & liquid_bits:
            water_cells += 1
            if secondary == 0xFFFF:
                cells_without_secondary += 1

    page_alpha = {}

    def fully_opaque(tile_index: int) -> bool:
        page, x, y = entries[tile_index]
        if page == 0xFFFFFFFF:
            return False
        if page not in page_alpha:
            name = f"{pvrz_prefix(base_resref)}{page:02d}".upper()
            raw, _ = resolve_resource(bif_entries, pvrzs[name])
            page_alpha[page] = decode_pvrz_page(raw).getchannel("A")
        return page_alpha[page].crop((x, y, x + TILE_SIZE, y + TILE_SIZE)).getextrema() == (255, 255)

    water_only_base_tiles = [
        tile for tile, uses in primary_uses.items()
        if all(flags & liquid_bits and secondary == 0xFFFF for flags, secondary in uses)
    ]
    static_candidates = [tile for tile in water_only_base_tiles if fully_opaque(tile)]
    liquid_black_sentinels = [
        tile for tile in water_only_base_tiles if entries[tile][0] == 0xFFFFFFFF
    ]

    overlays = []
    override_dir = Path(GAME_DIR) / "override"
    for layer in layers:
        if not layer["liquid"]:
            continue
        resref = layer["resref"]
        prefix = pvrz_prefix(resref)
        tis = override_dir / f"{resref}.TIS"
        pvrzs_override = sorted(override_dir.glob(f"{prefix}??.PVRZ"))
        stock_overlay = resref in STOCK_OVERLAYS
        overlays.append({
            "resref": resref,
            "override_tis": str(tis),
            "override_tis_present": tis.is_file(),
            "override_pvrz": [str(path) for path in pvrzs_override],
            "override_pvrz_present": bool(pvrzs_override),
            "overlay_policy": "keep-stock" if stock_overlay else "reuse-existing-override",
            "reuse_existing_override": (not stock_overlay) and tis.is_file() and bool(pvrzs_override),
        })

    report = {
        "area": area,
        "base_tileset": base_resref,
        "grid_cells": {"width": width, "height": height},
        "layers": layers,
        "water": {
            "flag_bits": liquid_bits,
            "flagged_cells": water_cells,
            "flagged_cells_without_secondary": cells_without_secondary,
            "water_only_base_tile_ids": len(water_only_base_tiles),
            "fully_opaque_static_base_tile_ids": len(static_candidates),
            "black_sentinel_liquid_base_tile_ids": len(liquid_black_sentinels),
            "recommended_build_flags": (
                ["--transparent-full-water-base", "--soften-water-contours"]
                if static_candidates else []
            ),
        },
        "overlay_reuse": overlays,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
