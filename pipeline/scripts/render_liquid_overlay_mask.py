"""Render the WED liquid-overlay coverage mask for an area.

The mask is a diagnostic aid: white cells receive an authored liquid overlay
(WT*, YS*), black cells do not.  It preserves the base WED grid exactly; it
does not alter game resources.

    python render_liquid_overlay_mask.py AR0900 output.png
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from bg2lib import load_key, resolve_resource


WED_TYPE = 0x03E9
CELL_PIXELS = 64
LEGEND_HEIGHT = 94
WATER_PREFIXES = ("WTWAVE", "WTRIV", "WTPOOL", "WTLAK", "WTFALL", "WTURN", "YSPOOL", "YSRIV", "YSWAVE", "WTSWAM", "WTSEW", "WTOIL", "WTLAV")


def is_water_tileset(resref: str) -> bool:
    return resref.upper().startswith(WATER_PREFIXES)


def main(area: str, destination: Path) -> None:
    area = area.upper()
    bif_entries, resource_entries = load_key()
    wed_by_name = {name.upper(): entry for name, kind, entry in resource_entries if kind == WED_TYPE}
    wed_entry = wed_by_name.get(area)
    if wed_entry is None:
        raise SystemExit(f"WED introuvable : {area}")

    wed, _ = resolve_resource(bif_entries, wed_entry)
    layer_count, _doors, overlays_offset = struct.unpack_from("<III", wed, 8)
    base_width, base_height = struct.unpack_from("<HH", wed, overlays_offset)
    base_tilemap_offset = struct.unpack_from("<I", wed, overlays_offset + 0x10)[0]

    liquid_overlay_bits = 0
    liquid_names: list[str] = []
    for overlay_index in range(1, layer_count):
        offset = overlays_offset + overlay_index * 24
        resref = wed[offset + 4 : offset + 12].split(b"\0")[0].decode("ascii")
        if is_water_tileset(resref):
            liquid_overlay_bits |= 1 << overlay_index
            liquid_names.append(resref.upper())

    width, height = base_width * CELL_PIXELS, base_height * CELL_PIXELS
    image = Image.new("RGB", (width, height + LEGEND_HEIGHT), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    liquid_cells = 0
    for cell in range(base_width * base_height):
        _start, _count, _secondary, flags = struct.unpack_from(
            "<HHHB3x", wed, base_tilemap_offset + cell * 10
        )
        if flags & liquid_overlay_bits:
            liquid_cells += 1
            x = (cell % base_width) * CELL_PIXELS
            y = (cell // base_width) * CELL_PIXELS
            draw.rectangle((x, y, x + CELL_PIXELS - 1, y + CELL_PIXELS - 1), fill=(255, 255, 255))

    legend_y = height + 12
    draw.text((12, legend_y), f"{area} — liquid overlay coverage mask", fill=(235, 238, 240))
    draw.text(
        (12, legend_y + 28),
        f"White: {', '.join(liquid_names) or 'none'}  |  {liquid_cells}/{base_width * base_height} WED cells",
        fill=(235, 238, 240),
    )
    draw.text((12, legend_y + 52), "Black: no liquid overlay", fill=(180, 184, 190))

    destination.parent.mkdir(parents=True, exist_ok=True)
    image.save(destination)
    print(f"wrote {destination}  {image.width}x{image.height}; liquid cells={liquid_cells}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], Path(sys.argv[2]))
