"""Render the WED overlay grid of an area as primary, secondary and empty cells.

The image is a diagnostic only: it identifies which WED cells use regular
background art, a conditional secondary tile (usually a door), or no drawable
primary tile.  It does not modify the game or the area resources.

    python render_tile_classes.py AR0602 output.png
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from bg2lib import load_key, resolve_resource, resolve_tileset_resource


WED_TYPE = 0x03E9
TIS_TYPE = 0x03EB
CELL_PIXELS = 16
LEGEND_HEIGHT = 84
COLORS = {
    "primary": (44, 144, 93),
    "secondary": (220, 107, 39),
    "empty": (39, 44, 51),
    "grid": (15, 18, 22),
    "text": (235, 238, 240),
}


def resources_by_type(entries, resource_type):
    return {name.upper(): entry for name, kind, entry in entries if kind == resource_type}


def main(area: str, destination: Path) -> None:
    area = area.upper()
    bif_entries, resource_entries = load_key()
    wed_by_name = resources_by_type(resource_entries, WED_TYPE)
    tis_by_name = resources_by_type(resource_entries, TIS_TYPE)
    if area not in wed_by_name:
        raise SystemExit(f"WED introuvable : {area}")

    wed, _ = resolve_resource(bif_entries, wed_by_name[area])
    _, _, overlays_offset = struct.unpack_from("<III", wed, 8)
    columns, rows = struct.unpack_from("<HH", wed, overlays_offset)
    tileset = wed[overlays_offset + 4 : overlays_offset + 12].split(b"\0")[0].decode("ascii").upper()
    tilemap_offset, lookup_offset = struct.unpack_from("<II", wed, overlays_offset + 0x10)
    tis, tile_count, entry_size, _ = resolve_tileset_resource(bif_entries, tis_by_name[tileset])
    if entry_size != 12:
        raise SystemExit(f"{area}: TIS non PVRZ (entry size {entry_size})")

    destination.parent.mkdir(parents=True, exist_ok=True)
    width = columns * CELL_PIXELS
    height = rows * CELL_PIXELS
    image = Image.new("RGB", (width, height + LEGEND_HEIGHT), COLORS["grid"])
    draw = ImageDraw.Draw(image)
    totals = {key: 0 for key in ("primary", "secondary", "empty")}

    for cell in range(columns * rows):
        lookup_start, _count, secondary_tile, _flags = struct.unpack_from(
            "<HHHB3x", wed, tilemap_offset + cell * 10
        )
        primary_tile = struct.unpack_from("<H", wed, lookup_offset + lookup_start * 2)[0]
        if primary_tile >= tile_count:
            raise SystemExit(f"tuile primaire hors TIS : cell={cell}, tile={primary_tile}")
        page, _u, _v = struct.unpack_from("<3I", tis, primary_tile * 12)
        if secondary_tile != 0xFFFF:
            category = "secondary"
        elif page == 0xFFFFFFFF:
            category = "empty"
        else:
            category = "primary"
        totals[category] += 1
        col, row = cell % columns, cell // columns
        x, y = col * CELL_PIXELS, row * CELL_PIXELS
        draw.rectangle((x, y, x + CELL_PIXELS - 1, y + CELL_PIXELS - 1), fill=COLORS[category])

    legend_y = height + 12
    draw.text((12, legend_y), f"{area} — WED {columns}x{rows} cells (x=column, y=row)", fill=COLORS["text"])
    x = 12
    for category, label in (
        ("primary", "Primary / regular background"),
        ("secondary", "Secondary / conditional (doors)"),
        ("empty", "Empty / black"),
    ):
        y = legend_y + 26
        draw.rectangle((x, y, x + 14, y + 14), fill=COLORS[category])
        draw.text((x + 20, y), f"{label}: {totals[category]}", fill=COLORS["text"])
        x += 350

    image.save(destination)
    print(f"wrote {destination}  {image.width}x{image.height}")
    print(" ".join(f"{key}={value}" for key, value in totals.items()))


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]))
