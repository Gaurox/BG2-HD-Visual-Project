"""Deterministic palette quantization for ReboutCX creature-sprite candidates."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

import numpy as np


QUANTIZER_ID = "oklab-euclidean-f64-classed-no-dither-v1"


def expand_index_spec(value: object) -> list[int]:
    if isinstance(value, list):
        result = [int(item) for item in value]
    elif isinstance(value, str) and ".." in value:
        first, last = (int(item) for item in value.split("..", 1))
        result = list(range(first, last + 1))
    else:
        raise RuntimeError(f"invalid palette-index specification: {value!r}")
    if not result or result != sorted(set(result)) or any(not 0 <= item <= 255 for item in result):
        raise RuntimeError(f"invalid palette-index set: {value!r}")
    return result


def expand_classes(specifications: Mapping[str, object]) -> dict[str, list[int]]:
    classes = {
        str(name): expand_index_spec(value)
        for name, value in specifications.items()
    }
    if not classes:
        raise RuntimeError("semantic palette classes are empty")
    seen: set[int] = set()
    for name, indices in classes.items():
        overlap = seen.intersection(indices)
        if overlap:
            raise RuntimeError(f"palette classes overlap at {min(overlap)} ({name})")
        seen.update(indices)
    return classes


def index_class_table(classes: Mapping[str, Sequence[int]]) -> tuple[np.ndarray, list[str]]:
    names = list(classes)
    table = np.full(256, -1, dtype=np.int16)
    for class_id, name in enumerate(names):
        for index in classes[name]:
            value = int(index)
            if not 0 <= value <= 255 or table[value] != -1:
                raise RuntimeError(f"invalid or duplicate palette class index: {value}")
            table[value] = class_id
    return table, names


def srgb_u8_to_oklab(rgb: np.ndarray) -> np.ndarray:
    values = np.asarray(rgb, dtype=np.float64)
    if values.shape[-1] != 3:
        raise RuntimeError("OKLab input must have three channels")
    values = values / 255.0
    linear = np.where(
        values <= 0.04045,
        values / 12.92,
        ((values + 0.055) / 1.055) ** 2.4,
    )
    red, green, blue = np.moveaxis(linear, -1, 0)
    l = 0.4122214708 * red + 0.5363325363 * green + 0.0514459929 * blue
    m = 0.2119034982 * red + 0.6806995451 * green + 0.1073969566 * blue
    s = 0.0883024619 * red + 0.2817188376 * green + 0.6299787005 * blue
    l_root, m_root, s_root = np.cbrt(l), np.cbrt(m), np.cbrt(s)
    return np.stack(
        (
            0.2104542553 * l_root + 0.7936177850 * m_root - 0.0040720468 * s_root,
            1.9779984951 * l_root - 2.4285922050 * m_root + 0.4505937099 * s_root,
            0.0259040371 * l_root + 0.7827717662 * m_root - 0.8086757660 * s_root,
        ),
        axis=-1,
    )


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
    class_table, class_names = index_class_table(classes)
    guide_classes = class_table[guide]
    if np.any(guide_classes < 0):
        missing = int(np.min(guide[guide_classes < 0]))
        raise RuntimeError(f"guide index {missing} has no semantic class")

    target_lab = srgb_u8_to_oklab(target).reshape(-1, 3)
    palette_lab = srgb_u8_to_oklab(palette)
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


def source_representatives(source_indices: np.ndarray) -> np.ndarray:
    flat = np.asarray(source_indices, dtype=np.uint8).reshape(-1)
    representatives = np.full(256, 0xFFFF, dtype=np.uint16)
    for offset, value in enumerate(flat.tolist()):
        if representatives[value] == 0xFFFF:
            representatives[value] = offset
    return representatives


def reconstruct_rgba(
    indices: np.ndarray, palette_rgb: np.ndarray, transparent_index: int
) -> np.ndarray:
    mapped = np.asarray(indices, dtype=np.uint8)
    rgba = np.empty((*mapped.shape, 4), dtype=np.uint8)
    rgba[..., :3] = np.asarray(palette_rgb, dtype=np.uint8)[mapped]
    rgba[..., 3] = np.where(mapped == int(transparent_index), 0, 255).astype(np.uint8)
    return rgba
