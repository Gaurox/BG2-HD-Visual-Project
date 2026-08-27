"""Prepare a derived RGB PNG for BC1/DXT1 texture encoding.

BC1 stores one four-colour palette per 4x4 block. Fine chroma variation from
an AI upscaler can therefore turn into coloured block noise after encoding.
This tool applies a very small Gaussian blur to Cb/Cr only: luma, geometry and
the original source PNG are left unchanged.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None


def edge_smooth_luma(channel: Image.Image, sigma: float) -> Image.Image:
    """One small bilateral-like pass on luma, processed in row strips.

    Neighbours across a strong luminance edge receive almost no weight, while
    small pixel-to-pixel fluctuations inside a material are averaged. This is
    deliberately limited to a 3x3 neighbourhood so grates and tile seams stay
    sharp at the x2 pixel scale.
    """
    if sigma <= 0:
        return channel
    source = np.asarray(channel, dtype=np.float32)
    result = np.empty_like(source)
    padded = np.pad(source, ((1, 1), (1, 1)), mode="edge")
    neighbours = (
        (-1, -1, 0.55), (-1, 0, 0.8), (-1, 1, 0.55),
        (0, -1, 0.8),                 (0, 1, 0.8),
        (1, -1, 0.55),  (1, 0, 0.8),  (1, 1, 0.55),
    )
    denom = 2.0 * sigma * sigma
    for top in range(0, source.shape[0], 256):
        bottom = min(top + 256, source.shape[0])
        center = source[top:bottom]
        total = center.copy()
        weights = np.ones_like(center)
        for dy, dx, spatial_weight in neighbours:
            neighbour = padded[top + 1 + dy:bottom + 1 + dy, 1 + dx:1 + dx + source.shape[1]]
            weight = spatial_weight * np.exp(-((neighbour - center) ** 2) / denom)
            total += weight * neighbour
            weights += weight
        result[top:bottom] = total / weights
    return Image.fromarray(np.rint(result).astype(np.uint8), mode="L")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--radius",
        type=float,
        default=1.0,
        help="Gaussian radius applied to chroma channels only (default: 1.0)",
    )
    parser.add_argument(
        "--luma-edge-sigma",
        type=float,
        default=0.0,
        help="edge-aware luma smoothing strength; 0 disables it (default: 0)",
    )
    args = parser.parse_args()
    if not args.source.is_file():
        parser.error(f"source not found: {args.source}")
    if args.radius <= 0 or args.radius > 4:
        parser.error("--radius must be in (0, 4]")
    if args.luma_edge_sigma < 0 or args.luma_edge_sigma > 40:
        parser.error("--luma-edge-sigma must be in [0, 40]")
    if args.output.exists():
        parser.error(f"output already exists: {args.output}")

    with Image.open(args.source) as source:
        rgb = source.convert("RGB")
        y, cb, cr = rgb.convert("YCbCr").split()
        y = edge_smooth_luma(y, args.luma_edge_sigma)
        cb = cb.filter(ImageFilter.GaussianBlur(args.radius))
        cr = cr.filter(ImageFilter.GaussianBlur(args.radius))
        result = Image.merge("YCbCr", (y, cb, cr)).convert("RGB")
        args.output.parent.mkdir(parents=True, exist_ok=True)
        result.save(args.output, format="PNG", compress_level=4)

    print(
        f"wrote {args.output} ({result.width}x{result.height}, chroma radius {args.radius}, "
        f"luma edge sigma {args.luma_edge_sigma})"
    )


if __name__ == "__main__":
    main()
