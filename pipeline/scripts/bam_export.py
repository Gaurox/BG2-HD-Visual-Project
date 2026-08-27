"""Decode BAM V1 area animations and export them for upscaling.

Emits, per animation:
  <NAME>_sheet.png   all frames side by side, RGB, transparent pixels matted
  <NAME>_alpha.png   the matching alpha mask
  <NAME>.gif         a preview of the animation
Splitting colour from alpha matters: upscalers handle RGB well and alpha badly,
so the mask is carried separately and recombined afterwards.
"""
import os
import struct
import sys
import zlib

import numpy as np
from PIL import Image

from bg2lib import load_key, resolve_resource

BAM_TYPE = 0x03E8


def load_bam(bif, entry):
    data, _ = resolve_resource(bif, entry[2])
    if data[0:4] == b"BAMC":
        data = zlib.decompress(data[12:])
    if data[0:4] != b"BAM " or data[4:8] != b"V1  ":
        raise ValueError(f"unsupported BAM: {data[0:8]!r}")
    return data


def decode_bam(data):
    frame_count, cycle_count, transparent = struct.unpack_from("<HBB", data, 8)
    off_frames, off_palette, off_lookup = struct.unpack_from("<III", data, 0x0C)

    palette = np.frombuffer(data, dtype=np.uint8, count=256 * 4,
                            offset=off_palette).reshape(256, 4)
    rgb = palette[:, [2, 1, 0]].astype(np.uint8)

    frames = []
    for i in range(frame_count):
        b = off_frames + i * 12
        w, h, cx, cy = struct.unpack_from("<HHhh", data, b)
        raw = struct.unpack_from("<I", data, b + 8)[0]
        compressed = (raw & 0x80000000) == 0
        offset = raw & 0x7FFFFFFF
        if w == 0 or h == 0:
            frames.append((np.zeros((1, 1), np.uint8), 0, 0, transparent))
            continue
        need = w * h
        if compressed:
            out = np.empty(need, dtype=np.uint8)
            p, n = offset, 0
            while n < need:
                v = data[p]; p += 1
                if v == transparent:
                    run = data[p] + 1; p += 1
                    run = min(run, need - n)
                    out[n:n + run] = transparent
                    n += run
                else:
                    out[n] = v
                    n += 1
        else:
            out = np.frombuffer(data, dtype=np.uint8, count=need, offset=offset).copy()
        frames.append((out.reshape(h, w), cx, cy, transparent))
    return frames, rgb, transparent


def export(name, frames, rgb, transparent, outdir):
    maxw = max(f.shape[1] for f, _, _, _ in frames)
    maxh = max(f.shape[0] for f, _, _, _ in frames)
    n = len(frames)

    sheet = np.zeros((maxh, maxw * n, 3), dtype=np.uint8)
    alpha = np.zeros((maxh, maxw * n), dtype=np.uint8)
    previews = []
    for i, (idx, cx, cy, tr) in enumerate(frames):
        h, w = idx.shape
        colour = rgb[idx]
        mask = (idx != tr).astype(np.uint8) * 255
        # matte the transparent pixels with the nearest opaque colour so the
        # upscaler is not fed hard edges against an arbitrary background
        if mask.any() and (mask == 0).any():
            filled = colour.copy()
            m = mask > 0
            for _ in range(4):
                if m.all():
                    break
                for ax, sh in ((0, 1), (0, -1), (1, 1), (1, -1)):
                    src_m = np.roll(m, sh, axis=ax)
                    src_c = np.roll(filled, sh, axis=ax)
                    fill = src_m & ~m
                    filled[fill] = src_c[fill]
                    m = m | fill
            colour = filled
        sheet[:h, i * maxw:i * maxw + w] = colour
        alpha[:h, i * maxw:i * maxw + w] = mask
        rgba = np.dstack([rgb[idx], (idx != tr).astype(np.uint8) * 255])
        previews.append(Image.fromarray(rgba, "RGBA"))

    os.makedirs(outdir, exist_ok=True)
    Image.fromarray(sheet).save(os.path.join(outdir, f"{name}_sheet.png"))
    Image.fromarray(alpha).save(os.path.join(outdir, f"{name}_alpha.png"))
    canvas = [Image.new("RGBA", (maxw, maxh), (0, 0, 0, 0)) for _ in previews]
    for c, p in zip(canvas, previews):
        c.paste(p, (0, 0))
    canvas[0].save(os.path.join(outdir, f"{name}.gif"), save_all=True,
                   append_images=canvas[1:], duration=100, loop=0, disposal=2)
    return maxw, maxh, n


def main(names, outdir):
    bif, res = load_key()
    bam_by = {r[0].upper(): r for r in res if r[1] == BAM_TYPE}
    print(f"{'BAM':<10}{'frames':>7}{'sheet':>14}")
    for name in names:
        entry = bam_by.get(name.upper())
        if entry is None:
            print(f"{name:<10} introuvable")
            continue
        frames, rgb, tr = decode_bam(load_bam(bif, entry))
        w, h, n = export(name.upper(), frames, rgb, tr, outdir)
        print(f"{name:<10}{n:>7}{f'{w*n} x {h}':>14}")


if __name__ == "__main__":
    out = sys.argv[1]
    main(sys.argv[2:], out)
