"""Repair the internal cross of a four-cycle quadrant animation at 30 fps.

The four cycles are reconstructed on their shared anchor before alpha fitting and
RGB filtering.  The source alpha is restored close to both internal axes, while
RGB receives one simultaneous 2D Gaussian blend confined to the cross.  Output
frame geometry and timelines remain byte-for-byte identical to the source pack.
"""

from __future__ import annotations

import argparse
import copy
import json
from dataclasses import dataclass
from pathlib import Path
import shutil
import sys
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_per_frame_spline_alpha_30fps_v2 as spline  # noqa: E402
import run_animation_upscale_30fps_v2 as runtime  # noqa: E402


SCHEMA = "bg2-upscale-animation-cross-cycle-seam-v1"
PIPELINE_NAME = "cross-cycle-joint-spline-alpha-axis-restore-rgb-gaussian-v2"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


@dataclass(frozen=True)
class Placement:
    frame: dict[str, Any]
    origin_x: int
    origin_y: int
    width: int
    height: int


def sorted_frames(resource: dict[str, Any]) -> list[dict[str, Any]]:
    frames = sorted(resource.get("frames") or [], key=lambda item: int(item["frame"]))
    require(
        len(frames) == int(resource.get("frame_count", 0))
        and [int(item["frame"]) for item in frames] == list(range(len(frames))),
        f"{resource.get('resref', '?')}: frames non contiguës",
    )
    return frames


def placement(frame: dict[str, Any]) -> Placement:
    physical = [int(value) for value in frame.get("physical_size_x4") or []]
    logical = [int(value) for value in frame.get("logical_size_x1") or []]
    centre = [int(value) for value in frame.get("centre_x1") or []]
    require(
        len(physical) == len(logical) == len(centre) == 2
        and physical == [logical[0] * 4, logical[1] * 4],
        "géométrie x4 invalide",
    )
    return Placement(
        frame=frame,
        origin_x=-centre[0] * 4,
        origin_y=-centre[1] * 4,
        width=physical[0],
        height=physical[1],
    )


def phase_indices(resource: dict[str, Any]) -> list[list[int]]:
    require(resource.get("playback_mode") == "TimedTimeline",
            f"{resource.get('resref', '?')}: TimedTimeline requis")
    cycles = sorted(resource.get("cycles") or [], key=lambda item: int(item["cycle"]))
    require(
        len(cycles) == 4 and [int(item["cycle"]) for item in cycles] == list(range(4)),
        f"{resource.get('resref', '?')}: quatre cycles quadrant attendus",
    )
    timelines = [[int(value) for value in item["timeline_frame_indices"]] for item in cycles]
    require(
        timelines[0] and len({len(item) for item in timelines}) == 1,
        f"{resource.get('resref', '?')}: timelines quadrant incompatibles",
    )
    return [list(indices) for indices in zip(*timelines, strict=True)]


def validate_quadrants(resource: dict[str, Any]) -> tuple[list[dict[str, Any]], list[list[int]]]:
    frames = sorted_frames(resource)
    phases = phase_indices(resource)
    by_index = {int(frame["frame"]): frame for frame in frames}
    used: list[int] = []
    for phase, indices in enumerate(phases):
        require(len(set(indices)) == 4, f"phase {phase}: frame quadrant dupliquée")
        for cycle, frame_index in enumerate(indices):
            require(frame_index in by_index, f"phase {phase}: frame {frame_index} absente")
            item = placement(by_index[frame_index])
            right, bottom = item.origin_x + item.width, item.origin_y + item.height
            expected = (
                item.origin_x < 0 and item.origin_y < 0 and right == 0 and bottom == 0,
                item.origin_x == 0 and item.origin_y < 0 and right > 0 and bottom == 0,
                item.origin_x < 0 and item.origin_y == 0 and right == 0 and bottom > 0,
                item.origin_x == 0 and item.origin_y == 0 and right > 0 and bottom > 0,
            )[cycle]
            require(expected, f"phase {phase}, cycle {cycle}: géométrie quadrant invalide")
            used.append(frame_index)
    require(len(used) == len(set(used)) == len(frames),
            f"{resource.get('resref', '?')}: chaque frame doit appartenir à une phase unique")
    return frames, phases


def read_rgba(pack: Path, frame: dict[str, Any]) -> np.ndarray:
    image = runtime.rgba_from_raw(pack / str(frame["asset"]), frame["physical_size_x4"])
    return np.asarray(image, dtype=np.uint8)


def reconstruct(pack: Path, by_index: dict[int, dict[str, Any]], indices: list[int]) -> tuple[
    np.ndarray, list[Placement], tuple[int, int]
]:
    placements = [placement(by_index[index]) for index in indices]
    left = min(item.origin_x for item in placements)
    top = min(item.origin_y for item in placements)
    right = max(item.origin_x + item.width for item in placements)
    bottom = max(item.origin_y + item.height for item in placements)
    require(left < 0 < right and top < 0 < bottom, "croix hors canvas reconstitué")
    canvas = np.zeros((bottom - top, right - left, 4), dtype=np.uint8)
    occupied = np.zeros(canvas.shape[:2], dtype=bool)
    for item in placements:
        x, y = item.origin_x - left, item.origin_y - top
        target = occupied[y:y + item.height, x:x + item.width]
        require(not target.any(), "rectangles quadrant en recouvrement")
        canvas[y:y + item.height, x:x + item.width] = read_rgba(pack, item.frame)
        target[:] = True
    return canvas, placements, (-left, -top)


def axis_restore_weight(shape: tuple[int, int], cross: tuple[int, int], *,
                        protected: int, transition: int) -> np.ndarray:
    require(protected > 0 and transition > 0, "protection alpha invalide")
    height, width = shape
    cross_x, cross_y = cross
    x = np.abs(np.arange(width, dtype=np.float32) + 0.5 - float(cross_x))
    y = np.abs(np.arange(height, dtype=np.float32) + 0.5 - float(cross_y))
    distance = np.minimum(y[:, None], x[None, :])
    progress = np.maximum(distance - float(protected), 0.0) / float(transition)
    return 1.0 - spline.smoothstep(progress)


def axis_rgb_weight(shape: tuple[int, int], cross: tuple[int, int], *,
                    depth: int, strength: float = 1.0) -> np.ndarray:
    require(depth > 0 and 0 < strength <= 1, "profondeur/intensité RGB invalide")
    height, width = shape
    cross_x, cross_y = cross
    x = np.abs(np.arange(width, dtype=np.float32) + 0.5 - float(cross_x))
    y = np.abs(np.arange(height, dtype=np.float32) + 0.5 - float(cross_y))
    distance = np.minimum(y[:, None], x[None, :])
    return (1.0 - spline.smoothstep(distance / float(depth))) * float(strength)


def alpha_weighted_gaussian_rgb(raw: np.ndarray, sigma: float) -> np.ndarray:
    require(sigma > 0, "sigma RGB invalide")
    alpha = raw[:, :, 3].astype(np.float32) / 255.0
    denominator = ndimage.gaussian_filter(alpha, sigma=sigma, mode="nearest")
    result = raw[:, :, :3].astype(np.float32).copy()
    for channel in range(3):
        premultiplied = raw[:, :, channel].astype(np.float32) * alpha
        numerator = ndimage.gaussian_filter(premultiplied, sigma=sigma, mode="nearest")
        np.divide(numerator, denominator, out=result[:, :, channel], where=denominator > 1e-6)
    return np.clip(result, 0.0, 255.0)


def seam_metric(raw: np.ndarray, cross: tuple[int, int], alpha_threshold: int) -> dict[str, Any]:
    cross_x, cross_y = cross
    alpha = raw[:, :, 3]
    vertical_valid = ((alpha[:, cross_x - 1] >= alpha_threshold)
                      & (alpha[:, cross_x] >= alpha_threshold))
    horizontal_valid = ((alpha[cross_y - 1, :] >= alpha_threshold)
                        & (alpha[cross_y, :] >= alpha_threshold))

    def measure(left: np.ndarray, right: np.ndarray, valid: np.ndarray) -> tuple[int, float, float]:
        if not valid.any():
            return 0, 0.0, 0.0
        delta = np.abs(left[valid, :3].astype(np.int16) - right[valid, :3].astype(np.int16))
        per_pixel = delta.mean(axis=1)
        return int(valid.sum()), round(float(per_pixel.mean()), 6), round(float(np.percentile(per_pixel, 95)), 6)

    v_count, v_mae, v_p95 = measure(raw[:, cross_x - 1], raw[:, cross_x], vertical_valid)
    h_count, h_mae, h_p95 = measure(raw[cross_y - 1, :], raw[cross_y, :], horizontal_valid)
    return {
        "vertical_paired_pixels": v_count,
        "vertical_rgb_mae": v_mae,
        "vertical_rgb_p95": v_p95,
        "horizontal_paired_pixels": h_count,
        "horizontal_rgb_mae": h_mae,
        "horizontal_rgb_p95": h_p95,
    }


def repair_canvas(raw: np.ndarray, cross: tuple[int, int], *, threshold: int,
                  fit_error: float, spacing: float, supersample: int, padding: int,
                  inner_feather: int, alpha_protected: int, alpha_transition: int,
                  rgb_sigma: float, rgb_depth: int,
                  rgb_strength: float = 1.0) -> tuple[np.ndarray, dict[str, Any]]:
    source_alpha = raw[:, :, 3]
    fitted_alpha, spline_report = spline.spline_alpha(
        source_alpha,
        threshold=threshold,
        fit_error=fit_error,
        spacing=spacing,
        supersample=supersample,
        padding=padding,
        inner_feather=inner_feather,
        protected_core=0,
    )
    restore = axis_restore_weight(
        source_alpha.shape, cross, protected=alpha_protected, transition=alpha_transition
    )
    final_alpha = np.rint(
        fitted_alpha.astype(np.float32) * (1.0 - restore)
        + source_alpha.astype(np.float32) * restore
    ).astype(np.uint8)
    final_alpha = np.minimum(final_alpha, source_alpha)

    rgb_weight = axis_rgb_weight(
        source_alpha.shape, cross, depth=rgb_depth, strength=rgb_strength
    )
    rgb_weight *= source_alpha > 0
    smooth_rgb = alpha_weighted_gaussian_rgb(raw, rgb_sigma)
    result = raw.copy()
    result[:, :, :3] = np.rint(
        raw[:, :, :3].astype(np.float32) * (1.0 - rgb_weight[:, :, None])
        + smooth_rgb * rgb_weight[:, :, None]
    ).astype(np.uint8)
    result[:, :, 3] = final_alpha

    outside_rgb = rgb_weight == 0
    require(np.array_equal(result[:, :, :3][outside_rgb], raw[:, :, :3][outside_rgb]),
            "RGB modifié hors bande de croix")
    require(np.all(result[:, :, 3] <= source_alpha), "alpha finale supérieure à la source")
    return result, {
        "spline": spline_report,
        "alpha_restored_pixels": int(((final_alpha > fitted_alpha) & (source_alpha > 0)).sum()),
        "alpha_changed_pixels": int((final_alpha != source_alpha).sum()),
        "rgb_changed_pixels": int(np.any(result[:, :, :3] != raw[:, :, :3], axis=2).sum()),
        "before": seam_metric(raw, cross, 128),
        "after": seam_metric(result, cross, 128),
    }


def split_canvas(canvas: np.ndarray, placements: list[Placement], cross: tuple[int, int]) -> dict[int, np.ndarray]:
    left, top = -cross[0], -cross[1]
    output: dict[int, np.ndarray] = {}
    for item in placements:
        x, y = item.origin_x - left, item.origin_y - top
        pixels = canvas[y:y + item.height, x:x + item.width].copy()
        require(pixels.shape == (item.height, item.width, 4), "découpe quadrant invalide")
        output[int(item.frame["frame"])] = pixels
    return output


def checkerboard_rgba(raw: np.ndarray) -> Image.Image:
    image = Image.fromarray(raw, "RGBA")
    background = runtime.checkerboard(image.size).convert("RGBA")
    return Image.alpha_composite(background, image).convert("RGB")


def review_pair(before: np.ndarray, after: np.ndarray, cross: tuple[int, int], label: str) -> Image.Image:
    radius = 240
    cross_x, cross_y = cross
    left, top = max(0, cross_x - radius), max(0, cross_y - radius)
    right, bottom = min(before.shape[1], cross_x + radius), min(before.shape[0], cross_y + radius)
    views = [checkerboard_rgba(item[top:bottom, left:right]) for item in (before, after)]
    target_height = 360
    resized = []
    for image in views:
        scale = target_height / image.height
        resized.append(image.resize((round(image.width * scale), target_height), Image.Resampling.LANCZOS))
    gap, label_height = 12, 22
    canvas = Image.new("RGB", (sum(item.width for item in resized) + gap,
                               target_height + label_height), (25, 25, 25))
    draw = ImageDraw.Draw(canvas)
    draw.text((4, 4), f"{label} — avant / après", fill="white")
    canvas.paste(resized[0], (0, label_height))
    canvas.paste(resized[1], (resized[0].width + gap, label_height))
    return canvas


def write_review(root: Path, resref: str, pairs: list[tuple[np.ndarray, np.ndarray, tuple[int, int]]],
                 ffmpeg: str) -> list[dict[str, str]]:
    review_root = root / "review"
    frames_root = review_root / f"{resref}-comparison-frames"
    frames_root.mkdir(parents=True)
    rows: list[Image.Image] = []
    sample_phases = set(np.linspace(0, len(pairs) - 1, min(4, len(pairs)), dtype=int))
    for phase, (before, after, cross) in enumerate(pairs):
        paired = review_pair(before, after, cross, f"{resref} phase {phase:02d}")
        paired.save(frames_root / f"frame_{phase:04d}.png")
        if phase in sample_phases:
            rows.append(paired)
    contact = Image.new("RGB", (max(item.width for item in rows), sum(item.height for item in rows)), "black")
    cursor = 0
    for row in rows:
        contact.paste(row, (0, cursor))
        cursor += row.height
    contact_path = review_root / f"{resref}-cross-seam-contact-sheet.png"
    contact.save(contact_path, optimize=True)
    exact = review_root / f"{resref}-cross-seam-30fps-exact.mp4"
    loop = review_root / f"{resref}-cross-seam-30fps-loop-4s.mp4"
    runtime.run_checked([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-i", str(frames_root / "frame_%04d.png"),
        "-frames:v", str(len(pairs)), "-c:v", "libx264", "-preset", "slow",
        "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(exact),
    ])
    runtime.run_checked([
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(exact), "-t", "4", "-c:v", "libx264",
        "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(loop),
    ])
    return [
        {"resref": resref, "kind": "comparison-contact-sheet",
         "file": contact_path.relative_to(root).as_posix(), "sha256": runtime.sha256_file(contact_path)},
        {"resref": resref, "kind": "comparison-exact",
         "file": exact.relative_to(root).as_posix(), "sha256": runtime.sha256_file(exact)},
        {"resref": resref, "kind": "comparison-loop-4s",
         "file": loop.relative_to(root).as_posix(), "sha256": runtime.sha256_file(loop)},
    ]


def update_pack_inventory(pack_root: Path, manifest: dict[str, Any], resources: list[dict[str, Any]],
                          target_names: set[str]) -> None:
    current_frames = {str(frame["asset"]): frame for resource in resources for frame in resource["frames"]}
    for resource in resources:
        resource["assets"] = [
            {"name": str(frame["asset"]), "sha256": str(frame["sha256"]), "bytes": int(frame["bytes"])}
            for frame in sorted_frames(resource)
        ]
    original_base = {str(item["name"]): item for item in manifest.get("base_assets") or []}
    original_new = {str(item["name"]): item for item in manifest.get("new_assets") or []}
    original_replacements = {
        str(item["name"]): item for item in manifest.get("replacement_assets") or []
    }
    require(target_names <= set(current_frames), "assets cible absents du pack")
    manifest["resources"] = resources
    manifest["resource_count"] = len(resources)
    manifest["frame_count"] = sum(int(item["frame_count"]) for item in resources)
    manifest["base_assets"] = [
        {"name": name, "sha256": current_frames[name]["sha256"], "bytes": current_frames[name]["bytes"]}
        for name in sorted(set(original_base) - target_names)
    ]
    manifest["new_assets"] = [
        {"name": name, "sha256": current_frames[name]["sha256"], "bytes": current_frames[name]["bytes"]}
        for name in sorted(original_new)
    ]
    manifest["replacement_assets"] = [
        original_replacements[name]
        for name in sorted(set(original_replacements) - target_names)
    ] + [
        {"name": name, "sha256": current_frames[name]["sha256"], "bytes": current_frames[name]["bytes"],
         "expected_base_sha256": original_base[name]["sha256"],
         "expected_base_bytes": original_base[name]["bytes"]}
        for name in sorted(target_names & set(original_base))
    ] + [
        {**original_replacements[name], "sha256": current_frames[name]["sha256"],
         "bytes": current_frames[name]["bytes"]}
        for name in sorted(target_names & set(original_replacements))
    ]
    registry = runtime.registry_v2_from_resources(resources, int(manifest["registry_version"]))
    registry_path = pack_root / runtime.REGISTRY_NAME
    registry_path.write_bytes(registry)
    manifest["registry_sha256"] = runtime.sha256_file(registry_path)
    manifest["registry_bytes"] = len(registry)
    manifest["raw_bytes"] = sum(int(asset["bytes"]) for item in resources for asset in item["assets"])


def build(source_run: Path, output: Path, resrefs: list[str], *, threshold: int,
          fit_error: float, spacing: float, supersample: int, padding: int,
          inner_feather: int, alpha_protected: int, alpha_transition: int,
          rgb_sigma: float, rgb_depth: int, rgb_strength: float,
          review_ffmpeg: str) -> dict[str, Any]:
    source_run = source_run.resolve()
    output = output.resolve()
    partial = output.with_name(output.name + ".partial")
    require(not output.exists() and not partial.exists(), f"sortie déjà présente : {output}")
    source_manifest = runtime.validate_run(source_run)
    source_pack = source_run / "03_runtime_pack"
    source_pack_manifest, source_resources = runtime.validate_v2_pack(source_pack)
    selected = [runtime.normalise_resref(value) for value in resrefs]
    require(selected and len(selected) == len(set(selected)), "resrefs invalides ou dupliqués")
    available = {str(item["resref"]): item for item in source_resources}
    require(set(selected) <= set(available), "resref absent du run source")

    partial.mkdir(parents=True)
    pack_root = partial / "03_runtime_pack"
    shutil.copytree(source_pack, pack_root, ignore=shutil.ignore_patterns("install-backups"))
    pack_manifest = copy.deepcopy(source_pack_manifest)
    resources = copy.deepcopy(source_resources)
    target_names: set[str] = set()
    reports: list[dict[str, Any]] = []
    reviews: list[dict[str, str]] = []
    parameters = {
        "threshold": threshold,
        "fit_error_x4": fit_error,
        "sample_spacing_x4": spacing,
        "raster_supersample": supersample,
        "padding_x4": padding,
        "inner_feather_x4": inner_feather,
        "alpha_axis_protected_x4": alpha_protected,
        "alpha_axis_transition_x4": alpha_transition,
        "rgb_gaussian_sigma_x4": rgb_sigma,
        "rgb_axis_depth_x4": rgb_depth,
        "rgb_blend_strength": rgb_strength,
        "geometry_policy": "byte-identical",
        "alpha_policy": "joint-spline-outer-contour-with-source-restore-on-both-internal-axes",
        "rgb_policy": "single-2d-alpha-weighted-gaussian-confined-to-both-internal-axes",
    }
    for resource in resources:
        resref = str(resource["resref"])
        if resref not in selected:
            continue
        frames, phases = validate_quadrants(resource)
        by_index = {int(frame["frame"]): frame for frame in frames}
        outputs: dict[int, np.ndarray] = {}
        review_pairs: list[tuple[np.ndarray, np.ndarray, tuple[int, int]]] = []
        phase_reports: list[dict[str, Any]] = []
        for phase, indices in enumerate(phases):
            before, placements, cross = reconstruct(source_pack, by_index, indices)
            after, phase_report = repair_canvas(
                before, cross,
                threshold=threshold,
                fit_error=fit_error,
                spacing=spacing,
                supersample=supersample,
                padding=padding,
                inner_feather=inner_feather,
                alpha_protected=alpha_protected,
                alpha_transition=alpha_transition,
                rgb_sigma=rgb_sigma,
                rgb_depth=rgb_depth,
                rgb_strength=rgb_strength,
            )
            outputs.update(split_canvas(after, placements, cross))
            review_pairs.append((before, after, cross))
            phase_reports.append({"phase": phase, "frame_indices": indices,
                                  "cross_x4": list(cross), **phase_report})
        require(set(outputs) == set(by_index), f"{resref}: frames de sortie incomplètes")
        for frame in frames:
            pixels = outputs[int(frame["frame"])]
            path = pack_root / str(frame["asset"])
            path.write_bytes(pixels.tobytes(order="C"))
            frame["bytes"] = path.stat().st_size
            frame["sha256"] = runtime.sha256_file(path)
            target_names.add(str(frame["asset"]))
        reports.append({"resref": resref, "phases": phase_reports})
        reviews.extend(write_review(partial, resref, review_pairs, review_ffmpeg))

    update_pack_inventory(pack_root, pack_manifest, resources, target_names)
    pack_manifest["created_utc"] = runtime.utc_now()
    pack_manifest["cross_cycle_seam_repair"] = {
        "schema": SCHEMA,
        "pipeline_name": PIPELINE_NAME,
        "source_run": source_run.as_posix(),
        "source_run_manifest_sha256": runtime.sha256_file(source_run / "manifest.json"),
        "asset_ids": [f"animations:bam:{value}" for value in selected],
        "parameters": parameters,
        "reports": reports,
    }
    runtime.write_json(pack_root / "manifest.json", pack_manifest)
    runtime.validate_v2_pack(pack_root)

    report_path = partial / "cross-cycle-seam-report.json"
    report = {
        "schema": SCHEMA,
        "status": "completed-pending-qa",
        "pipeline_name": PIPELINE_NAME,
        "asset_ids": [f"animations:bam:{value}" for value in selected],
        "source_run": source_run.as_posix(),
        "source_run_manifest_sha256": runtime.sha256_file(source_run / "manifest.json"),
        "parameters": parameters,
        "resources": reports,
        "installation": "not performed",
    }
    runtime.write_json(report_path, report)
    manifest = {
        "schema": runtime.RUN_SCHEMA,
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "input_mode": "four-cycle-joint-canvas-cross-seam-repair",
        "asset_ids": [f"animations:bam:{value}" for value in selected],
        "source_run": source_run.as_posix(),
        "source_run_manifest_sha256": runtime.sha256_file(source_run / "manifest.json"),
        "base_pack": source_manifest["base_pack"],
        "base_pack_manifest_sha256": source_manifest["base_pack_manifest_sha256"],
        "native_fps": source_manifest["native_fps"],
        "target_fps": source_manifest["target_fps"],
        "timed_resources": source_manifest["timed_resources"],
        "pack": "03_runtime_pack",
        "pack_manifest_sha256": runtime.sha256_file(pack_root / "manifest.json"),
        "registry_sha256": pack_manifest["registry_sha256"],
        "reviews": reviews,
        "qa_status": "pending-explicit-user-approval",
        "cross_cycle_seam_repair": {
            "pipeline_name": PIPELINE_NAME,
            "report": report_path.name,
            "report_sha256": runtime.sha256_file(report_path),
            "installation": "not performed",
        },
    }
    runtime.write_json(partial / "manifest.json", manifest)
    runtime.validate_run(partial)
    partial.replace(output)
    return manifest


def inspect(source_run: Path, output: Path, resrefs: list[str], parameters: dict[str, Any]) -> dict[str, Any]:
    source_run = source_run.resolve()
    manifest = runtime.validate_run(source_run)
    _pack_manifest, resources = runtime.validate_v2_pack(source_run / "03_runtime_pack")
    selected = [runtime.normalise_resref(value) for value in resrefs]
    available = {str(item["resref"]): item for item in resources}
    require(set(selected) <= set(available), "resref absent du run source")
    phase_counts = {}
    for resref in selected:
        _frames, phases = validate_quadrants(available[resref])
        phase_counts[resref] = len(phases)
    return {
        "schema": SCHEMA,
        "status": "planned",
        "pipeline_name": PIPELINE_NAME,
        "asset_ids": [f"animations:bam:{value}" for value in selected],
        "source_run": source_run.as_posix(),
        "source_run_manifest_sha256": runtime.sha256_file(source_run / "manifest.json"),
        "source_pack_manifest_sha256": manifest["pack_manifest_sha256"],
        "output": output.resolve().as_posix(),
        "phase_counts": phase_counts,
        "parameters": parameters,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", type=Path, required=True)
    parser.add_argument("--resref", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--threshold", type=int, default=127)
    parser.add_argument("--fit-error", type=float, default=1.0)
    parser.add_argument("--sample-spacing", type=float, default=1.5)
    parser.add_argument("--supersample", type=int, default=4)
    parser.add_argument("--padding", type=int, default=32)
    parser.add_argument("--inner-feather", type=int, default=4)
    parser.add_argument("--alpha-protected", type=int, default=8)
    parser.add_argument("--alpha-transition", type=int, default=16)
    parser.add_argument("--rgb-sigma", type=float, default=4.0)
    parser.add_argument("--rgb-depth", type=int, default=32)
    parser.add_argument("--rgb-strength", type=float, default=1.0)
    parser.add_argument("--review-ffmpeg", default="ffmpeg")
    parser.add_argument("--run", action="store_true", help="écrire le run ; sinon plan seul")
    args = parser.parse_args(argv)
    parameters = {
        "threshold": args.threshold,
        "fit_error_x4": args.fit_error,
        "sample_spacing_x4": args.sample_spacing,
        "raster_supersample": args.supersample,
        "padding_x4": args.padding,
        "inner_feather_x4": args.inner_feather,
        "alpha_axis_protected_x4": args.alpha_protected,
        "alpha_axis_transition_x4": args.alpha_transition,
        "rgb_gaussian_sigma_x4": args.rgb_sigma,
        "rgb_axis_depth_x4": args.rgb_depth,
        "rgb_blend_strength": args.rgb_strength,
        "geometry_policy": "byte-identical",
        "alpha_policy": "joint-spline-outer-contour-with-source-restore-on-both-internal-axes",
        "rgb_policy": "single-2d-alpha-weighted-gaussian-confined-to-both-internal-axes",
    }
    if args.run:
        result = build(
            args.source_run, args.output, args.resref,
            threshold=args.threshold,
            fit_error=args.fit_error,
            spacing=args.sample_spacing,
            supersample=args.supersample,
            padding=args.padding,
            inner_feather=args.inner_feather,
            alpha_protected=args.alpha_protected,
            alpha_transition=args.alpha_transition,
            rgb_sigma=args.rgb_sigma,
            rgb_depth=args.rgb_depth,
            rgb_strength=args.rgb_strength,
            review_ffmpeg=args.review_ffmpeg,
        )
    else:
        result = inspect(args.source_run, args.output, args.resref, parameters)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
