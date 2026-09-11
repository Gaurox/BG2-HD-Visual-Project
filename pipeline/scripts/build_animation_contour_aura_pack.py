"""Derive a Blended area-animation split-root with the validated FPIT1S contour aura.

The recipe fades alpha inward from the source silhouette, derives a bounded Gaussian aura from
that faded silhouette, fades the aura before the canvas edge, then premultiplies RGB by final
alpha. It is intentionally split-root based: each output remains an installable per-area pack.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter

sys.path.insert(0, str(Path(__file__).resolve().parent))

import run_animation_upscale_30fps_v2 as v2  # noqa: E402
import split_animation_pack_by_area as splitter  # noqa: E402
from build_alpha_feather import inner_feather_ramp  # noqa: E402

SCHEMA = "bg2-upscale-animation-contour-aura-pack-v1"


def smoothstep(value: np.ndarray) -> np.ndarray:
    clipped = np.clip(value, 0.0, 1.0)
    return clipped * clipped * (3.0 - 2.0 * clipped)


def canvas_edge_ramp(width: int, height: int, margin: float) -> np.ndarray:
    """Return a 0→1 ramp that makes a halo vanish before every canvas edge."""
    y, x = np.ogrid[:height, :width]
    distance = np.minimum(np.minimum(x, width - 1 - x), np.minimum(y, height - 1 - y))
    return smoothstep(distance.astype(np.float32) / margin)


def transform_pixels(raw: bytes, width: int, height: int, *, inner_feather_x4: float,
                     aura_sigma_x4: float, aura_gain: float,
                     border_margin_x4: float) -> tuple[bytes, dict[str, int]]:
    """Apply contour fade, bounded aura and Blended-safe premultiplication."""
    expected = width * height * 4
    v2.require(len(raw) == expected, f"buffer RGBA inattendu ({len(raw)} != {expected})")
    pixels = np.frombuffer(raw, dtype=np.uint8).reshape(height, width, 4).copy()
    source_alpha = pixels[..., 3].astype(np.float32)
    inner = source_alpha * inner_feather_ramp(source_alpha.astype(np.uint8), inner_feather_x4)
    aura = gaussian_filter(inner, sigma=aura_sigma_x4, mode="constant", cval=0.0,
                           truncate=8.0) * aura_gain
    final_alpha = np.maximum(inner, aura) * canvas_edge_ramp(width, height, border_margin_x4)
    alpha = np.rint(np.clip(final_alpha, 0.0, 255.0)).astype(np.uint8)
    source_mask = source_alpha > 0
    aura_only = (alpha > 0) & ~source_mask
    rgb_source = pixels[..., :3].copy()
    if aura_only.any():
        # Indexed/palette BAMs commonly keep a chroma key under alpha 0 (for
        # AM3011B: pure green). An aura expands alpha beyond the source mask;
        # use its nearest visible fire pixel rather than revealing that key.
        _, nearest = distance_transform_edt(~source_mask, return_indices=True)
        rgb_source[aura_only] = rgb_source[nearest[0][aura_only], nearest[1][aura_only]]
    rgb = np.rint(rgb_source.astype(np.float32) * (alpha[..., None] / 255.0))
    pixels[..., :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    pixels[..., 3] = alpha
    return pixels.tobytes(), {
        "source_alpha_nonzero_pixels": int((source_alpha > 0).sum()),
        "final_alpha_nonzero_pixels": int((alpha > 0).sum()),
        "aura_expanded_pixels": int(((alpha > 0) & (source_alpha == 0)).sum()),
        "aura_rgb_dilated_pixels": int(aura_only.sum()),
    }


def transform_area(area_dir: Path, targets: set[str], *, inner_feather_x4: float,
                   aura_sigma_x4: float, aura_gain: float,
                   border_margin_x4: float) -> tuple[dict[str, Any], dict[str, int]]:
    manifest = v2.load_json(area_dir / "manifest.json")
    stats = {"frames": 0, "pixels": 0, "aura_expanded_pixels": 0, "aura_rgb_dilated_pixels": 0}
    touched: list[str] = []
    for resource in manifest.get("resources") or []:
        resref = v2.normalise_resref(str(resource.get("resref", "")))
        if resref not in targets:
            continue
        touched.append(resref)
        assets = {str(asset["name"]): asset for asset in resource["assets"]}
        for frame in resource["frames"]:
            width, height = (int(value) for value in frame["physical_size_x4"])
            asset_path = area_dir / str(frame["asset"])
            transformed, frame_stats = transform_pixels(
                asset_path.read_bytes(), width, height,
                inner_feather_x4=inner_feather_x4, aura_sigma_x4=aura_sigma_x4,
                aura_gain=aura_gain, border_margin_x4=border_margin_x4,
            )
            asset_path.write_bytes(transformed)
            digest = v2.sha256_file(asset_path)
            size = asset_path.stat().st_size
            frame["sha256"], frame["bytes"] = digest, size
            assets[str(frame["asset"])]["sha256"] = digest
            assets[str(frame["asset"])]["bytes"] = size
            stats["frames"] += 1
            stats["pixels"] += frame_stats["final_alpha_nonzero_pixels"]
            stats["aura_expanded_pixels"] += frame_stats["aura_expanded_pixels"]
            stats["aura_rgb_dilated_pixels"] += frame_stats["aura_rgb_dilated_pixels"]
    if touched:
        manifest["contour_aura"] = {
            "schema": SCHEMA,
            "resrefs": sorted(touched),
            "inner_feather_x4": inner_feather_x4,
            "aura_sigma_x4": aura_sigma_x4,
            "aura_gain": aura_gain,
            "border_margin_x4": border_margin_x4,
            "rgb_policy": "nearest-opaque-for-aura-then-premultiplied-by-final-alpha",
            "aura_expanded_pixels": stats["aura_expanded_pixels"],
            "aura_rgb_dilated_pixels": stats["aura_rgb_dilated_pixels"],
        }
    return manifest, stats


def build(split_root: Path, output: Path, targets: set[str], *, inner_feather_x4: float,
          aura_sigma_x4: float, aura_gain: float, border_margin_x4: float,
          resume: bool) -> dict[str, Any]:
    source = split_root.resolve()
    destination = output.resolve()
    index = v2.load_json(source / "manifest.json")
    v2.require(index.get("schema") == splitter.INDEX_SCHEMA and index.get("status") == "completed",
               f"split-root incompatible : {source}")
    for entry in index.get("areas") or []:
        v2.validate_v2_pack(source / str(entry["directory"]))
    available = {v2.normalise_resref(str(resref)) for entry in index.get("areas") or []
                 for resref in entry.get("resrefs") or []}
    v2.require(not (targets - available), f"resrefs absents : {', '.join(sorted(targets - available))}")
    if destination.exists():
        v2.require(resume, f"sortie déjà présente sans --resume : {destination}")
        existing = v2.load_json(destination / "manifest.json")
        for entry in existing.get("areas") or []:
            v2.validate_v2_pack(destination / str(entry["directory"]))
        return existing

    shutil.copytree(source, destination, ignore=shutil.ignore_patterns("install-backups"))
    entries: list[dict[str, Any]] = []
    totals = {"frames": 0, "pixels": 0, "aura_expanded_pixels": 0, "aura_rgb_dilated_pixels": 0}
    for entry in sorted(index.get("areas") or [], key=lambda item: str(item["area_id"])):
        area_dir = destination / str(entry["directory"])
        manifest, stats = transform_area(
            area_dir, targets, inner_feather_x4=inner_feather_x4,
            aura_sigma_x4=aura_sigma_x4, aura_gain=aura_gain,
            border_margin_x4=border_margin_x4,
        )
        v2.write_json(area_dir / "manifest.json", manifest)
        v2.validate_v2_pack(area_dir)
        updated = dict(entry)
        updated["manifest_sha256"] = v2.sha256_file(area_dir / "manifest.json")
        entries.append(updated)
        for key in totals:
            totals[key] += stats[key]

    result = dict(index)
    result["created_utc"] = v2.utc_now()
    result["areas"] = entries
    result["contour_aura"] = {
        "schema": SCHEMA,
        "requested_resrefs": sorted(targets),
        "source_split_root": source.as_posix(),
        "inner_feather_x4": inner_feather_x4,
        "aura_sigma_x4": aura_sigma_x4,
        "aura_gain": aura_gain,
        "border_margin_x4": border_margin_x4,
        "rgb_policy": "nearest-opaque-for-aura-then-premultiplied-by-final-alpha",
        **totals,
    }
    v2.write_json(destination / "manifest.json", result)
    return result


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--split-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resref", action="append", required=True, dest="resrefs")
    parser.add_argument("--inner-feather-x4", type=float, required=True)
    parser.add_argument("--aura-sigma-x4", type=float, required=True)
    parser.add_argument("--aura-gain", type=float, required=True)
    parser.add_argument("--border-margin-x4", type=float, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    for name, value in (("inner-feather", args.inner_feather_x4), ("aura-sigma", args.aura_sigma_x4),
                        ("aura-gain", args.aura_gain), ("border-margin", args.border_margin_x4)):
        if value <= 0:
            raise SystemExit(f"--{name}-x4 doit être strictement positif")
    result = build(
        args.split_root, args.output, {v2.normalise_resref(value) for value in args.resrefs},
        inner_feather_x4=args.inner_feather_x4, aura_sigma_x4=args.aura_sigma_x4,
        aura_gain=args.aura_gain, border_margin_x4=args.border_margin_x4, resume=args.resume,
    )
    print(json.dumps({key: value for key, value in result.items() if key != "areas"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
