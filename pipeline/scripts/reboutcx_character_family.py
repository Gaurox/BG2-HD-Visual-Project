"""Bounded audit/orchestration for one complete false-color Character family."""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import json
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from reboutcx_batch import (
    infer_x4_box_x2,
    is_null_frame,
    load_model,
    load_palette_profiles,
    prepare_inference_rgb,
)
from reboutcx_quantize import semantic_classes_for_job
from run_creature_sprite_x2 import load_source_frames
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]
JOB_SCHEMA = "bg2-upscale-reboutcx-character-family-job-v1"
AUDIT_SCHEMA = "bg2-upscale-reboutcx-character-family-audit-v1"
PREPARED_SCHEMA = "bg2-upscale-reboutcx-character-family-prepared-v1"
RUN_SCHEMA = "bg2-upscale-reboutcx-character-family-run-v1"
FULL_JOB_SCHEMA = "bg2-upscale-reboutcx-full-job-v1"
FULL_RUN_SCHEMA = "bg2-upscale-reboutcx-full-run-v1"
FULL_RUN_NAME = "reboutcx-p8-full-v1"
CATALOG_JOB_SCHEMA = "bg2-upscale-reboutcx-derived-catalog-job-v1"
CATALOG_SEED_JOB = PROJECT_ROOT / "sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-character-6100-test-v1.json"
CATALOG_OUTPUT_JOB = PROJECT_ROOT / "sprite/catalogs/creature-x2-reboutcx/jobs/catalog-reboutcx-character-6100-complete-p8-v1.json"
CATALOG_RUN_DIR = PROJECT_ROOT / "sprite/catalogs/creature-x2-reboutcx/runs/catalog-reboutcx-character-6100-complete-p8-v1"


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


def write_json_atomic(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def run_dir(job: dict[str, Any]) -> Path:
    return resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)


def load_audit(job_path: Path, job: dict[str, Any]) -> dict[str, Any]:
    path = run_dir(job) / "audit.json"
    audit_report = read_json(path)
    if (
        audit_report.get("schema") != AUDIT_SCHEMA
        or audit_report.get("status") != "audited-pending-gpu"
        or audit_report.get("job_sha256") != sha256_file(job_path)
        or audit_report.get("animation_id") != job["animation_id"]
    ):
        raise RuntimeError("invalid or stale Character family audit")
    return audit_report


def load_family_job(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    if job.get("schema") != JOB_SCHEMA or job.get("installable") is not False:
        raise RuntimeError("invalid Character family job")
    return job


def load_template(job: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    path = resolve_path_reference(
        job["contract_template_job"], required=True, root=PROJECT_ROOT
    )
    require_hash(path, str(job["contract_template_job_sha256"]), "contract template")
    template = read_json(path)
    if template.get("schema") != FULL_JOB_SCHEMA:
        raise RuntimeError("invalid Character contract template")
    return path, template


def prepared_path(job: dict[str, Any]) -> Path:
    return run_dir(job) / "prepared.json"


def component_job_path(member: dict[str, Any]) -> Path:
    source_manifest = resolve_path_reference(
        member["source_manifest"], required=True, root=PROJECT_ROOT
    )
    return source_manifest.parent.parent / "jobs" / f"{FULL_RUN_NAME}.json"


def validate_component_job(
    component_job: dict[str, Any],
    member: dict[str, Any],
    template: dict[str, Any],
) -> None:
    expected_paths = {
        "source_manifest": member["source_manifest"],
        "run_dir": relative(
            resolve_path_reference(member["source_manifest"], root=PROJECT_ROOT).parent.parent
            / "runs"
            / FULL_RUN_NAME
        ),
        "chainner_python": template["paths"]["chainner_python"],
        "reboutcx_model": template["paths"]["reboutcx_model"],
        "scalepix": template["paths"]["scalepix"],
    }
    contract_keys = (
        "tools",
        "reboutcx",
        "semantic_classes_id",
        "null_frame_marker",
        "palette_reference",
    )
    if (
        component_job.get("schema") != FULL_JOB_SCHEMA
        or component_job.get("installable") is not False
        or component_job.get("scope") != "full-animation"
        or component_job.get("animation_id") != "0x6100"
        or component_job.get("runtime_profile") != "character-bg2ee-2.7.3.0"
        or component_job.get("layer") != member["layer"]
        or component_job.get("source_manifest_sha256")
        != member["source_manifest_sha256"]
        or component_job.get("paths") != expected_paths
        or any(component_job.get(key) != template.get(key) for key in contract_keys)
    ):
        raise RuntimeError(f"{member['bam_prefix']}: prepared job contract differs")
    if member["layer"] == "body":
        if component_job.get("armor_code") != member["armor_code"]:
            raise RuntimeError(f"{member['bam_prefix']}: armor code differs")
    elif component_job.get("item_resref") != member["item_resref"]:
        raise RuntimeError(f"{member['bam_prefix']}: item resref differs")
    source_manifest = read_json(
        resolve_path_reference(member["source_manifest"], required=True, root=PROJECT_ROOT)
    )
    expected_inventory = [{"name": str(item["name"]).upper()} for item in source_manifest["bams"]]
    if component_job.get("source_inventory") != expected_inventory:
        raise RuntimeError(f"{member['bam_prefix']}: prepared inventory differs")
    reference = component_job.get("reference", {})
    if (
        not reference.get("resref")
        or not isinstance(reference.get("frame"), int)
        or len(str(reference.get("x4_pixel_sha256", ""))) != 64
        or len(str(reference.get("x2_pixel_sha256", ""))) != 64
    ):
        raise RuntimeError(f"{member['bam_prefix']}: invalid prepared reference")


def make_component_job(
    member: dict[str, Any],
    template: dict[str, Any],
    descriptor: Any,
    reference_palette: np.ndarray,
) -> dict[str, Any]:
    source_manifest_path = resolve_path_reference(
        member["source_manifest"], required=True, root=PROJECT_ROOT
    )
    frames, resources, _source_manifest = load_source_frames(source_manifest_path)
    marker = int(template["null_frame_marker"])
    witness = None
    inference_rgb = None
    for frame in frames:
        if is_null_frame(frame, marker):
            continue
        candidate = prepare_inference_rgb(frame, reference_palette)
        if candidate is not None:
            witness = frame
            inference_rgb = candidate
            break
    if witness is None or inference_rgb is None:
        raise RuntimeError(f"{member['bam_prefix']}: no model witness frame")
    x4, x2 = infer_x4_box_x2(
        descriptor, inference_rgb, fp16=bool(template["reboutcx"]["fp16"])
    )
    component_root = source_manifest_path.parent.parent
    component_job: dict[str, Any] = {
        "schema": FULL_JOB_SCHEMA,
        "job_id": f"character-6100-{component_root.name}-{member['bam_prefix'].lower()}-{FULL_RUN_NAME}",
        "installable": False,
        "animation_id": "0x6100",
        "runtime_profile": "character-bg2ee-2.7.3.0",
        "layer": member["layer"],
        "source_inventory": [
            {"name": str(resource["source"]["name"]).upper()} for resource in resources
        ],
        "paths": {
            "source_manifest": member["source_manifest"],
            "run_dir": relative(component_root / "runs" / FULL_RUN_NAME),
            "chainner_python": template["paths"]["chainner_python"],
            "reboutcx_model": template["paths"]["reboutcx_model"],
            "scalepix": template["paths"]["scalepix"],
        },
        "source_manifest_sha256": member["source_manifest_sha256"],
        "tools": copy.deepcopy(template["tools"]),
        "reboutcx": copy.deepcopy(template["reboutcx"]),
        "semantic_classes_id": template["semantic_classes_id"],
        "null_frame_marker": marker,
        "palette_reference": copy.deepcopy(template["palette_reference"]),
        "reference": {
            "resref": witness.resref,
            "frame": witness.index,
            "x4_pixel_sha256": sha256_array(x4),
            "x2_pixel_sha256": sha256_array(x2),
        },
        "scope": "full-animation",
        "qa": {
            "background": "dark-light-green-checkerboard-quadrants",
            "groups": [
                {
                    "name": f"{member['bam_prefix'].lower()}-reference",
                    "resref": witness.resref,
                    "frames": [witness.index],
                    "duration_ms": 400,
                }
            ],
        },
    }
    if member["layer"] == "body":
        component_job["armor_code"] = member["armor_code"]
    else:
        component_job["item_resref"] = member["item_resref"]
    del frames, resources, _source_manifest, inference_rgb, x4, x2
    gc.collect()
    return component_job


def prepared_summary(path: Path, prepared: dict[str, Any]) -> None:
    print(
        json.dumps(
            {
                "status": prepared["status"],
                "pending_members": prepared["totals"]["pending_members"],
                "prepared": relative(path),
                "prepared_sha256": sha256_file(path),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )


def validate_prepared(
    path: Path,
    prepared: dict[str, Any],
    job_path: Path,
    audit_report: dict[str, Any],
    template: dict[str, Any],
) -> None:
    if (
        prepared.get("schema") != PREPARED_SCHEMA
        or prepared.get("status") != "prepared-pending-runs"
        or prepared.get("job_sha256") != sha256_file(job_path)
        or prepared.get("audit_sha256") != sha256_file(run_dir(read_json(job_path)) / "audit.json")
        or len(prepared.get("members", [])) != int(audit_report["totals"]["pending_members"])
    ):
        raise RuntimeError("invalid or stale prepared Character family")
    audit_by_prefix = {item["bam_prefix"]: item for item in audit_report["members"]}
    for record in prepared["members"]:
        member = audit_by_prefix.get(record["bam_prefix"])
        if member is None or member["reboutcx_status"] != "pending":
            raise RuntimeError("prepared Character member differs from audit")
        component_path = resolve_path_reference(record["job"], required=True, root=PROJECT_ROOT)
        require_hash(component_path, record["job_sha256"], f"{record['bam_prefix']} job")
        validate_component_job(read_json(component_path), member, template)


def prepare_execute(job_path: Path) -> dict[str, Any]:
    job = load_family_job(job_path)
    audit_report = load_audit(job_path, job)
    _template_path, template = load_template(job)
    output = prepared_path(job)
    if output.exists():
        existing = read_json(output)
        validate_prepared(output, existing, job_path, audit_report, template)
        prepared_summary(output, existing)
        return existing

    profiles, _palette_evidence = load_palette_profiles(template)
    reference_palette = profiles[0]["palette"]
    model_path = resolve_path_reference(
        template["paths"]["reboutcx_model"], required=True, root=PROJECT_ROOT
    )
    require_hash(model_path, template["reboutcx"]["model_sha256"], "ReboutCX model")
    descriptor = None
    versions: dict[str, str] | None = None
    records: list[dict[str, Any]] = []
    created_jobs = 0
    for member in audit_report["members"]:
        if member["reboutcx_status"] != "pending":
            continue
        path = component_job_path(member)
        if path.exists():
            component_job = read_json(path)
            validate_component_job(component_job, member, template)
        else:
            if descriptor is None:
                descriptor, versions = load_model(
                    model_path,
                    device=str(template["reboutcx"]["device"]),
                    fp16=bool(template["reboutcx"]["fp16"]),
                )
            component_job = make_component_job(
                member, template, descriptor, reference_palette
            )
            validate_component_job(component_job, member, template)
            write_json_atomic(path, component_job)
            created_jobs += 1
        records.append(
            {
                "bam_prefix": member["bam_prefix"],
                "component_index": member["component_index"],
                "job": relative(path),
                "job_sha256": sha256_file(path),
                "run_dir": component_job["paths"]["run_dir"],
            }
        )
    prepared = {
        "schema": PREPARED_SCHEMA,
        "status": "prepared-pending-runs",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "audit": relative(run_dir(job) / "audit.json"),
        "audit_sha256": sha256_file(run_dir(job) / "audit.json"),
        "model_sha256": template["reboutcx"]["model_sha256"],
        "versions": versions,
        "totals": {
            "pending_members": len(records),
            "reference_inferences": created_jobs,
        },
        "members": records,
    }
    write_json_atomic(output, prepared)
    prepared_summary(output, prepared)
    return prepared


def prepare_via_configured_python(job_path: Path) -> int:
    job = load_family_job(job_path)
    _template_path, template = load_template(job)
    python_path = resolve_path_reference(
        template["paths"]["chainner_python"], required=True, root=PROJECT_ROOT
    ).resolve()
    require_hash(
        python_path,
        str(template["tools"]["chainner_python_sha256"]),
        "configured chaiNNer Python",
    )
    if Path(sys.executable).resolve() == python_path:
        prepare_execute(job_path)
        return 0
    result = subprocess.run(
        [str(python_path), str(Path(__file__).resolve()), "_prepare", str(job_path)],
        check=False,
    )
    return int(result.returncode)


def run_logged(command: list[str], log_path: Path) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    if result.returncode:
        raise RuntimeError(f"child process failed; inspect {relative(log_path)}")


def build_family(job_path: Path) -> dict[str, Any]:
    job = load_family_job(job_path)
    audit_report = load_audit(job_path, job)
    _template_path, template = load_template(job)
    preparation_path = prepared_path(job)
    preparation = read_json(preparation_path)
    validate_prepared(
        preparation_path, preparation, job_path, audit_report, template
    )
    output = run_dir(job) / "manifest.json"
    if output.exists():
        manifest = read_json(output)
        if (
            manifest.get("schema") != RUN_SCHEMA
            or manifest.get("status") != "completed-pending-catalog"
            or manifest.get("job_sha256") != sha256_file(job_path)
            or manifest.get("prepared_sha256") != sha256_file(preparation_path)
        ):
            raise RuntimeError("invalid Character family manifest")
        print(json.dumps({"status": manifest["status"], "manifest": relative(output)}, separators=(",", ":")))
        return manifest

    full_script = SCRIPT_DIR / "reboutcx_full.py"
    chainner_python = resolve_path_reference(
        template["paths"]["chainner_python"], required=True, root=PROJECT_ROOT
    ).resolve()
    require_hash(
        chainner_python,
        str(template["tools"]["chainner_python_sha256"]),
        "configured chaiNNer Python",
    )
    logs = run_dir(job) / "logs"
    results: list[dict[str, Any]] = []
    started_family = time.perf_counter()
    count = len(preparation["members"])
    for position, record in enumerate(preparation["members"], start=1):
        prefix = record["bam_prefix"]
        component_path = resolve_path_reference(record["job"], required=True, root=PROJECT_ROOT)
        require_hash(component_path, record["job_sha256"], f"{prefix} prepared job")
        component_job = read_json(component_path)
        component_run = resolve_path_reference(component_job["paths"]["run_dir"], root=PROJECT_ROOT)
        component_manifest_path = component_run / "manifest.json"
        started = time.perf_counter()
        print(f"[{position}/{count}] {prefix} start", flush=True)
        if not component_manifest_path.exists():
            run_logged(
                [str(chainner_python), str(full_script), "_execute", str(component_path)],
                logs / f"{prefix.lower()}.run.log",
            )
        run_logged(
            [sys.executable, str(full_script), "verify", str(component_path)],
            logs / f"{prefix.lower()}.verify.log",
        )
        component_manifest = read_json(component_manifest_path)
        if (
            component_manifest.get("schema") != FULL_RUN_SCHEMA
            or component_manifest.get("status") != "completed-pending-human-review"
            or component_manifest.get("job_sha256") != sha256_file(component_path)
        ):
            raise RuntimeError(f"{prefix}: invalid verified component manifest")
        results.append(
            {
                "bam_prefix": prefix,
                "component_index": record["component_index"],
                "job": record["job"],
                "job_sha256": record["job_sha256"],
                "manifest": relative(component_manifest_path),
                "manifest_sha256": sha256_file(component_manifest_path),
                "resources": component_manifest["coverage"]["resources"],
                "frames": component_manifest["coverage"]["frames"],
                "model_frames": component_manifest["coverage"]["unique_model_frames"],
            }
        )
        print(
            f"[{position}/{count}] {prefix} verified {time.perf_counter() - started:.1f}s",
            flush=True,
        )
        del component_manifest
        gc.collect()

    completed = completed_members(job)
    audit_by_prefix = {item["bam_prefix"]: item for item in audit_report["members"]}
    for prefix, record in completed.items():
        results.append(
            {
                "bam_prefix": prefix,
                "component_index": audit_by_prefix[prefix]["component_index"],
                "job": record["job"],
                "job_sha256": record["job_sha256"],
                "manifest": record["manifest"],
                "manifest_sha256": record["manifest_sha256"],
                "sealed_completed_member": True,
            }
        )
    results.sort(key=lambda item: int(item["component_index"]))
    manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed-pending-catalog",
        "installable": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "audit_sha256": sha256_file(run_dir(job) / "audit.json"),
        "prepared_sha256": sha256_file(preparation_path),
        "animation_id": job["animation_id"],
        "runtime_profile": job["runtime_profile"],
        "elapsed_seconds": time.perf_counter() - started_family,
        "totals": {
            "members": len(results),
            "new_members": len(preparation["members"]),
            "sealed_members": len(completed),
        },
        "members": results,
    }
    if len(results) != int(audit_report["totals"]["members"]):
        raise RuntimeError("Character family completion count differs")
    write_json_atomic(output, manifest)
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "members": len(results),
                "manifest": relative(output),
                "manifest_sha256": sha256_file(output),
            },
            separators=(",", ":"),
        ),
        flush=True,
    )
    return manifest


def catalog_replacement(
    *,
    animation: dict[str, Any],
    component: dict[str, Any],
    logical_digest: str,
    shards: list[dict[str, Any]],
    manifest_path: Path,
    manifest: dict[str, Any],
) -> dict[str, Any]:
    return {
        "animation_id": animation["animation_id"],
        "expected_owner": int(animation["owner"]),
        "expected_component_indices": [int(component["index"])],
        "expected_component_digests": [component["digest"]],
        "expected_logical_component_digests": [logical_digest],
        "expected_shard_sha256s": [item["sha256"] for item in shards],
        "expected_resrefs": [item["resref"] for item in manifest["resources"]],
        "reboutcx_manifest": relative(manifest_path),
        "reboutcx_manifest_sha256": sha256_file(manifest_path),
    }


def catalog_family(job_path: Path) -> dict[str, Any]:
    job = load_family_job(job_path)
    family_manifest_path = run_dir(job) / "manifest.json"
    family_manifest = read_json(family_manifest_path)
    if (
        family_manifest.get("schema") != RUN_SCHEMA
        or family_manifest.get("status") != "completed-pending-catalog"
        or family_manifest.get("job_sha256") != sha256_file(job_path)
        or len(family_manifest.get("members", [])) != 65
    ):
        raise RuntimeError("invalid completed Character family")

    seed = read_json(CATALOG_SEED_JOB)
    if seed.get("schema") != CATALOG_JOB_SCHEMA or seed.get("installable") is not False:
        raise RuntimeError("invalid derived catalog seed job")
    pointer_path = resolve_path_reference(
        seed["paths"]["parent_pointer"], required=True, root=PROJECT_ROOT
    )
    require_hash(pointer_path, seed["parent"]["pointer_sha256"], "catalog parent pointer")
    pointer = read_json(pointer_path)
    parent_build_path = resolve_path_reference(pointer["generation_dir"], root=PROJECT_ROOT) / pointer["build_manifest"]
    require_hash(parent_build_path, seed["parent"]["build_manifest_sha256"], "catalog parent build")
    parent = read_json(parent_build_path)
    animation = next(
        item for item in parent["animations"] if item["animation_id"] == job["animation_id"]
    )
    components = {int(item["index"]): item for item in parent["components"]}
    logical_digests = parent["registry_catalog_logical_component_digests"]
    replacements = {
        (item["animation_id"], int(item["expected_component_indices"][0])): copy.deepcopy(item)
        for item in seed["replacements"]
    }
    family_targets: set[tuple[str, int]] = set()
    for member in family_manifest["members"]:
        component_index = int(member["component_index"])
        if component_index not in animation["component_indices"]:
            raise RuntimeError(f"{member['bam_prefix']}: component absent from 0x6100")
        manifest_path = resolve_path_reference(
            member["manifest"], required=True, root=PROJECT_ROOT
        )
        require_hash(manifest_path, member["manifest_sha256"], f"{member['bam_prefix']} manifest")
        component_manifest = read_json(manifest_path)
        if (
            component_manifest.get("schema") != FULL_RUN_SCHEMA
            or component_manifest.get("status") != "completed-pending-human-review"
            or component_manifest.get("animation_id") != job["animation_id"]
        ):
            raise RuntimeError(f"{member['bam_prefix']}: invalid catalog component manifest")
        component = components[component_index]
        start = int(component["shard_start"])
        shards = parent["shards"][start : start + int(component["shard_count"])]
        target = (job["animation_id"], component_index)
        replacements[target] = catalog_replacement(
            animation=animation,
            component=component,
            logical_digest=logical_digests[component_index],
            shards=shards,
            manifest_path=manifest_path,
            manifest=component_manifest,
        )
        family_targets.add(target)
    if len(family_targets) != 65:
        raise RuntimeError("catalog does not cover 65 distinct 0x6100 memberships")

    catalog_job = {
        "schema": CATALOG_JOB_SCHEMA,
        "job_id": "catalog-reboutcx-character-6100-complete-p8-v1",
        "installable": False,
        "target_scale": 2,
        "paths": {
            "parent_pointer": seed["paths"]["parent_pointer"],
            "run_dir": relative(CATALOG_RUN_DIR),
        },
        "parent": copy.deepcopy(seed["parent"]),
        "replacements": [
            replacements[key]
            for key in sorted(replacements, key=lambda value: (int(value[0], 16), value[1]))
        ],
    }
    if CATALOG_OUTPUT_JOB.exists():
        if read_json(CATALOG_OUTPUT_JOB) != catalog_job:
            raise RuntimeError("existing P8 catalog job differs")
    else:
        write_json_atomic(CATALOG_OUTPUT_JOB, catalog_job)

    catalog_script = SCRIPT_DIR / "reboutcx_catalog.py"
    pointer_output = CATALOG_RUN_DIR / "current-generation.json"
    logs = run_dir(job) / "logs"
    if not pointer_output.exists():
        run_logged(
            [sys.executable, str(catalog_script), "build", str(CATALOG_OUTPUT_JOB)],
            logs / "catalog.build.log",
        )
    run_logged(
        [sys.executable, str(catalog_script), "verify", str(CATALOG_OUTPUT_JOB)],
        logs / "catalog.verify.log",
    )
    catalog_pointer = read_json(pointer_output)
    result = {
        "status": "verified-pending-installation-and-human-review",
        "catalog_job": relative(CATALOG_OUTPUT_JOB),
        "catalog_job_sha256": sha256_file(CATALOG_OUTPUT_JOB),
        "family_manifest": relative(family_manifest_path),
        "family_manifest_sha256": sha256_file(family_manifest_path),
        "replacements": len(catalog_job["replacements"]),
        "character_6100_replacements": len(family_targets),
        "generation_id": catalog_pointer["generation_id"],
        "catalog_sha256": catalog_pointer["catalog_sha256"],
    }
    write_json_atomic(run_dir(job) / "catalog.json", result)
    print(json.dumps(result, separators=(",", ":")), flush=True)
    return result


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
    parser.add_argument(
        "command", choices=("audit", "prepare", "_prepare", "build", "catalog")
    )
    parser.add_argument("job", type=Path)
    args = parser.parse_args()
    job_path = args.job.resolve()
    if args.command == "audit":
        audit(job_path)
    elif args.command == "prepare":
        return prepare_via_configured_python(job_path)
    elif args.command == "_prepare":
        prepare_execute(job_path)
    elif args.command == "build":
        build_family(job_path)
    else:
        catalog_family(job_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
