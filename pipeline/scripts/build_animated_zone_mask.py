#!/usr/bin/env python3
"""Build a grayscale "animated zone" mask for an opaque rectangular area animation.

Some BAM animations are a fully opaque rectangle that repaints floor, furniture and walls
around a small moving part (a hearth fire and its flickering light).  At x4 the upscaled
rectangle never matches the upscaled map exactly, so its whole outline shows in game.  This
mask keeps the animation only where the light really moves and fades to the map elsewhere.

Seed = low-frequency temporal luminance deviation of the x1 frames above a threshold (dithered
transparency holes are median-filled first), closed, holes filled, small islands dropped,
grown, feathered, upscaled to the x4 frame size, then forced to zero at the canvas edges.
The PNG is meant for ``derive_animation_visual_treatment.py --alpha-mask`` and may be
retouched by hand before use (white keeps the animation, black shows the map).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import (
    binary_closing, binary_dilation, binary_fill_holes, distance_transform_edt,
    gaussian_filter, label, median_filter,
)

LUMA = np.array([0.299, 0.587, 0.114], dtype=np.float32)


def smoothstep(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def animated_zone_mask(
    frames: np.ndarray, size_x4: tuple[int, int], std_threshold: float,
    min_component_x1: int, grow_x1: int, feather_x1: float, edge_fade_x4: float,
) -> tuple[np.ndarray, dict[str, float]]:
    """Return an 8-bit mask of ``size_x4`` (width, height) and its statistics."""
    luma = frames[..., :3].astype(np.float32) @ LUMA
    visible = frames[..., 3] > 127
    filled = np.stack([
        np.where(opaque, value, median_filter(value, 3)) for value, opaque in zip(luma, visible)
    ])
    deviation = np.stack([gaussian_filter(value, 2.0) for value in filled]).std(axis=0)
    seed = binary_fill_holes(binary_closing(deviation > std_threshold, iterations=2))
    labels, count = label(seed)
    if count:
        sizes = np.bincount(labels.ravel())
        sizes[0] = 0
        seed = np.isin(labels, np.nonzero(sizes > min_component_x1)[0])
    if not seed.any():
        raise ValueError("aucune zone animée au-dessus du seuil")
    soft = gaussian_filter(binary_dilation(seed, iterations=grow_x1).astype(np.float32), feather_x1)
    width, height = size_x4
    upscaled = np.asarray(Image.fromarray(soft, "F").resize((width, height), Image.BICUBIC))
    inside = np.pad(np.ones((height, width), dtype=bool), 1, constant_values=False)
    edge = smoothstep((distance_transform_edt(inside)[1:-1, 1:-1] - 1.0) / edge_fade_x4)
    mask = np.clip(np.rint(np.clip(upscaled, 0.0, 1.0) * edge * 255.0), 0, 255).astype(np.uint8)
    return mask, {
        "seed_px_x1": int(seed.sum()),
        "canvas_px_x1": int(seed.size),
        "opaque_share_x4": round(float((mask >= 250).mean()), 4),
        "visible_share_x4": round(float((mask >= 128).mean()), 4),
    }


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames-x1", type=Path, required=True,
                        help="dossier rgba/ des frames x1 alignées (export_bam_frames.py)")
    parser.add_argument("--size-x4", type=int, nargs=2, required=True, metavar=("W", "H"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--std-threshold", type=float, default=1.5)
    parser.add_argument("--min-component-x1", type=int, default=40)
    parser.add_argument("--grow-x1", type=int, default=4)
    parser.add_argument("--feather-x1", type=float, default=3.0)
    parser.add_argument("--edge-fade-x4", type=float, default=24.0)
    args = parser.parse_args()
    paths = sorted(args.frames_x1.glob("frame_*.png"))
    if not paths:
        raise SystemExit(f"aucune frame_*.png dans {args.frames_x1}")
    frames = np.stack([np.asarray(Image.open(path).convert("RGBA")) for path in paths])
    width, height = args.size_x4
    if (frames.shape[2] * 4, frames.shape[1] * 4) != (width, height):
        raise SystemExit("taille x4 incohérente avec les frames x1 (x4 exact attendu)")
    mask, stats = animated_zone_mask(
        frames, (width, height), args.std_threshold, args.min_component_x1,
        args.grow_x1, args.feather_x1, args.edge_fade_x4,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.dstack([mask] * 3), "RGB").save(args.output)
    report = {
        "schema": "bg2-upscale-animated-zone-mask-v1",
        "frames_x1": str(args.frames_x1), "frame_count": len(paths),
        "size_x4": [width, height],
        "parameters": {
            "std_threshold": args.std_threshold, "min_component_x1": args.min_component_x1,
            "grow_x1": args.grow_x1, "feather_x1": args.feather_x1,
            "edge_fade_x4": args.edge_fade_x4,
        },
        "stats": stats,
    }
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
