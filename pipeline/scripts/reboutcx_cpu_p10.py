"""P10 CPU primitives. Historical modules are imported read-only; no monkeypatching."""
from __future__ import annotations
import hashlib
import struct
from functools import lru_cache
from pathlib import Path
from typing import Any, BinaryIO, Mapping, Sequence
import numpy as np
from reboutcx_full import (read_exact, ordered_cycles, sha256_file)
from reboutcx_quantize import (QUANTIZER_ID, index_class_table, srgb_u8_to_oklab,
    source_representatives as legacy_representatives)
from run_creature_sprite_x2 import (SourceFrame, inspect_registry, REGISTRY_HEADER_BYTES,
    REGISTRY_RESOURCE_HEADER_BYTES, REGISTRY_FRAME_HEADER_BYTES, XN_REGISTRY_MAGIC, XN_REGISTRY_VERSION)


def source_representatives(source_indices: np.ndarray) -> np.ndarray:
    flat = np.asarray(source_indices, dtype=np.uint8).reshape(-1)
    # Preserve the historical uint16/sentinel behaviour on oversized native frames.
    if flat.size > 65535:
        return legacy_representatives(flat)
    result = np.full(256, 0xFFFF, dtype=np.uint16)
    values, first = np.unique(flat, return_index=True)
    result[values] = first.astype(np.uint16)
    return result


@lru_cache(maxsize=64)
def palette_oklab(palette_bytes: bytes) -> np.ndarray:
    value = srgb_u8_to_oklab(np.frombuffer(palette_bytes, dtype=np.uint8).reshape(256, 3))
    value.setflags(write=False)
    return value


@lru_cache(maxsize=16)
def class_lookup(spec: tuple) -> tuple:
    table, names = index_class_table(dict(spec))
    table.setflags(write=False)
    return table, names


def map_output(
    frame: SourceFrame,
    output_rgba: bytes,
    provenance_indices: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    source_flat = frame.indices.reshape(-1)
    representatives = source_representatives(source_flat)
    color_to_index: dict[int, int] = {}
    for value in np.unique(source_flat).tolist():
        rgba = bytes([int(frame.palette[value, 0]), int(frame.palette[value, 1]), int(frame.palette[value, 2]), 0 if value == frame.transparent else 255])
        packed = int.from_bytes(rgba, "little")
        previous = color_to_index.get(packed)
        if previous is not None and previous != value and provenance_indices is None:
            raise RuntimeError(f"{frame.resref} frame {frame.index}: duplicate used RGBA indices {previous}/{value}")
        color_to_index[packed] = value
    pixels = np.frombuffer(output_rgba, dtype=np.uint8).reshape(-1, 4)
    if not np.all((pixels[:, 3] == 0) | (pixels[:, 3] == 255)):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: partial alpha")
    if provenance_indices is not None:
        mapped = np.asarray(provenance_indices, dtype=np.uint8).reshape(-1)
        if mapped.size != len(pixels):
            raise RuntimeError(
                f"{frame.resref} frame {frame.index}: provenance dimensions differ from xBR output"
            )
        if np.any(representatives[mapped] == 0xFFFF):
            raise RuntimeError(f"{frame.resref} frame {frame.index}: missing palette representative")
        expected = np.empty_like(pixels)
        expected[:, :3] = frame.palette[mapped]
        expected[:, 3] = np.where(mapped == frame.transparent, 0, 255)
        if not np.array_equal(expected, pixels):
            raise RuntimeError(
                f"{frame.resref} frame {frame.index}: palette-index provenance differs from xBR output"
            )
        return mapped, representatives
    packed_pixels = pixels.copy().view("<u4").reshape(-1)
    unique_colors, inverse = np.unique(packed_pixels, return_inverse=True)
    mapped_unique = np.empty(len(unique_colors), dtype=np.uint8)
    for unique_index, color in enumerate(unique_colors.tolist()):
        palette_index = color_to_index.get(int(color))
        if palette_index is None:
            raise RuntimeError(
                f"{frame.resref} frame {frame.index}: xBR introduced "
                f"{int(color).to_bytes(4, 'little').hex()}"
            )
        mapped_unique[unique_index] = palette_index
    mapped = mapped_unique[inverse]
    if np.any(representatives[mapped] == 0xFFFF):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: missing palette representative")
    return mapped, representatives


def write_frame_record(stream: BinaryIO, frame: SourceFrame, indices: np.ndarray, representatives: np.ndarray | None = None) -> None:
    payload = np.ascontiguousarray(indices, dtype=np.uint8)
    if payload.shape != (frame.height * 2, frame.width * 2):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: invalid x2 payload shape")
    if representatives is None:
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


def quantize_classed_oklab(
    target_rgb: np.ndarray,
    guide_indices: np.ndarray,
    palette_rgb: np.ndarray,
    used_indices: Sequence[int] | np.ndarray,
    classes: Mapping[str, Sequence[int]],
    *,
    transparent_index: int,
    chunk_pixels: int = 8192,
) -> tuple[np.ndarray, dict[str, Any]]:
    target = np.asarray(target_rgb, dtype=np.uint8)
    guide = np.asarray(guide_indices, dtype=np.uint8)
    palette = np.asarray(palette_rgb, dtype=np.uint8)
    if target.ndim != 3 or target.shape[2] != 3 or target.shape[:2] != guide.shape:
        raise RuntimeError("target RGB and guide dimensions differ")
    if palette.shape != (256, 3):
        raise RuntimeError("palette must contain 256 RGB entries")
    if not 0 <= int(transparent_index) <= 255:
        raise RuntimeError("transparent palette index is invalid")
    if chunk_pixels <= 0:
        raise RuntimeError("quantization chunk must be positive")

    used = np.asarray(sorted({int(value) for value in used_indices}), dtype=np.int16)
    if used.size == 0 or np.any((used < 0) | (used > 255)):
        raise RuntimeError("used palette indices are invalid")
    class_table, class_names = class_lookup(tuple((name, tuple(values)) for name, values in classes.items()))
    guide_classes = class_table[guide]
    if np.any(guide_classes < 0):
        missing = int(np.min(guide[guide_classes < 0]))
        raise RuntimeError(f"guide index {missing} has no semantic class")

    target_lab = srgb_u8_to_oklab(target).reshape(-1, 3)
    palette_lab = palette_oklab(palette.tobytes())
    flat_classes = guide_classes.reshape(-1)
    output = np.empty(flat_classes.size, dtype=np.uint8)
    squared_errors = np.empty(flat_classes.size, dtype=np.float64)
    class_counts: dict[str, int] = {}

    for class_id, name in enumerate(class_names):
        positions = np.flatnonzero(flat_classes == class_id)
        if not positions.size:
            continue
        candidates = np.asarray(
            sorted(set(int(value) for value in classes[name]).intersection(used.tolist())),
            dtype=np.int16,
        )
        if not candidates.size:
            raise RuntimeError(f"class {name} has no used palette candidate")
        candidate_lab = palette_lab[candidates]
        class_counts[name] = int(positions.size)
        for start in range(0, positions.size, chunk_pixels):
            current = positions[start : start + chunk_pixels]
            delta = target_lab[current, None, :] - candidate_lab[None, :, :]
            distances = np.einsum("nci,nci->nc", delta, delta, optimize=True)
            choices = np.argmin(distances, axis=1)
            output[current] = candidates[choices].astype(np.uint8)
            squared_errors[current] = distances[np.arange(current.size), choices]

    output = output.reshape(guide.shape)
    if not set(np.unique(output).tolist()).issubset(set(used.tolist())):
        raise RuntimeError("quantizer emitted an index absent from the source frame")
    if not np.array_equal(class_table[output], guide_classes):
        raise RuntimeError("quantizer changed a semantic palette class")
    transparent_mask = guide == int(transparent_index)
    if np.any(output[transparent_mask] != int(transparent_index)):
        raise RuntimeError("quantizer changed transparent pixels")

    visible = ~transparent_mask.reshape(-1)
    visible_errors = np.sqrt(squared_errors[visible])
    metrics = {
        "quantizer": QUANTIZER_ID,
        "pixels": int(output.size),
        "visible_pixels": int(visible.sum()),
        "class_pixels": class_counts,
        "output_indices": [int(value) for value in np.unique(output)],
        "oklab_error_mean": float(np.mean(visible_errors)) if visible_errors.size else 0.0,
        "oklab_error_p95": float(np.percentile(visible_errors, 95)) if visible_errors.size else 0.0,
        "oklab_error_max": float(np.max(visible_errors)) if visible_errors.size else 0.0,
    }
    return output, metrics
