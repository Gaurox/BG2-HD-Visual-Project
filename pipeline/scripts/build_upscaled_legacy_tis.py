"""Build a modern PVRZ TIS override from x2 frames of a legacy palette TIS.

The source TIS is read from the game key only to validate its tile count and
legacy entry size.  The supplied frames must retain its original ordering and
be named ``frame-000.png``, ``frame-001.png``, etc.  The output uses DXT5 so
an alpha channel is preserved when a legacy overlay needs one.

    python build_upscaled_legacy_tis.py WTLAKE frames-x2 output-dir
"""

from __future__ import annotations

import argparse
import io
import struct
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_tileset_resource


TIS_TYPE = 0x03EB
PVR_MAGIC = 0x03525650
LEGACY_ENTRY_SIZE = 5120
SOURCE_TILE_SIZE = 64
PAGE_SIZE = 2048
PAD = 4


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tileset", help="resref TIS, par exemple WTLAKE")
    parser.add_argument("frames", type=Path, help="dossier des frame-000.png x2 ordonnées")
    parser.add_argument("output", type=Path, help="dossier de sortie TIS/PVRZ")
    return parser.parse_args()


def source_tile_count(tileset: str) -> int:
    bif_entries, resource_entries = load_key()
    tis_by_name = {name.upper(): entry for name, kind, entry in resource_entries if kind == TIS_TYPE}
    entry = tis_by_name.get(tileset)
    if entry is None:
        raise RuntimeError(f"TIS introuvable : {tileset}")
    _data, tile_count, entry_size, _bif = resolve_tileset_resource(bif_entries, entry)
    if entry_size != LEGACY_ENTRY_SIZE:
        raise RuntimeError(
            f"{tileset}: TIS source non paletté ({entry_size} octets par tuile, "
            f"{LEGACY_ENTRY_SIZE} attendu)"
        )
    return tile_count


def load_frames(frames_dir: Path, expected_count: int) -> tuple[list[Image.Image], int]:
    paths = [frames_dir / f"frame-{index:03}.png" for index in range(expected_count)]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise RuntimeError(f"frames manquantes : {', '.join(missing)}")
    frames = []
    for path in paths:
        with Image.open(path) as opened:
            frames.append(opened.convert("RGBA"))
    sizes = {frame.size for frame in frames}
    if len(sizes) != 1:
        raise RuntimeError(f"tailles de frames incompatibles : {sorted(sizes)}")
    (width, height), = sizes
    if width != height or width % SOURCE_TILE_SIZE:
        raise RuntimeError(f"taille de frame invalide : {width}x{height}")
    return frames, width // SOURCE_TILE_SIZE


def write_pvrz(canvas: Image.Image, destination: Path) -> None:
    buffer = io.BytesIO()
    canvas.save(buffer, format="DDS", pixel_format="DXT5")
    dds = buffer.getvalue()
    payload = dds[128:]
    width, height = canvas.size
    header = struct.pack("<13I", PVR_MAGIC, 0, 11, 0, 0, 0, height, width, 1, 1, 1, 1, 0)
    pvr = header + payload
    destination.write_bytes(struct.pack("<I", len(pvr)) + zlib.compress(pvr, 9))


def main() -> None:
    args = parse_args()
    tileset = args.tileset.upper()
    tile_count = source_tile_count(tileset)
    frames, scale = load_frames(args.frames, tile_count)
    tile_size = SOURCE_TILE_SIZE * scale
    cell_size = tile_size + 2 * PAD
    per_row = PAGE_SIZE // cell_size
    if per_row == 0:
        raise RuntimeError(f"tuile x{scale} trop grande pour une page {PAGE_SIZE}x{PAGE_SIZE}")
    per_page = per_row * per_row

    args.output.mkdir(parents=True, exist_ok=True)
    pages: list[Image.Image] = []
    entries: list[tuple[int, int, int]] = []
    for index, frame in enumerate(frames):
        page_index, within_page = divmod(index, per_page)
        row, column = divmod(within_page, per_row)
        while len(pages) <= page_index:
            pages.append(Image.new("RGBA", (PAGE_SIZE, PAGE_SIZE), (0, 0, 0, 0)))
        x, y = column * cell_size + PAD, row * cell_size + PAD
        pages[page_index].paste(frame, (x, y))
        entries.append((page_index, x, y))

    for page_index, page in enumerate(pages):
        array = np.asarray(page).copy()
        for index, (entry_page, x, y) in enumerate(entries):
            if entry_page != page_index:
                continue
            block = array[y - PAD:y + tile_size + PAD, x - PAD:x + tile_size + PAD]
            block[:PAD, PAD:-PAD] = block[PAD:PAD + 1, PAD:-PAD]
            block[-PAD:, PAD:-PAD] = block[-PAD - 1:-PAD, PAD:-PAD]
            block[:, :PAD] = block[:, PAD:PAD + 1]
            block[:, -PAD:] = block[:, -PAD - 1:-PAD]
        pages[page_index] = Image.fromarray(array, mode="RGBA")

    prefix = tileset[0] + tileset[2:]
    for page_index, page in enumerate(pages):
        path = args.output / f"{prefix}{page_index:02d}.PVRZ"
        write_pvrz(page, path)
        print(f"{path.name}: {page.width}x{page.height}, {path.stat().st_size:,} octets")

    tis = bytearray(b"TIS V1  ")
    tis += struct.pack("<IIII", tile_count, 12, 24, tile_size)
    for page, x, y in entries:
        tis += struct.pack("<3I", page, x, y)
    tis_path = args.output / f"{tileset}.TIS"
    tis_path.write_bytes(tis)
    print(f"{tis_path.name}: {tile_count} tuiles, dimension {tile_size}, x{scale}")


if __name__ == "__main__":
    main()
