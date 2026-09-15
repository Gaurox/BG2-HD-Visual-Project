#!/usr/bin/env python3
"""Render all frames of one runtime-pack resource into a lossless PNG contact sheet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw


def checkerboard(size: tuple[int, int], cell: int = 16) -> Image.Image:
    width, height = size
    yy, xx = np.indices((height, width))
    value = np.where(((xx // cell) + (yy // cell)) % 2 == 0, 54, 86).astype(np.uint8)
    return Image.fromarray(np.dstack((value, value, value, np.full_like(value, 255))), "RGBA")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=5)
    args = parser.parse_args()

    manifest = json.loads((args.pack / "manifest.json").read_text(encoding="utf-8"))
    resource = next(item for item in manifest["resources"] if item["resref"] == args.resref.upper())
    by_index = {int(item["frame"]): item for item in resource["frames"]}
    timeline = resource.get("cycles", [{}])[0].get("timeline_frame_indices")
    frames = (
        [by_index[int(index)] for index in timeline]
        if timeline
        else [by_index[index] for index in sorted(by_index)]
    )
    scale = int(manifest["scale"])
    left = min(-int(item["centre_x1"][0]) * scale for item in frames)
    top = min(-int(item["centre_x1"][1]) * scale for item in frames)
    right = max(-int(item["centre_x1"][0]) * scale + int(item["physical_size_x4"][0]) for item in frames)
    bottom = max(-int(item["centre_x1"][1]) * scale + int(item["physical_size_x4"][1]) for item in frames)
    cell_w, cell_h = right - left, bottom - top
    header, gap, margin = 26, 12, 18
    columns = min(args.columns, len(frames))
    rows = (len(frames) + columns - 1) // columns
    sheet_w = margin * 2 + columns * cell_w + (columns - 1) * gap
    sheet_h = margin * 2 + rows * (header + cell_h) + (rows - 1) * gap
    sheet = Image.new("RGBA", (sheet_w, sheet_h), (24, 26, 30, 255))
    draw = ImageDraw.Draw(sheet)

    for position, item in enumerate(frames):
        column, row = position % columns, position // columns
        origin_x = margin + column * (cell_w + gap)
        origin_y = margin + row * (header + cell_h + gap)
        kind = "interpolee" if item.get("generated_by") else "native"
        draw.text((origin_x + 3, origin_y + 7), f"phase {position:02d} / frame {item['frame']:03d} / {kind}", fill="white")
        width, height = (int(value) for value in item["physical_size_x4"])
        raw = np.frombuffer((args.pack / item["asset"]).read_bytes(), dtype=np.uint8).reshape(height, width, 4)
        panel = checkerboard((cell_w, cell_h))
        x = -int(item["centre_x1"][0]) * scale - left
        y = -int(item["centre_x1"][1]) * scale - top
        panel.alpha_composite(Image.fromarray(raw, "RGBA"), (x, y))
        sheet.alpha_composite(panel, (origin_x, origin_y + header))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.convert("RGB").save(args.output, compress_level=9)
    print(args.output)


if __name__ == "__main__":
    main()
