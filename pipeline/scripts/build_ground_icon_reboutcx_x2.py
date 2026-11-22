"""Produce the ground-item ReboutCX x2 batch and its contact sheet."""

import argparse
import csv
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from workspace_paths import resolve_path_reference

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "icons/index"
SCALE = 4
SAMPLES = 16
MATTE = (74, 74, 74)


def sha256(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def evidence(path, role):
    return {"role": role, "path": path.relative_to(ROOT).as_posix(),
            "sha256": sha256(path), "bytes": path.stat().st_size}


def read_inventory():
    with (INDEX / "families.csv").open(newline="", encoding="utf-8-sig") as stream:
        keys = {row["asset_key"] for row in csv.DictReader(stream) if row["family"] == "item-ground"}
    with (INDEX / "resources.csv").open(newline="", encoding="utf-8-sig") as stream:
        resources = [row for row in csv.DictReader(stream) if row["asset_key"] in keys]
    if len(resources) != len(keys) or not resources:
        raise ValueError("Incomplete ground-item BAM inventory")
    return resources


def prepare(run, resources):
    from bam_export import decode_bam, native_palette_alpha
    from export_bam_frames import read_bam

    geometry = {}
    inputs = []
    for resource in resources:
        asset = resource["resref"]
        source = ROOT / resource["extracted_path"]
        record = evidence(source, f"{asset}:source-bam")
        if record["sha256"].upper() != resource["source_sha256"].upper():
            raise ValueError(f"{asset}: source BAM hash differs from inventory")
        inputs.append(record)

        data = read_bam(source)
        frames, palette, transparent = decode_bam(data)
        [(indices, centre_x, centre_y, _)] = frames
        if transparent != 0 or tuple(palette[1]) != (0, 255, 255):
            raise ValueError(f"{asset}: unexpected transparent or outline palette index")
        cyan = np.all(palette[indices] == (0, 255, 255), axis=2)
        if not np.array_equal(cyan, indices == 1) or not cyan.any():
            raise ValueError(f"{asset}: unexpected cyan pixel indices")
        alpha_palette = native_palette_alpha(data, transparent)
        alpha_palette[1] = 0
        alpha = alpha_palette[indices]
        if set(np.unique(alpha)) != {0, 255}:
            raise ValueError(f"{asset}: expected a binary body mask")
        sprite = Image.fromarray(np.dstack((palette[indices], alpha)), "RGBA")

        width, height = sprite.size
        canvas = tuple((length + 63) // 64 * 64 for length in sprite.size)
        left, top = (canvas[0] - width) // 2, (canvas[1] - height) // 2
        image = Image.new("RGB", canvas, MATTE)
        image.paste(sprite, (left, top), sprite)
        work = run / "work" / asset
        work.mkdir(parents=True)
        image.save(work / "input.png")
        sprite.getchannel("A").save(work / "alpha-x1.png")
        geometry[asset] = {
            "native_size": [width, height], "native_center": [centre_x, centre_y],
            "x2_size": [width * 2, height * 2], "x2_center": [centre_x * 2, centre_y * 2],
            "x4_crop": [p * SCALE for p in (left, top, left + width, top + height)],
        }
    return geometry, inputs


def infer(run):
    from reboutcx_batch import infer_x4_box_x2, load_model

    model = resolve_path_reference("config://reboutcx_model", required=True)
    descriptor, versions = load_model(model, device="cuda:0", fp16=True)
    for path in sorted((run / "work").glob("*/input.png")):
        rgb = np.asarray(Image.open(path).convert("RGB"))
        result, _ = infer_x4_box_x2(descriptor, rgb, fp16=True)
        Image.fromarray(result, "RGB").save(path.with_name("rgb-x4.png"))
    (run / "model.json").write_text(json.dumps({
        "model": model.name, "sha256": sha256(model), "precision": "fp16",
        "versions": versions,
    }, indent=2) + "\n", encoding="utf-8")


def coverage_alpha(source_alpha):
    from skimage.measure import find_contours, points_in_poly

    height, width = source_alpha.shape
    sample_scale = SCALE * SAMPLES
    y, x = np.indices((height * sample_scale, width * sample_scale))
    points = (np.column_stack((y.ravel(), x.ravel())) + 0.5) / sample_scale
    inside = np.zeros(len(points), dtype=bool)
    padded = np.pad(source_alpha != 0, 1)
    for polygon in find_contours(padded, 0.5, fully_connected="high"):
        inside ^= points_in_poly(points, polygon - 0.5)
    coverage = inside.reshape(height * SCALE, SAMPLES, width * SCALE, SAMPLES)
    return np.rint(coverage.mean(axis=(1, 3)) * 255).astype(np.uint8)


def soften_silhouette(mask):
    from scipy.ndimage import gaussian_filter

    coverage = np.asarray(mask, dtype=np.float64) / 255
    field = gaussian_filter(coverage, sigma=0.62 * SCALE, mode="constant")
    half_width = 0.19
    target_area = coverage.sum()
    lower, upper = 0.24, 0.64
    for _ in range(24):
        threshold = (lower + upper) / 2
        t = np.clip((field - threshold + half_width) / (2 * half_width), 0, 1)
        alpha = t * t * (3 - 2 * t)
        if alpha.sum() > target_area:
            lower = threshold
        else:
            upper = threshold
    return np.rint(alpha * 255).astype(np.uint8)


def soften_colors(rgb_x4, alpha_nearest, alpha_soft):
    from scipy.ndimage import distance_transform_edt, gaussian_filter

    opaque = alpha_nearest == 255
    distance = distance_transform_edt(np.pad(opaque, 1))[1:-1, 1:-1]
    weight = opaque * np.clip(distance - 0.75, 0.0, 2.0)
    rgb = np.asarray(rgb_x4, dtype=np.float64)
    denominator = gaussian_filter(weight, sigma=0.5 * SCALE, mode="constant")
    numerator = gaussian_filter(rgb * weight[..., None],
                                sigma=(0.5 * SCALE, 0.5 * SCALE, 0), mode="constant")
    if np.any(denominator[alpha_soft > 0] <= 0):
        raise ValueError("Missing color support under visible alpha")
    extended = np.divide(numerator, denominator[..., None],
                         out=rgb.copy(), where=denominator[..., None] > 0)
    blend = np.clip((SCALE - distance) / (SCALE - 1), 0, 1)[..., None]
    colors = np.rint(rgb * (1 - blend) + extended * blend).astype(np.uint8)
    return np.dstack((colors, alpha_soft))


def reduce_x4_to_x2(rgba):
    height, width, _ = rgba.shape
    blocks = rgba.astype(np.float64).reshape(height // 2, 2, width // 2, 2, 4)
    alpha = blocks[..., 3]
    alpha_sum = alpha.sum(axis=(1, 3))
    rgb_sum = (blocks[..., :3] * alpha[..., None]).sum(axis=(1, 3))
    rgb = np.divide(rgb_sum, alpha_sum[..., None], out=np.zeros_like(rgb_sum),
                    where=alpha_sum[..., None] > 0)
    return np.rint(np.dstack((rgb, alpha_sum / 4))).astype(np.uint8)


def build_sprites(run, geometry):
    outputs = []
    for asset, layout in geometry.items():
        work = run / "work" / asset
        mask = Image.open(work / "alpha-x1.png")
        rgb = Image.open(work / "rgb-x4.png").crop(tuple(layout["x4_crop"]))
        alpha_nearest = np.asarray(mask.resize(rgb.size, Image.Resampling.NEAREST))
        alpha_soft = soften_silhouette(coverage_alpha(np.asarray(mask)))
        rgba = reduce_x4_to_x2(soften_colors(rgb, alpha_nearest, alpha_soft))
        area = alpha_soft.sum(dtype=float)
        if area <= 0 or abs(rgba[..., 3].sum(dtype=float) * 4 / area - 1) >= 0.002:
            raise ValueError(f"{asset}: x2 alpha coverage differs from x4")
        image = Image.fromarray(rgba, "RGBA")
        if list(image.size) != layout["x2_size"]:
            raise ValueError(f"{asset}: incorrect x2 geometry")
        output = run / "assets" / asset / "reboutcx-lisse-x2.png"
        output.parent.mkdir(parents=True)
        image.save(output)
        outputs.append(evidence(output, f"{asset}:reboutcx-x2-rgba"))
    return outputs


def build_sheet(run, geometry):
    columns = 8
    cell_w, cell_h, step_x, step_y = 320, 212, 332, 224
    margin, top = 26, 111
    rows = (len(geometry) + columns - 1) // columns
    sheet = Image.new("RGB", (margin * 2 + columns * step_x - 12,
                              top + rows * step_y - 12 + margin), "#181b20")
    draw = ImageDraw.Draw(sheet)
    title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 42)
    body = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 23)
    label = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 23)
    draw.text((margin, 17), "Objets au sol · ReboutCX ×2", font=title, fill="#f2f4f6")
    draw.text((margin, 72), f"{len(geometry)} sprites · lissage renforcé · sans contour cyan · zoom d’affichage ×2",
              font=body, fill="#c0c8d2")
    for number, (asset, layout) in enumerate(geometry.items()):
        row, col = divmod(number, columns)
        x, y = margin + col * step_x, top + row * step_y
        draw.rounded_rectangle((x, y, x + cell_w - 1, y + cell_h - 1), radius=10, fill="#272d34")
        sprite = Image.open(run / "assets" / asset / "reboutcx-lisse-x2.png").convert("RGBA")
        width, height = layout["x2_size"]
        preview = sprite.resize((width * 2, height * 2), Image.Resampling.NEAREST)
        sheet.paste(preview, (x + (cell_w - preview.width) // 2, y + (182 - preview.height) // 2), preview)
        draw.text((x + cell_w // 2, y + 196), f"{asset}  {width}×{height}",
                  font=label, fill="#e1e6eb", anchor="mm")
    planche = run / "planche.png"
    sheet.save(planche)
    return planche


def write_json(path, payload):
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def build(run_id):
    run = ROOT / "icons/batches" / run_id
    run.mkdir(parents=True)
    started = datetime.now(timezone.utc).isoformat()
    geometry, inputs = prepare(run, read_inventory())
    write_json(run / "geometry.json", geometry)
    python = resolve_path_reference("config://chainner_python", required=True)
    subprocess.run([str(python), "-B", str(Path(__file__).resolve()), run_id, "--infer"],
                   cwd=ROOT, check=True)
    outputs = build_sprites(run, geometry)
    outputs.extend(evidence(run / name, role) for name, role in (
        ("geometry.json", "geometry"), ("model.json", "model-provenance")))
    outputs.append(evidence(build_sheet(run, geometry), "comparison-sheet"))

    script = Path(__file__).resolve()
    write_json(run / "run.json", {
        "$schema": "docs/workspace-run.schema.json", "schema_version": 1,
        "run_id": run_id, "domain": "icons", "asset_ids": list(geometry),
        "pipeline": {"id": "item-ground-reboutcx-x2-edge-smooth",
                     "recipe_path": script.relative_to(ROOT).as_posix(),
                     "recipe_sha256": sha256(script), "version": "1"},
        "inputs": inputs, "outputs": outputs,
        "provenance": {"created_at_utc": started, "generator": script.name,
                       "command": ["python", "-B", script.relative_to(ROOT).as_posix(), run_id]},
        "result": {"status": "completed", "sealed": True,
                   "completed_at_utc": datetime.now(timezone.utc).isoformat(),
                   "notes": "ReboutCX via RGB x4, contour cyan masqué, lissage renforcé, réduction x2 en alpha prémultiplié."},
    })
    print(f"{len(geometry)} assets: {run.relative_to(ROOT)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_id")
    parser.add_argument("--infer", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if Path(args.run_id).name != args.run_id or not args.run_id.startswith("item-ground-"):
        parser.error("Provide an item-ground-* directory name")
    if args.infer:
        infer(ROOT / "icons/batches" / args.run_id)
    else:
        build(args.run_id)


if __name__ == "__main__":
    main()
