#!/usr/bin/env python3
"""Build a lossless xBR-vs-ReboutCX x4 comparison for one RGBA animation frame."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from reboutcx_batch import infer_x4_box_x2, load_model  # noqa: E402
from run_animation_small_subject_xbr2 import nearest_x2, run_xbr2x  # noqa: E402


def filled_rgb(rgba: np.ndarray) -> np.ndarray:
    opaque = rgba[:, :, 3] > 0
    if not np.any(opaque):
        return np.zeros((*opaque.shape, 3), dtype=np.uint8)
    nearest = distance_transform_edt(~opaque, return_distances=False, return_indices=True)
    return np.asarray(rgba[:, :, :3][tuple(nearest)], dtype=np.uint8)


def checkerboard(width: int, height: int, cell: int = 16) -> Image.Image:
    yy, xx = np.indices((height, width))
    value = np.where(((xx // cell) + (yy // cell)) % 2 == 0, 54, 86).astype(np.uint8)
    return Image.fromarray(np.dstack((value, value, value, np.full_like(value, 255))), "RGBA")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--scalepix", type=Path, required=True)
    parser.add_argument("--zoom", type=int, default=2)
    args = parser.parse_args()

    source = np.asarray(Image.open(args.source).convert("RGBA"), dtype=np.uint8)
    xbr_x2 = run_xbr2x([source], args.scalepix, "node", False)[0]
    xbr_x4 = nearest_x2(xbr_x2)

    descriptor, _versions = load_model(args.model, device="cuda:0", fp16=True)
    rebout_rgb_x4, _rebout_rgb_x2 = infer_x4_box_x2(
        descriptor, filled_rgb(source), fp16=True
    )
    alpha_x4 = source[:, :, 3].repeat(4, axis=0).repeat(4, axis=1)
    rebout_x4 = np.dstack((rebout_rgb_x4, alpha_x4))

    args.output_dir.mkdir(parents=True, exist_ok=False)
    Image.fromarray(xbr_x4, "RGBA").save(args.output_dir / "xbr2x-nearest2-x4.png")
    Image.fromarray(rebout_x4, "RGBA").save(args.output_dir / "reboutcx-x4.png")

    height, width = xbr_x4.shape[:2]
    zoom = args.zoom
    panel_w, panel_h = width * zoom, height * zoom
    margin, header = 24, 42
    preview = Image.new("RGBA", (panel_w * 2 + margin * 3, panel_h + header + margin), (24, 26, 30, 255))
    draw = ImageDraw.Draw(preview)
    for column, (label, pixels) in enumerate((("xBR 2x + nearest 2x", xbr_x4), ("ReboutCX x4", rebout_x4))):
        x = margin + column * (panel_w + margin)
        draw.text((x, 14), label, fill=(255, 255, 255, 255))
        background = checkerboard(width, height)
        background.alpha_composite(Image.fromarray(pixels, "RGBA"))
        enlarged = background.resize((panel_w, panel_h), Image.Resampling.NEAREST)
        preview.alpha_composite(enlarged, (x, header))
    preview.convert("RGB").save(args.output_dir / "comparison-xbr-reboutcx-lossless.png", compress_level=9)
    print(args.output_dir / "comparison-xbr-reboutcx-lossless.png")


if __name__ == "__main__":
    main()
