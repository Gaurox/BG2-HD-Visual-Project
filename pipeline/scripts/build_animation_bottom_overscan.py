"""Build a geometry-changing bottom overscan prototype for one uniform BAM.

This is deliberately not an alpha correction: the logical frame height grows so
the replacement can draw below a source canvas that clipped the intended tip.
The existing visible pixels are preserved; only newly exposed boundary pixels
and the appended rows are synthesised from vertically retimed source rows.  A
derived BAM with transparent padding supplies matching native draw geometry.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))

import animation_paths  # noqa: E402
from bam_export import decode_bam  # noqa: E402
from export_bam_frames import cycle_metadata  # noqa: E402
import run_animation_upscale_30fps_v2 as runtime  # noqa: E402


SCHEMA = "bg2-upscale-animation-bottom-overscan-prototype-v1"
ALPHA_SCHEMA = "bg2-upscale-animation-alpha-feather-test-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_bam(path: Path) -> bytes:
    payload = path.read_bytes()
    if payload[:4] == b"BAMC":
        payload = zlib.decompress(payload[12:])
    require(payload[:8] == b"BAM V1  ", f"BAM V1 attendu : {path}")
    return payload


def pad_bam_bottom(source: bytes, rows: int) -> bytes:
    """Rebuild a BAM V1 with transparent rows appended to every frame."""
    require(rows > 0, "le padding BAM doit être positif")
    frame_count, cycle_count, transparent = struct.unpack_from("<HBB", source, 8)
    off_frames, off_palette, off_lookup = struct.unpack_from("<III", source, 0x0C)
    frames, _palette_rgb, decoded_transparent = decode_bam(source)
    require(decoded_transparent == transparent and len(frames) == frame_count,
            "décodage BAM incohérent")

    cycle_offset = off_frames + frame_count * 12
    cycles: list[tuple[int, int]] = []
    lookup_count = 0
    for index in range(cycle_count):
        count, start = struct.unpack_from("<HH", source, cycle_offset + index * 4)
        cycles.append((count, start))
        lookup_count = max(lookup_count, start + count)
    lookup = source[off_lookup:off_lookup + lookup_count * 2]
    palette = source[off_palette:off_palette + 256 * 4]
    require(len(lookup) == lookup_count * 2 and len(palette) == 256 * 4,
            "tables BAM tronquées")

    new_off_frames = 24
    new_cycle_offset = new_off_frames + frame_count * 12
    new_off_palette = new_cycle_offset + cycle_count * 4
    new_off_lookup = new_off_palette + 256 * 4
    data_offset = new_off_lookup + len(lookup)
    header = struct.pack(
        "<8sHBBIII", b"BAM V1  ", frame_count, cycle_count, transparent,
        new_off_frames, new_off_palette, new_off_lookup,
    )
    frame_table = bytearray()
    payloads: list[bytes] = []
    cursor = data_offset
    for indices, centre_x, centre_y, frame_transparent in frames:
        require(frame_transparent == transparent, "index transparent divergent")
        height, width = indices.shape
        new_height = height + rows
        require(width <= 0xFFFF and new_height <= 0xFFFF, "géométrie BAM hors limites")
        padded = np.full((new_height, width), transparent, dtype=np.uint8)
        padded[:height] = indices
        raw = padded.tobytes(order="C")
        require(cursor < 0x80000000, "offset BAM hors limites")
        frame_table.extend(struct.pack(
            "<HHhhI", width, new_height, centre_x, centre_y, cursor | 0x80000000
        ))
        payloads.append(raw)
        cursor += len(raw)
    cycle_table = b"".join(struct.pack("<HH", count, start) for count, start in cycles)
    return b"".join([header, bytes(frame_table), cycle_table, palette, lookup, *payloads])


def smoothstep(value: np.ndarray) -> np.ndarray:
    value = np.clip(value, 0.0, 1.0)
    return value * value * (3.0 - 2.0 * value)


def row_bounds(alpha: np.ndarray, start: int) -> tuple[np.ndarray, np.ndarray]:
    left = np.full(alpha.shape[0], np.nan, dtype=np.float32)
    right = np.full(alpha.shape[0], np.nan, dtype=np.float32)
    for y in range(start, alpha.shape[0]):
        opaque = np.flatnonzero(alpha[y] > 127)
        if opaque.size:
            left[y] = float(opaque[0])
            right[y] = float(opaque[-1])
    valid = np.flatnonzero(np.isfinite(left))
    require(valid.size >= 2 and valid[0] <= start and valid[-1] == alpha.shape[0] - 1,
            "la silhouette basse ne traverse pas toute la région demandée")
    rows = np.arange(alpha.shape[0], dtype=np.float32)
    left = np.interp(rows, valid.astype(np.float32), left[valid]).astype(np.float32)
    right = np.interp(rows, valid.astype(np.float32), right[valid]).astype(np.float32)
    return left, right


def extend_bottom(
    pixels: np.ndarray,
    overscan: int,
    retime_start: int,
    feather: float,
    texture_source_offset: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Extend only the lower silhouette while retaining all existing visible pixels."""
    height, width, channels = pixels.shape
    require(channels == 4 and overscan > 0, "buffer RGBA/overscan invalide")
    require(0 <= retime_start < height - 1, "début de retiming hors frame")
    require(feather > 0.0, "feather doit être positif")
    require(texture_source_offset >= 0, "décalage de texture négatif")
    alpha = pixels[:, :, 3]
    left, right = row_bounds(alpha, retime_start)
    output = np.zeros((height + overscan, width, 4), dtype=np.uint8)
    output[:height] = pixels
    target_alpha = np.zeros((height + overscan, width), dtype=np.uint8)
    target_rgb = np.zeros((height + overscan, width, 3), dtype=np.uint8)
    xx = np.arange(width, dtype=np.float32)
    source_span = float(height - 1 - retime_start)
    output_span = float(height + overscan - 1 - retime_start)
    raised = 0
    added = 0
    for y in range(retime_start, height + overscan):
        source_y = retime_start + (float(y - retime_start) * source_span / output_span)
        shape_y0 = int(np.floor(source_y))
        shape_y1 = min(height - 1, shape_y0 + 1)
        shape_fraction = source_y - shape_y0
        boundary_left = float(
            left[shape_y0] * (1.0 - shape_fraction) + left[shape_y1] * shape_fraction
        )
        boundary_right = float(
            right[shape_y0] * (1.0 - shape_fraction) + right[shape_y1] * shape_fraction
        )
        left_coverage = smoothstep((xx - (boundary_left - feather)) / feather)
        right_coverage = smoothstep(((boundary_right + feather) - xx) / feather)
        coverage = np.minimum(left_coverage, right_coverage)
        target_alpha[y] = np.rint(coverage * 255.0).astype(np.uint8)
        texture_y = max(0.0, source_y - float(texture_source_offset))
        texture_y0 = int(np.floor(texture_y))
        texture_y1 = min(height - 1, texture_y0 + 1)
        texture_fraction = texture_y - texture_y0
        rgb = (
            pixels[texture_y0, :, :3].astype(np.float32) * (1.0 - texture_fraction)
            + pixels[texture_y1, :, :3].astype(np.float32) * texture_fraction
        )
        target_rgb[y] = np.rint(np.clip(rgb, 0.0, 255.0)).astype(np.uint8)

    current_alpha = output[:, :, 3]
    expose = target_alpha > current_alpha
    rgb_expose = expose & (current_alpha == 0)
    output[rgb_expose, :3] = target_rgb[rgb_expose]
    output[:, :, 3] = np.maximum(current_alpha, target_alpha)
    raised = int(np.count_nonzero(expose[:height]))
    added = int(np.count_nonzero(output[height:, :, 3]))
    require(np.array_equal(output[:retime_start], pixels[:retime_start]),
            "pixels modifiés hors région basse")
    original_opaque = alpha > 0
    require(np.array_equal(output[:height, :, :3][original_opaque], pixels[:, :, :3][original_opaque]),
            "RGB visible existant modifié")
    require(np.all(output[:height, :, 3] >= alpha), "alpha existant abaissé")
    return output, {
        "retime_start_x4": retime_start,
        "overscan_x4": overscan,
        "feather_x4": feather,
        "texture_source_offset_x4": texture_source_offset,
        "raised_existing_canvas_pixels": raised,
        "new_canvas_alpha_pixels": added,
        "unchanged_prefix_rows_x4": retime_start,
    }


def checkerboard(size: tuple[int, int]) -> Image.Image:
    width, height = size
    yy, xx = np.indices((height, width))
    cells = ((xx // 16 + yy // 16) & 1).astype(np.uint8)
    grey = np.where(cells == 0, 70, 100).astype(np.uint8)
    return Image.fromarray(np.dstack([grey, grey, grey, np.full_like(grey, 255)]), "RGBA")


def labelled_pair(before: Image.Image, after: Image.Image, destination: Path,
                  left_label: str, right_label: str) -> None:
    width = max(before.width, after.width)
    height = max(before.height, after.height)
    margin, label_height, gap = 16, 28, 16
    canvas = Image.new("RGBA", (margin * 2 + width * 2 + gap, label_height + height), (30, 30, 30, 255))
    draw = ImageDraw.Draw(canvas)
    draw.text((margin, 7), left_label, fill=(255, 255, 255, 255))
    draw.text((margin + width + gap, 7), right_label, fill=(255, 255, 255, 255))
    for index, image in enumerate((before, after)):
        x = margin + index * (width + gap)
        background = checkerboard((width, height))
        background.alpha_composite(image, (0, 0))
        canvas.alpha_composite(background, (x, label_height))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    canvas.convert("RGB").save(temporary, format="PNG", optimize=True)
    temporary.replace(destination)


def write_json(payload: dict[str, Any], path: Path) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def build(args: argparse.Namespace) -> Path:
    resref = runtime.normalise_resref(args.resref)
    source_bam = args.source_bam.resolve()
    prototype = animation_paths.resolve_existing_run(args.prototype_run, [resref])
    base_pack = args.base_area_pack.resolve()
    output = animation_paths.resolve_run_destination(args.output_run, [resref])
    partial = output.with_name(output.name + ".partial")
    require(not output.exists() and not partial.exists(), f"sortie déjà présente : {output}")
    require(args.bottom_overscan_x1 > 0 and args.retime_height_x1 > 0,
            "dimensions overscan/retiming invalides")

    prototype_manifest = runtime.load_json(prototype / "manifest.json")
    require(prototype_manifest.get("schema") == ALPHA_SCHEMA and
            prototype_manifest.get("status") == "completed" and
            runtime.normalise_resref(str(prototype_manifest.get("resref", ""))) == resref,
            "prototype alpha incompatible")
    base_manifest, base_resources = runtime.validate_v2_pack(base_pack)
    matches = [copy.deepcopy(item) for item in base_resources if item["resref"] == resref]
    require(len(matches) == 1, f"{resref}: ressource unique absente du pack de base")
    resource = matches[0]
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    prototype_frames = sorted(prototype_manifest.get("frames") or [], key=lambda item: int(item["frame"]))
    require(len(frames) == len(prototype_frames) == int(resource["frame_count"]),
            "inventaire de frames divergent")
    logical_sizes = {tuple(int(value) for value in frame["logical_size_x1"]) for frame in frames}
    physical_sizes = {tuple(int(value) for value in frame["physical_size_x4"]) for frame in frames}
    require(len(logical_sizes) == len(physical_sizes) == 1, "prototype réservé à une géométrie uniforme")
    old_logical = next(iter(logical_sizes))
    old_physical = next(iter(physical_sizes))
    require(old_physical == (old_logical[0] * 4, old_logical[1] * 4), "échelle source différente de x4")
    overscan_x4 = args.bottom_overscan_x1 * 4
    retime_start = old_physical[1] - args.retime_height_x1 * 4
    new_logical = (old_logical[0], old_logical[1] + args.bottom_overscan_x1)
    new_physical = (old_physical[0], old_physical[1] + overscan_x4)

    partial.mkdir(parents=True)
    raw_dir = partial / "raw_rgba"
    rgba_dir = partial / "rgba"
    alpha_dir = partial / "alpha"
    preview_dir = partial / "preview"
    bam_dir = partial / "derived-bam"
    pack_dir = partial / "03_runtime_pack"
    for directory in (raw_dir, rgba_dir, alpha_dir, preview_dir, bam_dir, pack_dir):
        directory.mkdir()

    reports = []
    before_preview: Image.Image | None = None
    after_preview: Image.Image | None = None
    asset_records: list[dict[str, Any]] = []
    by_name = {str(asset["name"]): asset for asset in resource["assets"]}
    for expected, (frame, proto_frame) in enumerate(zip(frames, prototype_frames, strict=True)):
        require(int(frame["frame"]) == int(proto_frame["frame"]) == expected,
                "frames non contiguës")
        source_name = str(proto_frame["runtime_asset"])
        source_path = (prototype / source_name).resolve()
        require(source_path.is_file() and sha256(source_path) == str(frame["sha256"]).lower() and
                source_path.stat().st_size == int(frame["bytes"]),
                f"frame {expected}: prototype différent du pack de base")
        source_pixels = np.frombuffer(source_path.read_bytes(), dtype=np.uint8).reshape(
            old_physical[1], old_physical[0], 4
        )
        extended, report = extend_bottom(
            source_pixels, overscan_x4, retime_start, args.feather_x4,
            args.texture_source_offset_x4,
        )
        asset_name = str(frame["asset"])
        raw_path = raw_dir / asset_name
        raw_path.write_bytes(extended.tobytes(order="C"))
        rgba_path = rgba_dir / f"frame_{expected:03d}.png"
        alpha_path = alpha_dir / f"frame_{expected:03d}.png"
        Image.fromarray(extended, "RGBA").save(rgba_path)
        Image.fromarray(extended[:, :, 3], "L").save(alpha_path)
        frame["logical_size_x1"] = list(new_logical)
        frame["physical_size_x4"] = list(new_physical)
        frame["sha256"] = sha256(raw_path)
        frame["bytes"] = raw_path.stat().st_size
        by_name[asset_name]["sha256"] = frame["sha256"]
        by_name[asset_name]["bytes"] = frame["bytes"]
        asset_records.append({"name": asset_name, "sha256": frame["sha256"], "bytes": frame["bytes"]})
        reports.append({
            "frame": expected,
            "source_runtime_sha256": str(proto_frame["runtime_sha256"]).lower(),
            "runtime_asset": f"raw_rgba/{asset_name}",
            "runtime_sha256": frame["sha256"],
            "runtime_bytes": frame["bytes"],
            "rgba": f"rgba/frame_{expected:03d}.png",
            "alpha": f"alpha/frame_{expected:03d}.png",
            **report,
        })
        if expected == 0:
            before_preview = Image.fromarray(source_pixels, "RGBA")
            after_preview = Image.fromarray(extended, "RGBA")

    resource["frames"] = frames
    resource["assets"] = asset_records
    registry_version = int(base_manifest["registry_version"])
    registry_path = pack_dir / runtime.REGISTRY_NAME
    registry_path.write_bytes(runtime.registry_v2_from_resources([resource], registry_version))
    for record in reports:
        source = partial / str(record["runtime_asset"])
        destination = pack_dir / Path(str(record["runtime_asset"])).name
        destination.write_bytes(source.read_bytes())
    raw_bytes = sum(int(item["bytes"]) for item in asset_records)
    pack_manifest = {
        "schema": runtime.PACK_SCHEMA,
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "scale": 4,
        "registry_version": registry_version,
        "runtime_contract": copy.deepcopy(base_manifest["runtime_contract"]),
        "registry": runtime.REGISTRY_NAME,
        "registry_sha256": sha256(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": 1,
        "frame_count": int(resource["frame_count"]),
        "timed_resources": [],
        "raw_bytes": raw_bytes,
        "runtime_budget_enforced": True,
        "base_assets": [],
        "new_assets": [],
        "geometry_override": {
            "resref": resref,
            "old_logical_size_x1": list(old_logical),
            "new_logical_size_x1": list(new_logical),
            "centres_unchanged": True,
            "derived_bam_required": True,
        },
        "resources": [resource],
    }
    write_json(pack_manifest, pack_dir / "manifest.json")
    runtime.validate_v2_pack(pack_dir)

    source_bam_bytes = read_bam(source_bam)
    derived_bam = pad_bam_bottom(source_bam_bytes, args.bottom_overscan_x1)
    derived_bam_path = bam_dir / f"{resref}.BAM"
    derived_bam_path.write_bytes(derived_bam)
    source_frames, _source_palette, source_transparent = decode_bam(source_bam_bytes)
    derived_frames, _derived_palette, derived_transparent = decode_bam(derived_bam)
    require(derived_transparent == source_transparent and len(derived_frames) == len(source_frames),
            "BAM dérivé invalide")
    for source_frame, derived_frame in zip(source_frames, derived_frames, strict=True):
        source_indices, source_cx, source_cy, _ = source_frame
        derived_indices, derived_cx, derived_cy, _ = derived_frame
        require(derived_indices.shape == (source_indices.shape[0] + args.bottom_overscan_x1,
                                          source_indices.shape[1]) and
                np.array_equal(derived_indices[:source_indices.shape[0]], source_indices) and
                bool((derived_indices[source_indices.shape[0]:] == source_transparent).all()) and
                (derived_cx, derived_cy) == (source_cx, source_cy),
                "pixels, padding ou centres BAM divergents")
    require(cycle_metadata(source_bam_bytes, len(source_frames)) ==
            cycle_metadata(derived_bam, len(derived_frames)), "cycles BAM modifiés")

    require(before_preview is not None and after_preview is not None, "preview impossible")
    before_canvas = Image.new("RGBA", after_preview.size, (0, 0, 0, 0))
    before_canvas.alpha_composite(before_preview, (0, 0))
    labelled_pair(
        before_canvas, after_preview,
        preview_dir / "frame_000-comparison.png",
        f"actuel {old_logical[0]}x{old_logical[1]}",
        f"overscan bas {new_logical[0]}x{new_logical[1]}",
    )
    detail_top = max(0, retime_start - 16)
    detail_box = (max(0, old_physical[0] // 2 - 120), detail_top,
                  min(old_physical[0], old_physical[0] // 2 + 120), new_physical[1])
    detail_before = before_canvas.crop(detail_box).resize(
        ((detail_box[2] - detail_box[0]) * 2, (detail_box[3] - detail_box[1]) * 2),
        Image.Resampling.NEAREST,
    )
    detail_after = after_preview.crop(detail_box).resize(detail_before.size, Image.Resampling.NEAREST)
    labelled_pair(
        detail_before, detail_after,
        preview_dir / "frame_000-bottom-detail.png",
        "actuel - détail bas x2", "overscan - détail bas x2",
    )

    manifest = {
        "schema": SCHEMA,
        "status": "completed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "resref": resref,
        "asset_ids": [f"animations:bam:{resref}"],
        "source_prototype": prototype.as_posix(),
        "source_prototype_manifest_sha256": sha256(prototype / "manifest.json"),
        "source_bam": source_bam.as_posix(),
        "source_bam_sha256": sha256(source_bam),
        "base_area_pack": base_pack.as_posix(),
        "base_area_pack_manifest_sha256": sha256(base_pack / "manifest.json"),
        "geometry_operation": {
            "type": "bottom-canvas-overscan-with-local-vertical-retime",
            "bottom_overscan_x1": args.bottom_overscan_x1,
            "bottom_overscan_x4": overscan_x4,
            "retime_height_x1": args.retime_height_x1,
            "retime_start_x4": retime_start,
            "feather_x4": args.feather_x4,
            "texture_source_offset_x4": args.texture_source_offset_x4,
            "old_logical_size_x1": list(old_logical),
            "new_logical_size_x1": list(new_logical),
            "centres": "unchanged",
            "cycles": "unchanged",
            "existing_visible_rgb": "byte-identical",
            "alpha_policy": "raise-only inside the bounded lower retime region",
        },
        "derived_bam": "derived-bam/FALL2.BAM",
        "derived_bam_sha256": sha256(derived_bam_path),
        "runtime_pack": "03_runtime_pack",
        "runtime_pack_manifest_sha256": sha256(pack_dir / "manifest.json"),
        "frames": reports,
        "previews": [
            "preview/frame_000-comparison.png",
            "preview/frame_000-bottom-detail.png",
        ],
        "qa_status": "pending-explicit-user-approval",
    }
    write_json(manifest, partial / "manifest.json")
    partial.replace(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--source-bam", type=Path, required=True)
    parser.add_argument("--prototype-run", required=True)
    parser.add_argument("--base-area-pack", type=Path, required=True)
    parser.add_argument("--output-run", required=True)
    parser.add_argument("--bottom-overscan-x1", type=int, default=4)
    parser.add_argument("--retime-height-x1", type=int, default=20)
    parser.add_argument("--feather-x4", type=float, default=2.0)
    parser.add_argument("--texture-source-offset-x4", type=int, default=32)
    return parser.parse_args()


def main() -> None:
    output = build(parse_args())
    print(output)


if __name__ == "__main__":
    main()
