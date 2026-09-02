"""Build immutable 30 fps TimedTimeline packs beside the legacy x4 pipeline.

V1 remains the spatial-upscale authority. This V2 consumes a completed V1 run
and an immutable active runtime pack, interpolates each selected BAM cycle on
the common aligned canvas, then writes a registry-v3 pack. It never edits the
game, the source run, the base pack, the DLL, INI files, or catalogues.
"""

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
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops, ImageStat

import animation_paths
import build_animation_runtime_pack as runtime_v1
from workspace_paths import get_path


RUN_SCHEMA = "bg2-upscale-area-animation-30fps-run-v2"
PACK_SCHEMA = "bg2-upscale-area-animation-runtime-pack-v2"
PLAN_SCHEMA = "bg2-upscale-area-animation-30fps-plan-v2"
CYCLE_SCHEMA = "bg2-upscale-area-animation-30fps-cycle-v2"
APPROVAL_SCHEMA = "bg2-upscale-area-animation-30fps-approval-v2"
REGISTRY_MAGIC = b"IEEAAX4\0"
LEGACY_REGISTRY_VERSION = 2
REGISTRY_VERSION = 3
SUPPORTED_REGISTRY_VERSIONS = {LEGACY_REGISTRY_VERSION, REGISTRY_VERSION}
REGISTRY_NAME = "AreaAnimations-X4.registry"
MAX_RESOURCES = 512
MAX_FRAMES_PER_RESOURCE = 4096
MAX_CYCLES_PER_RESOURCE = 256
MAX_CYCLE_SLOTS = 65536
MAX_LOGICAL_DIMENSION = 8192
MAX_RAW_BYTES = 512 * 1024 * 1024
NATIVE_FPS = (15, 1)
TARGET_FPS = (30, 1)
DEFAULT_TVAI_FFMPEG = get_path("topaz_video_ffmpeg")
DEFAULT_TVAI_MODEL_DIR = get_path("topaz_video_models")
DEFAULT_MODEL = "apo-8"
DEFAULT_DEVICE = "-2"
TRANSPARENT_RGB_MODES = (
    "preserve-hidden-rgb",
    "nearest-opaque-dilate",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_json(payload: Any) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"manifeste absent : {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".part")
    temporary.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    temporary.replace(path)


def normalise_resref(value: str) -> str:
    result = value.strip().upper()
    require(result.isascii() and 1 <= len(result) <= 8 and any(c.isalnum() for c in result)
            and all(c.isalnum() or c == "_" for c in result),
            f"resref invalide : {value}")
    return result


def safe_relative(root: Path, value: str) -> Path:
    path = (root / value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise RuntimeError(f"chemin hors racine : {value}") from exc
    return path


def image_mae(left: Image.Image, right: Image.Image) -> float:
    require(left.mode == right.mode and left.size == right.size,
            "comparaison d'images incompatibles")
    difference = ImageChops.difference(left, right)
    return sum(ImageStat.Stat(difference).mean) / len(difference.getbands())


def asset_name(resref: str, frame_index: int, variant_index: int = 0) -> str:
    require(0 <= variant_index < MAX_RESOURCES,
            f"{resref}: index de variante invalide ({variant_index})")
    suffix = "" if variant_index == 0 else f"-v{variant_index}"
    return f"AAX4-{resref}{suffix}-frame{frame_index:03d}.rgba"


def resource_position(resource: dict[str, Any]) -> tuple[int, int] | None:
    value = resource.get("position")
    if value is None:
        return None
    require(isinstance(value, (list, tuple)) and len(value) == 2,
            f"{resource.get('resref', '?')}: position monde invalide")
    require(all(isinstance(component, int) and not isinstance(component, bool)
                for component in value),
            f"{resource.get('resref', '?')}: coordonnées monde non entières")
    x, y = value
    require(-(2 ** 31) <= x < 2 ** 31 and -(2 ** 31) <= y < 2 ** 31,
            f"{resource.get('resref', '?')}: position monde hors int32")
    return x, y


def resource_variant_index(resource: dict[str, Any]) -> int:
    value = resource.get("variant_index", 0)
    require(isinstance(value, int) and not isinstance(value, bool),
            f"{resource.get('resref', '?')}: index de variante non entier")
    require(0 <= value < MAX_RESOURCES,
            f"{resource.get('resref', '?')}: index de variante invalide ({value})")
    return value


def resource_sort_key(resource: dict[str, Any]) -> tuple[str, int]:
    return normalise_resref(str(resource.get("resref", ""))), resource_variant_index(resource)


def rate_record(rate: tuple[int, int]) -> dict[str, int]:
    return {"numerator": rate[0], "denominator": rate[1]}


def rate_tuple(value: Any) -> tuple[int, int]:
    require(isinstance(value, dict), "cadence rationnelle absente")
    numerator = int(value.get("numerator", 0))
    denominator = int(value.get("denominator", 0))
    require(0 < numerator <= 1000 and 0 < denominator <= 1000,
            "cadence rationnelle invalide")
    return numerator, denominator


def normalise_v1_resource(resource: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(resource)
    result["playback_mode"] = "Native"
    result["native_fps"] = {"numerator": 0, "denominator": 0}
    result["target_fps"] = {"numerator": 0, "denominator": 0}
    result["cycles"] = [
        {
            "cycle": int(cycle["cycle"]),
            "native_frame_indices": [int(value) for value in cycle["frame_indices"]],
            "timeline_frame_indices": [],
        }
        for cycle in resource["cycles"]
    ]
    return result


def resource_binary_v2(resource: dict[str, Any],
                       registry_version: int = REGISTRY_VERSION) -> bytes:
    require(registry_version in SUPPORTED_REGISTRY_VERSIONS,
            f"version de registre non prise en charge : {registry_version}")
    resref = normalise_resref(str(resource.get("resref", "")))
    position = resource_position(resource)
    variant_index = resource_variant_index(resource)
    if registry_version == LEGACY_REGISTRY_VERSION:
        require(position is None and variant_index == 0,
                f"{resref}: position/variante interdite dans un registre v2")
    encoded = resref.encode("ascii").ljust(8, b"\0")
    frames = sorted(resource.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    frame_count = int(resource.get("frame_count", 0))
    require(0 < frame_count <= MAX_FRAMES_PER_RESOURCE and len(frames) == frame_count and
            [int(frame.get("frame", -1)) for frame in frames] == list(range(frame_count)),
            f"{resref}: frames runtime non contiguës")
    cycles = sorted(resource.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    require(cycles and len(cycles) <= MAX_CYCLES_PER_RESOURCE and
            int(resource.get("cycle_count", -1)) == len(cycles) and
            [int(cycle.get("cycle", -1)) for cycle in cycles] == list(range(len(cycles))),
            f"{resref}: cycles runtime non contigus")

    mode_name = str(resource.get("playback_mode", ""))
    require(mode_name in ("Native", "TimedTimeline"), f"{resref}: mode playback invalide")
    mode = 0 if mode_name == "Native" else 1
    if mode == 0:
        native_rate = (0, 0)
        target_rate = (0, 0)
        require(resource.get("native_fps") == {"numerator": 0, "denominator": 0} and
                resource.get("target_fps") == {"numerator": 0, "denominator": 0},
                f"{resref}: une ressource Native ne porte pas de cadence")
    else:
        native_rate = rate_tuple(resource.get("native_fps"))
        target_rate = rate_tuple(resource.get("target_fps"))

    binary = bytearray(encoded)
    binary.extend(struct.pack("<II", frame_count, len(cycles)))
    binary.extend(struct.pack("<IIIII", mode, native_rate[0], native_rate[1],
                              target_rate[0], target_rate[1]))
    if registry_version == REGISTRY_VERSION:
        world_x, world_y = position or (0, 0)
        binary.extend(struct.pack("<IiiI", int(position is not None), world_x, world_y,
                                  variant_index))
    expected_assets: list[tuple[str, str, int]] = []
    for index, frame in enumerate(frames):
        logical = [int(value) for value in frame.get("logical_size_x1") or []]
        physical = [int(value) for value in frame.get("physical_size_x4") or []]
        require(len(logical) == 2 and len(physical) == 2 and
                0 < logical[0] <= MAX_LOGICAL_DIMENSION and
                0 < logical[1] <= MAX_LOGICAL_DIMENSION and
                physical == [logical[0] * 4, logical[1] * 4],
                f"{resref} frame {index}: géométrie runtime invalide")
        name = str(frame.get("asset", ""))
        digest = str(frame.get("sha256", "")).lower()
        size = physical[0] * physical[1] * 4
        require(name == asset_name(resref, index, variant_index) and
                int(frame.get("bytes", -1)) == size and
                len(digest) == 64 and all(char in "0123456789abcdef" for char in digest),
                f"{resref} frame {index}: inventaire runtime invalide")
        binary.extend(struct.pack("<II", *logical))
        expected_assets.append((name, digest, size))
    actual_assets = sorted(
        (str(item.get("name", "")), str(item.get("sha256", "")).lower(),
         int(item.get("bytes", -1))) for item in resource.get("assets") or []
    )
    require(sorted(expected_assets) == actual_assets,
            f"{resref}: inventaire frames/assets divergent")

    for cycle in cycles:
        native = [int(value) for value in cycle.get("native_frame_indices") or []]
        timeline = [int(value) for value in cycle.get("timeline_frame_indices") or []]
        require(native and len(native) <= MAX_CYCLE_SLOTS and
                all(0 <= value < frame_count for value in native),
                f"{resref}: cycle natif invalide")
        if mode == 0:
            require(not timeline, f"{resref}: timeline présente en mode Native")
        else:
            require(timeline and len(timeline) <= MAX_CYCLE_SLOTS and
                    all(0 <= value < frame_count for value in timeline),
                    f"{resref}: timeline invalide")
            left = len(timeline) * native_rate[0] * target_rate[1]
            right = len(native) * target_rate[0] * native_rate[1]
            require(left == right, f"{resref}: durée native/timeline divergente")
        binary.extend(struct.pack("<I", len(native)))
        binary.extend(struct.pack(f"<{len(native)}I", *native))
        binary.extend(struct.pack("<I", len(timeline)))
        if timeline:
            binary.extend(struct.pack(f"<{len(timeline)}I", *timeline))
    return bytes(binary)


def registry_v2_from_resources(resources: list[dict[str, Any]],
                               registry_version: int = REGISTRY_VERSION) -> bytes:
    require(registry_version in SUPPORTED_REGISTRY_VERSIONS,
            f"version de registre non prise en charge : {registry_version}")
    ordered = sorted(resources, key=resource_sort_key)
    resrefs = [normalise_resref(str(resource["resref"])) for resource in ordered]
    require(resrefs and len(resrefs) <= MAX_RESOURCES, "nombre de ressources invalide")
    if registry_version == LEGACY_REGISTRY_VERSION:
        require(len(resrefs) == len(set(resrefs)), "resref dupliqué dans le registre v2")
    else:
        seen_variants: set[tuple[str, int]] = set()
        seen_positions: set[tuple[str, tuple[int, int] | None]] = set()
        for resource in ordered:
            resref = normalise_resref(str(resource["resref"]))
            variant = resource_variant_index(resource)
            position = resource_position(resource)
            require((resref, variant) not in seen_variants,
                    f"{resref}: index de variante dupliqué ({variant})")
            require((resref, position) not in seen_positions,
                    f"{resref}: position de variante dupliquée ({position})")
            seen_variants.add((resref, variant))
            seen_positions.add((resref, position))
    registry = bytearray(REGISTRY_MAGIC)
    registry.extend(struct.pack("<IIII", registry_version, 4, len(ordered), 0))
    for resource in ordered:
        registry.extend(resource_binary_v2(resource, registry_version))
    return bytes(registry)


def validate_v2_pack(pack_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    pack_root = pack_root.resolve()
    manifest = load_json(pack_root / "manifest.json")
    registry_version = int(manifest.get("registry_version", 0))
    require(manifest.get("schema") == PACK_SCHEMA and manifest.get("status") == "completed" and
            int(manifest.get("scale", 0)) == 4 and
            registry_version in SUPPORTED_REGISTRY_VERSIONS,
            f"pack runtime v2 incompatible : {pack_root}")
    resources = sorted(manifest.get("resources") or [], key=resource_sort_key)
    require(resources and int(manifest.get("resource_count", 0)) == len(resources) and
            int(manifest.get("frame_count", 0)) == sum(int(item["frame_count"]) for item in resources),
            f"inventaire runtime v2 invalide : {pack_root}")
    # MAX_RAW_BYTES is what the runtime loads at once. A pack that declares itself an
    # authoring pack is never loaded whole: it exists only to be split per area by
    # split_animation_pack_by_area.py, and each area pack it yields is budget-checked
    # normally. The exemption is therefore recorded in the pack itself, never implied,
    # and the installer refuses any pack still carrying it.
    budget_enforced = bool(manifest.get("runtime_budget_enforced", True))
    raw_bytes = sum(int(asset["bytes"]) for resource in resources for asset in resource["assets"])
    require(budget_enforced or manifest.get("authoring_pack_for_area_split") is True,
            f"exemption de budget sans déclaration d'usage : {pack_root}")
    require(not budget_enforced or raw_bytes <= MAX_RAW_BYTES,
            f"pack runtime v2 au-delà de la limite mémoire : {pack_root}")
    registry = registry_v2_from_resources(resources, registry_version)
    registry_path = pack_root / REGISTRY_NAME
    require(registry_path.is_file() and registry_path.read_bytes() == registry and
            int(manifest.get("registry_bytes", -1)) == len(registry) and
            str(manifest.get("registry_sha256", "")).lower() == sha256_file(registry_path),
            f"registre runtime v2 incohérent : {registry_path}")
    expected_names = {"manifest.json", REGISTRY_NAME}
    for resource in resources:
        resource_binary_v2(resource, registry_version)
        for asset in resource["assets"]:
            name = str(asset["name"])
            path = pack_root / name
            require(Path(name).name == name and name not in expected_names and path.is_file() and
                    path.stat().st_size == int(asset["bytes"]) and
                    sha256_file(path) == str(asset["sha256"]).lower(),
                    f"asset runtime v2 incohérent : {path}")
            expected_names.add(name)
    actual_names = {item.name for item in pack_root.iterdir() if item.is_file()}
    extra_directories = {item.name for item in pack_root.iterdir() if item.is_dir()}
    require(actual_names == expected_names and extra_directories <= {"install-backups"},
            f"contenu supplémentaire ou manquant dans le pack v2 : {pack_root}")
    return manifest, resources


def validate_v1_base_pack(pack_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Validate V1 runtime payloads while tolerating installer-owned backups.

    Historical install scripts stored their reversible backups below the source pack.
    Those backups are not part of the pack payload.  The registry, manifest and every
    declared RGBA asset remain byte-for-byte validated here.
    """
    manifest = load_json(pack_root / "manifest.json")
    require(manifest.get("schema") == runtime_v1.PACK_SCHEMA and
            manifest.get("status") == "completed" and int(manifest.get("scale", 0)) == 4,
            f"pack runtime v1 incompatible : {pack_root}")
    resources = sorted(manifest.get("resources") or [], key=lambda item: str(item.get("resref", "")))
    require(resources and int(manifest.get("resource_count", 0)) == len(resources) and
            int(manifest.get("frame_count", 0)) == sum(int(item["frame_count"]) for item in resources),
            f"inventaire runtime v1 invalide : {pack_root}")
    require(len(resources) <= MAX_RESOURCES and
            sum(int(asset["bytes"]) for resource in resources for asset in resource["assets"])
            <= MAX_RAW_BYTES, f"pack runtime v1 au-delà des limites moteur : {pack_root}")
    expected_registry = runtime_v1.registry_from_resources(resources)
    registry_path = pack_root / REGISTRY_NAME
    require(registry_path.is_file() and registry_path.read_bytes() == expected_registry and
            int(manifest.get("registry_bytes", -1)) == len(expected_registry) and
            str(manifest.get("registry_sha256", "")).lower() == sha256_file(registry_path),
            f"registre runtime v1 incohérent : {registry_path}")
    expected_names = {"manifest.json", REGISTRY_NAME}
    for resource in resources:
        runtime_v1.resource_binary_from_manifest(resource)
        for asset in resource["assets"]:
            name = str(asset["name"])
            path = pack_root / name
            require(Path(name).name == name and name not in expected_names and path.is_file() and
                    path.stat().st_size == int(asset["bytes"]) and
                    sha256_file(path) == str(asset["sha256"]).lower(),
                    f"asset runtime v1 incohérent : {path}")
            expected_names.add(name)
    actual_names = {item.name for item in pack_root.iterdir() if item.is_file()}
    extra_directories = {item.name for item in pack_root.iterdir() if item.is_dir()}
    require(actual_names == expected_names and extra_directories <= {"install-backups"},
            f"contenu supplémentaire ou manquant dans le pack v1 : {pack_root}")
    return manifest, resources


def load_base_pack(pack_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Path]]:
    pack_root = pack_root.resolve()
    manifest = load_json(pack_root / "manifest.json")
    if manifest.get("schema") == runtime_v1.PACK_SCHEMA:
        manifest, raw_resources = validate_v1_base_pack(pack_root)
        resources = [normalise_v1_resource(resource) for resource in raw_resources]
    elif manifest.get("schema") == PACK_SCHEMA:
        manifest, resources = validate_v2_pack(pack_root)
        resources = copy.deepcopy(resources)
    else:
        raise RuntimeError(f"schéma de pack de base incompatible : {pack_root}")
    sources = {
        str(asset["name"]): pack_root / str(asset["name"])
        for resource in resources for asset in resource["assets"]
    }
    return manifest, resources, sources


def load_source_context(source_run: Path, resref: str) -> dict[str, Any]:
    source_run = source_run.resolve()
    run_manifest = load_json(source_run / "manifest.json")
    require(run_manifest.get("schema") == runtime_v1.RUN_SCHEMA and
            run_manifest.get("status") == "completed" and
            int((run_manifest.get("request") or {}).get("scale", 0)) == 4,
            f"run spatial V1 incomplet ou incompatible : {source_run}")
    matches = [item for item in run_manifest.get("resources") or []
               if normalise_resref(str(item.get("resref", ""))) == resref]
    require(len(matches) == 1 and matches[0].get("status") == "completed",
            f"{resref}: ressource spatiale V1 absente ou incomplète")
    record = matches[0]
    frames_root = safe_relative(source_run, str(record["frames_x1"]))
    upscale_root = safe_relative(source_run, str(record["upscale"]))
    frame_manifest_path = frames_root / "manifest.json"
    upscale_manifest_path = upscale_root / "manifest.json"
    frame_manifest = load_json(frame_manifest_path)
    upscale_manifest = load_json(upscale_manifest_path)
    require(frame_manifest.get("schema") == runtime_v1.FRAME_SCHEMA and
            upscale_manifest.get("schema") == runtime_v1.UPSCALE_SCHEMA and
            upscale_manifest.get("status") == "completed" and
            int(upscale_manifest.get("scale", 0)) == 4,
            f"{resref}: manifests spatial V1 invalides")
    frames = sorted(upscale_manifest.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    frame_count = int(frame_manifest.get("frame_count", 0))
    require(frame_count > 0 and len(frames) == frame_count and
            [int(frame.get("frame", -1)) for frame in frames] == list(range(frame_count)),
            f"{resref}: frames V1 non contiguës")
    aligned_x1 = [int(value) for value in upscale_manifest.get("aligned_canvas_size_x1") or []]
    require(len(aligned_x1) == 2 and aligned_x1[0] > 0 and aligned_x1[1] > 0,
            f"{resref}: canvas aligné absent")
    aligned_x4 = [aligned_x1[0] * 4, aligned_x1[1] * 4]
    validated_frames = []
    for index, frame in enumerate(frames):
        logical = [int(value) for value in frame.get("logical_size_x1") or []]
        physical = [int(value) for value in frame.get("physical_size_xn") or []]
        crop = [int(value) for value in frame.get("runtime_crop_box_xn") or []]
        require(len(logical) == 2 and physical == [logical[0] * 4, logical[1] * 4] and
                len(crop) == 4 and crop[2] - crop[0] == physical[0] and
                crop[3] - crop[1] == physical[1] and 0 <= crop[0] < crop[2] <= aligned_x4[0] and
                0 <= crop[1] < crop[3] <= aligned_x4[1],
                f"{resref} frame {index}: géométrie/crop V1 invalide")
        aligned_path = safe_relative(upscale_root, str(frame["aligned_rgba_xn"]))
        rgb_path = safe_relative(upscale_root, str(frame["rgb_xn"]))
        require(aligned_path.is_file() and rgb_path.is_file() and
                sha256_file(aligned_path) == str(frame["aligned_rgba_xn_sha256"]) and
                sha256_file(rgb_path) == str(frame["rgb_xn_sha256"]),
                f"{resref} frame {index}: PNG V1 modifié")
        with Image.open(aligned_path) as aligned, Image.open(rgb_path) as rgb:
            require(aligned.size == tuple(aligned_x4) and rgb.size == tuple(physical),
                    f"{resref} frame {index}: dimensions PNG V1 invalides")
        validated_frames.append({
            "frame": index,
            "logical_size_x1": logical,
            "physical_size_x4": physical,
            "centre_x1": frame.get("centre_x1"),
            "crop_box_x4": crop,
            "aligned_rgba": aligned_path,
            "aligned_rgba_sha256": str(frame["aligned_rgba_xn_sha256"]),
            "rgb": rgb_path,
            "rgb_sha256": str(frame["rgb_xn_sha256"]),
        })
    cycles = sorted(frame_manifest.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    require(cycles and [int(cycle.get("cycle", -1)) for cycle in cycles] == list(range(len(cycles))),
            f"{resref}: cycles V1 non contigus")
    lookups = []
    for cycle in cycles:
        lookup = [int(value) for value in cycle.get("frame_indices") or []]
        require(lookup and all(0 <= value < frame_count for value in lookup),
                f"{resref}: lookup V1 invalide")
        lookups.append(lookup)
    return {
        "input_mode": "spatial-v1",
        "resref": resref,
        "source_run": source_run,
        "run_manifest_sha256": sha256_file(source_run / "manifest.json"),
        "frame_manifest_sha256": sha256_file(frame_manifest_path),
        "upscale_manifest_sha256": sha256_file(upscale_manifest_path),
        "aligned_size_x4": aligned_x4,
        "geometry_mode": frame_manifest.get("geometry_mode"),
        "frames": validated_frames,
        "cycles": lookups,
    }


def load_runtime_uniform_context(base_pack: Path, resource: dict[str, Any]) -> dict[str, Any]:
    """Use a completed uniform 15 fps runtime resource as V2's interpolation source.

    This is for legacy resources whose native 15 fps stream was already expanded
    before V2 existed.  It deliberately refuses variable geometry: without the
    original aligned canvas/crop manifests, fabricating a shared canvas would make
    frame placement ambiguous.
    """
    base_pack = base_pack.resolve()
    resref = normalise_resref(str(resource.get("resref", "")))
    require(resource.get("playback_mode") == "Native",
            f"{resref}: déjà TimedTimeline dans le pack de base")
    frames = sorted(resource.get("frames") or [], key=lambda item: int(item.get("frame", -1)))
    frame_count = int(resource.get("frame_count", 0))
    require(0 < frame_count == len(frames) and
            [int(frame.get("frame", -1)) for frame in frames] == list(range(frame_count)),
            f"{resref}: frames runtime non contiguës")
    first_physical = [int(value) for value in frames[0].get("physical_size_x4") or []]
    first_logical = [int(value) for value in frames[0].get("logical_size_x1") or []]
    first_centre = frames[0].get("centre_x1")
    require(len(first_physical) == 2 and len(first_logical) == 2 and
            first_physical == [first_logical[0] * 4, first_logical[1] * 4],
            f"{resref}: géométrie runtime uniforme invalide")
    validated_frames = []
    for index, frame in enumerate(frames):
        physical = [int(value) for value in frame.get("physical_size_x4") or []]
        logical = [int(value) for value in frame.get("logical_size_x1") or []]
        name = str(frame.get("asset", ""))
        raw_path = base_pack / name
        require(logical == first_logical and physical == first_physical and
                frame.get("centre_x1") == first_centre,
                f"{resref}: entrée runtime-only réservée à la géométrie uniforme")
        require(raw_path.is_file() and sha256_file(raw_path) == str(frame.get("sha256", "")).lower() and
                raw_path.stat().st_size == int(frame.get("bytes", -1)),
                f"{resref} frame {index}: ancre runtime modifiée")
        validated_frames.append({
            "frame": index,
            "logical_size_x1": logical,
            "physical_size_x4": physical,
            "centre_x1": first_centre,
            "crop_box_x4": [0, 0, physical[0], physical[1]],
            "runtime_asset": name,
            "runtime_asset_sha256": str(frame["sha256"]).lower(),
        })
    cycles = sorted(resource.get("cycles") or [], key=lambda item: int(item.get("cycle", -1)))
    require(cycles and [int(cycle.get("cycle", -1)) for cycle in cycles] == list(range(len(cycles))),
            f"{resref}: cycles runtime non contigus")
    lookups = []
    for cycle in cycles:
        lookup = [int(value) for value in cycle.get("native_frame_indices") or []]
        require(lookup and all(0 <= value < frame_count for value in lookup),
                f"{resref}: cycle runtime invalide")
        lookups.append(lookup)
    return {
        "input_mode": "runtime-uniform-base",
        "resref": resref,
        "source_run": None,
        "run_manifest_sha256": None,
        "frame_manifest_sha256": None,
        "upscale_manifest_sha256": None,
        "aligned_size_x4": first_physical,
        "geometry_mode": "runtime-uniform-base",
        "frames": validated_frames,
        "cycles": lookups,
    }


def load_input_context(source_run: Path | None, base_pack: Path,
                       resource: dict[str, Any], resref: str) -> dict[str, Any]:
    if source_run is not None:
        return load_source_context(source_run, resref)
    return load_runtime_uniform_context(base_pack, resource)


def rgba_from_raw(path: Path, physical_size: list[int]) -> Image.Image:
    expected = physical_size[0] * physical_size[1] * 4
    require(path.is_file() and path.stat().st_size == expected,
            f"buffer RGBA absent ou tronqué : {path}")
    return Image.frombytes("RGBA", tuple(physical_size), path.read_bytes())


def validate_target_compatibility(base_root: Path, resource: dict[str, Any],
                                  context: dict[str, Any]) -> None:
    resref = context["resref"]
    require(resource.get("playback_mode") == "Native",
            f"{resref}: déjà TimedTimeline dans le pack de base")
    frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    require(len(frames) == len(context["frames"]),
            f"{resref}: nombre de frames base/run divergent")
    for base_frame, source_frame in zip(frames, context["frames"], strict=True):
        index = int(base_frame["frame"])
        require(base_frame["logical_size_x1"] == source_frame["logical_size_x1"] and
                base_frame["physical_size_x4"] == source_frame["physical_size_x4"],
                f"{resref} frame {index}: géométrie base/run divergente")
        raw_path = base_root / str(base_frame["asset"])
        require(sha256_file(raw_path) == str(base_frame["sha256"]).lower(),
                f"{resref} frame {index}: ancre runtime modifiée")
        if context["input_mode"] == "spatial-v1":
            base_rgba = rgba_from_raw(raw_path, base_frame["physical_size_x4"])
            with Image.open(source_frame["rgb"]) as source_rgb:
                require(base_rgba.convert("RGB").tobytes() == source_rgb.convert("RGB").tobytes(),
                        f"{resref} frame {index}: RGB base différent du run spatial V1")
        else:
            require(str(source_frame["runtime_asset"]) == str(base_frame["asset"]) and
                    str(source_frame["runtime_asset_sha256"]) == str(base_frame["sha256"]).lower(),
                    f"{resref} frame {index}: ancre runtime-only divergente")
    base_cycles = [cycle["native_frame_indices"] for cycle in resource["cycles"]]
    require(base_cycles == context["cycles"], f"{resref}: cycles base/run divergents")


def collapse_uniform_duplicate_hold_slots(lookup: list[int]) -> tuple[list[int], int]:
    require(len(lookup) >= 2, "cycle trop court pour supprimer des maintiens")
    runs: list[tuple[int, int]] = []
    for frame_index in lookup:
        if runs and runs[-1][0] == frame_index:
            runs[-1] = (frame_index, runs[-1][1] + 1)
        else:
            runs.append((frame_index, 1))
    require(len(runs) < len(lookup),
            "la suppression des maintiens exige des slots natifs consécutifs dupliqués")
    require(runs[0][0] != runs[-1][0],
            "la suppression des maintiens refuse un maintien qui traverse la couture cyclique")
    hold_slots = runs[0][1]
    require(hold_slots >= 2 and all(count == hold_slots for _frame, count in runs),
            "la suppression des maintiens exige des répétitions consécutives uniformes (>= 2)")
    unique = [frame for frame, _count in runs]
    require(len(set(unique)) == len(unique),
            "la suppression des maintiens refuse une frame réutilisée dans plusieurs maintiens")
    return unique, hold_slots


def build_plan(source_run: Path | None, base_pack: Path, resrefs: list[str],
               model: str = DEFAULT_MODEL, collapse_uniform_duplicate_holds: bool = False,
               authoring_for_area_split: bool = False,
               transparent_rgb_mode: str = "preserve-hidden-rgb") -> dict[str, Any]:
    if source_run is not None:
        source_run = source_run.resolve()
    base_pack = base_pack.resolve()
    selected = sorted({normalise_resref(value) for value in resrefs})
    require(selected, "sélection V2 vide")
    require(transparent_rgb_mode in TRANSPARENT_RGB_MODES,
            f"mode RGB transparent inconnu : {transparent_rgb_mode}")
    base_manifest, resources, _sources = load_base_pack(base_pack)
    by_resref = {normalise_resref(str(resource["resref"])): resource for resource in resources}
    targets = []
    for resref in selected:
        require(resref in by_resref, f"{resref}: absent du pack de base")
        context = load_input_context(source_run, base_pack, by_resref[resref], resref)
        validate_target_compatibility(base_pack, by_resref[resref], context)
        base_frame_count = int(by_resref[resref]["frame_count"])
        next_frame = base_frame_count
        cycle_plans = []
        added_bytes = 0
        for cycle_index, lookup in enumerate(context["cycles"]):
            if collapse_uniform_duplicate_holds:
                input_lookup, hold_slots = collapse_uniform_duplicate_hold_slots(lookup)
                phases_per_transition = hold_slots * TARGET_FPS[0] // NATIVE_FPS[0]
                require(phases_per_transition * NATIVE_FPS[0] == hold_slots * TARGET_FPS[0],
                        "subdivision de maintien non entière")
                intermediate_count = len(input_lookup) * (phases_per_transition - 1)
                intermediate = list(range(next_frame, next_frame + intermediate_count))
                next_frame += intermediate_count
                timeline = []
                segments = []
                offset = 0
                for segment, native_index in enumerate(input_lookup):
                    outputs = intermediate[offset:offset + phases_per_transition - 1]
                    offset += phases_per_transition - 1
                    right_native = input_lookup[(segment + 1) % len(input_lookup)]
                    timeline.append(native_index)
                    timeline.extend(outputs)
                    physical = context["frames"][native_index]["physical_size_x4"]
                    added_bytes += physical[0] * physical[1] * 4 * len(outputs)
                    segments.append({
                        "segment": segment,
                        "left_native_frame": native_index,
                        "right_native_frame": right_native,
                        "intermediate_frame_indices": outputs,
                    })
                cycle_plans.append({
                    "cycle": cycle_index,
                    "timing_strategy": "collapse-uniform-duplicate-holds",
                    "native_frame_indices": lookup,
                    "interpolation_input_frame_indices": input_lookup,
                    "hold_slots": hold_slots,
                    "phases_per_transition": phases_per_transition,
                    "intermediate_frame_indices": intermediate,
                    "interpolation_segments": segments,
                    "timeline_frame_indices": timeline,
                    "native_slots": len(lookup),
                    "timeline_phases": len(timeline),
                    "duration_seconds": len(lookup) / NATIVE_FPS[0],
                })
            else:
                intermediate = list(range(next_frame, next_frame + len(lookup)))
                next_frame += len(lookup)
                timeline = []
                for native_index, intermediate_index in zip(lookup, intermediate, strict=True):
                    timeline.extend([native_index, intermediate_index])
                    physical = context["frames"][native_index]["physical_size_x4"]
                    added_bytes += physical[0] * physical[1] * 4
                cycle_plans.append({
                    "cycle": cycle_index,
                    "native_frame_indices": lookup,
                    "intermediate_frame_indices": intermediate,
                    "timeline_frame_indices": timeline,
                    "native_slots": len(lookup),
                    "timeline_phases": len(timeline),
                    "duration_seconds": len(lookup) / NATIVE_FPS[0],
                })
        targets.append({
            "resref": resref,
            "geometry_mode": context["geometry_mode"],
            "input_mode": context["input_mode"],
            "aligned_size_x4": context["aligned_size_x4"],
            "base_frame_count": base_frame_count,
            "output_frame_count": next_frame,
            "cycle_count": len(cycle_plans),
            "added_intermediate_frames": next_frame - base_frame_count,
            "added_raw_bytes": added_bytes,
            "source": (
                {
                    "run_manifest_sha256": context["run_manifest_sha256"],
                    "frame_manifest_sha256": context["frame_manifest_sha256"],
                    "upscale_manifest_sha256": context["upscale_manifest_sha256"],
                    "aligned_rgba_sha256": [frame["aligned_rgba_sha256"]
                                             for frame in context["frames"]],
                }
                if context["input_mode"] == "spatial-v1" else
                {
                    "base_runtime_assets": [
                        {"asset": frame["runtime_asset"], "sha256": frame["runtime_asset_sha256"]}
                        for frame in context["frames"]
                    ],
                }
            ),
            "cycles": cycle_plans,
        })
    payload = {
        "schema": PLAN_SCHEMA,
        "status": "proposed",
        "input_mode": "spatial-v1" if source_run is not None else "runtime-uniform-base",
        "source_run": source_run.as_posix() if source_run is not None else None,
        "source_run_manifest_sha256": (
            sha256_file(source_run / "manifest.json") if source_run is not None else None
        ),
        "base_pack": base_pack.as_posix(),
        "base_pack_schema": base_manifest["schema"],
        "base_pack_manifest_sha256": sha256_file(base_pack / "manifest.json"),
        "base_registry_sha256": str(base_manifest["registry_sha256"]).lower(),
        "scale": 4,
        "native_fps": rate_record(NATIVE_FPS),
        "target_fps": rate_record(TARGET_FPS),
        "topaz": {"model": model, "replace_duplicate_threshold": -0.01,
                  "transparent_rgb_mode": transparent_rgb_mode,
                  "loop_strategy": "append first source slot once; no cyclic-context extrapolation"},
        "alpha_policy": "hold exact alpha of the current native (left) slot",
        "geometry_policy": "crop the aligned interpolation with the current native slot geometry",
        "targets": targets,
        "gates": [
            "the declared input mode and active base pack are hash-validated before build",
            "even phases reuse byte-exact runtime anchors",
            "Topaz must return 2*N+1 or 2*N frames for every closed cycle",
            "visual review and explicit approval file required before install",
        ],
    }
    if collapse_uniform_duplicate_holds:
        payload["duplicate_hold_strategy"] = (
            "collapse contiguous uniform duplicate slots; preserve duration; "
            "interpolate unique poses at the target cadence"
        )
    if authoring_for_area_split:
        payload["authoring_pack_for_area_split"] = True
        payload["runtime_budget_note"] = (
            "output is an authoring pack exempt from the runtime budget; it must be split "
            "with split_animation_pack_by_area.py before any installation"
        )
    payload["plan_sha256"] = sha256_json(payload)
    return payload


def run_checked(command: list[str], *, environment: dict[str, str] | None = None) -> None:
    completed = subprocess.run(command, capture_output=True, text=True, env=environment)
    require(completed.returncode == 0,
            f"commande échouée ({completed.returncode}) : {(completed.stderr or '')[:1200]}")


def checkerboard(size: tuple[int, int], cell: int = 32) -> Image.Image:
    image = Image.new("RGB", size, (48, 48, 48))
    pixels = image.load()
    for y in range(size[1]):
        for x in range(size[0]):
            value = 72 if ((x // cell) + (y // cell)) % 2 else 48
            pixels[x, y] = (value, value, value)
    return image


def aligned_runtime_preview(raw_path: Path, physical: list[int], crop: list[int],
                            aligned_size: list[int]) -> Image.Image:
    sprite = rgba_from_raw(raw_path, physical)
    canvas = Image.new("RGBA", tuple(aligned_size), (0, 0, 0, 0))
    canvas.alpha_composite(sprite, (crop[0], crop[1]))
    background = checkerboard(tuple(aligned_size)).convert("RGBA")
    return Image.alpha_composite(background, canvas).convert("RGB")


def nearest_opaque_dilate(image: Image.Image) -> tuple[Image.Image, int]:
    """Replace hidden RGB with the nearest visible colour for alpha-blind interpolation."""
    rgba = image.convert("RGBA")
    width, height = rgba.size
    pixels = bytearray(rgba.tobytes())
    visible = bytearray(pixels[offset + 3] > 0 for offset in range(0, len(pixels), 4))
    queue = deque(index for index, alpha in enumerate(visible) if alpha)
    require(queue, "une frame entièrement transparente ne peut pas alimenter Topaz")
    replaced = len(visible) - len(queue)
    while queue:
        current = queue.popleft()
        x, y = current % width, current // width
        for neighbour in (current - 1 if x else None,
                          current + 1 if x + 1 < width else None,
                          current - width if y else None,
                          current + width if y + 1 < height else None):
            if neighbour is None or visible[neighbour]:
                continue
            source = current * 4
            target = neighbour * 4
            pixels[target:target + 3] = pixels[source:source + 3]
            visible[neighbour] = 1
            queue.append(neighbour)
    return Image.frombytes("RGBA", (width, height), bytes(pixels)).convert("RGB"), replaced


def input_rgb(image: Image.Image, transparent_rgb_mode: str) -> tuple[Image.Image, int]:
    require(transparent_rgb_mode in TRANSPARENT_RGB_MODES,
            f"mode RGB transparent inconnu : {transparent_rgb_mode}")
    if transparent_rgb_mode == "preserve-hidden-rgb":
        return image.convert("RGB"), 0
    return nearest_opaque_dilate(image)


def save_input_rgb(base_pack: Path, context: dict[str, Any], frame_index: int,
                   destination: Path, transparent_rgb_mode: str) -> int:
    frame = context["frames"][frame_index]
    if context["input_mode"] == "spatial-v1":
        with Image.open(frame["aligned_rgba"]) as aligned:
            rgb, replaced = input_rgb(aligned, transparent_rgb_mode)
    else:
        raw = base_pack / str(frame["runtime_asset"])
        rgb, replaced = input_rgb(rgba_from_raw(raw, frame["physical_size_x4"]),
                                  transparent_rgb_mode)
    rgb.save(destination)
    return replaced


def validate_cycle_output(cycle_root: Path, expected_plan: dict[str, Any]) -> dict[str, Any]:
    report = load_json(cycle_root / "cycle.json")
    require(report.get("schema") == CYCLE_SCHEMA and report.get("status") == "completed" and
            report.get("cycle_plan_sha256") == sha256_json(expected_plan),
            f"cycle V2 existant incompatible : {cycle_root}")
    for frame in report.get("intermediate_frames") or []:
        path = safe_relative(cycle_root, str(frame["file"]))
        require(path.is_file() and path.stat().st_size == int(frame["bytes"]) and
                sha256_file(path) == str(frame["sha256"]),
                f"phase intermédiaire modifiée : {path}")
    for review in report.get("reviews") or []:
        path = safe_relative(cycle_root, str(review["file"]))
        require(path.is_file() and sha256_file(path) == str(review["sha256"]),
                f"review V2 modifiée : {path}")
    return report


def interpolate_cycle(base_pack: Path, base_resource: dict[str, Any], context: dict[str, Any],
                      cycle_plan: dict[str, Any], cycle_root: Path, tvai_ffmpeg: Path,
                      model_dir: Path, model: str, device: str, review_ffmpeg: str,
                      resume: bool, transparent_rgb_mode: str) -> dict[str, Any]:
    if (cycle_root.exists()):
        if resume and (cycle_root / "cycle.json").is_file():
            return validate_cycle_output(cycle_root, cycle_plan)
        if resume:
            resolved = cycle_root.resolve()
            require(resolved.parent == cycle_root.parent.resolve(),
                    "refus de nettoyer un cycle partiel hors work root")
            shutil.rmtree(resolved)
        else:
            raise RuntimeError(f"cycle V2 déjà présent sans --resume : {cycle_root}")
    input_dir = cycle_root / "input"
    raw_dir = cycle_root / "raw_topaz"
    runtime_dir = cycle_root / "runtime"
    review_frames = cycle_root / "review_frames"
    for directory in (input_dir, raw_dir, runtime_dir, review_frames):
        directory.mkdir(parents=True)

    lookup = [int(value) for value in cycle_plan["native_frame_indices"]]
    strategy = str(cycle_plan.get("timing_strategy", "native-slots-x2"))
    if strategy == "native-slots-x2":
        input_lookup = lookup
        input_framerate = "15"
        phases_per_transition = 2
        interpolation_entries = [
            {
                "slot": slot,
                "subphase": 1,
                "left_native_frame": native_index,
                "right_native_frame": lookup[(slot + 1) % len(lookup)],
                "output_index": output_index,
                "raw_index": slot * 2 + 1,
                "anchor_raw_index": slot * 2,
            }
            for slot, (native_index, output_index) in enumerate(zip(
                lookup, cycle_plan["intermediate_frame_indices"], strict=True))
        ]
    elif strategy == "collapse-uniform-duplicate-holds":
        input_lookup = [int(value) for value in cycle_plan["interpolation_input_frame_indices"]]
        hold_slots = int(cycle_plan["hold_slots"])
        phases_per_transition = int(cycle_plan["phases_per_transition"])
        require(phases_per_transition == hold_slots * TARGET_FPS[0] // NATIVE_FPS[0] and
                phases_per_transition * NATIVE_FPS[0] == hold_slots * TARGET_FPS[0],
                f"{context['resref']} cycle {cycle_plan['cycle']}: subdivision de maintien invalide")
        require(collapse_uniform_duplicate_hold_slots(lookup) == (input_lookup, hold_slots),
                f"{context['resref']} cycle {cycle_plan['cycle']}: maintien du plan incompatible")
        input_framerate = f"{NATIVE_FPS[0]}/{NATIVE_FPS[1] * hold_slots}"
        interpolation_entries = []
        segments = cycle_plan.get("interpolation_segments") or []
        require(len(segments) == len(input_lookup),
                f"{context['resref']} cycle {cycle_plan['cycle']}: segments de maintien invalides")
        for segment, specification in enumerate(segments):
            left_native = int(specification["left_native_frame"])
            right_native = int(specification["right_native_frame"])
            outputs = [int(value) for value in specification["intermediate_frame_indices"]]
            require(left_native == input_lookup[segment] and
                    right_native == input_lookup[(segment + 1) % len(input_lookup)] and
                    len(outputs) == phases_per_transition - 1,
                    f"{context['resref']} cycle {cycle_plan['cycle']}: segment de maintien divergent")
            for subphase, output_index in enumerate(outputs, start=1):
                interpolation_entries.append({
                    "slot": segment,
                    "subphase": subphase,
                    "left_native_frame": left_native,
                    "right_native_frame": right_native,
                    "output_index": output_index,
                    "raw_index": segment * phases_per_transition + subphase,
                    "anchor_raw_index": segment * phases_per_transition,
                })
        require([entry["output_index"] for entry in interpolation_entries] ==
                [int(value) for value in cycle_plan["intermediate_frame_indices"]],
                f"{context['resref']} cycle {cycle_plan['cycle']}: indices intermédiaires divergents")
    else:
        raise RuntimeError(f"{context['resref']} cycle {cycle_plan['cycle']}: stratégie temporelle inconnue")

    input_hidden_rgb_replaced = []
    for position, frame_index in enumerate(input_lookup + [input_lookup[0]]):
        replaced = save_input_rgb(base_pack, context, frame_index,
                                  input_dir / f"in_{position:04d}.png", transparent_rgb_mode)
        input_hidden_rgb_replaced.append(replaced)
    filter_text = f"tvai_fi=model={model}:fps=30:rdt=-0.01:device={device}"
    environment = dict(os.environ)
    environment["TVAI_MODEL_DIR"] = str(model_dir)
    environment["TVAI_MODEL_DATA_DIR"] = str(model_dir)
    run_checked([
        str(tvai_ffmpeg), "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", input_framerate, "-i", str(input_dir / "in_%04d.png"),
        "-vf", filter_text, "-pix_fmt", "rgb24", str(raw_dir / "out_%04d.png"),
    ], environment=environment)
    raw = sorted(raw_dir.glob("out_*.png"))
    expected_raw = len(input_lookup) * phases_per_transition + 1
    require(len(raw) in (expected_raw, expected_raw - 1),
            f"{context['resref']} cycle {cycle_plan['cycle']}: Topaz a produit {len(raw)} "
            f"frames, attendu {expected_raw} ou {expected_raw - 1}")

    base_frames = sorted(base_resource["frames"], key=lambda item: int(item["frame"]))
    intermediates = []
    raw_anchor_mae = []
    for entry in interpolation_entries:
        slot = int(entry["slot"])
        native_index = int(entry["left_native_frame"])
        right_native = int(entry["right_native_frame"])
        output_index = int(entry["output_index"])
        source = context["frames"][native_index]
        base_frame = base_frames[native_index]
        if int(entry["subphase"]) == 1:
            with Image.open(raw[int(entry["anchor_raw_index"])]) as topaz_anchor, Image.open(
                    input_dir / f"in_{slot:04d}.png") as anchor:
                raw_anchor_mae.append(image_mae(topaz_anchor.convert("RGB"), anchor.convert("RGB")))
        with Image.open(raw[int(entry["raw_index"])]) as topaz_middle:
            rgb = topaz_middle.convert("RGB").crop(tuple(source["crop_box_x4"]))
        base_raw = base_pack / str(base_frame["asset"])
        alpha = rgba_from_raw(base_raw, source["physical_size_x4"]).getchannel("A")
        rgba = rgb.convert("RGBA")
        rgba.putalpha(alpha)
        name = asset_name(context["resref"], output_index)
        destination = runtime_dir / name
        destination.write_bytes(rgba.tobytes())
        intermediates.append({
            "frame": output_index,
            "slot": slot,
            "subphase": int(entry["subphase"]),
            "left_native_frame": native_index,
            "right_native_frame": right_native,
            "logical_size_x1": source["logical_size_x1"],
            "physical_size_x4": source["physical_size_x4"],
            "centre_x1": source["centre_x1"],
            "file": f"runtime/{name}",
            "asset": name,
            "sha256": sha256_file(destination),
            "bytes": destination.stat().st_size,
            "alpha_source_asset": str(base_frame["asset"]),
            "alpha_source_sha256": str(base_frame["sha256"]),
        })

    by_output = {int(item["frame"]): item for item in intermediates}
    for phase, frame_index in enumerate(cycle_plan["timeline_frame_indices"]):
        if int(frame_index) in by_output:
            item = by_output[int(frame_index)]
            native_index = int(item["left_native_frame"])
            source = context["frames"][native_index]
            raw_path = cycle_root / str(item["file"])
        else:
            native_index = int(frame_index)
            frame = base_frames[native_index]
            source = context["frames"][native_index]
            raw_path = base_pack / str(frame["asset"])
        preview = aligned_runtime_preview(raw_path, source["physical_size_x4"],
                                          source["crop_box_x4"], context["aligned_size_x4"])
        preview.save(review_frames / f"frame_{phase:04d}.png")

    exact_review = cycle_root / "review-30fps-exact.mp4"
    loop_review = cycle_root / "review-30fps-loop-4s.mp4"
    run_checked([
        review_ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-framerate", "30", "-i", str(review_frames / "frame_%04d.png"),
        "-frames:v", str(len(cycle_plan["timeline_frame_indices"])), "-c:v", "libx264", "-preset", "slow",
        "-crf", "12", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(exact_review),
    ])
    run_checked([
        review_ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", str(exact_review), "-t", "4",
        "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(loop_review),
    ])
    require(exact_review.is_file() and loop_review.is_file(), "ffmpeg n'a pas produit les reviews")
    report = {
        "schema": CYCLE_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "resref": context["resref"],
        "cycle": int(cycle_plan["cycle"]),
        "cycle_plan_sha256": sha256_json(cycle_plan),
        "native_fps": rate_record(NATIVE_FPS),
        "target_fps": rate_record(TARGET_FPS),
        "topaz": {"model": model, "filter": filter_text, "raw_frame_count": len(raw),
                  "expected_raw_frame_count": expected_raw,
                  "input_framerate": input_framerate,
                  "transparent_rgb_mode": transparent_rgb_mode,
                  "input_hidden_rgb_replaced": input_hidden_rgb_replaced,
                  "raw_anchor_rgb_mae": [round(value, 6) for value in raw_anchor_mae]},
        "native_frame_indices": lookup,
        "timing_strategy": strategy,
        "interpolation_input_frame_indices": input_lookup,
        "timeline_frame_indices": cycle_plan["timeline_frame_indices"],
        "intermediate_frames": intermediates,
        "reviews": [
            {"kind": "exact", "file": exact_review.name, "sha256": sha256_file(exact_review)},
            {"kind": "loop-4s", "file": loop_review.name, "sha256": sha256_file(loop_review)},
        ],
    }
    write_json(cycle_root / "cycle.json", report)
    return validate_cycle_output(cycle_root, cycle_plan)


def write_v2_pack(pack_root: Path, base_pack: Path, base_manifest: dict[str, Any],
                  resources: list[dict[str, Any]], base_sources: dict[str, Path],
                  cycle_reports: dict[tuple[str, int], tuple[Path, dict[str, Any]]],
                  targets: list[str], authoring_for_area_split: bool = False) -> dict[str, Any]:
    output_resources = copy.deepcopy(resources)
    by_resref = {normalise_resref(str(item["resref"])): item for item in output_resources}
    sources = dict(base_sources)
    new_assets = []
    for resref in targets:
        resource = by_resref[resref]
        for cycle in resource["cycles"]:
            cycle_root, report = cycle_reports[(resref, int(cycle["cycle"]))]
            cycle["timeline_frame_indices"] = [int(value) for value in report["timeline_frame_indices"]]
            for intermediate in report["intermediate_frames"]:
                index = int(intermediate["frame"])
                require(index == len(resource["frames"]),
                        f"{resref}: index intermédiaire non contigu")
                frame = {
                    "frame": index,
                    "logical_size_x1": intermediate["logical_size_x1"],
                    "physical_size_x4": intermediate["physical_size_x4"],
                    "centre_x1": intermediate.get("centre_x1"),
                    "asset": intermediate["asset"],
                    "sha256": intermediate["sha256"],
                    "bytes": intermediate["bytes"],
                    "generated_by": {"mode": "TimedTimeline", "cycle": int(cycle["cycle"]),
                                     "slot": int(intermediate["slot"]),
                                     "left_native_frame": int(intermediate["left_native_frame"]),
                                     "right_native_frame": int(intermediate["right_native_frame"])},
                }
                resource["frames"].append(frame)
                asset = {"name": frame["asset"], "sha256": frame["sha256"],
                         "bytes": frame["bytes"]}
                resource["assets"].append(asset)
                path = safe_relative(cycle_root, str(intermediate["file"]))
                sources[frame["asset"]] = path
                new_assets.append(asset)
        resource["frame_count"] = len(resource["frames"])
        resource["playback_mode"] = "TimedTimeline"
        resource["native_fps"] = rate_record(NATIVE_FPS)
        resource["target_fps"] = rate_record(TARGET_FPS)

    ordered = sorted(output_resources, key=lambda item: str(item["resref"]))
    registry = registry_v2_from_resources(ordered)
    pack_root.mkdir(parents=True)
    registry_path = pack_root / REGISTRY_NAME
    registry_path.write_bytes(registry)
    for resource in ordered:
        for asset in resource["assets"]:
            source = sources[str(asset["name"])]
            destination = pack_root / str(asset["name"])
            shutil.copyfile(source, destination)
            require(destination.stat().st_size == int(asset["bytes"]) and
                    sha256_file(destination) == str(asset["sha256"]),
                    f"copie runtime v2 corrompue : {destination}")
    base_assets = sorted(
        ({"name": name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
         for name, path in base_sources.items()), key=lambda item: item["name"]
    )
    manifest = {
        "schema": PACK_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "scale": 4,
        "registry_version": REGISTRY_VERSION,
        "runtime_contract": {
            "feature": "TimedTimeline",
            "clock": "QPC-pause-aware",
            "registry_version": REGISTRY_VERSION,
        },
        "registry": REGISTRY_NAME,
        "registry_sha256": sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": len(ordered),
        "frame_count": sum(int(item["frame_count"]) for item in ordered),
        "timed_resources": targets,
        "runtime_budget_enforced": not authoring_for_area_split,
        "authoring_pack_for_area_split": authoring_for_area_split,
        "base_pack": base_pack.as_posix(),
        "base_pack_manifest_sha256": sha256_file(base_pack / "manifest.json"),
        "base_registry_sha256": str(base_manifest["registry_sha256"]).lower(),
        "base_registry_bytes": int(base_manifest["registry_bytes"]),
        "base_assets": base_assets,
        "new_assets": sorted(new_assets, key=lambda item: item["name"]),
        "resources": ordered,
    }
    write_json(pack_root / "manifest.json", manifest)
    validate_v2_pack(pack_root)
    return manifest


def adopt_clock_patch(base_pack: Path, clock_patch: Path, output: Path,
                      resume: bool) -> dict[str, Any]:
    """Promote the accepted single-resource runtime-clock patch into a full V2 pack.

    The early PORTL1A proof predated the V2 pack orchestrator and contains only
    its registry replacement plus odd frames.  This command verifies that exact
    patch against its immutable V1 base, then writes a full V2 pack so future
    V2 runs can extend it without dropping the accepted timed resource.
    """
    base_pack = base_pack.resolve()
    clock_patch = clock_patch.resolve()
    output = output.resolve()
    base_manifest, resources, base_sources = load_base_pack(base_pack)
    require(base_manifest.get("schema") == runtime_v1.PACK_SCHEMA,
            "adoption de patch d'horloge réservée à une base runtime V1")
    patch = load_json(clock_patch / "manifest.json")
    require(patch.get("schema") == "bg2-upscale-area-animation-runtime-clock-patch-v1" and
            patch.get("status") == "completed" and int(patch.get("scale", 0)) == 4 and
            int(patch.get("registry_version", 0)) == LEGACY_REGISTRY_VERSION and
            patch.get("playback_mode") == "TimedTimeline" and
            rate_tuple({"numerator": int((patch.get("native_fps") or [0, 0])[0]),
                        "denominator": int((patch.get("native_fps") or [0, 0])[1])}) == NATIVE_FPS and
            rate_tuple({"numerator": int((patch.get("target_fps") or [0, 0])[0]),
                        "denominator": int((patch.get("target_fps") or [0, 0])[1])}) == TARGET_FPS,
            f"patch d'horloge incompatible : {clock_patch}")
    require(str(patch.get("base_registry_sha256", "")).lower() ==
            str(base_manifest.get("registry_sha256", "")).lower() and
            int(patch.get("base_registry_bytes", -1)) == int(base_manifest.get("registry_bytes", -2)),
            "le patch d'horloge ne correspond pas au pack V1 fourni")
    resref = normalise_resref(str(patch.get("resref", "")))
    by_resref = {normalise_resref(str(resource["resref"])): copy.deepcopy(resource)
                 for resource in resources}
    require(resref in by_resref, f"{resref}: absent de la base V1")
    resource = by_resref[resref]
    base_frames = sorted(resource["frames"], key=lambda item: int(item["frame"]))
    patch_base_frames = sorted(patch.get("base_frames") or [], key=lambda item: int(item.get("frame", -1)))
    require(len(base_frames) == len(patch_base_frames),
            f"{resref}: ancres patch/base de nombre différent")
    for base_frame, patch_frame in zip(base_frames, patch_base_frames, strict=True):
        require(int(base_frame["frame"]) == int(patch_frame.get("frame", -1)) and
                str(base_frame["asset"]) == str(patch_frame.get("asset", "")) and
                int(base_frame["bytes"]) == int(patch_frame.get("bytes", -1)) and
                str(base_frame["sha256"]).lower() == str(patch_frame.get("sha256", "")).lower(),
                f"{resref}: ancre patch/base divergente")
    require(len(resource["cycles"]) == 1, f"{resref}: patch historique mono-cycle incompatible")
    native = [int(value) for value in resource["cycles"][0]["native_frame_indices"]]
    timeline = [int(value) for value in patch.get("timeline_frame_indices") or []]
    require(len(native) == int(patch.get("native_cycle_slots", -1)) and
            len(timeline) == int(patch.get("timeline_phases", -1)) == len(native) * 2 and
            timeline[::2] == native,
            f"{resref}: timeline du patch incompatible avec le cycle de base")
    new_frames = sorted(patch.get("new_frames") or [], key=lambda item: int(item.get("frame", -1)))
    expected_new_indices = list(range(len(base_frames), len(base_frames) + len(native)))
    require([int(frame.get("frame", -1)) for frame in new_frames] == expected_new_indices and
            timeline[1::2] == expected_new_indices,
            f"{resref}: phases impaires du patch non contiguës")

    new_assets = []
    sources = dict(base_sources)
    for phase, patch_frame in enumerate(new_frames):
        index = int(patch_frame["frame"])
        left_native = native[phase]
        left_frame = base_frames[left_native]
        logical = [int(value) for value in patch_frame.get("logical_size_x1") or []]
        physical = [int(value) for value in patch_frame.get("physical_size_x4") or []]
        name = str(patch_frame.get("asset", ""))
        source = clock_patch / name
        expected_bytes = physical[0] * physical[1] * 4 if len(physical) == 2 else -1
        require(name == asset_name(resref, index) and len(logical) == 2 and
                physical == [logical[0] * 4, logical[1] * 4] and
                expected_bytes == int(patch_frame.get("bytes", -1)) and source.is_file() and
                sha256_file(source) == str(patch_frame.get("sha256", "")).lower(),
                f"{resref} phase {index}: asset de patch invalide")
        frame = {
            "frame": index,
            "logical_size_x1": logical,
            "physical_size_x4": physical,
            "centre_x1": left_frame.get("centre_x1"),
            "asset": name,
            "sha256": str(patch_frame["sha256"]).lower(),
            "bytes": expected_bytes,
            "adopted_from": {"clock_patch": clock_patch.as_posix(), "phase": phase,
                              "left_native_frame": left_native},
        }
        resource["frames"].append(frame)
        asset = {"name": name, "sha256": frame["sha256"], "bytes": expected_bytes}
        resource["assets"].append(asset)
        new_assets.append(asset)
        sources[name] = source
    resource["frame_count"] = len(resource["frames"])
    resource["playback_mode"] = "TimedTimeline"
    resource["native_fps"] = rate_record(NATIVE_FPS)
    resource["target_fps"] = rate_record(TARGET_FPS)
    resource["cycles"][0]["timeline_frame_indices"] = timeline

    output_resources = sorted(by_resref.values(), key=lambda item: str(item["resref"]))
    legacy_registry = registry_v2_from_resources(output_resources, LEGACY_REGISTRY_VERSION)
    patch_registry = clock_patch / REGISTRY_NAME
    require(patch_registry.is_file() and patch_registry.read_bytes() == legacy_registry and
            sha256_file(patch_registry) == str(patch.get("target_registry_sha256", "")).lower() and
            patch_registry.stat().st_size == int(patch.get("target_registry_bytes", -1)),
            f"{resref}: registre du patch incompatible")
    registry = registry_v2_from_resources(output_resources)
    if output.exists():
        require(resume, f"base V2 déjà présente sans --resume : {output}")
        manifest, _validated = validate_v2_pack(output)
        require(manifest.get("adopted_clock_patch", {}).get("manifest_sha256") ==
                sha256_file(clock_patch / "manifest.json"),
                "base V2 existante issue d'un autre patch")
        return manifest
    output.mkdir(parents=True)
    registry_path = output / REGISTRY_NAME
    registry_path.write_bytes(registry)
    for resource_item in output_resources:
        for asset in resource_item["assets"]:
            source = sources[str(asset["name"])]
            destination = output / str(asset["name"])
            shutil.copyfile(source, destination)
            require(destination.stat().st_size == int(asset["bytes"]) and
                    sha256_file(destination) == str(asset["sha256"]),
                    f"copie de base V2 corrompue : {destination}")
    manifest = {
        "schema": PACK_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "scale": 4,
        "registry_version": REGISTRY_VERSION,
        "runtime_contract": {"feature": "TimedTimeline", "clock": "QPC-pause-aware",
                             "registry_version": REGISTRY_VERSION},
        "registry": REGISTRY_NAME,
        "registry_sha256": sha256_file(registry_path),
        "registry_bytes": registry_path.stat().st_size,
        "resource_count": len(output_resources),
        "frame_count": sum(int(item["frame_count"]) for item in output_resources),
        "timed_resources": [resref],
        "base_pack": base_pack.as_posix(),
        "base_pack_manifest_sha256": sha256_file(base_pack / "manifest.json"),
        "base_registry_sha256": str(base_manifest["registry_sha256"]).lower(),
        "base_registry_bytes": int(base_manifest["registry_bytes"]),
        "base_assets": sorted(
            ({"name": name, "sha256": sha256_file(path), "bytes": path.stat().st_size}
             for name, path in base_sources.items()), key=lambda item: item["name"]),
        "new_assets": sorted(new_assets, key=lambda item: item["name"]),
        "adopted_clock_patch": {
            "path": clock_patch.as_posix(),
            "manifest_sha256": sha256_file(clock_patch / "manifest.json"),
            "registry_sha256": sha256_file(patch_registry),
        },
        "resources": output_resources,
    }
    write_json(output / "manifest.json", manifest)
    validate_v2_pack(output)
    return manifest


def validate_run(output: Path, expected_plan_sha256: str | None = None) -> dict[str, Any]:
    output = output.resolve()
    manifest = load_json(output / "manifest.json")
    require(manifest.get("schema") == RUN_SCHEMA and manifest.get("status") == "completed",
            f"run temporel V2 incomplet : {output}")
    if expected_plan_sha256:
        require(manifest.get("plan_sha256") == expected_plan_sha256,
                "run V2 produit depuis un autre plan")
    pack_manifest, _resources = validate_v2_pack(output / "03_runtime_pack")
    require(manifest.get("pack_manifest_sha256") ==
            sha256_file(output / "03_runtime_pack" / "manifest.json") and
            manifest.get("registry_sha256") == pack_manifest["registry_sha256"],
            "provenance pack/run V2 divergente")
    for review in manifest.get("reviews") or []:
        path = safe_relative(output, str(review["file"]))
        require(path.is_file() and sha256_file(path) == str(review["sha256"]),
                f"review run V2 modifiée : {path}")
    manual_patch = manifest.get("manual_alpha_patch")
    if isinstance(manual_patch, dict) and manual_patch.get("mask_storage") == "run-relative-v1":
        descriptor = load_json(output / "manual-mask.json")
        require(descriptor == manual_patch, "descripteur de masque manuel différent du run")
        targets = manual_patch.get("targets")
        require(isinstance(targets, list) and targets, "masques manuels absents du run")
        seen: set[str] = set()
        for target in targets:
            require(isinstance(target, dict), "entrée de masque manuel invalide")
            resref = normalise_resref(str(target.get("resref", "")))
            require(resref not in seen, f"masque manuel dupliqué : {resref}")
            seen.add(resref)
            expected_source = f"manual-mask/{resref}/source.png"
            require(target.get("mask_source") == expected_source,
                    f"source de masque non canonique : {resref}")
            mask = safe_relative(output, expected_source)
            require(mask.is_file() and sha256_file(mask) == str(target.get("mask_sha256", "")),
                    f"masque manuel modifié : {mask}")
    return manifest


def build_run(source_run: Path | None, base_pack: Path, output: Path, resrefs: list[str],
              approved_plan_sha256: str, tvai_ffmpeg: Path, model_dir: Path, model: str,
              device: str, review_ffmpeg: str, resume: bool,
              collapse_uniform_duplicate_holds: bool = False,
              authoring_for_area_split: bool = False,
              transparent_rgb_mode: str = "preserve-hidden-rgb") -> dict[str, Any]:
    plan = build_plan(source_run, base_pack, resrefs, model, collapse_uniform_duplicate_holds,
                      authoring_for_area_split, transparent_rgb_mode)
    require(plan["plan_sha256"] == approved_plan_sha256,
            "hash de plan non approuvé ou plan modifié depuis la proposition")
    output = output.resolve()
    if output.exists():
        require(resume, f"sortie V2 déjà présente sans --resume : {output}")
        return validate_run(output, plan["plan_sha256"])
    partial = output.with_name(output.name + ".partial")
    if partial.exists():
        require(resume, f"sortie V2 partielle présente ; employer --resume : {partial}")
        request = load_json(partial / "request.json")
        require(request.get("plan_sha256") == plan["plan_sha256"],
                "la sortie partielle appartient à un autre plan")
    else:
        partial.mkdir(parents=True)
        write_json(partial / "request.json", plan)

    require(tvai_ffmpeg.is_file() and model_dir.is_dir() and
            (model_dir / f"{model}.json").is_file(), "installation Topaz Video AI incomplète")
    base_manifest, resources, base_sources = load_base_pack(base_pack)
    by_resref = {normalise_resref(str(item["resref"])): item for item in resources}
    contexts = {
        resref: load_input_context(source_run, base_pack, by_resref[resref], resref)
        for resref in sorted({normalise_resref(value) for value in resrefs})
    }
    cycle_reports: dict[tuple[str, int], tuple[Path, dict[str, Any]]] = {}
    reviews = []
    plan_by_resref = {item["resref"]: item for item in plan["targets"]}
    for resref, context in contexts.items():
        validate_target_compatibility(base_pack, by_resref[resref], context)
        for cycle_plan in plan_by_resref[resref]["cycles"]:
            cycle_index = int(cycle_plan["cycle"])
            cycle_root = partial / "work" / resref / f"cycle_{cycle_index:03d}"
            report = interpolate_cycle(base_pack, by_resref[resref], context, cycle_plan,
                                       cycle_root, tvai_ffmpeg, model_dir, model, device,
                                       review_ffmpeg, resume, transparent_rgb_mode)
            cycle_reports[(resref, cycle_index)] = (cycle_root, report)
            for review in report["reviews"]:
                path = cycle_root / str(review["file"])
                reviews.append({
                    "resref": resref,
                    "cycle": cycle_index,
                    "kind": review["kind"],
                    "file": path.relative_to(partial).as_posix(),
                    "sha256": review["sha256"],
                })

    pack_root = partial / "03_runtime_pack"
    if pack_root.exists():
        resolved = pack_root.resolve()
        require(resolved.parent == partial.resolve(), "pack partiel hors run V2")
        shutil.rmtree(resolved)
    pack_manifest = write_v2_pack(pack_root, base_pack.resolve(), base_manifest, resources,
                                  base_sources, cycle_reports, sorted(contexts),
                                  authoring_for_area_split)
    manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed",
        "created_utc": utc_now(),
        "plan_sha256": plan["plan_sha256"],
        "input_mode": plan["input_mode"],
        "source_run": source_run.resolve().as_posix() if source_run is not None else None,
        "source_run_manifest_sha256": plan["source_run_manifest_sha256"],
        "base_pack": base_pack.resolve().as_posix(),
        "base_pack_manifest_sha256": plan["base_pack_manifest_sha256"],
        "native_fps": rate_record(NATIVE_FPS),
        "target_fps": rate_record(TARGET_FPS),
        "timed_resources": sorted(contexts),
        "topaz": {"ffmpeg": tvai_ffmpeg.resolve().as_posix(),
                  "model_dir": model_dir.resolve().as_posix(), "model": model,
                  "device": device, "replace_duplicate_threshold": -0.01,
                  "transparent_rgb_mode": transparent_rgb_mode},
        "pack": "03_runtime_pack",
        "pack_manifest_sha256": sha256_file(pack_root / "manifest.json"),
        "registry_sha256": pack_manifest["registry_sha256"],
        "reviews": reviews,
        "qa_status": "pending-explicit-user-approval",
    }
    write_json(partial / "manifest.json", manifest)
    validate_run(partial, plan["plan_sha256"])
    partial.replace(output)
    return validate_run(output, plan["plan_sha256"])


def approve_run(output: Path, approved_run_manifest_sha256: str,
                resrefs: list[str]) -> dict[str, Any]:
    output = output.resolve()
    manifest = validate_run(output)
    actual_manifest_hash = sha256_file(output / "manifest.json")
    require(actual_manifest_hash == approved_run_manifest_sha256.lower(),
            "hash du run visuellement approuvé différent")
    selected = sorted({normalise_resref(value) for value in resrefs})
    require(selected == sorted(manifest["timed_resources"]),
            "l'approbation doit couvrir exactement toutes les ressources temporisées")
    approval = {
        "schema": APPROVAL_SCHEMA,
        "status": "accepted",
        "created_utc": utc_now(),
        "run_manifest_sha256": actual_manifest_hash,
        "pack_manifest_sha256": sha256_file(output / "03_runtime_pack" / "manifest.json"),
        "registry_sha256": manifest["registry_sha256"],
        "accepted_resrefs": selected,
        "reviews": manifest["reviews"],
        "decision": "explicit user visual approval required and recorded by the invoking agent",
    }
    approval_path = output / "qa-approval.json"
    if approval_path.exists():
        existing = load_json(approval_path)
        comparable = copy.deepcopy(existing)
        comparable.pop("created_utc", None)
        expected = copy.deepcopy(approval)
        expected.pop("created_utc", None)
        require(comparable == expected, "une autre approbation QA existe déjà")
        return existing
    write_json(approval_path, approval)
    return approval


def add_common_source_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source-run", type=Path,
                        help="chemin ou identifiant d'un run spatial V1 x4 terminé")
    parser.add_argument("--base-runtime-only", action="store_true",
                        help="utiliser les ancres 15 fps uniformes du pack de base")
    parser.add_argument("--base-pack", type=Path, required=True,
                        help="pack runtime V1 ou V2 immuable à étendre")
    parser.add_argument("--resref", action="append", required=True,
                        help="BAM à temporiser ; répétable")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--transparent-rgb-mode", choices=TRANSPARENT_RGB_MODES,
                        default="preserve-hidden-rgb",
                        help="RGB fourni à Topaz sous alpha nul")
    parser.add_argument("--collapse-uniform-duplicate-holds", action="store_true",
                        help="interpoler les poses uniques d'un cycle à maintiens uniformes")
    parser.add_argument("--authoring-pack-for-area-split", action="store_true",
                        help="produire un pack d'auteur exempté du budget runtime de 512 MiB ; "
                             "il devra être découpé par zone avec split_animation_pack_by_area.py "
                             "avant toute installation")


def validate_input_mode(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    if bool(args.source_run) == bool(args.base_runtime_only):
        parser.error("fournir exactement un --source-run ou --base-runtime-only")


def add_run_destination_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--run",
        help=(
            "identifiant simple; nouveau run mono-resref sous "
            "animations/ressources/<RESREF>/runs, sinon sous animations/batches"
        ),
    )
    group.add_argument(
        "--output",
        type=Path,
        help="chemin explicite, notamment pour reprendre un run legacy",
    )


def resolve_source_run(value: Path | None, resrefs: list[str]) -> Path | None:
    if value is None:
        return None
    return animation_paths.resolve_existing_run(value, resrefs)


def resolve_run_destination(args: argparse.Namespace) -> Path:
    if args.output is not None:
        output = args.output.resolve()
        partial = output.with_name(output.name + ".partial")
        if not output.exists() and not partial.exists():
            animation_paths.validate_run_location(output, args.resref)
        return output
    return animation_paths.resolve_run_destination(args.run, args.resref)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    plan_parser = subparsers.add_parser("plan", help="audit en lecture seule et proposition")
    add_common_source_arguments(plan_parser)
    plan_parser.add_argument(
        "--run",
        help="identifiant simple dont l'emplacement canonique sera proposé sans être créé",
    )

    build_parser = subparsers.add_parser("build", help="interpolation et pack V2 immuable")
    add_common_source_arguments(build_parser)
    add_run_destination_arguments(build_parser)
    build_parser.add_argument("--approve-plan-sha256", required=True)
    build_parser.add_argument("--tvai-ffmpeg", type=Path, default=DEFAULT_TVAI_FFMPEG)
    build_parser.add_argument("--tvai-model-dir", type=Path, default=DEFAULT_TVAI_MODEL_DIR)
    build_parser.add_argument("--device", default=DEFAULT_DEVICE)
    build_parser.add_argument("--review-ffmpeg", default="ffmpeg")
    build_parser.add_argument("--resume", action="store_true")

    adopt_parser = subparsers.add_parser(
        "adopt-clock-patch",
        help="promouvoir un patch runtime historique mono-ressource en pack V2 complet",
    )
    adopt_parser.add_argument("--base-pack", type=Path, required=True)
    adopt_parser.add_argument("--clock-patch", type=Path, required=True)
    adopt_parser.add_argument("--output", type=Path, required=True)
    adopt_parser.add_argument("--resume", action="store_true")

    validate_parser = subparsers.add_parser("validate", help="revalider un run V2 sans écrire")
    validate_parser.add_argument("--output", type=Path, required=True)

    approve_parser = subparsers.add_parser("approve", help="enregistrer l'approbation visuelle")
    approve_parser.add_argument("--output", type=Path, required=True)
    approve_parser.add_argument("--approve-run-manifest-sha256", required=True)
    approve_parser.add_argument("--resref", action="append", required=True)

    args = parser.parse_args(argv)
    if args.command == "plan":
        validate_input_mode(args, plan_parser)
        source_run = resolve_source_run(args.source_run, args.resref)
        proposed = (
            animation_paths.resolve_run_destination(args.run, args.resref)
            if args.run
            else animation_paths.default_run_root(args.resref)
        )
        print(
            "Emplacement de run proposé : " + animation_paths.display_path(proposed),
            file=sys.stderr,
        )
        result = build_plan(source_run, args.base_pack, args.resref, args.model,
                            args.collapse_uniform_duplicate_holds,
                            args.authoring_pack_for_area_split,
                            args.transparent_rgb_mode)
    elif args.command == "build":
        validate_input_mode(args, build_parser)
        source_run = resolve_source_run(args.source_run, args.resref)
        output = resolve_run_destination(args)
        result = build_run(source_run, args.base_pack, output, args.resref,
                           args.approve_plan_sha256.lower(), args.tvai_ffmpeg.resolve(),
                           args.tvai_model_dir.resolve(), args.model, args.device,
                           args.review_ffmpeg, args.resume,
                           args.collapse_uniform_duplicate_holds,
                           args.authoring_pack_for_area_split,
                           args.transparent_rgb_mode)
    elif args.command == "adopt-clock-patch":
        result = adopt_clock_patch(args.base_pack, args.clock_patch, args.output, args.resume)
    elif args.command == "validate":
        result = validate_run(args.output)
    else:
        result = approve_run(args.output, args.approve_run_manifest_sha256, args.resref)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
