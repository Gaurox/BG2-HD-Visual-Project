"""Offline ReboutCX x4-to-x2 prototype runner for indexed creature sprites."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import struct
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import scipy
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt

from reboutcx_quantize import (
    CHARACTER_CHMB1_CLASSES_ID,
    CHARACTER_CHMB1_PALETTE_ID,
    QUANTIZER_ID,
    character_chmb1_palette_rgb,
    quantize_classed_oklab,
    reconstruct_rgba,
    semantic_classes_for_job,
    source_representatives,
)
from bg2lib import load_key, resolve_resource
from run_creature_sprite_x2 import (
    LEGACY_UPSCALE,
    REGISTRY_FRAME_HEADER_BYTES,
    REGISTRY_HEADER_BYTES,
    REGISTRY_RESOURCE_HEADER_BYTES,
    XN_REGISTRY_MAGIC,
    XN_REGISTRY_VERSION,
    SourceFrame,
    has_duplicate_used_rgba_indices,
    inspect_registry,
    load_source_frames,
    map_output,
    run_xbr,
    xbr_provenance_indices,
)
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
JOB_SCHEMA = "bg2-upscale-reboutcx-prototype-job-v1"
RUN_SCHEMA = "bg2-upscale-reboutcx-prototype-run-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha256_pixels(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest().upper()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def is_null_frame(frame: SourceFrame, marker_index: int) -> bool:
    return (
        frame.width == 1
        and frame.height == 1
        and frame.center_x == 0
        and frame.center_y == 0
        and frame.indices.shape == (1, 1)
        and int(frame.indices[0, 0]) == int(marker_index)
    )


def prepare_inference_rgb(
    frame: SourceFrame, palette_rgb: np.ndarray | None = None
) -> np.ndarray | None:
    palette = frame.palette if palette_rgb is None else np.asarray(palette_rgb, dtype=np.uint8)
    if palette.shape != (256, 3):
        raise RuntimeError("inference palette must contain 256 RGB entries")
    rgb = np.asarray(palette[frame.indices], dtype=np.uint8)
    opaque = frame.indices != frame.transparent
    if not np.any(opaque):
        return None
    if np.all(opaque):
        return rgb.copy()
    nearest = distance_transform_edt(
        ~opaque, return_distances=False, return_indices=True
    )
    filled = rgb[tuple(nearest)]
    if not np.array_equal(filled[opaque], rgb[opaque]):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: opaque RGB changed during fill")
    return np.asarray(filled, dtype=np.uint8)


def load_palette_profiles(job: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Load a pinned native Character palette resource; absent means legacy BAM RGB."""
    specification = job.get("palette_reference")
    if specification is None:
        return [], None
    if (
        specification.get("id") != CHARACTER_CHMB1_PALETTE_ID
        or job.get("semantic_classes_id") != CHARACTER_CHMB1_CLASSES_ID
    ):
        raise RuntimeError("Character palette reference/profile mismatch")
    source = specification.get("source")
    if not isinstance(source, dict) or str(source.get("resource", "")).upper() != "RANGES12":
        raise RuntimeError("Character palette reference requires RANGES12")
    bifs, resources = load_key()
    matches = [
        entry
        for entry in resources
        if entry[0].upper() == "RANGES12" and int(entry[1]) == int(source.get("type", 1))
    ]
    if len(matches) != 1:
        raise RuntimeError("RANGES12 resource identity is ambiguous")
    entry = matches[0]
    raw, bif_name = resolve_resource(bifs, entry[2])
    if (
        f"0x{entry[2]:08X}".upper() != str(source.get("locator", "")).upper()
        or bif_name.replace("\\", "/").lower() != str(source.get("bif", "")).lower()
        or hashlib.sha256(raw).hexdigest().upper() != str(source.get("sha256", "")).upper()
    ):
        raise RuntimeError("RANGES12 resource provenance differs")
    image = Image.open(io.BytesIO(raw)).convert("RGB")
    if image.size != (12, 256):
        raise RuntimeError("RANGES12 dimensions differ")
    gradients = np.asarray(image, dtype=np.uint8)
    profiles = []
    seen: set[str] = set()
    for record in specification.get("profiles", []):
        name = str(record.get("name", ""))
        rows = tuple(int(value) for value in record.get("colors", []))
        if not name or name in seen or len(rows) != 7 or any(not 0 <= value < 256 for value in rows):
            raise RuntimeError("invalid Character palette profile")
        seen.add(name)
        palette = character_chmb1_palette_rgb(gradients[list(rows)])
        digest = sha256_pixels(palette)
        if digest != str(record.get("palette_rgb_sha256", "")).upper():
            raise RuntimeError(f"Character palette profile differs: {name}")
        profiles.append({"name": name, "colors": list(rows), "palette": palette, "sha256": digest})
    if not profiles or profiles[0]["name"] != "reference":
        raise RuntimeError("first Character palette profile must be reference")
    evidence = {
        "id": specification["id"],
        "source": {
            "resource": "RANGES12",
            "type": int(entry[1]),
            "locator": f"0x{entry[2]:08X}",
            "bif": bif_name.replace("\\", "/"),
            "sha256": hashlib.sha256(raw).hexdigest().upper(),
            "dimensions": [image.width, image.height],
        },
        "profiles": [
            {"name": item["name"], "colors": item["colors"], "palette_rgb_sha256": item["sha256"]}
            for item in profiles
        ],
    }
    return profiles, evidence


def load_model(model_path: Path, *, device: str, fp16: bool) -> tuple[Any, dict[str, str]]:
    try:
        import spandrel
        import torch
        from spandrel import ModelLoader
    except ImportError as error:
        raise RuntimeError("run this command with the configured chaiNNer Python") from error
    if device != "cuda:0" or not torch.cuda.is_available():
        raise RuntimeError("P1 is pinned to CUDA device 0")
    torch.cuda.set_device(0)
    torch.backends.cudnn.benchmark = False
    descriptor = ModelLoader().load_from_file(str(model_path))
    if (
        int(descriptor.scale) != 4
        or int(descriptor.input_channels) != 3
        or int(descriptor.output_channels) != 3
    ):
        raise RuntimeError("ReboutCX descriptor is not RGB-to-RGB x4")
    descriptor = descriptor.cuda().eval()
    if fp16:
        if not descriptor.supports_half:
            raise RuntimeError("ReboutCX descriptor does not support FP16")
        descriptor = descriptor.half()
    return descriptor, {
        "python": sys.version.split()[0],
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "torch": str(torch.__version__),
        "spandrel": str(spandrel.__version__),
    }


def infer_x4_box_x2(
    descriptor: Any, rgb_u8: np.ndarray, *, fp16: bool
) -> tuple[np.ndarray, np.ndarray]:
    import torch
    from chainner_ext import ResizeFilter, resize

    source = np.asarray(rgb_u8, dtype=np.float32) / 255.0
    tensor = torch.from_numpy(source.transpose(2, 0, 1)).unsqueeze(0).cuda()
    tensor = tensor.half() if fp16 else tensor.float()
    with torch.inference_mode():
        output = descriptor(tensor).float().clamp(0, 1).cpu().numpy()[0]
    x4_float = np.ascontiguousarray(output.transpose(1, 2, 0), dtype=np.float32)
    height, width = source.shape[:2]
    if x4_float.shape != (height * 4, width * 4, 3):
        raise RuntimeError("ReboutCX output dimensions are not exact x4")
    x2_float = resize(
        x4_float,
        (width * 2, height * 2),
        ResizeFilter.Box,
        False,
    )
    x4 = np.rint(x4_float * 255.0).astype(np.uint8)
    x2 = np.rint(np.clip(x2_float, 0, 1) * 255.0).astype(np.uint8)
    return x4, x2


def selected_frames(
    job: dict[str, Any], frames: list[SourceFrame]
) -> tuple[list[SourceFrame], dict[str, list[tuple[str, int]]]]:
    lookup = {(frame.resref, frame.index): frame for frame in frames}
    group_keys: dict[str, list[tuple[str, int]]] = {}
    selected: dict[tuple[str, int], SourceFrame] = {}
    for group in job["sample"]["groups"]:
        name = str(group["name"])
        if name in group_keys:
            raise RuntimeError(f"duplicate sample group: {name}")
        resref = str(group["resref"]).upper()
        keys = [(resref, int(index)) for index in group["frames"]]
        if not keys or len(keys) != len(set(keys)):
            raise RuntimeError(f"invalid frame list for sample group {name}")
        for key in keys:
            if key not in lookup:
                raise RuntimeError(f"unknown sample frame: {key[0]} {key[1]}")
            selected[key] = lookup[key]
        group_keys[name] = keys
    resource_order = {
        str(item["name"]).upper(): index
        for index, item in enumerate(job["source_inventory"])
    }
    ordered = sorted(
        selected.values(), key=lambda frame: (resource_order[frame.resref], frame.index)
    )
    return ordered, group_keys


def save_image(path: Path, pixels: np.ndarray, mode: str) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(np.asarray(pixels, dtype=np.uint8), mode).save(path, optimize=True)
    return {
        "path": relative(path),
        "sha256": sha256_file(path),
        "pixel_sha256": sha256_pixels(pixels),
    }


def checkerboard(width: int, height: int, cell: int = 8) -> Image.Image:
    y, x = np.indices((height, width))
    values = np.where(((x // cell + y // cell) & 1) == 0, 88, 120).astype(np.uint8)
    rgb = np.repeat(values[:, :, None], 3, axis=2)
    return Image.fromarray(rgb, "RGB").convert("RGBA")


def make_group_comparison(
    name: str,
    keys: list[tuple[str, int]],
    results: dict[tuple[str, int], dict[str, Any]],
    destination: Path,
    *,
    duration_ms: int,
) -> dict[str, Any]:
    records = [results[key] for key in keys]
    scale = 2
    left = min(-record["frame"].center_x * scale for record in records)
    top = min(-record["frame"].center_y * scale for record in records)
    right = max(
        -record["frame"].center_x * scale + record["frame"].width * scale
        for record in records
    )
    bottom = max(
        -record["frame"].center_y * scale + record["frame"].height * scale
        for record in records
    )
    panel_width, panel_height = right - left, bottom - top
    margin, label_height = 12, 28
    labels = ("NATIF x2", "xBR2X", "ReboutCX brut", "ReboutCX indexe")
    animation: list[Image.Image] = []
    for record in records:
        frame: SourceFrame = record["frame"]
        panels = (
            record["native_rgba"],
            record["xbr_rgba"],
            record["raw_masked_rgba"],
            record["quantized_rgba"],
        )
        canvas = Image.new(
            "RGBA",
            ((panel_width + margin) * 4 + margin, panel_height + label_height + margin),
            (24, 26, 30, 255),
        )
        draw = ImageDraw.Draw(canvas)
        x = -frame.center_x * scale - left
        y = -frame.center_y * scale - top
        for column, (label, pixels) in enumerate(zip(labels, panels, strict=True)):
            origin_x = margin + column * (panel_width + margin)
            draw.text((origin_x + 3, 7), label, fill="white")
            background = checkerboard(panel_width, panel_height)
            background.alpha_composite(Image.fromarray(pixels, "RGBA"), (x, y))
            canvas.alpha_composite(background, (origin_x, label_height))
        draw.text((margin, panel_height + label_height), f"{frame.resref} frame {frame.index}", fill="white")
        animation.append(canvas.convert("RGB"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    animation[0].save(
        destination,
        save_all=True,
        append_images=animation[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )
    return {
        "name": name,
        "path": relative(destination),
        "sha256": sha256_file(destination),
        "frames": len(animation),
        "duration_ms": duration_ms,
    }


def make_palette_comparison(
    name: str,
    keys: list[tuple[str, int]],
    results: dict[tuple[str, int], dict[str, Any]],
    destination: Path,
    *,
    palette_name: str,
    duration_ms: int,
) -> dict[str, Any]:
    records = [results[key] for key in keys]
    scale = 2
    left = min(-record["frame"].center_x * scale for record in records)
    top = min(-record["frame"].center_y * scale for record in records)
    right = max(
        -record["frame"].center_x * scale + record["frame"].width * scale
        for record in records
    )
    bottom = max(
        -record["frame"].center_y * scale + record["frame"].height * scale
        for record in records
    )
    panel_width, panel_height = right - left, bottom - top
    margin, label_height = 12, 28
    animation: list[Image.Image] = []
    for record in records:
        frame: SourceFrame = record["frame"]
        recolored = record["palette_previews"][palette_name]
        canvas = Image.new(
            "RGBA",
            ((panel_width + margin) * 2 + margin, panel_height + label_height + margin),
            (24, 26, 30, 255),
        )
        draw = ImageDraw.Draw(canvas)
        x = -frame.center_x * scale - left
        y = -frame.center_y * scale - top
        for column, (label, pixels) in enumerate(
            (("xBR2X", recolored["xbr_rgba"]), ("ReboutCX indexe", recolored["quantized_rgba"]))
        ):
            origin_x = margin + column * (panel_width + margin)
            draw.text((origin_x + 3, 7), f"{label} / {palette_name}", fill="white")
            background = checkerboard(panel_width, panel_height)
            background.alpha_composite(Image.fromarray(pixels, "RGBA"), (x, y))
            canvas.alpha_composite(background, (origin_x, label_height))
        draw.text((margin, panel_height + label_height), f"{frame.resref} frame {frame.index}", fill="white")
        animation.append(canvas.convert("RGB"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    animation[0].save(
        destination,
        save_all=True,
        append_images=animation[1:],
        duration=duration_ms,
        loop=0,
        disposal=2,
        optimize=False,
    )
    return {
        "name": name,
        "palette": palette_name,
        "path": relative(destination),
        "sha256": sha256_file(destination),
        "frames": len(animation),
        "duration_ms": duration_ms,
    }


def write_prototype_registry(
    path: Path,
    *,
    animation_id: int,
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        stream.write(XN_REGISTRY_MAGIC)
        stream.write(struct.pack("<IIII", XN_REGISTRY_VERSION, 2, len(resources), animation_id))
        for resource in resources:
            frames = resource["frames"]
            resref = str(resource["resref"])
            stream.write(resref.encode("ascii").ljust(8, b"\0"))
            stream.write(bytes.fromhex(str(resource["source_sha256"])))
            stream.write(struct.pack("<II", len(frames), 1))
            for record in frames:
                frame: SourceFrame = record["frame"]
                indices = np.asarray(record["quantized_indices"], dtype=np.uint8)
                representatives = source_representatives(frame.indices)
                if np.any(representatives[indices] == 0xFFFF):
                    raise RuntimeError(f"{resref} frame {frame.index}: missing representative")
                stream.write(
                    struct.pack(
                        "<HHhhB3xI",
                        frame.width,
                        frame.height,
                        frame.center_x,
                        frame.center_y,
                        frame.transparent,
                        indices.size,
                    )
                )
                stream.write(representatives.astype("<u2", copy=False).tobytes())
                stream.write(indices.reshape(-1).tobytes())
            stream.write(struct.pack("<I", len(frames)))
            stream.write(struct.pack(f"<{len(frames)}I", *range(len(frames))))
    return inspect_registry(path, include_resource_records=True)


def verify_prototype_registry(path: Path, resources: list[dict[str, Any]]) -> None:
    with path.open("rb") as stream:
        header = stream.read(REGISTRY_HEADER_BYTES)
        if header[:8] != XN_REGISTRY_MAGIC:
            raise RuntimeError("prototype registry magic differs")
        version, scale, resource_count, _animation_id = struct.unpack_from("<IIII", header, 8)
        if (version, scale, resource_count) != (XN_REGISTRY_VERSION, 2, len(resources)):
            raise RuntimeError("prototype registry header differs")
        for resource in resources:
            resource_header = stream.read(REGISTRY_RESOURCE_HEADER_BYTES)
            resref = resource_header[:8].split(b"\0", 1)[0].decode("ascii")
            frame_count, cycle_count = struct.unpack_from("<II", resource_header, 40)
            if resref != resource["resref"] or frame_count != len(resource["frames"]) or cycle_count != 1:
                raise RuntimeError("prototype registry resource metadata differs")
            for record in resource["frames"]:
                frame: SourceFrame = record["frame"]
                frame_header = stream.read(REGISTRY_FRAME_HEADER_BYTES)
                width, height, center_x, center_y, transparent, stored = struct.unpack_from(
                    "<HHhhB3xI", frame_header, 0
                )
                expected_geometry = (
                    frame.width,
                    frame.height,
                    frame.center_x,
                    frame.center_y,
                    frame.transparent,
                    int(record["quantized_indices"].size),
                )
                if (width, height, center_x, center_y, transparent, stored) != expected_geometry:
                    raise RuntimeError("prototype registry frame geometry differs")
                expected_representatives = source_representatives(frame.indices)
                actual_representatives = np.frombuffer(frame_header, dtype="<u2", count=256, offset=16)
                if not np.array_equal(actual_representatives, expected_representatives):
                    raise RuntimeError("prototype registry representatives differ")
                payload = np.frombuffer(stream.read(stored), dtype=np.uint8)
                if not np.array_equal(payload, record["quantized_indices"].reshape(-1)):
                    raise RuntimeError("prototype registry indices differ")
            slots = struct.unpack("<I", stream.read(4))[0]
            lookup = struct.unpack(f"<{slots}I", stream.read(slots * 4))
            if lookup != tuple(range(len(resource["frames"]))):
                raise RuntimeError("prototype registry local cycle differs")
        if stream.read(1):
            raise RuntimeError("prototype registry has trailing bytes")


def execute(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if job.get("schema") != JOB_SCHEMA or job.get("installable") is not False:
        raise RuntimeError("invalid or installable ReboutCX prototype job")
    if int(job["reboutcx"]["target_scale"]) != 2:
        raise RuntimeError("ReboutCX target_scale must be 2")
    output = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)
    if output.exists():
        raise RuntimeError(f"prototype run already exists: {output}")
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise RuntimeError(f"prototype temporary path already exists: {temporary}")
    temporary.mkdir(parents=True)

    source_manifest_path = resolve_path_reference(
        job["paths"]["source_manifest"], required=True, root=PROJECT_ROOT
    )
    if sha256_file(source_manifest_path) != str(job["source_manifest_sha256"]):
        raise RuntimeError("source manifest hash differs")
    model_path = resolve_path_reference(
        job["paths"]["reboutcx_model"], required=True, root=PROJECT_ROOT
    )
    if sha256_file(model_path) != str(job["reboutcx"]["model_sha256"]):
        raise RuntimeError("ReboutCX model hash differs")
    scalepix = resolve_path_reference(
        job["paths"]["scalepix"], required=True, root=PROJECT_ROOT
    )
    frames, resources, source_manifest = load_source_frames(source_manifest_path)
    if int(source_manifest["animation_id"], 16) != int(job["animation_id"], 16):
        raise RuntimeError("source animation id differs")
    selected, groups = selected_frames(job, frames)
    classes, classes_id = semantic_classes_for_job(job)
    palette_profiles, palette_evidence = load_palette_profiles(job)
    reference_palette = palette_profiles[0]["palette"] if palette_profiles else None
    marker_index = int(job["null_frame_marker"])

    xbr_started = time.perf_counter()
    xbr_outputs = run_xbr(selected, scalepix, str(job["tools"].get("node", "node")), LEGACY_UPSCALE)
    xbr_seconds = time.perf_counter() - xbr_started
    descriptor, versions = load_model(
        model_path,
        device=str(job["reboutcx"]["device"]),
        fp16=bool(job["reboutcx"]["fp16"]),
    )

    results: dict[tuple[str, int], dict[str, Any]] = {}
    frame_manifest: list[dict[str, Any]] = []
    inference_seconds = 0.0
    quantization_seconds = 0.0
    for frame, xbr_output in zip(selected, xbr_outputs, strict=True):
        scaled_width, scaled_height, xbr_bytes = xbr_output
        if (scaled_width, scaled_height) != (frame.width * 2, frame.height * 2):
            raise RuntimeError(f"{frame.resref} frame {frame.index}: xBR geometry differs")
        provenance = xbr_provenance_indices(frame, 2) if has_duplicate_used_rgba_indices(frame) else None
        guide_flat, _representatives = map_output(frame, xbr_bytes, provenance)
        guide = guide_flat.reshape(scaled_height, scaled_width)
        source_xbr_rgba = np.frombuffer(xbr_bytes, dtype=np.uint8).reshape(
            scaled_height, scaled_width, 4
        ).copy()
        if reference_palette is None:
            xbr_rgba = source_xbr_rgba
            native_rgba = np.asarray(
                Image.frombytes("RGBA", (frame.width, frame.height), frame.rgba).resize(
                    (scaled_width, scaled_height), Image.Resampling.NEAREST
                ),
                dtype=np.uint8,
            )
            quantization_palette = frame.palette
        else:
            xbr_rgba = reconstruct_rgba(guide, reference_palette, frame.transparent)
            native_indices = np.repeat(np.repeat(frame.indices, 2, axis=0), 2, axis=1)
            native_rgba = reconstruct_rgba(native_indices, reference_palette, frame.transparent)
            quantization_palette = reference_palette

        if is_null_frame(frame, marker_index):
            x4 = np.full((4, 4, 3), quantization_palette[marker_index], dtype=np.uint8)
            target_rgb = np.full((2, 2, 3), quantization_palette[marker_index], dtype=np.uint8)
            quantized = np.full((2, 2), marker_index, dtype=np.uint8)
            metrics = {
                "quantizer": QUANTIZER_ID,
                "pixels": 4,
                "visible_pixels": 4,
                "class_pixels": {"null_frame_marker": 4},
                "output_indices": [marker_index],
                "oklab_error_mean": 0.0,
                "oklab_error_p95": 0.0,
                "oklab_error_max": 0.0,
                "model_bypassed": True,
            }
        else:
            inference_rgb = prepare_inference_rgb(frame, quantization_palette)
            if inference_rgb is None:
                x4 = np.repeat(np.repeat(quantization_palette[frame.transparent][None, None, :], frame.height * 4, axis=0), frame.width * 4, axis=1)
                target_rgb = np.repeat(np.repeat(quantization_palette[frame.transparent][None, None, :], frame.height * 2, axis=0), frame.width * 2, axis=1)
            else:
                started = time.perf_counter()
                x4, target_rgb = infer_x4_box_x2(
                    descriptor, inference_rgb, fp16=bool(job["reboutcx"]["fp16"])
                )
                inference_seconds += time.perf_counter() - started
            used = np.unique(frame.indices)
            started = time.perf_counter()
            quantized, metrics = quantize_classed_oklab(
                target_rgb,
                guide,
                quantization_palette,
                used,
                classes,
                transparent_index=frame.transparent,
            )
            repeated, _repeat_metrics = quantize_classed_oklab(
                target_rgb,
                guide,
                quantization_palette,
                used,
                classes,
                transparent_index=frame.transparent,
            )
            quantization_seconds += time.perf_counter() - started
            if not np.array_equal(quantized, repeated):
                raise RuntimeError(f"{frame.resref} frame {frame.index}: quantizer is not deterministic")

        quantized_rgba = reconstruct_rgba(quantized, quantization_palette, frame.transparent)
        raw_masked_rgba = np.dstack(
            (target_rgb, np.where(guide == frame.transparent, 0, 255).astype(np.uint8))
        )
        frame_dir = temporary / "frames" / frame.resref / f"frame-{frame.index:04d}"
        files = {
            "native_x2": save_image(frame_dir / "native-x2.png", native_rgba, "RGBA"),
            "xbr_x2": save_image(frame_dir / "xbr-x2.png", xbr_rgba, "RGBA"),
            "reboutcx_raw_x2": save_image(frame_dir / "reboutcx-raw-x2.png", raw_masked_rgba, "RGBA"),
            "reboutcx_quantized_x2": save_image(frame_dir / "reboutcx-quantized-x2.png", quantized_rgba, "RGBA"),
        }
        if reference_palette is not None:
            files["xbr_source_palette_x2"] = save_image(
                frame_dir / "xbr-source-palette-x2.png", source_xbr_rgba, "RGBA"
            )
        if (frame.resref, frame.index) == (
            str(job["reference"]["resref"]),
            int(job["reference"]["frame"]),
        ):
            if job["reference"].get("x4_pixel_sha256") and sha256_pixels(x4) != str(job["reference"]["x4_pixel_sha256"]):
                raise RuntimeError("P0 witness x4 pixels differ")
            if job["reference"].get("x2_pixel_sha256") and sha256_pixels(target_rgb) != str(job["reference"]["x2_pixel_sha256"]):
                raise RuntimeError("P0 witness BOX x2 pixels differ")
            files["reboutcx_x4"] = save_image(frame_dir / "reboutcx-x4.png", x4, "RGB")
        palette_previews = {
            profile["name"]: {
                "xbr_rgba": reconstruct_rgba(guide, profile["palette"], frame.transparent),
                "quantized_rgba": reconstruct_rgba(
                    quantized, profile["palette"], frame.transparent
                ),
            }
            for profile in palette_profiles
        }
        record = {
            "frame": frame,
            "native_rgba": native_rgba,
            "xbr_rgba": xbr_rgba,
            "raw_masked_rgba": raw_masked_rgba,
            "quantized_rgba": quantized_rgba,
            "quantized_indices": quantized,
            "palette_previews": palette_previews,
        }
        results[(frame.resref, frame.index)] = record
        frame_manifest.append(
            {
                "resref": frame.resref,
                "source_frame": frame.index,
                "width": frame.width,
                "height": frame.height,
                "center_x": frame.center_x,
                "center_y": frame.center_y,
                "transparent_index": frame.transparent,
                "guide_indices": [int(value) for value in np.unique(guide)],
                "guide_index_sha256": sha256_pixels(guide),
                "xbr_source_rgba_pixel_sha256": sha256_pixels(source_xbr_rgba),
                "quantized_index_sha256": sha256_pixels(quantized),
                "metrics": metrics,
                "files": files,
            }
        )

    qa = []
    group_by_name = {str(group["name"]): group for group in job["sample"]["groups"]}
    for name, keys in groups.items():
        group = group_by_name[name]
        qa.append(
            make_group_comparison(
                name,
                keys,
                results,
                temporary / "qa" / f"{name}.gif",
                duration_ms=int(group["duration_ms"]),
            )
        )
        for profile_index, profile in enumerate(palette_profiles):
            qa.append(
                make_palette_comparison(
                    name,
                    keys,
                    results,
                    temporary / "qa" / f"{name}-palette-{profile_index:02d}.gif",
                    palette_name=profile["name"],
                    duration_ms=int(group["duration_ms"]),
                )
            )

    source_by_resref = {str(item["source"]["name"]).upper(): item for item in resources}
    registry_resources = []
    for resref in dict.fromkeys(frame.resref for frame in selected):
        resource = source_by_resref[resref]
        records = [results[(frame.resref, frame.index)] for frame in selected if frame.resref == resref]
        registry_resources.append(
            {
                "resref": resref,
                "source_sha256": sha256_file(resource["source_path"]),
                "frames": records,
            }
        )
    registry_path = temporary / "prototype" / "CreatureSprites-XN.registry"
    registry_info = write_prototype_registry(
        registry_path,
        animation_id=int(job["animation_id"], 16),
        resources=registry_resources,
    )
    verify_prototype_registry(registry_path, registry_resources)
    registry_info.pop("resource_records", None)
    registry_info["path"] = relative(registry_path)
    registry_info["round_trip_exact"] = True
    registry_info["installable"] = False
    registry_info["cycle_contract"] = "one local synthetic cycle per sampled resref"

    manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed-pending-human-review",
        "installable": False,
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "source_manifest": relative(source_manifest_path),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "animation_id": job["animation_id"],
        "model_sha256": sha256_file(model_path),
        "target_scale": 2,
        "versions": versions,
        "semantic_classes_id": classes_id,
        "semantic_classes": classes,
        "palette_reference": palette_evidence,
        "code": {
            "reboutcx_batch": {
                "path": relative(Path(__file__)),
                "sha256": sha256_file(Path(__file__)),
            },
            "reboutcx_quantize": {
                "path": relative(SCRIPT_DIR / "reboutcx_quantize.py"),
                "sha256": sha256_file(SCRIPT_DIR / "reboutcx_quantize.py"),
            },
            "creature_sprite_x2": {
                "path": relative(SCRIPT_DIR / "run_creature_sprite_x2.py"),
                "sha256": sha256_file(SCRIPT_DIR / "run_creature_sprite_x2.py"),
            },
            "bam_export": {
                "path": relative(SCRIPT_DIR / "bam_export.py"),
                "sha256": sha256_file(SCRIPT_DIR / "bam_export.py"),
            },
            "xbr_adapter": {
                "path": relative(SCRIPT_DIR / "xbr2x_batch.js"),
                "sha256": sha256_file(SCRIPT_DIR / "xbr2x_batch.js"),
            },
            "scalepix": {
                "path": str(job["paths"]["scalepix"]),
                "sha256": sha256_file(scalepix),
            },
            "chainner_python": {
                "path": str(job["paths"]["chainner_python"]),
                "sha256": sha256_file(Path(sys.executable)),
            },
        },
        "method": {
            "provider": "chaiNNer-integrated-python",
            "model_scale": 4,
            "device": job["reboutcx"]["device"],
            "fp16": job["reboutcx"]["fp16"],
            "tiling": "none",
            "padding": "none",
            "downscale": "chainner_ext ResizeFilter.Box float32 before u8 rounding",
            "rgb_under_transparency": "scipy distance_transform_edt nearest opaque",
            "alpha": "xbr2x-mask-v1",
            "quantizer": QUANTIZER_ID,
            "palette_rgb": (
                CHARACTER_CHMB1_PALETTE_ID if reference_palette is not None else "source-bam"
            ),
            "dither": False,
        },
        "sample_groups": job["sample"]["groups"],
        "resource_count": len(registry_resources),
        "frame_count": len(selected),
        "timing_seconds": {
            "xbr": xbr_seconds,
            "reboutcx": inference_seconds,
            "quantization_with_repeat_check": quantization_seconds,
        },
        "frames": frame_manifest,
        "qa": qa,
        "registry": registry_info,
    }
    temporary_prefix = relative(temporary)
    output_prefix = relative(output)
    manifest = json.loads(
        json.dumps(manifest).replace(temporary_prefix, output_prefix)
    )
    manifest_path = temporary / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    temporary.rename(output)
    final_manifest = output / "manifest.json"
    print(json.dumps({"status": manifest["status"], "run": relative(output), "manifest_sha256": sha256_file(final_manifest), "frames": len(selected)}, indent=2))
    return manifest


def verify(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    output = resolve_path_reference(job["paths"]["run_dir"], required=True, root=PROJECT_ROOT)
    manifest_path = output / "manifest.json"
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != RUN_SCHEMA
        or manifest.get("status") != "completed-pending-human-review"
        or manifest.get("installable") is not False
        or int(manifest.get("target_scale", 0)) != 2
    ):
        raise RuntimeError("invalid ReboutCX prototype manifest")
    if manifest.get("job_sha256") != sha256_file(job_path):
        raise RuntimeError("prototype job hash differs")
    for evidence in manifest["code"].values():
        reference = str(evidence["path"])
        path = resolve_path_reference(reference, required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError(f"prototype code/input hash differs: {reference}")
    checked_files = 0
    for frame in manifest["frames"]:
        for evidence in frame["files"].values():
            path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
            if sha256_file(path) != str(evidence["sha256"]):
                raise RuntimeError(f"prototype frame file hash differs: {path}")
            checked_files += 1
    for evidence in manifest["qa"]:
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError(f"prototype QA hash differs: {path}")
        checked_files += 1
    registry_path = resolve_path_reference(
        manifest["registry"]["path"], required=True, root=PROJECT_ROOT
    )
    registry = inspect_registry(registry_path)
    for key in (
        "version",
        "scale",
        "registry_magic",
        "animation_id",
        "resource_count",
        "frame_count",
        "index_bytes",
        "registry_bytes",
        "sha256",
        "crc32",
    ):
        if registry[key] != manifest["registry"][key]:
            raise RuntimeError(f"prototype registry verification differs: {key}")
    result = {
        "status": "verified",
        "run": relative(output),
        "manifest_sha256": sha256_file(manifest_path),
        "frame_count": manifest["frame_count"],
        "checked_files": checked_files + 2,
        "registry_sha256": registry["sha256"],
    }
    print(json.dumps(result, indent=2))
    return result


def run_via_configured_python(job_path: Path) -> int:
    job = read_json(job_path)
    python_path = resolve_path_reference(
        job["paths"]["chainner_python"], required=True, root=PROJECT_ROOT
    ).resolve()
    expected_python_hash = str(job["tools"].get("chainner_python_sha256", ""))
    if expected_python_hash and sha256_file(python_path) != expected_python_hash:
        raise RuntimeError("configured chaiNNer Python hash differs")
    if Path(sys.executable).resolve() != python_path:
        result = subprocess.run(
            [str(python_path), str(Path(__file__).resolve()), "_execute", str(job_path.resolve())],
            check=False,
        )
        return int(result.returncode)
    execute(job_path)
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("run", "_execute", "verify"):
        child = subparsers.add_parser(command)
        child.add_argument("job", type=Path)
    arguments = parser.parse_args(argv)
    job_path = arguments.job.resolve()
    if arguments.command == "run":
        return run_via_configured_python(job_path)
    if arguments.command == "verify":
        verify(job_path)
        return 0
    execute(job_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
