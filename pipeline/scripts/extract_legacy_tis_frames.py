"""Export every frame of a legacy palette TIS as a PNG.

Legacy liquid overlays such as WTPOOL are palette TIS resources.  Their
frames must be extracted in their original order before the shared x2 overlay
pipeline can process them.

    python extract_legacy_tis_frames.py WTPOOL output-frames
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_tileset_resource


TIS_TYPE = 0x03EB
LEGACY_ENTRY_SIZE = 5120
PALETTE_BYTES = 256 * 4
TILE_SIZE = 64


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tileset", help="resref TIS, par exemple WTPOOL")
    parser.add_argument("output", type=Path, help="dossier des frame-000.png")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tileset = args.tileset.upper()
    bif_entries, resources = load_key()
    tis_by_name = {name.upper(): entry for name, kind, entry in resources if kind == TIS_TYPE}
    entry = tis_by_name.get(tileset)
    if entry is None:
        raise SystemExit(f"TIS introuvable : {tileset}")
    data, tile_count, entry_size, _ = resolve_tileset_resource(bif_entries, entry)
    if entry_size != LEGACY_ENTRY_SIZE:
        raise SystemExit(
            f"{tileset}: TIS non paletté ({entry_size} octets/tuile, {LEGACY_ENTRY_SIZE} attendu)")

    args.output.mkdir(parents=True, exist_ok=True)
    for index in range(tile_count):
        offset = index * entry_size
        palette_bgra = np.frombuffer(data, dtype=np.uint8, count=PALETTE_BYTES, offset=offset).reshape(256, 4)
        palette_rgb = palette_bgra[:, [2, 1, 0]]
        indices = np.frombuffer(
            data, dtype=np.uint8, count=TILE_SIZE * TILE_SIZE, offset=offset + PALETTE_BYTES
        ).reshape(TILE_SIZE, TILE_SIZE)
        rgb = palette_rgb[indices]
        # Palette entry byte 3 is not an alpha channel in legacy TIS data.
        # Liquid overlays are opaque frames; their map-specific reveal mask
        # lives in the base-area PVRZ alpha and is restored by the area builder.
        rgba = np.dstack((rgb, np.full((TILE_SIZE, TILE_SIZE), 255, dtype=np.uint8)))
        Image.fromarray(rgba, mode="RGBA").save(args.output / f"frame-{index:03}.png")
    print(f"{tileset}: {tile_count} frames -> {args.output}")


if __name__ == "__main__":
    main()
