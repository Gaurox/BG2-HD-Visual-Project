"""Merge x4 Recover v2 selector assets with the validated main-menu atlases."""

from __future__ import annotations

import io
import json
import struct
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
VARIANT_ROOT = ROOT.parent
PROJECT_ROOT = next(parent for parent in ROOT.parents if (parent / "pipeline" / "scripts").is_dir())
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from bg2lib import load_key, resolve_resource  # noqa: E402


SCALE = 4
TYPE_BAM = 1000
TYPE_MOS = 1004
TYPE_PVRZ = 1028
PAGES = (181, 182, 183, 184, 185, 258, 259)
MERGED_PAGES = {181, 258}
SELECTOR_BAMS = ("LOGOTOB", "LOGOTBP", "MAINEEAN")


def resource(index: dict[tuple[str, int], int], bifs: list[str], name: str, kind: int) -> bytes:
    data, _bif = resolve_resource(bifs, index[(name, kind)])
    if data is None:
        raise RuntimeError(f"resource missing: {name}")
    return data


def mos_blocks(data: bytes) -> list[tuple[int, int, int, int, int, int, int]]:
    if data[:8] != b"MOS V2  ":
        raise RuntimeError("MOS V2 expected")
    _width, _height, count, offset = struct.unpack_from("<IIII", data, 8)
    return [struct.unpack_from("<7I", data, offset + block * 28) for block in range(count)]


def bam_frames(data: bytes) -> list[tuple[int, int, list[tuple[int, int, int, int, int, int, int]]]]:
    signature, count, _cycles, _blocks, frames_offset, _cycles_offset, blocks_offset, _palette = struct.unpack_from("<8s7I", data, 0)
    if signature != b"BAM V2  ":
        raise RuntimeError(f"BAM V2 expected, got {signature!r}")
    parsed = []
    for frame in range(count):
        width, height, _center_x, _center_y, packed = struct.unpack_from("<HHhhI", data, frames_offset + frame * 12)
        first, amount = packed & 0xFFFF, packed >> 16
        blocks = [struct.unpack_from("<7I", data, blocks_offset + block * 28) for block in range(first, first + amount)]
        parsed.append((width, height, blocks))
    return parsed


def x4_image(path: Path, expected: tuple[int, int]) -> Image.Image:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    if image.size != expected:
        raise RuntimeError(f"invalid x4 dimensions: {path.name} = {image.size}, expected {expected}")
    return image


def paste_element(atlases: dict[int, Image.Image], image: Image.Image, blocks: list[tuple[int, int, int, int, int, int, int]]) -> None:
    for page, source_x, source_y, width, height, dest_x, dest_y in blocks:
        if page not in atlases:
            raise RuntimeError(f"unexpected selector page MOS{page:04d}")
        part = image.crop((dest_x * SCALE, dest_y * SCALE, (dest_x + width) * SCALE, (dest_y + height) * SCALE))
        atlases[page].paste(part, (source_x * SCALE, source_y * SCALE), part)


def main() -> None:
    bifs, entries = load_key()
    index = {(name.upper(), kind): locator for name, kind, locator in entries}
    source_pages = ROOT / "sources" / "pages"
    topaz = ROOT / "upscale-topaz-recovery-v2-d50"
    atlases: dict[int, Image.Image] = {}
    for page in PAGES:
        if page in MERGED_PAGES:
            preview = VARIANT_ROOT / "assets" / f"MAINMENU-MOS{page:04d}-x4preview.png"
            with Image.open(preview) as opened:
                atlas = opened.convert("RGBA")
        else:
            with Image.open(source_pages / f"MOS{page:04d}-x1.png") as opened:
                original = opened.convert("RGBA")
            atlas = original.resize((original.width * SCALE, original.height * SCALE), Image.Resampling.LANCZOS)
        atlases[page] = atlas

    start3 = x4_image(topaz / "START3EE-background-x4.png", (1024 * SCALE, 768 * SCALE))
    paste_element(atlases, start3, mos_blocks(resource(index, bifs, "START3EE", TYPE_MOS)))

    for bam_name in SELECTOR_BAMS:
        for frame_index, (width, height, blocks) in enumerate(bam_frames(resource(index, bifs, bam_name, TYPE_BAM))):
            image = x4_image(topaz / f"{bam_name}-frame-{frame_index:02d}-x4.png", (width * SCALE, height * SCALE))
            paste_element(atlases, image, blocks)

    output = ROOT / "assets"
    output.mkdir(parents=True, exist_ok=True)
    manifest: list[dict[str, object]] = []
    for page, atlas in sorted(atlases.items()):
        stem = f"MAINMENU-MOS{page:04d}-x4" if page in MERGED_PAGES else f"SELECTOR-MOS{page:04d}-x4"
        preview = output / f"{stem}preview.png"
        asset = output / f"{stem}.dxt5"
        atlas.save(preview)
        buffer = io.BytesIO()
        atlas.save(buffer, format="DDS", pixel_format="DXT5")
        raw = buffer.getvalue()
        expected_bytes = 128 + atlas.width * atlas.height
        if raw[:4] != b"DDS " or len(raw) != expected_bytes:
            raise RuntimeError(f"invalid DXT5 output for MOS{page:04d}")
        asset.write_bytes(raw[128:])
        manifest.append({"page": page, "asset": asset.name, "bytes": asset.stat().st_size, "preview": preview.name, "merged_with_main_menu": page in MERGED_PAGES})
        print(f"packaged {asset.name}: {asset.stat().st_size:,} bytes")
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
