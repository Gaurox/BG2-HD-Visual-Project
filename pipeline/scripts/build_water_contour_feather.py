"""Build a reversible transparency-fade (Gaussian feather) alpha variant for
one map, applied on top of an already-built DXT5 reference (e.g. a spline-fit
build). Only the requested output directory is written.  The source TIS/PVRZ
build, game override, WED and liquid overlays are never modified.

This adapts the documented `--water-contour-feather` recipe from
WATER_MAP_PIPELINE.md (a Gaussian blur of the alpha before the bilinear
upscale, radius in x1 pixels) to a post-build correction on an existing xN
alpha canvas: the blur radius is expressed directly in xN pixels here, and no
re-thresholding is applied afterwards, so the result is a genuine graduated
fade rather than a re-sharpened silhouette (unlike
GEOMETRIC_ALPHA_MASK_CLEANUP.md's sigma+threshold recipe).
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import struct
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
from bg2lib import load_key, resolve_resource  # noqa: E402
from mos_decode import decode_pvrz_page  # noqa: E402


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def pvr_prefix(area: str) -> str:
    return area[0] + area[2:]


def load_tis(directory: Path, area: str):
    raw = (directory / f"{area}.TIS").read_bytes()
    if raw[:8] != b"TIS V1  ":
        raise RuntimeError(f"TIS invalide : {directory}")
    count, entry_size, header_size, tile_size = struct.unpack_from("<IIII", raw, 8)
    if entry_size != 12:
        raise RuntimeError("seuls les TIS PVRZ sont acceptés")
    return tile_size, [struct.unpack_from("<3I", raw, header_size + index * 12)
                       for index in range(count)]


def load_page(directory: Path, area: str, page: int, cache: dict[int, Image.Image]) -> Image.Image:
    if page not in cache:
        cache[page] = decode_pvrz_page((directory / f"{pvr_prefix(area)}{page:02d}.PVRZ").read_bytes())
    return cache[page]


def encode_pvrz(image: Image.Image, source_path: Path) -> bytes:
    original_pvr = zlib.decompress(source_path.read_bytes()[4:])
    header = list(struct.unpack_from("<13I", original_pvr, 0))
    if header[2] != 11:
        raise RuntimeError(f"{source_path.name}: le test exige DXT5 (PVR format 11)")
    dds = io.BytesIO()
    image.save(dds, format="DDS", pixel_format="DXT5")
    pvr = struct.pack("<13I", *header) + dds.getvalue()[128:]
    return struct.pack("<I", len(pvr)) + zlib.compress(pvr, 9)


def mode_cells(wed: bytes, width: int, height: int, tilemap_offset: int, lookup_offset: int):
    primary: dict[int, int] = {}
    secondary: dict[int, int] = {}
    for cell in range(width * height):
        start, _count, second, _flags = struct.unpack_from("<HHHB3x", wed, tilemap_offset + cell * 10)
        first = struct.unpack_from("<H", wed, lookup_offset + start * 2)[0]
        if first in primary:
            raise RuntimeError(f"tuile primaire partagée {first}; ce pipeline exige une tuile par cellule")
        primary[first] = cell
        if second != 0xFFFF:
            if second in secondary:
                raise RuntimeError(f"tuile secondaire partagée {second}; ce pipeline exige une tuile par cellule")
            secondary[second] = cell
    if set(primary) & set(secondary):
        raise RuntimeError("une tuile appartient aux deux états WED")
    return {"primary": primary, "secondary": secondary}


def assemble_mask(directory: Path, area: str, entries, tile_size: int, width: int, height: int, cells: dict[int, int]):
    canvas = Image.new("L", (width * tile_size, height * tile_size))
    cache: dict[int, Image.Image] = {}
    for tile_id, cell in cells.items():
        page, x, y = entries[tile_id]
        if page != 0xFFFFFFFF:
            alpha = load_page(directory, area, page, cache).getchannel("A").crop((x, y, x + tile_size, y + tile_size))
            canvas.paste(alpha, ((cell % width) * tile_size, (cell // width) * tile_size))
    return canvas


def feather_mask(mask: Image.Image, radius: float):
    blurred = mask.filter(ImageFilter.GaussianBlur(radius=radius))
    before = np.asarray(mask)
    after = np.asarray(blurred)
    return blurred, {
        "changed_pixels": int(np.count_nonzero(before != after)),
        "alpha_levels": len(np.unique(after)),
        "mean_abs_delta": float(np.mean(np.abs(before.astype(np.int16) - after.astype(np.int16)))),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a requested map water-contour feather variant; does not install it.")
    parser.add_argument("--area", required=True, type=str.upper, help="WED/TIS area resref, e.g. AR0900 or AR0900N")
    parser.add_argument("reference", type=Path, help="existing DXT5 build directory")
    parser.add_argument("output", type=Path, help="new build directory; must not exist")
    parser.add_argument("--feather-radius-x4", type=float, default=5.0,
                        help="Gaussian blur radius in xN pixels; documented starting point 1.25 x1 (~5.0 at x4)")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Z0-9]{1,8}", args.area):
        raise SystemExit("resref de zone invalide")
    if not args.reference.is_dir():
        raise SystemExit(f"build de référence absent: {args.reference}")
    if args.output.exists():
        raise SystemExit(f"refus d'écraser une sortie existante: {args.output}")
    if args.feather_radius_x4 <= 0:
        raise SystemExit("rayon de fondu invalide")

    tile_size, entries = load_tis(args.reference, args.area)
    bif_entries, resources = load_key()
    wed_by_name = {name.upper(): locator for name, kind, locator in resources if kind == 0x03E9}
    if args.area not in wed_by_name:
        raise SystemExit(f"WED introuvable dans chitin.key: {args.area}")
    wed, _ = resolve_resource(bif_entries, wed_by_name[args.area])
    _layers, _doors, overlays_offset = struct.unpack_from("<III", wed, 8)
    width, height = struct.unpack_from("<HH", wed, overlays_offset)
    tilemap_offset, lookup_offset = struct.unpack_from("<II", wed, overlays_offset + 0x10)
    states = {mode: cells for mode, cells in mode_cells(wed, width, height, tilemap_offset, lookup_offset).items()
              if cells}
    source_masks = {mode: assemble_mask(args.reference, args.area, entries, tile_size, width, height, cells)
                    for mode, cells in states.items()}
    feathered_masks, report_states = {}, {}
    for mode, mask in source_masks.items():
        feathered_masks[mode], report_states[mode] = feather_mask(mask, args.feather_radius_x4)

    shutil.copytree(args.reference, args.output)
    pages: dict[int, Image.Image] = {}
    affected_pages: set[int] = set()
    for mode, cells in states.items():
        for tile_id, cell in cells.items():
            page, x, y = entries[tile_id]
            if page == 0xFFFFFFFF:
                continue
            page_image = load_page(args.output, args.area, page, pages).copy()
            pages[page] = page_image
            alpha = page_image.getchannel("A")
            alpha.paste(feathered_masks[mode].crop(((cell % width) * tile_size, (cell // width) * tile_size,
                                                     (cell % width + 1) * tile_size, (cell // width + 1) * tile_size)), (x, y))
            page_image.putalpha(alpha)
            affected_pages.add(page)
    for page in sorted(affected_pages):
        source = args.reference / f"{pvr_prefix(args.area)}{page:02d}.PVRZ"
        (args.output / source.name).write_bytes(encode_pvrz(pages[page], source))

    report = {
        "area": args.area,
        "method": "gaussian blur of full WED alpha canvas, no re-threshold (graduated fade)",
        "feather_radius_x4": args.feather_radius_x4,
        "reference": str(args.reference.resolve()),
        "reference_tis_sha256": sha256(args.reference / f"{args.area}.TIS"),
        "tile_dimension": tile_size,
        "states": report_states,
        "affected_pages": sorted(affected_pages),
        "installation": "not performed",
    }
    (args.output / "water-contour-feather-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
