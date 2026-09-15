"""Full offline ReboutCX x4-to-x2 runner for one indexed sprite animation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path
from typing import Any, BinaryIO, Iterable

import numpy as np
from PIL import Image, ImageDraw

from reboutcx_batch import (
    infer_x4_box_x2,
    is_null_frame,
    load_palette_profiles,
    load_model,
    prepare_inference_rgb,
)
from reboutcx_quantize import (
    QUANTIZER_ID,
    quantize_classed_oklab,
    reconstruct_rgba,
    semantic_classes_for_job,
    source_representatives,
)
from run_creature_sprite_x2 import (
    LEGACY_UPSCALE,
    REGISTRY_FRAME_HEADER_BYTES,
    REGISTRY_HEADER_BYTES,
    REGISTRY_RESOURCE_HEADER_BYTES,
    XBR_OUTPUT_BATCH_BUDGET_BYTES,
    XN_REGISTRY_MAGIC,
    XN_REGISTRY_VERSION,
    SourceFrame,
    has_duplicate_used_rgba_indices,
    inspect_registry,
    load_source_frames,
    map_output,
    run_xbr,
    xbr_output_batch_ranges,
    xbr_provenance_indices,
)
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
JOB_SCHEMA = "bg2-upscale-reboutcx-full-job-v1"
RUN_SCHEMA = "bg2-upscale-reboutcx-full-run-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest().upper()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def render_contract_digest(
    job: dict[str, Any],
    classes: dict[str, list[int]],
    palette_evidence: dict[str, Any] | None,
) -> str:
    """Pin every job-level input that can change rendered indices."""
    contract = {
        "runtime_profile": job.get("runtime_profile"),
        "layer": job.get("layer"),
        "armor_code": job.get("armor_code"),
        "item_resref": job.get("item_resref"),
        "semantic_classes_id": job.get("semantic_classes_id"),
        "semantic_classes": classes,
        "palette_reference": palette_evidence,
        "null_frame_marker": int(job["null_frame_marker"]),
        "reboutcx": job["reboutcx"],
        "quantizer": QUANTIZER_ID,
        "alpha": "xbr2x-mask-v1",
        "rgb_under_transparency": "scipy distance_transform_edt nearest opaque",
    }
    payload = json.dumps(contract, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()


def read_exact(stream: BinaryIO, size: int, label: str) -> bytes:
    data = stream.read(size)
    if len(data) != size:
        raise RuntimeError(f"truncated {label}")
    return data


def ordered_cycles(resource: dict[str, Any]) -> list[dict[str, Any]]:
    cycles = sorted(resource["cycles"], key=lambda item: int(item["index"]))
    if [int(item["index"]) for item in cycles] != list(range(len(cycles))):
        raise RuntimeError(f"{resource['source']['name']}: non-contiguous cycles")
    frame_count = len(resource["frames"])
    for cycle in cycles:
        slots = [int(value) for value in cycle["frame_indices"]]
        if any(value < 0 or value >= frame_count for value in slots):
            raise RuntimeError(f"{resource['source']['name']}: invalid cycle lookup")
    return cycles


def write_component_header(
    stream: BinaryIO,
    *,
    animation_id: int,
    resref: str,
    source_sha256: str,
    frame_count: int,
    cycle_count: int,
) -> None:
    stream.write(XN_REGISTRY_MAGIC)
    stream.write(struct.pack("<IIII", XN_REGISTRY_VERSION, 2, 1, animation_id))
    stream.write(resref.encode("ascii").ljust(8, b"\0"))
    stream.write(bytes.fromhex(source_sha256))
    stream.write(struct.pack("<II", frame_count, cycle_count))


def write_frame_record(stream: BinaryIO, frame: SourceFrame, indices: np.ndarray) -> None:
    payload = np.ascontiguousarray(indices, dtype=np.uint8)
    if payload.shape != (frame.height * 2, frame.width * 2):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: invalid x2 payload shape")
    representatives = source_representatives(frame.indices)
    if np.any(representatives[payload] == 0xFFFF):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: missing representative")
    stream.write(
        struct.pack(
            "<HHhhB3xI",
            frame.width,
            frame.height,
            frame.center_x,
            frame.center_y,
            frame.transparent,
            payload.size,
        )
    )
    stream.write(representatives.astype("<u2", copy=False).tobytes())
    stream.write(payload.tobytes())


def write_cycles(stream: BinaryIO, cycles: list[dict[str, Any]]) -> None:
    for cycle in cycles:
        slots = [int(value) for value in cycle["frame_indices"]]
        stream.write(struct.pack("<I", len(slots)))
        if slots:
            stream.write(struct.pack(f"<{len(slots)}I", *slots))


def validate_component_registry(
    path: Path,
    *,
    animation_id: int,
    resource: dict[str, Any],
    frame_manifest: list[dict[str, Any]],
) -> dict[str, Any]:
    frames: list[SourceFrame] = resource["frames"]
    cycles = ordered_cycles(resource)
    resref = str(resource["source"]["name"]).upper()
    if len(frame_manifest) != len(frames):
        raise RuntimeError(f"{resref}: frame manifest count differs")
    with path.open("rb") as stream:
        header = read_exact(stream, REGISTRY_HEADER_BYTES, "registry header")
        if header[:8] != XN_REGISTRY_MAGIC:
            raise RuntimeError(f"{resref}: registry magic differs")
        version, scale, resources, stored_animation = struct.unpack_from("<IIII", header, 8)
        if (version, scale, resources, stored_animation) != (
            XN_REGISTRY_VERSION,
            2,
            1,
            animation_id,
        ):
            raise RuntimeError(f"{resref}: registry identity differs")
        resource_header = read_exact(stream, REGISTRY_RESOURCE_HEADER_BYTES, "resource header")
        stored_resref = resource_header[:8].split(b"\0", 1)[0].decode("ascii")
        source_sha256 = sha256_file(resource["source_path"])
        frame_count, cycle_count = struct.unpack_from("<II", resource_header, 40)
        if (
            stored_resref != resref
            or resource_header[8:40] != bytes.fromhex(source_sha256)
            or frame_count != len(frames)
            or cycle_count != len(cycles)
        ):
            raise RuntimeError(f"{resref}: resource metadata differs")
        for frame, evidence in zip(frames, frame_manifest, strict=True):
            frame_header = read_exact(stream, REGISTRY_FRAME_HEADER_BYTES, "frame header")
            width, height, center_x, center_y, transparent, stored = struct.unpack_from(
                "<HHhhB3xI", frame_header, 0
            )
            expected = (
                frame.width,
                frame.height,
                frame.center_x,
                frame.center_y,
                frame.transparent,
                frame.width * frame.height * 4,
            )
            if (width, height, center_x, center_y, transparent, stored) != expected:
                raise RuntimeError(f"{resref} frame {frame.index}: geometry differs")
            representatives = np.frombuffer(frame_header, dtype="<u2", count=256, offset=16)
            if not np.array_equal(representatives, source_representatives(frame.indices)):
                raise RuntimeError(f"{resref} frame {frame.index}: representatives differ")
            payload = read_exact(stream, stored, "frame payload")
            if hashlib.sha256(payload).hexdigest().upper() != evidence["indices_sha256"]:
                raise RuntimeError(f"{resref} frame {frame.index}: index payload differs")
            values = np.frombuffer(payload, dtype=np.uint8)
            if np.any(representatives[values] == 0xFFFF):
                raise RuntimeError(f"{resref} frame {frame.index}: invalid palette index")
        for expected_cycle in cycles:
            slots = struct.unpack("<I", read_exact(stream, 4, "cycle header"))[0]
            payload = read_exact(stream, slots * 4, "cycle lookup")
            actual = np.frombuffer(payload, dtype="<u4").tolist()
            if actual != [int(value) for value in expected_cycle["frame_indices"]]:
                raise RuntimeError(f"{resref} cycle {expected_cycle['index']}: lookup differs")
        if stream.read(1):
            raise RuntimeError(f"{resref}: trailing registry bytes")
    info = inspect_registry(path)
    if info["resource_count"] != 1 or info["frame_count"] != len(frames):
        raise RuntimeError(f"{resref}: registry inspection differs")
    return info


def copy_component_for_resref(source: Path, destination: Path, resref: str) -> None:
    shutil.copyfile(source, destination)
    with destination.open("r+b") as stream:
        stream.seek(REGISTRY_HEADER_BYTES)
        stream.write(resref.encode("ascii").ljust(8, b"\0"))


def xbr_batches(
    frames: list[SourceFrame], scalepix: Path, node: str
) -> Iterable[tuple[SourceFrame, tuple[int, int, bytes]]]:
    for start, end, _bytes in xbr_output_batch_ranges(
        frames, 2, XBR_OUTPUT_BATCH_BUDGET_BYTES
    ):
        batch_frames = frames[start:end]
        outputs = run_xbr(batch_frames, scalepix, node, LEGACY_UPSCALE)
        for frame, output in zip(batch_frames, outputs, strict=True):
            yield frame, output


def multibackground(width: int, height: int) -> Image.Image:
    canvas = Image.new("RGBA", (width, height), (28, 30, 34, 255))
    draw = ImageDraw.Draw(canvas)
    middle = width // 2
    draw.rectangle((middle, 0, width, height // 2), fill=(218, 211, 192, 255))
    draw.rectangle((0, height // 2, middle, height), fill=(72, 91, 65, 255))
    cell = 8
    for y in range(height // 2, height, cell):
        for x in range(middle, width, cell):
            value = 88 if ((x // cell + y // cell) & 1) == 0 else 124
            draw.rectangle((x, y, min(x + cell - 1, width), min(y + cell - 1, height)), fill=(value, value, value, 255))
    return canvas


def make_group_comparison(
    group: dict[str, Any],
    results: dict[tuple[str, int], dict[str, Any]],
    destination: Path,
) -> dict[str, Any]:
    resref = str(group["resref"]).upper()
    keys = [(resref, int(index)) for index in group["frames"]]
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
    margin, label_height, footer = 12, 28, 18
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
            ((panel_width + margin) * 4 + margin, panel_height + label_height + footer),
            (24, 26, 30, 255),
        )
        draw = ImageDraw.Draw(canvas)
        x = -frame.center_x * scale - left
        y = -frame.center_y * scale - top
        for column, (label, pixels) in enumerate(zip(labels, panels, strict=True)):
            origin_x = margin + column * (panel_width + margin)
            draw.text((origin_x + 3, 7), label, fill="white")
            background = multibackground(panel_width, panel_height)
            background.alpha_composite(Image.fromarray(pixels, "RGBA"), (x, y))
            canvas.alpha_composite(background, (origin_x, label_height))
        draw.text(
            (margin, panel_height + label_height + 2),
            f"{frame.resref} frame {frame.index} | fonds: sombre, clair, vert, damier",
            fill="white",
        )
        animation.append(canvas.convert("RGB"))
    destination.parent.mkdir(parents=True, exist_ok=True)
    animation[0].save(
        destination,
        save_all=True,
        append_images=animation[1:],
        duration=int(group["duration_ms"]),
        loop=0,
        disposal=2,
        optimize=False,
    )
    return {
        "name": str(group["name"]),
        "resref": resref,
        "path": relative(destination),
        "sha256": sha256_file(destination),
        "frames": len(animation),
        "duration_ms": int(group["duration_ms"]),
        "backgrounds": ["dark", "light", "green", "checkerboard"],
    }


def qa_contract(
    job: dict[str, Any],
    resources: list[dict[str, Any]],
    canonical_by_resref: dict[str, str],
) -> tuple[list[dict[str, Any]], dict[str, set[int]]]:
    lookup = {
        (str(resource["source"]["name"]).upper(), frame.index): frame
        for resource in resources
        for frame in resource["frames"]
    }
    names: set[str] = set()
    required: dict[str, set[int]] = defaultdict(set)
    groups = job["qa"]["groups"]
    if not groups:
        raise RuntimeError("QA groups are empty")
    for group in groups:
        name = str(group["name"])
        resref = str(group["resref"]).upper()
        frames = [int(value) for value in group["frames"]]
        if name in names or not frames or len(frames) != len(set(frames)):
            raise RuntimeError(f"invalid QA group: {name}")
        if int(group["duration_ms"]) <= 0:
            raise RuntimeError(f"invalid QA duration: {name}")
        names.add(name)
        for index in frames:
            if (resref, index) not in lookup:
                raise RuntimeError(f"unknown QA frame: {resref} {index}")
            required[canonical_by_resref[resref]].add(index)
    return groups, required


def render_resource(
    *,
    resource: dict[str, Any],
    component_path: Path,
    animation_id: int,
    descriptor: Any,
    fp16: bool,
    scalepix: Path,
    node: str,
    classes: dict[str, list[int]],
    marker_index: int,
    reference_palette: np.ndarray | None,
    qa_indices: set[int],
    reference: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[str, float | int]]:
    frames: list[SourceFrame] = resource["frames"]
    cycles = ordered_cycles(resource)
    resref = str(resource["source"]["name"]).upper()
    non_null = [frame for frame in frames if not is_null_frame(frame, marker_index)]
    xbr_iterator = iter(xbr_batches(non_null, scalepix, node))
    frame_manifest: list[dict[str, Any]] = []
    qa_records: dict[int, dict[str, Any]] = {}
    timing: dict[str, float | int] = {
        "xbr": 0.0,
        "reboutcx": 0.0,
        "quantization": 0.0,
        "model_frames": 0,
        "null_frames": 0,
    }
    component_path.parent.mkdir(parents=True, exist_ok=True)
    with component_path.open("wb") as stream:
        write_component_header(
            stream,
            animation_id=animation_id,
            resref=resref,
            source_sha256=sha256_file(resource["source_path"]),
            frame_count=len(frames),
            cycle_count=len(cycles),
        )
        for frame in frames:
            quantization_palette = (
                frame.palette if reference_palette is None else reference_palette
            )
            if is_null_frame(frame, marker_index):
                guide = np.full((2, 2), marker_index, dtype=np.uint8)
                target_rgb = np.full(
                    (2, 2, 3), quantization_palette[marker_index], dtype=np.uint8
                )
                quantized = guide.copy()
                xbr_rgba = reconstruct_rgba(
                    guide, quantization_palette, frame.transparent
                )
                marker_classes = [
                    name for name, indices in classes.items() if marker_index in indices
                ]
                if len(marker_classes) != 1:
                    raise RuntimeError("null marker must belong to exactly one semantic class")
                visible_pixels = 4 if reference_palette is not None else 0
                metrics = {
                    "visible_pixels": visible_pixels,
                    "class_pixels": {marker_classes[0]: 4},
                    "oklab_error_mean": 0.0,
                    "oklab_error_p95": 0.0,
                    "oklab_error_max": 0.0,
                    "model_bypassed": True,
                }
                timing["null_frames"] = int(timing["null_frames"]) + 1
            else:
                xbr_started = time.perf_counter()
                xbr_frame, xbr_output = next(xbr_iterator)
                timing["xbr"] = float(timing["xbr"]) + time.perf_counter() - xbr_started
                if xbr_frame is not frame:
                    raise RuntimeError(f"{resref}: xBR frame order differs")
                scaled_width, scaled_height, xbr_bytes = xbr_output
                if (scaled_width, scaled_height) != (frame.width * 2, frame.height * 2):
                    raise RuntimeError(f"{resref} frame {frame.index}: xBR geometry differs")
                provenance = (
                    xbr_provenance_indices(frame, 2)
                    if has_duplicate_used_rgba_indices(frame)
                    else None
                )
                guide_flat, _representatives = map_output(frame, xbr_bytes, provenance)
                guide = guide_flat.reshape(scaled_height, scaled_width)
                source_xbr_rgba = np.frombuffer(xbr_bytes, dtype=np.uint8).reshape(
                    scaled_height, scaled_width, 4
                )
                xbr_rgba = (
                    source_xbr_rgba
                    if reference_palette is None
                    else reconstruct_rgba(guide, quantization_palette, frame.transparent)
                )
                inference_rgb = prepare_inference_rgb(frame, quantization_palette)
                if inference_rgb is None:
                    target_rgb = np.full(
                        (scaled_height, scaled_width, 3),
                        quantization_palette[frame.transparent],
                        dtype=np.uint8,
                    )
                    x4 = np.repeat(np.repeat(target_rgb, 2, axis=0), 2, axis=1)
                else:
                    started = time.perf_counter()
                    x4, target_rgb = infer_x4_box_x2(descriptor, inference_rgb, fp16=fp16)
                    timing["reboutcx"] = float(timing["reboutcx"]) + time.perf_counter() - started
                    timing["model_frames"] = int(timing["model_frames"]) + 1
                started = time.perf_counter()
                quantized, metrics = quantize_classed_oklab(
                    target_rgb,
                    guide,
                    quantization_palette,
                    np.unique(frame.indices),
                    classes,
                    transparent_index=frame.transparent,
                )
                timing["quantization"] = float(timing["quantization"]) + time.perf_counter() - started
                if (resref, frame.index) == (
                    str(reference["resref"]).upper(),
                    int(reference["frame"]),
                ):
                    if sha256_array(x4) != str(reference["x4_pixel_sha256"]):
                        raise RuntimeError("P0 witness x4 pixels differ")
                    if sha256_array(target_rgb) != str(reference["x2_pixel_sha256"]):
                        raise RuntimeError("P0 witness BOX x2 pixels differ")
            write_frame_record(stream, frame, quantized)
            frame_manifest.append(
                {
                    "source_frame": frame.index,
                    "width": frame.width,
                    "height": frame.height,
                    "center_x": frame.center_x,
                    "center_y": frame.center_y,
                    "transparent_index": frame.transparent,
                    "indices_sha256": sha256_array(quantized),
                    "guide_sha256": sha256_array(guide),
                    "visible_pixels": int(metrics["visible_pixels"]),
                    "oklab_error_mean": float(metrics["oklab_error_mean"]),
                    "oklab_error_p95": float(metrics["oklab_error_p95"]),
                    "oklab_error_max": float(metrics["oklab_error_max"]),
                    "model_bypassed": bool(metrics.get("model_bypassed", False)),
                }
            )
            if frame.index in qa_indices:
                if reference_palette is None:
                    native_rgba = np.asarray(
                        Image.frombytes("RGBA", (frame.width, frame.height), frame.rgba).resize(
                            (frame.width * 2, frame.height * 2), Image.Resampling.NEAREST
                        ),
                        dtype=np.uint8,
                    )
                else:
                    native_indices = np.repeat(
                        np.repeat(frame.indices, 2, axis=0), 2, axis=1
                    )
                    native_rgba = reconstruct_rgba(
                        native_indices, quantization_palette, frame.transparent
                    )
                qa_records[frame.index] = {
                    "frame": frame,
                    "native_rgba": native_rgba,
                    "xbr_rgba": np.asarray(xbr_rgba, dtype=np.uint8).copy(),
                    "raw_masked_rgba": np.dstack(
                        (
                            target_rgb,
                            np.where(guide == frame.transparent, 0, 255).astype(np.uint8),
                        )
                    ),
                    "quantized_rgba": reconstruct_rgba(
                        quantized, quantization_palette, frame.transparent
                    ),
                }
        try:
            next(xbr_iterator)
        except StopIteration:
            pass
        else:
            raise RuntimeError(f"{resref}: extra xBR output")
        write_cycles(stream, cycles)
    return frame_manifest, qa_records, timing


def execute(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if (
        job.get("schema") != JOB_SCHEMA
        or job.get("installable") is not False
        or job.get("scope") != "full-animation"
    ):
        raise RuntimeError("invalid or installable ReboutCX full job")
    if int(job["reboutcx"]["target_scale"]) != 2:
        raise RuntimeError("ReboutCX target_scale must be 2")
    output = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)
    if output.exists():
        raise RuntimeError(f"full run already exists: {output}")
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise RuntimeError(f"full temporary path already exists: {temporary}")
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
    animation_id = int(job["animation_id"], 16)
    if int(source_manifest["animation_id"], 16) != animation_id:
        raise RuntimeError("source animation id differs")
    if job.get("runtime_profile") is not None and source_manifest.get(
        "runtime_profile"
    ) != job.get("runtime_profile"):
        raise RuntimeError("source runtime profile differs")
    source_layer = (source_manifest.get("layer") or {}).get("kind")
    if job.get("layer") is not None and source_layer != job.get("layer"):
        raise RuntimeError("source layer differs")
    actual_inventory = [str(item["source"]["name"]).upper() for item in resources]
    requested_inventory = [str(item["name"]).upper() for item in job["source_inventory"]]
    if actual_inventory != requested_inventory:
        raise RuntimeError("source inventory differs from full job")

    classes, classes_id = semantic_classes_for_job(job)
    palette_profiles, palette_evidence = load_palette_profiles(job)
    reference_palette = palette_profiles[0]["palette"] if palette_profiles else None
    contract_digest = render_contract_digest(job, classes, palette_evidence)
    resource_by_resref = {
        str(resource["source"]["name"]).upper(): resource for resource in resources
    }
    canonical_by_key: dict[tuple[str, str, str], str] = {}
    canonical_by_resref: dict[str, str] = {}
    for resref in actual_inventory:
        resource = resource_by_resref[resref]
        key = (
            sha256_file(resource["bam_path"]),
            sha256_file(resource["source_path"]),
            contract_digest,
        )
        canonical = canonical_by_key.setdefault(key, resref)
        canonical_by_resref[resref] = canonical

    groups, required_qa = qa_contract(job, resources, canonical_by_resref)
    marker_index = int(job["null_frame_marker"])
    descriptor, versions = load_model(
        model_path,
        device=str(job["reboutcx"]["device"]),
        fp16=bool(job["reboutcx"]["fp16"]),
    )

    qa_records_by_canonical: dict[str, dict[int, dict[str, Any]]] = {}
    manifests_by_resref: dict[str, list[dict[str, Any]]] = {}
    resource_reports: list[dict[str, Any]] = []
    component_by_resref: dict[str, Path] = {}
    timings = defaultdict(float)
    components_dir = temporary / "components"
    components_dir.mkdir(parents=True)
    for resref in actual_inventory:
        resource = resource_by_resref[resref]
        canonical = canonical_by_resref[resref]
        component_path = components_dir / f"{resref}.registry"
        reused_from: str | None = None
        if canonical == resref:
            frame_manifest, qa_records, timing = render_resource(
                resource=resource,
                component_path=component_path,
                animation_id=animation_id,
                descriptor=descriptor,
                fp16=bool(job["reboutcx"]["fp16"]),
                scalepix=scalepix,
                node=str(job["tools"].get("node", "node")),
                classes=classes,
                marker_index=marker_index,
                reference_palette=reference_palette,
                qa_indices=required_qa.get(resref, set()),
                reference=job["reference"],
            )
            manifests_by_resref[resref] = frame_manifest
            qa_records_by_canonical[resref] = qa_records
            for key, value in timing.items():
                timings[key] += float(value)
        else:
            reused_from = canonical
            origin = component_by_resref[canonical]
            copy_component_for_resref(origin, component_path, resref)
            frame_manifest = copy.deepcopy(manifests_by_resref[canonical])
            manifests_by_resref[resref] = frame_manifest
        component_by_resref[resref] = component_path
        registry_info = validate_component_registry(
            component_path,
            animation_id=animation_id,
            resource=resource,
            frame_manifest=manifests_by_resref[resref],
        )
        cycles = ordered_cycles(resource)
        registry_info.pop("resource_records", None)
        resource_reports.append(
            {
                "resref": resref,
                "source": relative(resource["source_path"]),
                "source_sha256": sha256_file(resource["source_path"]),
                "canonical_bam_sha256": sha256_file(resource["bam_path"]),
                "reused_render_from": reused_from,
                "frames": len(resource["frames"]),
                "null_frames": sum(is_null_frame(frame, marker_index) for frame in resource["frames"]),
                "cycles": len(cycles),
                "cycle_slots": sum(len(item["frame_indices"]) for item in cycles),
                "frame_records": manifests_by_resref[resref],
                "component": {
                    "path": relative(component_path),
                    "sha256": sha256_file(component_path),
                    "registry": registry_info,
                },
            }
        )


    qa_results: dict[tuple[str, int], dict[str, Any]] = {}
    for group in groups:
        resref = str(group["resref"]).upper()
        canonical = canonical_by_resref[resref]
        target_frames = {frame.index: frame for frame in resource_by_resref[resref]["frames"]}
        for index in [int(value) for value in group["frames"]]:
            record = copy.copy(qa_records_by_canonical[canonical][index])
            record["frame"] = target_frames[index]
            qa_results[(resref, index)] = record
    qa = [
        make_group_comparison(
            group,
            qa_results,
            temporary / "qa" / f"{group['name']}.gif",
        )
        for group in groups
    ]

    all_records = [record for report in resource_reports for record in report["frame_records"]]
    visible = sum(int(record["visible_pixels"]) for record in all_records)
    evaluated_records = [record for record in all_records if not record["model_bypassed"]]
    evaluated_visible = sum(int(record["visible_pixels"]) for record in evaluated_records)
    weighted_error = sum(
        float(record["oklab_error_mean"]) * int(record["visible_pixels"])
        for record in evaluated_records
    )
    manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed-pending-human-review",
        "installable": False,
        "scope": "full-animation",
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "source_manifest": relative(source_manifest_path),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "animation_id": job["animation_id"],
        "runtime_profile": job.get("runtime_profile"),
        "layer": job.get("layer"),
        "model_sha256": sha256_file(model_path),
        "target_scale": 2,
        "versions": versions,
        "semantic_classes_id": classes_id,
        "semantic_classes": classes,
        "palette_reference": palette_evidence,
        "render_contract_sha256": contract_digest,
        "code": {
            "reboutcx_full": {"path": relative(Path(__file__)), "sha256": sha256_file(Path(__file__))},
            "reboutcx_batch": {"path": relative(SCRIPT_DIR / "reboutcx_batch.py"), "sha256": sha256_file(SCRIPT_DIR / "reboutcx_batch.py")},
            "reboutcx_quantize": {"path": relative(SCRIPT_DIR / "reboutcx_quantize.py"), "sha256": sha256_file(SCRIPT_DIR / "reboutcx_quantize.py")},
            "creature_sprite_x2": {"path": relative(SCRIPT_DIR / "run_creature_sprite_x2.py"), "sha256": sha256_file(SCRIPT_DIR / "run_creature_sprite_x2.py")},
            "bam_export": {"path": relative(SCRIPT_DIR / "bam_export.py"), "sha256": sha256_file(SCRIPT_DIR / "bam_export.py")},
            "xbr_adapter": {"path": relative(SCRIPT_DIR / "xbr2x_batch.js"), "sha256": sha256_file(SCRIPT_DIR / "xbr2x_batch.js")},
            "scalepix": {"path": str(job["paths"]["scalepix"]), "sha256": sha256_file(scalepix)},
            "chainner_python": {"path": str(job["paths"]["chainner_python"]), "sha256": sha256_file(Path(sys.executable))},
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
                palette_evidence["id"] if palette_evidence is not None else "source-bam"
            ),
            "dither": False,
            "duplicate_source_policy": (
                "render once per BAM/BAMC/render-contract digest; clone component payload; "
                "verify each resref"
            ),
        },
        "coverage": {
            "resources": len(resources),
            "frames": len(frames),
            "null_frames": sum(is_null_frame(frame, marker_index) for frame in frames),
            "cycles": sum(len(resource["cycles"]) for resource in resources),
            "cycle_slots": sum(
                len(cycle["frame_indices"])
                for resource in resources
                for cycle in resource["cycles"]
            ),
            "unique_source_payloads": len(canonical_by_key),
            "unique_model_frames": int(timings["model_frames"]),
        },
        "timing_seconds": {
            "xbr": timings["xbr"],
            "reboutcx": timings["reboutcx"],
            "quantization": timings["quantization"],
        },
        "metrics": {
            "visible_pixels": visible,
            "model_evaluated_visible_pixels": evaluated_visible,
            "weighted_oklab_error_mean": (
                weighted_error / evaluated_visible if evaluated_visible else 0.0
            ),
            "worst_frame_p95": max(
                (float(record["oklab_error_p95"]) for record in evaluated_records),
                default=0.0,
            ),
            "worst_frame_max": max(
                (float(record["oklab_error_max"]) for record in evaluated_records),
                default=0.0,
            ),
        },
        "qa_contract": job["qa"],
        "qa": qa,
        "resources": resource_reports,
        "components": {
            "count": len(resource_reports),
            "total_bytes": sum(Path(report["component"]["path"]).stat().st_size if Path(report["component"]["path"]).is_absolute() else component_by_resref[report["resref"]].stat().st_size for report in resource_reports),
            "format": "IEECSXN V3 x2 raw; one non-installable component per resref",
        },
    }
    temporary_prefix = relative(temporary)
    output_prefix = relative(output)
    manifest = json.loads(json.dumps(manifest).replace(temporary_prefix, output_prefix))
    (temporary / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    temporary.rename(output)
    final_manifest = output / "manifest.json"
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "run": relative(output),
                "manifest_sha256": sha256_file(final_manifest),
                "resources": len(resources),
                "frames": len(frames),
                "components": len(resource_reports),
            },
            indent=2,
        )
    )
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
        or manifest.get("scope") != "full-animation"
        or int(manifest.get("target_scale", 0)) != 2
    ):
        raise RuntimeError("invalid ReboutCX full manifest")
    if manifest.get("job_sha256") != sha256_file(job_path):
        raise RuntimeError("full job hash differs")
    if manifest.get("source_manifest_sha256") != sha256_file(
        resolve_path_reference(job["paths"]["source_manifest"], required=True, root=PROJECT_ROOT)
    ):
        raise RuntimeError("source manifest hash differs")
    classes, classes_id = semantic_classes_for_job(job)
    _palette_profiles, palette_evidence = load_palette_profiles(job)
    if classes_id is not None:
        if (
            manifest.get("semantic_classes_id") != classes_id
            or manifest.get("semantic_classes") != classes
            or manifest.get("palette_reference") != palette_evidence
            or manifest.get("render_contract_sha256")
            != render_contract_digest(job, classes, palette_evidence)
        ):
            raise RuntimeError("Character render contract differs")
    for evidence in manifest["code"].values():
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError(f"full code/input hash differs: {evidence['path']}")
    _, resources, source_manifest = load_source_frames(
        resolve_path_reference(manifest["source_manifest"], required=True, root=PROJECT_ROOT)
    )
    report_by_resref = {report["resref"]: report for report in manifest["resources"]}
    checked = 0
    for resource in resources:
        resref = str(resource["source"]["name"]).upper()
        report = report_by_resref[resref]
        path = resolve_path_reference(report["component"]["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != report["component"]["sha256"]:
            raise RuntimeError(f"{resref}: component hash differs")
        info = validate_component_registry(
            path,
            animation_id=int(source_manifest["animation_id"], 16),
            resource=resource,
            frame_manifest=report["frame_records"],
        )
        for key in ("version", "scale", "animation_id", "resource_count", "frame_count", "index_bytes", "registry_bytes", "sha256", "crc32"):
            if info[key] != report["component"]["registry"][key]:
                raise RuntimeError(f"{resref}: component inspection differs: {key}")
        checked += 1
    for evidence in manifest["qa"]:
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != evidence["sha256"]:
            raise RuntimeError(f"QA hash differs: {evidence['path']}")
        checked += 1
    result = {
        "status": "verified",
        "run": relative(output),
        "manifest_sha256": sha256_file(manifest_path),
        "resources": manifest["coverage"]["resources"],
        "frames": manifest["coverage"]["frames"],
        "checked_files": checked + 2,
    }
    print(json.dumps(result, indent=2))
    return result


def run_via_configured_python(job_path: Path) -> int:
    job = read_json(job_path)
    python_path = resolve_path_reference(
        job["paths"]["chainner_python"], required=True, root=PROJECT_ROOT
    ).resolve()
    expected = str(job["tools"].get("chainner_python_sha256", ""))
    if expected and sha256_file(python_path) != expected:
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
    for name in ("run", "_execute", "verify"):
        command = subparsers.add_parser(name)
        command.add_argument("job", type=Path)
    args = parser.parse_args(argv)
    job_path = args.job.resolve()
    if args.command == "run":
        return run_via_configured_python(job_path)
    if args.command == "_execute":
        execute(job_path)
        return 0
    verify(job_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
