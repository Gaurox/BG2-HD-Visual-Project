"""Build the reversible BIGLOGO x4 atlas while preserving original UV coordinates."""

from __future__ import annotations

import argparse
import io
import struct
import sys
from pathlib import Path

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[3]
ROOT = Path(__file__).resolve().parent
SOURCE_ROOT = PROJECT_ROOT / "interface" / "menus-options-bg2ee" / "reference" / "extracted-game-resources"
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from mos_decode import decode_pvrz_page  # noqa: E402


SCALE = 4
FRAME_ZERO_BLOCK_COUNT = 21


def frame_zero_blocks(bam_path: Path) -> list[tuple[int, int, int, int, int, int, int]]:
    data = bam_path.read_bytes()
    signature, frame_count, _cycles, block_count, frames_off, _cycles_off, blocks_off, _palette = struct.unpack_from("<8s7I", data, 0)
    if signature != b"BAM V2  " or frame_count < 1 or block_count < FRAME_ZERO_BLOCK_COUNT:
        raise ValueError("BIGLOGO.BAM V2 unexpected")
    _w, _h, _cx, _cy, packed_blocks = struct.unpack_from("<HHhhI", data, frames_off)
    first_block, count = packed_blocks & 0xFFFF, packed_blocks >> 16
    if first_block != 0 or count != FRAME_ZERO_BLOCK_COUNT:
        raise ValueError(f"unexpected BIGLOGO frame 0 blocks: start={first_block}, count={count}")
    return [struct.unpack_from("<7I", data, blocks_off + index * 28) for index in range(first_block, first_block + count)]


def create_atlas(output_dir: Path) -> tuple[Path, Path]:
    original_page = decode_pvrz_page((SOURCE_ROOT / "MOS0017.pvrz").read_bytes()).convert("RGBA")
    if original_page.size != (1024, 1024):
        raise ValueError(f"unexpected MOS0017 size: {original_page.size}")
    logo = Image.open(ROOT / "upscale-topaz-recovery-v2-d50" / "BIGLOGO-options-frame-0-x4.png").convert("RGBA")
    if logo.size != (346 * SCALE, 449 * SCALE):
        raise ValueError(f"unexpected SeedVR x4 size: {logo.size}")
    atlas = original_page.resize((1024 * SCALE, 1024 * SCALE), Image.Resampling.LANCZOS)
    for page, src_x, src_y, width, height, dst_x, dst_y in frame_zero_blocks(SOURCE_ROOT / "BIGLOGO.bam"):
        if page != 17:
            raise ValueError(f"BIGLOGO frame 0 unexpectedly references page {page}")
        crop = logo.crop((dst_x * SCALE, dst_y * SCALE, (dst_x + width) * SCALE, (dst_y + height) * SCALE))
        atlas.paste(crop, (src_x * SCALE, src_y * SCALE), crop)
    output_dir.mkdir(parents=True, exist_ok=True)
    preview = output_dir / "BIGLOGO-MOS0017-x4-atlas-preview.png"
    atlas.save(preview)
    dds = io.BytesIO()
    atlas.save(dds, format="DDS", pixel_format="DXT5")
    raw = dds.getvalue()
    if raw[:4] != b"DDS " or len(raw) != 128 + 4096 * 4096:
        raise ValueError(f"unexpected DXT5 DDS output: {len(raw)} bytes")
    output = output_dir / "BIGLOGO-MOS0017-x4.dxt5"
    output.write_bytes(raw[128:])
    return output, preview


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=ROOT / "assets")
    args = parser.parse_args()
    asset, preview = create_atlas(args.output_dir)
    print(f"wrote {asset} ({asset.stat().st_size:,} bytes)")
    print(f"preview {preview}")
