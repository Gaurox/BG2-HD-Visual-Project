"""Build separate cyan x2 overlays and a ground-item comparison sheet."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from bam_export import decode_bam
from build_ground_icon_reboutcx_x2 import (
    ROOT, coverage_alpha, evidence, read_inventory, sha256, soften_silhouette, write_json,
)
from export_bam_frames import read_bam


CYAN = (0, 255, 255)
BATCHES = ROOT / "icons/batches"


def contour_layer(source: Path, body: Image.Image) -> Image.Image:
    frames, palette, transparent = decode_bam(read_bam(source))
    [(indices, _, _, _)] = frames
    cyan_indices = indices == 1
    cyan_pixels = np.all(palette[indices] == CYAN, axis=2)
    if transparent != 0 or tuple(palette[1]) != CYAN or not cyan_indices.any() or not np.array_equal(cyan_indices, cyan_pixels):
        raise ValueError(f"{source.parent.name}: unexpected ground-item outline palette")

    # The body and original outline together define the outer edge.
    silhouette = (indices != transparent).astype(np.uint8) * 255
    outer_x4 = soften_silhouette(coverage_alpha(silhouette))
    outer = Image.fromarray(outer_x4).resize(body.size, Image.Resampling.BOX)
    envelope = np.asarray(outer, dtype=np.float64) / 255
    body_alpha = np.asarray(body.getchannel("A"), dtype=np.float64) / 255

    # Solve source-over for the cyan layer behind the approved body pixels.
    available = 1 - body_alpha
    added_coverage = np.maximum(0, envelope - body_alpha)
    alpha = np.divide(added_coverage, available, out=np.zeros_like(available), where=available > 0)
    layer = Image.new("RGBA", body.size, (*CYAN, 255))
    layer.putalpha(Image.fromarray(np.rint(alpha * 255).astype(np.uint8)))
    return layer


def build_sheet(run, sprites):
    columns = 4
    margin, top = 26, 108
    tile_width, tile_height, divider = 310, 184, 6
    card_width = 2 * tile_width + divider
    step_x, step_y = card_width + 16, 233
    rows = (len(sprites) + columns - 1) // columns
    width = 2 * margin + columns * step_x - 16
    height = top + rows * step_y - 10 + margin
    sheet = Image.new("RGB", (width, height), "#181b20")
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 42)
    body = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 24)
    label = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 23)
    ink, muted = "#f2f4f6", "#c0c8d2"
    draw.text((margin, 14), "Objets au sol ×2 · surbrillance cyan", font=title, fill=ink)
    draw.text((margin, 68), f"{len(sprites)} objets · sans surbrillance à gauche · avec surbrillance à droite · zoom d’affichage ×2",
              font=body, fill=muted)
    for position, (asset, normal, highlighted) in enumerate(sprites):
        row, col = divmod(position, columns)
        left, y = margin + col * step_x, top + row * step_y
        draw.rounded_rectangle((left, y, left + card_width - 1, y + 219), radius=10, fill="#21262d")
        draw.text((left + card_width // 2, y + 16), f"{asset}  {normal.width}×{normal.height}",
                  font=label, fill=ink, anchor="mm")
        for state, sprite in enumerate((normal, highlighted)):
            x = left + state * (tile_width + divider)
            draw.rounded_rectangle((x, y + 34, x + tile_width - 1, y + 34 + tile_height - 1),
                                   radius=8, fill="#282d34")
            size = (sprite.width * 2, sprite.height * 2)
            if size[0] > tile_width or size[1] > tile_height:
                raise ValueError(f"{asset}: sprite exceeds the comparison cell")
            preview = sprite.resize(size, Image.Resampling.NEAREST)
            sheet.paste(preview, (x + (tile_width - preview.width) // 2,
                                  y + 34 + (tile_height - preview.height) // 2), preview)
    path = run / "planche.png"
    sheet.save(path)
    return path


def build(body_run_id, run_id):
    body_run = BATCHES / body_run_id
    body_descriptor = body_run / "run.json"
    parent = json.loads(body_descriptor.read_text(encoding="utf-8"))
    resources = read_inventory()
    asset_ids = [resource["resref"] for resource in resources]
    if set(parent["asset_ids"]) != set(asset_ids) or parent["result"]["status"] != "completed" or not parent["result"]["sealed"]:
        raise ValueError("Body run must be sealed and cover the active ground-item inventory")
    parents_by_path = {row["path"]: row["sha256"] for group in ("inputs", "outputs") for row in parent[group]}

    run = BATCHES / run_id
    run.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    sprites, outputs = [], []
    for resource in resources:
        asset = resource["resref"]
        source = ROOT / resource["extracted_path"]
        body_path = body_run / "assets" / asset / "reboutcx-lisse-x2.png"
        for path in (source, body_path):
            if sha256(path) != parents_by_path[path.relative_to(ROOT).as_posix()]:
                raise ValueError(f"{asset}: evidence differs from the sealed body run")
        with Image.open(body_path) as image:
            body = image.convert("RGBA")
        layer = contour_layer(source, body)
        highlighted = Image.alpha_composite(layer, body)
        original = np.asarray(body)
        result = np.asarray(highlighted)
        opaque = original[..., 3] == 255
        added = (original[..., 3] == 0) & (result[..., 3] > 0)
        if not np.array_equal(original[opaque], result[opaque]) or not np.any(added):
            raise ValueError(f"{asset}: highlight does not preserve the body and add a contour")
        directory = run / "assets" / asset
        directory.mkdir(parents=True)
        for image, name, role in (
            (layer, "contour-cyan-x2.png", "cyan-overlay-x2"),
            (highlighted, "surbrillance-x2.png", "highlight-preview-x2"),
        ):
            path = directory / name
            image.save(path)
            outputs.append(evidence(path, f"{asset}:{role}"))
        sprites.append((asset, body, highlighted))
    outputs.append(evidence(build_sheet(run, sprites), "comparison-sheet"))

    script = Path(__file__).resolve()
    recipe = script.relative_to(ROOT).as_posix()
    write_json(run / "run.json", {
        "$schema": "docs/workspace-run.schema.json", "schema_version": 1,
        "run_id": run_id, "domain": "icons", "asset_ids": asset_ids,
        "pipeline": {"id": "item-ground-cyan-overlay-x2", "recipe_path": recipe,
                     "recipe_sha256": sha256(script), "version": "1"},
        "inputs": [
            evidence(body_descriptor, "reboutcx-x2-body-run"),
            evidence(script.with_name("build_ground_icon_reboutcx_x2.py"), "edge-smoothing-implementation"),
        ],
        "outputs": outputs,
        "provenance": {"created_at_utc": started, "generator": script.name,
                       "command": ["python", "-B", recipe, body_run_id, run_id],
                       "parents": [body_run_id]},
        "result": {"status": "completed", "sealed": True,
                   "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                   "notes": "Calques RGBA cyan x2 issus de l'index 1 des BAM et aperçus de surbrillance derrière les corps approuvés."},
    })
    print(f"{len(asset_ids)} cyan overlays and comparisons: {run.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("body_run_id")
    parser.add_argument("run_id")
    args = parser.parse_args()
    for name in (args.body_run_id, args.run_id):
        if Path(name).name != name or not name.startswith("item-ground-"):
            parser.error("Provide item-ground-* directory names")
    build(args.body_run_id, args.run_id)


if __name__ == "__main__":
    main()
