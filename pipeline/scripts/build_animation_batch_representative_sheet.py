#!/usr/bin/env python3
"""Render one inventory-selected frame per resource from a runtime pack."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import run_animation_upscale_30fps_v2 as v2


def checkerboard(width: int, height: int, cell: int = 16) -> np.ndarray:
    yy, xx = np.indices((height, width))
    value = np.where(((xx // cell) + (yy // cell)) % 2 == 0, 50, 78).astype(np.uint8)
    return np.dstack((value, value, value))


def composite(background: np.ndarray, rgba: np.ndarray, premultiplied: bool) -> np.ndarray:
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    rgb = rgba[:, :, :3].astype(np.float32)
    foreground = rgb if premultiplied else rgb * alpha
    return np.clip(np.rint(foreground + background * (1.0 - alpha)), 0, 255).astype(np.uint8)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pack", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--columns", type=int, default=4)
    parser.add_argument("--resref", action="append", default=[])
    parser.add_argument("--premultiplied-resref", action="append", default=[])
    args = parser.parse_args()

    pack = args.pack.resolve()
    _manifest, resources = v2.validate_v2_pack(pack)
    by_resref = {v2.normalise_resref(item["resref"]): item for item in resources}
    with args.inventory.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if args.resref:
        selected = {v2.normalise_resref(value) for value in args.resref}
        rows = [row for row in rows if v2.normalise_resref(row["resref"]) in selected]
        v2.require({v2.normalise_resref(row["resref"]) for row in rows} == selected,
                   "resref demandé absent de l'inventaire")
    v2.require(rows, "inventaire vide")
    premultiplied = {v2.normalise_resref(value) for value in args.premultiplied_resref}

    card_width, card_height = 420, 360
    image_width, image_height = 396, 306
    columns = max(1, args.columns)
    lines = (len(rows) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * card_width, lines * card_height), (18, 20, 24))
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()

    for position, row in enumerate(rows):
        resref = v2.normalise_resref(row["resref"])
        v2.require(resref in by_resref, f"{resref}: absent du pack")
        resource = by_resref[resref]
        frame_index = int(row["representative_frame_index"])
        frames = {int(item["frame"]): item for item in resource["frames"]}
        v2.require(frame_index in frames, f"{resref}: frame {frame_index} absente")
        frame = frames[frame_index]
        width, height = (int(value) for value in frame["physical_size_x4"])
        payload = (pack / str(frame["asset"])).read_bytes()
        v2.require(len(payload) == width * height * 4, f"{resref}: payload RGBA invalide")
        rgba = np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 4)
        rgb = composite(checkerboard(width, height), rgba, resref in premultiplied)
        preview = Image.fromarray(rgb, "RGB")
        preview.thumbnail((image_width, image_height), Image.Resampling.LANCZOS)

        column, line = position % columns, position // columns
        x0, y0 = column * card_width, line * card_height
        px = x0 + (card_width - preview.width) // 2
        py = y0 + 34 + (image_height - preview.height) // 2
        sheet.paste(preview, (px, py))
        draw.rectangle((x0, y0, x0 + card_width - 1, y0 + card_height - 1), outline=(70, 75, 84))
        draw.text((x0 + 12, y0 + 10), f"{resref}  frame {frame_index:03d}", fill=(245, 245, 245), font=font)
        draw.text((x0 + 12, y0 + 342), f"{width}x{height} px (x4)", fill=(170, 178, 190), font=font)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output, optimize=True)
    print(args.output.resolve())


if __name__ == "__main__":
    main()
