"""Build one immutable x4 projectile/effect runtime pack from a sealed spatial run."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageChops, ImageFilter
from scipy.ndimage import binary_fill_holes, distance_transform_edt


REPO_ROOT = Path(__file__).resolve().parents[2]
RUN_SCHEMA_VERSION = 1
FRAME_SCHEMA = "bg2-upscale-animation-frames-x1-v1"
SPATIAL_SCHEMA = "bg2-upscale-animation-frames-v1"
INTERPOLATION_SCHEMA = "bg2-upscale-effect-interpolation-30fps-v1"
PACK_SCHEMA = "bg2-upscale-effect-animation-runtime-pack-v1"
RUNTIME_GEOMETRY_SCHEMA = "bg2-upscale-effect-runtime-geometry-v1"
ALPHA_POLICY_SCHEMA = "bg2-upscale-effect-alpha-policy-v1"
REGISTRY_MAGIC = b"IEEEFX4\0"
REGISTRY_VERSION = 1
TIMELINE_REGISTRY_VERSION = 2
REGISTRY_NAME = "EffectAnimations-X4.registry"
MAX_FRAME_DIMENSION = 2048


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"manifeste absent : {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"manifeste invalide : {path}")
    return payload


def relative_to_repo(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError as exc:
        raise RuntimeError(f"chemin hors workspace : {path}") from exc


def require_relative(parent: Path, value: str, label: str) -> Path:
    target = (parent / value).resolve()
    try:
        target.relative_to(parent.resolve())
    except ValueError as exc:
        raise RuntimeError(f"{label} hors de son répertoire : {value}") from exc
    return target


def frame_asset_name(resref: str, frame_index: int) -> str:
    return f"EFX4-{resref}-frame{frame_index:03d}.rgba"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def require_hash(path: Path, expected: str, label: str) -> str:
    digest = sha256_file(path)
    if digest != expected.upper():
        raise RuntimeError(f"hash {label} incohérent : {path}")
    return digest


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def crop_rgba(
    payload: bytes,
    source_size: list[int],
    crop_box_x1: list[int],
    *,
    scale: int = 4,
) -> bytes:
    source_width, source_height = source_size
    left, top, right, bottom = crop_box_x1
    physical_width = source_width * scale
    physical_height = source_height * scale
    if len(payload) != physical_width * physical_height * 4:
        raise RuntimeError("RGBA source absent ou tronqué")
    left *= scale
    top *= scale
    right *= scale
    bottom *= scale
    row_bytes = physical_width * 4
    cropped_row_bytes = (right - left) * 4
    source = memoryview(payload)
    rows = [
        source[y * row_bytes + left * 4:y * row_bytes + left * 4 + cropped_row_bytes]
        for y in range(top, bottom)
    ]
    return b"".join(rows)


def transform_rgba(
    payload: bytes,
    source_size: list[int],
    source_box_x1: list[int],
    target_size_x1: list[int],
    destination_box_x1: list[int],
    *,
    scale: int = 4,
    alpha_mask_x1: Image.Image | None = None,
    alpha_source_box_x1: list[int] | None = None,
    alpha_policy: dict[str, Any] | None = None,
    runtime_centre_x1: list[int] | None = None,
) -> bytes:
    source_width, source_height = source_size
    physical_source_size = (source_width * scale, source_height * scale)
    if len(payload) != physical_source_size[0] * physical_source_size[1] * 4:
        raise RuntimeError("RGBA source absent ou tronqué")
    source_box = tuple(value * scale for value in source_box_x1)
    destination_box = tuple(value * scale for value in destination_box_x1)
    destination_size = (
        destination_box[2] - destination_box[0],
        destination_box[3] - destination_box[1],
    )
    source = Image.frombytes("RGBA", physical_source_size, payload)
    region = source.crop(source_box)
    if region.size != destination_size:
        region = region.resize(destination_size, Image.Resampling.LANCZOS)
    if alpha_mask_x1 is not None:
        mask_box = alpha_source_box_x1 or source_box_x1
        alpha = alpha_mask_x1.crop(tuple(mask_box))
        if alpha.size != destination_size:
            alpha = alpha.resize(destination_size, Image.Resampling.LANCZOS)
        region.putalpha(alpha)
    if alpha_policy is not None and alpha_policy.get("mode") == "runtime-rgb-luminance":
        low = alpha_policy["luminance_low"]
        high = alpha_policy["luminance_high"]
        region_pixels = region.tobytes()
        values = bytearray(region.width * region.height)
        for pixel_index, offset in enumerate(range(0, len(region_pixels), 4)):
            luminance = sum(region_pixels[offset:offset + 3]) / 3.0
            ramp = min(1.0, max(0.0, (luminance - low) / (high - low)))
            ramp = ramp * ramp * (3.0 - 2.0 * ramp)
            values[pixel_index] = round(region_pixels[offset + 3] * ramp)
        region.putalpha(Image.frombytes("L", region.size, bytes(values)))
    if alpha_policy is not None and alpha_policy.get("alpha_erode_radius_x4", 0):
        radius = alpha_policy["alpha_erode_radius_x4"]
        region.putalpha(region.getchannel("A").filter(ImageFilter.MinFilter(radius * 2 + 1)))
    if alpha_policy is not None and alpha_policy.get("alpha_gaussian_sigma_x4", 0.0):
        alpha = region.getchannel("A")
        smoothed = alpha.filter(ImageFilter.GaussianBlur(alpha_policy["alpha_gaussian_sigma_x4"]))
        region.putalpha(ImageChops.darker(alpha, smoothed))
    target = Image.new(
        "RGBA", (target_size_x1[0] * scale, target_size_x1[1] * scale), (0, 0, 0, 0)
    )
    target.paste(region, destination_box[:2])
    pixels = bytearray(target.tobytes())
    if alpha_policy is not None and alpha_policy.get("mode") == "runtime-radial":
        if runtime_centre_x1 is None:
            raise RuntimeError("centre runtime absent pour le masque radial")
        centre_x = runtime_centre_x1[0] * scale
        centre_y = runtime_centre_x1[1] * scale
        outer_x = float(alpha_policy["outer_radius_x_x1"]) * scale
        outer_y = float(alpha_policy["outer_radius_y_x1"]) * scale
        inner = float(alpha_policy["inner_fraction"])
        physical_width = target_size_x1[0] * scale
        physical_height = target_size_x1[1] * scale
        for y in range(physical_height):
            for x in range(physical_width):
                distance = (
                    ((x + 0.5 - centre_x) / outer_x) ** 2
                    + ((y + 0.5 - centre_y) / outer_y) ** 2
                ) ** 0.5
                ramp = min(1.0, max(0.0, (1.0 - distance) / (1.0 - inner)))
                ramp = ramp * ramp * (3.0 - 2.0 * ramp)
                offset = (y * physical_width + x) * 4
                pixels[offset + 3] = round(pixels[offset + 3] * ramp)
    if alpha_policy is not None and alpha_policy.get("mode") in {
        "runtime-inner-feather",
        "runtime-exterior-feather",
    }:
        radius = float(alpha_policy["inner_radius_x4"])
        opacity = float(alpha_policy["global_opacity"])
        values = np.frombuffer(pixels, dtype=np.uint8).reshape(
            target_size_x1[1] * scale, target_size_x1[0] * scale, 4
        ).copy()
        source_alpha = values[:, :, 3]
        silhouette = source_alpha > 0
        if alpha_policy["mode"] == "runtime-exterior-feather":
            silhouette = binary_fill_holes(silhouette)
        distance = distance_transform_edt(silhouette)
        ramp = np.clip(distance / radius, 0.0, 1.0)
        values[:, :, 3] = np.rint(source_alpha * opacity * ramp).astype(np.uint8)
        pixels = bytearray(values.tobytes())
    if alpha_policy is not None and alpha_policy.get("rgb_alpha_mode") == "premultiply":
        for offset in range(0, len(pixels), 4):
            alpha_value = pixels[offset + 3]
            pixels[offset] = (pixels[offset] * alpha_value + 127) // 255
            pixels[offset + 1] = (pixels[offset + 1] * alpha_value + 127) // 255
            pixels[offset + 2] = (pixels[offset + 2] * alpha_value + 127) // 255
    return bytes(pixels)


def validate_alpha_policy(alpha_policy: Any, *, label: str) -> dict[str, Any]:
    if not isinstance(alpha_policy, dict):
        raise RuntimeError(f"{label} invalide")
    mode = alpha_policy.get("mode")
    luminance_valid = (
        mode == "runtime-rgb-luminance"
        and type(alpha_policy.get("luminance_low")) in {int, float}
        and type(alpha_policy.get("luminance_high")) in {int, float}
        and 0 <= alpha_policy["luminance_low"] < alpha_policy["luminance_high"] <= 255
    )
    erosion_radius = alpha_policy.get("alpha_erode_radius_x4", 0)
    erosion_valid = type(erosion_radius) is int and 0 <= erosion_radius <= 2
    gaussian_sigma = alpha_policy.get("alpha_gaussian_sigma_x4", 0.0)
    gaussian_valid = (
        type(gaussian_sigma) in {int, float} and 0.0 <= gaussian_sigma <= 2.0
    )
    inner_feather_valid = (
        mode in {"runtime-inner-feather", "runtime-exterior-feather"}
        and type(alpha_policy.get("inner_radius_x4")) in {int, float}
        and 0.0 < float(alpha_policy["inner_radius_x4"]) <= 128.0
        and type(alpha_policy.get("global_opacity")) in {int, float}
        and 0.0 < float(alpha_policy["global_opacity"]) <= 1.0
    )
    if (
        not (luminance_valid or inner_feather_valid)
        or not erosion_valid
        or not gaussian_valid
        or alpha_policy.get("rgb_alpha_mode") != "premultiply"
    ):
        raise RuntimeError(f"{label} invalide")
    return dict(alpha_policy)


def validate_external_alpha_policy(
    resref: str,
    frames_x1: dict[str, Any],
    path: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = load_json(path)
    if (
        payload.get("schema") != ALPHA_POLICY_SCHEMA
        or payload.get("resref") != resref
        or str(payload.get("source_bam_sha256", "")).upper()
        != str(frames_x1.get("source_sha256", "")).upper()
    ):
        raise RuntimeError("politique alpha liée à une autre source BAM")
    alpha_policy = validate_alpha_policy(payload.get("alpha_policy"), label="politique alpha")
    return alpha_policy, {
        "path": relative_to_repo(path),
        "sha256": sha256_file(path),
        "schema": ALPHA_POLICY_SCHEMA,
    }


def source_rgb_alpha_mask(
    frame_index: int,
    frames_x1: dict[str, Any],
    spatial: dict[str, Any],
    alpha_policy: dict[str, Any],
) -> Image.Image:
    mode = alpha_policy.get("mode")
    if mode not in {"source-rgb-key", "source-rgb-luminance"}:
        raise RuntimeError("politique alpha runtime inconnue")
    source_frames = frames_x1.get("frames")
    source = spatial.get("source")
    if not isinstance(source_frames, list) or not isinstance(source, dict):
        raise RuntimeError("source RGB x1 absente pour le masque alpha runtime")
    if frame_index < 0 or frame_index >= len(source_frames):
        raise RuntimeError("frame source alpha runtime hors limites")
    frame = source_frames[frame_index]
    rgb_root = require_relative(REPO_ROOT, str(source.get("rgb", "")), "RGB source x1")
    rgb_path = require_relative(rgb_root, str(frame.get("file", "")), "frame RGB source x1")
    require_hash(rgb_path, str(frame.get("rgb_sha256", "")), "RGB source x1")
    alpha_root = require_relative(REPO_ROOT, str(source.get("alpha", "")), "alpha source x1")
    alpha_path = require_relative(
        alpha_root, str(frame.get("file", "")), "frame alpha source x1"
    )
    require_hash(alpha_path, str(frame.get("alpha_sha256", "")), "alpha source x1")
    with Image.open(rgb_path) as image:
        rgb = image.convert("RGB")
    with Image.open(alpha_path) as image:
        source_alpha = image.convert("L")
    if list(rgb.size) != frame.get("source_size") or source_alpha.size != rgb.size:
        raise RuntimeError("dimensions RGB/alpha source x1 incompatibles")
    pixels = rgb.tobytes()
    source_alpha_bytes = source_alpha.tobytes()
    if mode == "source-rgb-key":
        threshold = alpha_policy["transparent_max_channel"]
        mask = bytes(
            0
            if max(pixels[offset:offset + 3]) <= threshold
            else source_alpha_bytes[offset // 3]
            for offset in range(0, len(pixels), 3)
        )
    else:
        low = alpha_policy["luminance_low"]
        high = alpha_policy["luminance_high"]
        values = bytearray(len(source_alpha_bytes))
        for pixel_index, offset in enumerate(range(0, len(pixels), 3)):
            luminance = sum(pixels[offset:offset + 3]) / 3.0
            ramp = min(1.0, max(0.0, (luminance - low) / (high - low)))
            ramp = ramp * ramp * (3.0 - 2.0 * ramp)
            values[pixel_index] = round(source_alpha_bytes[pixel_index] * ramp)
        mask = bytes(values)
    return Image.frombytes("L", rgb.size, mask)


def validate_runtime_geometry(
    resref: str,
    frames_x1: dict[str, Any],
    path: Path,
) -> tuple[dict[int, dict[str, Any]], dict[str, Any]]:
    payload = load_json(path)
    if (
        payload.get("schema") != RUNTIME_GEOMETRY_SCHEMA
        or payload.get("resref") != resref
        or str(payload.get("source_bam_sha256", "")).upper()
        != str(frames_x1.get("source_sha256", "")).upper()
    ):
        raise RuntimeError("géométrie runtime liée à une autre source BAM")
    source_frames = frames_x1.get("frames")
    geometry_frames = payload.get("frames")
    if (
        not isinstance(source_frames, list)
        or not isinstance(geometry_frames, list)
        or len(geometry_frames) != len(source_frames)
        or [item.get("frame") for item in geometry_frames] != list(range(len(source_frames)))
    ):
        raise RuntimeError("géométrie runtime incomplète ou non contiguë")

    alpha_policy = payload.get("alpha_policy")
    if alpha_policy is not None:
        if not isinstance(alpha_policy, dict):
            raise RuntimeError("politique alpha runtime invalide")
        mode = alpha_policy.get("mode")
        key_valid = (
            mode == "source-rgb-key"
            and type(alpha_policy.get("transparent_max_channel")) is int
            and 0 <= alpha_policy["transparent_max_channel"] < 255
        )
        luminance_valid = (
            mode in {"source-rgb-luminance", "runtime-rgb-luminance"}
            and type(alpha_policy.get("luminance_low")) in {int, float}
            and type(alpha_policy.get("luminance_high")) in {int, float}
            and 0 <= alpha_policy["luminance_low"] < alpha_policy["luminance_high"] <= 255
        )
        radial_valid = (
            mode == "runtime-radial"
            and type(alpha_policy.get("outer_radius_x_x1")) in {int, float}
            and type(alpha_policy.get("outer_radius_y_x1")) in {int, float}
            and type(alpha_policy.get("inner_fraction")) in {int, float}
            and alpha_policy["outer_radius_x_x1"] > 0
            and alpha_policy["outer_radius_y_x1"] > 0
            and 0 <= alpha_policy["inner_fraction"] < 1
        )
        inner_feather_valid = (
            mode in {"runtime-inner-feather", "runtime-exterior-feather"}
            and type(alpha_policy.get("inner_radius_x4")) in {int, float}
            and 0.0 < float(alpha_policy["inner_radius_x4"]) <= 128.0
            and type(alpha_policy.get("global_opacity")) in {int, float}
            and 0.0 < float(alpha_policy["global_opacity"]) <= 1.0
        )
        if (
            not (key_valid or luminance_valid or radial_valid or inner_feather_valid)
            or alpha_policy.get("rgb_alpha_mode") != "premultiply"
        ):
            raise RuntimeError("politique alpha runtime invalide")

    result: dict[int, dict[str, Any]] = {}
    for index, (source_frame, geometry) in enumerate(zip(source_frames, geometry_frames)):
        source_size = source_frame.get("source_size")
        centre = source_frame.get("centre")
        canvas_offset = source_frame.get("canvas_offset")
        logical = geometry.get("logical_size_x1")
        crop = geometry.get("crop_box_x1")
        mapping = geometry.get("mapping")
        runtime_centre = geometry.get("runtime_centre_x1")
        if (
            not isinstance(source_size, list)
            or len(source_size) != 2
            or not isinstance(centre, list)
            or len(centre) != 2
            or not isinstance(canvas_offset, list)
            or len(canvas_offset) != 2
            or not isinstance(logical, list)
            or len(logical) != 2
            or not isinstance(runtime_centre, list)
            or len(runtime_centre) != 2
            or not all(
                type(value) is int
                for value in source_size + centre + canvas_offset + logical + runtime_centre
            )
        ):
            raise RuntimeError(f"frame {index}: géométrie runtime invalide")
        width, height = logical
        if width <= 0 or height <= 0 or width > MAX_FRAME_DIMENSION or height > MAX_FRAME_DIMENSION:
            raise RuntimeError(f"frame {index}: dimensions runtime invalides")
        if alpha_policy is not None and alpha_policy.get("mode") == "runtime-radial":
            if (
                alpha_policy["outer_radius_x_x1"]
                > min(runtime_centre[0], width - runtime_centre[0])
                or alpha_policy["outer_radius_y_x1"]
                > min(runtime_centre[1], height - runtime_centre[1])
            ):
                raise RuntimeError(f"frame {index}: masque radial hors géométrie runtime")
        if mapping is None:
            if (
                not isinstance(crop, list)
                or len(crop) != 4
                or not all(type(value) is int for value in crop)
            ):
                raise RuntimeError(f"frame {index}: crop runtime invalide")
            source_box = crop
            destination_box = [0, 0, width, height]
            mapping_mode = "crop"
        else:
            if (
                crop is not None
                or not isinstance(mapping, dict)
                or mapping.get("mode") != "contain"
                or not isinstance(mapping.get("source_box_x1"), list)
                or len(mapping["source_box_x1"]) != 4
                or not isinstance(mapping.get("destination_box_x1"), list)
                or len(mapping["destination_box_x1"]) != 4
                or not all(
                    type(value) is int
                    for value in mapping["source_box_x1"] + mapping["destination_box_x1"]
                )
            ):
                raise RuntimeError(f"frame {index}: reframe runtime invalide")
            source_box = mapping["source_box_x1"]
            destination_box = mapping["destination_box_x1"]
            mapping_mode = "contain"
        left, top, right, bottom = source_box
        destination_left, destination_top, destination_right, destination_bottom = destination_box
        source_width = right - left
        source_height = bottom - top
        destination_width = destination_right - destination_left
        destination_height = destination_bottom - destination_top
        anchor_matches = (
            (centre[0] - left) * destination_width
            == (runtime_centre[0] - destination_left) * source_width
            and (centre[1] - top) * destination_height
            == (runtime_centre[1] - destination_top) * source_height
        )
        if (
            source_width <= 0
            or source_height <= 0
            or destination_width <= 0
            or destination_height <= 0
            or left < 0
            or top < 0
            or right > source_size[0]
            or bottom > source_size[1]
            or destination_left < 0
            or destination_top < 0
            or destination_right > width
            or destination_bottom > height
            or not anchor_matches
            or (mapping_mode == "crop" and [source_width, source_height] != logical)
            or (
                mapping_mode == "contain"
                and source_width * destination_height != source_height * destination_width
            )
        ):
            raise RuntimeError(f"frame {index}: mapping runtime incompatible avec l'ancre BAM")
        result[index] = {
            "logical_size_x1": logical,
            "mapping_mode": mapping_mode,
            "source_box_x1": source_box,
            "aligned_source_box_x1": [
                left + canvas_offset[0],
                top + canvas_offset[1],
                right + canvas_offset[0],
                bottom + canvas_offset[1],
            ],
            "destination_box_x1": destination_box,
            "runtime_centre_x1": runtime_centre,
            "alpha_policy": alpha_policy,
        }
        if mapping_mode == "crop":
            result[index]["crop_box_x1"] = source_box

    observed_slots = payload.get("observed_slots")
    expected_slots = [
        {"cycle": int(cycle["cycle"]), "slot": slot, "frame": int(frame)}
        for cycle in frames_x1.get("cycles", [])
        for slot, frame in enumerate(cycle.get("frame_indices", []))
    ]
    if not isinstance(observed_slots, list) or len(observed_slots) != len(expected_slots):
        raise RuntimeError("géométrie runtime sans mesure de chaque slot BAM")
    for expected, observed in zip(expected_slots, observed_slots):
        frame = expected["frame"]
        if (
            not isinstance(observed, dict)
            or any(observed.get(key) != value for key, value in expected.items())
            or observed.get("logical_size_x1") != result[frame]["logical_size_x1"]
        ):
            raise RuntimeError("mesures runtime incompatibles avec les slots BAM")
    evidence = {
        "path": relative_to_repo(path),
        "sha256": sha256_file(path),
        "schema": RUNTIME_GEOMETRY_SCHEMA,
        "observation": payload.get("observation"),
    }
    return result, evidence


def validate_input(resref: str, run_dir: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    descriptor_path = run_dir / "run.json"
    descriptor = load_json(descriptor_path)
    if (
        descriptor.get("schema_version") != RUN_SCHEMA_VERSION
        or descriptor.get("domain") != "effects"
        or descriptor.get("run_id") != run_dir.name
        or descriptor.get("result", {}).get("sealed") is not True
        or descriptor.get("result", {}).get("status") != "completed"
        or descriptor.get("pipeline", {}).get("id") != "effects.spatial-x4.v1"
        or descriptor.get("asset_ids") != [f"effects:bam:{resref}"]
    ):
        raise RuntimeError("run spatial non scellé ou incompatible")

    spatial_outputs = [
        item for item in descriptor.get("outputs", []) if item.get("role") == "spatial-manifest"
    ]
    if len(spatial_outputs) != 1:
        raise RuntimeError("run spatial sans manifeste de sortie unique")
    spatial_record = spatial_outputs[0]
    spatial_path = require_relative(REPO_ROOT, str(spatial_record.get("path", "")), "manifeste spatial")
    require_hash(spatial_path, str(spatial_record.get("sha256", "")), "manifeste spatial")
    spatial = load_json(spatial_path)
    if spatial.get("schema") != SPATIAL_SCHEMA or spatial.get("status") != "completed" or spatial.get("scale") != 4:
        raise RuntimeError("manifeste spatial incomplet ou non x4")

    source = spatial.get("source")
    if not isinstance(source, dict):
        raise RuntimeError("provenance x1 absente")
    source_manifest = require_relative(
        REPO_ROOT, str(source.get("frame_manifest", "")), "manifeste x1"
    )
    require_hash(source_manifest, str(source.get("frame_manifest_sha256", "")), "manifeste x1")
    frames_x1 = load_json(source_manifest)
    if frames_x1.get("schema") != FRAME_SCHEMA or frames_x1.get("source_sha256") is None:
        raise RuntimeError("manifeste x1 incompatible")
    return descriptor, frames_x1, spatial


def validate_interpolation_input(
    resref: str,
    run_dir: Path,
    parent_descriptor: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], Path]:
    descriptor_path = run_dir / "run.json"
    descriptor = load_json(descriptor_path)
    if (
        descriptor.get("schema_version") != RUN_SCHEMA_VERSION
        or descriptor.get("domain") != "effects"
        or descriptor.get("run_id") != run_dir.name
        or descriptor.get("result", {}).get("sealed") is not True
        or descriptor.get("result", {}).get("status") != "completed"
        or descriptor.get("pipeline", {}).get("id") != "effects.interpolation-30fps.v1"
        or descriptor.get("asset_ids") != [f"effects:bam:{resref}"]
        or descriptor.get("provenance", {}).get("parents") != [parent_descriptor["run_id"]]
    ):
        raise RuntimeError("run d'interpolation non scellé ou incompatible")
    parent_outputs = {
        (item.get("path"), str(item.get("sha256", "")).upper(), item.get("bytes"))
        for item in parent_descriptor.get("outputs", [])
    }
    bindings = {
        (item.get("path"), str(item.get("sha256", "")).upper(), item.get("bytes"))
        for item in descriptor.get("inputs", [])
        if item.get("role") == "parent-spatial-output"
    }
    if not parent_outputs & bindings:
        raise RuntimeError("run interpolation non lié à une sortie spatiale parent")
    records = [item for item in descriptor.get("outputs", []) if item.get("role") == "interpolation-manifest"]
    if len(records) != 1:
        raise RuntimeError("run interpolation sans manifeste de sortie unique")
    record = records[0]
    manifest_path = require_relative(REPO_ROOT, str(record.get("path", "")), "manifeste interpolation")
    require_hash(manifest_path, str(record.get("sha256", "")), "manifeste interpolation")
    manifest = load_json(manifest_path)
    if (
        manifest.get("schema") != INTERPOLATION_SCHEMA
        or manifest.get("status") != "completed"
        or manifest.get("resref") != resref
        or manifest.get("scale") != 4
    ):
        raise RuntimeError("manifeste interpolation incomplet")
    return descriptor, manifest, manifest_path


def build_pack_record(
    resref: str,
    frames_x1: dict[str, Any],
    spatial: dict[str, Any],
    spatial_dir: Path,
    runtime_geometry: dict[int, dict[str, Any]] | None = None,
    alpha_policy: dict[str, Any] | None = None,
) -> tuple[bytes, list[dict[str, Any]]]:
    encoded_resref = resref.encode("ascii")
    if not encoded_resref or len(encoded_resref) > 8 or not all(
        character.isalnum() or character == "_" for character in resref
    ):
        raise RuntimeError(f"resref invalide : {resref}")

    frame_count = frames_x1.get("frame_count")
    if type(frame_count) is not int or frame_count <= 0:
        raise RuntimeError("nombre de frames x1 invalide")
    source_frames = frames_x1.get("frames")
    scaled_frames = spatial.get("frames")
    if not isinstance(source_frames, list) or not isinstance(scaled_frames, list):
        raise RuntimeError("liste de frames absente")
    if len(source_frames) != frame_count or len(scaled_frames) != frame_count:
        raise RuntimeError("nombre de frames x1/x4 divergent")

    registry = bytearray(encoded_resref.ljust(8, b"\0"))
    cycles = frames_x1.get("cycles")
    if not isinstance(cycles, list) or not cycles:
        raise RuntimeError("cycles BAM absents")
    ordered_cycles = sorted(cycles, key=lambda item: item.get("cycle", -1))
    if [item.get("cycle") for item in ordered_cycles] != list(range(len(ordered_cycles))):
        raise RuntimeError("cycles BAM non contigus")
    if len(ordered_cycles) > 256:
        raise RuntimeError("trop de cycles BAM")
    registry.extend(struct.pack("<II", frame_count, len(ordered_cycles)))

    assets: list[dict[str, Any]] = []
    alpha_masks: dict[int, Image.Image] = {}
    for index, (source_frame, scaled_frame) in enumerate(zip(source_frames, scaled_frames)):
        if source_frame.get("frame") != index or scaled_frame.get("frame") != index:
            raise RuntimeError("frames non contiguës")
        source_size = source_frame.get("source_size")
        logical_size = scaled_frame.get("logical_size_x1")
        physical_size = scaled_frame.get("physical_size_xn")
        if (
            not isinstance(source_size, list)
            or not isinstance(logical_size, list)
            or not isinstance(physical_size, list)
            or len(source_size) != 2
            or len(logical_size) != 2
            or len(physical_size) != 2
        ):
            raise RuntimeError(f"frame {index}: dimensions absentes")
        width, height = (int(value) for value in logical_size)
        if (
            width <= 0
            or height <= 0
            or width > MAX_FRAME_DIMENSION
            or height > MAX_FRAME_DIMENSION
            or source_size != logical_size
            or physical_size != [width * 4, height * 4]
        ):
            raise RuntimeError(f"frame {index}: géométrie x1/x4 invalide")
        raw_relative = scaled_frame.get("raw_rgba_xn")
        if not isinstance(raw_relative, str):
            raise RuntimeError(f"frame {index}: RGBA x4 absent")
        raw_path = require_relative(spatial_dir, raw_relative, f"frame {index}")
        expected_bytes = width * 4 * height * 4 * 4
        if not raw_path.is_file() or raw_path.stat().st_size != expected_bytes:
            raise RuntimeError(f"frame {index}: RGBA x4 absent ou tronqué")
        source_digest = require_hash(
            raw_path, str(scaled_frame.get("raw_rgba_xn_sha256", "")), f"frame {index}"
        )
        payload: bytes | None = None
        geometry = runtime_geometry.get(index) if runtime_geometry is not None else None
        if geometry is not None:
            alpha_policy = geometry.get("alpha_policy")
            alpha_mask = None
            if alpha_policy is not None and str(alpha_policy.get("mode", "")).startswith(
                "source-rgb-"
            ):
                if index not in alpha_masks:
                    alpha_masks[index] = source_rgb_alpha_mask(
                        index, frames_x1, spatial, alpha_policy
                    )
                alpha_mask = alpha_masks[index]
            payload = transform_rgba(
                raw_path.read_bytes(),
                logical_size,
                geometry["source_box_x1"],
                geometry["logical_size_x1"],
                geometry["destination_box_x1"],
                alpha_mask_x1=alpha_mask,
                alpha_source_box_x1=geometry["source_box_x1"],
                alpha_policy=alpha_policy,
                runtime_centre_x1=geometry["runtime_centre_x1"],
            )
            width, height = geometry["logical_size_x1"]
            expected_bytes = width * 4 * height * 4 * 4
            if len(payload) != expected_bytes:
                raise RuntimeError(f"frame {index}: reframe RGBA x4 incohérent")
            digest = sha256_bytes(payload)
        elif alpha_policy is not None:
            payload = transform_rgba(
                raw_path.read_bytes(), logical_size, [0, 0, width, height], logical_size,
                [0, 0, width, height], alpha_policy=alpha_policy,
            )
            digest = sha256_bytes(payload)
        else:
            digest = source_digest
        name = frame_asset_name(resref, index)
        registry.extend(struct.pack("<II", width, height))
        asset = {
            "frame": index,
            "asset": name,
            "source": relative_to_repo(raw_path),
            "source_sha256": source_digest,
            "sha256": digest,
            "bytes": expected_bytes,
            "logical_size_x1": [width, height],
            "physical_size_x4": [width * 4, height * 4],
        }
        if geometry is not None:
            asset.update(
                {
                    "source_logical_size_x1": logical_size,
                    "mapping": {
                        "mode": geometry["mapping_mode"],
                        "source_box_x1": geometry["source_box_x1"],
                        "destination_box_x1": geometry["destination_box_x1"],
                    },
                    "runtime_centre_x1": geometry["runtime_centre_x1"],
                    "alpha_policy": geometry.get("alpha_policy"),
                    "_payload": payload,
                }
            )
            if geometry["mapping_mode"] == "crop":
                asset["crop_box_x1"] = geometry["source_box_x1"]
        elif alpha_policy is not None:
            asset.update({"alpha_policy": alpha_policy, "_payload": payload})
        assets.append(asset)

    for cycle in ordered_cycles:
        frames = cycle.get("frame_indices")
        if not isinstance(frames, list) or not frames or len(frames) > 65536:
            raise RuntimeError("cycle BAM vide ou trop long")
        if any(type(frame) is not int or frame < 0 or frame >= frame_count for frame in frames):
            raise RuntimeError("cycle BAM avec frame invalide")
        registry.extend(struct.pack("<I", len(frames)))
        registry.extend(struct.pack(f"<{len(frames)}I", *frames))
    return bytes(registry), assets


def build_interpolated_pack_record(
    resref: str,
    interpolation: dict[str, Any],
    interpolation_dir: Path,
    frames_x1: dict[str, Any] | None = None,
    spatial: dict[str, Any] | None = None,
    runtime_geometry: dict[int, dict[str, Any]] | None = None,
    alpha_policy: dict[str, Any] | None = None,
) -> tuple[bytes, list[dict[str, Any]], dict[str, Any]]:
    frames = interpolation.get("frames")
    timing = interpolation.get("timing")
    if not isinstance(frames, list) or not frames or not isinstance(timing, dict):
        raise RuntimeError("frames ou timing interpolation absents")
    if [frame.get("frame") for frame in frames] != list(range(len(frames))):
        raise RuntimeError("frames interpolées non contiguës")
    native_fps = timing.get("native_fps")
    target_fps = timing.get("target_fps")
    native_indices = timing.get("native_frame_indices")
    timeline_indices = timing.get("timeline_frame_indices")
    if (
        not isinstance(native_fps, list)
        or not isinstance(target_fps, list)
        or len(native_fps) != 2
        or len(target_fps) != 2
        or not all(type(value) is int and value > 0 for value in native_fps + target_fps)
        or not isinstance(native_indices, list)
        or not isinstance(timeline_indices, list)
        or timeline_indices != list(range(len(frames)))
        or int(timing.get("timeline_phase_count", 0)) != len(frames)
        or not native_indices
        or any(type(value) is not int or value < 0 or value >= len(frames) for value in native_indices)
    ):
        raise RuntimeError("timing interpolation invalide")
    multiplier_numerator = target_fps[0] * native_fps[1]
    multiplier_denominator = native_fps[0] * target_fps[1]
    if multiplier_numerator <= multiplier_denominator or multiplier_numerator % multiplier_denominator:
        raise RuntimeError("ratio FPS interpolation invalide")
    if len(frames) != len(native_indices) * multiplier_numerator // multiplier_denominator:
        raise RuntimeError("nombre de phases interpolation incompatible avec le cycle natif")

    interpolation_geometry: dict[str, Any] | None = None
    if runtime_geometry is not None:
        geometries = list(runtime_geometry.values())
        if not geometries or any(geometry != geometries[0] for geometry in geometries[1:]):
            raise RuntimeError(
                "l'interpolation exige une géométrie runtime uniforme entre les slots natifs"
            )
        interpolation_geometry = geometries[0]

    registry = bytearray(resref.encode("ascii").ljust(8, b"\0"))
    registry.extend(struct.pack("<II", len(frames), 1))
    assets: list[dict[str, Any]] = []
    alpha_masks: dict[int, Image.Image] = {}
    for index, frame in enumerate(frames):
        logical = frame.get("logical_size_x1")
        physical = frame.get("physical_size_x4")
        raw_relative = frame.get("raw_rgba_x4")
        if (
            not isinstance(logical, list)
            or not isinstance(physical, list)
            or len(logical) != 2
            or len(physical) != 2
            or not all(type(value) is int and value > 0 for value in logical + physical)
            or physical != [logical[0] * 4, logical[1] * 4]
            or not isinstance(raw_relative, str)
        ):
            raise RuntimeError(f"frame interpolée {index}: géométrie absente ou invalide")
        raw_path = require_relative(interpolation_dir, raw_relative, f"frame interpolée {index}")
        expected_bytes = physical[0] * physical[1] * 4
        if not raw_path.is_file() or raw_path.stat().st_size != expected_bytes:
            raise RuntimeError(f"frame interpolée {index}: RGBA absent ou tronqué")
        source_digest = require_hash(
            raw_path, str(frame.get("raw_rgba_x4_sha256", "")), f"frame interpolée {index}"
        )
        payload: bytes | None = None
        runtime_logical = logical
        runtime_physical = physical
        digest = source_digest
        if interpolation_geometry is not None:
            alpha_policy = interpolation_geometry.get("alpha_policy")
            alpha_mask = None
            alpha_source_frame = frame.get("alpha_source_frame")
            if alpha_policy is not None and str(alpha_policy.get("mode", "")).startswith(
                "source-rgb-"
            ):
                if (
                    frames_x1 is None
                    or spatial is None
                    or type(alpha_source_frame) is not int
                ):
                    raise RuntimeError(
                        f"frame interpolée {index}: source alpha runtime absente"
                    )
                if alpha_source_frame not in alpha_masks:
                    alpha_masks[alpha_source_frame] = source_rgb_alpha_mask(
                        alpha_source_frame, frames_x1, spatial, alpha_policy
                    )
                alpha_mask = alpha_masks[alpha_source_frame]
            payload = transform_rgba(
                raw_path.read_bytes(),
                logical,
                interpolation_geometry["aligned_source_box_x1"],
                interpolation_geometry["logical_size_x1"],
                interpolation_geometry["destination_box_x1"],
                alpha_mask_x1=alpha_mask,
                alpha_source_box_x1=interpolation_geometry["source_box_x1"],
                alpha_policy=alpha_policy,
                runtime_centre_x1=interpolation_geometry["runtime_centre_x1"],
            )
            runtime_logical = interpolation_geometry["logical_size_x1"]
            runtime_physical = [runtime_logical[0] * 4, runtime_logical[1] * 4]
            expected_bytes = runtime_physical[0] * runtime_physical[1] * 4
            if len(payload) != expected_bytes:
                raise RuntimeError(f"frame interpolée {index}: reframe RGBA x4 incohérent")
            digest = sha256_bytes(payload)
        elif alpha_policy is not None:
            payload = transform_rgba(
                raw_path.read_bytes(), logical, [0, 0, logical[0], logical[1]], logical,
                [0, 0, logical[0], logical[1]], alpha_policy=alpha_policy,
            )
            digest = sha256_bytes(payload)
        registry.extend(struct.pack("<II", runtime_logical[0], runtime_logical[1]))
        asset = {
            "frame": index,
            "asset": frame_asset_name(resref, index),
            "source": relative_to_repo(raw_path),
            "source_sha256": source_digest,
            "sha256": digest,
            "bytes": expected_bytes,
            "logical_size_x1": runtime_logical,
            "physical_size_x4": runtime_physical,
            "alpha_source_frame": frame.get("alpha_source_frame"),
        }
        if interpolation_geometry is not None:
            asset.update(
                {
                    "source_logical_size_x1": logical,
                    "mapping": {
                        "mode": interpolation_geometry["mapping_mode"],
                        "source_box_x1": interpolation_geometry["source_box_x1"],
                        "aligned_source_box_x1": interpolation_geometry[
                            "aligned_source_box_x1"
                        ],
                        "destination_box_x1": interpolation_geometry[
                            "destination_box_x1"
                        ],
                    },
                    "runtime_centre_x1": interpolation_geometry["runtime_centre_x1"],
                    "alpha_policy": interpolation_geometry.get("alpha_policy"),
                    "_payload": payload,
                }
            )
            if interpolation_geometry["mapping_mode"] == "crop":
                asset["crop_box_x1"] = interpolation_geometry["aligned_source_box_x1"]
        elif alpha_policy is not None:
            asset.update({"alpha_policy": alpha_policy, "_payload": payload})
        assets.append(asset)
    registry.extend(struct.pack(f"<I{len(native_indices)}I", len(native_indices), *native_indices))
    registry.extend(
        struct.pack(
            "<IIIII",
            native_fps[0], native_fps[1], target_fps[0], target_fps[1], len(timeline_indices),
        )
    )
    registry.extend(struct.pack(f"<{len(timeline_indices)}I", *timeline_indices))
    timeline = {
        "native_fps": native_fps,
        "target_fps": target_fps,
        "phase_count": len(timeline_indices),
        "native_frame_indices": native_indices,
        "timeline_frame_indices": timeline_indices,
    }
    return bytes(registry), assets, timeline


def write_pack(output: Path, registry: bytes, assets: list[dict[str, Any]],
               descriptor: dict[str, Any], frames_x1: dict[str, Any], spatial: dict[str, Any],
               *, registry_version: int = REGISTRY_VERSION,
               timeline: dict[str, Any] | None = None,
               interpolation_descriptor: dict[str, Any] | None = None,
               runtime_geometry_evidence: dict[str, Any] | None = None,
               alpha_policy_evidence: dict[str, Any] | None = None) -> dict[str, Any]:
    if output.exists():
        if not output.is_dir():
            raise RuntimeError(f"sortie runtime non répertoire : {output}")
        residual = {path.name for path in output.iterdir()} - {"README.md"}
        if residual:
            raise RuntimeError(f"sortie runtime déjà occupée : {output}")
    else:
        output.mkdir(parents=True)
    try:
        registry_path = output / REGISTRY_NAME
        registry_path.write_bytes(registry)
        manifest_assets: list[dict[str, Any]] = []
        for asset in assets:
            target = output / asset["asset"]
            payload = asset.get("_payload")
            if isinstance(payload, bytes):
                target.write_bytes(payload)
            else:
                source = REPO_ROOT / asset["source"]
                shutil.copyfile(source, target)
            if sha256_file(target) != asset["sha256"]:
                raise RuntimeError(f"copie runtime corrompue : {asset['asset']}")
            manifest_assets.append(
                {key: value for key, value in asset.items() if not key.startswith("_")}
            )
        manifest = {
            "schema": PACK_SCHEMA,
            "status": "completed",
            "created_utc": utc_now(),
            "resref": descriptor["asset_ids"][0].rsplit(":", 1)[-1],
            "scale": 4,
            "registry": REGISTRY_NAME,
            "registry_magic": REGISTRY_MAGIC.rstrip(b"\0").decode("ascii"),
            "registry_version": registry_version,
            "registry_sha256": sha256_file(registry_path),
            "registry_bytes": registry_path.stat().st_size,
            "frame_count": len(assets),
            "cycles": frames_x1["cycles"],
            "frames": manifest_assets,
            "source": {
                "spatial_run": descriptor["run_id"],
                "spatial_run_descriptor_sha256": sha256_file(
                    REPO_ROOT / "effects" / "ressources" / descriptor["asset_ids"][0].rsplit(":", 1)[-1] / "runs" / descriptor["run_id"] / "run.json"
                ),
                "source_bam_sha256": frames_x1["source_sha256"],
                "spatial_manifest_sha256": sha256_file(
                    REPO_ROOT / next(
                        item["path"] for item in descriptor["outputs"] if item["role"] == "spatial-manifest"
                    )
                ),
            },
        }
        if timeline is not None:
            manifest["timeline"] = timeline
        if interpolation_descriptor is not None:
            manifest["source"]["interpolation_run"] = interpolation_descriptor["run_id"]
            manifest["source"]["interpolation_run_descriptor_sha256"] = sha256_file(
                REPO_ROOT / "effects" / "ressources" / descriptor["asset_ids"][0].rsplit(":", 1)[-1]
                / "runs" / interpolation_descriptor["run_id"] / "run.json"
            )
        if runtime_geometry_evidence is not None:
            manifest["source"]["runtime_geometry"] = runtime_geometry_evidence
        if alpha_policy_evidence is not None:
            manifest["source"]["alpha_policy"] = alpha_policy_evidence
        (output / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return manifest
    except Exception:
        # A partial pack is deliberately left visible for diagnosis and cannot
        # be used: the runtime requires registry + all exact payloads.
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resref", required=True, help="BAM effect resref")
    parser.add_argument("--spatial-run", required=True, help="sealed spatial run id")
    parser.add_argument(
        "--interpolation-run",
        help="sealed 30 FPS derived run; omitted builds the native-cadence x4 pack",
    )
    parser.add_argument(
        "--output",
        default="engine/InfinityEngine-Enhancer/source-patchee/assets/effects",
        help="empty runtime-pack destination relative to the workspace",
    )
    parser.add_argument(
        "--runtime-geometry",
        help="measured runtime geometry manifest relative to the workspace",
    )
    parser.add_argument(
        "--alpha-policy",
        help="versioned alpha policy relative to the workspace",
    )
    parser.add_argument("--run", action="store_true", help="write the runtime pack")
    args = parser.parse_args(argv)
    try:
        resref = args.resref.strip().upper()
        run_dir = REPO_ROOT / "effects" / "ressources" / resref / "runs" / args.spatial_run
        output = require_relative(REPO_ROOT, args.output, "sortie runtime")
        descriptor, frames_x1, spatial = validate_input(resref, run_dir)
        runtime_geometry: dict[int, dict[str, Any]] | None = None
        runtime_geometry_evidence: dict[str, Any] | None = None
        alpha_policy: dict[str, Any] | None = None
        alpha_policy_evidence: dict[str, Any] | None = None
        if args.runtime_geometry:
            geometry_path = require_relative(
                REPO_ROOT, args.runtime_geometry, "géométrie runtime"
            )
            runtime_geometry, runtime_geometry_evidence = validate_runtime_geometry(
                resref, frames_x1, geometry_path
            )
        if args.alpha_policy:
            if runtime_geometry is not None:
                raise RuntimeError("politique alpha externe incompatible avec géométrie runtime")
            alpha_policy_path = require_relative(REPO_ROOT, args.alpha_policy, "politique alpha")
            alpha_policy, alpha_policy_evidence = validate_external_alpha_policy(
                resref, frames_x1, alpha_policy_path
            )
        spatial_path = REPO_ROOT / next(
            item["path"] for item in descriptor["outputs"] if item["role"] == "spatial-manifest"
        )
        registry_version = REGISTRY_VERSION
        timeline: dict[str, Any] | None = None
        interpolation_descriptor: dict[str, Any] | None = None
        if args.interpolation_run:
            interpolation_dir = (
                REPO_ROOT / "effects" / "ressources" / resref / "runs" / args.interpolation_run
            )
            interpolation_descriptor, interpolation, interpolation_path = validate_interpolation_input(
                resref, interpolation_dir, descriptor
            )
            registry_record, assets, timeline = build_interpolated_pack_record(
                resref,
                interpolation,
                interpolation_path.parent,
                frames_x1,
                spatial,
                runtime_geometry,
                alpha_policy,
            )
            registry_version = TIMELINE_REGISTRY_VERSION
        else:
            registry_record, assets = build_pack_record(
                resref, frames_x1, spatial, spatial_path.parent, runtime_geometry, alpha_policy
            )
        registry = bytearray(REGISTRY_MAGIC)
        registry.extend(struct.pack("<IIII", registry_version, 4, 1, 0))
        registry.extend(registry_record)
        plan = {
            "resref": resref,
            "spatial_run": args.spatial_run,
            "output": relative_to_repo(output),
            "registry": REGISTRY_NAME,
            "registry_version": registry_version,
            "registry_bytes": len(registry),
            "frame_count": len(assets),
            "frame_bytes": sum(int(asset["bytes"]) for asset in assets),
            "interpolation_run": args.interpolation_run,
            "runtime_geometry": runtime_geometry_evidence,
            "alpha_policy": alpha_policy_evidence,
            "write": bool(args.run),
        }
        if not args.run:
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            return 0
        manifest = write_pack(
            output, bytes(registry), assets, descriptor, frames_x1, spatial,
            registry_version=registry_version, timeline=timeline,
            interpolation_descriptor=interpolation_descriptor,
            runtime_geometry_evidence=runtime_geometry_evidence,
            alpha_policy_evidence=alpha_policy_evidence,
        )
        plan["manifest_sha256"] = sha256_file(output / "manifest.json")
        plan["registry_sha256"] = manifest["registry_sha256"]
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0
    except (KeyError, OSError, RuntimeError, TypeError, ValueError) as error:
        print(f"erreur: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
