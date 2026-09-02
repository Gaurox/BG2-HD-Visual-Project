"""Build a reversible per-frame multi-contour spline alpha variant for one V2 run.

Unlike build_manual_alpha_mask_30fps_v2.py, this tool supports variable frame
geometry. It fits every connected alpha component independently after transparent
padding, keeps empty phases empty, applies an optional inner feather, and
premultiplies RGB because the target is an ARE Blended resource.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage
from scipy.interpolate import splprep, splev

import run_animation_upscale_30fps_v2 as temporal
import animation_paths


SCHEMA = "bg2-upscale-area-animation-per-frame-spline-alpha-v1"
PIPELINE_NAME = "spline-fit1-multicontour-per-frame-feather4"
CORE_GUARD_16_PIPELINE_NAME = "spline-fit1-multicontour-core-guard16"
OVAL_EDGE_FADE_20X6_EFFECT = "oval-edge-fade20x6"
TIMELINE_GLOBAL_FADE_70_EFFECT = "timeline-global-fade70"
TIMELINE_ACTIVE_FADE_7_20_7_EFFECT = "timeline-active-fade7-20-7"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resample_closed(points: np.ndarray, spacing: float) -> np.ndarray:
    loop = np.vstack((points, points[0]))
    distances = np.hypot(np.diff(loop[:, 0]), np.diff(loop[:, 1]))
    cumulative = np.concatenate(([0.0], np.cumsum(distances)))
    positions = np.arange(0.0, cumulative[-1], spacing)
    if len(positions) < 4:
        return points
    return np.column_stack((
        np.interp(positions, cumulative, loop[:, 0]),
        np.interp(positions, cumulative, loop[:, 1]),
    ))


def smoothstep(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(values, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def fit_component(component: np.ndarray, fit_error: float, spacing: float,
                  supersample: int) -> tuple[np.ndarray, dict[str, int | str]]:
    """Fit the outer contour of one padded connected component."""
    paths = plt.contour(component.astype(np.uint8), levels=[0.5]).get_paths()
    plt.close()
    if not paths:
        return component.astype(np.uint8) * 255, {"status": "preserved-no-contour"}
    contour = max((path.vertices for path in paths), key=len)
    if np.allclose(contour[0], contour[-1]):
        contour = contour[:-1]
    samples = resample_closed(contour, spacing)
    if len(samples) < 4:
        return component.astype(np.uint8) * 255, {"status": "preserved-short-contour"}
    tck, _ = splprep(
        [samples[:, 0], samples[:, 1]],
        s=len(samples) * fit_error ** 2,
        per=True,
        k=3,
    )
    curve = np.asarray(
        splev(np.linspace(0.0, 1.0, len(samples) * 3, endpoint=False), tck)
    ).T
    height, width = component.shape
    high = Image.new("L", (width * supersample, height * supersample), 0)
    ImageDraw.Draw(high).polygon(
        [tuple(point * supersample) for point in curve], fill=255
    )
    result = np.asarray(
        high.resize((width, height), Image.Resampling.LANCZOS), dtype=np.uint8
    )
    return result, {
        "status": "fitted",
        "input_vertices": int(len(contour)),
        "fit_samples": int(len(samples)),
        "curve_points": int(len(curve)),
    }


def spline_alpha(alpha: np.ndarray, *, threshold: int, fit_error: float,
                 spacing: float, supersample: int, padding: int,
                 inner_feather: int, protected_core: int) -> tuple[np.ndarray, dict[str, Any]]:
    """Return an alpha that never exceeds the input alpha and preserves islands."""
    source = alpha.astype(np.uint8, copy=False)
    binary = source > threshold
    if not binary.any():
        return source.copy(), {
            "source_nonzero": 0,
            "components": 0,
            "touches_canvas_edge": False,
            "intermediate_alpha_pixels": 0,
            "status": "empty-preserved",
        }

    touches_edge = bool(
        binary[0, :].any() or binary[-1, :].any() or
        binary[:, 0].any() or binary[:, -1].any()
    )
    padded = np.pad(binary, padding, mode="constant")
    labels, component_count = ndimage.label(
        padded, structure=np.ones((3, 3), dtype=np.uint8)
    )
    spline = np.zeros_like(padded, dtype=np.uint8)
    component_reports: list[dict[str, int | str]] = []
    for label in range(1, int(component_count) + 1):
        component_mask = labels == label
        fitted, component_report = fit_component(
            component_mask, fit_error, spacing, supersample
        )
        spline = np.maximum(spline, fitted)
        component_reports.append(component_report)
    spline = spline[padding:-padding, padding:-padding]

    result = np.rint(source.astype(np.float32) * spline.astype(np.float32) / 255.0)
    if inner_feather:
        distance = ndimage.distance_transform_edt(spline > threshold)
        feather = smoothstep((distance - 1.0) / float(inner_feather))
        result *= feather
    output = np.rint(result).astype(np.uint8)
    protected_core_pixels = 0
    if protected_core:
        source_distance = ndimage.distance_transform_edt(binary)
        protected = source_distance >= float(protected_core)
        protected_core_pixels = int(protected.sum())
        output[protected] = source[protected]
    require(np.all(output <= source), "la spline augmente l'alpha source")
    return output, {
        "source_nonzero": int((source > 0).sum()),
        "components": int(component_count),
        "touches_canvas_edge": touches_edge,
        "intermediate_alpha_pixels": int(((output > 0) & (output < 255)).sum()),
        "protected_source_core_x4": protected_core,
        "protected_source_core_pixels": protected_core_pixels,
        "status": "fitted",
        "component_reports": component_reports,
    }


def oval_edge_fade(alpha: np.ndarray, *, top_bottom_fade: int,
                   side_fade: int) -> tuple[np.ndarray, dict[str, int | str]]:
    """Apply a rounded elliptical canvas-edge taper without raising alpha.

    The outer ellipse meets the canvas edges.  The inner ellipse is inset more
    on Y than X, so top/bottom fade first while side fading stays subtle.
    """
    source = alpha.astype(np.uint8, copy=False)
    if top_bottom_fade == 0 and side_fade == 0:
        return source.copy(), {"status": "disabled", "attenuated_pixels": 0}
    height, width = source.shape
    outer_x = (width - 1) / 2.0
    outer_y = (height - 1) / 2.0
    require(0 <= side_fade < outer_x and 0 <= top_bottom_fade < outer_y,
            "fade ovale incompatible avec les dimensions de frame")
    x, y = np.meshgrid(np.arange(width, dtype=np.float32),
                       np.arange(height, dtype=np.float32))
    x -= outer_x
    y -= outer_y
    inner_x = outer_x - float(side_fade)
    inner_y = outer_y - float(top_bottom_fade)
    outer_metric = np.sqrt((x / outer_x) ** 2 + (y / outer_y) ** 2)
    inner_metric = np.sqrt((x / inner_x) ** 2 + (y / inner_y) ** 2)
    denominator = inner_metric - outer_metric
    factor = np.ones_like(outer_metric, dtype=np.float32)
    np.divide(1.0 - outer_metric, denominator, out=factor,
              where=denominator > 1e-6)
    factor = smoothstep(factor)
    output = np.rint(source.astype(np.float32) * factor).astype(np.uint8)
    require(np.all(output <= source), "le fade ovale augmente l'alpha source")
    return output, {
        "status": "applied",
        "top_bottom_fade_x4": top_bottom_fade,
        "side_fade_x4": side_fade,
        "attenuated_pixels": int(((output < source) & (source > 0)).sum()),
    }


def premultiply_rgb(raw: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    result = raw.copy()
    result[:, :, :3] = np.rint(
        raw[:, :, :3].astype(np.float32) * alpha[:, :, None] / 255.0
    ).astype(np.uint8)
    result[:, :, 3] = alpha
    return result


def apply_timeline_global_fade(pack_root: Path, resource: dict[str, Any], *,
                               hold_ratio: float) -> dict[str, Any]:
    """Clone timeline phases so repeated frames can carry phase-specific alpha."""
    if hold_ratio == 1.0:
        return {"status": "disabled", "hold_ratio": hold_ratio}
    cycles = sorted(resource["cycles"], key=lambda item: int(item["cycle"]))
    require(len(cycles) == 1, "fade global : multi-cycle non supporté")
    cycle = cycles[0]
    timeline = [int(value) for value in cycle["timeline_frame_indices"]]
    require(len(timeline) >= 2, "fade global : timeline trop courte")
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    by_index = {int(frame["frame"]): frame for frame in frames}
    require(len(by_index) == len(frames) and all(index in by_index for index in timeline),
            "fade global : frames/timeline incompatibles")
    phase_count = len(timeline)
    fade_span = (phase_count - 1) * (1.0 - hold_ratio) / 2.0
    require(fade_span > 0.0, "fade global : durée de fade nulle")
    phases = np.arange(phase_count, dtype=np.float32)
    ramps = np.minimum(phases / fade_span, (phase_count - 1 - phases) / fade_span)
    weights = smoothstep(ramps)
    first_clone_index = max(by_index) + 1
    clones: list[dict[str, Any]] = []
    for phase, source_index in enumerate(timeline):
        source_frame = by_index[source_index]
        width, height = (int(value) for value in source_frame["physical_size_x4"])
        source_path = pack_root / str(source_frame["asset"])
        raw = np.frombuffer(source_path.read_bytes(), dtype=np.uint8).reshape(height, width, 4)
        faded = np.rint(raw.astype(np.float32) * float(weights[phase])).astype(np.uint8)
        clone = copy.deepcopy(source_frame)
        clone_index = first_clone_index + phase
        clone_name = temporal.asset_name(
            str(resource["resref"]), clone_index, int(resource.get("variant_index", 0))
        )
        clone_path = pack_root / clone_name
        clone_path.write_bytes(faded.tobytes())
        clone.update({
            "frame": clone_index,
            "asset": clone_name,
            "sha256": sha256_file(clone_path),
            "bytes": clone_path.stat().st_size,
            "timeline_global_fade_phase": phase,
            "timeline_global_fade_weight": float(weights[phase]),
            "review_source_asset": str(source_frame["asset"]),
        })
        clones.append(clone)
    resource["frames"] = frames + clones
    resource["frame_count"] = len(resource["frames"])
    cycle["timeline_frame_indices"] = [int(frame["frame"]) for frame in clones]
    full = np.flatnonzero(weights >= 1.0 - 1e-6)
    return {
        "status": "applied",
        "curve": "smoothstep",
        "hold_ratio": hold_ratio,
        "phase_count": phase_count,
        "fade_span_phases": fade_span,
        "full_opacity_phase_first": int(full[0]),
        "full_opacity_phase_last": int(full[-1]),
        "clone_frame_count": len(clones),
    }


def apply_timeline_active_fade(pack_root: Path, resource: dict[str, Any], *,
                               fade_in: int, full: int, fade_out: int) -> dict[str, Any]:
    """Fade only the contiguous non-empty interval of a one-cycle timeline."""
    if fade_in == full == fade_out == 0:
        return {"status": "disabled"}
    require(fade_in > 0 and full > 0 and fade_out > 0,
            "fade actif : segments incomplets")
    cycles = sorted(resource["cycles"], key=lambda item: int(item["cycle"]))
    require(len(cycles) == 1, "fade actif : multi-cycle non supporté")
    cycle = cycles[0]
    timeline = [int(value) for value in cycle["timeline_frame_indices"]]
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    by_index = {int(frame["frame"]): frame for frame in frames}
    require(len(by_index) == len(frames) and all(index in by_index for index in timeline),
            "fade actif : frames/timeline incompatibles")
    nonempty: list[int] = []
    for phase, frame_index in enumerate(timeline):
        frame = by_index[frame_index]
        width, height = (int(value) for value in frame["physical_size_x4"])
        alpha = np.frombuffer((pack_root / str(frame["asset"])).read_bytes(), dtype=np.uint8)
        if alpha.reshape(height, width, 4)[:, :, 3].any():
            nonempty.append(phase)
    require(nonempty, "fade actif : aucune phase non vide")
    first, last = nonempty[0], nonempty[-1]
    require(nonempty == list(range(first, last + 1)),
            "fade actif : phases non vides non contiguës")
    active_count = last - first + 1
    require(active_count == fade_in + full + fade_out,
            f"fade actif : {active_count} phases non vides, attendu {fade_in + full + fade_out}")
    first_clone_index = max(by_index) + 1
    clones: list[dict[str, Any]] = []
    updated_timeline = timeline.copy()
    for ordinal, phase in enumerate(range(first, last + 1)):
        if ordinal < fade_in:
            weight = float(smoothstep(np.array([ordinal / fade_in], dtype=np.float32))[0])
        elif ordinal < fade_in + full:
            continue
        else:
            weight = float(smoothstep(np.array([(active_count - 1 - ordinal) / fade_out],
                                               dtype=np.float32))[0])
        source_frame = by_index[timeline[phase]]
        width, height = (int(value) for value in source_frame["physical_size_x4"])
        raw = np.frombuffer((pack_root / str(source_frame["asset"])).read_bytes(),
                            dtype=np.uint8).reshape(height, width, 4)
        faded = np.rint(raw.astype(np.float32) * weight).astype(np.uint8)
        clone = copy.deepcopy(source_frame)
        clone_index = first_clone_index + len(clones)
        clone_name = temporal.asset_name(
            str(resource["resref"]), clone_index, int(resource.get("variant_index", 0))
        )
        clone_path = pack_root / clone_name
        clone_path.write_bytes(faded.tobytes())
        clone.update({
            "frame": clone_index,
            "asset": clone_name,
            "sha256": sha256_file(clone_path),
            "bytes": clone_path.stat().st_size,
            "timeline_active_fade_phase": phase,
            "timeline_active_fade_weight": weight,
            "review_source_asset": str(source_frame["asset"]),
        })
        clones.append(clone)
        updated_timeline[phase] = clone_index
    resource["frames"] = frames + clones
    resource["frame_count"] = len(resource["frames"])
    cycle["timeline_frame_indices"] = updated_timeline
    return {
        "status": "applied",
        "curve": "smoothstep",
        "first_nonempty_phase": first,
        "last_nonempty_phase": last,
        "segments": {"fade_in": fade_in, "full": full, "fade_out": fade_out},
        "clone_frame_count": len(clones),
    }


def alignment_bounds(frames: list[dict[str, Any]]) -> tuple[tuple[int, int], list[tuple[int, int]]]:
    centres = [tuple(int(value) * 4 for value in frame["centre_x1"]) for frame in frames]
    sizes = [tuple(int(value) for value in frame["physical_size_x4"]) for frame in frames]
    left = max(x for x, _ in centres)
    top = max(y for _, y in centres)
    right = max(width - x for (x, _), (width, _) in zip(centres, sizes, strict=True))
    bottom = max(height - y for (_, y), (_, height) in zip(centres, sizes, strict=True))
    return (left + right, top + bottom), [(left - x, top - y) for x, y in centres]


def preview(raw_path: Path, physical_size: list[int], offset: tuple[int, int],
            canvas_size: tuple[int, int]) -> Image.Image:
    sprite = temporal.rgba_from_raw(raw_path, physical_size)
    canvas = Image.new("RGBA", canvas_size, (0, 0, 0, 0))
    canvas.alpha_composite(sprite, offset)
    return Image.alpha_composite(
        temporal.checkerboard(canvas_size).convert("RGBA"), canvas
    ).convert("RGB")


def add_label(image: Image.Image, label: str) -> Image.Image:
    labelled = Image.new("RGB", (image.width, image.height + 18), "black")
    labelled.paste(image, (0, 18))
    ImageDraw.Draw(labelled).text((4, 3), label, fill="white")
    return labelled


def render_reviews(source_pack: Path, output_pack: Path, resource: dict[str, Any],
                   work_root: Path, review_ffmpeg: str) -> list[dict[str, str]]:
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    by_index = {int(frame["frame"]): frame for frame in frames}
    cycles = sorted(resource["cycles"], key=lambda item: int(item["cycle"]))
    require(len(cycles) == 1, "review spline : multi-cycle non supporté")
    timeline = [int(value) for value in cycles[0]["timeline_frame_indices"]]
    canvas_size, offsets = alignment_bounds(frames)
    offset_by_index = {
        int(frame["frame"]): offset for frame, offset in zip(frames, offsets, strict=True)
    }
    review_frames = work_root / "comparison_frames"
    review_frames.mkdir(parents=True)
    samples: list[Image.Image] = []
    sample_positions = set(np.linspace(0, len(timeline) - 1, min(6, len(timeline)), dtype=int))
    for phase, frame_index in enumerate(timeline):
        frame = by_index[frame_index]
        before = preview(source_pack / str(frame.get("review_source_asset", frame["asset"])), frame["physical_size_x4"],
                         offset_by_index[frame_index], canvas_size)
        after = preview(output_pack / str(frame["asset"]), frame["physical_size_x4"],
                        offset_by_index[frame_index], canvas_size)
        paired = Image.new("RGB", (before.width * 2, before.height), "black")
        paired.paste(before, (0, 0))
        paired.paste(after, (before.width, 0))
        paired = add_label(paired, f"phase {phase:02d} — avant (gauche) / spline fit 1 + feather (droite)")
        paired.save(review_frames / f"frame_{phase:04d}.png")
        if phase in sample_positions:
            samples.append(paired)
    contact = Image.new("RGB", (max(image.width for image in samples),
                                  sum(image.height for image in samples)), "black")
    cursor = 0
    for image in samples:
        contact.paste(image, (0, cursor))
        cursor += image.height
    contact_path = work_root / "review-comparison-contact-sheet.png"
    contact.save(contact_path)
    exact = work_root / "review-comparison-30fps-exact.mp4"
    loop = work_root / "review-comparison-30fps-loop-4s.mp4"
    temporal.run_checked([
        review_ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-i", str(review_frames / "frame_%04d.png"),
        "-frames:v", str(len(timeline)), "-c:v", "libx264", "-preset", "slow",
        "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(exact),
    ])
    temporal.run_checked([
        review_ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(exact), "-t", "4", "-c:v", "libx264",
        "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
        str(loop),
    ])
    require(exact.is_file() and loop.is_file(), "ffmpeg n'a pas produit les reviews spline")
    return [
        {"kind": "comparison-contact-sheet", "file": contact_path.name,
         "sha256": sha256_file(contact_path)},
        {"kind": "comparison-exact", "file": exact.name, "sha256": sha256_file(exact)},
        {"kind": "comparison-loop-4s", "file": loop.name, "sha256": sha256_file(loop)},
    ]


def build(temporal_run: Path, resref: str, output: Path, *, threshold: int,
          fit_error: float, sample_spacing: float, supersample: int, padding: int,
          inner_feather: int, protected_core: int, oval_top_bottom_fade: int,
          oval_side_fade: int, global_fade_hold_ratio: float, active_fade_in: int,
          active_fade_full: int, active_fade_out: int,
          review_ffmpeg: str) -> dict[str, Any]:
    require(not output.exists() and not output.with_name(output.name + ".partial").exists(),
            f"sortie déjà présente : {output}")
    require(fit_error > 0 and sample_spacing > 0 and supersample >= 1 and padding >= 1 and
            inner_feather >= 0 and protected_core >= 0 and oval_top_bottom_fade >= 0 and oval_side_fade >= 0 and
            0 < global_fade_hold_ratio <= 1 and active_fade_in >= 0 and active_fade_full >= 0 and
            active_fade_out >= 0 and 0 <= threshold <= 255, "paramètres spline invalides")
    active_fade_requested = any((active_fade_in, active_fade_full, active_fade_out))
    require(not active_fade_requested or (active_fade_in > 0 and active_fade_full > 0 and active_fade_out > 0),
            "fade actif : fournir les trois segments")
    require(not active_fade_requested or global_fade_hold_ratio == 1.0,
            "fade global et fade actif incompatibles")
    temporal_run = temporal_run.resolve()
    output = output.resolve()
    resref = temporal.normalise_resref(resref)
    pipeline_name = (CORE_GUARD_16_PIPELINE_NAME if protected_core == 16
                     else PIPELINE_NAME)
    pipeline_effects = [PIPELINE_NAME]
    if protected_core == 16:
        pipeline_effects.append(CORE_GUARD_16_PIPELINE_NAME)
    if oval_top_bottom_fade == 20 and oval_side_fade == 6:
        pipeline_effects.append(OVAL_EDGE_FADE_20X6_EFFECT)
    if global_fade_hold_ratio == 0.70:
        pipeline_effects.append(TIMELINE_GLOBAL_FADE_70_EFFECT)
    if (active_fade_in, active_fade_full, active_fade_out) == (7, 20, 7):
        pipeline_effects.append(TIMELINE_ACTIVE_FADE_7_20_7_EFFECT)
    source_manifest = temporal.validate_run(temporal_run)
    require(resref in [temporal.normalise_resref(value) for value in source_manifest["timed_resources"]],
            f"{resref}: absent du run temporel")
    source_pack = temporal_run / "03_runtime_pack"
    source_pack_manifest, source_resources = temporal.validate_v2_pack(source_pack)
    base_pack = Path(str(source_manifest["base_pack"])).resolve()
    base_manifest, base_resources, _sources = temporal.load_base_pack(base_pack)
    require(sha256_file(base_pack / "manifest.json") == source_manifest["base_pack_manifest_sha256"],
            "pack de base du run temporel modifié")
    source_resource = next(item for item in source_resources if item["resref"] == resref)
    base_resource = next(item for item in base_resources if item["resref"] == resref)
    require(source_resource["playback_mode"] == "TimedTimeline" and
            base_resource["playback_mode"] == "Native", f"{resref}: source V2 incompatible")

    partial = output.with_name(output.name + ".partial")
    partial.mkdir(parents=True)
    pack_root = partial / "03_runtime_pack"
    shutil.copytree(source_pack, pack_root, ignore=shutil.ignore_patterns("install-backups"))
    pack_manifest = copy.deepcopy(source_pack_manifest)
    resources = copy.deepcopy(source_resources)
    resource = next(item for item in resources if item["resref"] == resref)
    target_names = {str(frame["asset"]) for frame in resource["frames"]}
    reports: list[dict[str, Any]] = []
    for frame in sorted(resource["frames"], key=lambda item: int(item["frame"])):
        asset_path = pack_root / str(frame["asset"])
        rgba = temporal.rgba_from_raw(asset_path, frame["physical_size_x4"])
        raw = np.asarray(rgba, dtype=np.uint8)
        alpha, report = spline_alpha(
            raw[:, :, 3], threshold=threshold, fit_error=fit_error,
            spacing=sample_spacing, supersample=supersample, padding=padding,
            inner_feather=inner_feather, protected_core=protected_core,
        )
        alpha, oval_report = oval_edge_fade(
            alpha, top_bottom_fade=oval_top_bottom_fade,
            side_fade=oval_side_fade,
        )
        result = premultiply_rgb(raw, alpha)
        asset_path.write_bytes(result.tobytes())
        frame["bytes"] = asset_path.stat().st_size
        frame["sha256"] = sha256_file(asset_path)
        reports.append({
            "frame": int(frame["frame"]), "asset": str(frame["asset"]),
            **report, "oval_edge_fade": oval_report,
        })
    timeline_fade = (apply_timeline_active_fade(
        pack_root, resource, fade_in=active_fade_in, full=active_fade_full,
        fade_out=active_fade_out,
    ) if active_fade_requested else apply_timeline_global_fade(
        pack_root, resource, hold_ratio=global_fade_hold_ratio,
    ))
    for item in resources:
        item["assets"] = [
            {"name": str(frame["asset"]), "sha256": str(frame["sha256"]), "bytes": int(frame["bytes"])}
            for frame in item["frames"]
        ]
    original_base = {str(item["name"]): item for item in source_pack_manifest["base_assets"]}
    original_new = {str(item["name"]): item for item in source_pack_manifest["new_assets"]}
    original_replacements = {
        str(item["name"]): item
        for item in source_pack_manifest.get("replacement_assets") or []
    }
    require(target_names <= (set(original_base) | set(original_new) | set(original_replacements)),
            f"{resref}: assets source absents du manifeste")
    current_frames = {str(frame["asset"]): frame for item in resources for frame in item["frames"]}
    generated_fade_names = set(current_frames) - (set(original_base) | set(original_new) | set(original_replacements))
    pack_manifest["resources"] = resources
    pack_manifest["resource_count"] = len(resources)
    pack_manifest["frame_count"] = sum(int(item["frame_count"]) for item in resources)
    pack_manifest["base_assets"] = [
        {"name": name, "sha256": current_frames[name]["sha256"], "bytes": current_frames[name]["bytes"]}
        for name in sorted(set(original_base) - target_names)
    ]
    pack_manifest["new_assets"] = [
        {"name": name, "sha256": current_frames[name]["sha256"], "bytes": current_frames[name]["bytes"]}
        for name in sorted(set(original_new))
    ] + [
        {"name": name, "sha256": current_frames[name]["sha256"], "bytes": current_frames[name]["bytes"]}
        for name in sorted(generated_fade_names)
    ]
    pack_manifest["replacement_assets"] = [
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
    registry = temporal.registry_v2_from_resources(resources, int(pack_manifest["registry_version"]))
    registry_path = pack_root / temporal.REGISTRY_NAME
    registry_path.write_bytes(registry)
    pack_manifest["registry_sha256"] = sha256_file(registry_path)
    pack_manifest["registry_bytes"] = len(registry)
    pack_manifest["raw_bytes"] = sum(int(asset["bytes"]) for item in resources for asset in item["assets"])
    pack_manifest["per_frame_spline_alpha"] = {
        "schema": SCHEMA,
        "pipeline_name": pipeline_name,
        "pipeline_effects": pipeline_effects,
        "resref": resref,
        "fit_error_x4": fit_error,
        "sample_spacing_x4": sample_spacing,
        "raster_supersample": supersample,
        "padding_x4": padding,
        "inner_feather_x4": inner_feather,
        "protected_source_core_x4": protected_core,
        "oval_edge_fade": {
            "shape": "inner-to-outer-ellipse-smoothstep",
            "top_bottom_fade_x4": oval_top_bottom_fade,
            "side_fade_x4": oval_side_fade,
        },
        "timeline_fade": timeline_fade,
        "alpha_formula": "alpha_source * spline_mask * inner_smoothstep",
        "rgb_policy": "premultiplied-by-final-alpha",
    }
    temporal.write_json(pack_root / "manifest.json", pack_manifest)
    temporal.validate_v2_pack(pack_root)

    report_path = partial / "spline-alpha-report.json"
    report = {
        "schema": SCHEMA,
        "pipeline_name": pipeline_name,
        "pipeline_effects": pipeline_effects,
        "status": "completed-pending-qa",
        "resref": resref,
        "source_temporal_run": temporal_run.as_posix(),
        "source_temporal_run_manifest_sha256": sha256_file(temporal_run / "manifest.json"),
        "parameters": {
            "fit_error_x4": fit_error, "sample_spacing_x4": sample_spacing,
            "raster_supersample": supersample, "padding_x4": padding,
            "inner_feather_x4": inner_feather, "threshold": threshold,
            "protected_source_core_x4": protected_core,
            "oval_top_bottom_fade_x4": oval_top_bottom_fade,
            "oval_side_fade_x4": oval_side_fade,
            "global_fade_hold_ratio": global_fade_hold_ratio,
            "active_fade_in_phases": active_fade_in,
            "active_fade_full_phases": active_fade_full,
            "active_fade_out_phases": active_fade_out,
        },
        "frames": reports,
        "timeline_fade": timeline_fade,
        "alpha_invariant": "alpha_final <= alpha_source",
        "rgb_policy": "premultiplied-by-final-alpha",
        "installation": "not performed",
    }
    temporal.write_json(report_path, report)
    reviews = render_reviews(source_pack, pack_root, resource, partial / "review", review_ffmpeg)
    manifest = {
        "schema": temporal.RUN_SCHEMA,
        "status": "completed",
        "created_utc": temporal.utc_now(),
        "input_mode": "per-frame-multi-contour-spline-alpha-on-timed-run",
        "source_run": temporal_run.as_posix(),
        "source_run_manifest_sha256": sha256_file(temporal_run / "manifest.json"),
        "base_pack": base_pack.as_posix(),
        "base_pack_manifest_sha256": sha256_file(base_pack / "manifest.json"),
        "native_fps": temporal.rate_record(temporal.NATIVE_FPS),
        "target_fps": temporal.rate_record(temporal.TARGET_FPS),
        "timed_resources": source_manifest["timed_resources"],
        "pack": "03_runtime_pack",
        "pack_manifest_sha256": sha256_file(pack_root / "manifest.json"),
        "registry_sha256": pack_manifest["registry_sha256"],
        "reviews": [{**item, "file": f"review/{item['file']}"} for item in reviews],
        "qa_status": "pending-explicit-user-approval",
        "per_frame_spline_alpha": {
            "pipeline_name": pipeline_name,
            "pipeline_effects": pipeline_effects,
            "report": "spline-alpha-report.json",
            "report_sha256": sha256_file(report_path),
            "installation": "not performed",
        },
    }
    temporal.write_json(partial / "manifest.json", manifest)
    temporal.validate_run(partial)
    partial.replace(output)
    return temporal.validate_run(output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--temporal-run", type=Path, required=True)
    parser.add_argument("--resref", required=True)
    output_group = parser.add_mutually_exclusive_group(required=True)
    output_group.add_argument(
        "--run", help="identifiant du nouveau run mono-resref dans le layout courant"
    )
    output_group.add_argument(
        "--output", type=Path, help="chemin explicite, réservé à la reprise legacy"
    )
    parser.add_argument("--fit-error", type=float, default=1.0)
    parser.add_argument("--sample-spacing", type=float, default=1.5)
    parser.add_argument("--supersample", type=int, default=4)
    parser.add_argument("--padding-x4", type=int, default=32)
    parser.add_argument("--inner-feather-x4", type=int, default=4)
    parser.add_argument("--protect-source-core-x4", type=int, default=0,
                        help="préserve l'alpha source au-delà de cette profondeur de contour")
    parser.add_argument("--oval-top-bottom-fade-x4", type=int, default=0,
                        help="fondu elliptique vertical ; 0 désactive l'effet")
    parser.add_argument("--oval-side-fade-x4", type=int, default=0,
                        help="fondu elliptique latéral ; 0 désactive l'effet")
    parser.add_argument("--global-fade-hold-ratio", type=float, default=1.0,
                        help="part centrale à opacité 100 %% ; 1 désactive le fade global")
    parser.add_argument("--active-fade-in-phases", type=int, default=0)
    parser.add_argument("--active-fade-full-phases", type=int, default=0)
    parser.add_argument("--active-fade-out-phases", type=int, default=0)
    parser.add_argument("--threshold", type=int, default=127)
    parser.add_argument("--review-ffmpeg", default="ffmpeg")
    args = parser.parse_args()
    output = (
        animation_paths.resolve_run_destination(args.run, [args.resref])
        if args.run
        else args.output.resolve()
    )
    temporal_run = animation_paths.resolve_existing_run(
        args.temporal_run, [args.resref]
    )
    result = build(
        temporal_run, args.resref, output, threshold=args.threshold,
        fit_error=args.fit_error, sample_spacing=args.sample_spacing,
        supersample=args.supersample, padding=args.padding_x4,
        inner_feather=args.inner_feather_x4,
        protected_core=args.protect_source_core_x4,
        oval_top_bottom_fade=args.oval_top_bottom_fade_x4,
        oval_side_fade=args.oval_side_fade_x4,
        global_fade_hold_ratio=args.global_fade_hold_ratio,
        active_fade_in=args.active_fade_in_phases,
        active_fade_full=args.active_fade_full_phases,
        active_fade_out=args.active_fade_out_phases,
        review_ffmpeg=args.review_ffmpeg,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
