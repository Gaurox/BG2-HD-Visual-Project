"""Do the opaque BAM frames merely repeat the tile art underneath them?

If they do, the rectangle seen in game is redundant background that could be
made transparent, letting the upscaled tiles show through - no engine change
needed.
"""
import struct
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_resource
from bam_export import decode_bam

Image.MAX_IMAGE_PIXELS = None
AREA = "AR0602"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AREA_PNG = PROJECT_ROOT / "maps" / AREA / "rendus-x1" / "tuiles-principales" / f"{AREA}-tuiles-principales-x1.png"

bif, res = load_key()
are_by = {r[0].upper(): r for r in res if r[1] == 0x03F2}
bam_by = {r[0].upper(): r for r in res if r[1] == 0x03E8}

data, _ = resolve_resource(bif, are_by[AREA][2])
count = struct.unpack_from("<I", data, 0xAC)[0]
off = struct.unpack_from("<I", data, 0xB0)[0]

area = np.asarray(Image.open(AREA_PNG).convert("RGB"), dtype=np.int16)

print(f"{'BAM':<10}{'pos':>12}{'frame':>11}{'opaque':>9}{'vs tiles':>26}")
seen = set()
for i in range(count):
    b = off + i * 76
    name = data[b + 0x28:b + 0x30].split(b"\0")[0].decode("ascii", "replace").upper()
    x, y = struct.unpack_from("<hh", data, b + 0x20)
    if name in seen or name not in bam_by:
        continue
    seen.add(name)

    raw, _ = resolve_resource(bif, bam_by[name][2])
    if raw[0:4] == b"BAMC":
        raw = zlib.decompress(raw[12:])
    frames, rgb, tr = decode_bam(raw)
    idx, cx, cy, _ = frames[0]
    h, w = idx.shape
    opaque = float((idx != tr).mean())

    # where the engine puts this frame
    x0, y0 = x - cx, y - cy
    if x0 < 0 or y0 < 0 or y0 + h > area.shape[0] or x0 + w > area.shape[1]:
        print(f"{name:<10}{f'({x},{y})':>12}{f'{w}x{h}':>11}{opaque*100:8.0f}%{'  hors carte':>26}")
        continue

    under = area[y0:y0 + h, x0:x0 + w]
    over = rgb[idx].astype(np.int16)
    mask = (idx != tr)
    if mask.sum() == 0:
        verdict = "  entierement transparent"
    else:
        diff = np.abs(over - under).mean(axis=2)[mask]
        same = float((diff < 12).mean())
        verdict = f"  {diff.mean():5.1f}/255, {same*100:3.0f}% identique"
    print(f"{name:<10}{f'({x},{y})':>12}{f'{w}x{h}':>11}{opaque*100:8.0f}%{verdict:>26}")

print("\n'% identique' = pixels opaques du BAM qui reproduisent deja la tuile en dessous")
