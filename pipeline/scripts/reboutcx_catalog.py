"""Build and verify an offline catalog derived from xBR with ReboutCX replacements."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import struct
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from run_creature_sprite_x2 import (
    CATALOG_SHARD_REGISTRY_VERSION,
    MAX_REGISTRY_SET_SHARDS,
    MAX_RESOURCES,
    REGISTRY_FRAME_CODEC_RAW,
    REGISTRY_FRAME_CODEC_XPRESS_HUFF,
    REGISTRY_FRAME_HEADER_BYTES,
    REGISTRY_HEADER_BYTES,
    REGISTRY_RESOURCE_HEADER_BYTES,
    XN_COMPRESSED_REGISTRY_VERSION,
    XN_REGISTRY_VERSION,
    catalog_component_digest,
    catalog_logical_content_digest,
    catalog_shard_entry_bytes,
    catalog_shard_filename,
    catalog_source_component_sha256,
    inspect_registry,
    maximum_registry_bytes,
    partition_registry_resources,
    read_sealed_catalog_index,
    write_compressed_catalog_registry_records,
    write_registry_catalog_index,
)
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
JOB_SCHEMA = "bg2-upscale-reboutcx-derived-catalog-job-v1"
BUILD_SCHEMA = "bg2-upscale-reboutcx-derived-catalog-build-v1"
POINTER_SCHEMA = "bg2-upscale-reboutcx-derived-catalog-current-v1"
P2_SCHEMA = "bg2-upscale-reboutcx-full-run-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def sealed_animations(animations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep only fields encoded by the catalog animation table."""

    return [
        {
            "animation_id": str(value["animation_id"]),
            "owner": int(value["owner"]),
            "component_indices": [int(index) for index in value["component_indices"]],
        }
        for value in animations
    ]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def canonical_json_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest().upper()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def require_sha256(value: object, label: str) -> str:
    result = str(value).upper()
    if re.fullmatch(r"[0-9A-F]{64}", result) is None:
        raise RuntimeError(f"invalid {label} SHA-256")
    return result


def normalize_animation_id(value: object) -> str:
    try:
        number = int(str(value), 16)
    except ValueError as error:
        raise RuntimeError("invalid animation id") from error
    if not 0 <= number <= 0xFFFF:
        raise RuntimeError("invalid animation id")
    return f"0x{number:04X}"


def parent_context(job: dict[str, Any]) -> dict[str, Any]:
    pointer_path = resolve_path_reference(
        job["paths"]["parent_pointer"], required=True, root=PROJECT_ROOT
    )
    expected_pointer_sha = require_sha256(job["parent"]["pointer_sha256"], "parent pointer")
    if sha256_file(pointer_path) != expected_pointer_sha:
        raise RuntimeError("canonical xBR pointer hash differs")
    pointer = read_json(pointer_path)
    expected_generation = require_sha256(job["parent"]["generation_id"], "parent generation")
    if str(pointer.get("generation_id", "")).upper() != expected_generation:
        raise RuntimeError("canonical xBR generation differs")
    generation_dir = resolve_path_reference(
        pointer["generation_dir"], required=True, root=PROJECT_ROOT
    )
    manifest_path = generation_dir / str(pointer["build_manifest"])
    expected_manifest_sha = require_sha256(
        job["parent"]["build_manifest_sha256"], "parent manifest"
    )
    if (
        sha256_file(manifest_path) != expected_manifest_sha
        or str(pointer.get("build_manifest_sha256", "")).upper()
        != expected_manifest_sha
    ):
        raise RuntimeError("canonical xBR build manifest differs")
    manifest = read_json(manifest_path)
    catalog_path = manifest_path.parent / str(manifest["registry_catalog"])
    expected_catalog_sha = require_sha256(job["parent"]["catalog_sha256"], "parent catalog")
    if (
        sha256_file(catalog_path) != expected_catalog_sha
        or str(manifest.get("registry_catalog_sha256", "")).upper()
        != expected_catalog_sha
    ):
        raise RuntimeError("canonical xBR catalog differs")
    expected_logical = require_sha256(
        job["parent"]["logical_content_sha256"], "parent logical content"
    )
    if str(manifest.get("registry_catalog_logical_content_sha256", "")).upper() != expected_logical:
        raise RuntimeError("canonical xBR logical content differs")
    index = read_sealed_catalog_index(catalog_path, expected_catalog_sha)
    if index["scale"] != 2:
        raise RuntimeError("canonical parent scale is not x2")
    logical_digests = [
        require_sha256(value, "parent logical component")
        for value in manifest["registry_catalog_logical_component_digests"]
    ]
    if len(logical_digests) != len(index["components"]):
        raise RuntimeError("parent logical component inventory differs")
    return {
        "pointer_path": pointer_path,
        "pointer": pointer,
        "generation_dir": generation_dir,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "catalog_path": catalog_path,
        "pack_dir": catalog_path.parent,
        "index": index,
        "logical_digests": logical_digests,
    }


def resource_contract_digest(record: dict[str, Any]) -> str:
    """Hash source identity, geometry, representatives and cycles; skip HD indices."""

    physical_bytes = int(record["bytes"])
    scale = int(record["scale"])
    storage_version = int(record["storage_version"])
    with Path(record["path"]).open("rb") as stream:
        stream.seek(int(record["offset"]))
        raw = stream.read(physical_bytes)
    if len(raw) != physical_bytes:
        raise RuntimeError(f"truncated resource record: {record['resref']}")
    offset = 0
    resource_header = raw[offset : offset + REGISTRY_RESOURCE_HEADER_BYTES]
    offset += REGISTRY_RESOURCE_HEADER_BYTES
    if len(resource_header) != REGISTRY_RESOURCE_HEADER_BYTES:
        raise RuntimeError("truncated resource header")
    frame_count, cycle_count = struct.unpack_from("<II", resource_header, 40)
    digest = hashlib.sha256()
    digest.update(b"IEECSN-RESOURCE-CONTRACT-V1\0")
    digest.update(resource_header)
    logical_bytes = REGISTRY_RESOURCE_HEADER_BYTES
    for _ in range(frame_count):
        frame_header = bytearray(raw[offset : offset + REGISTRY_FRAME_HEADER_BYTES])
        offset += REGISTRY_FRAME_HEADER_BYTES
        if len(frame_header) != REGISTRY_FRAME_HEADER_BYTES:
            raise RuntimeError("truncated resource frame header")
        width, height, _x, _y, _transparent, stored_bytes = struct.unpack_from(
            "<HHhhB3xI", frame_header, 0
        )
        logical_payload = width * height * scale * scale
        codec = frame_header[9]
        valid_storage = (
            storage_version == XN_REGISTRY_VERSION
            and codec == REGISTRY_FRAME_CODEC_RAW
            and stored_bytes == logical_payload
        ) or (
            storage_version == XN_COMPRESSED_REGISTRY_VERSION
            and (
                (codec == REGISTRY_FRAME_CODEC_RAW and stored_bytes == logical_payload)
                or (
                    codec == REGISTRY_FRAME_CODEC_XPRESS_HUFF
                    and 0 < stored_bytes < logical_payload
                )
            )
        )
        if not valid_storage or offset + stored_bytes > len(raw):
            raise RuntimeError("invalid resource frame storage")
        offset += stored_bytes
        frame_header[9:12] = b"\0\0\0"
        struct.pack_into("<I", frame_header, 12, logical_payload)
        digest.update(frame_header)
        logical_bytes += REGISTRY_FRAME_HEADER_BYTES + logical_payload
    for _ in range(cycle_count):
        if offset + 4 > len(raw):
            raise RuntimeError("truncated resource cycle")
        slots = struct.unpack_from("<I", raw, offset)[0]
        size = 4 + slots * 4
        if offset + size > len(raw):
            raise RuntimeError("truncated resource cycle lookup")
        digest.update(raw[offset : offset + size])
        offset += size
        logical_bytes += size
    if offset != len(raw) or logical_bytes != int(record["logical_bytes"]):
        raise RuntimeError("resource logical size differs")
    return digest.hexdigest().upper()


def inspect_component_records(
    paths: list[Path], *, expected_animation_id: str | None
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    records: list[dict[str, Any]] = []
    infos: list[dict[str, Any]] = []
    for path in paths:
        info = inspect_registry(path, include_resource_records=True)
        if (
            info["scale"] != 2
            or info["registry_magic"] != "IEECSXN"
            or (
                expected_animation_id is not None
                and info["animation_id"].upper() != expected_animation_id.upper()
            )
        ):
            raise RuntimeError(f"incompatible component registry: {path}")
        records.extend(info["resource_records"])
        infos.append(info)
    records.sort(key=lambda item: str(item["resref"]))
    if len({str(record["resref"]) for record in records}) != len(records):
        raise RuntimeError("duplicate resref in component")
    return records, infos


def load_replacement(
    specification: dict[str, Any], parent: dict[str, Any]
) -> dict[str, Any]:
    animation_id = normalize_animation_id(specification["animation_id"])
    parent_animation = next(
        (value for value in parent["index"]["animations"] if value["animation_id"] == animation_id),
        None,
    )
    if parent_animation is None:
        raise RuntimeError(f"replacement animation absent from parent: {animation_id}")
    expected_owner = int(specification["expected_owner"])
    expected_indices = [int(value) for value in specification["expected_component_indices"]]
    expected_digests = [
        require_sha256(value, "expected component")
        for value in specification["expected_component_digests"]
    ]
    expected_logical = [
        require_sha256(value, "expected logical component")
        for value in specification["expected_logical_component_digests"]
    ]
    if (
        int(parent_animation["owner"]) != expected_owner
        or parent_animation["component_indices"] != expected_indices
        or len(expected_indices) != 1
        or [parent["index"]["components"][index]["digest"] for index in expected_indices]
        != expected_digests
        or [parent["logical_digests"][index] for index in expected_indices]
        != expected_logical
    ):
        raise RuntimeError(f"parent component contract differs: {animation_id}")
    old_component = parent["index"]["components"][expected_indices[0]]
    old_shards = parent["index"]["shards"][
        old_component["shard_start"] : old_component["shard_start"]
        + old_component["shard_count"]
    ]
    expected_shards = [
        require_sha256(value, "expected shard")
        for value in specification["expected_shard_sha256s"]
    ]
    if [shard["sha256"] for shard in old_shards] != expected_shards:
        raise RuntimeError(f"parent shard contract differs: {animation_id}")

    manifest_path = resolve_path_reference(
        specification["reboutcx_manifest"], required=True, root=PROJECT_ROOT
    )
    expected_manifest_sha = require_sha256(
        specification["reboutcx_manifest_sha256"], "ReboutCX manifest"
    )
    if sha256_file(manifest_path) != expected_manifest_sha:
        raise RuntimeError(f"ReboutCX manifest differs: {animation_id}")
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != P2_SCHEMA
        or manifest.get("status") != "completed-pending-human-review"
        or manifest.get("installable") is not False
        or int(manifest.get("target_scale", 0)) != 2
        or normalize_animation_id(manifest.get("animation_id", "")) != animation_id
    ):
        raise RuntimeError(f"invalid P2 manifest: {animation_id}")
    for evidence in manifest["code"].values():
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError(f"P2 code/input changed: {evidence['path']}")
    component_paths: list[Path] = []
    for resource in manifest["resources"]:
        evidence = resource["component"]
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError(f"P2 component changed: {resource['resref']}")
        component_paths.append(path)
    new_records, _new_infos = inspect_component_records(
        component_paths, expected_animation_id=animation_id
    )
    if (
        len(new_records) != int(old_component["resource_count"])
        or sum(int(record["frame_count"]) for record in new_records)
        != int(old_component["frame_count"])
        or sum(int(record["index_bytes"]) for record in new_records)
        != int(old_component["index_bytes"])
    ):
        raise RuntimeError(f"replacement totals differ from xBR: {animation_id}")

    parent_paths = [
        parent["pack_dir"] / Path(str(shard["registry"])).name for shard in old_shards
    ]
    old_records, old_infos = inspect_component_records(
        parent_paths, expected_animation_id="0xFFFF"
    )
    old_by_resref = {str(record["resref"]): record for record in old_records}
    new_by_resref = {str(record["resref"]): record for record in new_records}
    if old_by_resref.keys() != new_by_resref.keys():
        raise RuntimeError(f"replacement resrefs differ from xBR: {animation_id}")
    contract_digests = {}
    for resref in sorted(old_by_resref):
        old_contract = resource_contract_digest(old_by_resref[resref])
        new_contract = resource_contract_digest(new_by_resref[resref])
        if old_contract != new_contract:
            raise RuntimeError(f"replacement metadata differs from xBR: {animation_id} {resref}")
        contract_digests[resref] = new_contract
    expected_resrefs = [str(value).upper() for value in specification["expected_resrefs"]]
    if sorted(expected_resrefs) != sorted(new_by_resref):
        raise RuntimeError(f"replacement expected resrefs differ: {animation_id}")
    logical_digest = catalog_source_component_sha256(2, new_records)
    if logical_digest in parent["logical_digests"]:
        raise RuntimeError(f"replacement logical digest did not change: {animation_id}")
    return {
        "animation_id": animation_id,
        "owner": expected_owner,
        "old_component_index": expected_indices[0],
        "old_component": old_component,
        "old_shards": old_shards,
        "old_shard_infos": old_infos,
        "old_logical_digest": expected_logical[0],
        "p2_manifest": manifest_path,
        "p2_manifest_sha256": expected_manifest_sha,
        "records": new_records,
        "resrefs": sorted(new_by_resref),
        "resource_contract_digests": contract_digests,
        "logical_digest": logical_digest,
    }


def emit_replacement_shards(
    replacement: dict[str, Any], pack_dir: Path
) -> None:
    partitions = partition_registry_resources(
        replacement["records"],
        maximum_resources=MAX_RESOURCES,
        maximum_bytes=maximum_registry_bytes(2),
        maximum_shards=MAX_REGISTRY_SET_SHARDS,
    )
    infos: list[dict[str, Any]] = []
    resources: list[list[str]] = []
    raw_entries: list[bytes] = []
    for index, records in enumerate(partitions):
        scratch = pack_dir / f".replacement-{replacement['animation_id'][2:]}-{index:02d}.tmp"
        info = write_compressed_catalog_registry_records(scratch, 2, records)
        destination = pack_dir / catalog_shard_filename(info["sha256"])
        if destination.exists():
            raise RuntimeError("replacement shard filename collision")
        scratch.replace(destination)
        info["registry"] = "iee-assets/creature-sprites/" + destination.name
        infos.append(info)
        resources.append(list(info["resources"]))
        raw_entries.append(catalog_shard_entry_bytes(info, destination))
    replacement["new_shards"] = infos
    replacement["new_shard_resources"] = resources
    replacement["new_component_digest"] = catalog_component_digest(2, raw_entries)


def assemble_catalog(
    parent: dict[str, Any], replacements: list[dict[str, Any]]
) -> dict[str, Any]:
    parent_index = parent["index"]
    replacement_by_id = {value["animation_id"]: value for value in replacements}
    if len(replacement_by_id) != len(replacements):
        raise RuntimeError("duplicate replacement animation")
    replaced_components = {int(value["old_component_index"]) for value in replacements}
    references_after = {
        index
        for animation in parent_index["animations"]
        if animation["animation_id"] not in replacement_by_id
        for index in animation["component_indices"]
    }
    dropped_components = replaced_components - references_after
    kept_component_indices = [
        index for index in range(len(parent_index["components"])) if index not in dropped_components
    ]
    kept_shard_indices = [
        shard_index
        for component_index in kept_component_indices
        for shard_index in range(
            int(parent_index["components"][component_index]["shard_start"]),
            int(parent_index["components"][component_index]["shard_start"])
            + int(parent_index["components"][component_index]["shard_count"]),
        )
    ]
    component_map = {old: new for new, old in enumerate(kept_component_indices)}
    shard_map = {old: new for new, old in enumerate(kept_shard_indices)}
    shards = []
    shard_resources: list[list[str]] = []
    parent_directory_by_shard: dict[int, dict[int, str]] = {}
    for entry in parent_index["directory"]:
        ordinal_map = parent_directory_by_shard.setdefault(int(entry["shard_index"]), {})
        ordinal = int(entry["resource_ordinal"])
        existing = ordinal_map.setdefault(ordinal, str(entry["resref"]))
        if existing != str(entry["resref"]):
            raise RuntimeError("parent shard ordinal conflict")
    for old_index in kept_shard_indices:
        value = dict(parent_index["shards"][old_index])
        value["index"] = len(shards)
        shards.append(value)
        ordinals = parent_directory_by_shard[old_index]
        expected = int(value["resource_count"])
        if sorted(ordinals) != list(range(expected)):
            raise RuntimeError("parent shard resource directory is incomplete")
        shard_resources.append([ordinals[index] for index in range(expected)])
    components = []
    logical_digests = []
    for old_index in kept_component_indices:
        old = parent_index["components"][old_index]
        old_shards = list(
            range(int(old["shard_start"]), int(old["shard_start"]) + int(old["shard_count"]))
        )
        mapped = [shard_map[index] for index in old_shards]
        if mapped != list(range(mapped[0], mapped[0] + len(mapped))):
            raise RuntimeError("kept parent component shards became non-contiguous")
        value = dict(old)
        value["index"] = len(components)
        value["shard_start"] = mapped[0]
        components.append(value)
        logical_digests.append(parent["logical_digests"][old_index])
    new_component_by_animation: dict[str, int] = {}
    for replacement in sorted(replacements, key=lambda value: int(value["animation_id"], 16)):
        shard_start = len(shards)
        for info, resources in zip(
            replacement["new_shards"], replacement["new_shard_resources"], strict=True
        ):
            value = {key: info[key] for key in (
                "sha256", "crc32", "resource_count", "frame_count", "index_bytes", "registry_bytes"
            )}
            value["index"] = len(shards)
            value["registry"] = info["registry"]
            shards.append(value)
            shard_resources.append(resources)
        component_index = len(components)
        new_component_by_animation[replacement["animation_id"]] = component_index
        component_shards = shards[shard_start:]
        components.append(
            {
                "index": component_index,
                "digest": replacement["new_component_digest"],
                "shard_start": shard_start,
                "shard_count": len(replacement["new_shards"]),
                "resource_count": sum(int(value["resource_count"]) for value in component_shards),
                "frame_count": sum(int(value["frame_count"]) for value in component_shards),
                "index_bytes": sum(int(value["index_bytes"]) for value in component_shards),
                "registry_bytes": sum(int(value["registry_bytes"]) for value in component_shards),
            }
        )
        logical_digests.append(replacement["logical_digest"])
    animations = []
    for animation in parent_index["animations"]:
        animation_id = animation["animation_id"]
        indices = (
            [new_component_by_animation[animation_id]]
            if animation_id in replacement_by_id
            else [component_map[int(index)] for index in animation["component_indices"]]
        )
        animations.append(
            {
                "animation_id": animation_id,
                "owner": int(animation["owner"]),
                "component_indices": indices,
            }
        )
    directory = []
    for animation in animations:
        animation_id = animation["animation_id"]
        for component_index in animation["component_indices"]:
            component = components[component_index]
            for shard_index in range(
                int(component["shard_start"]),
                int(component["shard_start"]) + int(component["shard_count"]),
            ):
                for ordinal, resref in enumerate(shard_resources[shard_index]):
                    directory.append(
                        {
                            "animation_id": animation_id,
                            "resref": resref,
                            "component_index": component_index,
                            "shard_index": shard_index,
                            "resource_ordinal": ordinal,
                        }
                    )
    return {
        "animations": animations,
        "components": components,
        "shards": shards,
        "directory": directory,
        "logical_digests": logical_digests,
        "kept_component_indices": kept_component_indices,
        "kept_shard_indices": kept_shard_indices,
        "component_map": component_map,
        "shard_map": shard_map,
        "new_component_by_animation": new_component_by_animation,
        "dropped_components": sorted(dropped_components),
    }


def calculate_storage(
    parent: dict[str, Any], assembled: dict[str, Any], replacements: list[dict[str, Any]]
) -> dict[str, Any]:
    storage = parent["manifest"]["storage"]
    dropped_shards = set(range(len(parent["index"]["shards"]))) - set(
        assembled["kept_shard_indices"]
    )
    inspected_old: dict[int, dict[str, Any]] = {}
    for replacement in replacements:
        component = replacement["old_component"]
        for offset, info in enumerate(replacement["old_shard_infos"]):
            inspected_old[int(component["shard_start"]) + offset] = info
    if not dropped_shards.issubset(inspected_old):
        raise RuntimeError("storage proof missing for dropped parent shard")
    new_infos = [info for replacement in replacements for info in replacement["new_shards"]]
    stored = int(storage["stored_index_bytes"]) - sum(
        int(inspected_old[index]["stored_index_bytes"]) for index in dropped_shards
    ) + sum(int(info["stored_index_bytes"]) for info in new_infos)
    compressed = int(storage["compressed_frame_count"]) - sum(
        int(inspected_old[index]["compressed_frame_count"]) for index in dropped_shards
    ) + sum(int(info["compressed_frame_count"]) for info in new_infos)
    raw = int(storage["raw_frame_count"]) - sum(
        int(inspected_old[index]["raw_frame_count"]) for index in dropped_shards
    ) + sum(int(info["raw_frame_count"]) for info in new_infos)
    total_index = sum(int(value["index_bytes"]) for value in assembled["components"])
    return {
        "stored_index_bytes": stored,
        "compressed_frame_count": compressed,
        "raw_frame_count": raw,
        "index_storage_ratio": stored / total_index,
    }


def validate_diff(
    parent: dict[str, Any], assembled: dict[str, Any], replacements: list[dict[str, Any]]
) -> dict[str, Any]:
    targets = {value["animation_id"] for value in replacements}
    old_animations = {value["animation_id"]: value for value in parent["index"]["animations"]}
    new_animations = {value["animation_id"]: value for value in assembled["animations"]}
    if old_animations.keys() != new_animations.keys():
        raise RuntimeError("derived animation inventory differs")
    unchanged = 0
    for animation_id, old in old_animations.items():
        new = new_animations[animation_id]
        if int(old["owner"]) != int(new["owner"]):
            raise RuntimeError(f"derived owner differs: {animation_id}")
        if animation_id not in targets:
            expected = [assembled["component_map"][int(index)] for index in old["component_indices"]]
            if new["component_indices"] != expected:
                raise RuntimeError(f"unrelated animation mapping differs: {animation_id}")
            unchanged += 1
    old_directory = parent["index"]["directory"]
    new_directory = assembled["directory"]
    old_resources = {}
    new_resources = {}
    for entry in old_directory:
        old_resources.setdefault(entry["animation_id"], []).append(entry["resref"])
    for entry in new_directory:
        new_resources.setdefault(entry["animation_id"], []).append(entry["resref"])
    if {key: sorted(value) for key, value in old_resources.items()} != {
        key: sorted(value) for key, value in new_resources.items()
    }:
        raise RuntimeError("derived animation resources differ")
    return {
        "unchanged_animations": unchanged,
        "replaced_animations": sorted(targets),
        "animation_resources_identical": True,
        "owners_identical": True,
        "unrelated_component_mappings_preserved": True,
    }


def input_lock(job_path: Path, job: dict[str, Any], parent: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "bg2-upscale-reboutcx-derived-catalog-input-lock-v1",
        "job_sha256": sha256_file(job_path),
        "builder_sha256": sha256_file(Path(__file__)),
        "catalog_writer_sha256": sha256_file(SCRIPT_DIR / "run_creature_sprite_x2.py"),
        "parent": {
            "pointer_sha256": sha256_file(parent["pointer_path"]),
            "generation_id": parent["pointer"]["generation_id"],
            "build_manifest_sha256": sha256_file(parent["manifest_path"]),
            "catalog_sha256": sha256_file(parent["catalog_path"]),
        },
        "replacements": [
            {
                "animation_id": value["animation_id"],
                "reboutcx_manifest_sha256": value["reboutcx_manifest_sha256"],
            }
            for value in job["replacements"]
        ],
    }


def output_paths(job: dict[str, Any], generation_id: str) -> tuple[Path, Path, Path]:
    run_dir = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)
    generation = run_dir / "generations" / generation_id.lower()
    return run_dir, generation, generation / "build"


def build(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if (
        job.get("schema") != JOB_SCHEMA
        or job.get("installable") is not False
        or int(job.get("target_scale", 0)) != 2
        or not job.get("replacements")
    ):
        raise RuntimeError("invalid or installable derived catalog job")
    parent = parent_context(job)
    replacements = [load_replacement(value, parent) for value in job["replacements"]]
    lock = input_lock(job_path, job, parent)
    generation_id = canonical_json_sha256(lock)
    run_dir, generation, output = output_paths(job, generation_id)
    if output.exists():
        raise RuntimeError(f"derived catalog generation exists: {output}")
    generation.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="build-", dir=generation))
    try:
        pack_dir = temporary / "iee-assets" / "creature-sprites"
        pack_dir.mkdir(parents=True)
        for replacement in replacements:
            emit_replacement_shards(replacement, pack_dir)
        assembled = assemble_catalog(parent, replacements)
        for old_shard_index in assembled["kept_shard_indices"]:
            shard = parent["index"]["shards"][old_shard_index]
            name = Path(str(shard["registry"])).name
            source = parent["pack_dir"] / name
            destination = pack_dir / name
            if not source.is_file() or destination.exists():
                raise RuntimeError(f"parent shard unavailable or colliding: {name}")
            os.link(source, destination)
            if not os.path.samefile(source, destination):
                raise RuntimeError(f"parent shard is not hardlinked: {name}")
        storage = calculate_storage(parent, assembled, replacements)
        catalog_path = pack_dir / "CreatureSprites-XN.catalog"
        info = write_registry_catalog_index(
            catalog_path,
            2,
            assembled["animations"],
            assembled["components"],
            assembled["shards"],
            assembled["directory"],
            assembled["logical_digests"],
            storage,
        )
        diff = validate_diff(parent, assembled, replacements)
        sealed = read_sealed_catalog_index(catalog_path, info["sha256"])
        if (
            sealed["animations"] != sealed_animations(info["animations"])
            or sealed["components"] != info["components"]
            or sealed["shards"] != info["shards"]
            or sealed["directory"] != sorted(
                assembled["directory"],
                key=lambda item: (int(item["animation_id"], 16), str(item["resref"])),
            )
        ):
            raise RuntimeError("derived catalog binary round-trip differs")
        provenance = temporary / "provenance"
        provenance.mkdir()
        shutil.copyfile(job_path, provenance / "job.json")
        shutil.copyfile(parent["manifest_path"], provenance / "parent-build-manifest.json")
        for replacement in replacements:
            shutil.copyfile(
                replacement["p2_manifest"],
                provenance / f"reboutcx-{replacement['animation_id'][2:].lower()}-manifest.json",
            )
        replacement_reports = []
        for replacement in replacements:
            new_index = assembled["new_component_by_animation"][replacement["animation_id"]]
            new_component = assembled["components"][new_index]
            replacement_reports.append(
                {
                    "animation_id": replacement["animation_id"],
                    "old_component_index": replacement["old_component_index"],
                    "old_component_digest": replacement["old_component"]["digest"],
                    "old_logical_digest": replacement["old_logical_digest"],
                    "old_shard_sha256s": [value["sha256"] for value in replacement["old_shards"]],
                    "new_component_index": new_index,
                    "new_component_digest": new_component["digest"],
                    "new_logical_digest": replacement["logical_digest"],
                    "new_shard_sha256s": [value["sha256"] for value in replacement["new_shards"]],
                    "resrefs": replacement["resrefs"],
                    "resource_contract_digests": replacement["resource_contract_digests"],
                    "reboutcx_manifest": relative(replacement["p2_manifest"]),
                    "reboutcx_manifest_sha256": replacement["p2_manifest_sha256"],
                }
            )
        manifest = {
            "schema": BUILD_SCHEMA,
            "status": "built-offline-verified",
            "installable": False,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "job_file": relative(job_path),
            "job_sha256": sha256_file(job_path),
            "job_snapshot": "provenance/job.json",
            "job_snapshot_sha256": sha256_file(provenance / "job.json"),
            "generation_id": generation_id,
            "input_lock": lock,
            "method": {
                "kind": "mixed-derived-catalog-v1",
                "baseline": parent["manifest"]["method"],
                "replacement": "ReboutCX x4 -> BOX x2 -> classed OKLab indexed",
                "target_scale": 2,
            },
            "parent": {
                "pointer": relative(parent["pointer_path"]),
                "pointer_sha256": sha256_file(parent["pointer_path"]),
                "generation_id": parent["pointer"]["generation_id"],
                "build_manifest": relative(parent["manifest_path"]),
                "build_manifest_sha256": sha256_file(parent["manifest_path"]),
                "catalog_sha256": sha256_file(parent["catalog_path"]),
                "logical_content_sha256": parent["manifest"]["registry_catalog_logical_content_sha256"],
            },
            "registry_catalog": "iee-assets/creature-sprites/CreatureSprites-XN.catalog",
            "registry_scale": 2,
            "registry_catalog_sha256": info["sha256"],
            "registry_catalog_bytes": info["registry_catalog_bytes"],
            "registry_catalog_directory_count": info["directory_count"],
            "registry_catalog_directory_sha256": info["directory_sha256"],
            "registry_catalog_logical_component_digests": info["logical_component_digests"],
            "registry_catalog_logical_content_sha256": info["logical_content_sha256"],
            "animations": sealed_animations(info["animations"]),
            "components": info["components"],
            "shards": info["shards"],
            "totals": {key: info[key] for key in (
                "total_resources", "total_frames", "total_index_bytes", "total_registry_bytes"
            )},
            "storage": {
                "shard_registry_version": CATALOG_SHARD_REGISTRY_VERSION,
                "frame_storage": "XPRESS_HUFF-or-raw-per-frame-v1",
                **storage,
            },
            "replacements": replacement_reports,
            "validation": {
                **diff,
                "parent_shards_reused": len(assembled["kept_shard_indices"]),
                "parent_shards_dropped_from_index": sorted(
                    set(range(len(parent["index"]["shards"])))
                    - set(assembled["kept_shard_indices"])
                ),
                "replacement_shards_verified": sum(len(value["new_shards"]) for value in replacements),
                "resource_contracts_identical": True,
                "catalog_binary_round_trip_exact": True,
                "parent_full_rescan_deferred": True,
                "canonical_xbr_pointer_unchanged": True,
                "game_files_modified": False,
            },
            "code": {
                "builder": {"path": relative(Path(__file__)), "sha256": sha256_file(Path(__file__))},
                "catalog_writer": {"path": relative(SCRIPT_DIR / "run_creature_sprite_x2.py"), "sha256": sha256_file(SCRIPT_DIR / "run_creature_sprite_x2.py")},
            },
        }
        write_json(temporary / "build-manifest.json", manifest)
        temporary.replace(output)
        pointer = {
            "schema": POINTER_SCHEMA,
            "generation_id": generation_id,
            "job_sha256": sha256_file(job_path),
            "generation_dir": relative(output.parent),
            "build_manifest": "build/build-manifest.json",
            "build_manifest_sha256": sha256_file(output / "build-manifest.json"),
            "catalog_sha256": info["sha256"],
        }
        pointer_path = run_dir / "current-generation.json"
        write_json(pointer_path.with_suffix(".json.tmp"), pointer)
        os.replace(pointer_path.with_suffix(".json.tmp"), pointer_path)
        result = {
            "status": manifest["status"],
            "generation_id": generation_id,
            "run": relative(run_dir),
            "catalog_sha256": info["sha256"],
            "replacements": [value["animation_id"] for value in replacements],
            "parent_shards_reused": len(assembled["kept_shard_indices"]),
            "replacement_shards": sum(len(value["new_shards"]) for value in replacements),
        }
        print(json.dumps(result, indent=2))
        return result
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    parent = parent_context(job)
    lock = input_lock(job_path, job, parent)
    generation_id = canonical_json_sha256(lock)
    run_dir, _generation, output = output_paths(job, generation_id)
    pointer_path = run_dir / "current-generation.json"
    pointer = read_json(pointer_path)
    manifest_path = output / "build-manifest.json"
    if (
        pointer.get("schema") != POINTER_SCHEMA
        or pointer.get("generation_id") != generation_id
        or pointer.get("job_sha256") != sha256_file(job_path)
        or pointer.get("build_manifest_sha256") != sha256_file(manifest_path)
    ):
        raise RuntimeError("derived catalog pointer differs")
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != BUILD_SCHEMA
        or manifest.get("status") != "built-offline-verified"
        or manifest.get("installable") is not False
        or manifest.get("generation_id") != generation_id
        or manifest.get("input_lock") != lock
    ):
        raise RuntimeError("derived catalog manifest differs")
    for evidence in manifest["code"].values():
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != evidence["sha256"]:
            raise RuntimeError(f"derived catalog code changed: {evidence['path']}")
    catalog_path = output / manifest["registry_catalog"]
    if sha256_file(catalog_path) != manifest["registry_catalog_sha256"]:
        raise RuntimeError("derived catalog hash differs")
    index = read_sealed_catalog_index(catalog_path, manifest["registry_catalog_sha256"])
    for key in ("animations", "components", "shards"):
        if index[key] != manifest[key]:
            raise RuntimeError(f"derived catalog {key} differ")
    expected_directory = sorted(
        index["directory"],
        key=lambda item: (int(item["animation_id"], 16), str(item["resref"])),
    )
    if index["directory"] != expected_directory:
        raise RuntimeError("derived catalog directory order differs")
    for key in ("total_resources", "total_frames", "total_index_bytes", "total_registry_bytes"):
        if int(index[key]) != int(manifest["totals"][key]):
            raise RuntimeError(f"derived catalog {key} differs")
    logical_content_sha256 = catalog_logical_content_digest(
        2, manifest["animations"], manifest["registry_catalog_logical_component_digests"]
    )
    if logical_content_sha256 != manifest["registry_catalog_logical_content_sha256"]:
        raise RuntimeError("derived catalog logical content hash differs")
    expected_names = {Path(value["registry"]).name for value in manifest["shards"]}
    actual_names = {
        path.name
        for path in catalog_path.parent.glob("CreatureSprites-XN-*.registry")
    }
    if actual_names != expected_names:
        raise RuntimeError("derived shard filenames are not exact")
    replacement_shards = {
        digest
        for replacement in manifest["replacements"]
        for digest in replacement["new_shard_sha256s"]
    }
    parent_shards = {value["sha256"]: value for value in parent["index"]["shards"]}
    checked_new = 0
    checked_parent_links = 0
    for shard in manifest["shards"]:
        path = catalog_path.parent / Path(shard["registry"]).name
        if shard["sha256"] in replacement_shards:
            info = inspect_registry(path, include_resource_records=True)
            for key in ("sha256", "crc32", "resource_count", "frame_count", "index_bytes", "registry_bytes"):
                if info[key] != shard[key]:
                    raise RuntimeError(f"replacement shard differs: {shard['sha256']} {key}")
            checked_new += 1
        else:
            old = parent_shards.get(shard["sha256"])
            source = parent["pack_dir"] / Path(str(old["registry"])).name if old else None
            if source is None or not source.is_file() or not os.path.samefile(source, path):
                raise RuntimeError(f"parent shard hardlink differs: {shard['sha256']}")
            if path.stat().st_size != int(shard["registry_bytes"]):
                raise RuntimeError(f"parent shard size differs: {shard['sha256']}")
            checked_parent_links += 1
    targets = {value["animation_id"] for value in manifest["replacements"]}
    old_resources = {}
    new_resources = {}
    for entry in parent["index"]["directory"]:
        old_resources.setdefault(entry["animation_id"], []).append(entry["resref"])
    for entry in index["directory"]:
        new_resources.setdefault(entry["animation_id"], []).append(entry["resref"])
    if {key: sorted(value) for key, value in old_resources.items()} != {
        key: sorted(value) for key, value in new_resources.items()
    }:
        raise RuntimeError("verified derived resources differ from parent")
    old_animations = {value["animation_id"]: value for value in parent["index"]["animations"]}
    new_animations = {value["animation_id"]: value for value in index["animations"]}
    old_logical = parent["logical_digests"]
    new_logical = manifest["registry_catalog_logical_component_digests"]
    changed_logical = 0
    for animation_id, old in old_animations.items():
        if animation_id in targets:
            changed_logical += 1
            continue
        old_values = [old_logical[index] for index in old["component_indices"]]
        new_values = [new_logical[index] for index in new_animations[animation_id]["component_indices"]]
        if old_values != new_values:
            raise RuntimeError(f"unrelated logical component changed: {animation_id}")
    if changed_logical != len(targets):
        raise RuntimeError("replacement logical coverage differs")
    if sha256_file(parent["pointer_path"]) != job["parent"]["pointer_sha256"]:
        raise RuntimeError("canonical xBR pointer changed during verification")
    result = {
        "status": "verified",
        "generation_id": generation_id,
        "catalog_sha256": manifest["registry_catalog_sha256"],
        "animations": len(index["animations"]),
        "unchanged_animations": len(index["animations"]) - len(targets),
        "replacements": sorted(targets),
        "parent_shards_hardlinked": checked_parent_links,
        "replacement_shards_verified": checked_new,
        "canonical_xbr_pointer_unchanged": True,
    }
    print(json.dumps(result, indent=2))
    return result


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("build", "verify"):
        command = commands.add_parser(name)
        command.add_argument("job", type=Path)
    args = parser.parse_args(argv)
    job_path = args.job.resolve()
    if args.command == "build":
        build(job_path)
    else:
        verify(job_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
