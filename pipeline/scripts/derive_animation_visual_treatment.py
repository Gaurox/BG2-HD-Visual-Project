#!/usr/bin/env python3
"""Derive immutable runtime packs with alpha masks, fades, light RGBA blur or a bright-core blur.

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
from scipy.ndimage import (
    binary_closing, binary_dilation, binary_fill_holes, distance_transform_edt,
    gaussian_filter, label,
)

import build_per_frame_spline_alpha_30fps_v2 as spline
import run_animation_upscale_30fps_v2 as v2


RUN_SCHEMA = "bg2-upscale-animation-visual-treatment-v1"


def read_rgba(pack: Path, frame: dict[str, Any]) -> np.ndarray:
    width, height = (int(value) for value in frame["physical_size_x4"])
    payload = (pack / str(frame["asset"])).read_bytes()
    v2.require(len(payload) == width * height * 4,
               f"payload RGBA incohérent : {frame['asset']}")
    return np.frombuffer(payload, dtype=np.uint8).reshape(height, width, 4).copy()


def load_alpha_mask(path: Path, expected_size: tuple[int, int]) -> np.ndarray:
    """Load one grayscale mask; black hides, white preserves, grey softens alpha."""
    v2.require(path.is_file(), f"masque alpha absent : {path}")
    with Image.open(path) as opened:
        v2.require(opened.size == expected_size,
                   f"masque alpha {path}: dimensions {opened.size}, attendu {expected_size}")
        rgb = np.asarray(opened.convert("RGB"), dtype=np.uint8)
    v2.require(np.array_equal(rgb[:, :, 0], rgb[:, :, 1])
               and np.array_equal(rgb[:, :, 0], rgb[:, :, 2]),
               f"masque alpha non monochrome : {path}")
    return rgb[:, :, 0].copy()


def apply_alpha_mask(rgba: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Multiply only alpha by a user-authored 8-bit grayscale mask."""
    v2.require(mask.shape == rgba.shape[:2], "dimensions du masque alpha incohérentes")
    output = rgba.copy()
    alpha = rgba[:, :, 3].astype(np.uint16)
    output[:, :, 3] = ((alpha * mask.astype(np.uint16) + 127) // 255).astype(np.uint8)
    return output


def bright_core_mask(
    frames: list[np.ndarray], seed_luma: float, margin_x4: int, feather_x4: float
) -> tuple[np.ndarray, int]:
    """One loop-wide soft mask over the largest bright opaque core (a flame body).

    Seed = union over the loop of opaque pixels brighter than ``seed_luma``; closed,
    largest connected component only, holes filled, then a margin dilation and a
    Gaussian feather.  Returns the float mask in [0, 1] and the seed pixel count.
    """
    weights = np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
    seed = np.zeros(frames[0].shape[:2], dtype=bool)
    for rgba in frames:
        luma = rgba[:, :, :3].astype(np.float32) @ weights
        seed |= (luma > seed_luma) & (rgba[:, :, 3] > 0)
    seed = binary_closing(seed, iterations=3)
    labelled, count = label(seed)
    v2.require(count > 0, "aucun noyau lumineux : seuil de luminance trop haut")
    sizes = np.bincount(labelled.ravel())[1:]
    seed = binary_fill_holes(labelled == (int(sizes.argmax()) + 1))
    grown = binary_dilation(seed, iterations=margin_x4).astype(np.float32)
    return np.clip(gaussian_filter(grown, feather_x4), 0.0, 1.0), int(seed.sum())


def apply_masked_rgb_gaussian(rgba: np.ndarray, mask: np.ndarray, sigma: float) -> np.ndarray:
    """Blur straight RGB inside ``mask``; alpha and geometry are copied verbatim."""
    v2.require(mask.shape == rgba.shape[:2], "dimensions du masque de flou incohérentes")
    rgb = rgba[:, :, :3].astype(np.float32)
    blurred = np.stack([gaussian_filter(rgb[:, :, c], sigma) for c in range(3)], axis=-1)
    weight = mask[:, :, None]
    output = rgba.copy()
    output[:, :, :3] = np.clip(np.rint(rgb * (1.0 - weight) + blurred * weight), 0, 255).astype(np.uint8)
    return output


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


def dilate_rgb_under_transparency(rgba: np.ndarray) -> tuple[np.ndarray, int]:
    """Fill hidden RGB from the nearest visible texel without changing alpha."""
    transparent = rgba[:, :, 3] == 0
    if not np.any(transparent):
        return rgba.copy(), 0
    output = rgba.copy()
    if np.any(~transparent):
        nearest = distance_transform_edt(
            transparent, return_distances=False, return_indices=True
        )
        output[transparent, :3] = rgba[
            nearest[0][transparent], nearest[1][transparent], :3
        ]
    else:
        output[transparent, :3] = 0
    changed = np.any(output[:, :, :3] != rgba[:, :, :3], axis=2)
    return output, int(np.count_nonzero(changed))


def apply_inner_contour_fade(
    rgba: np.ndarray, radius: float, rgb_policy: str, open_canvas_edges: bool = False
) -> tuple[np.ndarray, int]:
    """Fade strictly inside the alpha silhouette; canvas exterior is transparent.

    With ``open_canvas_edges`` the silhouette continues past the canvas where it is opaque, so a
    canvas-cut edge (e.g. the contact seam between two adjacent BAM) keeps its source alpha.
    """
    inside = rgba[:, :, 3] > 0
    if open_canvas_edges:
        padded = np.pad(inside, 1, mode="edge")
    else:
        padded = np.pad(inside, 1, mode="constant", constant_values=False)
    distance = (
        distance_transform_edt(padded)[1:-1, 1:-1] if not padded.all()
        else np.full(inside.shape, radius + 1.0)
    )
    factor = smoothstep((distance - 1.0) / radius)
    if rgb_policy == "premultiplied":
        return (
            np.rint(rgba.astype(np.float32) * factor[:, :, None]).astype(np.uint8),
            0,
        )
    output = rgba.copy()
    output[:, :, 3] = np.clip(
        np.rint(rgba[:, :, 3].astype(np.float32) * factor), 0, 255
    ).astype(np.uint8)
    return dilate_rgb_under_transparency(output)


def apply_luminance_alpha(
    rgba: np.ndarray, low: float, high: float
) -> np.ndarray:
    """Reconstruct soft alpha from baked dark RGB and premultiply for Blended."""
    luminance = rgba[:, :, :3].astype(np.float32).mean(axis=2)
    factor = smoothstep((luminance - low) / (high - low))
    source_alpha = rgba[:, :, 3].astype(np.float32) / 255.0
    alpha = source_alpha * factor
    output = rgba.copy()
    output[:, :, :3] = np.clip(
        np.rint(rgba[:, :, :3].astype(np.float32) * alpha[:, :, None]), 0, 255
    ).astype(np.uint8)
    output[:, :, 3] = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    return output


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


def apply_lower_edge_cover(
    rgba: np.ndarray, reference: np.ndarray, rows: int, depth: int, zone: int
) -> tuple[np.ndarray, int]:
    """Cover the lower silhouette edges of a strict-alpha animation with opaque water.

    A map hole under the animation can carry a bright halo and dark fill just outside
    the source alpha; a feathered alpha lets both show at the lower edges.  The source
    silhouette (``reference``, the alpha before any feather) is extended ``rows`` rows
    downward, smoothed by the same spline fit, and merged with the current alpha inside
    ``zone`` px of the added ring.  There the RGB is repushed from ``depth`` px inside
    the source edge, which also drops the BAM's light edge dots.

    Frame dimensions stay exactly those of the native BAM frame, so the ring is clipped
    at the canvas: the engine binds an x4 frame only when its logical size matches the
    CVidCell draw (``resolve_timeline_subframe``), and a padded frame silently falls
    back to the vanilla BAM.  Returns the frame and the added ring pixels."""
    source = reference[:, :, 3] > 127
    if not source.any():
        return rgba, 0
    extended = source.copy()
    for step in range(1, rows + 1):
        extended[step:] |= source[:-step]
    ring = extended & ~source
    canvas = np.pad(extended, 32)
    labels, count = label(canvas, structure=np.ones((3, 3), dtype=np.uint8))
    mask = np.zeros(canvas.shape, dtype=np.uint8)
    for index in range(1, int(count) + 1):
        fitted, _ = spline.fit_component(labels == index, 1.0, 1.5, 4)
        mask = np.maximum(mask, fitted)
    mask = mask[32:-32, 32:-32].astype(np.float32)
    near_ring = distance_transform_edt(~ring) <= float(zone)
    alpha = rgba[:, :, 3].astype(np.float32)
    merged = np.where(near_ring, np.maximum(alpha, mask), alpha)
    inside = distance_transform_edt(source)
    _, nearest = distance_transform_edt(inside < depth, return_indices=True)
    band = near_ring & (merged > 0) & ((inside < depth) | ring)
    output = rgba.copy()
    output[:, :, :3][band] = rgba[:, :, :3][nearest[0][band], nearest[1][band]]
    output[:, :, 3] = np.clip(np.rint(merged), 0, 255).astype(np.uint8)
    return output, int(ring.sum())


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
    using_luminance = args.luminance_low is not None or args.luminance_high is not None
    using_alpha_mask = bool(args.alpha_mask)
    using_bright_core = args.bright_core_blur_sigma_x4 > 0.0
    using_lower_cover = args.lower_edge_cover_rows > 0
    alpha_mask_paths = [path.resolve() for path in (args.alpha_mask or [])]
    v2.require(not using_alpha_mask or len(alpha_mask_paths) == len(selected),
               "fournir exactement un --alpha-mask par --resref, dans le même ordre")
    v2.require(not using_luminance or (
        args.luminance_low is not None and args.luminance_high is not None
        and 0.0 <= args.luminance_low < args.luminance_high <= 255.0
    ), "seuils de luminance invalides")
    v2.require(sum((using_inner_contour, using_gaussian, using_luminance, using_alpha_mask,
                    using_bright_core, using_lower_cover)) == 1
               or (using_fade and not using_inner_contour and not using_gaussian),
               "activer un traitement principal ; le fade canvas peut compléter la luminance")
    v2.require(not using_fade or 0.0 < args.canvas_edge_fade_fraction < 0.5,
               "fraction de fade hors intervalle (0, 0.5)")
    v2.require(not using_inner_contour or args.inner_contour_fade_x4 <= 64.0,
               "rayon de fade contour hors intervalle (0, 64]")
    v2.require(args.rgb_policy in {"premultiplied", "preserve"},
               "politique RGB inconnue")
    v2.require(args.rgb_policy != "preserve" or using_inner_contour or using_alpha_mask
               or using_bright_core or using_lower_cover,
               "RGB preserve est réservé aux traitements alpha stricts")
    v2.require(not using_bright_core or args.rgb_policy == "preserve",
               "le flou du noyau lumineux exige --rgb-policy preserve (RGB droit)")
    v2.require(not using_lower_cover or (
        args.rgb_policy == "preserve" and args.alpha_reference_pack is not None
        and 0 < args.lower_edge_cover_rows <= 16
        and args.lower_edge_cover_depth_x4 >= 0 and args.lower_edge_cover_zone_x4 > 0
    ), "couverture du bord bas : exige --rgb-policy preserve, --alpha-reference-pack et "
       "1 <= lignes <= 16")
    reference_pack = None
    reference_by_resref: dict[str, dict[str, Any]] = {}
    if using_lower_cover:
        reference_pack = args.alpha_reference_pack.resolve()
        _reference_manifest, reference_resources = v2.validate_v2_pack(reference_pack)
        reference_by_resref = {
            v2.normalise_resref(item["resref"]): item for item in reference_resources
        }
        v2.require(set(selected) <= set(reference_by_resref),
                   "ressource absente du pack de référence alpha")
    v2.require(not using_bright_core or args.bright_core_blur_sigma_x4 <= 16.0,
               "sigma du flou de noyau hors intervalle (0, 16]")
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
    alpha_masks: dict[str, np.ndarray] = {}
    alpha_mask_records: dict[str, dict[str, Any]] = {}
    if using_alpha_mask:
        sealed_root = partial / "manual-alpha-masks"
        for resref, source_resource, mask_path in zip(
            selected, source_selected, alpha_mask_paths, strict=True
        ):
            sizes = {
                tuple(int(value) for value in frame["physical_size_x4"])
                for frame in source_resource["frames"]
            }
            v2.require(len(sizes) == 1,
                       f"{resref}: un masque répété exige une géométrie uniforme")
            expected_size = next(iter(sizes))
            alpha_masks[resref] = load_alpha_mask(mask_path, expected_size)
            sealed = sealed_root / resref / "source.png"
            sealed.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(mask_path, sealed)
            alpha_mask_records[resref] = {
                "source": str(sealed.relative_to(partial)).replace("\\", "/"),
                "sha256": v2.sha256_file(sealed),
                "size_x4": list(expected_size),
            }
    source_asset_records = {
        str(asset["name"]): copy.deepcopy(asset)
        for resource in source_selected for asset in resource["assets"]
    }
    for name in source_asset_records:
        shutil.copy2(source_pack / name, pack / name)

    metrics: dict[str, Any] = {}
    for resource in resources:
        changed = 0
        core_mask = None
        core_seed_px = 0
        if using_bright_core:
            core_mask, core_seed_px = bright_core_mask(
                [read_rgba(pack, frame) for frame in resource["frames"]],
                args.bright_core_seed_luma, args.bright_core_margin_x4,
                args.bright_core_feather_x4,
            )
        fade_widths: list[float] = []
        alpha_before = 0
        alpha_after = 0
        rgb_dilated_pixels = 0
        cover_ring_pixels = 0
        for frame in resource["frames"]:
            rgba = read_rgba(pack, frame)
            alpha_before += int(rgba[:, :, 3].sum(dtype=np.uint64))
            if using_alpha_mask:
                treated = apply_alpha_mask(rgba, alpha_masks[resource["resref"]])
            elif using_luminance:
                treated = apply_luminance_alpha(
                    rgba, args.luminance_low, args.luminance_high
                )
                if using_fade:
                    treated, fade_width = apply_canvas_edge_fade(
                        treated, args.canvas_edge_fade_fraction
                    )
                    fade_widths.append(fade_width)
            elif using_fade:
                treated, fade_width = apply_canvas_edge_fade(
                    rgba, args.canvas_edge_fade_fraction
                )
                fade_widths.append(fade_width)
            elif using_bright_core:
                treated = apply_masked_rgb_gaussian(
                    rgba, core_mask, args.bright_core_blur_sigma_x4
                )
            elif using_lower_cover:
                reference_frame = next(
                    item for item in reference_by_resref[resource["resref"]]["frames"]
                    if str(item["asset"]) == str(frame["asset"])
                )
                treated, cover_ring_px = apply_lower_edge_cover(
                    rgba, read_rgba(reference_pack, reference_frame),
                    args.lower_edge_cover_rows, args.lower_edge_cover_depth_x4,
                    args.lower_edge_cover_zone_x4,
                )
                cover_ring_pixels += cover_ring_px
            elif using_inner_contour:
                treated, dilated = apply_inner_contour_fade(
                    rgba, args.inner_contour_fade_x4, args.rgb_policy,
                    args.inner_contour_open_canvas_edges
                )
                rgb_dilated_pixels += dilated
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
            "rgb_policy": args.rgb_policy if using_inner_contour else None,
            "rgb_dilated_pixels": rgb_dilated_pixels,
            "gaussian_padding_x4": padding if using_gaussian else 0,
            "geometry_preserved": bool(args.gaussian_preserve_geometry),
            "alpha_mask": alpha_mask_records.get(resource["resref"]),
            "bright_core_seed_px": core_seed_px if using_bright_core else None,
            "bright_core_mask_px": (
                int((core_mask > 0.3).sum()) if core_mask is not None else None
            ),
            "lower_edge_cover_ring_px": cover_ring_pixels if using_lower_cover else None,
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
    if using_alpha_mask:
        treatment = {
            "kind": "manual-grayscale-alpha-mask",
            "alpha_formula": "alpha_final = alpha_source * grayscale_mask / 255",
            "rgba_policy": "preserve-straight-rgb",
            "mask_assignment": "one mask per resref, repeated on every native and interpolated frame",
            "masks": alpha_mask_records,
        }
    elif using_luminance:
        treatment = {
            "kind": "luminance-alpha-with-canvas-edge-fade",
            "luminance_low": args.luminance_low,
            "luminance_high": args.luminance_high,
            "curve": "smoothstep",
            "canvas_edge_fade_fraction": (
                args.canvas_edge_fade_fraction if using_fade else 0.0
            ),
            "rgba_policy": "reconstruct-alpha-and-premultiply-rgb",
        }
    elif using_lower_cover:
        treatment = {
            "kind": "lower-edge-cover",
            "rows_x4": args.lower_edge_cover_rows,
            "rgb_depth_x4": args.lower_edge_cover_depth_x4,
            "zone_x4": args.lower_edge_cover_zone_x4,
            "geometry": "native-bam-dimensions-preserved-ring-clipped-at-canvas",
            "alpha_reference_pack": str(reference_pack),
            "alpha_reference_pack_manifest_sha256": v2.sha256_file(reference_pack / "manifest.json"),
            "rgba_policy": "preserve-straight-rgb-repushed-from-inside-in-the-cover-zone",
            "alpha_constraint": "final>=input alpha inside the zone, unchanged elsewhere",
        }
    elif using_bright_core:
        treatment = {
            "kind": "bright-core-masked-gaussian",
            "sigma_x4": args.bright_core_blur_sigma_x4,
            "seed_luma": args.bright_core_seed_luma,
            "margin_x4": args.bright_core_margin_x4,
            "feather_x4": args.bright_core_feather_x4,
            "mask": "union over the loop of opaque pixels above seed_luma, largest component, filled, dilated, feathered",
            "rgba_policy": "blur-straight-rgb-inside-mask-alpha-and-geometry-verbatim",
        }
    elif using_fade:
        treatment = {
            "kind": "canvas-edge-fade", "curve": "smoothstep-min-distance",
            "fraction_of_min_dimension": args.canvas_edge_fade_fraction,
            "rgba_policy": "multiply-premultiplied-rgba",
        }
    elif using_inner_contour:
        treatment = {
            "kind": "inner-contour-fade", "curve": "smoothstep-distance-transform",
            "radius_x4": args.inner_contour_fade_x4,
            "open_canvas_edges": args.inner_contour_open_canvas_edges,
            "rgba_policy": (
                "preserve-straight-rgb-dilate-under-zero-alpha"
                if args.rgb_policy == "preserve"
                else "multiply-premultiplied-rgba"
            ),
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
    resized = sum(
        1
        for source_resource, output_resource in zip(source_selected, resources, strict=True)
        for source_frame, output_frame in zip(
            source_resource["frames"], output_resource["frames"], strict=True
        )
        if list(source_frame["logical_size_x1"]) != list(output_frame["logical_size_x1"])
    )
    if resized:
        print(f"ATTENTION : {resized} frame(s) changent de taille logique. Le moteur ne lie une "
              "frame x4 que si sa taille logique est celle du BAM natif "
              "(resolve_timeline_subframe) ; sinon il rend le BAM vanilla sans rien journaliser.")
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="pack runtime V2 source")
    parser.add_argument("--output", type=Path, required=True, help="nouveau run dérivé")
    parser.add_argument("--resref", action="append", required=True)
    parser.add_argument("--canvas-edge-fade-fraction", type=float, default=0.0)
    parser.add_argument("--luminance-low", type=float)
    parser.add_argument("--luminance-high", type=float)
    parser.add_argument("--inner-contour-fade-x4", type=float, default=0.0)
    parser.add_argument(
        "--inner-contour-open-canvas-edges", action="store_true",
        help="ne pas faire fondre les bords coupés par le canvas (raccord entre deux BAM)",
    )
    parser.add_argument(
        "--alpha-mask", type=Path, action="append",
        help="masque PNG monochrome correspondant au --resref de même position",
    )
    parser.add_argument(
        "--rgb-policy", choices=("premultiplied", "preserve"), default="premultiplied"
    )
    parser.add_argument("--gaussian-sigma-x4", type=float, default=0.0)
    parser.add_argument(
        "--gaussian-padding-x4", type=int,
        help="agrandit le canevas : le moteur n'accepte que la taille logique du BAM natif "
             "et retombe en vanilla sinon ; préférer --gaussian-preserve-geometry",
    )
    parser.add_argument(
        "--bright-core-blur-sigma-x4", type=float, default=0.0,
        help="flou gaussien du RGB limité au plus grand noyau lumineux (corps d'une flamme "
             "que SeedVR reconstruit en matière) ; exige --rgb-policy preserve",
    )
    parser.add_argument("--bright-core-seed-luma", type=float, default=110.0)
    parser.add_argument("--bright-core-margin-x4", type=int, default=12)
    parser.add_argument("--bright-core-feather-x4", type=float, default=8.0)
    parser.add_argument("--gaussian-preserve-geometry", action="store_true")
    parser.add_argument(
        "--lower-edge-cover-rows", type=int, default=0,
        help="étend l'alpha source de N lignes x4 vers le bas (couvre le halo d'un trou de map)",
    )
    parser.add_argument("--lower-edge-cover-depth-x4", type=int, default=5)
    parser.add_argument("--lower-edge-cover-zone-x4", type=int, default=10)
    parser.add_argument(
        "--alpha-reference-pack", type=Path,
        help="pack V2 portant l'alpha source avant feather (mêmes assets que --input)",
    )
    parser.add_argument("--ffmpeg")
    return parser.parse_args()


def main() -> None:
    output = build(parse_args())
    print(output)


if __name__ == "__main__":
    main()
