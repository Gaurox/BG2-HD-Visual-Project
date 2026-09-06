"""Add animated water texture only where a user-authored grayscale mask requests it.

The source prototype stays immutable.  Black mask pixels preserve the padded source
byte-for-byte; lighter pixels raise alpha and receive RGB sampled from opaque water
inside the same animation frame.  If the mask is taller than the native frame, a
matching transparent-padded BAM is emitted without changing centres or cycles.
"""

from __future__ import annotations

import argparse
import copy
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops
from scipy.ndimage import binary_erosion, distance_transform_edt

sys.path.insert(0, str(Path(__file__).resolve().parent))

import animation_paths  # noqa: E402
import build_animation_bottom_overscan as bottom  # noqa: E402
from bam_export import decode_bam  # noqa: E402
from export_bam_frames import cycle_metadata  # noqa: E402
import run_animation_upscale_30fps_v2 as runtime  # noqa: E402


SCHEMA = "bg2-upscale-animation-manual-water-expansion-v1"
SOURCE_SCHEMA = "bg2-upscale-animation-alpha-feather-test-v1"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def load_mask(path: Path) -> np.ndarray:
    require(path.is_file(), f"masque absent : {path}")
    with Image.open(path) as opened:
        rgb = opened.convert("RGB")
        red = rgb.getchannel("R")
        require(
            ImageChops.difference(red, rgb.getchannel("G")).getbbox() is None
            and ImageChops.difference(red, rgb.getchannel("B")).getbbox() is None,
            "le masque doit être monochrome",
        )
    return np.asarray(red, dtype=np.uint8)


def add_masked_water(
    source: np.ndarray,
    mask: np.ndarray,
    *,
    sample_inset: int,
) -> tuple[np.ndarray, dict[str, int]]:
    old_height, width, channels = source.shape
    require(channels == 4 and mask.shape[1] == width and mask.shape[0] >= old_height,
            "dimensions du masque incompatibles avec la frame")
    require(sample_inset >= 0, "sample_inset négatif")

    output = np.zeros((mask.shape[0], width, 4), dtype=np.uint8)
    output[:old_height] = source
    padded_before = output.copy()
    current_alpha = output[:, :, 3]
    expose = mask > current_alpha

    visible = np.zeros(mask.shape, dtype=bool)
    visible[:old_height] = source[:, :, 3] >= 192
    core = binary_erosion(visible, iterations=sample_inset) if sample_inset else visible
    require(bool(core.any()), "aucun cœur d'eau opaque disponible pour échantillonnage")
    nearest = distance_transform_edt(~core, return_distances=False, return_indices=True)
    source_y = np.minimum(nearest[0], old_height - 1)
    source_x = nearest[1]
    output[expose, :3] = padded_before[source_y[expose], source_x[expose], :3]
    output[:, :, 3] = np.maximum(current_alpha, mask)

    untouched = mask == 0
    require(np.array_equal(output[untouched], padded_before[untouched]),
            "un pixel hors masque a été modifié")
    require(np.all(output[:, :, 3] >= current_alpha), "alpha source abaissé")
    return output, {
        "mask_nonzero_pixels": int(np.count_nonzero(mask)),
        "alpha_raised_pixels": int(np.count_nonzero(expose)),
        "new_canvas_alpha_pixels": int(np.count_nonzero(output[old_height:, :, 3])),
        "sample_inset_x4": sample_inset,
    }


def validate_derived_bam(source: bytes, derived: bytes, padding_x1: int) -> None:
    source_frames, _source_palette, source_transparent = decode_bam(source)
    derived_frames, _derived_palette, derived_transparent = decode_bam(derived)
    require(derived_transparent == source_transparent and len(derived_frames) == len(source_frames),
            "BAM dérivé invalide")
    for source_frame, derived_frame in zip(source_frames, derived_frames, strict=True):
        source_indices, source_cx, source_cy, _ = source_frame
        derived_indices, derived_cx, derived_cy, _ = derived_frame
        require(
            derived_indices.shape == (source_indices.shape[0] + padding_x1, source_indices.shape[1])
            and np.array_equal(derived_indices[:source_indices.shape[0]], source_indices)
            and bool((derived_indices[source_indices.shape[0]:] == source_transparent).all())
            and (derived_cx, derived_cy) == (source_cx, source_cy),
            "géométrie, pixels ou centres du BAM dérivé divergents",
        )
    require(
        cycle_metadata(source, len(source_frames)) == cycle_metadata(derived, len(derived_frames)),
        "cycles BAM modifiés",
    )


def build(args: argparse.Namespace) -> Path:
    resref = runtime.normalise_resref(args.resref)
    source_bam = args.source_bam.resolve()
    prototype = animation_paths.resolve_existing_run(args.prototype_run, [resref])
    base_pack = args.base_area_pack.resolve()
    mask_path = args.mask.resolve()
    output = animation_paths.resolve_run_destination(args.output_run, [resref])
    partial = output.with_name(output.name + ".partial")
    require(not output.exists() and not partial.exists(), f"sortie déjà présente : {output}")

    prototype_manifest = runtime.load_json(prototype / "manifest.json")
    require(
        prototype_manifest.get("schema") == SOURCE_SCHEMA
        and prototype_manifest.get("status") == "completed"
        and runtime.normalise_resref(str(prototype_manifest.get("resref", ""))) == resref,
        "prototype alpha incompatible",
    )
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
    require(len(logical_sizes) == len(physical_sizes) == 1, "géométrie source non uniforme")
    old_logical = next(iter(logical_sizes))
    old_physical = next(iter(physical_sizes))
    require(old_physical == (old_logical[0] * 4, old_logical[1] * 4), "source différente de x4")

    mask = load_mask(mask_path)
    require(mask.shape[1] == old_physical[0] and mask.shape[0] >= old_physical[1],
            f"masque {mask.shape[::-1]}, attendu largeur {old_physical[0]} et hauteur >= {old_physical[1]}")
    require(mask.shape[0] % 4 == 0, "hauteur du masque non divisible par quatre")
    new_physical = (old_physical[0], mask.shape[0])
    new_logical = (old_logical[0], mask.shape[0] // 4)
    padding_x1 = new_logical[1] - old_logical[1]
    require(padding_x1 > 0, "ce producteur exige un masque avec padding vertical")

    partial.mkdir(parents=True)
    raw_dir = partial / "raw_rgba"
    rgba_dir = partial / "rgba"
    alpha_dir = partial / "alpha"
    preview_dir = partial / "preview"
    bam_dir = partial / "derived-bam"
    pack_dir = partial / "03_runtime_pack"
    input_dir = partial / "manual-mask"
    for directory in (raw_dir, rgba_dir, alpha_dir, preview_dir, bam_dir, pack_dir, input_dir):
        directory.mkdir()
    sealed_mask_path = input_dir / "source.png"
    shutil.copyfile(mask_path, sealed_mask_path)
    require(bottom.sha256(sealed_mask_path) == bottom.sha256(mask_path),
            "copie du masque utilisateur divergente")

    reports: list[dict[str, Any]] = []
    asset_records: list[dict[str, Any]] = []
    by_name = {str(asset["name"]): asset for asset in resource["assets"]}
    before_preview: Image.Image | None = None
    after_preview: Image.Image | None = None
    for expected, (frame, proto_frame) in enumerate(zip(frames, prototype_frames, strict=True)):
        require(int(frame["frame"]) == int(proto_frame["frame"]) == expected, "frames non contiguës")
        source_name = str(proto_frame["runtime_asset"])
        source_path = (prototype / source_name).resolve()
        require(
            source_path.is_file()
            and bottom.sha256(source_path) == str(frame["sha256"]).lower()
            and source_path.stat().st_size == int(frame["bytes"]),
            f"frame {expected}: prototype différent du pack de base",
        )
        source_pixels = np.frombuffer(source_path.read_bytes(), dtype=np.uint8).reshape(
            old_physical[1], old_physical[0], 4
        )
        expanded, report = add_masked_water(source_pixels, mask, sample_inset=args.sample_inset_x4)
        asset_name = str(frame["asset"])
        raw_path = raw_dir / asset_name
        raw_path.write_bytes(expanded.tobytes(order="C"))
        rgba_path = rgba_dir / f"frame_{expected:03d}.png"
        alpha_path = alpha_dir / f"frame_{expected:03d}.png"
        Image.fromarray(expanded, "RGBA").save(rgba_path)
        Image.fromarray(expanded[:, :, 3], "L").save(alpha_path)
        frame["logical_size_x1"] = list(new_logical)
        frame["physical_size_x4"] = list(new_physical)
        frame["sha256"] = bottom.sha256(raw_path)
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
            padded = np.zeros_like(expanded)
            padded[:old_physical[1]] = source_pixels
            before_preview = Image.fromarray(padded, "RGBA")
            after_preview = Image.fromarray(expanded, "RGBA")

    resource["frames"] = frames
    resource["assets"] = asset_records
    registry_version = int(base_manifest["registry_version"])
    registry_path = pack_dir / runtime.REGISTRY_NAME
    registry_path.write_bytes(runtime.registry_v2_from_resources([resource], registry_version))
    for record in reports:
        source = partial / str(record["runtime_asset"])
        (pack_dir / source.name).write_bytes(source.read_bytes())
    raw_bytes = sum(int(item["bytes"]) for item in asset_records)
    pack_manifest = {
        "schema": runtime.PACK_SCHEMA,
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "scale": 4,
        "registry_version": registry_version,
        "runtime_contract": copy.deepcopy(base_manifest["runtime_contract"]),
        "registry": runtime.REGISTRY_NAME,
        "registry_sha256": bottom.sha256(registry_path),
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
    bottom.write_json(pack_manifest, pack_dir / "manifest.json")
    runtime.validate_v2_pack(pack_dir)

    source_bam_bytes = bottom.read_bam(source_bam)
    derived_bam = bottom.pad_bam_bottom(source_bam_bytes, padding_x1)
    validate_derived_bam(source_bam_bytes, derived_bam, padding_x1)
    derived_bam_path = bam_dir / f"{resref}.BAM"
    derived_bam_path.write_bytes(derived_bam)

    require(before_preview is not None and after_preview is not None, "preview impossible")
    bottom.labelled_pair(
        before_preview,
        after_preview,
        preview_dir / "frame_000-comparison.png",
        "avant: correction auto retirée",
        "après: masque utilisateur",
    )
    Image.fromarray(mask, "L").save(preview_dir / "user-mask.png")

    manifest = {
        "schema": SCHEMA,
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "resref": resref,
        "asset_ids": [f"animations:bam:{resref}"],
        "source_prototype": prototype.as_posix(),
        "source_prototype_manifest_sha256": bottom.sha256(prototype / "manifest.json"),
        "source_bam": source_bam.as_posix(),
        "source_bam_sha256": bottom.sha256(source_bam),
        "source_mask": "manual-mask/source.png",
        "source_mask_sha256": bottom.sha256(sealed_mask_path),
        "base_area_pack": base_pack.as_posix(),
        "base_area_pack_manifest_sha256": bottom.sha256(base_pack / "manifest.json"),
        "operation": {
            "type": "user-mask-water-texture-expansion",
            "alpha_formula": "max(previous_alpha, grayscale_user_mask)",
            "rgb_formula": "nearest eroded opaque water sample from the same animation frame",
            "sample_inset_x4": args.sample_inset_x4,
            "black_mask_policy": "padded source byte-identical",
            "old_logical_size_x1": list(old_logical),
            "new_logical_size_x1": list(new_logical),
            "centres": "unchanged",
            "cycles": "unchanged",
            "automatic_bottom_retime": "not applied",
        },
        "derived_bam": f"derived-bam/{resref}.BAM",
        "derived_bam_sha256": bottom.sha256(derived_bam_path),
        "runtime_pack": "03_runtime_pack",
        "runtime_pack_manifest_sha256": bottom.sha256(pack_dir / "manifest.json"),
        "frames": reports,
        "previews": ["preview/frame_000-comparison.png", "preview/user-mask.png"],
        "qa_status": "pending-explicit-user-approval",
    }
    bottom.write_json(manifest, partial / "manifest.json")
    partial.replace(output)
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True)
    parser.add_argument("--source-bam", type=Path, required=True)
    parser.add_argument("--prototype-run", required=True)
    parser.add_argument("--base-area-pack", type=Path, required=True)
    parser.add_argument("--mask", type=Path, required=True)
    parser.add_argument("--output-run", required=True)
    parser.add_argument("--sample-inset-x4", type=int, default=8)
    return parser.parse_args()


def main() -> None:
    output = build(parse_args())
    print(output)


if __name__ == "__main__":
    main()
