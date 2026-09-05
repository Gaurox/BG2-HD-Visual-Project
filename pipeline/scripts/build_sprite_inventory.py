"""Build a read-only, normalized inventory of BG2EE creature sprites.

The scanner reads only stock KEY/BIF resources plus override filenames used as
collision signals.  It never writes to the game directory.  Its four CSVs are
intended to answer two separate questions without conflating them:

* which animation, layer, item and BAM resources exist;
* which exact families are accepted by the current xN pipeline/runtime.

The manifest also records the canonical monolith and multi-shard registry-set
contracts.  Per-resource size estimates remain the historical V2/x2 cost so
existing consumers keep the same meaning; callers can project another scale
with :func:`estimate_registry_resource_bytes`.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import struct
import sys
import zlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import numpy as np


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

from bam_export import decode_bam  # noqa: E402
from run_creature_sprite_x2 import (  # noqa: E402
    BAM_TYPE,
    CHARACTER_BODY_SUFFIXES,
    CHARACTER_EQUIPMENT_SUFFIXES_BY_LAYER,
    INI_TYPE,
    IDS_TYPE,
    ITM_TYPE,
    MAX_FRAMES_PER_RESOURCE,
    MAX_LAZY_FRAME_INDEX_BYTES,
    MAX_REGISTRY_BYTES,
    MAX_REGISTRY_BYTES_BY_SCALE,
    MAX_REGISTRY_SET_BYTES,
    MAX_REGISTRY_SET_FRAMES,
    MAX_REGISTRY_SET_RESOURCES,
    MAX_REGISTRY_SET_SHARDS,
    MAX_RESOURCES,
    REGISTRY_HEADER_BYTES,
    XN_REGISTRY_MAGIC,
    XN_REGISTRY_SET_MAGIC,
    XN_REGISTRY_SET_VERSION,
    XN_REGISTRY_VERSION,
    XBR_OUTPUT_BATCH_BUDGET_BYTES,
    KeyIndex,
    maximum_registry_bytes,
    parse_animation_ini,
    parse_ids,
    partition_registry_resources,
)
from workspace_paths import get_path  # noqa: E402


TDA_TYPE = 0x03F4
CRE_TYPE = 0x03F1
SCHEMA = "bg2-upscale-sprite-inventory-v1"
DEFAULT_GAME_ROOT = get_path("bg2ee_game_root")
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "sprite" / "index"
WEAPON_ITEM_TYPES = frozenset(range(15, 31))

ANIMATION_FIELDS = (
    "animation_id",
    "animation_id_decimal",
    "ids_symbol",
    "ids_present",
    "ini_present",
    "symbol_class",
    "symbol_gender",
    "symbol_race",
    "symbol_variant",
    "animation_family",
    "animation_type",
    "engine_section",
    "ini_resref",
    "ini_source_bif",
    "ini_sha256",
    "split_bams",
    "false_color",
    "can_lie_down",
    "detected_by_infravision",
    "equip_helmet",
    "resref",
    "resref_paperdoll",
    "resref_armor_base",
    "resref_armor_specific",
    "armor_max_code",
    "height_code",
    "height_code_helmet",
    "height_code_shield",
    "resref_weapon1",
    "resref_weapon2",
    "ini_sections_json",
    "runtime_profile",
    "runtime_supported",
    "family_count",
    "pipeline_ready_family_count",
    "override_collision",
    "blocker",
)

FAMILY_FIELDS = (
    "family_id",
    "animation_id",
    "ids_symbol",
    "animation_type",
    "engine_section",
    "layer_kind",
    "variant_kind",
    "variant_value",
    "item_animation_code",
    "item_count",
    "item_resrefs",
    "height_code",
    "bam_prefix",
    "discovery_rule",
    "expected_suffixes",
    "suffixes_present",
    "missing_suffixes",
    "unexpected_suffixes",
    "paperdoll_resources",
    "resource_count",
    "frame_count",
    "cycle_count",
    "registry_estimated_bytes",
    "registry_estimated_mib",
    "required_job_contract",
    "registry_layout_x2",
    "shard_count_x2",
    "resource_limit_pass",
    "frame_limit_pass",
    "registry_limit_pass",
    "suffixes_supported",
    "duplicate_used_rgba_frames",
    "duplicate_used_rgba_examples",
    "runtime_profile",
    "runtime_supported",
    "pipeline_ready",
    "override_collision",
    "blocker",
)

RESOURCE_FIELDS = (
    "bam_resref",
    "source_bif",
    "locator",
    "source_sha256",
    "canonical_sha256",
    "bam_container",
    "bam_version",
    "decode_status",
    "decode_error",
    "frame_count",
    "cycle_count",
    "cycle_slot_count",
    "transparent_palette_index",
    "width_min",
    "width_max",
    "height_min",
    "height_max",
    "center_x_min",
    "center_x_max",
    "center_y_min",
    "center_y_max",
    "native_pixel_count",
    "native_frame_pixel_count_max",
    "transparent_pixel_count",
    "opaque_pixel_count",
    "used_palette_index_count",
    "partial_alpha_pixels",
    "duplicate_used_rgba_frames",
    "duplicate_used_rgba_pairs",
    "duplicate_used_rgba_examples",
    "registry_resource_estimated_bytes",
    "family_count",
    "family_ids",
    "animation_ids",
    "layer_kinds",
    "bam_prefixes",
    "bam_suffixes",
    "runtime_relevant",
    "override_collision",
    "blocker",
)

ITEM_FIELDS = (
    "item_resref",
    "item_type",
    "item_type_symbol",
    "visual_layer",
    "animation_code_raw_hex",
    "animation_code",
    "animation_code_valid",
    "body_armor_code",
    "source_bif",
    "locator",
    "source_sha256",
    "candidate_family_count",
    "compatible_animation_count",
    "compatible_animation_ids",
    "candidate_bam_prefixes",
    "resolved_bam_prefixes",
    "unresolved_bam_prefixes",
    "pipeline_ready_prefixes",
    "override_collision",
    "blocker",
)


def yes_no(value: bool) -> str:
    return "yes" if value else "no"


def joined(values: Iterable[Any]) -> str:
    return ";".join(sorted({str(value) for value in values if str(value) != ""}))


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def safe_int(value: str) -> int | None:
    return int(value) if value.isdigit() else None


def estimate_registry_resource_bytes(resource: dict[str, Any], scale: int) -> int:
    """Project one V2/V3 resource record without materializing scaled pixels."""

    if scale not in (2, 4):
        raise ValueError("inventory registry projection supports scale 2 or 4")
    return (
        48
        + int(resource["frame_count"]) * 528
        + int(resource["native_pixel_count"]) * scale * scale
        + int(resource["cycle_count"]) * 4
        + int(resource["cycle_slot_count"]) * 4
    )


def build_registry_set_projections(
    resources: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project deterministic x2/x4 sets for every runtime-relevant animation."""

    by_animation: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for resource in resources:
        if (
            resource.get("decode_status") != "ok"
            or resource.get("runtime_relevant") != "yes"
            or resource.get("override_collision") != "no"
        ):
            continue
        for animation_id in filter(None, str(resource.get("animation_ids", "")).split(";")):
            by_animation[animation_id].append(resource)

    animations: dict[str, Any] = {}
    for animation_id in sorted(by_animation):
        selected = sorted(by_animation[animation_id], key=lambda row: row["bam_resref"])
        frame_count = sum(int(resource["frame_count"]) for resource in selected)
        projection: dict[str, Any] = {
            "resource_count": len(selected),
            "frame_count": frame_count,
        }
        for scale in (2, 4):
            sized = [
                {
                    "resref": resource["bam_resref"],
                    "bytes": estimate_registry_resource_bytes(resource, scale),
                }
                for resource in selected
            ]
            largest = max(sized, key=lambda record: (record["bytes"], record["resref"]))
            largest_frame = max(
                selected,
                key=lambda resource: (
                    int(resource["native_frame_pixel_count_max"]),
                    resource["bam_resref"],
                ),
            )
            largest_frame_bytes = (
                int(largest_frame["native_frame_pixel_count_max"]) * scale * scale
            )
            byte_limit = maximum_registry_bytes(scale)
            blocker = ""
            shards: list[list[dict[str, Any]]] = []
            if len(sized) > MAX_REGISTRY_SET_RESOURCES:
                blocker = "registry-set-resource-limit"
            elif frame_count > MAX_REGISTRY_SET_FRAMES:
                blocker = "registry-set-frame-limit"
            elif largest_frame_bytes > MAX_LAZY_FRAME_INDEX_BYTES:
                blocker = "registry-set-frame-index-size-limit"
            elif REGISTRY_HEADER_BYTES + int(largest["bytes"]) > byte_limit:
                blocker = "registry-set-resource-shard-size-limit"
            else:
                try:
                    shards = partition_registry_resources(
                        sized, maximum_bytes=byte_limit
                    )
                except RuntimeError:
                    blocker = "registry-set-shard-count-limit"
            aggregate_bytes = (
                sum(int(record["bytes"]) for record in sized)
                + len(shards) * REGISTRY_HEADER_BYTES
                if not blocker
                else None
            )
            if aggregate_bytes is not None and aggregate_bytes > MAX_REGISTRY_SET_BYTES:
                blocker = "registry-set-aggregate-size-limit"
                aggregate_bytes = None
                shards = []
            projection[f"x{scale}"] = {
                "shard_byte_limit": byte_limit,
                "maximum_resource_resref": largest["resref"],
                "maximum_resource_bytes": int(largest["bytes"]),
                "maximum_frame_resref": largest_frame["bam_resref"],
                "maximum_frame_index_bytes": largest_frame_bytes,
                "shard_count": len(shards) if not blocker else None,
                "total_registry_bytes": aggregate_bytes,
                "fits_set": not blocker,
                "blocker": blocker,
            }
        animations[animation_id] = projection
    return {
        "policy": (
            "unique decoded runtime-relevant stock BAMs without override collision, "
            "grouped per animation_id and ordered by bam_resref"
        ),
        "animations": animations,
    }


def animation_symbol_parts(symbol: str) -> tuple[str, str, str, str]:
    if not symbol:
        return "", "", "", ""
    tokens = symbol.split("_")
    gender = next((value for value in ("MALE", "FEMALE") if value in tokens), "")
    races = ("HALF_ELF", "HALFORC", "HALFLING", "HUMAN", "DWARF", "GNOME", "ELF")
    race = next((value for value in races if value in symbol), "")
    variants = [value for value in ("LOW", "BG1", "BG2") if value in tokens]
    stop = set(gender.split("_")) | set(race.split("_")) | set(variants)
    role_tokens = [token for token in tokens if token not in stop]
    return "_".join(role_tokens), gender, race, joined(variants)


def engine_section(sections: dict[str, dict[str, str]]) -> str:
    names = [name for name in sections if name not in {"general", "sounds"}]
    return joined(names)


def current_runtime(
    animation_id: int, animation_type: str, section: str
) -> tuple[str, bool]:
    family = animation_id & 0xF000
    if family in {0x5000, 0x6000} and animation_type in {"5000", "6000"}:
        return "character-bg2ee-2.7.3.0", section == "character"
    if family == 0xE000 and animation_type == "E000":
        return "monster-icewind-bg2ee-2.7.3.0", section == "monster_icewind"
    return "", False


def build_stock_cre_usage(
    index: KeyIndex,
    animations: list[dict[str, Any]],
    families: list[dict[str, Any]],
) -> dict[str, Any]:
    """Count stock CRE animation use and join it to current pipeline eligibility."""

    counts: Counter[int] = Counter()
    versions: Counter[str] = Counter()
    for name, entry in sorted(index.resource_map(CRE_TYPE).items()):
        raw, _ = index.resolve(entry)
        if len(raw) < 0x2A or raw[:4] != b"CRE ":
            raise RuntimeError(f"unsupported stock CRE resource: {name}")
        version = raw[:8].decode("ascii", errors="strict")
        if version != "CRE V1.0":
            raise RuntimeError(f"unsupported stock CRE version for {name}: {version}")
        versions[version] += 1
        counts[struct.unpack_from("<H", raw, 0x28)[0]] += 1

    animation_by_id = {
        int(animation["animation_id_decimal"]): animation for animation in animations
    }
    families_by_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for family in families:
        families_by_id[int(family["animation_id"], 16)].append(family)

    used_ids = set(counts)
    unknown_ids = sorted(used_ids - set(animation_by_id))
    if unknown_ids:
        formatted = ", ".join(f"0x{animation_id:04X}" for animation_id in unknown_ids)
        raise RuntimeError(f"stock CRE references unknown animation IDs: {formatted}")

    fully_ready_ids: list[int] = []
    with_bam_ids: list[int] = []
    without_bam_ids: list[int] = []
    runtime_supported_without_bam_ids: list[int] = []
    runtime_supported_blocked_ids: list[int] = []
    runtime_unsupported_ids: list[int] = []
    for animation_id in sorted(used_ids):
        animation = animation_by_id[animation_id]
        nonempty = [
            family
            for family in families_by_id.get(animation_id, [])
            if int(family["resource_count"] or 0) > 0
        ]
        if nonempty:
            with_bam_ids.append(animation_id)
        else:
            without_bam_ids.append(animation_id)
        if nonempty and all(
            family["pipeline_ready"] == "yes"
            and not family["blocker"]
            and not family["override_collision"]
            for family in nonempty
        ):
            fully_ready_ids.append(animation_id)
        elif animation["runtime_supported"] == "yes" and not nonempty:
            runtime_supported_without_bam_ids.append(animation_id)
        elif animation["runtime_supported"] == "yes":
            runtime_supported_blocked_ids.append(animation_id)
        elif animation["runtime_supported"] == "no":
            runtime_unsupported_ids.append(animation_id)

    classified_ids = (
        set(fully_ready_ids)
        | set(runtime_supported_without_bam_ids)
        | set(runtime_supported_blocked_ids)
        | set(runtime_unsupported_ids)
    )
    if classified_ids != used_ids:
        raise RuntimeError("stock CRE animation classification is not exhaustive")

    ready_cre_resources = sum(counts[animation_id] for animation_id in fully_ready_ids)
    total_cre_resources = sum(counts.values())
    return {
        "source": {
            "resource_type": f"0x{CRE_TYPE:04X}",
            "container": "stock KEY/BIF",
            "animation_id_encoding": "u16-le",
            "animation_id_offset": 0x28,
        },
        "cre_versions": dict(sorted(versions.items())),
        "cre_resource_count": total_cre_resources,
        "animation_id_count": len(used_ids),
        "animation_ids": [f"0x{animation_id:04X}" for animation_id in sorted(used_ids)],
        "zero_animation_id_cre_resource_count": counts.get(0, 0),
        "nonzero_animation_id_count": len(used_ids - {0}),
        "nonzero_animation_ids": [
            f"0x{animation_id:04X}" for animation_id in sorted(used_ids - {0})
        ],
        "with_bam_animation_id_count": len(with_bam_ids),
        "with_bam_animation_ids": [
            f"0x{animation_id:04X}" for animation_id in with_bam_ids
        ],
        "without_bam_animation_id_count": len(without_bam_ids),
        "without_bam_animation_ids": [
            f"0x{animation_id:04X}" for animation_id in without_bam_ids
        ],
        "without_bam_nonzero_animation_id_count": len(
            set(without_bam_ids) - {0}
        ),
        "without_bam_nonzero_animation_ids": [
            f"0x{animation_id:04X}"
            for animation_id in sorted(set(without_bam_ids) - {0})
        ],
        "cre_resources_by_animation_id": {
            f"0x{animation_id:04X}": counts[animation_id]
            for animation_id in sorted(used_ids)
        },
        "fully_pipeline_ready_animation_id_count": len(fully_ready_ids),
        "fully_pipeline_ready_animation_ids": [
            f"0x{animation_id:04X}" for animation_id in fully_ready_ids
        ],
        "fully_pipeline_ready_cre_resource_count": ready_cre_resources,
        "fully_pipeline_ready_cre_coverage_percent": round(
            100.0 * ready_cre_resources / total_cre_resources, 3
        )
        if total_cre_resources
        else 0.0,
        "runtime_supported_without_bam_animation_id_count": len(
            runtime_supported_without_bam_ids
        ),
        "runtime_supported_without_bam_animation_ids": [
            f"0x{animation_id:04X}"
            for animation_id in runtime_supported_without_bam_ids
        ],
        "runtime_supported_blocked_animation_id_count": len(
            runtime_supported_blocked_ids
        ),
        "runtime_supported_blocked_animation_ids": [
            f"0x{animation_id:04X}" for animation_id in runtime_supported_blocked_ids
        ],
        "runtime_unsupported_animation_id_count": len(runtime_unsupported_ids),
        "runtime_unsupported_animation_ids": [
            f"0x{animation_id:04X}" for animation_id in runtime_unsupported_ids
        ],
        "runtime_unsupported_nonzero_animation_id_count": len(
            set(runtime_unsupported_ids) - {0}
        ),
        "runtime_unsupported_nonzero_animation_ids": [
            f"0x{animation_id:04X}"
            for animation_id in sorted(set(runtime_unsupported_ids) - {0})
        ],
    }


def override_resrefs(game_root: Path, suffix: str) -> set[str]:
    directory = game_root / "override"
    if not directory.is_dir():
        return set()
    return {
        path.stem.upper()
        for path in directory.iterdir()
        if path.is_file() and path.suffix.upper() == suffix.upper()
    }


def canonical_bam(raw: bytes) -> tuple[bytes, str]:
    if raw[:4] == b"BAMC":
        if len(raw) < 12:
            raise RuntimeError("truncated BAMC")
        return zlib.decompress(raw[12:]), "BAMC"
    return raw, "BAM"


def bam_stats(index: KeyIndex, entry: tuple[str, int, int]) -> dict[str, Any]:
    name, _, locator = entry
    raw, bif_name = index.resolve(entry)
    result: dict[str, Any] = {
        "bam_resref": name,
        "source_bif": bif_name.replace("\\", "/"),
        "locator": f"0x{locator:08X}",
        "source_sha256": sha256_bytes(raw),
        "canonical_sha256": "",
        "bam_container": "",
        "bam_version": "",
        "decode_status": "error",
        "decode_error": "",
        "frame_count": "",
        "cycle_count": "",
        "cycle_slot_count": "",
        "transparent_palette_index": "",
        "width_min": "",
        "width_max": "",
        "height_min": "",
        "height_max": "",
        "center_x_min": "",
        "center_x_max": "",
        "center_y_min": "",
        "center_y_max": "",
        "native_pixel_count": "",
        "native_frame_pixel_count_max": "",
        "transparent_pixel_count": "",
        "opaque_pixel_count": "",
        "used_palette_index_count": "",
        "partial_alpha_pixels": 0,
        "duplicate_used_rgba_frames": "",
        "duplicate_used_rgba_pairs": "",
        "duplicate_used_rgba_examples": "",
        "registry_resource_estimated_bytes": "",
    }
    try:
        data, container = canonical_bam(raw)
        if data[:8] != b"BAM V1  ":
            raise RuntimeError(f"unsupported BAM signature {data[:8]!r}")
        frames, palette, transparent = decode_bam(data)
        frame_count, cycle_count = struct.unpack_from("<HB", data, 8)
        if frame_count != len(frames):
            raise RuntimeError("decoded frame count differs from BAM header")
        off_frames, _, lookup_offset = struct.unpack_from("<III", data, 0x0C)
        cycle_offset = off_frames + frame_count * 12
        cycle_slots = 0
        for cycle_index in range(cycle_count):
            count, first = struct.unpack_from("<HH", data, cycle_offset + cycle_index * 4)
            if lookup_offset + (first + count) * 2 > len(data):
                raise RuntimeError(f"invalid cycle lookup {cycle_index}")
            cycle_slots += count

        widths: list[int] = []
        heights: list[int] = []
        centers_x: list[int] = []
        centers_y: list[int] = []
        native_pixels = 0
        transparent_pixels = 0
        used_indices: set[int] = set()
        duplicate_frames = 0
        duplicate_pairs: set[str] = set()
        duplicate_examples: list[str] = []
        for frame_index, (indices, center_x, center_y, frame_transparent) in enumerate(frames):
            height, width = indices.shape
            widths.append(width)
            heights.append(height)
            centers_x.append(center_x)
            centers_y.append(center_y)
            native_pixels += int(indices.size)
            transparent_pixels += int(np.count_nonzero(indices == frame_transparent))
            used = np.unique(indices).tolist()
            used_indices.update(int(value) for value in used)
            colors: dict[tuple[int, int, int, int], list[int]] = defaultdict(list)
            for palette_index in used:
                value = int(palette_index)
                rgba = (
                    int(palette[value, 0]),
                    int(palette[value, 1]),
                    int(palette[value, 2]),
                    0 if value == frame_transparent else 255,
                )
                colors[rgba].append(value)
            duplicates = [values for values in colors.values() if len(values) > 1]
            if duplicates:
                duplicate_frames += 1
                for values in duplicates:
                    for left_index, left in enumerate(values):
                        for right in values[left_index + 1 :]:
                            duplicate_pairs.add(f"{left}={right}")
                if len(duplicate_examples) < 12:
                    compact = ",".join("=".join(map(str, values)) for values in duplicates[:3])
                    duplicate_examples.append(f"{frame_index}:{compact}")

        registry_bytes = (
            48
            + frame_count * 528
            + native_pixels * 4
            + cycle_count * 4
            + cycle_slots * 4
        )
        result.update(
            {
                "canonical_sha256": sha256_bytes(data),
                "bam_container": container,
                "bam_version": "V1",
                "decode_status": "ok",
                "frame_count": frame_count,
                "cycle_count": cycle_count,
                "cycle_slot_count": cycle_slots,
                "transparent_palette_index": transparent,
                "width_min": min(widths) if widths else "",
                "width_max": max(widths) if widths else "",
                "height_min": min(heights) if heights else "",
                "height_max": max(heights) if heights else "",
                "center_x_min": min(centers_x) if centers_x else "",
                "center_x_max": max(centers_x) if centers_x else "",
                "center_y_min": min(centers_y) if centers_y else "",
                "center_y_max": max(centers_y) if centers_y else "",
                "native_pixel_count": native_pixels,
                "native_frame_pixel_count_max": max(
                    (int(indices.size) for indices, *_ in frames), default=0
                ),
                "transparent_pixel_count": transparent_pixels,
                "opaque_pixel_count": native_pixels - transparent_pixels,
                "used_palette_index_count": len(used_indices),
                "duplicate_used_rgba_frames": duplicate_frames,
                "duplicate_used_rgba_pairs": len(duplicate_pairs),
                "duplicate_used_rgba_examples": joined(duplicate_examples),
                "registry_resource_estimated_bytes": registry_bytes,
            }
        )
    except Exception as error:  # keep the row: decode failures are inventory data
        result["decode_error"] = f"{type(error).__name__}: {error}"
    return result


def family_id(
    animation_id: int,
    layer: str,
    variant_kind: str,
    variant_value: str,
    prefix: str,
) -> str:
    variant = re.sub(r"[^A-Z0-9_-]+", "-", variant_value.upper()) or "BASE"
    return f"0x{animation_id:04X}:{layer}:{variant_kind}:{variant}:{prefix}"


def base_family(
    animation: dict[str, Any],
    layer: str,
    variant_kind: str,
    variant_value: str,
    prefix: str,
    discovery_rule: str,
) -> dict[str, Any]:
    return {
        "family_id": family_id(
            int(animation["animation_id_decimal"]),
            layer,
            variant_kind,
            variant_value,
            prefix,
        ),
        "animation_id": animation["animation_id"],
        "ids_symbol": animation["ids_symbol"],
        "animation_type": animation["animation_type"],
        "engine_section": animation["engine_section"],
        "layer_kind": layer,
        "variant_kind": variant_kind,
        "variant_value": variant_value,
        "item_animation_code": "",
        "item_count": 0,
        "item_resrefs": "",
        "height_code": "",
        "bam_prefix": prefix,
        "discovery_rule": discovery_rule,
        "expected_suffixes": "",
        "_resource_names": [],
        "_runtime_profile": animation["runtime_profile"],
        "_runtime_supported": animation["runtime_supported"] == "yes",
    }


def item_visual_layer(item_type: int) -> str:
    if item_type == 2:
        return "body"
    if item_type == 7:
        return "helmet"
    if item_type == 12:
        return "shield"
    if item_type in WEAPON_ITEM_TYPES:
        return "weapon"
    return ""


def build_inventory(game_root: Path) -> tuple[list[dict[str, Any]], ...]:
    index = KeyIndex(game_root)
    bam_map = index.resource_map(BAM_TYPE)
    ini_map = index.resource_map(INI_TYPE)
    itm_map = index.resource_map(ITM_TYPE)
    ids_map = index.resource_map(IDS_TYPE)
    override_bams = override_resrefs(game_root, ".BAM")
    override_inis = override_resrefs(game_root, ".INI")
    override_itms = override_resrefs(game_root, ".ITM")
    animate_override = "ANIMATE" in override_resrefs(game_root, ".IDS")

    animate_entry = ids_map.get("ANIMATE")
    if animate_entry is None:
        raise RuntimeError("ANIMATE.IDS is absent from the stock KEY/BIF index")
    animate_raw, _ = index.resolve(animate_entry)
    animate_ids = parse_ids(animate_raw)
    item_categories: dict[int, str] = {}
    itemcat_entry = ids_map.get("ITEMCAT")
    if itemcat_entry is not None:
        item_categories = parse_ids(index.resolve(itemcat_entry)[0])

    ini_ids = {
        int(name, 16)
        for name in ini_map
        if re.fullmatch(r"[0-9A-F]{4}", name)
    }
    animation_ids = sorted(set(animate_ids) | ini_ids)
    animations: list[dict[str, Any]] = []
    sections_by_id: dict[int, dict[str, dict[str, str]]] = {}
    for animation_id in animation_ids:
        symbol = animate_ids.get(animation_id, "")
        role, gender, race, variant = animation_symbol_parts(symbol)
        ini_name = f"{animation_id:04X}"
        entry = ini_map.get(ini_name)
        sections: dict[str, dict[str, str]] = {}
        source_bif = ""
        ini_sha = ""
        if entry is not None:
            raw, source_bif = index.resolve(entry)
            sections = parse_animation_ini(raw)
            source_bif = source_bif.replace("\\", "/")
            ini_sha = sha256_bytes(raw)
        sections_by_id[animation_id] = sections
        section = engine_section(sections)
        config = sections.get(section, {}) if section and ";" not in section else {}
        animation_type = sections.get("general", {}).get("animation_type", "").upper()
        runtime_profile, runtime_supported = current_runtime(
            animation_id, animation_type, section
        )
        blockers: list[str] = []
        if not symbol:
            blockers.append("animate-ids-symbol-missing")
        if entry is None:
            blockers.append("animation-ini-missing")
        if entry is not None and not section:
            blockers.append("engine-section-missing")
        expected_type = f"{animation_id & 0xF000:04X}"
        if animation_type and animation_type != expected_type:
            blockers.append("animation-type-id-mismatch")
        if not runtime_supported:
            blockers.append("runtime-profile-unsupported")
        if ini_name in override_inis or animate_override:
            blockers.append("identity-override-collision")
        animations.append(
            {
                "animation_id": f"0x{animation_id:04X}",
                "animation_id_decimal": animation_id,
                "ids_symbol": symbol,
                "ids_present": yes_no(bool(symbol)),
                "ini_present": yes_no(entry is not None),
                "symbol_class": role,
                "symbol_gender": gender,
                "symbol_race": race,
                "symbol_variant": variant,
                "animation_family": f"0x{animation_id & 0xF000:04X}",
                "animation_type": animation_type,
                "engine_section": section,
                "ini_resref": f"{ini_name}.INI" if entry else "",
                "ini_source_bif": source_bif,
                "ini_sha256": ini_sha,
                "split_bams": config.get("split_bams", ""),
                "false_color": config.get("false_color", ""),
                "can_lie_down": config.get("can_lie_down", ""),
                "detected_by_infravision": config.get("detected_by_infravision", ""),
                "equip_helmet": config.get("equip_helmet", ""),
                "resref": config.get("resref", "").upper(),
                "resref_paperdoll": config.get("resref_paperdoll", "").upper(),
                "resref_armor_base": config.get("resref_armor_base", "").upper(),
                "resref_armor_specific": config.get("resref_armor_specific", "").upper(),
                "armor_max_code": config.get("armor_max_code", ""),
                "height_code": config.get("height_code", "").upper(),
                "height_code_helmet": config.get("height_code_helmet", "").upper(),
                "height_code_shield": config.get("height_code_shield", "").upper(),
                "resref_weapon1": config.get("resref_weapon1", "").upper(),
                "resref_weapon2": config.get("resref_weapon2", "").upper(),
                "ini_sections_json": json.dumps(
                    sections, ensure_ascii=False, sort_keys=True, separators=(",", ":")
                )
                if sections
                else "",
                "runtime_profile": runtime_profile,
                "runtime_supported": yes_no(runtime_supported),
                "family_count": 0,
                "pipeline_ready_family_count": 0,
                "override_collision": yes_no(ini_name in override_inis or animate_override),
                "blocker": joined(blockers),
            }
        )

    items: list[dict[str, Any]] = []
    items_by_layer_code: dict[tuple[str, str], list[str]] = defaultdict(list)
    for item_name, entry in sorted(itm_map.items()):
        raw, bif_name = index.resolve(entry)
        item_type: int | None = None
        animation_code = ""
        raw_code = raw[0x22:0x24] if len(raw) >= 0x24 else b""
        valid = False
        blockers: list[str] = []
        if len(raw) < 0x24 or raw[:8] != b"ITM V1  ":
            blockers.append("unsupported-itm-format")
        else:
            item_type = struct.unpack_from("<H", raw, 0x1C)[0]
            try:
                animation_code = raw_code.decode("ascii").upper()
            except UnicodeDecodeError:
                animation_code = ""
            valid = bool(re.fullmatch(r"[A-Z0-9]{2}", animation_code))
        layer = item_visual_layer(item_type) if item_type is not None else ""
        body_code = animation_code[0] if layer == "body" and animation_code[:1].isdigit() else ""
        if layer and not valid:
            blockers.append("visual-animation-code-invalid")
        if item_name in override_itms:
            blockers.append("item-override-collision")
        if layer in {"helmet", "shield", "weapon"} and valid:
            items_by_layer_code[(layer, animation_code)].append(item_name)
        items.append(
            {
                "item_resref": item_name,
                "item_type": item_type if item_type is not None else "",
                "item_type_symbol": item_categories.get(item_type, "") if item_type is not None else "",
                "visual_layer": layer,
                "animation_code_raw_hex": raw_code.hex().upper(),
                "animation_code": animation_code if valid else "",
                "animation_code_valid": yes_no(valid),
                "body_armor_code": body_code,
                "source_bif": bif_name.replace("\\", "/"),
                "locator": f"0x{entry[2]:08X}",
                "source_sha256": sha256_bytes(raw),
                "candidate_family_count": 0,
                "compatible_animation_count": 0,
                "compatible_animation_ids": "",
                "candidate_bam_prefixes": "",
                "resolved_bam_prefixes": "",
                "unresolved_bam_prefixes": "",
                "pipeline_ready_prefixes": "",
                "override_collision": yes_no(item_name in override_itms),
                "blocker": joined(blockers),
            }
        )

    families: list[dict[str, Any]] = []
    body_family_by_animation_code: dict[tuple[str, str], str] = {}
    for animation in animations:
        animation_id = int(animation["animation_id_decimal"])
        section = animation["engine_section"]
        config = sections_by_id[animation_id].get(section, {}) if section else {}
        prefix = animation["resref"]
        if not prefix:
            continue
        if section == "character":
            armor_max = safe_int(animation["armor_max_code"])
            if not armor_max or not 1 <= armor_max <= 9:
                continue
            for armor_code in range(1, armor_max + 1):
                body_resref = prefix
                armor_base = animation["resref_armor_base"]
                armor_specific = animation["resref_armor_specific"]
                if armor_code == armor_max and armor_specific:
                    if armor_base and body_resref.endswith(armor_base):
                        body_resref = body_resref[: -len(armor_base)] + armor_specific
                bam_prefix = f"{body_resref}{armor_code}"
                family = base_family(
                    animation, "body", "armor-code", str(armor_code), bam_prefix, "character-exact"
                )
                family["expected_suffixes"] = joined(CHARACTER_BODY_SUFFIXES)
                family["_resource_names"] = [
                    f"{bam_prefix}{suffix}"
                    for suffix in CHARACTER_BODY_SUFFIXES
                    if f"{bam_prefix}{suffix}" in bam_map
                ]
                families.append(family)
                body_family_by_animation_code[(animation["animation_id"], str(armor_code))] = family["family_id"]

            for (layer, code), item_names in sorted(items_by_layer_code.items()):
                height_key = {
                    "helmet": "height_code_helmet",
                    "shield": "height_code_shield",
                    "weapon": "height_code",
                }[layer]
                height = animation[height_key] or animation["height_code"]
                if not height:
                    continue
                bam_prefix = f"{height}{code}"
                family = base_family(
                    animation, layer, "item-animation-code", code, bam_prefix, "character-whitelist"
                )
                family["item_animation_code"] = code
                family["item_count"] = len(item_names)
                family["item_resrefs"] = joined(item_names)
                family["height_code"] = height
                equipment_suffixes = CHARACTER_EQUIPMENT_SUFFIXES_BY_LAYER[layer]
                family["expected_suffixes"] = joined(equipment_suffixes)
                family["_resource_names"] = [
                    f"{bam_prefix}{suffix}"
                    for suffix in equipment_suffixes
                    if f"{bam_prefix}{suffix}" in bam_map
                ]
                families.append(family)
        else:
            family = base_family(
                animation, "body", "base-resref", prefix, prefix, "stock-prefix"
            )
            family["_resource_names"] = sorted(name for name in bam_map if name.startswith(prefix))
            families.append(family)

    referenced = sorted({name for family in families for name in family["_resource_names"]})
    print(f"Decoding {len(referenced)} sprite BAM resources...", flush=True)
    stats_by_name: dict[str, dict[str, Any]] = {}
    for position, name in enumerate(referenced, 1):
        stats_by_name[name] = bam_stats(index, bam_map[name])
        if position % 250 == 0 or position == len(referenced):
            print(f"  {position}/{len(referenced)}", flush=True)

    resource_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for family in families:
        prefix = family["bam_prefix"]
        names: list[str] = family.pop("_resource_names")
        suffixes = [name[len(prefix) :] for name in names]
        family["suffixes_present"] = joined(suffixes)
        expected = set(filter(None, family["expected_suffixes"].split(";")))
        present = set(suffixes)
        missing = expected - present if family["discovery_rule"] == "character-exact" else set()
        unexpected = set()
        paperdolls = {name for name in bam_map if name == f"{prefix}INV"}
        if family["discovery_rule"] == "character-whitelist":
            unexpected = {
                name[len(prefix) :]
                for name in bam_map
                if name.startswith(prefix)
                and name not in names
                and name not in paperdolls
            }
        family["missing_suffixes"] = joined(missing)
        family["unexpected_suffixes"] = joined(unexpected)
        family["paperdoll_resources"] = joined(paperdolls)
        family["resource_count"] = len(names)
        decoded = [stats_by_name[name] for name in names]
        family["frame_count"] = sum(
            int(item["frame_count"]) for item in decoded if item["decode_status"] == "ok"
        )
        family["cycle_count"] = sum(
            int(item["cycle_count"]) for item in decoded if item["decode_status"] == "ok"
        )
        registry_bytes = 24 + sum(
            int(item["registry_resource_estimated_bytes"])
            for item in decoded
            if item["decode_status"] == "ok"
        )
        family["registry_estimated_bytes"] = registry_bytes
        family["registry_estimated_mib"] = f"{registry_bytes / (1024 * 1024):.3f}"
        resource_limit = 1 <= len(names) <= MAX_RESOURCES
        frame_limit = all(
            item["decode_status"] == "ok"
            and 1 <= int(item["frame_count"]) <= MAX_FRAMES_PER_RESOURCE
            for item in decoded
        ) and bool(decoded)
        registry_limit = False
        family_partitions: list[list[dict[str, Any]]] = []
        try:
            family_partitions = partition_registry_resources(
                [
                    {
                        "resref": str(item["bam_resref"]),
                        "bytes": int(item["registry_resource_estimated_bytes"]),
                    }
                    for item in decoded
                    if item["decode_status"] == "ok"
                ],
                maximum_bytes=MAX_REGISTRY_BYTES,
            )
            projected_set_bytes = sum(
                REGISTRY_HEADER_BYTES
                + sum(int(record["bytes"]) for record in partition)
                for partition in family_partitions
            )
            registry_limit = (
                frame_limit
                and len(names) <= MAX_REGISTRY_SET_RESOURCES
                and family["frame_count"] <= MAX_REGISTRY_SET_FRAMES
                and projected_set_bytes <= MAX_REGISTRY_SET_BYTES
            )
        except (RuntimeError, TypeError, ValueError):
            registry_limit = False
        family["required_job_contract"] = (
            "unavailable"
            if not family_partitions
            else "explicit-xn"
            if len(family_partitions) > 1
            else "legacy-or-explicit-xn"
        )
        family["registry_layout_x2"] = (
            "set" if len(family_partitions) > 1 else "monolith"
        ) if family_partitions else "unavailable"
        family["shard_count_x2"] = len(family_partitions)
        suffixes_supported = not missing and not unexpected and bool(names)
        duplicate_frames = sum(
            int(item["duplicate_used_rgba_frames"] or 0) for item in decoded
        )
        examples = []
        for item in decoded:
            if item["duplicate_used_rgba_examples"]:
                examples.extend(
                    f"{item['bam_resref']}:{value}"
                    for value in item["duplicate_used_rgba_examples"].split(";")
                )
        collisions = sorted(set(names) & override_bams)
        blockers: list[str] = []
        if not family.pop("_runtime_supported"):
            blockers.append("runtime-profile-unsupported")
        if not names:
            blockers.append("no-bam-resources")
        if missing:
            blockers.append("missing-required-suffixes")
        if unexpected:
            blockers.append("unexpected-character-suffixes")
        if any(item["decode_status"] != "ok" for item in decoded):
            blockers.append("bam-decode-error")
        # Distinct used indices with identical RGBA remain diagnostic data.
        # The xBR runner now carries source-index provenance for those frames,
        # so the engine can still apply independent dynamic palette entries.
        if not resource_limit:
            blockers.append("resource-limit")
        if not frame_limit:
            blockers.append("per-resource-frame-limit")
        if not registry_limit:
            blockers.append("registry-size-limit")
        if collisions:
            blockers.append("bam-override-collision")
        family["resource_limit_pass"] = yes_no(resource_limit)
        family["frame_limit_pass"] = yes_no(frame_limit)
        family["registry_limit_pass"] = yes_no(registry_limit)
        family["suffixes_supported"] = yes_no(suffixes_supported)
        family["duplicate_used_rgba_frames"] = duplicate_frames
        family["duplicate_used_rgba_examples"] = joined(examples[:24])
        family["runtime_profile"] = family.pop("_runtime_profile")
        family["runtime_supported"] = yes_no("runtime-profile-unsupported" not in blockers)
        family["pipeline_ready"] = yes_no(not blockers)
        family["override_collision"] = joined(collisions)
        family["blocker"] = joined(blockers)
        for name in names:
            resource_links[name].append(family)

    families.sort(key=lambda row: row["family_id"])
    family_by_id = {row["family_id"]: row for row in families}
    family_ids_by_animation: dict[str, list[str]] = defaultdict(list)
    ready_by_animation: dict[str, list[str]] = defaultdict(list)
    for family in families:
        family_ids_by_animation[family["animation_id"]].append(family["family_id"])
        if family["pipeline_ready"] == "yes":
            ready_by_animation[family["animation_id"]].append(family["family_id"])
    for animation in animations:
        aid = animation["animation_id"]
        animation["family_count"] = len(family_ids_by_animation[aid])
        animation["pipeline_ready_family_count"] = len(ready_by_animation[aid])

    item_links: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for family in families:
        for item_name in filter(None, family["item_resrefs"].split(";")):
            item_links[item_name].append(family)
    for item in items:
        if item["visual_layer"] == "body" and item["body_armor_code"]:
            for animation in animations:
                key = (animation["animation_id"], item["body_armor_code"])
                target = body_family_by_animation_code.get(key)
                if target:
                    item_links[item["item_resref"]].append(family_by_id[target])
        links = item_links[item["item_resref"]]
        ids = {family["animation_id"] for family in links}
        prefixes = {family["bam_prefix"] for family in links}
        resolved = {family["bam_prefix"] for family in links if family["resource_count"]}
        ready = {family["bam_prefix"] for family in links if family["pipeline_ready"] == "yes"}
        item["candidate_family_count"] = len(links)
        item["compatible_animation_count"] = len(ids)
        item["compatible_animation_ids"] = joined(ids)
        item["candidate_bam_prefixes"] = joined(prefixes)
        item["resolved_bam_prefixes"] = joined(resolved)
        item["unresolved_bam_prefixes"] = joined(prefixes - resolved)
        item["pipeline_ready_prefixes"] = joined(ready)
        blockers = set(filter(None, item["blocker"].split(";")))
        if item["visual_layer"] and not links:
            blockers.add("no-compatible-character-family")
        if links and not ready:
            blockers.add("no-pipeline-ready-family")
        item["blocker"] = joined(blockers)

    resources: list[dict[str, Any]] = []
    for name in referenced:
        row = dict(stats_by_name[name])
        links = resource_links[name]
        prefixes = {family["bam_prefix"] for family in links}
        row["family_count"] = len(links)
        row["family_ids"] = joined(family["family_id"] for family in links)
        row["animation_ids"] = joined(family["animation_id"] for family in links)
        row["layer_kinds"] = joined(family["layer_kind"] for family in links)
        row["bam_prefixes"] = joined(prefixes)
        row["bam_suffixes"] = joined(name[len(prefix) :] for prefix in prefixes)
        row["runtime_relevant"] = yes_no(any(family["runtime_supported"] == "yes" for family in links))
        row["override_collision"] = yes_no(name in override_bams)
        blockers: list[str] = []
        if row["decode_status"] != "ok":
            blockers.append("bam-decode-error")
        # See the family-level rule above: duplicate RGBA indices are
        # preserved by source-index provenance and do not block the pipeline.
        if row["decode_status"] == "ok" and int(row["frame_count"]) > MAX_FRAMES_PER_RESOURCE:
            blockers.append("per-resource-frame-limit")
        if name in override_bams:
            blockers.append("bam-override-collision")
        row["blocker"] = joined(blockers)
        resources.append(row)

    stock_cre_usage = build_stock_cre_usage(index, animations, families)
    return animations, families, resources, items, index.resources, stock_cre_usage


def verify_inventory(
    animations: list[dict[str, Any]],
    families: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    items: list[dict[str, Any]],
) -> None:
    def require_unique(rows: list[dict[str, Any]], key: str) -> set[str]:
        values = [str(row[key]) for row in rows]
        if len(values) != len(set(values)):
            raise RuntimeError(f"duplicate {key} in generated inventory")
        return set(values)

    animation_ids = require_unique(animations, "animation_id")
    family_ids = require_unique(families, "family_id")
    resource_ids = require_unique(resources, "bam_resref")
    require_unique(items, "item_resref")
    if any(family["animation_id"] not in animation_ids for family in families):
        raise RuntimeError("family references an unknown animation")
    for resource in resources:
        linked = set(filter(None, resource["family_ids"].split(";")))
        if not linked or not linked <= family_ids:
            raise RuntimeError(f"invalid family links for {resource['bam_resref']}")
    if any(not resource["family_ids"] for resource in resources):
        raise RuntimeError("resource/family relation is not closed")
    for fields, rows in (
        (ANIMATION_FIELDS, animations),
        (FAMILY_FIELDS, families),
        (RESOURCE_FIELDS, resources),
        (ITEM_FIELDS, items),
    ):
        missing = set(fields) - set(rows[0]) if rows else set(fields)
        if missing:
            raise RuntimeError(f"generated rows miss columns: {joined(missing)}")


def write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, default=DEFAULT_GAME_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    game_root = args.game_root.resolve()
    output_dir = args.output_dir.resolve()
    if not (game_root / "chitin.key").is_file():
        raise SystemExit(f"missing chitin.key: {game_root}")
    if output_dir == game_root or game_root in output_dir.parents:
        raise SystemExit("output directory must stay outside the game directory")

    (
        animations,
        families,
        resources,
        items,
        key_resources,
        stock_cre_usage,
    ) = build_inventory(game_root)
    verify_inventory(animations, families, resources, items)
    output_dir.mkdir(parents=True, exist_ok=True)
    outputs = {
        "sprite_animations.csv": (ANIMATION_FIELDS, animations),
        "sprite_families.csv": (FAMILY_FIELDS, families),
        "sprite_resources.csv": (RESOURCE_FIELDS, resources),
        "sprite_items.csv": (ITEM_FIELDS, items),
    }
    for name, (fields, rows) in outputs.items():
        write_csv(output_dir / name, fields, rows)

    manifest = {
        "schema": SCHEMA,
        "status": "generated-verified-read-only-source",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "game_root": str(game_root),
        "chitin_key_sha256": sha256_file(game_root / "chitin.key"),
        "baldur_real_sha256": sha256_file(game_root / "BaldurReal.exe")
        if (game_root / "BaldurReal.exe").is_file()
        else "",
        "source_policy": "stock KEY/BIF data; override filenames are collision signals only",
        "limits": {
            "max_resources_per_registry": MAX_RESOURCES,
            "max_frames_per_resource": MAX_FRAMES_PER_RESOURCE,
            "max_registry_bytes": MAX_REGISTRY_BYTES,
            "max_lazy_frame_index_bytes": MAX_LAZY_FRAME_INDEX_BYTES,
            "xbr_output_batch_budget_bytes": XBR_OUTPUT_BATCH_BUDGET_BYTES,
            "max_registry_bytes_by_scale": {
                str(scale): byte_limit
                for scale, byte_limit in sorted(MAX_REGISTRY_BYTES_BY_SCALE.items())
            },
            "max_shards_per_registry_set": MAX_REGISTRY_SET_SHARDS,
            "max_resources_per_registry_set": MAX_REGISTRY_SET_RESOURCES,
            "max_frames_per_registry_set": MAX_REGISTRY_SET_FRAMES,
            "max_registry_set_bytes": MAX_REGISTRY_SET_BYTES,
        },
        "registry_contracts": {
            "resource_cost_column": {
                "field": "registry_resource_estimated_bytes",
                "scale": 2,
                "format": "IEECSX2/v2",
                "projection_formula": (
                    "48 + frame_count*528 + native_pixel_count*scale^2 + "
                    "cycle_count*4 + cycle_slot_count*4"
                ),
                "projection_scales": [2, 4],
            },
            "explicit_xn": {
                "magic": XN_REGISTRY_MAGIC.rstrip(b"\0").decode("ascii"),
                "version": XN_REGISTRY_VERSION,
                "supported_scales": [2, 4],
            },
            "registry_set": {
                "magic": XN_REGISTRY_SET_MAGIC.rstrip(b"\0").decode("ascii"),
                "version": XN_REGISTRY_SET_VERSION,
                "member_magic": XN_REGISTRY_MAGIC.rstrip(b"\0").decode("ascii"),
                "partition": "deterministic-greedy-at-resource-boundaries",
                "shard_byte_limit": "scale-indexed-x2-128MiB-x4-512MiB",
                "checksums": ["sha256", "crc32"],
                "runtime_priority": ["registry-set", "xn-monolith", "legacy-monolith"],
                "invalid_present_set_policy": "fail-closed-no-monolith-fallback",
                "prepare_validation": "all-shards-before-ready",
                "payload_loading": "frame-indices-lazy-bounded-lru",
                "aggregate_size_definition": "sum-of-member-registry-bytes",
                "member_header_bytes": REGISTRY_HEADER_BYTES,
            },
        },
        "registry_set_projections": build_registry_set_projections(resources),
        "stock_cre_usage": stock_cre_usage,
        "counts": {
            "key_resources": len(key_resources),
            "animations": len(animations),
            "animations_with_ini": sum(row["ini_present"] == "yes" for row in animations),
            "runtime_supported_animations": sum(row["runtime_supported"] == "yes" for row in animations),
            "families": len(families),
            "runtime_supported_families": sum(row["runtime_supported"] == "yes" for row in families),
            "pipeline_ready_families": sum(row["pipeline_ready"] == "yes" for row in families),
            "sprite_bam_resources": len(resources),
            "sprite_bams_with_duplicate_used_rgba": sum(int(row["duplicate_used_rgba_frames"] or 0) > 0 for row in resources),
            "items": len(items),
            "visual_items": sum(bool(row["visual_layer"]) for row in items),
        },
        "files": {},
    }
    for name in outputs:
        path = output_dir / name
        manifest["files"][name] = {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
    manifest_path = output_dir / "manifest.json"
    temporary = manifest_path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(manifest_path)
    print(json.dumps(manifest["counts"], ensure_ascii=False, indent=2))
    print(f"Inventory written to {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
