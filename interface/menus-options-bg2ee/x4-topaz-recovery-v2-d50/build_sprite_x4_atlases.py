"""Build reversible x4 main-menu atlases from individually upscaled visual elements.

Unlike the earlier atlas-wide experiment, every LOGOSOA and STARTMBT BAM frame
is extracted with alpha and upscaled independently. START2EE is a single MOS
background composition and is treated as its own visual element. No game
archive is ever written by this tool.
"""

from __future__ import annotations

import argparse
import io
import json
import struct
import sys
from collections import defaultdict
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from bg2lib import load_key, resolve_resource  # noqa: E402
from mos_decode import decode_mos_v2, decode_pvrz_page  # noqa: E402


ROOT = Path(__file__).resolve().parent
SCALE = 4
TYPE_BAM = 1000
TYPE_MOS = 1004
TYPE_PVRZ = 1028
PAGES = (181, 257, 258, 261, 262, 265, 266)
ASSET_NAMES = {page: f"MAINMENU-MOS{page:04d}-x4.dxt5" for page in PAGES}


def load_resources() -> tuple[list[str], dict[tuple[str, int], int]]:
    bifs, entries = load_key()
    return bifs, {(name.upper(), resource_type): locator for name, resource_type, locator in entries}


def read_resource(index: dict[tuple[str, int], int], bifs: list[str], name: str, resource_type: int) -> bytes:
    try:
        locator = index[(name.upper(), resource_type)]
    except KeyError as error:
        raise KeyError(f"ressource absente : {name} (type {resource_type})") from error
    data, _bif = resolve_resource(bifs, locator)
    if data is None:
        raise RuntimeError(f"impossible de lire {name}")
    return data


def parse_bam(data: bytes) -> list[dict[str, object]]:
    signature, frame_count, _cycle_count, _block_count, frames_off, _cycles_off, blocks_off, _ = struct.unpack_from(
        "<8s7I", data, 0
    )
    if signature != b"BAM V2  ":
        raise ValueError("BAM V2 attendu")
    frames: list[dict[str, object]] = []
    for index in range(frame_count):
        width, height, center_x, center_y, packed_blocks = struct.unpack_from("<HHhhI", data, frames_off + index * 12)
        first = packed_blocks & 0xFFFF
        count = packed_blocks >> 16
        blocks = [
            list(struct.unpack_from("<7I", data, blocks_off + block_index * 28))
            for block_index in range(first, first + count)
        ]
        frames.append({"width": width, "height": height, "center_x": center_x, "center_y": center_y, "blocks": blocks})
    return frames


def parse_mos_v2(data: bytes) -> tuple[int, int, list[list[int]]]:
    if data[:8] != b"MOS V2  ":
        raise ValueError("MOS V2 attendu")
    width, height, block_count, blocks_off = struct.unpack_from("<IIII", data, 8)
    blocks = [list(struct.unpack_from("<7I", data, blocks_off + index * 28)) for index in range(block_count)]
    return width, height, blocks


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def extract() -> None:
    bifs, index = load_resources()
    source_pages = ROOT / "sources" / "pages"
    sprite_dir = ROOT / "sources" / "sprites"
    source_pages.mkdir(parents=True, exist_ok=True)
    sprite_dir.mkdir(parents=True, exist_ok=True)
    page_images: dict[int, Image.Image] = {}
    for page in PAGES:
        image = decode_pvrz_page(read_resource(index, bifs, f"MOS{page:04d}", TYPE_PVRZ)).convert("RGBA")
        page_images[page] = image
        image.save(source_pages / f"MOS{page:04d}-x1.png")

    manifest: dict[str, object] = {"scale": SCALE, "pages": list(PAGES), "sprites": []}
    for bam_name in ("LOGOSOA", "STARTMBT", "TITLE"):
        frames = parse_bam(read_resource(index, bifs, bam_name, TYPE_BAM))
        for frame_index, frame in enumerate(frames):
            width, height = int(frame["width"]), int(frame["height"])
            sprite = Image.new("RGBA", (width, height), (0, 0, 0, 0))
            for page, source_x, source_y, block_width, block_height, dest_x, dest_y in frame["blocks"]:
                part = page_images[page].crop((source_x, source_y, source_x + block_width, source_y + block_height))
                sprite.paste(part, (dest_x, dest_y), part)
            relative = Path("sources") / "sprites" / f"{bam_name}-frame-{frame_index:02d}.png"
            sprite.save(ROOT / relative)
            manifest["sprites"].append(
                {
                    "name": f"{bam_name}-frame-{frame_index:02d}",
                    "source": relative.as_posix(),
                    "width": width,
                    "height": height,
                    "blocks": frame["blocks"],
                }
            )

    mos_data = read_resource(index, bifs, "START2EE", TYPE_MOS)
    mos_width, mos_height, mos_blocks = parse_mos_v2(mos_data)
    background = decode_mos_v2(mos_data, lambda page: page_images[page]).convert("RGBA")
    background_relative = Path("sources") / "START2EE-background-x1.png"
    background.save(ROOT / background_relative)
    manifest["background"] = {
        "source": background_relative.as_posix(),
        "width": mos_width,
        "height": mos_height,
        "blocks": mos_blocks,
    }
    write_json(ROOT / "sprite-manifest.json", manifest)
    print(f"extracted {len(manifest['sprites'])} sprites and START2EE background")


def image_x4(path: Path, expected: tuple[int, int]) -> Image.Image:
    with Image.open(path) as opened:
        image = opened.convert("RGBA")
    if image.size != expected:
        raise RuntimeError(f"taille invalide : {path.name} = {image.size}, attendu {expected}")
    return image


def package() -> None:
    manifest = json.loads((ROOT / "sprite-manifest.json").read_text(encoding="utf-8"))
    atlases: dict[int, Image.Image] = {}
    for page in manifest["pages"]:
        original = Image.open(ROOT / "sources" / "pages" / f"MOS{page:04d}-x1.png").convert("RGBA")
        atlases[page] = original.resize((original.width * SCALE, original.height * SCALE), Image.Resampling.LANCZOS)

    background = manifest["background"]
    background_x4 = image_x4(ROOT / "upscale-topaz-recovery-v2-d50" / "START2EE-background-x4.png", (background["width"] * SCALE, background["height"] * SCALE))
    for page, source_x, source_y, width, height, dest_x, dest_y in background["blocks"]:
        part = background_x4.crop((dest_x * SCALE, dest_y * SCALE, (dest_x + width) * SCALE, (dest_y + height) * SCALE))
        atlases[page].paste(part, (source_x * SCALE, source_y * SCALE), part)

    for sprite in manifest["sprites"]:
        upscaled = image_x4(ROOT / "upscale-topaz-recovery-v2-d50" / f"{sprite['name']}-x4.png", (sprite["width"] * SCALE, sprite["height"] * SCALE))
        for page, source_x, source_y, width, height, dest_x, dest_y in sprite["blocks"]:
            part = upscaled.crop((dest_x * SCALE, dest_y * SCALE, (dest_x + width) * SCALE, (dest_y + height) * SCALE))
            atlases[page].paste(part, (source_x * SCALE, source_y * SCALE), part)

    output = ROOT / "assets"
    output.mkdir(parents=True, exist_ok=True)
    for page, atlas in atlases.items():
        atlas.save(output / f"{ASSET_NAMES[page][:-5]}preview.png")
        buffer = io.BytesIO()
        atlas.save(buffer, format="DDS", pixel_format="DXT5")
        dds = buffer.getvalue()
        expected_bytes = 128 + atlas.width * atlas.height
        if dds[:4] != b"DDS " or len(dds) != expected_bytes:
            raise RuntimeError(f"DDS invalide pour MOS{page:04d}")
        path = output / ASSET_NAMES[page]
        path.write_bytes(dds[128:])
        print(f"packaged {path.name}: {path.stat().st_size:,} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", action="store_true")
    args = parser.parse_args()
    package() if args.package else extract()
