"""Package the Topaz Low Resolution x2 BIGLOGO result into the MOS0017 DXT5 atlas."""

from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = next(parent for parent in ROOT.parents if (parent / "pipeline" / "scripts").is_dir())
SOURCE_ROOT = PROJECT_ROOT / "interface" / "menus-options-bg2ee" / "reference" / "extracted-game-resources"
sys.path.insert(0, str(PROJECT_ROOT / "pipeline" / "scripts"))
from mos_decode import decode_pvrz_page  # noqa: E402


SCALE = 2
FRAME_ZERO_BLOCK_COUNT = 21


def frame_zero_blocks() -> list[tuple[int, int, int, int, int, int, int]]:
    data = (SOURCE_ROOT / "BIGLOGO.bam").read_bytes()
    signature, frame_count, _cycles, block_count, frames_off, _cycles_off, blocks_off, _palette = struct.unpack_from("<8s7I", data, 0)
    if signature != b"BAM V2  " or frame_count < 1 or block_count < FRAME_ZERO_BLOCK_COUNT:
        raise ValueError("BIGLOGO.BAM V2 unexpected")
    _w, _h, _cx, _cy, packed_blocks = struct.unpack_from("<HHhhI", data, frames_off)
    first_block, count = packed_blocks & 0xFFFF, packed_blocks >> 16
    if first_block != 0 or count != FRAME_ZERO_BLOCK_COUNT:
        raise ValueError(f"unexpected BIGLOGO frame 0 blocks: start={first_block}, count={count}")
    return [struct.unpack_from("<7I", data, blocks_off + index * 28) for index in range(first_block, first_block + count)]


def main() -> None:
    original = decode_pvrz_page((SOURCE_ROOT / "MOS0017.pvrz").read_bytes()).convert("RGBA")
    if original.size != (1024, 1024):
        raise ValueError(f"unexpected MOS0017 size: {original.size}")
    topaz = Image.open(ROOT / "x2" / "BIGLOGO-options-frame-0-original-topaz-low-resolution-x2.png").convert("RGBA")
    if topaz.size != (346 * SCALE, 449 * SCALE):
        raise ValueError(f"unexpected Topaz x2 size: {topaz.size}")
    atlas = original.resize((1024 * SCALE, 1024 * SCALE), Image.Resampling.LANCZOS)
    for page, src_x, src_y, width, height, dst_x, dst_y in frame_zero_blocks():
        if page != 17:
            raise ValueError(f"BIGLOGO frame 0 unexpectedly references page {page}")
        crop = topaz.crop((dst_x * SCALE, dst_y * SCALE, (dst_x + width) * SCALE, (dst_y + height) * SCALE))
        atlas.paste(crop, (src_x * SCALE, src_y * SCALE), crop)
    output = ROOT / "assets"
    output.mkdir(parents=True, exist_ok=True)
    preview = output / "BIGLOGO-MOS0017-x2-topaz-lowres-preview.png"
    atlas.save(preview)
    buffer = io.BytesIO()
    atlas.save(buffer, format="DDS", pixel_format="DXT5")
    dds = buffer.getvalue()
    if dds[:4] != b"DDS " or len(dds) != 128 + 2048 * 2048:
        raise ValueError(f"unexpected DXT5 DDS output: {len(dds)} bytes")
    asset = output / "BIGLOGO-MOS0017-x2-topaz-lowres.dxt5"
    asset.write_bytes(dds[128:])
    print(f"wrote {asset} ({asset.stat().st_size:,} bytes)")
    print(f"preview {preview}")


if __name__ == "__main__":
    main()
