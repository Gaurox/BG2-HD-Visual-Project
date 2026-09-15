#!/usr/bin/env python3
"""Compare xBR2x+nearest2x with two successive xBR2x passes on one RGBA frame."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from run_animation_small_subject_xbr2 import nearest_x2, run_xbr2x  # noqa: E402


def checkerboard(width: int, height: int, cell: int = 16) -> Image.Image:
    yy, xx = np.indices((height, width))
    value = np.where(((xx // cell) + (yy // cell)) % 2 == 0, 54, 86).astype(np.uint8)
    rgba = np.dstack((value, value, value, np.full_like(value, 255)))
    return Image.fromarray(rgba, "RGBA")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--scalepix", type=Path, required=True)
    parser.add_argument("--zoom", type=int, default=2)
    args = parser.parse_args()

    source = np.asarray(Image.open(args.source).convert("RGBA"), dtype=np.uint8)
    xbr_x2 = run_xbr2x([source], args.scalepix, "node", False)[0]
    reference_x4 = nearest_x2(xbr_x2)
    xbr_x4 = run_xbr2x([xbr_x2], args.scalepix, "node", False)[0]

    args.output_dir.mkdir(parents=True, exist_ok=False)
    Image.fromarray(xbr_x4, "RGBA").save(args.output_dir / "xbr2x-twice-x4.png")

    height, width = xbr_x4.shape[:2]
    zoom = args.zoom
    panel_w, panel_h = width * zoom, height * zoom
    margin, header = 24, 42
    preview = Image.new("RGBA", (panel_w * 2 + margin * 3, panel_h + header + margin), (24, 26, 30, 255))
    draw = ImageDraw.Draw(preview)
    panels = (
        ("xBR2x + nearest2x", reference_x4),
        ("xBR2x + xBR2x (x4)", xbr_x4),
    )
    for column, (label, pixels) in enumerate(panels):
        x = margin + column * (panel_w + margin)
        draw.text((x, 14), label, fill=(255, 255, 255, 255))
        background = checkerboard(width, height)
        background.alpha_composite(Image.fromarray(pixels, "RGBA"))
        enlarged = background.resize((panel_w, panel_h), Image.Resampling.NEAREST)
        preview.alpha_composite(enlarged, (x, header))
    preview.convert("RGB").save(args.output_dir / "comparison-xbr4-lossless.png", compress_level=9)
    print(args.output_dir / "comparison-xbr4-lossless.png")


if __name__ == "__main__":
    main()
