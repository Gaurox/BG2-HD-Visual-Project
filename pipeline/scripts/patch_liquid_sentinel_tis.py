"""Create a narrow TIS-only liquid-sentinel repair without repacking PVRZ.

The selected WED cells must use black-sentinel primary entries, be exclusively
covered by a recognised liquid overlay, and have no secondary tile.  Their TIS
entries are redirected to one *existing*, fully transparent DXT5 tile from the
same already-validated build.  No PVRZ is written or modified, preserving the
atlas and every later-rendered decoration.

    python patch_liquid_sentinel_tis.py AR0413 base/AR0413.TIS base output/AR0413.TIS \
        --cells "1,2;2,2"
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import struct
import sys
import zlib
from collections import defaultdict
from pathlib import Path

from PIL import Image

from bg2lib import load_key, resolve_resource
from mos_decode import pvr_to_dds_bytes


WED_TYPE = 0x03E9
TILE = 64
LIQUID_PREFIXES = (
    "WTWAVE", "WTRIV", "WTPOOL", "WTLAK", "WTFALL", "WTURN", "YSPOOL", "YSRIV", "YSWAVE",
    "WTSWAM", "WTSEW", "WTOIL", "WTLAV",
)


def parse_cells(value: str) -> list[tuple[int, int]]:
    cells: list[tuple[int, int]] = []
    for token in value.split(";"):
        try:
            x_text, y_text = token.split(",", 1)
            cell = (int(x_text), int(y_text))
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                "--cells doit être une liste x,y séparée par des ;") from exc
        if cell in cells:
            raise argparse.ArgumentTypeError(f"cellule dupliquée : {cell[0]},{cell[1]}")
        cells.append(cell)
    if not cells:
        raise argparse.ArgumentTypeError("--cells ne peut pas être vide")
    return cells


def load_pvrz_alpha(path: Path) -> Image.Image:
    raw = path.read_bytes()
    pvr = zlib.decompress(raw[4:])
    dds, _width, _height = pvr_to_dds_bytes(pvr)
    image = Image.open(io.BytesIO(dds))
    image.load()
    return image.convert("RGBA").getchannel("A")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("area")
    parser.add_argument("input_tis", type=Path)
    parser.add_argument("pvrz_dir", type=Path)
    parser.add_argument("output_tis", type=Path)
    parser.add_argument("--cells", required=True, type=parse_cells)
    parser.add_argument("--report", type=Path,
                        help="manifeste JSON de la modification TIS (optionnel)")
    args = parser.parse_args()

    area = args.area.upper()
    source = bytearray(args.input_tis.read_bytes())
    if source[:8] != b"TIS V1  ":
        raise SystemExit(f"{args.input_tis}: signature TIS invalide")
    tile_count, entry_size, header_size, tile_dimension = struct.unpack_from("<IIII", source, 8)
    if entry_size != 12 or header_size != 24 or tile_dimension not in (64, 128, 256, 512):
        raise SystemExit(f"{args.input_tis}: TIS PVRZ à dimension explicite requis")
    if len(source) != header_size + tile_count * entry_size:
        raise SystemExit(f"{args.input_tis}: taille de table TIS incohérente")

    bif_entries, resources = load_key()
    weds = {name.upper(): entry for name, kind, entry in resources if kind == WED_TYPE}
    if area not in weds:
        raise SystemExit(f"WED introuvable : {area}")
    wed, _ = resolve_resource(bif_entries, weds[area])
    overlay_count, _, overlays_offset = struct.unpack_from("<III", wed, 8)
    width, height = struct.unpack_from("<HH", wed, overlays_offset)
    tilemap_offset, lookup_offset = struct.unpack_from("<II", wed, overlays_offset + 0x10)
    base_tileset = wed[overlays_offset + 4:overlays_offset + 12].split(b"\0")[0].decode("ascii").upper()

    liquid_bits = 0
    for index in range(1, overlay_count):
        offset = overlays_offset + index * 24
        resref = wed[offset + 4:offset + 12].split(b"\0")[0].decode("ascii").upper()
        if resref.startswith(LIQUID_PREFIXES):
            liquid_bits |= 1 << index
    if not liquid_bits:
        raise SystemExit(f"{area}: aucun overlay liquide reconnu")

    uses: dict[int, list[tuple[int, int, int, int]]] = defaultdict(list)
    for cell in range(width * height):
        start, _count, secondary, flags = struct.unpack_from("<HHHB3x", wed, tilemap_offset + cell * 10)
        tile_id = struct.unpack_from("<H", wed, lookup_offset + start * 2)[0]
        uses[tile_id].append((cell % width, cell // width, flags, secondary))

    target_ids: list[int] = []
    for x, y in args.cells:
        if not (0 <= x < width and 0 <= y < height):
            raise SystemExit(f"{area}: cellule hors grille : {x},{y}")
        cell = y * width + x
        start, _count, secondary, flags = struct.unpack_from("<HHHB3x", wed, tilemap_offset + cell * 10)
        tile_id = struct.unpack_from("<H", wed, lookup_offset + start * 2)[0]
        if tile_id >= tile_count:
            raise SystemExit(f"{area}: cellule {x},{y} référence la tuile invalide {tile_id}")
        page, _u, _v = struct.unpack_from("<3I", source, header_size + tile_id * entry_size)
        if page != 0xFFFFFFFF:
            raise SystemExit(f"{area}: cellule {x},{y} n'est pas une sentinelle noire")
        if not (flags & liquid_bits) or secondary != 0xFFFF:
            raise SystemExit(f"{area}: cellule {x},{y} n'est pas une sentinelle liquide sans secondaire")
        if any((other_x, other_y) not in args.cells for other_x, other_y, _flags, _secondary in uses[tile_id]):
            raise SystemExit(f"{area}: tuile sentinelle {tile_id} partagée hors de la sélection")
        target_ids.append(tile_id)

    prefix = base_tileset[0] + base_tileset[2:]
    alpha_pages: dict[int, Image.Image] = {}
    carrier: tuple[int, int, int, int] | None = None
    for tile_id in range(tile_count):
        page, x, y = struct.unpack_from("<3I", source, header_size + tile_id * entry_size)
        if page == 0xFFFFFFFF:
            continue
        if page not in alpha_pages:
            path = args.pvrz_dir / f"{prefix}{page:02d}.PVRZ"
            if not path.is_file():
                raise SystemExit(f"page PVRZ introuvable : {path}")
            alpha_pages[page] = load_pvrz_alpha(path)
        if alpha_pages[page].crop((x, y, x + tile_dimension, y + tile_dimension)).getextrema() == (0, 0):
            carrier = (tile_id, page, x, y)
            break
    if carrier is None:
        raise SystemExit(f"{area}: aucune tuile transparente valide pour servir de support")

    carrier_id, carrier_page, carrier_x, carrier_y = carrier
    for tile_id in target_ids:
        struct.pack_into("<3I", source, header_size + tile_id * entry_size,
                         carrier_page, carrier_x, carrier_y)
    report = {
        "area": area,
        "input_tis": str(args.input_tis),
        "output_tis": str(args.output_tis),
        "tile_dimension": tile_dimension,
        "cells": [{"x": x, "y": y, "tile_id": tile_id}
                  for (x, y), tile_id in zip(args.cells, target_ids)],
        "transparent_carrier": {"tile_id": carrier_id, "page": carrier_page,
                                "x": carrier_x, "y": carrier_y},
        "input_sha256": hashlib.sha256(args.input_tis.read_bytes()).hexdigest(),
        "output_sha256": hashlib.sha256(source).hexdigest(),
    }
    if args.output_tis.exists():
        if args.output_tis.read_bytes() != source:
            raise SystemExit(f"destination existante différente : {args.output_tis}")
    else:
        args.output_tis.parent.mkdir(parents=True, exist_ok=True)
        args.output_tis.write_bytes(source)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
