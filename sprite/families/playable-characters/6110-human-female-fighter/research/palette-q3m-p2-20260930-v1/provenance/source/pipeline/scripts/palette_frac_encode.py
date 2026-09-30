"""P1 Character Q6/Q3m reference encoder; logical I/F planes, no runtime writer."""
from __future__ import annotations

from functools import lru_cache
from typing import Sequence

import numpy as np

from reboutcx_quantize import (
    character_chmb1_classes, index_class_table, srgb_u8_to_oklab,
)

DECODE_RULE = "ramp-lerp-srgb8-v1"
CLASS_PROFILE = "character-bg2ee-2.7.3.0"
ENCODER_ID = "character-exhaustive-oklab-squared-q3-integer-v1"
CLASSES = character_chmb1_classes()
CLASS_TABLE, CLASS_NAMES = index_class_table(CLASSES)


def checked_u8(value, name: str) -> np.ndarray:
    array = np.asarray(value)
    if (not np.issubdtype(array.dtype, np.integer) or
            np.any(array < 0) or np.any(array > 255)):
        raise ValueError(f"{name} must contain u8 integers")
    return array.astype(np.uint8, copy=False)


@lru_cache(maxsize=1)
def successors() -> np.ndarray:
    indices = np.arange(256, dtype=np.uint16)
    terminal = ((indices <= 3) |
                ((indices >= 4) & (indices <= 87) & ((indices - 4) % 12 == 11)) |
                ((indices >= 88) & ((indices - 88) % 8 == 7)))
    result = np.where(terminal, indices, indices + 1).astype(np.uint8)
    result.setflags(write=False)
    return result


def validate_planes(indices, fractions) -> tuple[np.ndarray, np.ndarray]:
    i = checked_u8(indices, "I")
    f = checked_u8(fractions, "F")
    if i.shape != f.shape or i.ndim != 2 or not i.size:
        raise ValueError("I/F require matching, nonempty 2D planes")
    if np.any(f > 7) or np.any((f > 0) & (successors()[i] == i)):
        raise ValueError("invalid fraction or fractional terminal/special index")
    return i, f


def decode(indices, fractions, palette) -> np.ndarray:
    """Native RGB/RGBA/BGRA bytes; alpha copied from primary entry when present."""
    i, f = validate_planes(indices, fractions)
    p = checked_u8(palette, "palette")
    if p.shape not in ((256, 3), (256, 4)):
        raise ValueError("palette must have 256 RGB or native RGBA/BGRA entries")
    a = p[i, :3].astype(np.uint16)
    b = p[successors()[i], :3].astype(np.uint16)
    fraction = f[..., None].astype(np.uint16)
    rgb = ((a * (8 - fraction) + b * fraction + 4) >> 3).astype(np.uint8)
    return rgb if p.shape[1] == 3 else np.dstack((rgb, p[i, 3]))


def dependency_mask(indices, fractions) -> np.ndarray:
    i, f = validate_planes(indices, fractions)
    bits = np.zeros(256, dtype=np.uint8)
    bits[np.unique(i)] = 1
    bits[np.unique(successors()[i[f > 0]])] = 1
    return np.packbits(bits, bitorder="little")


def check_contract(guide, indices, fractions, dep_mask=None) -> dict:
    g = checked_u8(guide, "guide")
    i, f = validate_planes(indices, fractions)
    if g.shape != i.shape:
        raise ValueError("guide and I/F dimensions differ")
    leaks = int(np.count_nonzero(CLASS_TABLE[g] != CLASS_TABLE[i]))
    changed_special = int(np.count_nonzero((g <= 3) & ((g != i) | (f != 0))))
    exact_mask = dependency_mask(i, f)
    if dep_mask is not None and not np.array_equal(dep_mask, exact_mask):
        raise ValueError("dependency mask is not exact")
    if leaks or changed_special:
        raise ValueError(f"semantic leak={leaks}, changed specials={changed_special}")
    return {"class_leaks": leaks, "changed_specials": changed_special,
            "fractional_pixels": int(np.count_nonzero(f)),
            "dependency_entries": int(np.unpackbits(exact_mask).sum())}


@lru_cache(maxsize=32)
def candidates(class_id: int) -> tuple[np.ndarray, np.ndarray]:
    pairs = [(i, f) for i in CLASSES[CLASS_NAMES[class_id]]
             for f in (range(8) if successors()[i] != i else (0,))]
    return tuple(np.asarray([p[k] for p in pairs], dtype=np.uint8) for k in (0, 1))


def encode_variants(guide, targets, palettes, *, ks: Sequence[int] = (3, 4, 6),
                    weights=None, chunk_pixels: int = 512) -> dict:
    """Float targets in [0,1]; nested K fits share an exhaustive cost calculation.

    Distances are evaluated directly in f64 (no projected polyline). Sorted
    candidates and np.argmin implement lowest I, then lowest F tie breaking.
    """
    g = checked_u8(guide, "guide")
    p = checked_u8(palettes, "palettes")
    t = np.asarray(targets, dtype=np.float64)
    ks = tuple(sorted(set(int(k) for k in ks)))
    if (g.ndim != 2 or p.ndim != 3 or p.shape[1:] != (256, 3) or
            t.shape != (len(p), *g.shape, 3) or not ks or
            min(ks) < 1 or max(ks) > len(p) or chunk_pixels < 1 or
            not np.isfinite(t).all() or np.any(t < 0) or np.any(t > 1)):
        raise ValueError("invalid encoder inputs")
    w = np.ones(len(p), dtype=np.float64) if weights is None else np.asarray(weights, dtype=np.float64)
    if w.shape != (len(p),) or not np.isfinite(w).all() or np.any(w <= 0):
        raise ValueError("palette weights must be finite and positive")
    outputs = {f"{method}-k{k}": (g.copy(), np.zeros_like(g))
               for k in ks for method in ("Q6", "Q3m")}
    target_lab = srgb_u8_to_oklab(t * 255).reshape(len(p), -1, 3)
    flat_class = CLASS_TABLE[g].reshape(-1)
    for class_id in np.unique(flat_class):
        if class_id < 4:
            continue
        positions = np.flatnonzero(flat_class == class_id)
        ci, cf = candidates(int(class_id))
        indexed_candidates = np.flatnonzero(cf == 0)
        cand_labs = np.stack([srgb_u8_to_oklab(decode(ci[None], cf[None], pal)[0]) for pal in p])
        for start in range(0, len(positions), chunk_pixels):
            loc = positions[start:start + chunk_pixels]
            cost = np.zeros((len(loc), len(ci)), dtype=np.float64)
            for k in range(1, max(ks) + 1):
                delta = target_lab[k-1, loc, None, :] - cand_labs[k-1, None, :, :]
                cost += w[k-1] * np.einsum("nci,nci->nc", delta, delta, optimize=True)
                if k not in ks:
                    continue
                for method, allowed in (("Q3m", np.arange(len(ci))), ("Q6", indexed_candidates)):
                    choice = allowed[np.argmin(cost[:, allowed], axis=1)]
                    oi, of = outputs[f"{method}-k{k}"]
                    oi.reshape(-1)[loc], of.reshape(-1)[loc] = ci[choice], cf[choice]
    result = {}
    for name, (i, f) in outputs.items():
        mask = dependency_mask(i, f)
        result[name] = {"I": i, "F": f, "dep_mask": mask,
                        "checks": check_contract(g, i, f, mask)}
    return result
