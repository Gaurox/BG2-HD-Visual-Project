"""Round-trip check: re-render an area from the generated TIS/PVRZ and
compare it against the upscaled source image, emulating what the DLL does
(sample a 64*scale span at the raw TIS coordinates)."""
import io
import os
import struct
import sys
import zlib

import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_resource
from mos_decode import pvr_to_dds_bytes

Image.MAX_IMAGE_PIXELS = None


def load_pvrz_file(path):
    blob = open(path, "rb").read()
    declared = struct.unpack_from("<I", blob, 0)[0]
    pvr = zlib.decompress(blob[4:])
    assert len(pvr) == declared, f"{path}: declared {declared}, got {len(pvr)}"
    dds, w, h = pvr_to_dds_bytes(pvr)
    img = Image.open(io.BytesIO(dds))
    img.load()
    return img.convert("RGB")


def main(area, out_dir, upscaled_png):
    bif_entries, res_entries = load_key()
    wed_by = {r[0].upper(): r for r in res_entries if r[1] == 0x03E9}

    wdata, _ = resolve_resource(bif_entries, wed_by[area][2])
    _, _, off_overlays = struct.unpack_from("<III", wdata, 8)
    ov_w, ov_h = struct.unpack_from("<HH", wdata, off_overlays)
    tileset = wdata[off_overlays + 4:off_overlays + 12].split(b"\0")[0].decode("ascii")
    off_tilemap, off_lookup = struct.unpack_from("<II", wdata, off_overlays + 0x10)

    tis = open(os.path.join(out_dir, f"{tileset.upper()}.TIS"), "rb").read()
    assert tis[:8] == b"TIS V1  ", "bad TIS signature"
    tile_count, entry_size, header_size, tile_dim = struct.unpack_from("<IIII", tis, 8)
    print(f"TIS: {tile_count} tiles, entry {entry_size}, header {header_size}, tile dimension {tile_dim}")
    assert entry_size == 12 and header_size == 24
    scale = tile_dim // 64
    assert scale in (1, 2, 4, 8), f"bad tile dimension {tile_dim}"

    prefix = tileset[0] + tileset[2:]
    pages = {}

    def page_img(p):
        if p not in pages:
            pages[p] = load_pvrz_file(os.path.join(out_dir, f"{prefix}{p:02d}.PVRZ".upper()))
        return pages[p]

    span = 64 * scale
    canvas = Image.new("RGB", (ov_w * span, ov_h * span))
    oob = 0
    for cell in range(ov_w * ov_h):
        start, _c, _s, _f = struct.unpack_from("<HHHB3x", wdata, off_tilemap + cell * 10)
        tid = struct.unpack_from("<H", wdata, off_lookup + start * 2)[0]
        page, u, v = struct.unpack_from("<3I", tis, header_size + tid * 12)
        col, row = cell % ov_w, cell // ov_w
        if page == 0xFFFFFFFF:
            continue
        img = page_img(page)
        if u + span > img.width or v + span > img.height:
            oob += 1
            continue
        canvas.paste(img.crop((u, v, u + span, v + span)), (col * span, row * span))

    print(f"out-of-bounds tiles: {oob}")

    src = Image.open(upscaled_png).convert("RGB")
    print(f"rendered {canvas.size}, source {src.size}")
    assert canvas.size == src.size

    a = np.asarray(canvas, dtype=np.float64)
    b = np.asarray(src, dtype=np.float64)
    mse = float(np.mean((a - b) ** 2))
    psnr = float("inf") if mse == 0 else 10 * np.log10(255.0 ** 2 / mse)
    print(f"MSE={mse:.3f}  PSNR={psnr:.2f} dB")

    # Ignore black tiles when judging: they are legitimately absent.
    diff = np.abs(a - b).max(axis=2)
    nonblack = b.max(axis=2) > 8
    if nonblack.any():
        print(f"non-black pixels: max abs diff {diff[nonblack].max():.0f}, "
              f"mean {diff[nonblack].mean():.2f}")

    if "--write-canvas" in sys.argv[4:]:
        canvas.save(os.path.join(out_dir, "_roundtrip_render.png"))
        print("full rendered canvas written")

    canvas.resize((canvas.width // 8, canvas.height // 8)).save(
        os.path.join(out_dir, "_roundtrip_thumb.png"))
    print("thumbnail written")
    print("rappel : apres integration + QA en jeu, mettre a jour areas.csv "
          "(refresh_area_catalog.py, puis runs/build/status et leurs equivalents _nuit)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3])
