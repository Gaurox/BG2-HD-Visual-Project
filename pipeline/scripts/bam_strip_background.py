"""Make an area animation's redundant background transparent.

Many BG2 area animations paint a rectangle of ordinary scenery around the part
that actually moves. That rectangle is drawn at the original resolution on top
of upscaled tiles, which is exactly what shows up in game as a soft, slightly
mismatched square. Where the animation merely repeats the tile beneath it, the
pixel can be made transparent and the upscaled tile shows through instead.

A pixel is only cleared when it matches the underlying art in EVERY frame, so
anything that moves at any point in the cycle is preserved.
"""
import os
from pathlib import Path
import struct
import sys
import zlib

import numpy as np
from PIL import Image

from bam_export import decode_bam
from bg2lib import load_key, resolve_resource
from scipy.ndimage import binary_closing, label

Image.MAX_IMAGE_PIXELS = None
AREA = "AR0602"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
AREA_PNG = PROJECT_ROOT / "maps" / AREA / "rendus-x1" / "tuiles-principales" / f"{AREA}-tuiles-principales-x1.png"
MOTION_THRESHOLD = int(os.environ.get("IEE_BAM_MOTION", "10"))  # per-pixel change across the cycle
FAR_THRESHOLD = int(os.environ.get("IEE_BAM_FAR", "60"))        # departure from the tile the tile cannot cover
MIN_COMPONENT = int(os.environ.get("IEE_BAM_MINCOMP", "40"))  # smallest kept fragment, in pixels
MIN_REDUNDANCY = 0.25   # skip animations that are mostly genuine content


def write_bam_v1(original, frames, transparent):
    """Rebuild a BAM V1 with new (uncompressed) frame pixel data."""
    frame_count, cycle_count, tr = struct.unpack_from("<HBB", original, 8)
    off_frames, off_palette, off_lookup = struct.unpack_from("<III", original, 0x0C)
    off_cycles = off_frames + frame_count * 12

    cycles = original[off_cycles:off_cycles + cycle_count * 4]
    palette = original[off_palette:off_palette + 1024]

    lookup_len = 0
    for c in range(cycle_count):
        n, first = struct.unpack_from("<HH", original, off_cycles + c * 4)
        lookup_len = max(lookup_len, first + n)
    lookup = original[off_lookup:off_lookup + lookup_len * 2]

    hdr = 0x18
    new_off_frames = hdr
    new_off_cycles = new_off_frames + frame_count * 12
    new_off_palette = new_off_cycles + cycle_count * 4
    new_off_lookup = new_off_palette + 1024
    data_start = new_off_lookup + len(lookup)

    entries = bytearray()
    blob = bytearray()
    for i in range(frame_count):
        idx, cx, cy, _ = frames[i]
        h, w = idx.shape
        off = data_start + len(blob)
        entries += struct.pack("<HHhhI", w, h, cx, cy, off | 0x80000000)
        blob += idx.astype(np.uint8).tobytes()

    out = bytearray()
    out += b"BAM V1  "
    out += struct.pack("<HBB", frame_count, cycle_count, transparent)
    out += struct.pack("<III", new_off_frames, new_off_palette, new_off_lookup)
    assert len(out) == hdr
    out += entries
    out += cycles
    out += palette
    out += lookup
    out += blob
    return bytes(out)


def main(outdir):
    os.makedirs(outdir, exist_ok=True)
    bif, res = load_key()
    are_by = {r[0].upper(): r for r in res if r[1] == 0x03F2}
    bam_by = {r[0].upper(): r for r in res if r[1] == 0x03E8}

    adata, _ = resolve_resource(bif, are_by[AREA][2])
    count = struct.unpack_from("<I", adata, 0xAC)[0]
    aoff = struct.unpack_from("<I", adata, 0xB0)[0]

    placements = {}
    for i in range(count):
        b = aoff + i * 76
        name = adata[b + 0x28:b + 0x30].split(b"\0")[0].decode("ascii", "replace").upper()
        x, y = struct.unpack_from("<hh", adata, b + 0x20)
        placements.setdefault(name, []).append((x, y))

    area = np.asarray(Image.open(AREA_PNG).convert("RGB"), dtype=np.int16)

    print(f"{'BAM':<10}{'uses':>5}{'cleared':>10}   result")
    for name, pos in sorted(placements.items()):
        if name not in bam_by:
            continue
        if len(pos) != 1:
            print(f"{name:<10}{len(pos):>5}{'-':>10}   ignore (place a plusieurs endroits)")
            continue

        raw, _ = resolve_resource(bif, bam_by[name][2])
        if raw[0:4] == b"BAMC":
            raw = zlib.decompress(raw[12:])
        frames, rgb, tr = decode_bam(raw)
        x, y = pos[0]

        # The tile underneath already carries every static part of these
        # animations - often the whole object. So keep a pixel only when it
        # actually moves during the cycle, or when it departs far enough from
        # the tile that the tile cannot stand in for it.
        redundant = None
        ok = True
        stack = []
        for idx, cx, cy, _ in frames:
            h, w = idx.shape
            x0, y0 = x - cx, y - cy
            if x0 < 0 or y0 < 0 or y0 + h > area.shape[0] or x0 + w > area.shape[1]:
                ok = False
                break
            under = area[y0:y0 + h, x0:x0 + w]
            over = rgb[idx].astype(np.int16)
            far = (np.abs(over - under).mean(axis=2) >= FAR_THRESHOLD) & (idx != tr)
            if stack and stack[-1][0].shape != over.shape:
                ok = False
                break
            stack.append((over, far))

        if ok and stack:
            cube = np.stack([s[0] for s in stack])
            moves = (cube.max(axis=0) - cube.min(axis=0)).mean(axis=2) >= MOTION_THRESHOLD
            far_any = np.any([s[1] for s in stack], axis=0)
            redundant = ~(moves | far_any)

        # Binary transparency has no gradient, so a ragged mask reads as hard
        # speckle in game. Close pinholes, then drop kept fragments that are too
        # small to be real content - they are threshold noise in the light spill.
        if ok and redundant is not None:
            kept = ~redundant
            kept = binary_closing(kept, np.ones((3, 3), bool))
            labels, n = label(kept)
            if n:
                sizes = np.bincount(labels.ravel())
                sizes[0] = 0
                keep_ids = np.where(sizes >= MIN_COMPONENT)[0]
                kept = np.isin(labels, keep_ids)
            redundant = ~kept
        if not ok or redundant is None:
            print(f"{name:<10}{len(pos):>5}{'-':>10}   ignore (frames de tailles differentes ou hors carte)")
            continue

        opaque = sum(int((f[0] != tr).sum()) for f in frames)
        cleared = int(redundant.sum()) * len(frames)
        share = cleared / max(opaque, 1)
        if share < MIN_REDUNDANCY:
            print(f"{name:<10}{len(pos):>5}{share*100:9.0f}%   ignore (contenu majoritairement reel)")
            continue

        new_frames = []
        for idx, cx, cy, _ in frames:
            n = idx.copy()
            n[redundant] = tr
            new_frames.append((n, cx, cy, tr))

        blob = write_bam_v1(raw, new_frames, tr)
        path = os.path.join(outdir, f"{name}.BAM")
        with open(path, "wb") as fh:
            fh.write(blob)
        print(f"{name:<10}{len(pos):>5}{share*100:9.0f}%   ecrit {os.path.basename(path)} ({len(blob):,} o)")


if __name__ == "__main__":
    main(sys.argv[1])
