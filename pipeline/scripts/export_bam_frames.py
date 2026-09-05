"""Export a BAM V1 into aligned PNG frames for temporal-interpolation tests.

The files in ``rgba/`` preserve the original pixels and binary alpha.  ``rgb/``
and ``alpha/`` are supplied for image models that cannot accept alpha.  Frames
are placed on one shared canvas around their BAM centre coordinates, so motion
is not lost by independently cropping every frame.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image

from bam_export import decode_bam


SCHEMA = "bg2-upscale-animation-frames-x1-v1"


def configure_utf8_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def save_png_atomic(image: Image.Image, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    image.save(temporary, format="PNG")
    temporary.replace(destination)


def write_json_atomic(payload: dict, destination: Path) -> None:
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(destination)


def read_bam(path: Path) -> bytes:
    data = path.read_bytes()
    if data[:4] == b"BAMC":
        data = zlib.decompress(data[12:])
    if data[:8] != b"BAM V1  ":
        raise ValueError(f"{path.name}: BAM V1 expected, got {data[:8]!r}")
    return data


def cycle_metadata(data: bytes, frame_count: int) -> list[dict[str, object]]:
    off_frames, _, off_lookup = struct.unpack_from("<III", data, 0x0C)
    cycle_count = data[0x0A]
    cycle_offset = off_frames + frame_count * 12
    cycles = []
    for index in range(cycle_count):
        count, start = struct.unpack_from("<HH", data, cycle_offset + index * 4)
        lookup = list(struct.unpack_from(f"<{count}H", data, off_lookup + start * 2))
        cycles.append({"cycle": index, "lookup_start": start, "frame_indices": lookup})
    return cycles


def fill_transparent(colour: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Fill transparent RGB only for model input; alpha remains authoritative."""
    filled = colour.copy()
    known = alpha > 0
    for _ in range(max(colour.shape[:2])):
        if known.all():
            break
        changed = np.zeros_like(known)
        for axis, shift in ((0, 1), (0, -1), (1, 1), (1, -1)):
            source_known = np.roll(known, shift, axis=axis)
            source_colour = np.roll(filled, shift, axis=axis)
            take = source_known & ~known & ~changed
            filled[take] = source_colour[take]
            changed |= take
        if not changed.any():
            break
        known |= changed
    return filled


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path, help="BAM V1 or BAMC source")
    parser.add_argument("output", type=Path, help="Empty destination folder")
    args = parser.parse_args()

    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty directory: {args.output}")

    source = args.source.resolve()
    output = args.output.resolve()
    data = read_bam(source)
    frames, palette, transparent = decode_bam(data)
    frame_count = len(frames)
    left = min(-centre_x for _, centre_x, _, _ in frames)
    top = min(-centre_y for _, _, centre_y, _ in frames)
    right = max(-centre_x + indices.shape[1] for indices, centre_x, _, _ in frames)
    bottom = max(-centre_y + indices.shape[0] for indices, _, centre_y, _ in frames)
    canvas_size = (right - left, bottom - top)

    rgba_dir = output / "rgba"
    rgb_dir = output / "rgb"
    alpha_dir = output / "alpha"
    for directory in (rgba_dir, rgb_dir, alpha_dir):
        directory.mkdir(parents=True, exist_ok=True)

    exported = []
    for number, (indices, centre_x, centre_y, frame_transparent) in enumerate(frames):
        height, width = indices.shape
        x = -centre_x - left
        y = -centre_y - top
        alpha = (indices != frame_transparent).astype(np.uint8) * 255
        colour = palette[indices]
        canvas_rgba = np.zeros((canvas_size[1], canvas_size[0], 4), dtype=np.uint8)
        canvas_rgba[y:y + height, x:x + width, :3] = colour
        canvas_rgba[y:y + height, x:x + width, 3] = alpha
        canvas_alpha = canvas_rgba[:, :, 3]
        canvas_rgb = fill_transparent(canvas_rgba[:, :, :3], canvas_alpha)
        stem = f"frame_{number:03d}.png"
        rgba_path = rgba_dir / stem
        rgb_path = rgb_dir / stem
        alpha_path = alpha_dir / stem
        save_png_atomic(Image.fromarray(canvas_rgba, "RGBA"), rgba_path)
        save_png_atomic(Image.fromarray(canvas_rgb, "RGB"), rgb_path)
        save_png_atomic(Image.fromarray(canvas_alpha, "L"), alpha_path)
        exported.append({
            "frame": number,
            "file": stem,
            "source_size": [width, height],
            "centre": [centre_x, centre_y],
            "canvas_offset": [x, y],
            "rgb_sha256": sha256_file(rgb_path),
            "alpha_sha256": sha256_file(alpha_path),
            "rgba_sha256": sha256_file(rgba_path),
        })

    geometries = {
        (tuple(frame["source_size"]), tuple(frame["centre"]))
        for frame in exported
    }
    manifest = {
        "schema": SCHEMA,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source": source.as_posix(),
        "source_sha256": sha256_file(source),
        "format": "BAM V1",
        "frame_count": frame_count,
        "source_transparent_index": transparent,
        "aligned_canvas_size": list(canvas_size),
        "anchor_bounds": {"left": left, "top": top, "right": right, "bottom": bottom},
        "geometry_mode": "uniform" if len(geometries) == 1 else "per-frame",
        "frames": exported,
        "cycles": cycle_metadata(data, frame_count),
        "notes": [
            "Use rgb/ as input to an image-only interpolation model.",
            "Keep alpha/ separate; rgba/ is the authoritative source export.",
            "The BAM format does not store frames-per-second; preserve cycle duration at reconstruction.",
        ],
    }
    write_json_atomic(manifest, output / "manifest.json")
    print(f"Exported {frame_count} aligned frames ({canvas_size[0]}x{canvas_size[1]}) to {output}")


if __name__ == "__main__":
    configure_utf8_console()
    main()
