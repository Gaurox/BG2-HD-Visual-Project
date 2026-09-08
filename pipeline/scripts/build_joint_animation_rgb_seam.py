"""Repair a world-aligned seam between two 30 fps animation runtime packs.

The source packs remain immutable.  The resulting multi-resource batch preserves
all RGBA geometry, changes RGB only in the mutually opaque seam band, and writes
two independently valid runtime packs for later area merging.  An optional alpha
reference can restore only large connected regions removed by a faulty spline fit.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))

from bam_export import decode_bam  # noqa: E402
from export_bam_frames import cycle_metadata  # noqa: E402
import run_animation_upscale_30fps_v2 as runtime  # noqa: E402


SCHEMA = "bg2-upscale-animation-joint-rgb-seam-batch-v3"
BLEND_MODES = ("symmetric-midpoint", "continue-top-into-bottom")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def parse_position(value: str) -> tuple[int, int]:
    values = value.split(",")
    require(len(values) == 2 and all(item.strip() for item in values),
            f"position X,Y attendue : {value}")
    try:
        return int(values[0]), int(values[1])
    except ValueError as exc:
        raise RuntimeError(f"position invalide : {value}") from exc


def smoothstep(value: float) -> float:
    clamped = min(1.0, max(0.0, value))
    return clamped * clamped * (3.0 - 2.0 * clamped)


@dataclass(frozen=True)
class FrameLayout:
    width: int
    height: int
    origin_x: int
    origin_y: int


@dataclass(frozen=True)
class PackInput:
    root: Path
    manifest: dict[str, Any]
    resource: dict[str, Any]
    position_x1: tuple[int, int]


def load_single_resource_pack(path: Path, position_x1: tuple[int, int]) -> PackInput:
    root = path.resolve()
    manifest, resources = runtime.validate_v2_pack(root)
    require(len(resources) == 1, f"pack mono-ressource attendu : {root}")
    resource = copy.deepcopy(resources[0])
    require(resource.get("playback_mode") == "TimedTimeline",
            f"{resource.get('resref', '?')}: TimedTimeline 30 fps requis")
    return PackInput(root, manifest, resource, position_x1)


def sorted_frames(resource: dict[str, Any]) -> list[dict[str, Any]]:
    frames = sorted(resource.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    frame_count = int(resource.get("frame_count", 0))
    require(len(frames) == frame_count and
            [int(item.get("frame", -1)) for item in frames] == list(range(frame_count)),
            f"{resource.get('resref', '?')}: frames non contiguës")
    return frames


def frame_layout(frame: dict[str, Any], position_x1: tuple[int, int]) -> FrameLayout:
    physical = [int(value) for value in frame.get("physical_size_x4") or []]
    logical = [int(value) for value in frame.get("logical_size_x1") or []]
    centre = frame.get("centre_x1")
    require(len(physical) == len(logical) == 2 and
            physical == [logical[0] * 4, logical[1] * 4] and
            isinstance(centre, list) and len(centre) == 2,
            "géométrie x4/centre de frame invalide")
    centre_x, centre_y = (int(value) for value in centre)
    return FrameLayout(
        width=physical[0], height=physical[1],
        origin_x=(position_x1[0] - centre_x) * 4,
        origin_y=(position_x1[1] - centre_y) * 4,
    )


def compatible_timeline(top: dict[str, Any], bottom: dict[str, Any]) -> None:
    require(top.get("native_fps") == bottom.get("native_fps") and
            top.get("target_fps") == bottom.get("target_fps"),
            "cadences des deux animations incompatibles")
    top_cycles = sorted(top.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    bottom_cycles = sorted(bottom.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    require(len(top_cycles) == len(bottom_cycles) and top_cycles,
            "cycles des deux animations incompatibles")
    for index, (top_cycle, bottom_cycle) in enumerate(zip(top_cycles, bottom_cycles, strict=True)):
        require(int(top_cycle.get("cycle", -1)) == int(bottom_cycle.get("cycle", -1)) == index and
                top_cycle.get("native_frame_indices") == bottom_cycle.get("native_frame_indices") and
                top_cycle.get("timeline_frame_indices") == bottom_cycle.get("timeline_frame_indices"),
                f"cycle {index}: timeline B/C incompatible")


def validate_alpha_reference(bottom: PackInput, reference: PackInput) -> list[dict[str, Any]]:
    require(runtime.normalise_resref(str(bottom.resource.get("resref", ""))) ==
            runtime.normalise_resref(str(reference.resource.get("resref", ""))),
            "la référence alpha doit viser la ressource inférieure")
    compatible_timeline(bottom.resource, reference.resource)
    bottom_frames = sorted_frames(bottom.resource)
    reference_frames = sorted_frames(reference.resource)
    require(len(bottom_frames) == len(reference_frames),
            "nombre de frames divergent pour la référence alpha")
    for index, (bottom_frame, reference_frame) in enumerate(
            zip(bottom_frames, reference_frames, strict=True)):
        require(frame_layout(bottom_frame, bottom.position_x1) ==
                frame_layout(reference_frame, reference.position_x1),
                f"frame {index}: géométrie de la référence alpha incompatible")
    return reference_frames


def validate_pair(top: PackInput, bottom: PackInput, seam_depth_x4: int) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    top_ref = runtime.normalise_resref(str(top.resource.get("resref", "")))
    bottom_ref = runtime.normalise_resref(str(bottom.resource.get("resref", "")))
    require(top_ref != bottom_ref, "les deux entrées doivent être des ressources distinctes")
    compatible_timeline(top.resource, bottom.resource)
    top_frames = sorted_frames(top.resource)
    bottom_frames = sorted_frames(bottom.resource)
    require(len(top_frames) == len(bottom_frames), "nombre de frames B/C divergent")
    require(seam_depth_x4 > 0, "profondeur de raccord positive requise")
    for index, (top_frame, bottom_frame) in enumerate(zip(top_frames, bottom_frames, strict=True)):
        top_layout = frame_layout(top_frame, top.position_x1)
        bottom_layout = frame_layout(bottom_frame, bottom.position_x1)
        require(top_layout.height > seam_depth_x4 and bottom_layout.height > seam_depth_x4,
                f"frame {index}: profondeur de raccord hors canvas")
        require(top_layout.origin_y + top_layout.height == bottom_layout.origin_y,
                f"frame {index}: les bords B/C ne sont pas jointifs")
        require(max(top_layout.origin_x, bottom_layout.origin_x) <
                min(top_layout.origin_x + top_layout.width, bottom_layout.origin_x + bottom_layout.width),
                f"frame {index}: aucune largeur commune au raccord")
    return top_frames, bottom_frames


def read_rgba(path: Path, layout: FrameLayout) -> np.ndarray:
    expected = layout.width * layout.height * 4
    require(path.is_file() and path.stat().st_size == expected,
            f"RGBA absent ou tronqué : {path}")
    return np.frombuffer(path.read_bytes(), dtype=np.uint8).reshape(
        layout.height, layout.width, 4
    ).copy()


def restore_large_removed_alpha(current_pixels: np.ndarray, reference_pixels: np.ndarray,
                                min_pixels: int) -> tuple[np.ndarray, dict[str, Any]]:
    """Restore reference alpha only in large connected regions lost by the current fit."""
    require(current_pixels.shape == reference_pixels.shape, "dimensions alpha incompatibles")
    require(min_pixels > 0, "seuil de composante alpha positif requis")
    current_alpha = current_pixels[:, :, 3]
    reference_alpha = reference_pixels[:, :, 3]
    removed = reference_alpha > current_alpha
    labels, count = ndimage.label(removed, structure=np.ones((3, 3), dtype=np.uint8))
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    selected = [int(label) for label in range(1, count + 1)
                if int(sizes[label]) >= min_pixels]
    restore_mask = np.isin(labels, selected)
    output = current_pixels.copy()
    output[:, :, 3][restore_mask] = reference_alpha[restore_mask]
    components = []
    for label in selected:
        ys, xs = np.nonzero(labels == label)
        components.append({
            "pixels": int(sizes[label]),
            "bbox_x4": [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1],
        })
    require(np.array_equal(output[:, :, 3][~restore_mask], current_alpha[~restore_mask]),
            "la restauration alpha a modifié des pixels hors composante retenue")
    require(np.array_equal(output[:, :, 3][restore_mask], reference_alpha[restore_mask]),
            "la restauration alpha ne correspond pas à la référence")
    return output, {
        "candidate_removed_components": int(count),
        "selected_components": len(selected),
        "restored_alpha_pixels": int(restore_mask.sum()),
        "min_component_pixels": min_pixels,
        "components": components,
    }


def add_top_overlap(top_pixels: np.ndarray, bottom_pixels: np.ndarray, *,
                    top_layout: FrameLayout, bottom_layout: FrameLayout,
                    overlap_x4: int) -> tuple[np.ndarray, FrameLayout, dict[str, Any]]:
    """Extend the bottom canvas upward and fade it over the unchanged top asset."""
    require(overlap_x4 > 0 and overlap_x4 % 4 == 0,
            "le recouvrement haut doit être un multiple positif de 4 px x4")
    require(overlap_x4 < top_layout.height and overlap_x4 < bottom_layout.height,
            "recouvrement haut hors canvas")
    seam_y = top_layout.origin_y + top_layout.height
    require(seam_y == bottom_layout.origin_y, "les sources doivent être jointives avant recouvrement")
    output = np.empty((bottom_layout.height + overlap_x4, bottom_layout.width, 4),
                      dtype=np.uint8)
    output[overlap_x4:] = bottom_pixels
    output[:overlap_x4, :, :3] = bottom_pixels[0:1, :, :3]
    progress = np.arange(overlap_x4, dtype=np.float32) / float(overlap_x4)
    ramp = progress * progress * (3.0 - 2.0 * progress)
    output[:overlap_x4, :, 3] = np.rint(
        bottom_pixels[0:1, :, 3].astype(np.float32) * ramp[:, None]
    ).astype(np.uint8)

    overlap_left = max(top_layout.origin_x, bottom_layout.origin_x)
    overlap_right = min(top_layout.origin_x + top_layout.width,
                        bottom_layout.origin_x + bottom_layout.width)
    top_x0 = overlap_left - top_layout.origin_x
    top_x1 = overlap_right - top_layout.origin_x
    bottom_x0 = overlap_left - bottom_layout.origin_x
    bottom_x1 = overlap_right - bottom_layout.origin_x
    top_rows = top_pixels[-overlap_x4:, top_x0:top_x1]
    extension = output[:overlap_x4, bottom_x0:bottom_x1]
    visible_top = top_rows[:, :, 3] > 0
    extension[:, :, :3] = np.where(
        visible_top[:, :, None], top_rows[:, :, :3], extension[:, :, :3]
    )
    output[:overlap_x4, bottom_x0:bottom_x1] = extension

    require(np.array_equal(output[overlap_x4:], bottom_pixels),
            "le recouvrement a modifié les pixels existants de la ressource basse")
    require(bool((output[0, :, 3] == 0).all()),
            "la première ligne du recouvrement doit être transparente")
    padded_layout = FrameLayout(
        width=bottom_layout.width,
        height=bottom_layout.height + overlap_x4,
        origin_x=bottom_layout.origin_x,
        origin_y=bottom_layout.origin_y - overlap_x4,
    )
    return output, padded_layout, {
        "top_overlap_x1": overlap_x4 // 4,
        "top_overlap_x4": overlap_x4,
        "world_overlap_rect_x4": [overlap_left, seam_y - overlap_x4,
                                    overlap_right, seam_y],
        "alpha_policy": "bottom-fade-in-smoothstep-over-unchanged-top",
        "rgb_policy": "copy-visible-top-rows-else-repeat-bottom-first-row",
        "added_nonzero_alpha_pixels": int((output[:overlap_x4, :, 3] > 0).sum()),
    }


def add_bilateral_overlap(top_pixels: np.ndarray, bottom_pixels: np.ndarray, *,
                          top_layout: FrameLayout, bottom_layout: FrameLayout,
                          extension_x4: int) -> tuple[np.ndarray, np.ndarray,
                                                      FrameLayout, FrameLayout,
                                                      dict[str, Any]]:
    """Extend both canvases and crossfade them across a shared 2*extension band."""
    require(extension_x4 > 0 and extension_x4 % 4 == 0,
            "l'extension bilatérale doit être un multiple positif de 4 px x4")
    require(extension_x4 * 2 < top_layout.height and
            extension_x4 * 2 < bottom_layout.height,
            "extension bilatérale hors canvas")
    seam_y = top_layout.origin_y + top_layout.height
    require(seam_y == bottom_layout.origin_y,
            "les sources doivent être jointives avant recouvrement bilatéral")

    output_top = np.empty((top_layout.height + extension_x4, top_layout.width, 4),
                          dtype=np.uint8)
    output_bottom = np.empty((bottom_layout.height + extension_x4,
                              bottom_layout.width, 4), dtype=np.uint8)
    output_top[:top_layout.height] = top_pixels
    output_bottom[extension_x4:] = bottom_pixels
    output_top[top_layout.height:] = top_pixels[-extension_x4:]
    output_bottom[:extension_x4] = bottom_pixels[:extension_x4]

    overlap_left = max(top_layout.origin_x, bottom_layout.origin_x)
    overlap_right = min(top_layout.origin_x + top_layout.width,
                        bottom_layout.origin_x + bottom_layout.width)
    top_x0 = overlap_left - top_layout.origin_x
    top_x1 = overlap_right - top_layout.origin_x
    bottom_x0 = overlap_left - bottom_layout.origin_x
    bottom_x1 = overlap_right - bottom_layout.origin_x

    shared = np.concatenate([
        top_pixels[-extension_x4:, top_x0:top_x1],
        bottom_pixels[:extension_x4, bottom_x0:bottom_x1],
    ], axis=0)
    output_top[top_layout.height - extension_x4:top_layout.height + extension_x4,
               top_x0:top_x1] = shared
    output_bottom[:extension_x4 * 2, bottom_x0:bottom_x1] = shared

    progress = np.arange(extension_x4 * 2, dtype=np.float32) / float(
        extension_x4 * 2 - 1
    )
    bottom_weight = progress * progress * (3.0 - 2.0 * progress)
    top_band = output_top[top_layout.height - extension_x4:
                          top_layout.height + extension_x4]
    bottom_band = output_bottom[:extension_x4 * 2]
    top_weight = 1.0 - bottom_weight
    top_band[:, :, 3] = np.rint(
        top_band[:, :, 3].astype(np.float32) * top_weight[:, None]
    ).astype(np.uint8)
    bottom_band[:, :, 3] = np.rint(
        bottom_band[:, :, 3].astype(np.float32) * bottom_weight[:, None]
    ).astype(np.uint8)
    # AM2805C is drawn after AM2805B. Complementary source alphas are not
    # complementary after source-over composition: at 50 %, an opaque pair
    # produces only 75 % combined opacity and lets the cyan map background tint
    # the seam. Split the target premultiplied contribution instead. With b the
    # lower (last-drawn) alpha and a the upper alpha:
    #     b + a * (1 - b) = target_alpha
    # This preserves both the shared RGB and the target opacity over the whole
    # transition, independently of the background colour.
    target_alpha = shared[:, :, 3].astype(np.float32) / 255.0
    weight = bottom_weight[:, None]
    bottom_alpha = target_alpha * weight
    denominator = 1.0 - bottom_alpha
    top_alpha = np.divide(
        target_alpha * (1.0 - weight), denominator,
        out=np.zeros_like(target_alpha), where=denominator > 1e-7,
    )
    top_band[:, top_x0:top_x1, 3] = np.rint(
        top_alpha * 255.0
    ).astype(np.uint8)
    bottom_band[:, bottom_x0:bottom_x1, 3] = np.rint(
        bottom_alpha * 255.0
    ).astype(np.uint8)
    output_top[top_layout.height - extension_x4:
               top_layout.height + extension_x4] = top_band
    output_bottom[:extension_x4 * 2] = bottom_band

    quantized_top = top_band[:, top_x0:top_x1, 3].astype(np.float32)
    quantized_bottom = bottom_band[:, bottom_x0:bottom_x1, 3].astype(np.float32)
    composite_alpha = quantized_bottom + quantized_top * (
        1.0 - quantized_bottom / 255.0
    )
    composite_error = np.abs(composite_alpha - shared[:, :, 3].astype(np.float32))

    require(np.array_equal(output_top[:top_layout.height - extension_x4],
                           top_pixels[:top_layout.height - extension_x4]),
            "le recouvrement bilatéral a modifié le haut hors bande")
    require(np.array_equal(output_bottom[extension_x4 * 2:],
                           bottom_pixels[extension_x4:]),
            "le recouvrement bilatéral a modifié le bas hors bande")
    require(bool((output_bottom[0, :, 3] == 0).all()) and
            bool((output_top[-1, :, 3] == 0).all()),
            "les extrémités du fondu bilatéral doivent être transparentes")

    padded_top_layout = FrameLayout(
        width=top_layout.width,
        height=top_layout.height + extension_x4,
        origin_x=top_layout.origin_x,
        origin_y=top_layout.origin_y,
    )
    padded_bottom_layout = FrameLayout(
        width=bottom_layout.width,
        height=bottom_layout.height + extension_x4,
        origin_x=bottom_layout.origin_x,
        origin_y=bottom_layout.origin_y - extension_x4,
    )
    return output_top, output_bottom, padded_top_layout, padded_bottom_layout, {
        "extension_each_x1": extension_x4 // 4,
        "extension_each_x4": extension_x4,
        "total_overlap_x1": extension_x4 // 2,
        "total_overlap_x4": extension_x4 * 2,
        "world_overlap_rect_x4": [overlap_left, seam_y - extension_x4,
                                    overlap_right, seam_y + extension_x4],
        "alpha_policy": "source-over-opacity-preserving-smoothstep-bottom-over-top",
        "rgb_policy": "source-over-colour-preserving-shared-world-field",
        "composite_alpha_max_error_u8": round(float(composite_error.max()), 6),
        "composite_alpha_mean_error_u8": round(float(composite_error.mean()), 6),
        "top_changed_alpha_pixels": int((output_top[:, :, 3] !=
                                          np.pad(top_pixels[:, :, 3],
                                                 ((0, extension_x4), (0, 0)))).sum()),
        "bottom_changed_alpha_pixels": int((output_bottom[:, :, 3] !=
                                             np.pad(bottom_pixels[:, :, 3],
                                                    ((extension_x4, 0), (0, 0)))).sum()),
    }


def read_bam(path: Path) -> bytes:
    payload = path.read_bytes()
    if payload[:4] == b"BAMC":
        payload = zlib.decompress(payload[12:])
    require(payload[:8] == b"BAM V1  ", f"BAM V1 attendu : {path}")
    return payload


def pad_bam_top(source: bytes, rows: int) -> bytes:
    """Prepend transparent native rows and move centre Y to retain world placement."""
    require(rows > 0, "padding BAM haut positif requis")
    frame_count, cycle_count, transparent = struct.unpack_from("<HBB", source, 8)
    off_frames, off_palette, off_lookup = struct.unpack_from("<III", source, 0x0C)
    frames, _palette_rgb, decoded_transparent = decode_bam(source)
    require(decoded_transparent == transparent and len(frames) == frame_count,
            "décodage BAM source incohérent")
    cycle_offset = off_frames + frame_count * 12
    cycles: list[tuple[int, int]] = []
    lookup_count = 0
    for index in range(cycle_count):
        count, start = struct.unpack_from("<HH", source, cycle_offset + index * 4)
        cycles.append((count, start))
        lookup_count = max(lookup_count, start + count)
    lookup = source[off_lookup:off_lookup + lookup_count * 2]
    palette = source[off_palette:off_palette + 256 * 4]
    require(len(lookup) == lookup_count * 2 and len(palette) == 256 * 4,
            "tables BAM source tronquées")

    new_off_frames = 24
    new_cycle_offset = new_off_frames + frame_count * 12
    new_off_palette = new_cycle_offset + cycle_count * 4
    new_off_lookup = new_off_palette + 256 * 4
    cursor = new_off_lookup + len(lookup)
    frame_table = bytearray()
    payloads: list[bytes] = []
    for indices, centre_x, centre_y, frame_transparent in frames:
        require(frame_transparent == transparent, "index transparent divergent")
        height, width = indices.shape
        new_height = height + rows
        new_centre_y = centre_y + rows
        require(width <= 0xFFFF and new_height <= 0xFFFF and
                -0x8000 <= new_centre_y <= 0x7FFF,
                "géométrie BAM dérivée hors limites")
        padded = np.full((new_height, width), transparent, dtype=np.uint8)
        padded[rows:] = indices
        raw = padded.tobytes(order="C")
        require(cursor < 0x80000000, "offset BAM dérivé hors limites")
        frame_table.extend(struct.pack(
            "<HHhhI", width, new_height, centre_x, new_centre_y, cursor | 0x80000000
        ))
        payloads.append(raw)
        cursor += len(raw)
    cycle_table = b"".join(struct.pack("<HH", count, start) for count, start in cycles)
    header = struct.pack(
        "<8sHBBIII", b"BAM V1  ", frame_count, cycle_count, transparent,
        new_off_frames, new_off_palette, new_off_lookup,
    )
    return b"".join([header, bytes(frame_table), cycle_table, palette, lookup, *payloads])


def pad_bam_bottom(source: bytes, rows: int) -> bytes:
    """Append transparent native rows without moving the native BAM centre."""
    require(rows > 0, "padding BAM bas positif requis")
    frame_count, cycle_count, transparent = struct.unpack_from("<HBB", source, 8)
    off_frames, off_palette, off_lookup = struct.unpack_from("<III", source, 0x0C)
    frames, _palette_rgb, decoded_transparent = decode_bam(source)
    require(decoded_transparent == transparent and len(frames) == frame_count,
            "décodage BAM source incohérent")
    cycle_offset = off_frames + frame_count * 12
    cycles: list[tuple[int, int]] = []
    lookup_count = 0
    for index in range(cycle_count):
        count, start = struct.unpack_from("<HH", source, cycle_offset + index * 4)
        cycles.append((count, start))
        lookup_count = max(lookup_count, start + count)
    lookup = source[off_lookup:off_lookup + lookup_count * 2]
    palette = source[off_palette:off_palette + 256 * 4]
    require(len(lookup) == lookup_count * 2 and len(palette) == 256 * 4,
            "tables BAM source tronquées")
    new_off_frames = 24
    new_cycle_offset = new_off_frames + frame_count * 12
    new_off_palette = new_cycle_offset + cycle_count * 4
    new_off_lookup = new_off_palette + 256 * 4
    cursor = new_off_lookup + len(lookup)
    frame_table = bytearray()
    payloads: list[bytes] = []
    for indices, centre_x, centre_y, frame_transparent in frames:
        require(frame_transparent == transparent, "index transparent divergent")
        height, width = indices.shape
        new_height = height + rows
        require(width <= 0xFFFF and new_height <= 0xFFFF,
                "géométrie BAM dérivée hors limites")
        padded = np.full((new_height, width), transparent, dtype=np.uint8)
        padded[:height] = indices
        raw = padded.tobytes(order="C")
        require(cursor < 0x80000000, "offset BAM dérivé hors limites")
        frame_table.extend(struct.pack(
            "<HHhhI", width, new_height, centre_x, centre_y, cursor | 0x80000000
        ))
        payloads.append(raw)
        cursor += len(raw)
    cycle_table = b"".join(struct.pack("<HH", count, start) for count, start in cycles)
    header = struct.pack(
        "<8sHBBIII", b"BAM V1  ", frame_count, cycle_count, transparent,
        new_off_frames, new_off_palette, new_off_lookup,
    )
    return b"".join([header, bytes(frame_table), cycle_table, palette, lookup, *payloads])


def derive_top_padded_bam(source_path: Path, resource: dict[str, Any],
                          padding_x1: int) -> bytes:
    source = read_bam(source_path)
    source_frames, _palette, transparent = decode_bam(source)
    runtime_frames = sorted_frames(resource)
    native_indices = sorted({int(index) for cycle in resource.get("cycles") or []
                             for index in cycle.get("native_frame_indices") or []})
    require(len(source_frames) == len(native_indices),
            "frames natives BAM/runtime divergentes")
    for source_frame, runtime_index in zip(source_frames, native_indices, strict=True):
        indices, centre_x, centre_y, _transparent = source_frame
        frame = runtime_frames[runtime_index]
        require([indices.shape[1], indices.shape[0]] == frame["logical_size_x1"] and
                [centre_x, centre_y] == frame["centre_x1"],
                f"frame native {runtime_index}: géométrie BAM/runtime divergente")
    derived = pad_bam_top(source, padding_x1)
    derived_frames, _derived_palette, derived_transparent = decode_bam(derived)
    require(derived_transparent == transparent and len(derived_frames) == len(source_frames),
            "BAM dérivé invalide")
    for source_frame, derived_frame in zip(source_frames, derived_frames, strict=True):
        source_indices, source_cx, source_cy, _ = source_frame
        derived_indices, derived_cx, derived_cy, _ = derived_frame
        require(derived_indices.shape == (source_indices.shape[0] + padding_x1,
                                          source_indices.shape[1]) and
                bool((derived_indices[:padding_x1] == transparent).all()) and
                np.array_equal(derived_indices[padding_x1:], source_indices) and
                (derived_cx, derived_cy) == (source_cx, source_cy + padding_x1),
                "pixels, padding ou centres du BAM dérivé divergents")
    require(cycle_metadata(source, len(source_frames)) ==
            cycle_metadata(derived, len(derived_frames)), "cycles BAM modifiés")
    return derived


def derive_bottom_padded_bam(source_path: Path, resource: dict[str, Any],
                             padding_x1: int) -> bytes:
    source = read_bam(source_path)
    source_frames, _palette, transparent = decode_bam(source)
    runtime_frames = sorted_frames(resource)
    native_indices = sorted({int(index) for cycle in resource.get("cycles") or []
                             for index in cycle.get("native_frame_indices") or []})
    require(len(source_frames) == len(native_indices),
            "frames natives BAM/runtime divergentes")
    for source_frame, runtime_index in zip(source_frames, native_indices, strict=True):
        indices, centre_x, centre_y, _transparent = source_frame
        frame = runtime_frames[runtime_index]
        require([indices.shape[1], indices.shape[0]] == frame["logical_size_x1"] and
                [centre_x, centre_y] == frame["centre_x1"],
                f"frame native {runtime_index}: géométrie BAM/runtime divergente")
    derived = pad_bam_bottom(source, padding_x1)
    derived_frames, _derived_palette, derived_transparent = decode_bam(derived)
    require(derived_transparent == transparent and len(derived_frames) == len(source_frames),
            "BAM dérivé invalide")
    for source_frame, derived_frame in zip(source_frames, derived_frames, strict=True):
        source_indices, source_cx, source_cy, _ = source_frame
        derived_indices, derived_cx, derived_cy, _ = derived_frame
        height = source_indices.shape[0]
        require(derived_indices.shape == (height + padding_x1, source_indices.shape[1]) and
                np.array_equal(derived_indices[:height], source_indices) and
                bool((derived_indices[height:] == transparent).all()) and
                (derived_cx, derived_cy) == (source_cx, source_cy),
                "pixels, padding ou centres du BAM dérivé divergents")
    require(cycle_metadata(source, len(source_frames)) ==
            cycle_metadata(derived, len(derived_frames)), "cycles BAM modifiés")
    return derived


def repair_frame(top_pixels: np.ndarray, bottom_pixels: np.ndarray, *,
                 top_layout: FrameLayout, bottom_layout: FrameLayout,
                 seam_depth_x4: int, alpha_threshold: int,
                 blend_mode: str) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Blend matching world rows without changing the supplied alpha."""
    require(blend_mode in BLEND_MODES, f"mode de raccord RGB inconnu : {blend_mode}")
    output_top = top_pixels.copy()
    output_bottom = bottom_pixels.copy()
    overlap_left = max(top_layout.origin_x, bottom_layout.origin_x)
    overlap_right = min(top_layout.origin_x + top_layout.width,
                        bottom_layout.origin_x + bottom_layout.width)
    top_x0 = overlap_left - top_layout.origin_x
    top_x1 = overlap_right - top_layout.origin_x
    bottom_x0 = overlap_left - bottom_layout.origin_x
    bottom_x1 = overlap_right - bottom_layout.origin_x

    before_differences: list[np.ndarray] = []
    after_differences: list[np.ndarray] = []
    changed_pixels = 0
    paired_pixels = 0
    for distance in range(seam_depth_x4):
        top_y = top_layout.height - 1 - distance
        bottom_y = distance
        top_row = top_pixels[top_y, top_x0:top_x1]
        bottom_row = bottom_pixels[bottom_y, bottom_x0:bottom_x1]
        support = ((top_row[:, 3] >= alpha_threshold) &
                   (bottom_row[:, 3] >= alpha_threshold))
        if not support.any():
            continue
        top_rgb = top_row[:, :3].astype(np.float32)
        bottom_rgb = bottom_row[:, :3].astype(np.float32)
        weight = 1.0 if seam_depth_x4 == 1 else 1.0 - smoothstep(
            distance / float(seam_depth_x4 - 1)
        )
        if blend_mode == "symmetric-midpoint":
            midpoint = np.rint((top_rgb + bottom_rgb) / 2.0)
            updated_top = np.rint(top_rgb * (1.0 - weight) + midpoint * weight).astype(np.uint8)
            updated_bottom = np.rint(bottom_rgb * (1.0 - weight) + midpoint * weight).astype(np.uint8)
        else:
            updated_top = top_rgb.astype(np.uint8)
            updated_bottom = np.rint(
                bottom_rgb * (1.0 - weight) + top_rgb * weight
            ).astype(np.uint8)
        output_top[top_y, top_x0:top_x1, :3][support] = updated_top[support]
        output_bottom[bottom_y, bottom_x0:bottom_x1, :3][support] = updated_bottom[support]
        before_differences.append(np.abs(top_rgb[support] - bottom_rgb[support]))
        after_differences.append(np.abs(updated_top[support].astype(np.float32) -
                                        updated_bottom[support].astype(np.float32)))
        changed_pixels += int(np.any(updated_top != top_rgb, axis=1)[support].sum())
        changed_pixels += int(np.any(updated_bottom != bottom_rgb, axis=1)[support].sum())
        paired_pixels += int(support.sum())

    require(np.array_equal(output_top[:, :, 3], top_pixels[:, :, 3]) and
            np.array_equal(output_bottom[:, :, 3], bottom_pixels[:, :, 3]),
            "invariant rompu : le raccord RGB a modifié l'alpha")
    require(before_differences and after_differences,
            "aucun pixel alpha commun dans la bande de raccord")
    before = np.concatenate(before_differences, axis=0)
    after = np.concatenate(after_differences, axis=0)
    return output_top, output_bottom, {
        "shared_world_rect_x4": [overlap_left, top_layout.origin_y + top_layout.height,
                                  overlap_right, bottom_layout.origin_y],
        "seam_depth_x4": seam_depth_x4,
        "alpha_threshold": alpha_threshold,
        "blend_mode": blend_mode,
        "paired_opaque_pixels": paired_pixels,
        "changed_rgb_pixels": changed_pixels,
        "rgb_mae_before": round(float(before.mean()), 6),
        "rgb_mae_after": round(float(after.mean()), 6),
        "rgb_p95_before": round(float(np.percentile(before, 95)), 6),
        "rgb_p95_after": round(float(np.percentile(after, 95)), 6),
    }


def atomic_bytes(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_bytes(payload)
    temporary.replace(path)


def update_resource(resource: dict[str, Any], frames: list[dict[str, Any]],
                    pixels: list[np.ndarray], top_padding_x1: int = 0,
                    bottom_padding_x1: int = 0) -> dict[str, Any]:
    updated = copy.deepcopy(resource)
    updated_frames = sorted(updated["frames"], key=lambda item: int(item["frame"]))
    assets = {str(item["name"]): item for item in updated["assets"]}
    for source_frame, pixels_for_frame in zip(updated_frames, pixels, strict=True):
        name = str(source_frame["asset"])
        payload = pixels_for_frame.tobytes(order="C")
        source_frame["sha256"] = hashlib.sha256(payload).hexdigest()
        source_frame["bytes"] = len(payload)
        assets[name]["sha256"] = source_frame["sha256"]
        assets[name]["bytes"] = source_frame["bytes"]
        if top_padding_x1 or bottom_padding_x1:
            logical = [int(value) for value in source_frame["logical_size_x1"]]
            physical = [int(value) for value in source_frame["physical_size_x4"]]
            centre = [int(value) for value in source_frame["centre_x1"]]
            total_padding_x1 = top_padding_x1 + bottom_padding_x1
            source_frame["logical_size_x1"] = [logical[0], logical[1] + total_padding_x1]
            source_frame["physical_size_x4"] = [physical[0], physical[1] + total_padding_x1 * 4]
            source_frame["centre_x1"] = [centre[0], centre[1] + top_padding_x1]
    updated["frames"] = updated_frames
    updated["assets"] = [assets[str(frame["asset"])] for frame in updated_frames]
    return updated


def write_runtime_pack(destination: Path, source: PackInput, frames: list[dict[str, Any]],
                       pixels: list[np.ndarray], provenance: dict[str, Any],
                       top_padding_x1: int = 0,
                       bottom_padding_x1: int = 0) -> dict[str, Any]:
    resource = update_resource(source.resource, frames, pixels, top_padding_x1,
                               bottom_padding_x1)
    registry_version = int(source.manifest["registry_version"])
    registry = runtime.registry_v2_from_resources([resource], registry_version)
    destination.mkdir(parents=True)
    registry_path = destination / runtime.REGISTRY_NAME
    atomic_bytes(registry_path, registry)
    for frame, pixels_for_frame in zip(sorted_frames(resource), pixels, strict=True):
        atomic_bytes(destination / str(frame["asset"]), pixels_for_frame.tobytes(order="C"))
    manifest = copy.deepcopy(source.manifest)
    manifest.update({
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "registry": runtime.REGISTRY_NAME,
        "registry_sha256": runtime.sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": 1,
        "frame_count": int(resource["frame_count"]),
        "timed_resources": [runtime.normalise_resref(str(resource["resref"]))],
        "raw_bytes": sum(int(asset["bytes"]) for asset in resource["assets"]),
        "runtime_budget_enforced": True,
        "resources": [resource],
        "joint_rgb_seam_repair": provenance,
        "geometry_override": ({
            "resref": runtime.normalise_resref(str(resource["resref"])),
            "operation": "overlap-padding",
            "top_padding_x1": top_padding_x1,
            "top_padding_x4": top_padding_x1 * 4,
            "bottom_padding_x1": bottom_padding_x1,
            "bottom_padding_x4": bottom_padding_x1 * 4,
            "centre_y_delta_x1": top_padding_x1,
            "derived_bam_required": True,
        } if top_padding_x1 or bottom_padding_x1 else None),
    })
    runtime.write_json(destination / "manifest.json", manifest)
    runtime.validate_v2_pack(destination)
    return manifest


def compose_preview(top: np.ndarray, bottom: np.ndarray, *, top_layout: FrameLayout,
                    bottom_layout: FrameLayout, seam_depth_x4: int) -> Image.Image:
    left = min(top_layout.origin_x, bottom_layout.origin_x)
    right = max(top_layout.origin_x + top_layout.width, bottom_layout.origin_x + bottom_layout.width)
    start_y = max(top_layout.origin_y, top_layout.origin_y + top_layout.height - seam_depth_x4 * 3)
    end_y = min(bottom_layout.origin_y + bottom_layout.height,
                bottom_layout.origin_y + seam_depth_x4 * 3)
    image = Image.new("RGBA", (right - left, end_y - start_y), (0, 0, 0, 0))
    image.alpha_composite(Image.fromarray(top, "RGBA"),
                          (top_layout.origin_x - left, top_layout.origin_y - start_y))
    image.alpha_composite(Image.fromarray(bottom, "RGBA"),
                          (bottom_layout.origin_x - left, bottom_layout.origin_y - start_y))
    return image


def write_review(path: Path, before: list[Image.Image], after: list[Image.Image]) -> None:
    require(len(before) == len(after) and before, "prévisualisation B/C absente")
    width = max(image.width for image in before + after)
    height = max(image.height for image in before + after)
    scale = min(1.0, 420.0 / float(width))
    preview_size = (max(1, round(width * scale)), max(1, round(height * scale)))
    columns = 2
    label_height, gap = 20, 12
    rows = (len(before) + columns - 1) // columns
    canvas = Image.new("RGB", (columns * (preview_size[0] * 2 + gap) + (columns + 1) * gap,
                                rows * (preview_size[1] + label_height + gap) + gap),
                       (35, 35, 35))
    draw = ImageDraw.Draw(canvas)
    for index, (left, right) in enumerate(zip(before, after, strict=True)):
        column, row = index % columns, index // columns
        x = gap + column * (preview_size[0] * 2 + gap * 2)
        y = gap + row * (preview_size[1] + label_height + gap)
        draw.text((x, y), f"phase {index:02d}  avant / après", fill=(235, 235, 235))
        left_rgb = Image.new("RGB", left.size, (70, 70, 70))
        left_rgb.paste(left, mask=left.getchannel("A"))
        right_rgb = Image.new("RGB", right.size, (70, 70, 70))
        right_rgb.paste(right, mask=right.getchannel("A"))
        canvas.paste(left_rgb.resize(preview_size, Image.Resampling.LANCZOS), (x, y + label_height))
        canvas.paste(right_rgb.resize(preview_size, Image.Resampling.LANCZOS),
                     (x + preview_size[0] + gap, y + label_height))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    canvas.save(temporary, format="PNG", optimize=True)
    temporary.replace(path)


def inspect(top: PackInput, bottom: PackInput, seam_depth_x4: int,
            alpha_threshold: int, blend_mode: str,
            bottom_alpha_reference: PackInput | None,
            restore_removed_component_min_pixels: int,
            bottom_top_overlap_x1: int, bottom_source_bam: Path | None,
            bilateral_extension_x1: int, top_source_bam: Path | None,
            area: str | None) -> dict[str, Any]:
    top_frames, bottom_frames = validate_pair(top, bottom, seam_depth_x4)
    require(blend_mode in BLEND_MODES, f"mode de raccord RGB inconnu : {blend_mode}")
    if bottom_alpha_reference is not None:
        validate_alpha_reference(bottom, bottom_alpha_reference)
        require(restore_removed_component_min_pixels > 0,
                "seuil de restauration alpha positif requis avec une référence")
    else:
        require(restore_removed_component_min_pixels == 0,
                "une référence alpha inférieure est requise pour restaurer des composantes")
    unilateral_requested = bottom_top_overlap_x1 > 0
    bilateral_requested = bilateral_extension_x1 > 0
    require(bottom_top_overlap_x1 >= 0 and bilateral_extension_x1 >= 0,
            "recouvrement négatif")
    require(not (unilateral_requested and bilateral_requested),
            "les recouvrements unilatéral et bilatéral sont exclusifs")
    require((unilateral_requested or bilateral_requested) == (bottom_source_bam is not None),
            "le recouvrement et le BAM source inférieur doivent être fournis ensemble")
    require(bilateral_requested == (top_source_bam is not None),
            "l'extension bilatérale et le BAM source supérieur doivent être fournis ensemble")
    if unilateral_requested or bilateral_requested:
        require(bool(area) and area == str(area).upper(), "zone uppercase requise pour l'override BAM")
        require(bottom_source_bam is not None and bottom_source_bam.is_file(),
                "BAM source inférieur absent")
        bottom_padding = bilateral_extension_x1 or bottom_top_overlap_x1
        derive_top_padded_bam(bottom_source_bam, bottom.resource, bottom_padding)
    if bilateral_requested:
        require(top_source_bam is not None and top_source_bam.is_file(),
                "BAM source supérieur absent")
        derive_bottom_padded_bam(top_source_bam, top.resource, bilateral_extension_x1)
    inputs = [
        {"role": "top", "pack": top.root.as_posix(),
         "pack_manifest_sha256": runtime.sha256_file(top.root / "manifest.json"),
         "position_x1": list(top.position_x1)},
        {"role": "bottom", "pack": bottom.root.as_posix(),
         "pack_manifest_sha256": runtime.sha256_file(bottom.root / "manifest.json"),
         "position_x1": list(bottom.position_x1)},
    ]
    if bottom_alpha_reference is not None:
        inputs.append({
            "role": "bottom-alpha-reference",
            "pack": bottom_alpha_reference.root.as_posix(),
            "pack_manifest_sha256": runtime.sha256_file(
                bottom_alpha_reference.root / "manifest.json"
            ),
            "position_x1": list(bottom_alpha_reference.position_x1),
        })
    if bottom_source_bam is not None:
        inputs.append({
            "role": "bottom-source-bam",
            "file": bottom_source_bam.as_posix(),
            "sha256": runtime.sha256_file(bottom_source_bam),
        })
    if top_source_bam is not None:
        inputs.append({
            "role": "top-source-bam",
            "file": top_source_bam.as_posix(),
            "sha256": runtime.sha256_file(top_source_bam),
        })
    return {
        "schema": SCHEMA,
        "status": "planned",
        "asset_ids": [
            f"animations:bam:{runtime.normalise_resref(str(top.resource['resref']))}",
            f"animations:bam:{runtime.normalise_resref(str(bottom.resource['resref']))}",
        ],
        "inputs": inputs,
        "parameters": {
            "seam_depth_x4": seam_depth_x4,
            "alpha_threshold": alpha_threshold,
            "blend_mode": blend_mode,
            "alpha_policy": ("bottom-restore-large-removed-components-from-reference"
                             if bottom_alpha_reference is not None else "byte-identical"),
            "restore_removed_component_min_pixels": restore_removed_component_min_pixels,
            "rgb_policy": "smoothstep-on-mutually-opaque-world-aligned-band",
            "bottom_top_overlap_x1": bottom_top_overlap_x1,
            "bottom_top_overlap_x4": bottom_top_overlap_x1 * 4,
            "bilateral_extension_each_x1": bilateral_extension_x1,
            "bilateral_extension_each_x4": bilateral_extension_x1 * 4,
            "bilateral_total_overlap_x1": bilateral_extension_x1 * 2,
            "bilateral_total_overlap_x4": bilateral_extension_x1 * 8,
            "overlap_policy": (
                "source-over-opacity-and-colour-preserving-smoothstep"
                if bilateral_requested else
                "bottom-fade-in-over-unchanged-top" if unilateral_requested else None
            ),
            "area": area,
        },
        "frame_count": len(top_frames),
        "timeline": copy.deepcopy(top.resource["cycles"]),
    }


def build(top: PackInput, bottom: PackInput, output: Path, *, seam_depth_x4: int,
          alpha_threshold: int, write: bool, resume: bool,
          blend_mode: str = "symmetric-midpoint",
          bottom_alpha_reference: PackInput | None = None,
          restore_removed_component_min_pixels: int = 0,
          bottom_top_overlap_x1: int = 0,
          bottom_source_bam: Path | None = None,
          bilateral_extension_x1: int = 0,
          top_source_bam: Path | None = None,
          area: str | None = None) -> dict[str, Any]:
    require(0 <= alpha_threshold <= 255, "seuil alpha hors plage")
    if bottom_source_bam is not None:
        bottom_source_bam = bottom_source_bam.resolve()
    if top_source_bam is not None:
        top_source_bam = top_source_bam.resolve()
    plan = inspect(top, bottom, seam_depth_x4, alpha_threshold, blend_mode,
                   bottom_alpha_reference, restore_removed_component_min_pixels,
                   bottom_top_overlap_x1, bottom_source_bam,
                   bilateral_extension_x1, top_source_bam, area)
    output = output.resolve()
    plan["output"] = output.as_posix()
    if not write:
        return plan
    if output.exists():
        require(resume, f"sortie déjà présente : {output}")
        existing = runtime.load_json(output / "manifest.json")
        require(existing.get("schema") == SCHEMA and existing.get("status") == "completed" and
                existing.get("inputs") == plan["inputs"] and existing.get("parameters") == plan["parameters"],
                "sortie existante issue d'autres entrées ou paramètres")
        for resource in existing.get("outputs") or []:
            runtime.validate_v2_pack(output / str(resource["runtime_pack"]))
        return existing
    partial = output.with_name(output.name + ".partial")
    require(not partial.exists(), f"sortie partielle présente : {partial}")

    top_frames, bottom_frames = validate_pair(top, bottom, seam_depth_x4)
    reference_frames = (validate_alpha_reference(bottom, bottom_alpha_reference)
                        if bottom_alpha_reference is not None else None)
    output_top: list[np.ndarray] = []
    output_bottom: list[np.ndarray] = []
    reports: list[dict[str, Any]] = []
    previews_before: list[Image.Image] = []
    previews_after: list[Image.Image] = []
    for index, (top_frame, bottom_frame) in enumerate(zip(top_frames, bottom_frames, strict=True)):
        top_layout = frame_layout(top_frame, top.position_x1)
        bottom_layout = frame_layout(bottom_frame, bottom.position_x1)
        top_pixels = read_rgba(top.root / str(top_frame["asset"]), top_layout)
        bottom_pixels = read_rgba(bottom.root / str(bottom_frame["asset"]), bottom_layout)
        alpha_restore_report = None
        seam_bottom_pixels = bottom_pixels
        if bottom_alpha_reference is not None and reference_frames is not None:
            reference_frame = reference_frames[index]
            reference_pixels = read_rgba(
                bottom_alpha_reference.root / str(reference_frame["asset"]), bottom_layout
            )
            seam_bottom_pixels, alpha_restore_report = restore_large_removed_alpha(
                bottom_pixels, reference_pixels, restore_removed_component_min_pixels
            )
        repaired_top, repaired_bottom, report = repair_frame(
            top_pixels, seam_bottom_pixels, top_layout=top_layout, bottom_layout=bottom_layout,
            seam_depth_x4=seam_depth_x4, alpha_threshold=alpha_threshold,
            blend_mode=blend_mode,
        )
        require(np.array_equal(repaired_top[:, :, 3], top_pixels[:, :, 3]) and
                np.array_equal(repaired_bottom[:, :, 3], seam_bottom_pixels[:, :, 3]),
                f"frame {index}: le raccord RGB a modifié l'alpha")
        overlap_report = None
        repaired_top_layout = top_layout
        repaired_bottom_layout = bottom_layout
        if bilateral_extension_x1:
            (repaired_top, repaired_bottom, repaired_top_layout,
             repaired_bottom_layout, overlap_report) = add_bilateral_overlap(
                repaired_top, repaired_bottom,
                top_layout=top_layout, bottom_layout=bottom_layout,
                extension_x4=bilateral_extension_x1 * 4,
            )
        elif bottom_top_overlap_x1:
            repaired_bottom, repaired_bottom_layout, overlap_report = add_top_overlap(
                repaired_top, repaired_bottom,
                top_layout=top_layout, bottom_layout=bottom_layout,
                overlap_x4=bottom_top_overlap_x1 * 4,
            )
        output_top.append(repaired_top)
        output_bottom.append(repaired_bottom)
        reports.append({"frame": index, "alpha_restore": alpha_restore_report,
                        "top_overlap": overlap_report, **report})
        previews_before.append(compose_preview(
            top_pixels, bottom_pixels, top_layout=top_layout, bottom_layout=bottom_layout,
            seam_depth_x4=seam_depth_x4,
        ))
        previews_after.append(compose_preview(
            repaired_top, repaired_bottom, top_layout=repaired_top_layout,
            bottom_layout=repaired_bottom_layout,
            seam_depth_x4=seam_depth_x4,
        ))

    partial.mkdir(parents=True)
    repair_provenance = {
        "parameters": plan["parameters"],
        "top_position_x1": list(top.position_x1),
        "bottom_position_x1": list(bottom.position_x1),
        "frame_reports": reports,
    }
    top_pack = Path(runtime.normalise_resref(str(top.resource["resref"]))) / "03_runtime_pack"
    bottom_pack = Path(runtime.normalise_resref(str(bottom.resource["resref"]))) / "03_runtime_pack"
    top_manifest = write_runtime_pack(
        partial / top_pack, top, top_frames, output_top, repair_provenance,
        bottom_padding_x1=bilateral_extension_x1,
    )
    bottom_manifest = write_runtime_pack(
        partial / bottom_pack, bottom, bottom_frames, output_bottom, repair_provenance,
        top_padding_x1=bilateral_extension_x1 or bottom_top_overlap_x1,
    )
    override_assets = None
    if bottom_top_overlap_x1 or bilateral_extension_x1:
        require(bottom_source_bam is not None and area is not None,
                "provenance BAM/zone absente pour le recouvrement")
        top_resref = runtime.normalise_resref(str(top.resource["resref"]))
        bottom_resref = runtime.normalise_resref(str(bottom.resource["resref"]))
        bottom_padding = bilateral_extension_x1 or bottom_top_overlap_x1
        derived_bam = derive_top_padded_bam(
            bottom_source_bam, bottom.resource, bottom_padding
        )
        override_root = partial / "override-assets"
        override_root.mkdir()
        bam_name = f"{bottom_resref}.BAM"
        bam_path = override_root / bam_name
        atomic_bytes(bam_path, derived_bam)
        override_files = {
            bam_name: {
                "bytes": bam_path.stat().st_size,
                "sha256": runtime.sha256_file(bam_path),
            },
        }
        geometry_operations = [{
            "resref": bottom_resref,
            "operation": "top-transparent-padding-for-runtime-overlap",
            "top_padding_x1": bottom_padding,
            "centre_y_delta_x1": bottom_padding,
            "pixels_existing": "byte-identical",
            "cycles": "byte-identical",
        }]
        source_bams = [{
            "resref": bottom_resref,
            "file": bottom_source_bam.as_posix(),
            "sha256": runtime.sha256_file(bottom_source_bam),
        }]
        if bilateral_extension_x1:
            require(top_source_bam is not None, "BAM source supérieur absent")
            top_bam = derive_bottom_padded_bam(
                top_source_bam, top.resource, bilateral_extension_x1
            )
            top_bam_name = f"{top_resref}.BAM"
            top_bam_path = override_root / top_bam_name
            atomic_bytes(top_bam_path, top_bam)
            override_files[top_bam_name] = {
                "bytes": top_bam_path.stat().st_size,
                "sha256": runtime.sha256_file(top_bam_path),
            }
            geometry_operations.append({
                "resref": top_resref,
                "operation": "bottom-transparent-padding-for-runtime-overlap",
                "bottom_padding_x1": bilateral_extension_x1,
                "centre_y_delta_x1": 0,
                "pixels_existing": "byte-identical",
                "cycles": "byte-identical",
            })
            source_bams.append({
                "resref": top_resref,
                "file": top_source_bam.as_posix(),
                "sha256": runtime.sha256_file(top_source_bam),
            })
        override_manifest = {
            "schema": "bg2-upscale-area-animation-override-assets-v1",
            "status": "completed",
            "created_utc": runtime.utc_now(),
            "area": area,
            "files": override_files,
            "source_bams": source_bams,
            "geometry_operations": geometry_operations,
        }
        runtime.write_json(override_root / "manifest.json", override_manifest)
        override_assets = {
            "directory": "override-assets",
            "manifest_sha256": runtime.sha256_file(override_root / "manifest.json"),
            "bams": [{"file": f"override-assets/{name}", "sha256": values["sha256"]}
                     for name, values in sorted(override_files.items())],
        }
    review_path = partial / "review" / "joint-rgb-seam-contact-sheet.png"
    write_review(review_path, previews_before, previews_after)
    plan.update({
        "status": "completed",
        "created_utc": runtime.utc_now(),
        "frame_reports": reports,
        "outputs": [
            {"resref": top.resource["resref"], "runtime_pack": top_pack.as_posix(),
             "runtime_pack_manifest_sha256": runtime.sha256_file(partial / top_pack / "manifest.json"),
             "registry_sha256": top_manifest["registry_sha256"]},
            {"resref": bottom.resource["resref"], "runtime_pack": bottom_pack.as_posix(),
             "runtime_pack_manifest_sha256": runtime.sha256_file(partial / bottom_pack / "manifest.json"),
             "registry_sha256": bottom_manifest["registry_sha256"]},
        ],
        "override_assets": override_assets,
        "review": {"file": "review/joint-rgb-seam-contact-sheet.png",
                   "sha256": runtime.sha256_file(review_path)},
        "qa_status": "pending-explicit-user-approval",
    })
    runtime.write_json(partial / "manifest.json", plan)
    partial.replace(output)
    return plan


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--top-pack", type=Path, required=True,
                        help="pack de la cascade supérieure")
    parser.add_argument("--bottom-pack", type=Path, required=True,
                        help="pack de la cascade inférieure")
    parser.add_argument("--bottom-alpha-reference-pack", type=Path,
                        help="pack de référence pour restaurer les grosses pertes alpha inférieures")
    parser.add_argument("--top-position", required=True, help="position ARE X,Y de la cascade supérieure")
    parser.add_argument("--bottom-position", required=True, help="position ARE X,Y de la cascade inférieure")
    parser.add_argument("--output", type=Path, required=True,
                        help="nouveau batch multi-ressources")
    parser.add_argument("--seam-depth-x4", type=int, default=16,
                        help="profondeur RGB de chaque côté du raccord (défaut : 16)")
    parser.add_argument("--alpha-threshold", type=int, default=128,
                        help="seuil d'opacité partagé pour autoriser la retouche RGB")
    parser.add_argument("--blend-mode", choices=BLEND_MODES, default="symmetric-midpoint",
                        help="politique de raccord RGB")
    parser.add_argument("--restore-removed-component-min-pixels", type=int, default=0,
                        help="restaurer depuis la référence les composantes alpha supprimées de cette taille")
    parser.add_argument("--bottom-top-overlap-x1", type=int, default=0,
                        help="extension haute x1 de la ressource basse avec fade alpha")
    parser.add_argument("--bottom-source-bam", type=Path,
                        help="BAM natif à dériver pour la géométrie du recouvrement")
    parser.add_argument("--bilateral-extension-x1", type=int, default=0,
                        help="extension de chaque BAM x1 ; recouvrement total double")
    parser.add_argument("--top-source-bam", type=Path,
                        help="BAM natif supérieur requis par le recouvrement bilatéral")
    parser.add_argument("--area", help="zone cible de l'override BAM, ex. AR2804")
    parser.add_argument("--run", action="store_true", help="écrire le batch ; sinon plan seul")
    parser.add_argument("--resume", action="store_true", help="revalider un batch identique existant")
    args = parser.parse_args(argv)
    top = load_single_resource_pack(args.top_pack, parse_position(args.top_position))
    bottom = load_single_resource_pack(args.bottom_pack, parse_position(args.bottom_position))
    bottom_alpha_reference = (
        load_single_resource_pack(args.bottom_alpha_reference_pack,
                                  parse_position(args.bottom_position))
        if args.bottom_alpha_reference_pack else None
    )
    report = build(top, bottom, args.output, seam_depth_x4=args.seam_depth_x4,
                   alpha_threshold=args.alpha_threshold, write=args.run, resume=args.resume,
                   blend_mode=args.blend_mode,
                   bottom_alpha_reference=bottom_alpha_reference,
                   restore_removed_component_min_pixels=
                   args.restore_removed_component_min_pixels,
                   bottom_top_overlap_x1=args.bottom_top_overlap_x1,
                   bottom_source_bam=args.bottom_source_bam,
                   bilateral_extension_x1=args.bilateral_extension_x1,
                   top_source_bam=args.top_source_bam,
                   area=args.area)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
