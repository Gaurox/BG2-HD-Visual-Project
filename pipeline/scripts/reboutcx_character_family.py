"""Bounded audit/orchestration for one complete false-color Character family."""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from reboutcx_batch import is_null_frame
from reboutcx_quantize import semantic_classes_for_job
from run_creature_sprite_x2 import load_source_frames
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
JOB_SCHEMA = "bg2-upscale-reboutcx-character-family-job-v1"
AUDIT_SCHEMA = "bg2-upscale-reboutcx-character-family-audit-v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def sha256_array(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest().upper()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def require_hash(path: Path, expected: str, label: str) -> None:
    if sha256_file(path) != expected.upper():
        raise RuntimeError(f"{label} hash differs")


def member_layer(source_job: dict[str, Any]) -> tuple[str, int | None, str | None]:
    animation = source_job["animation"]
    if "armor_code" in animation:
        return "body", int(animation["armor_code"]), None
    layer = animation.get("layer")
    if not isinstance(layer, dict) or not layer.get("kind"):
        raise RuntimeError("Character member has no body/equipment layer")
    item = layer.get("item_resref")
    return str(layer["kind"]), None, str(item).upper() if item else None


def completed_members(job: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for item in job["completed_members"]:
        prefix = str(item["bam_prefix"]).upper()
        if prefix in result:
            raise RuntimeError(f"duplicate completed member: {prefix}")
        job_path = resolve_path_reference(item["job"], required=True, root=PROJECT_ROOT)
        manifest_path = resolve_path_reference(item["manifest"], required=True, root=PROJECT_ROOT)
        require_hash(job_path, str(item["job_sha256"]), f"{prefix} completed job")
        require_hash(manifest_path, str(item["manifest_sha256"]), f"{prefix} completed manifest")
        result[prefix] = item
    return result


def audit(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if job.get("schema") != JOB_SCHEMA or job.get("installable") is not False:
        raise RuntimeError("invalid Character family job")

    source_job_path = resolve_path_reference(
        job["source_family_job"], required=True, root=PROJECT_ROOT
    )
    require_hash(source_job_path, str(job["source_family_job_sha256"]), "source family job")
    source_job = read_json(source_job_path)
    members = source_job["members"]

    pointer_path = resolve_path_reference(
        job["parent_catalog_pointer"], required=True, root=PROJECT_ROOT
    )
    require_hash(pointer_path, str(job["parent_catalog_pointer_sha256"]), "catalog pointer")
    pointer = read_json(pointer_path)
    build_path = resolve_path_reference(pointer["generation_dir"], root=PROJECT_ROOT) / str(
        pointer["build_manifest"]
    )
    require_hash(build_path, str(pointer["build_manifest_sha256"]), "catalog build")
    build = read_json(build_path)
    source_member = next(
        item for item in build["source_members"] if item["animation_id"] == job["animation_id"]
    )
    prefixes = [str(value).upper() for value in source_member["bam_prefixes"]]
    component_indices = [int(value) for value in source_member["component_indices"]]
    if len(members) != len(prefixes) or len(prefixes) != len(component_indices):
        raise RuntimeError("source family membership lengths differ")

    template_path = resolve_path_reference(
        job["contract_template_job"], required=True, root=PROJECT_ROOT
    )
    require_hash(template_path, str(job["contract_template_job_sha256"]), "contract template")
    classes, classes_id = semantic_classes_for_job(read_json(template_path))
    classified = {index for indices in classes.values() for index in indices}
    completed = completed_members(job)
    components = {int(item["index"]): item for item in build["components"]}
    animation_components = {
        item["animation_id"]: {int(value) for value in item["component_indices"]}
        for item in build["animations"]
    }

    reports: list[dict[str, Any]] = []
    layer_counts: Counter[str] = Counter()
    palette_hashes: set[str] = set()
    total_resources = total_frames = total_null = total_model_frames = 0
    total_model_pixels = 0

    for member_ref, prefix, component_index in zip(members, prefixes, component_indices):
        member_path = resolve_path_reference(member_ref, required=True, root=PROJECT_ROOT)
        member_job = read_json(member_path)
        if str(member_job["animation"]["bam_prefix"]).upper() != prefix:
            raise RuntimeError(f"{prefix}: source member order differs")
        layer, armor_code, item_resref = member_layer(member_job)
        source_manifest_path = (
            resolve_path_reference(member_job["paths"]["source_dir"], required=True, root=PROJECT_ROOT)
            / "manifest.json"
        )
        frames, resources, source_manifest = load_source_frames(source_manifest_path)
        if (
            source_manifest["animation_id"] != job["animation_id"]
            or source_manifest["runtime_profile"] != job["runtime_profile"]
            or str(source_manifest["bam_prefix"]).upper() != prefix
            or source_manifest["layer"]["kind"] != layer
        ):
            raise RuntimeError(f"{prefix}: source contract differs")

        seen_payloads: set[tuple[str, str]] = set()
        model_frames = model_pixels = 0
        used = np.zeros(256, dtype=bool)
        transparencies: set[int] = set()
        for resource in resources:
            transparencies.update(int(frame.transparent) for frame in resource["frames"])
            if resource["frames"]:
                palette_hashes.add(sha256_array(resource["frames"][0].palette))
            for frame in resource["frames"]:
                used[np.unique(frame.indices)] = True
            payload = (sha256_file(resource["bam_path"]), sha256_file(resource["source_path"]))
            if payload in seen_payloads:
                continue
            seen_payloads.add(payload)
            for frame in resource["frames"]:
                if not is_null_frame(frame, 2):
                    model_frames += 1
                    model_pixels += int(frame.width) * int(frame.height)
        invalid_indices = [int(value) for value in np.flatnonzero(used) if value not in classified]
        if transparencies != {0} or invalid_indices:
            raise RuntimeError(f"{prefix}: incompatible false-color indices/transparency")

        null_frames = sum(is_null_frame(frame, 2) for frame in frames)
        shared_with = sorted(
            animation_id
            for animation_id, indices in animation_components.items()
            if component_index in indices and animation_id != job["animation_id"]
        )
        component = components[component_index]
        reports.append(
            {
                "bam_prefix": prefix,
                "layer": layer,
                "armor_code": armor_code,
                "item_resref": item_resref,
                "source_job": relative(member_path),
                "source_job_sha256": sha256_file(member_path),
                "source_manifest": relative(source_manifest_path),
                "source_manifest_sha256": sha256_file(source_manifest_path),
                "component_index": component_index,
                "component_digest": component["digest"],
                "resources": len(resources),
                "frames": len(frames),
                "null_frames": null_frames,
                "unique_source_payloads": len(seen_payloads),
                "unique_model_frames": model_frames,
                "model_source_pixels": model_pixels,
                "shared_with_animation_ids": shared_with,
                "reboutcx_status": "completed" if prefix in completed else "pending",
            }
        )
        layer_counts[layer] += 1
        total_resources += len(resources)
        total_frames += len(frames)
        total_null += null_frames
        total_model_frames += model_frames
        total_model_pixels += model_pixels
        del frames, resources, source_manifest
        gc.collect()

    completed_model_frames = sum(
        item["unique_model_frames"] for item in reports if item["reboutcx_status"] == "completed"
    )
    reference_manifests = [read_json(resolve_path_reference(item["manifest"], root=PROJECT_ROOT)) for item in completed.values()]
    reference_seconds = sum(float(item["timing_seconds"]["reboutcx"]) for item in reference_manifests)
    reference_frames = sum(int(item["coverage"]["unique_model_frames"]) for item in reference_manifests)
    seconds_per_frame = reference_seconds / reference_frames
    pending_model_frames = total_model_frames - completed_model_frames

    result = {
        "schema": AUDIT_SCHEMA,
        "status": "audited-pending-gpu",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "animation_id": job["animation_id"],
        "runtime_profile": job["runtime_profile"],
        "semantic_classes_id": classes_id,
        "parent_catalog_generation": pointer["generation_id"],
        "parent_catalog_build_manifest_sha256": pointer["build_manifest_sha256"],
        "totals": {
            "members": len(reports),
            "completed_members": len(completed),
            "pending_members": len(reports) - len(completed),
            "layers": dict(sorted(layer_counts.items())),
            "resources": total_resources,
            "frames": total_frames,
            "null_frames": total_null,
            "unique_model_frames": total_model_frames,
            "pending_model_frames": pending_model_frames,
            "model_source_pixels": total_model_pixels,
            "source_palette_sha256_count": len(palette_hashes),
            "shared_components": sum(bool(item["shared_with_animation_ids"]) for item in reports),
        },
        "estimate": {
            "reference_seconds_per_model_frame": seconds_per_frame,
            "pending_gpu_model_seconds": pending_model_frames * seconds_per_frame,
        },
        "members": reports,
    }
    output = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT) / "audit.json"
    if output.exists():
        raise RuntimeError(f"audit already exists: {relative(output)}")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output)
    summary = {
        "status": result["status"],
        "members": result["totals"]["members"],
        "pending_members": result["totals"]["pending_members"],
        "frames": result["totals"]["frames"],
        "pending_model_frames": pending_model_frames,
        "estimated_gpu_minutes": round(result["estimate"]["pending_gpu_model_seconds"] / 60, 1),
        "audit": relative(output),
    }
    print(json.dumps(summary, separators=(",", ":")))
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("audit",))
    parser.add_argument("job", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        audit(args.job.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
