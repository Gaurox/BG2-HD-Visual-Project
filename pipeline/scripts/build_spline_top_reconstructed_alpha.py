"""Build a reproducible spline + reconstructed-top alpha correction.

The source mask's principal connected silhouette is replaced by a Fit 1 spline
with transparent padding and supersampled rasterisation. A two-dimensional
Gaussian coverage field, calculated from the original alpha, then replaces a
bounded upper region. That preserves a reviewed top fade independently of the
spline while smoothing the silhouette's remaining contours. Pixels below a
minimum coverage are cleared: this removes isolated source blocks while
allowing a continuous fade to occupy former alpha holes. RGB, geometry, frame
order and cycles stay unchanged. The output is an immutable alpha-override
prototype consumable by ``build_animation_runtime_pack.py --alpha-override-manifest``.
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
from build_per_frame_spline_alpha_30fps_v2 import fit_component


def spline_main_silhouette(
    alpha: np.ndarray,
    *,
    threshold: int,
    fit_error: float,
    spacing: float,
    supersample: int,
    padding: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Replace the largest padded alpha component with a periodic Fit 1 spline.

    Tiny disconnected source islands are deliberately excluded. They are not
    separate animation elements in this recipe; the top reconstruction supplies
    the intended soft coverage in their place.
    """
    binary = alpha > threshold
    require(bool(binary.any()), "masque alpha source vide")
    padded = np.pad(binary, padding, mode="constant")
    labels, component_count = ndimage.label(padded, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    largest_label = int(np.argmax(sizes))
    fitted_padded, report = fit_component(
        labels == largest_label,
        fit_error=fit_error,
        spacing=spacing,
        supersample=supersample,
    )
    fitted = fitted_padded[padding:-padding, padding:-padding]
    return fitted, {
        "source_components": int(component_count),
        "discarded_components": int(component_count - 1),
        "main_component_pixels": int(sizes[largest_label]),
        "padding_x4": padding,
        "fit": report,
    }


def rebuild_top_region(
    base_alpha: np.ndarray,
    fade_source_alpha: np.ndarray,
    *,
    sigma: float,
    top_height: int,
    left_x: int,
    minimum_alpha: int,
) -> tuple[np.ndarray, dict[str, int | float]]:
    """Replace the selected upper alpha band with a smooth coverage field.

    The Gaussian is deliberately calculated from the original alpha mask: its
    visual fade is independently reviewed. Only ``y < top_height`` and
    ``x >= left_x`` are replaced over the already spline-fitted base. This may
    intentionally raise alpha inside former holes; that is recorded rather
    than hidden behind the normal ``final <= source`` feather invariant.
    """
    if base_alpha.shape != fade_source_alpha.shape:
        raise RuntimeError("masques alpha de dimensions differentes")
    height, width = base_alpha.shape
    if not 0 < top_height <= height:
        raise RuntimeError("hauteur de region haute hors canvas")
    if not 0 <= left_x < width:
        raise RuntimeError("abscisse gauche de region haute hors canvas")
    if sigma <= 0.0:
        raise RuntimeError("sigma gaussien doit etre strictement positif")
    if not 0 <= minimum_alpha <= 255:
        raise RuntimeError("seuil alpha minimal invalide")

    blurred = gaussian_filter(fade_source_alpha.astype(np.float32), sigma=sigma, mode="constant", cval=0.0)
    reconstructed = np.where(blurred >= float(minimum_alpha), np.rint(blurred), 0).astype(np.uint8)
    yy, xx = np.indices((height, width))
    region = (yy < top_height) & (xx >= left_x)
    output = base_alpha.copy()
    output[region] = reconstructed[region]
    return output, {
        "region_pixels": int(region.sum()),
        "changed_alpha_pixels": int(np.count_nonzero(output != base_alpha)),
        "raised_alpha_pixels": int(np.count_nonzero(output > base_alpha)),
        "cleared_alpha_pixels": int(np.count_nonzero((output == 0) & (base_alpha > 0) & region)),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--run", required=True, help="identifiant ou chemin du run source")
    parser.add_argument("--runs-root", type=Path, help="racine explicite pour une reprise legacy")
    output = parser.add_mutually_exclusive_group(required=True)
    output.add_argument("--output-run", help="identifiant du nouveau run mono-resref")
    output.add_argument("--output", type=Path, help="chemin legacy explicite")
    parser.add_argument("--fit-error", type=float, default=1.0)
    parser.add_argument("--sample-spacing", type=float, default=1.5)
    parser.add_argument("--supersample", type=int, default=4)
    parser.add_argument("--padding-x4", type=int, default=32)
    parser.add_argument("--threshold", type=int, default=127)
    parser.add_argument("--top-gaussian-sigma-x4", type=float, required=True)
    parser.add_argument("--top-height-x4", type=int, required=True)
    parser.add_argument("--top-left-x-x4", type=int, required=True)
    parser.add_argument("--top-minimum-alpha", type=int, default=12)
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
    require(args.fit_error > 0.0, "fit-error doit etre strictement positif")
    require(args.sample_spacing > 0.0, "sample-spacing doit etre strictement positif")
    require(args.supersample >= 1, "supersample doit etre positif")
    require(args.padding_x4 > 0, "padding-x4 doit etre strictement positif")
    require(0 <= args.threshold <= 255, "threshold invalide")
    require(not output.exists() or not any(output.iterdir()), f"sortie non vide : {output}")

    source_manifest_path = source_root / "manifest.json"
    require(source_manifest_path.is_file(), f"manifest d'upscale absent : {source_manifest_path}")
    source_manifest = json.loads(source_manifest_path.read_text(encoding="utf-8-sig"))
    require(
        source_manifest.get("schema") == UPSCALE_SCHEMA and source_manifest.get("status") == "completed",
        "run source incomplet ou schema incompatible.",
    )
    require(int(source_manifest.get("scale", 0)) == 4, "seul le canal runtime x4 est pris en charge.")
    source_frames = sorted(source_manifest.get("frames") or [], key=lambda item: int(item["frame"]))
    require(source_frames, "aucune frame dans le run source.")

    directories = {
        "rgba": output / "rgba",
        "alpha": output / "alpha",
        "raw": output / "raw_rgba",
        "preview": output / "preview",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)

    records: list[dict[str, Any]] = []
    preview_original: Image.Image | None = None
    preview_corrected: Image.Image | None = None
    for index, frame in enumerate(source_frames):
        require(int(frame["frame"]) == index, "index de frame non contigu.")
        raw_relative = str(frame["raw_rgba_xn"])
        raw_source = (source_root / raw_relative).resolve()
        physical_width, physical_height = (int(value) for value in frame["physical_size_xn"])
        expected_bytes = physical_width * physical_height * 4
        require(
            raw_source.is_file()
            and raw_source.stat().st_size == expected_bytes
            and sha256(raw_source) == str(frame["raw_rgba_xn_sha256"]).lower(),
            f"asset brut source incoherent : {raw_source}",
        )
        source_pixels = np.frombuffer(raw_source.read_bytes(), dtype=np.uint8).reshape(
            (physical_height, physical_width, 4)
        )
        fitted_alpha, spline_report = spline_main_silhouette(
            source_pixels[:, :, 3],
            threshold=args.threshold,
            fit_error=args.fit_error,
            spacing=args.sample_spacing,
            supersample=args.supersample,
            padding=args.padding_x4,
        )
        corrected_alpha, top_report = rebuild_top_region(
            fitted_alpha,
            source_pixels[:, :, 3],
            sigma=args.top_gaussian_sigma_x4,
            top_height=args.top_height_x4,
            left_x=args.top_left_x_x4,
            minimum_alpha=args.top_minimum_alpha,
        )
        pixels = source_pixels.copy()
        pixels[:, :, 3] = corrected_alpha
        require(
            bool(np.array_equal(pixels[:, :, :3], source_pixels[:, :, :3])),
            f"{resref} frame {index}: RGB modifie.",
        )

        asset_name = f"AAX4-{resref}-frame{index:03d}.rgba"
        rgba_path = directories["rgba"] / f"frame_{index:03d}.png"
        alpha_path = directories["alpha"] / f"frame_{index:03d}.png"
        raw_path = directories["raw"] / asset_name
        save_png(Image.fromarray(pixels, "RGBA"), rgba_path)
        save_png(Image.fromarray(corrected_alpha, "L"), alpha_path)
        temporary_raw = raw_path.with_suffix(raw_path.suffix + ".part")
        temporary_raw.write_bytes(pixels.tobytes(order="C"))
        temporary_raw.replace(raw_path)
        records.append({
            "frame": index,
            "source_runtime_asset": raw_relative,
            "source_runtime_sha256": sha256(raw_source),
            "source_runtime_bytes": raw_source.stat().st_size,
            "runtime_asset": raw_path.relative_to(output).as_posix(),
            "runtime_sha256": sha256(raw_path),
            "runtime_bytes": raw_path.stat().st_size,
            "rgba": rgba_path.relative_to(output).as_posix(),
            "rgba_sha256": sha256(rgba_path),
            "alpha": alpha_path.relative_to(output).as_posix(),
            "alpha_sha256": sha256(alpha_path),
            "source_alpha_nonzero_pixels": int(np.count_nonzero(source_pixels[:, :, 3])),
            "spline_changed_alpha_pixels": int(np.count_nonzero(fitted_alpha != source_pixels[:, :, 3])),
            "spline": spline_report,
            "top_reconstruction": top_report,
            "final_raised_over_source_alpha_pixels": int(np.count_nonzero(corrected_alpha > source_pixels[:, :, 3])),
            "final_cleared_source_alpha_pixels": int(np.count_nonzero(
                (corrected_alpha == 0) & (source_pixels[:, :, 3] > 0)
            )),
        })
        if index == 0:
            preview_original = Image.fromarray(source_pixels, "RGBA")
            preview_corrected = Image.fromarray(pixels, "RGBA")

    require(preview_original is not None and preview_corrected is not None, "preview impossible.")
    write_preview(
        preview_original,
        preview_corrected,
        "spline Fit 1 + reconstruction gaussienne haute",
        directories["preview"] / "frame_000-comparison.png",
    )
    physical_sizes = {tuple(int(v) for v in frame["physical_size_xn"]) for frame in source_frames}
    manifest = {
        "schema": SCHEMA,
        "status": "completed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "resref": resref,
        "scale": 4,
        "frame_count": len(source_frames),
        "physical_size_x4": list(next(iter(physical_sizes))) if len(physical_sizes) == 1 else None,
        "source_run": source_root.as_posix(),
        "source_run_manifest_sha256": sha256(source_manifest_path),
        "alpha_operation": {
            "type": "main-silhouette-spline-fit1-plus-source-top-reconstructed-gaussian",
            "spline": {
                "fit_error": args.fit_error,
                "sample_spacing_x4": args.sample_spacing,
                "supersample": args.supersample,
                "padding_x4": args.padding_x4,
                "threshold": args.threshold,
                "scope": "largest-connected-component; disconnected islands discarded",
            },
            "top_reconstructed_gaussian": {
                "sigma_x4": args.top_gaussian_sigma_x4,
                "height_x4_exclusive": args.top_height_x4,
                "left_x4_inclusive": args.top_left_x_x4,
                "minimum_alpha": args.top_minimum_alpha,
                "source": "original-alpha-before-spline",
                "may_expand_alpha_inside_reconstructed_region": True,
            },
            "rgb_policy": "unchanged",
            "geometry_policy": "unchanged",
            "timeline_policy": "unchanged",
        },
        "frames": records,
    }
    write_json(manifest, output / "manifest.json")
    print(f"{resref}: {len(source_frames)} frames, spline Fit 1 + reconstruction gaussienne haute.")


if __name__ == "__main__":
    main()
