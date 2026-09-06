"""Build a per-frame, multi-component Fit 1 alpha override for a spatial x4 run.

The normal path keeps RGB and all animation geometry byte-identical while
attenuating the source alpha with a multi-component spline mask.  An optional
bounded Gaussian reconstruction is reserved for inspected pixel-island raccords;
only that rectangle may raise alpha over the source mask.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.ndimage import gaussian_filter

import animation_paths
from build_alpha_feather import SCHEMA, UPSCALE_SCHEMA, require, save_png, sha256, write_json, write_preview
from build_per_frame_spline_alpha_30fps_v2 import fit_component, spline_alpha


def smoothstep(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def reconstruction_gate(
    width: int,
    height: int,
    region: tuple[int, int, int, int],
    transition: int,
) -> np.ndarray:
    """Return a bounded rectangular gate, feathered only at interior edges."""
    x0, y0, x1, y1 = region
    require(0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height, "region de reconstruction hors frame")
    require(transition >= 0, "transition de reconstruction negative")
    gate = np.zeros((height, width), dtype=np.float32)
    gate[y0:y1, x0:x1] = 1.0
    if transition == 0:
        return gate
    yy, xx = np.indices((height, width), dtype=np.float32)
    if x0 > 0:
        gate *= smoothstep((xx - float(x0)) / float(transition))
    if x1 < width:
        gate *= smoothstep((float(x1 - 1) - xx) / float(transition))
    if y0 > 0:
        gate *= smoothstep((yy - float(y0)) / float(transition))
    if y1 < height:
        gate *= smoothstep((float(y1 - 1) - yy) / float(transition))
    return gate


def reconstruct_local_alpha(
    spline: np.ndarray,
    source: np.ndarray,
    *,
    region: tuple[int, int, int, int],
    sigma: float,
    minimum_alpha: int,
    transition: int,
) -> tuple[np.ndarray, dict[str, int | float | list[int]]]:
    """Blend a Gaussian alpha field into one inspected raccord rectangle."""
    require(spline.shape == source.shape, "masques alpha incompatibles")
    require(sigma > 0.0, "sigma de reconstruction doit etre strictement positif")
    require(0 <= minimum_alpha <= 255, "seuil de reconstruction invalide")
    height, width = source.shape
    gate = reconstruction_gate(width, height, region, transition)
    blurred = gaussian_filter(source.astype(np.float32), sigma=sigma, mode="constant", cval=0.0, truncate=8.0)
    reconstructed = np.where(blurred >= float(minimum_alpha), np.rint(blurred), 0.0)
    output = np.rint(spline.astype(np.float32) * (1.0 - gate) + reconstructed * gate).astype(np.uint8)
    outside = gate <= 0.0
    require(bool(np.array_equal(output[outside], spline[outside])), "reconstruction hors region")
    return output, {
        "region_x4": list(region),
        "sigma_x4": sigma,
        "minimum_alpha": minimum_alpha,
        "transition_x4": transition,
        "region_pixels": int(np.count_nonzero(gate > 0.0)),
        "raised_over_spline_pixels": int(np.count_nonzero(output > spline)),
        "raised_over_source_pixels": int(np.count_nonzero(output > source)),
    }


def reinforce_local_alpha(
    spline: np.ndarray,
    source: np.ndarray,
    *,
    region: tuple[int, int, int, int],
    threshold: int,
    outset: float,
    feather: float,
    transition: int,
) -> tuple[np.ndarray, dict[str, int | float | list[int]]]:
    """Raise one bounded raccord with a smooth signed-distance envelope.

    The source core remains fully opaque, while the local silhouette receives
    an isotropic x4 outset and an anti-aliased exterior. Padding makes a
    silhouette that touches the canvas edge behave as if transparent pixels
    continued outside the frame before the result is cropped back.
    """
    require(spline.shape == source.shape, "masques alpha incompatibles")
    require(outset >= 0.0 and feather > 0.0, "renforcement local invalide")
    height, width = source.shape
    gate = reconstruction_gate(width, height, region, transition)
    binary = source > threshold
    padding = max(2, int(np.ceil(outset + feather)) + 2)
    padded = np.pad(binary, padding, mode="constant")
    signed_distance = (
        ndimage.distance_transform_edt(padded)
        - ndimage.distance_transform_edt(~padded)
    )[padding:-padding, padding:-padding]
    envelope = np.rint(
        255.0 * smoothstep((signed_distance + float(outset)) / float(feather))
    ).astype(np.uint8)
    reinforced = np.maximum(spline, envelope)
    output = np.rint(
        spline.astype(np.float32) * (1.0 - gate) + reinforced.astype(np.float32) * gate
    ).astype(np.uint8)
    outside = gate <= 0.0
    require(bool(np.array_equal(output[outside], spline[outside])), "renforcement hors region")
    return output, {
        "region_x4": list(region),
        "threshold": threshold,
        "outset_x4": outset,
        "feather_x4": feather,
        "transition_x4": transition,
        "region_pixels": int(np.count_nonzero(gate > 0.0)),
        "raised_over_spline_pixels": int(np.count_nonzero(output > spline)),
        "raised_over_source_pixels": int(np.count_nonzero(output > source)),
    }


def safe_boundary_spline_alpha(
    source: np.ndarray,
    *,
    threshold: int,
    fit_error: float,
    spacing: float,
    supersample: int,
    padding: int,
    inner_band: float,
    outer_band: float,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Use a fitted contour only in a narrow signed-distance band.

    A raw periodic spline may self-intersect on a long concave component. The
    old alpha-only intersection retained x4 stairsteps. This mode preserves the
    opaque core and permits an anti-aliased outset only near the source edge.
    """
    require(inner_band > 0.0 and outer_band > 0.0, "bandes spline securisees invalides")
    binary = source > threshold
    if not binary.any():
        return source.copy(), {
            "source_nonzero": 0,
            "components": 0,
            "status": "empty-preserved",
            "mode": "safe-boundary",
        }
    padded = np.pad(binary, padding, mode="constant")
    labels, component_count = ndimage.label(
        padded, structure=np.ones((3, 3), dtype=np.uint8)
    )
    fitted = np.zeros_like(padded, dtype=np.uint8)
    component_reports: list[dict[str, int | str]] = []
    for label in range(1, int(component_count) + 1):
        component, report = fit_component(
            labels == label, fit_error, spacing, supersample
        )
        fitted = np.maximum(fitted, component)
        component_reports.append(report)
    fitted = fitted[padding:-padding, padding:-padding]

    inside_distance = ndimage.distance_transform_edt(binary)
    outside_distance = ndimage.distance_transform_edt(~binary)
    source_float = source.astype(np.float32)
    result = np.zeros_like(source_float)
    inside_weight = 1.0 - smoothstep((inside_distance - 0.5) / float(inner_band))
    result[binary] = (
        source_float[binary] * (1.0 - inside_weight[binary])
        + fitted[binary].astype(np.float32) * inside_weight[binary]
    )
    outside_allowed = (~binary) & (outside_distance <= float(outer_band))
    result[outside_allowed] = fitted[outside_allowed]
    output = np.rint(np.clip(result, 0.0, 255.0)).astype(np.uint8)
    require(
        not np.any((output > source) & ~outside_allowed),
        "spline securisee etendue hors bande autorisee",
    )
    return output, {
        "source_nonzero": int(np.count_nonzero(source)),
        "components": int(component_count),
        "status": "fitted",
        "mode": "safe-boundary",
        "inner_band_x4": inner_band,
        "outer_band_x4": outer_band,
        "expanded_alpha_pixels": int(np.count_nonzero((output > source) & outside_allowed)),
        "component_reports": component_reports,
    }


def blur_left_edge(
    alpha: np.ndarray,
    source: np.ndarray,
    *,
    threshold: int,
    sigma: float,
    inner_band: int,
    outer_band: int,
) -> tuple[np.ndarray, dict[str, int | float]]:
    """Blend a Gaussian alpha field only around each row's leftmost source edge."""
    require(sigma > 0.0 and inner_band > 0 and outer_band > 0, "flou gauche invalide")
    binary = source > threshold
    blurred = gaussian_filter(
        source.astype(np.float32), sigma=sigma, mode="constant", cval=0.0, truncate=8.0
    )
    result = alpha.astype(np.float32).copy()
    height, width = source.shape
    rows = 0
    changed = 0
    for y in range(height):
        opaque = np.flatnonzero(binary[y])
        if opaque.size == 0:
            continue
        rows += 1
        left = int(opaque[0])
        x0 = max(0, left - outer_band)
        x1 = min(width, left + inner_band + 1)
        xs = np.arange(x0, x1, dtype=np.float32)
        offsets = xs - float(left)
        weights = np.where(
            offsets <= 0.0,
            smoothstep((offsets + float(outer_band)) / float(outer_band)),
            1.0 - smoothstep(offsets / float(inner_band)),
        )
        before = result[y, x0:x1].copy()
        result[y, x0:x1] = before * (1.0 - weights) + blurred[y, x0:x1] * weights
        changed += int(np.count_nonzero(
            np.rint(result[y, x0:x1]).astype(np.uint8) != np.rint(before).astype(np.uint8)
        ))
    return np.rint(np.clip(result, 0.0, 255.0)).astype(np.uint8), {
        "sigma_x4": sigma,
        "inner_band_x4": inner_band,
        "outer_band_x4": outer_band,
        "rows": rows,
        "changed_alpha_pixels": changed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--run", required=True, help="run spatial source, mono ou batch")
    parser.add_argument("--runs-root", type=Path, help="racine legacy explicite")
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--output-run", help="nouveau run mono-resref")
    output.add_argument("--output", type=Path, help="chemin legacy explicite")
    parser.add_argument("--fit-error", type=float, default=1.0)
    parser.add_argument("--sample-spacing", type=float, default=1.5)
    parser.add_argument("--supersample", type=int, default=4)
    parser.add_argument("--padding-x4", type=int, default=32)
    parser.add_argument("--threshold", type=int, default=127)
    parser.add_argument(
        "--safe-boundary-inner-x4", type=float, default=0.0,
        help="largeur interne du remplacement spline securise; active avec --safe-boundary-outer-x4",
    )
    parser.add_argument(
        "--safe-boundary-outer-x4", type=float, default=0.0,
        help="outset maximal de la spline securisee; active avec --safe-boundary-inner-x4",
    )
    parser.add_argument("--left-edge-blur-sigma-x4", type=float, default=0.0)
    parser.add_argument("--left-edge-blur-inner-x4", type=int, default=0)
    parser.add_argument("--left-edge-blur-outer-x4", type=int, default=0)
    parser.add_argument(
        "--reconstruct-region-x4", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"),
        help="rectangle exclusif x0,y0,x1,y1 du seul raccord a reconstruire",
    )
    parser.add_argument("--reconstruct-sigma-x4", type=float, default=0.0)
    parser.add_argument("--reconstruct-min-alpha", type=int, default=12)
    parser.add_argument("--reconstruct-transition-x4", type=int, default=32)
    parser.add_argument(
        "--reinforce-region-x4", nargs=4, type=int, metavar=("X0", "Y0", "X1", "Y1"),
        help="rectangle exclusif du raccord a epaissir par enveloppe SDF",
    )
    parser.add_argument("--reinforce-outset-x4", type=float, default=0.0)
    parser.add_argument("--reinforce-feather-x4", type=float, default=0.0)
    parser.add_argument("--reinforce-transition-x4", type=int, default=32)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    resref = args.resref.upper()
    source_run = (
        (args.runs_root / args.run).resolve()
        if args.runs_root is not None
        else animation_paths.resolve_existing_run(args.run, [resref])
    )
    source_root = source_run / "resources" / resref / "02_upscale_x4"
    output = (
        animation_paths.resolve_run_destination(args.output_run, [resref])
        if args.output_run else args.output.resolve()
    )
    require(args.fit_error > 0.0 and args.sample_spacing > 0.0, "parametres spline invalides")
    require(args.supersample >= 1 and args.padding_x4 > 0, "rasterisation spline invalide")
    require(0 <= args.threshold <= 255, "seuil spline invalide")
    safe_boundary = args.safe_boundary_inner_x4 > 0.0 or args.safe_boundary_outer_x4 > 0.0
    require(
        not safe_boundary or (args.safe_boundary_inner_x4 > 0.0 and args.safe_boundary_outer_x4 > 0.0),
        "fournir ensemble les deux bandes spline securisee",
    )
    left_blur = args.left_edge_blur_sigma_x4 > 0.0
    require(
        not left_blur or (args.left_edge_blur_inner_x4 > 0 and args.left_edge_blur_outer_x4 > 0),
        "fournir les bandes du flou gauche",
    )
    has_region = args.reconstruct_region_x4 is not None
    require(
        has_region == (args.reconstruct_sigma_x4 > 0.0),
        "fournir ensemble --reconstruct-region-x4 et --reconstruct-sigma-x4",
    )
    has_reinforcement = args.reinforce_region_x4 is not None
    require(
        has_reinforcement
        == (args.reinforce_outset_x4 > 0.0 and args.reinforce_feather_x4 > 0.0),
        "fournir ensemble la region, l'outset et le feather de renforcement",
    )
    require(not output.exists() and not output.with_name(output.name + ".partial").exists(), "sortie deja presente")

    source_manifest_path = source_root / "manifest.json"
    require(source_manifest_path.is_file(), f"manifest x4 absent : {source_manifest_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8-sig"))
    require(
        source_manifest.get("schema") == UPSCALE_SCHEMA and source_manifest.get("status") == "completed",
        "run spatial source incomplet ou schema incompatible",
    )
    require(int(source_manifest.get("scale", 0)) == 4, "seul x4 est supporte")
    source_frames = sorted(source_manifest.get("frames") or [], key=lambda item: int(item["frame"]))
    require(source_frames, "aucune frame x4")

    partial = output.with_name(output.name + ".partial")
    directories = {
        "rgba": partial / "rgba",
        "alpha": partial / "alpha",
        "raw": partial / "raw_rgba",
        "preview": partial / "preview",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    region = tuple(args.reconstruct_region_x4) if has_region else None
    reinforcement_region = tuple(args.reinforce_region_x4) if has_reinforcement else None
    records: list[dict[str, Any]] = []
    preview_original: Image.Image | None = None
    preview_corrected: Image.Image | None = None
    for index, frame in enumerate(source_frames):
        require(int(frame["frame"]) == index, "index de frame non contigu")
        raw_relative = str(frame["raw_rgba_xn"])
        raw_source = (source_root / raw_relative).resolve()
        physical_width, physical_height = (int(value) for value in frame["physical_size_xn"])
        expected_bytes = physical_width * physical_height * 4
        require(
            raw_source.is_file()
            and raw_source.stat().st_size == expected_bytes
            and sha256(raw_source) == str(frame["raw_rgba_xn_sha256"]).lower(),
            f"frame {index}: source brut incoherent",
        )
        source_pixels = np.frombuffer(raw_source.read_bytes(), dtype=np.uint8).reshape(
            (physical_height, physical_width, 4)
        )
        source_alpha = source_pixels[:, :, 3]
        if safe_boundary:
            corrected, spline_report = safe_boundary_spline_alpha(
                source_alpha,
                threshold=args.threshold,
                fit_error=args.fit_error,
                spacing=args.sample_spacing,
                supersample=args.supersample,
                padding=args.padding_x4,
                inner_band=args.safe_boundary_inner_x4,
                outer_band=args.safe_boundary_outer_x4,
            )
        else:
            corrected, spline_report = spline_alpha(
                source_alpha,
                threshold=args.threshold,
                fit_error=args.fit_error,
                spacing=args.sample_spacing,
                supersample=args.supersample,
                padding=args.padding_x4,
                inner_feather=0,
                protected_core=0,
            )
            require(bool(np.all(corrected <= source_alpha)), f"frame {index}: spline etend l'alpha")
        left_blur_report: dict[str, int | float] | None = None
        if left_blur:
            corrected, left_blur_report = blur_left_edge(
                corrected,
                source_alpha,
                threshold=args.threshold,
                sigma=args.left_edge_blur_sigma_x4,
                inner_band=args.left_edge_blur_inner_x4,
                outer_band=args.left_edge_blur_outer_x4,
            )
        reconstruction_report: dict[str, Any] | None = None
        if region is not None:
            corrected, reconstruction_report = reconstruct_local_alpha(
                corrected,
                source_alpha,
                region=region,
                sigma=args.reconstruct_sigma_x4,
                minimum_alpha=args.reconstruct_min_alpha,
                transition=args.reconstruct_transition_x4,
            )
        reinforcement_report: dict[str, int | float | list[int]] | None = None
        if reinforcement_region is not None:
            corrected, reinforcement_report = reinforce_local_alpha(
                corrected,
                source_alpha,
                region=reinforcement_region,
                threshold=args.threshold,
                outset=args.reinforce_outset_x4,
                feather=args.reinforce_feather_x4,
                transition=args.reinforce_transition_x4,
            )
        pixels = source_pixels.copy()
        pixels[:, :, 3] = corrected
        require(bool(np.array_equal(pixels[:, :, :3], source_pixels[:, :, :3])), f"frame {index}: RGB modifie")

        asset_name = f"AAX4-{resref}-frame{index:03d}.rgba"
        raw_path = directories["raw"] / asset_name
        rgba_path = directories["rgba"] / f"frame_{index:03d}.png"
        alpha_path = directories["alpha"] / f"frame_{index:03d}.png"
        temporary_raw = raw_path.with_suffix(raw_path.suffix + ".part")
        temporary_raw.write_bytes(pixels.tobytes(order="C"))
        temporary_raw.replace(raw_path)
        save_png(Image.fromarray(pixels, "RGBA"), rgba_path)
        save_png(Image.fromarray(corrected, "L"), alpha_path)
        records.append({
            "frame": index,
            "source_runtime_asset": raw_relative,
            "source_runtime_sha256": sha256(raw_source),
            "source_runtime_bytes": raw_source.stat().st_size,
            "runtime_asset": raw_path.relative_to(partial).as_posix(),
            "runtime_sha256": sha256(raw_path),
            "runtime_bytes": raw_path.stat().st_size,
            "rgba": rgba_path.relative_to(partial).as_posix(),
            "rgba_sha256": sha256(rgba_path),
            "alpha": alpha_path.relative_to(partial).as_posix(),
            "alpha_sha256": sha256(alpha_path),
            "spline": spline_report,
            "left_edge_blur": left_blur_report,
            "local_reconstruction": reconstruction_report,
            "local_reinforcement": reinforcement_report,
            "changed_alpha_pixels": int(np.count_nonzero(corrected != source_alpha)),
            "raised_over_source_alpha_pixels": int(np.count_nonzero(corrected > source_alpha)),
            "rgb_byte_identical": True,
        })
        if index == 0:
            preview_original = Image.fromarray(source_pixels, "RGBA")
            preview_corrected = Image.fromarray(pixels, "RGBA")

    require(preview_original is not None and preview_corrected is not None, "preview impossible")
    label = "spline Fit 1 multi-composante"
    if safe_boundary:
        label += " securisee"
    if left_blur:
        label += " + flou bord gauche"
    if region is not None:
        label += " + reconstruction gaussienne locale"
    if reinforcement_region is not None:
        label += " + renforcement SDF local"
    write_preview(preview_original, preview_corrected, label, directories["preview"] / "frame_000-comparison.png")
    physical_sizes = {tuple(int(v) for v in frame["physical_size_xn"]) for frame in source_frames}
    manifest = {
        "schema": SCHEMA,
        "status": "completed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "resref": resref,
        "asset_ids": [f"animations:bam:{resref}"],
        "scale": 4,
        "frame_count": len(source_frames),
        "physical_size_x4": list(next(iter(physical_sizes))) if len(physical_sizes) == 1 else None,
        "source_run": source_root.as_posix(),
        "source_run_manifest_sha256": sha256(source_manifest_path),
        "alpha_operation": {
            "type": "per-frame-multi-component-spline-fit1"
            + ("-safe-boundary" if safe_boundary else "")
            + ("-plus-left-edge-gaussian" if left_blur else "")
            + ("-plus-bounded-gaussian-reconstruction" if region else ""),
            "fit_error": args.fit_error,
            "sample_spacing_x4": args.sample_spacing,
            "supersample": args.supersample,
            "padding_x4": args.padding_x4,
            "threshold": args.threshold,
            "components": "all 8-connected components preserved and fitted independently",
            "safe_boundary": {
                "inner_band_x4": args.safe_boundary_inner_x4,
                "outer_band_x4": args.safe_boundary_outer_x4,
                "opaque_core_preserved": True,
                "outset_limited_to_outer_band": True,
            } if safe_boundary else None,
            "left_edge_blur": {
                "sigma_x4": args.left_edge_blur_sigma_x4,
                "inner_band_x4": args.left_edge_blur_inner_x4,
                "outer_band_x4": args.left_edge_blur_outer_x4,
            } if left_blur else None,
            "local_reconstruction": {
                "region_x4": list(region),
                "sigma_x4": args.reconstruct_sigma_x4,
                "minimum_alpha": args.reconstruct_min_alpha,
                "transition_x4": args.reconstruct_transition_x4,
                "may_raise_alpha_only_inside_region": True,
            } if region else None,
            "local_reinforcement": {
                "region_x4": list(reinforcement_region),
                "outset_x4": args.reinforce_outset_x4,
                "feather_x4": args.reinforce_feather_x4,
                "transition_x4": args.reinforce_transition_x4,
                "may_raise_alpha_only_inside_region": True,
            } if reinforcement_region else None,
            "rgb_policy": "unchanged",
            "geometry_policy": "unchanged",
            "timeline_policy": "unchanged",
        },
        "frames": records,
    }
    write_json(manifest, partial / "manifest.json")
    partial.replace(output)
    print(f"{resref}: {len(records)} frames, {label} -> {output}")


if __name__ == "__main__":
    main()
