"""Render the area a second time with the door (secondary) tiles substituted in.

The main area render only ever shows primary tiles, so the alternate door art
has no upscaled source. Rendering it in place - surrounded by its real
neighbours - lets the same upscaler treat it in the same context, instead of
resampling it and leaving visibly original-looking squares in game.
"""
import struct
import sys
from pathlib import Path
import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_resource, resolve_tileset_resource
from area_decode import decode_tis_tiles

NIGHT = "--night" in sys.argv
_positional = [a for a in sys.argv[1:] if a != "--night"]
AREA = _positional[0] if _positional else "AR0602"
WED_RESREF = f"{AREA}N" if NIGHT else AREA
PROJECT_ROOT = Path(__file__).resolve().parents[2]
VARIANT_DIR = "tuiles-secondaires-nuit" if NIGHT else "tuiles-secondaires"
FILE_STEM = f"{AREA}N" if NIGHT else AREA
OUT = (
    Path(_positional[1])
    if len(_positional) > 1
    else PROJECT_ROOT / "maps" / AREA / "rendus-x1" / VARIANT_DIR / f"{FILE_STEM}-tuiles-secondaires-x1.png"
)
OUT.parent.mkdir(parents=True, exist_ok=True)

bif, res = load_key()
wed_by = {r[0].upper(): r for r in res if r[1] == 0x03E9}
tis_by = {r[0].upper(): r for r in res if r[1] == 0x03EB}
pvrz_by = {r[0].upper(): r for r in res if r[1] == 0x0404}

if WED_RESREF not in wed_by:
    raise KeyError(f"WED not found for {WED_RESREF}" + (" (no night variant)" if NIGHT else ""))
w, _ = resolve_resource(bif, wed_by[WED_RESREF][2])
_, _, off_ov = struct.unpack_from("<III", w, 8)
ov_w, ov_h = struct.unpack_from("<HH", w, off_ov)
tileset = w[off_ov + 4:off_ov + 12].split(b"\0")[0].decode("ascii")
tm, lut = struct.unpack_from("<II", w, off_ov + 0x10)

get_tile, tile_count = decode_tis_tiles(bif, pvrz_by, tileset.upper(), tis_by[tileset.upper()][2])

canvas = Image.new("RGB", (ov_w * 64, ov_h * 64))
doors = []
invalid_secondary = []
for cell in range(ov_w * ov_h):
    start, _cnt, sec, _flags = struct.unpack_from("<HHHB3x", w, tm + cell * 10)
    tid = struct.unpack_from("<H", w, lut + start * 2)[0]
    use = tid
    if sec != 0xFFFF:
        if sec < tile_count:
            use = sec
            doors.append((cell % ov_w, cell // ov_w, tid, sec))
        else:
            invalid_secondary.append((cell % ov_w, cell // ov_w, tid, sec))
    col, row = cell % ov_w, cell // ov_w
    canvas.paste(get_tile(use).convert("RGB"), (col * 64, row * 64))

canvas.save(OUT)
print(f"wrote {OUT}  {canvas.size}  ({len(doors)} door cells substituted)")
if invalid_secondary:
    print(f"invalid secondary tile references: {len(invalid_secondary)}; primary tiles retained")

# how different is the door art from the primary at the same cell?
diffs = []
for col, row, tid, sec in doors:
    a = np.asarray(get_tile(tid).convert("RGB"), dtype=np.float64)
    b = np.asarray(get_tile(sec).convert("RGB"), dtype=np.float64)
    diffs.append(np.abs(a - b).mean())
diffs = np.array(diffs)
if not len(diffs):
    print("no secondary tiles: the secondary render is identical to the main render")
else:
    print(f"door art vs primary art: mean abs diff = {diffs.mean():.1f}/255 "
          f"(min {diffs.min():.1f}, max {diffs.max():.1f})")
    print(f"cells where the two are near-identical (<3): {(diffs < 3).sum()} of {len(diffs)}")
