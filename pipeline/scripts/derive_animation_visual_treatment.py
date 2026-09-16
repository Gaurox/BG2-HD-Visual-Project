#!/usr/bin/env python3
"""Derive immutable runtime packs with canvas fade or light premultiplied RGBA blur.

The temporal timeline is copied verbatim.  Only selected resource payloads and,
for Gaussian blur, their padded frame geometry are changed.  The result is a
new run containing a validated ``03_runtime_pack`` and side-by-side reviews.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

import run_animation_upscale_30fps_v2 as v2


RUN_SCHEMA = "bg2-upscale-animation-visual-treatment-v1"


def read_rgba(pack: Path, frame: dict[str, Any]) -> np.ndarray:
    width, height = (int(value) for value in frame["physical_size_x4"])
    payload = (pack / str(frame["asset"])).read_bytes()
    v2.require(len(payload) == width * height * 4,
               f"payload RGBA incohérent : {frame['asset']}")
    return np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 4).copy()


def smoothstep(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def apply_canvas_edge_fade(rgba: np.ndarray, fraction: float) -> tuple[np.ndarray, float]:
    height, width = rgba.shape[:2]
    fade_width = max(1.0, min(width, height) * fraction)
    x = np.minimum(np.arange(width), np.arange(width)[::-1]).astype(np.float32)
    y = np.minimum(np.arange(height), np.arange(height)[::-1]).astype(np.float32)
    factor = smoothstep(np.minimum.outer(y, x) / fade_width)
    output = np.rint(rgba.astype(np.float32) * factor[:, :, None]).astype(np.uint8)
    return output, fade_width


def apply_inner_contour_fade(rgba: np.ndarray, radius: float) -> np.ndarray:
    """Fade strictly inside the alpha silhouette; canvas exterior is transparent."""
    inside = rgba[:, :, 3] > 0
    padded = np.pad(inside, 1, mode="constant", constant_values=False)
    distance = distance_transform_edt(padded)[1:-1, 1:-1]
    factor = smoothstep((distance - 1.0) / radius)
    return np.rint(rgba.astype(np.float32) * factor[:, :, None]).astype(np.uint8)


def apply_premultiplied_gaussian(
    rgba: np.ndarray, sigma: float, padding: int
) -> np.ndarray:
    if not np.any(rgba[:, :, 3]):
        return rgba
    padded = np.pad(
        rgba.astype(np.float32),
        ((padding, padding), (padding, padding), (0, 0)),
        mode="constant",
    )
    blurred = gaussian_filter(
        padded, sigma=(sigma, sigma, 0.0), mode="constant", cval=0.0, truncate=4.0
    )
    output = np.clip(np.rint(blurred), 0, 255).astype(np.uint8)
    output[:, :, :3] = np.minimum(output[:, :, :3], output[:, :, 3:4])
    return output


def apply_geometry_preserving_rgb_gaussian(rgba: np.ndarray, sigma: float) -> np.ndarray:
    """Blur visible colour while preserving alpha, dimensions and runtime lookup geometry."""
    alpha = rgba[:, :, 3].astype(np.float32)
    if not np.any(alpha):
        return rgba
    coverage = alpha / 255.0
    blurred_coverage = gaussian_filter(
        coverage, sigma=sigma, mode="constant", cval=0.0, truncate=4.0
    )
    blurred_premultiplied = np.stack(
        [
            gaussian_filter(
                rgba[:, :, channel].astype(np.float32),
                sigma=sigma,
                mode="constant",
                cval=0.0,
                truncate=4.0,
            )
            for channel in range(3)
        ],
        axis=2,
    )
    straight = blurred_premultiplied / np.maximum(blurred_coverage, 1e-6)[:, :, None]
    output = rgba.copy()
    output[:, :, :3] = np.clip(
        np.rint(straight * coverage[:, :, None]), 0, 255
    ).astype(np.uint8)
    output[:, :, :3] = np.minimum(output[:, :, :3], output[:, :, 3:4])
    return output


def asset_record(resource: dict[str, Any], name: str) -> dict[str, Any]:
    matches = [item for item in resource["assets"] if item["name"] == name]
    v2.require(len(matches) == 1, f"asset absent ou ambigu : {name}")
    return matches[0]


def update_payload(
    pack: Path, resource: dict[str, Any], frame: dict[str, Any], rgba: np.ndarray
) -> None:
    path = pack / str(frame["asset"])
    path.write_bytes(rgba.tobytes())
    digest = v2.sha256_file(path)
    size = path.stat().st_size
    frame["sha256"] = digest
    frame["bytes"] = size
    record = asset_record(resource, str(frame["asset"]))
    record["sha256"] = digest
    record["bytes"] = size


def checkerboard(width: int, height: int, cell: int = 16) -> np.ndarray:
    yy, xx = np.indices((height, width))
    value = np.where(((xx // cell) + (yy // cell)) % 2 == 0, 54, 86).astype(np.uint8)
    return np.dstack((value, value, value))


def composite_premultiplied(background: np.ndarray, rgba: np.ndarray, x: int, y: int) -> None:
    height, width = rgba.shape[:2]
    target = background[y:y + height, x:x + width].astype(np.float32)
    alpha = rgba[:, :, 3:4].astype(np.float32) / 255.0
    result = rgba[:, :, :3].astype(np.float32) + target * (1.0 - alpha)
    background[y:y + height, x:x + width] = np.clip(np.rint(result), 0, 255).astype(np.uint8)


def resource_bounds(resources: list[dict[str, Any]], scale: int) -> tuple[int, int, int, int]:
    frames = [frame for resource in resources for frame in resource["frames"]]
    left = min(-int(frame["centre_x1"][0]) * scale for frame in frames)
    top = min(-int(frame["centre_x1"][1]) * scale for frame in frames)
    right = max(
        -int(frame["centre_x1"][0]) * scale + int(frame["physical_size_x4"][0])
        for frame in frames
    )
    bottom = max(
        -int(frame["centre_x1"][1]) * scale + int(frame["physical_size_x4"][1])
        for frame in frames
    )
    return left, top, right, bottom


def render_reviews(
    source_pack: Path,
    output_pack: Path,
    source_resource: dict[str, Any],
    output_resource: dict[str, Any],
    review_root: Path,
    ffmpeg: str,
) -> list[dict[str, Any]]:
    scale = 4
    left, top, right, bottom = resource_bounds(
        [source_resource, output_resource], scale
    )
    panel_width, panel_height = right - left, bottom - top
    header, gap = 28, 12
    source_frames = {int(item["frame"]): item for item in source_resource["frames"]}
    output_frames = {int(item["frame"]): item for item in output_resource["frames"]}
    source_timeline = [int(value) for value in source_resource["cycles"][0]["timeline_frame_indices"]]
    output_timeline = [int(value) for value in output_resource["cycles"][0]["timeline_frame_indices"]]
    v2.require(source_timeline == output_timeline, f"{output_resource['resref']}: timeline modifiée")

    frames_root = review_root / output_resource["resref"] / "frames"
    frames_root.mkdir(parents=True)
    for phase, frame_index in enumerate(output_timeline):
        canvas = np.full(
            (header + panel_height, panel_width * 2 + gap, 3), (24, 26, 30), dtype=np.uint8
        )
        image = Image.fromarray(canvas, "RGB")
        draw = ImageDraw.Draw(image)
        draw.text((8, 8), "avant", fill="white")
        draw.text((panel_width + gap + 8, 8), "apres", fill="white")
        canvas = np.asarray(image).copy()
        for column, (pack, frame) in enumerate((
            (source_pack, source_frames[frame_index]),
            (output_pack, output_frames[frame_index]),
        )):
            panel = checkerboard(panel_width, panel_height)
            rgba = read_rgba(pack, frame)
            x = -int(frame["centre_x1"][0]) * scale - left
            y = -int(frame["centre_x1"][1]) * scale - top
            composite_premultiplied(panel, rgba, x, y)
            x0 = column * (panel_width + gap)
            canvas[header:header + panel_height, x0:x0 + panel_width] = panel
        Image.fromarray(canvas, "RGB").save(frames_root / f"frame_{phase:04d}.png")

    exact = review_root / output_resource["resref"] / "comparison-30fps-exact.mp4"
    loop = review_root / output_resource["resref"] / "comparison-30fps-loop-4s.mp4"
    v2.run_checked([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-framerate", "30",
        "-i", str(frames_root / "frame_%04d.png"), "-frames:v", str(len(output_timeline)),
        "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(exact),
    ])
    v2.run_checked([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-stream_loop", "-1",
        "-i", str(exact), "-t", "4", "-c:v", "libx264", "-preset", "slow",
        "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(loop),
    ])
    return [
        {"resref": output_resource["resref"], "kind": "comparison-exact",
         "file": str(exact.relative_to(review_root.parent)).replace("\\", "/"),
         "sha256": v2.sha256_file(exact)},
        {"resref": output_resource["resref"], "kind": "comparison-loop-4s",
         "file": str(loop.relative_to(review_root.parent)).replace("\\", "/"),
         "sha256": v2.sha256_file(loop)},
    ]


def build(args: argparse.Namespace) -> Path:
    source_pack = args.input.resolve()
    output = args.output.resolve()
    partial = output.with_name(output.name + ".partial")
    v2.require(not output.exists() and not partial.exists(), f"sortie déjà présente : {output}")
    source_manifest, source_resources = v2.validate_v2_pack(source_pack)
    selected = [v2.normalise_resref(value) for value in args.resref]
    v2.require(len(selected) == len(set(selected)), "resref demandé en double")
    by_resref = {v2.normalise_resref(item["resref"]): item for item in source_resources}
    v2.require(set(selected) <= set(by_resref), "ressource demandée absente du pack source")
    using_fade = args.canvas_edge_fade_fraction > 0.0
    using_inner_contour = args.inner_contour_fade_x4 > 0.0
    using_gaussian = args.gaussian_sigma_x4 > 0.0
    v2.require(sum((using_fade, using_inner_contour, using_gaussian)) == 1,
               "activer exactement un traitement : fade canvas, contour interne ou gaussien")
    v2.require(not using_fade or 0.0 < args.canvas_edge_fade_fraction < 0.5,
               "fraction de fade hors intervalle (0, 0.5)")
    v2.require(not using_inner_contour or args.inner_contour_fade_x4 <= 64.0,
               "rayon de fade contour hors intervalle (0, 64]")
    v2.require(not using_gaussian or args.gaussian_sigma_x4 <= 8.0,
               "sigma gaussien hors intervalle (0, 8]")
    v2.require(not args.gaussian_preserve_geometry or using_gaussian,
               "--gaussian-preserve-geometry exige un sigma gaussien")
    padding = args.gaussian_padding_x4
    if using_gaussian and not args.gaussian_preserve_geometry and padding is None:
        padding = int(math.ceil((4.0 * args.gaussian_sigma_x4) / 4.0) * 4)
    padding = int(padding or 0)
    v2.require(not using_gaussian or args.gaussian_preserve_geometry
               or (padding >= math.ceil(4.0 * args.gaussian_sigma_x4)
                   and padding % 4 == 0),
               "padding gaussien insuffisant ou non divisible par 4")

    pack = partial / "03_runtime_pack"
    pack.mkdir(parents=True)
    resources = [copy.deepcopy(by_resref[resref]) for resref in selected]
    source_selected = [by_resref[resref] for resref in selected]
    source_asset_records = {
        str(asset["name"]): copy.deepcopy(asset)
        for resource in source_selected for asset in resource["assets"]
    }
    for name in source_asset_records:
        shutil.copy2(source_pack / name, pack / name)

    metrics: dict[str, Any] = {}
    for resource in resources:
        changed = 0
        fade_widths: list[float] = []
        alpha_before = 0
        alpha_after = 0
        for frame in resource["frames"]:
            rgba = read_rgba(pack, frame)
            alpha_before += int(rgba[:, :, 3].sum(dtype=np.uint64))
            if using_fade:
                treated, fade_width = apply_canvas_edge_fade(
                    rgba, args.canvas_edge_fade_fraction
                )
                fade_widths.append(fade_width)
            elif using_inner_contour:
                treated = apply_inner_contour_fade(
                    rgba, args.inner_contour_fade_x4
                )
            elif np.any(rgba[:, :, 3]):
                if args.gaussian_preserve_geometry:
                    treated = apply_geometry_preserving_rgb_gaussian(
                        rgba, args.gaussian_sigma_x4
                    )
                else:
                    treated = apply_premultiplied_gaussian(
                        rgba, args.gaussian_sigma_x4, padding
                    )
                    frame["physical_size_x4"] = [int(treated.shape[1]), int(treated.shape[0])]
                    frame["logical_size_x1"] = [int(treated.shape[1] // 4), int(treated.shape[0] // 4)]
                    frame["centre_x1"] = [
                        int(frame["centre_x1"][0]) + padding // 4,
                        int(frame["centre_x1"][1]) + padding // 4,
                    ]
            else:
                treated = rgba
            alpha_after += int(treated[:, :, 3].sum(dtype=np.uint64))
            if treated.shape != rgba.shape or not np.array_equal(treated, rgba):
                update_payload(pack, resource, frame, treated)
                changed += 1
        metrics[resource["resref"]] = {
            "frame_count": len(resource["frames"]),
            "changed_frame_count": changed,
            "alpha_sum_before": alpha_before,
            "alpha_sum_after": alpha_after,
            "fade_width_x4_min": min(fade_widths) if fade_widths else None,
            "fade_width_x4_max": max(fade_widths) if fade_widths else None,
            "inner_contour_radius_x4": (
                args.inner_contour_fade_x4 if using_inner_contour else None
            ),
            "gaussian_padding_x4": padding if using_gaussian else 0,
            "geometry_preserved": bool(args.gaussian_preserve_geometry),
        }

    registry = v2.registry_v2_from_resources(resources, int(source_manifest["registry_version"]))
    registry_path = pack / v2.REGISTRY_NAME
    registry_path.write_bytes(registry)
    replacement_assets = []
    for resource in resources:
        for asset in resource["assets"]:
            source = source_asset_records[asset["name"]]
            replacement_assets.append({
                "name": asset["name"], "sha256": asset["sha256"], "bytes": asset["bytes"],
                "expected_base_sha256": source["sha256"],
                "expected_base_bytes": source["bytes"],
            })
    now = datetime.now(timezone.utc).isoformat()
    if using_fade:
        treatment = {
            "kind": "canvas-edge-fade", "curve": "smoothstep-min-distance",
            "fraction_of_min_dimension": args.canvas_edge_fade_fraction,
            "rgba_policy": "multiply-premultiplied-rgba",
        }
    elif using_inner_contour:
        treatment = {
            "kind": "inner-contour-fade", "curve": "smoothstep-distance-transform",
            "radius_x4": args.inner_contour_fade_x4,
            "rgba_policy": "multiply-premultiplied-rgba",
            "alpha_constraint": "final<=source",
        }
    elif args.gaussian_preserve_geometry:
        treatment = {
            "kind": "alpha-weighted-rgb-gaussian", "sigma_x4": args.gaussian_sigma_x4,
            "padding_x4": 0, "truncate": 4.0,
            "rgba_policy": "blur-visible-rgb-preserve-alpha-and-geometry",
        }
    else:
        treatment = {
            "kind": "premultiplied-rgba-gaussian", "sigma_x4": args.gaussian_sigma_x4,
            "padding_x4": padding, "truncate": 4.0,
            "rgba_policy": "blur-premultiplied-rgba-with-transparent-padding",
        }
    manifest = {
        "schema": v2.PACK_SCHEMA,
        "status": "completed",
        "created_utc": now,
        "scale": 4,
        "registry_version": int(source_manifest["registry_version"]),
        "runtime_contract": source_manifest.get("runtime_contract"),
        "registry": v2.REGISTRY_NAME,
        "registry_sha256": v2.sha256_file(registry_path),
        "registry_bytes": len(registry),
        "resource_count": len(resources),
        "frame_count": sum(int(resource["frame_count"]) for resource in resources),
        "timed_resources": selected,
        "timed_resource_variants": [
            item for item in source_manifest.get("timed_resource_variants", [])
            if v2.normalise_resref(item["resref"]) in selected
        ],
        "runtime_budget_enforced": True,
        "authoring_pack_for_area_split": False,
        "base_pack": str(source_pack),
        "base_pack_manifest_sha256": v2.sha256_file(source_pack / "manifest.json"),
        "base_registry_sha256": v2.sha256_file(source_pack / v2.REGISTRY_NAME),
        "base_registry_bytes": (source_pack / v2.REGISTRY_NAME).stat().st_size,
        "base_assets": [],
        "new_assets": [],
        "resources": resources,
        "replacement_assets": replacement_assets,
        "raw_bytes": sum(int(asset["bytes"]) for resource in resources for asset in resource["assets"]),
        "derived_from": str(source_pack),
        "visual_treatment": treatment,
        "visual_treatment_metrics": metrics,
    }
    v2.write_json(pack / "manifest.json", manifest)
    v2.validate_v2_pack(pack)

    ffmpeg = args.ffmpeg or shutil.which("ffmpeg")
    v2.require(bool(ffmpeg), "ffmpeg introuvable pour les aperçus")
    reviews = []
    review_root = partial / "review"
    for source_resource, output_resource in zip(source_selected, resources, strict=True):
        reviews.extend(render_reviews(
            source_pack, pack, source_resource, output_resource, review_root, str(ffmpeg)
        ))
    run_manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed",
        "created_utc": now,
        "source_pack": str(source_pack),
        "source_pack_manifest_sha256": v2.sha256_file(source_pack / "manifest.json"),
        "runtime_pack": "03_runtime_pack",
        "runtime_pack_manifest_sha256": v2.sha256_file(pack / "manifest.json"),
        "resrefs": selected,
        "visual_treatment": treatment,
        "metrics": metrics,
        "reviews": reviews,
        "qa": "explicit visual approval required before installation",
    }
    v2.write_json(partial / "manifest.json", run_manifest)
    partial.rename(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="pack runtime V2 source")
    parser.add_argument("--output", type=Path, required=True, help="nouveau run dérivé")
    parser.add_argument("--resref", action="append", required=True)
    parser.add_argument("--canvas-edge-fade-fraction", type=float, default=0.0)
    parser.add_argument("--inner-contour-fade-x4", type=float, default=0.0)
    parser.add_argument("--gaussian-sigma-x4", type=float, default=0.0)
    parser.add_argument("--gaussian-padding-x4", type=int)
    parser.add_argument("--gaussian-preserve-geometry", action="store_true")
    parser.add_argument("--ffmpeg")
    return parser.parse_args()


def main() -> None:
    output = build(parse_args())
    print(output)


if __name__ == "__main__":
    main()
