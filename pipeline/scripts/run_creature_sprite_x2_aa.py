#!/usr/bin/env python3
"""Isolated xBR2X Antialias experiment for palette-driven creature sprites.

This runner deliberately does not change the V2/V3 production contracts. It
reads an already verified source manifest, writes a separate V4 monolithic
registry containing palette indices plus ordered xBR blend recipes, and uses a
dedicated transactional installer.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tempfile
from typing import Any

import numpy as np

import run_creature_sprite_x2 as base


JOB_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-aa-job-v1"
BUILD_SCHEMA = "bg2-upscale-creature-sprite-xbr2x-aa-pack-v1"
REGISTRY_MAGIC = b"IEECSXN\0"
REGISTRY_VERSION = 4
REGISTRY_FILENAME = "CreatureSprites-XN.registry"
FRAME_HEADER_BYTES = 528
MAX_RECIPE_OPERATIONS = 8
AA_ADAPTER = Path(__file__).with_name("xbr2x_antialias_batch.js")
INSTALL_SCRIPT = Path(__file__).with_name("Install-CreatureSprite-AA-Variant-Test.ps1")
RESTORE_SCRIPT = Path(__file__).with_name("Restore-CreatureSprite-AA-Variant-Test.ps1")

# Codes are source contributions in Scalepix's alphaBlend* helpers.
BLEND_WEIGHTS: tuple[tuple[int, int], ...] = (
    (7, 1),  # 1/8
    (3, 1),  # 1/4
    (1, 1),  # 1/2
    (1, 3),  # 3/4
    (1, 7),  # 7/8
)
BLEND_64 = 1
BLEND_128 = 2
BLEND_192 = 3


@dataclass(frozen=True)
class RecipePixel:
    base_index: int
    operations: tuple[tuple[int, int], ...] = ()

    def blend(self, source_index: int, code: int) -> "RecipePixel":
        operations = self.operations + ((int(source_index), int(code)),)
        if len(operations) > MAX_RECIPE_OPERATIONS:
            raise RuntimeError("xBR2X Antialias recipe exceeds its operation bound")
        return RecipePixel(self.base_index, operations)


def load_job(path: Path) -> dict[str, Any]:
    path = path.resolve()
    job = base.read_json(path)
    if job.get("schema") != JOB_SCHEMA:
        raise RuntimeError(f"unsupported AA job schema: {job.get('schema')!r}")
    job_id = str(job.get("job_id", ""))
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,63}", job_id):
        raise RuntimeError("AA job_id is invalid")
    animation = job.get("animation")
    paths = job.get("paths")
    compatibility = job.get("compatibility")
    if not isinstance(animation, dict) or not isinstance(paths, dict) or not isinstance(
        compatibility, dict
    ):
        raise RuntimeError("AA job requires animation, paths, and compatibility")
    if animation.get("id") != "0x6102" or animation.get("bam_prefix") != "CDMB1":
        raise RuntimeError("the initial AA experiment is restricted to CDMB1 / 0x6102")
    if animation.get("runtime_profile") != "character-bg2ee-2.7.3.0":
        raise RuntimeError("AA job requires the verified Character runtime profile")
    if animation.get("armor_code") != 1:
        raise RuntimeError("AA job requires Character armor code 1")
    required_paths = (
        "game_root",
        "source_manifest",
        "run_dir",
        "scalepix",
        "engine_source",
        "engine_build",
    )
    missing = [key for key in required_paths if not paths.get(key)]
    if missing:
        raise RuntimeError("AA job paths missing: " + ", ".join(missing))
    for key in ("source_manifest", "run_dir", "engine_source", "engine_build"):
        resolved = base.resolve_path(paths[key])
        if key != "source_manifest":
            base.assert_workspace_child(resolved, f"paths.{key}")
    expected_exe = str(compatibility.get("baldur_real_sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_exe):
        raise RuntimeError("AA compatibility hash is invalid")
    method = job.get("upscale")
    if method != {
        "algorithm": "XBR/xbr2X",
        "scale": 2,
        "passes": 1,
        "antialias": True,
        "xbr_blend": True,
    }:
        raise RuntimeError("AA job must use exact xBR2X Antialias settings")
    expected_source_hash = str(job.get("source_manifest_sha256", "")).upper()
    if not re.fullmatch(r"[0-9A-F]{64}", expected_source_hash):
        raise RuntimeError("AA job requires source_manifest_sha256")
    source_manifest = base.resolve_path(paths["source_manifest"])
    if not source_manifest.is_file() or base.sha256_file(source_manifest) != expected_source_hash:
        raise RuntimeError("AA source manifest is missing or differs from the pinned baseline")
    job["_job_file"] = str(path)
    return job


def job_path(job: dict[str, Any], key: str) -> Path:
    return base.resolve_path(job["paths"][key])


def run_dir(job: dict[str, Any]) -> Path:
    return job_path(job, "run_dir")


def build_dir(job: dict[str, Any]) -> Path:
    return run_dir(job) / "build"


def runtime_dir(job: dict[str, Any]) -> Path:
    return run_dir(job) / "runtime"


def active_state_path(job: dict[str, Any]) -> Path:
    return run_dir(job) / "ingame-test" / "active-test.json"


def run_xbr_aa(
    frames: list[base.SourceFrame], scalepix: Path, node: str
) -> list[tuple[int, int, bytes]]:
    if not frames or not scalepix.is_file() or not AA_ADAPTER.is_file():
        raise RuntimeError("Scalepix, AA adapter, or frame batch is missing")
    payload = bytearray(b"XBRA2BT\0")
    payload.extend(struct.pack("<I", len(frames)))
    for frame in frames:
        payload.extend(struct.pack("<III", frame.width, frame.height, len(frame.rgba)))
        payload.extend(frame.rgba)
    result = subprocess.run(
        [node, str(AA_ADAPTER), str(scalepix)],
        input=bytes(payload),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "xBR2X Antialias batch failed:\n"
            + result.stderr.decode("utf-8", errors="replace")
        )
    raw = result.stdout
    if len(raw) < 12 or raw[:8] != b"XBRA2OT\0":
        raise RuntimeError("invalid xBR2X Antialias batch output")
    count = struct.unpack_from("<I", raw, 8)[0]
    if count != len(frames):
        raise RuntimeError("xBR2X Antialias output count differs from input")
    outputs: list[tuple[int, int, bytes]] = []
    offset = 12
    for frame_index in range(count):
        if offset + 12 > len(raw):
            raise RuntimeError("truncated xBR2X Antialias output")
        width, height, byte_count = struct.unpack_from("<III", raw, offset)
        offset += 12
        if byte_count != width * height * 4 or offset + byte_count > len(raw):
            raise RuntimeError(f"invalid AA output frame {frame_index}")
        outputs.append((width, height, raw[offset : offset + byte_count]))
        offset += byte_count
    if offset != len(raw):
        raise RuntimeError("trailing xBR2X Antialias output bytes")
    return outputs


def _yuv(value: int) -> tuple[float, float, float]:
    red, green, blue = value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF
    return (
        red * 0.299 + green * 0.587 + blue * 0.114,
        red * -0.168736 + green * -0.331264 + blue * 0.5,
        red * 0.5 + green * -0.418688 + blue * -0.081312,
    )


def _difference(left: int, right: int) -> float:
    alpha_left = (left >> 24) & 0xFF
    alpha_right = (right >> 24) & 0xFF
    if alpha_left == 0 and alpha_right == 0:
        return 0.0
    if alpha_left == 0 or alpha_right == 0:
        return 1_000_000.0
    y_left, u_left, v_left = _yuv(left)
    y_right, u_right, v_right = _yuv(right)
    return (
        abs(y_left - y_right) * 48
        + abs(u_left - u_right) * 7
        + abs(v_left - v_right) * 6
    )


def _equal(left: int, right: int) -> bool:
    alpha_left = (left >> 24) & 0xFF
    alpha_right = (right >> 24) & 0xFF
    if alpha_left == 0 and alpha_right == 0:
        return True
    if alpha_left == 0 or alpha_right == 0:
        return False
    y_left, u_left, v_left = _yuv(left)
    y_right, u_right, v_right = _yuv(right)
    return (
        abs(y_left - y_right) <= 48
        and abs(u_left - u_right) <= 7
        and abs(v_left - v_right) <= 6
    )


def _kernel_2x(
    colors: list[int],
    labels: list[int],
    n1: RecipePixel,
    n2: RecipePixel,
    n3: RecipePixel,
) -> tuple[RecipePixel, RecipePixel, RecipePixel]:
    pe, pi, ph, pf, pg, pc, pd, pb, f4, i4, h5, i5 = colors
    ph_label, pf_label = labels[2], labels[3]
    if pe == ph or pe == pf:
        return n1, n2, n3
    edge = (
        _difference(pe, pc)
        + _difference(pe, pg)
        + _difference(pi, h5)
        + _difference(pi, f4)
        + (int(_difference(ph, pf)) << 2)
    )
    inverse = (
        _difference(ph, pd)
        + _difference(ph, i5)
        + _difference(pf, i4)
        + _difference(pf, pb)
        + (int(_difference(pe, pi)) << 2)
    )
    pixel_label = pf_label if _difference(pe, pf) <= _difference(pe, ph) else ph_label
    if edge < inverse and (
        (not _equal(pf, pb) and not _equal(ph, pd))
        or (_equal(pe, pi) and (not _equal(pf, i4) and not _equal(ph, i5)))
        or _equal(pe, pg)
        or _equal(pe, pc)
    ):
        edge_left = _difference(pf, pg)
        edge_up = _difference(ph, pc)
        distinct_up = pe != pc and pb != pc
        distinct_left = pe != pg and pd != pg
        left = (int(edge_left) << 1) <= edge_up and distinct_left
        up = edge_left >= (int(edge_up) << 1) and distinct_up
        if left or up:
            if left:
                n3 = n3.blend(pixel_label, BLEND_192)
                n2 = n2.blend(pixel_label, BLEND_64)
            if up:
                n3 = n3.blend(pixel_label, BLEND_192)
                n1 = n1.blend(pixel_label, BLEND_64)
        else:
            n3 = n3.blend(pixel_label, BLEND_128)
    elif edge <= inverse:
        n3 = n3.blend(pixel_label, BLEND_64)
    return n1, n2, n3


def frame_blend_recipes(
    frame: base.SourceFrame,
) -> tuple[np.ndarray, list[tuple[int, tuple[tuple[int, int], ...]]]]:
    colors = np.frombuffer(frame.rgba, dtype="<u4").reshape(frame.height, frame.width)
    labels = np.asarray(frame.indices, dtype=np.uint8)
    if labels.shape != (frame.height, frame.width):
        raise RuntimeError(f"{frame.resref} frame {frame.index}: invalid source indices")
    output_width = frame.width * 2
    base_indices = np.repeat(np.repeat(labels, 2, axis=0), 2, axis=1).reshape(-1)
    recipes: list[tuple[int, tuple[tuple[int, int], ...]]] = []
    rotations = (
        (10, 16, 15, 11, 14, 6, 9, 5, 12, 17, 19, 20),
        (10, 6, 11, 5, 16, 4, 15, 9, 1, 2, 12, 7),
        (10, 4, 5, 9, 6, 14, 11, 15, 8, 3, 1, 0),
        (10, 14, 9, 15, 4, 16, 5, 11, 19, 18, 8, 13),
    )

    def related(x: int, y: int) -> tuple[list[int], list[int]]:
        xm1, xm2 = max(0, x - 1), max(0, x - 2)
        xp1, xp2 = min(frame.width - 1, x + 1), min(frame.width - 1, x + 2)
        ym1, ym2 = max(0, y - 1), max(0, y - 2)
        yp1, yp2 = min(frame.height - 1, y + 1), min(frame.height - 1, y + 2)
        coordinates = (
            (xm1, ym2), (x, ym2), (xp1, ym2),
            (xm2, ym1), (xm1, ym1), (x, ym1), (xp1, ym1), (xp2, ym1),
            (xm2, y), (xm1, y), (x, y), (xp1, y), (xp2, y),
            (xm2, yp1), (xm1, yp1), (x, yp1), (xp1, yp1), (xp2, yp1),
            (xm1, yp2), (x, yp2), (xp1, yp2),
        )
        return (
            [int(colors[row, column]) for column, row in coordinates],
            [int(labels[row, column]) for column, row in coordinates],
        )

    for x in range(frame.width):
        for y in range(frame.height):
            related_colors, related_labels = related(x, y)
            center = related_labels[10]
            e0 = e1 = e2 = e3 = RecipePixel(center)
            e1, e2, e3 = _kernel_2x(
                [related_colors[index] for index in rotations[0]],
                [related_labels[index] for index in rotations[0]], e1, e2, e3,
            )
            e0, e3, e1 = _kernel_2x(
                [related_colors[index] for index in rotations[1]],
                [related_labels[index] for index in rotations[1]], e0, e3, e1,
            )
            e2, e1, e0 = _kernel_2x(
                [related_colors[index] for index in rotations[2]],
                [related_labels[index] for index in rotations[2]], e2, e1, e0,
            )
            e3, e0, e2 = _kernel_2x(
                [related_colors[index] for index in rotations[3]],
                [related_labels[index] for index in rotations[3]], e3, e0, e2,
            )
            positions = (
                y * 2 * output_width + x * 2,
                y * 2 * output_width + x * 2 + 1,
                (y * 2 + 1) * output_width + x * 2,
                (y * 2 + 1) * output_width + x * 2 + 1,
            )
            for position, value in zip(positions, (e0, e1, e2, e3), strict=True):
                if value.base_index != int(base_indices[position]):
                    raise RuntimeError("AA recipe base provenance differs from source center")
                if value.operations:
                    recipes.append((position, value.operations))
    recipes.sort(key=lambda item: item[0])
    return base_indices.astype(np.uint8, copy=False), recipes


def interpolate_pixel(destination: int, source: int, code: int) -> int:
    if not 0 <= code < len(BLEND_WEIGHTS):
        raise RuntimeError("invalid xBR blend code")
    q1, q2 = BLEND_WEIGHTS[code]
    alpha_destination = (destination >> 24) & 0xFF
    alpha_source = (source >> 24) & 0xFF
    channels: list[int] = []
    for shift in (0, 8, 16):
        dst = (destination >> shift) & 0xFF
        src = (source >> shift) & 0xFF
        if alpha_destination == 0:
            channels.append(src)
        elif alpha_source == 0:
            channels.append(dst)
        else:
            channels.append((q2 * src + q1 * dst) // (q1 + q2))
    alpha = (q2 * alpha_source + q1 * alpha_destination) // (q1 + q2)
    return channels[0] | (channels[1] << 8) | (channels[2] << 16) | (alpha << 24)


def render_recipes(
    frame: base.SourceFrame,
    base_indices: np.ndarray,
    recipes: list[tuple[int, tuple[tuple[int, int], ...]]],
) -> bytes:
    palette = np.zeros(256, dtype="<u4")
    palette |= frame.palette[:, 0].astype("<u4")
    palette |= frame.palette[:, 1].astype("<u4") << 8
    palette |= frame.palette[:, 2].astype("<u4") << 16
    alphas = np.full(256, 255, dtype="<u4")
    alphas[frame.transparent] = 0
    palette |= alphas << 24
    output = palette[base_indices].astype("<u4", copy=True)
    for pixel_index, operations in recipes:
        value = int(output[pixel_index])
        for source_index, code in operations:
            value = interpolate_pixel(value, int(palette[source_index]), code)
        output[pixel_index] = value
    return output.tobytes()


def encode_recipes(
    recipes: list[tuple[int, tuple[tuple[int, int], ...]]], pixel_count: int
) -> bytes:
    payload = bytearray(struct.pack("<I", len(recipes)))
    previous = -1
    for pixel_index, operations in recipes:
        if not previous < pixel_index < pixel_count or not 1 <= len(operations) <= MAX_RECIPE_OPERATIONS:
            raise RuntimeError("invalid ordered AA recipe")
        payload.extend(struct.pack("<IB", pixel_index, len(operations)))
        for source_index, code in operations:
            if not 0 <= source_index <= 255 or not 0 <= code < len(BLEND_WEIGHTS):
                raise RuntimeError("invalid AA recipe operation")
            payload.extend(struct.pack("<BB", source_index, code))
        previous = pixel_index
    return bytes(payload)


def frame_representatives(frame: base.SourceFrame) -> np.ndarray:
    representatives = np.full(256, 0xFFFF, dtype=np.uint16)
    for offset, raw_index in enumerate(np.asarray(frame.indices).reshape(-1).tolist()):
        if representatives[raw_index] == 0xFFFF:
            representatives[raw_index] = offset
    return representatives


def inspect_registry(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    if size <= 24 or size > base.MAX_REGISTRY_BYTES:
        raise RuntimeError("AA registry size is outside the V4 monolith bound")
    resource_count = 0
    frame_count = 0
    index_bytes_total = 0
    recipe_bytes_total = 0
    recipe_count_total = 0
    operation_count_total = 0
    seen: set[str] = set()
    with path.open("rb") as stream:
        if stream.read(8) != REGISTRY_MAGIC:
            raise RuntimeError("invalid AA registry magic")
        version, scale, declared_resources, animation_id = struct.unpack(
            "<IIII", stream.read(16)
        )
        if version != REGISTRY_VERSION or scale != 2 or animation_id != 0x6102:
            raise RuntimeError("invalid AA registry identity")
        if not 1 <= declared_resources <= base.MAX_RESOURCES:
            raise RuntimeError("invalid AA registry resource count")
        for _ in range(declared_resources):
            header = stream.read(48)
            if len(header) != 48:
                raise RuntimeError("truncated AA resource header")
            raw_resref = header[:8]
            resref = raw_resref.split(b"\0", 1)[0].decode("ascii")
            frames, cycles = struct.unpack_from("<II", header, 40)
            if not re.fullmatch(r"CDMB1[A-Z0-9]{1,3}", resref) or resref in seen:
                raise RuntimeError("invalid or duplicate AA resref")
            if not 1 <= frames <= base.MAX_FRAMES_PER_RESOURCE or not 1 <= cycles <= base.MAX_CYCLES_PER_RESOURCE:
                raise RuntimeError("invalid AA resource counts")
            seen.add(resref)
            for _ in range(frames):
                frame_header = stream.read(FRAME_HEADER_BYTES)
                if len(frame_header) != FRAME_HEADER_BYTES:
                    raise RuntimeError("truncated AA frame header")
                width, height, _, _, _, index_bytes = struct.unpack_from(
                    "<HHhhB3xI", frame_header, 0
                )
                if index_bytes != width * height * 4 or width == 0 or height == 0:
                    raise RuntimeError("invalid AA base-index payload")
                representatives = np.frombuffer(frame_header, dtype="<u2", count=256, offset=16)
                indices = np.frombuffer(stream.read(index_bytes), dtype=np.uint8)
                if indices.size != index_bytes or np.any(representatives[indices] == 0xFFFF):
                    raise RuntimeError("AA base payload lacks palette provenance")
                raw_recipe_size = stream.read(4)
                if len(raw_recipe_size) != 4:
                    raise RuntimeError("truncated AA recipe size")
                recipe_size = struct.unpack("<I", raw_recipe_size)[0]
                recipe_payload = stream.read(recipe_size)
                if len(recipe_payload) != recipe_size or recipe_size < 4:
                    raise RuntimeError("truncated AA recipe payload")
                recipe_count = struct.unpack_from("<I", recipe_payload, 0)[0]
                offset = 4
                previous = -1
                operations = 0
                for _ in range(recipe_count):
                    if offset + 5 > len(recipe_payload):
                        raise RuntimeError("truncated AA recipe record")
                    pixel, op_count = struct.unpack_from("<IB", recipe_payload, offset)
                    offset += 5
                    if not previous < pixel < index_bytes or not 1 <= op_count <= MAX_RECIPE_OPERATIONS:
                        raise RuntimeError("invalid AA recipe record")
                    if offset + op_count * 2 > len(recipe_payload):
                        raise RuntimeError("truncated AA recipe operations")
                    for operation in range(op_count):
                        source_index, code = struct.unpack_from(
                            "<BB", recipe_payload, offset + operation * 2
                        )
                        if representatives[source_index] == 0xFFFF or code >= len(BLEND_WEIGHTS):
                            raise RuntimeError("invalid AA recipe palette provenance")
                    offset += op_count * 2
                    previous = pixel
                    operations += op_count
                if offset != len(recipe_payload):
                    raise RuntimeError("trailing AA recipe bytes")
                frame_count += 1
                index_bytes_total += index_bytes
                recipe_bytes_total += recipe_size
                recipe_count_total += recipe_count
                operation_count_total += operations
            for _ in range(cycles):
                raw_count = stream.read(4)
                if len(raw_count) != 4:
                    raise RuntimeError("truncated AA cycle")
                slot_count = struct.unpack("<I", raw_count)[0]
                slots = stream.read(slot_count * 4)
                if slot_count == 0 or len(slots) != slot_count * 4:
                    raise RuntimeError("invalid AA cycle")
                if any(value >= frames for value in struct.unpack(f"<{slot_count}I", slots)):
                    raise RuntimeError("AA cycle frame index is invalid")
            resource_count += 1
        if stream.read(1):
            raise RuntimeError("trailing AA registry bytes")
    if resource_count != declared_resources:
        raise RuntimeError("AA registry resource total differs")
    return {
        "registry_magic": "IEECSXN",
        "registry_version": REGISTRY_VERSION,
        "registry_scale": 2,
        "animation_id": "0x6102",
        "resource_count": resource_count,
        "frame_count": frame_count,
        "index_bytes": index_bytes_total,
        "recipe_bytes": recipe_bytes_total,
        "recipe_count": recipe_count_total,
        "operation_count": operation_count_total,
        "registry_bytes": size,
        "sha256": base.sha256_file(path),
    }


def verify_source_contract(job: dict[str, Any]) -> tuple[list[base.SourceFrame], list[dict[str, Any]], dict[str, Any]]:
    manifest_path = job_path(job, "source_manifest")
    if base.sha256_file(manifest_path) != str(job["source_manifest_sha256"]).upper():
        raise RuntimeError("AA source manifest changed")
    frames, resources, manifest = base.load_source_frames(manifest_path)
    if manifest.get("job_id") != "dwarf-male-fighter-cdmb1-xbr2x":
        raise RuntimeError("AA source is not the pinned CDMB1 baseline job")
    if len(resources) != 23 or len(frames) != 10323:
        raise RuntimeError("AA source inventory differs from CDMB1")
    if [str(item["source"]["name"]).upper() for item in resources] != sorted(
        str(item["source"]["name"]).upper() for item in resources
    ):
        raise RuntimeError("AA source resources are not canonically ordered")
    return frames, resources, manifest


def verify_game_contract(job: dict[str, Any]) -> None:
    game = job_path(job, "game_root")
    executable = game / "BaldurReal.exe"
    if base.sha256_file(executable) != str(job["compatibility"]["baldur_real_sha256"]).upper():
        raise RuntimeError("installed BaldurReal.exe differs from the AA job")
    identity_job = {
        "animation": job["animation"],
        "paths": {"game_root": str(game)},
    }
    base.require_clean_character_identity_overrides(identity_job, game)
    identity = base.verify_character_animation_identity(identity_job, base.KeyIndex(game))
    if identity.get("bam_prefix") != "CDMB1":
        raise RuntimeError("installed game no longer resolves CDMB1 for armor code 1")


def build_pack(job: dict[str, Any], force: bool, resume: bool) -> dict[str, Any]:
    verify_game_contract(job)
    frames, resources, _ = verify_source_contract(job)
    output = build_dir(job)
    manifest_path = output / "build-manifest.json"
    if resume and manifest_path.is_file():
        try:
            return {"status": "reused", **verify_build(job)}
        except (OSError, RuntimeError, ValueError, KeyError):
            pass
    if output.exists() and not (force or resume):
        raise RuntimeError(f"AA build exists; use --resume or --force: {output}")
    base.assert_workspace_child(output, "AA build output")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="aa-build.tmp-", dir=output.parent))
    scalepix = job_path(job, "scalepix")
    node = str(job.get("tools", {}).get("node", "node"))
    contract = base.UpscaleContract(
        scale=2,
        algorithm="XBR/xbr2X",
        passes=1,
        antialias=True,
        xbr_blend=True,
        explicit=True,
    )
    total_pixels = 0
    total_partial_alpha = 0
    total_recipes = 0
    total_operations = 0
    report_resources: list[dict[str, Any]] = []
    try:
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True)
        registry = pack_dir / REGISTRY_FILENAME
        with registry.open("wb") as stream:
            stream.write(REGISTRY_MAGIC)
            stream.write(struct.pack("<IIII", REGISTRY_VERSION, 2, len(resources), 0x6102))
            for resource in resources:
                source = resource["source"]
                resref = str(source["name"]).upper()
                resource_frames: list[base.SourceFrame] = resource["frames"]
                cycles = sorted(resource["cycles"], key=lambda item: int(item["index"]))
                if [int(item["index"]) for item in cycles] != list(range(len(cycles))):
                    raise RuntimeError(f"{resref}: non-contiguous cycles")
                stream.write(resref.encode("ascii").ljust(8, b"\0"))
                stream.write(bytes.fromhex(base.sha256_file(resource["source_path"])))
                stream.write(struct.pack("<II", len(resource_frames), len(cycles)))
                samples: dict[int, tuple[int, int, bytes]] = {}
                sample_positions = set(base.comparison_sample_positions(len(resource_frames)))
                blended_for_resource = 0
                operations_for_resource = 0
                for batch_start, batch_end, _ in base.xbr_output_batch_ranges(
                    resource_frames, 2, base.XBR_OUTPUT_BATCH_BUDGET_BYTES
                ):
                    batch_frames = resource_frames[batch_start:batch_end]
                    batch_outputs = run_xbr_aa(batch_frames, scalepix, node)
                    for local_offset, (frame, output_record) in enumerate(
                        zip(batch_frames, batch_outputs, strict=True)
                    ):
                        frame_index = batch_start + local_offset
                        width, height, scaled_rgba = output_record
                        if width != frame.width * 2 or height != frame.height * 2:
                            raise RuntimeError(f"{resref} frame {frame.index}: AA dimensions differ")
                        base_indices, recipes = frame_blend_recipes(frame)
                        reproduced = render_recipes(frame, base_indices, recipes)
                        if reproduced != scaled_rgba:
                            raise RuntimeError(
                                f"{resref} frame {frame.index}: palette recipe differs from Scalepix AA"
                            )
                        representatives = frame_representatives(frame)
                        if np.any(representatives[base_indices] == 0xFFFF):
                            raise RuntimeError(f"{resref} frame {frame.index}: missing base provenance")
                        recipe_payload = encode_recipes(recipes, base_indices.size)
                        stream.write(
                            struct.pack(
                                "<HHhhB3xI",
                                frame.width,
                                frame.height,
                                frame.center_x,
                                frame.center_y,
                                frame.transparent,
                                base_indices.size,
                            )
                        )
                        stream.write(representatives.astype("<u2", copy=False).tobytes())
                        stream.write(memoryview(base_indices))
                        stream.write(struct.pack("<I", len(recipe_payload)))
                        stream.write(recipe_payload)
                        alpha = np.frombuffer(scaled_rgba, dtype=np.uint8).reshape(-1, 4)[:, 3]
                        total_partial_alpha += int(np.count_nonzero((alpha != 0) & (alpha != 255)))
                        operation_count = sum(len(item[1]) for item in recipes)
                        total_pixels += base_indices.size
                        total_recipes += len(recipes)
                        total_operations += operation_count
                        blended_for_resource += len(recipes)
                        operations_for_resource += operation_count
                        if frame_index in sample_positions:
                            samples[frame_index] = output_record
                    del batch_outputs, batch_frames
                for cycle in cycles:
                    lookup = [int(value) for value in cycle["frame_indices"]]
                    if not lookup or any(value < 0 or value >= len(resource_frames) for value in lookup):
                        raise RuntimeError(f"{resref}: invalid cycle lookup")
                    stream.write(struct.pack("<I", len(lookup)))
                    stream.write(struct.pack(f"<{len(lookup)}I", *lookup))
                base.make_comparison_sheet_samples(
                    resource_frames,
                    samples,
                    temporary / "qa" / f"{resref}-comparison.png",
                    contract,
                )
                report_resources.append(
                    {
                        "resref": resref,
                        "source": base.relative_project_path(resource["source_path"]),
                        "source_sha256": base.sha256_file(resource["source_path"]),
                        "frames": len(resource_frames),
                        "cycles": len(cycles),
                        "cycle_slots": sum(len(item["frame_indices"]) for item in cycles),
                        "blended_pixels": blended_for_resource,
                        "blend_operations": operations_for_resource,
                        "qa_sheet": f"qa/{resref}-comparison.png",
                    }
                )
        info = inspect_registry(registry)
        if info["frame_count"] != len(frames) or info["index_bytes"] != total_pixels:
            raise RuntimeError("AA registry totals differ from generated frames")
        if info["recipe_count"] != total_recipes or info["operation_count"] != total_operations:
            raise RuntimeError("AA registry recipe totals differ")
        report = {
            "schema": BUILD_SCHEMA,
            "status": "built-pending-ingame-qa",
            "created_at_utc": base.utc_now(),
            "job_id": job["job_id"],
            "animation_id": "0x6102",
            "bam_prefix": "CDMB1",
            "runtime_profile": "character-bg2ee-2.7.3.0",
            "registry_magic": "IEECSXN",
            "registry_version": REGISTRY_VERSION,
            "registry_scale": 2,
            "registry_layout": "monolith",
            "registry": f"iee-assets/creature-sprites/{REGISTRY_FILENAME}",
            "registry_bytes": info["registry_bytes"],
            "registry_sha256": info["sha256"],
            "source_manifest": base.relative_project_path(job_path(job, "source_manifest")),
            "source_manifest_sha256": base.sha256_file(job_path(job, "source_manifest")),
            "scalepix": str(scalepix),
            "scalepix_sha256": base.sha256_file(scalepix),
            "xbr_adapter": base.relative_project_path(AA_ADAPTER),
            "xbr_adapter_sha256": base.sha256_file(AA_ADAPTER),
            "method": job["upscale"],
            "sampling": "NEAREST",
            "resources": report_resources,
            "resource_count": len(resources),
            "frame_count": len(frames),
            "x2_pixel_count": total_pixels,
            "total_index_bytes": info["index_bytes"],
            "total_recipe_bytes": info["recipe_bytes"],
            "blended_pixel_count": total_recipes,
            "blend_operation_count": total_operations,
            "validation": {
                "dimensions_exact_x2": len(frames),
                "frames_exactly_reproduced_from_palette_recipes": len(frames),
                "duplicate_palette_indices_preserved_by_source_provenance": True,
                "partial_alpha_pixels": total_partial_alpha,
                "partial_alpha_policy": "allowed-and-counted-for-single-body-layer",
                "new_fixed_rgba_colors": 0,
                "runtime_sampling": "NEAREST",
            },
            "layer": {"kind": "body", "armor_code": 1},
        }
        base.write_json(temporary / "build-manifest.json", report)
        if output.exists():
            shutil.rmtree(output)
        temporary.replace(output)
        return {"status": "built", **info, "partial_alpha_pixels": total_partial_alpha}
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify_build(job: dict[str, Any]) -> dict[str, Any]:
    verify_source_contract(job)
    manifest = base.read_json(build_dir(job) / "build-manifest.json")
    if manifest.get("schema") != BUILD_SCHEMA or manifest.get("status") != "built-pending-ingame-qa":
        raise RuntimeError("AA build manifest is invalid")
    if manifest.get("job_id") != job["job_id"] or manifest.get("method") != job["upscale"]:
        raise RuntimeError("AA build identity differs from the job")
    if manifest.get("source_manifest_sha256") != base.sha256_file(job_path(job, "source_manifest")):
        raise RuntimeError("AA build source manifest changed")
    if manifest.get("scalepix_sha256") != base.sha256_file(job_path(job, "scalepix")):
        raise RuntimeError("AA build Scalepix changed")
    if manifest.get("xbr_adapter_sha256") != base.sha256_file(AA_ADAPTER):
        raise RuntimeError("AA build adapter changed")
    registry = build_dir(job) / "iee-assets" / "creature-sprites" / REGISTRY_FILENAME
    info = inspect_registry(registry)
    if manifest.get("registry_sha256") != info["sha256"] or manifest.get("registry_bytes") != info["registry_bytes"]:
        raise RuntimeError("AA registry differs from its build manifest")
    if manifest.get("frame_count") != info["frame_count"] or manifest.get("resource_count") != info["resource_count"]:
        raise RuntimeError("AA build totals differ from its registry")
    validation = manifest.get("validation", {})
    if validation.get("frames_exactly_reproduced_from_palette_recipes") != info["frame_count"]:
        raise RuntimeError("AA exact-reproduction gate is incomplete")
    if validation.get("runtime_sampling") != "NEAREST":
        raise RuntimeError("AA build must use NEAREST sampling")
    return info


def build_runtime(job: dict[str, Any]) -> dict[str, Any]:
    return base.build_runtime(job)


def verify_runtime(job: dict[str, Any]) -> dict[str, Any]:
    return base.verify_runtime(job)


def plan(job: dict[str, Any]) -> dict[str, Any]:
    game = job_path(job, "game_root")
    active_parent: list[str] = []
    sprite_root = base.PROJECT_ROOT / "sprite"
    for candidate in sprite_root.rglob("active-test.json"):
        if candidate.resolve() == active_state_path(job).resolve():
            continue
        try:
            state = base.read_json(candidate)
        except (OSError, RuntimeError, ValueError):
            continue
        if state.get("status") in {
            "installing", "restoring", "installed-pending-qa", "validated-installed", "qa-failed"
        }:
            active_parent.append(str(candidate))
    return {
        "job_id": job["job_id"],
        "scope": "CDMB1 body only; Character armor code 1; no equipped overlays",
        "method": "XBR/xbr2X x2 one-pass Antialias; palette blend recipes; NEAREST",
        "source_manifest": str(job_path(job, "source_manifest")),
        "source_manifest_pinned": base.sha256_file(job_path(job, "source_manifest"))
        == str(job["source_manifest_sha256"]).upper(),
        "game_compatible": (game / "BaldurReal.exe").is_file()
        and base.sha256_file(game / "BaldurReal.exe")
        == str(job["compatibility"]["baldur_real_sha256"]).upper(),
        "build_exists": (build_dir(job) / "build-manifest.json").is_file(),
        "runtime_exists": (runtime_dir(job) / "runtime-manifest.json").is_file(),
        "active_parent_tests": active_parent,
        "parallel_artifacts_only": True,
        "release_manifest_modified": False,
        "game_launch_is_never_automatic": True,
    }


def prepare(job: dict[str, Any], force: bool, resume: bool) -> dict[str, Any]:
    built = build_pack(job, force, resume)
    runtime = build_runtime(job)
    return {"build": built, "runtime": runtime}


def invoke_powershell(
    script: Path,
    job: dict[str, Any],
    recover: bool = False,
    verify_only: bool = False,
) -> None:
    if not script.is_file():
        raise RuntimeError(f"missing AA transaction script: {script}")
    powershell = shutil.which("pwsh") or shutil.which("powershell")
    if not powershell:
        raise RuntimeError("PowerShell is required for the AA ingame transaction")
    command = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-JobFile",
        str(job["_job_file"]),
    ]
    if verify_only:
        command.append("-VerifyOnly")
    if recover:
        command.append("-RecoverInterrupted")
    base.run_checked(command)


def status(job: dict[str, Any]) -> dict[str, Any]:
    state_path = active_state_path(job)
    if not state_path.is_file():
        return {"status": "not-installed", "state": str(state_path)}
    return base.read_json(state_path)


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "plan",
            "build",
            "build-runtime",
            "prepare",
            "verify",
            "install",
            "verify-restore",
            "restore",
            "status",
        ),
    )
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--recover-interrupted", action="store_true")
    return parser


def main() -> None:
    args = make_parser().parse_args()
    job = load_job(args.job)
    if args.command == "plan":
        result = plan(job)
    elif args.command == "build":
        result = build_pack(job, args.force, args.resume)
    elif args.command == "build-runtime":
        result = build_runtime(job)
    elif args.command == "prepare":
        result = prepare(job, args.force, args.resume)
    elif args.command == "verify":
        verify_game_contract(job)
        result = {"build": verify_build(job), "runtime": verify_runtime(job)}
    elif args.command == "install":
        verify_game_contract(job)
        verify_build(job)
        verify_runtime(job)
        invoke_powershell(INSTALL_SCRIPT, job)
        result = status(job)
    elif args.command == "verify-restore":
        invoke_powershell(RESTORE_SCRIPT, job, verify_only=True)
        result = {
            "restore_preflight": "verified",
            "active_state": status(job),
        }
    elif args.command == "restore":
        invoke_powershell(RESTORE_SCRIPT, job, args.recover_interrupted)
        result = status(job)
    else:
        result = status(job)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
