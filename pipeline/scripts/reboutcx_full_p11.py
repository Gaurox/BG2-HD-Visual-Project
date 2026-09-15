"""Versioned P11 full component runner. No writes to P8/P9 or derived catalogs."""
from __future__ import annotations
import argparse
import copy
import hashlib
import json
import os
import sys
import time
from collections import defaultdict, deque
from pathlib import Path
from typing import Any
import numpy as np
from PIL import Image
import reboutcx_full as p8
from reboutcx_full import (JOB_SCHEMA, RUN_SCHEMA, PROJECT_ROOT, SCRIPT_DIR, read_json,
    resolve_path_reference, sha256_file, load_source_frames, semantic_classes_for_job,
    load_palette_profiles, qa_contract, ordered_cycles, is_null_frame, copy_component_for_resref,
    make_group_comparison, QUANTIZER_ID, relative)
from reboutcx_cpu_p10 import validate_component_registry
from reboutcx_runtime_p11 import (Runtime, GroupWindow, plan_groups, process_group,
    CANVAS_QUANTUM, GROUP_MAX_RESOURCES, GROUP_NATIVE_PIXEL_CAP)

RUN_ID = "reboutcx-p11-q32-group86-v1"
BATCH_CONTRACT = {
    "id": "p11-normalized-q32-group86-v1", "max_frames": 86, "canvas_quantum": CANVAS_QUANTUM,
    "input": "uint8-to-float32-div255-before-fp16",
    "padding": "zero-top-left-before-model; crop-to-source-after-model",
    "grouping": "canonical-resource-order; bounded-groups; geometry-buckets; no-duplicates",
    "group_max_resources": GROUP_MAX_RESOURCES, "group_native_pixel_cap": GROUP_NATIVE_PIXEL_CAP,
    "oversize_resource": "single-resource-group",
    "downscale": "chainner_ext-box-float32-v1",
    "deterministic_algorithms": True,
}


def validate_job(job: dict) -> None:
    if (job.get("schema") != JOB_SCHEMA or job.get("installable") is not False
            or job.get("scope") != "full-animation"
            or not str(job.get("job_id", "")).endswith(RUN_ID)
            or job.get("reboutcx_batch") != BATCH_CONTRACT
            or Path(str(job.get("paths", {}).get("run_dir", ""))).name != RUN_ID):
        raise RuntimeError("P11 requires its own versioned, non-installable job/run contract")


def derive_job(source_path: Path, destination: Path | None = None) -> Path:
    source = source_path.resolve()
    job = read_json(source)
    suffix = next((s for s in ("reboutcx-p9-batch86-v1", "reboutcx-p8-full-v1")
                   if str(job.get("job_id", "")).endswith(s)), None)
    if (suffix is None or job.get("schema") != JOB_SCHEMA or job.get("installable") is not False
            or Path(job["paths"]["run_dir"]).name != suffix):
        raise RuntimeError("derive-job requires a prepared P8/P9 component job")
    result = copy.deepcopy(job)
    result["job_id"] = job["job_id"][:-len(suffix)] + RUN_ID
    result["paths"]["run_dir"] = str(Path(job["paths"]["run_dir"]).with_name(RUN_ID)).replace("\\", "/")
    result["reboutcx_batch"] = copy.deepcopy(BATCH_CONTRACT)
    result["p11_source_job"] = {"path": relative(source), "sha256": sha256_file(source)}
    validate_job(result)
    output = destination.resolve() if destination else source.with_name(RUN_ID + ".json")
    if output.exists():
        if read_json(output) != result:
            raise RuntimeError("existing P11 job differs; select a new version")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, indent=2)
            stream.write("\n")
    return output


def render_contract_digest(job: dict, classes: dict, palette_evidence: dict | None) -> str:
    value = {"base": p8.render_contract_digest(job, classes, palette_evidence),
             "p11": job["reboutcx_batch"]}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest().upper()


def write_resource(*, resource: dict, component_path: Path, animation_id: int,
                   states: dict, qa_indices: set[int], reference_palette: np.ndarray | None):
    from reboutcx_cpu_p10 import write_frame_record
    frames = resource["frames"]
    cycles = p8.ordered_cycles(resource)
    resref = str(resource["source"]["name"]).upper()
    timing = defaultdict(float)
    write_started = time.perf_counter()
    component_path.parent.mkdir(parents=True, exist_ok=True)
    frame_manifest: list[dict[str, Any]] = []
    qa_records: dict[int, dict[str, Any]] = {}
    with component_path.open("wb") as stream:
        p8.write_component_header(
            stream,
            animation_id=animation_id,
            resref=resref,
            source_sha256=p8.sha256_file(resource["source_path"]),
            frame_count=len(frames),
            cycle_count=len(cycles),
        )
        for frame in frames:
            state = states[frame.index]
            quantized = state["quantized"]
            metrics = state["metrics"]
            write_frame_record(stream, frame, quantized, state.get("representatives"))
            frame_manifest.append(
                {
                    "source_frame": frame.index,
                    "width": frame.width,
                    "height": frame.height,
                    "center_x": frame.center_x,
                    "center_y": frame.center_y,
                    "transparent_index": frame.transparent,
                    "indices_sha256": p8.sha256_array(quantized),
                    "guide_sha256": p8.sha256_array(state["guide"]),
                    "visible_pixels": int(metrics["visible_pixels"]),
                    "oklab_error_mean": float(metrics["oklab_error_mean"]),
                    "oklab_error_p95": float(metrics["oklab_error_p95"]),
                    "oklab_error_max": float(metrics["oklab_error_max"]),
                    "model_bypassed": bool(metrics.get("model_bypassed", False)),
                }
            )
            if frame.index in qa_indices:
                palette = state["palette"]
                if reference_palette is None:
                    native_rgba = np.asarray(
                        Image.frombytes("RGBA", (frame.width, frame.height), frame.rgba).resize(
                            (frame.width * 2, frame.height * 2), Image.Resampling.NEAREST
                        ),
                        dtype=np.uint8,
                    )
                else:
                    native_rgba = p8.reconstruct_rgba(
                        np.repeat(np.repeat(frame.indices, 2, axis=0), 2, axis=1),
                        palette,
                        frame.transparent,
                    )
                target = state["target_rgb"]
                if target is None or state["xbr_rgba"] is None:
                    raise RuntimeError(f"{resref} frame {frame.index}: missing P11 comparison pixels")
                qa_records[frame.index] = {
                    "frame": frame,
                    "native_rgba": native_rgba,
                    "xbr_rgba": np.asarray(state["xbr_rgba"], dtype=np.uint8).copy(),
                    "raw_masked_rgba": np.dstack((target, np.where(state["guide"] == frame.transparent, 0, 255).astype(np.uint8))),
                    "quantized_rgba": p8.reconstruct_rgba(quantized, palette, frame.transparent),
                }
        p8.write_cycles(stream, cycles)
    timing["write_and_frame_metadata_seconds"] += time.perf_counter() - write_started
    return frame_manifest, qa_records, dict(timing)


def _execute_payload(job_path: Path, runtime: Runtime, windows: list) -> dict[str, Any]:
    started = time.perf_counter()
    job = read_json(job_path)
    validate_job(job)
    if (
        job.get("schema") != JOB_SCHEMA
        or job.get("installable") is not False
        or job.get("scope") != "full-animation"
    ):
        raise RuntimeError("invalid or installable ReboutCX full job")
    if int(job["reboutcx"]["target_scale"]) != 2:
        raise RuntimeError("ReboutCX target_scale must be 2")
    output = resolve_path_reference(job["paths"]["run_dir"], root=PROJECT_ROOT)
    if output.exists():
        raise RuntimeError(f"full run already exists: {output}")
    temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
    if temporary.exists():
        raise RuntimeError(f"full temporary path already exists: {temporary}")
    temporary.mkdir(parents=True)

    source_manifest_path = resolve_path_reference(
        job["paths"]["source_manifest"], required=True, root=PROJECT_ROOT
    )
    if sha256_file(source_manifest_path) != str(job["source_manifest_sha256"]):
        raise RuntimeError("source manifest hash differs")
    model_path = resolve_path_reference(
        job["paths"]["reboutcx_model"], required=True, root=PROJECT_ROOT
    )
    if sha256_file(model_path) != str(job["reboutcx"]["model_sha256"]):
        raise RuntimeError("ReboutCX model hash differs")
    scalepix = resolve_path_reference(
        job["paths"]["scalepix"], required=True, root=PROJECT_ROOT
    )
    source_started = time.perf_counter()
    frames, resources, source_manifest = load_source_frames(source_manifest_path)
    decode_seconds = time.perf_counter() - source_started
    animation_id = int(job["animation_id"], 16)
    if int(source_manifest["animation_id"], 16) != animation_id:
        raise RuntimeError("source animation id differs")
    if job.get("runtime_profile") is not None and source_manifest.get(
        "runtime_profile"
    ) != job.get("runtime_profile"):
        raise RuntimeError("source runtime profile differs")
    source_layer = source_manifest.get("layer", {}).get("kind")
    if job.get("layer") is not None and source_layer != job.get("layer"):
        raise RuntimeError("source layer differs")
    actual_inventory = [str(item["source"]["name"]).upper() for item in resources]
    requested_inventory = [str(item["name"]).upper() for item in job["source_inventory"]]
    if actual_inventory != requested_inventory:
        raise RuntimeError("source inventory differs from full job")

    classes, classes_id = semantic_classes_for_job(job)
    palette_profiles, palette_evidence = load_palette_profiles(job)
    reference_palette = palette_profiles[0]["palette"] if palette_profiles else None
    contract_digest = render_contract_digest(job, classes, palette_evidence)
    resource_by_resref = {
        str(resource["source"]["name"]).upper(): resource for resource in resources
    }
    canonical_by_key: dict[tuple[str, str, str], str] = {}
    canonical_by_resref: dict[str, str] = {}
    for resref in actual_inventory:
        resource = resource_by_resref[resref]
        key = (
            sha256_file(resource["bam_path"]),
            sha256_file(resource["source_path"]),
            contract_digest,
        )
        canonical = canonical_by_key.setdefault(key, resref)
        canonical_by_resref[resref] = canonical

    groups, required_qa = qa_contract(job, resources, canonical_by_resref)
    marker_index = int(job["null_frame_marker"])
    versions = runtime.model_info(
        model_path,
        device=str(job["reboutcx"]["device"]),
        fp16=bool(job["reboutcx"]["fp16"]),
    )

    qa_records_by_canonical: dict[str, dict[int, dict[str, Any]]] = {}
    manifests_by_resref: dict[str, list[dict[str, Any]]] = {}
    resource_reports: list[dict[str, Any]] = []
    component_by_resref: dict[str, Path] = {}
    timings = defaultdict(float)
    window = GroupWindow(runtime, scalepix=scalepix, node=str(job["tools"].get("node", "node")),
                            marker=marker_index, palette=reference_palette, classes=classes)
    windows.append(window)
    canonical_order = [name for name in actual_inventory if canonical_by_resref[name] == name]
    resource_groups = plan_groups([resource_by_resref[name] for name in canonical_order])
    group_by_name = {str(r["source"]["name"]).upper(): (i, group)
                     for i, group in enumerate(resource_groups) for r in group}
    components_dir = temporary / "components"
    components_dir.mkdir(parents=True)
    for resref in actual_inventory:
        resource = resource_by_resref[resref]
        canonical = canonical_by_resref[resref]
        component_path = components_dir / f"{resref}.registry"
        reused_from: str | None = None
        if canonical == resref:
            if resref not in manifests_by_resref:
                position, batch_group = group_by_name[resref]
                states, preparation_timing = window.get(batch_group)
                if position + 1 < len(resource_groups):
                    window.submit(resource_groups[position + 1], blocking=False)
                for key, value in preparation_timing.items():
                    timings[key] += value
                group_timing = process_group(runtime, batch_group, states,
                    fp16=bool(job["reboutcx"]["fp16"]), classes=classes, required_qa=required_qa)
                for key, value in group_timing.items():
                    timings[key] += value
                for member in batch_group:
                    name = str(member["source"]["name"]).upper()
                    member_path = components_dir / f"{name}.registry"
                    frame_manifest, qa_records, timing = write_resource(
                        resource=member, component_path=member_path, animation_id=animation_id,
                        states=states[name], reference_palette=reference_palette,
                        qa_indices=required_qa.get(name, set()))
                    manifests_by_resref[name] = frame_manifest
                    qa_records_by_canonical[name] = qa_records
                    component_by_resref[name] = member_path
                    for key, value in timing.items():
                        timings[key] += value
                window.release(batch_group)
                del states
        else:
            reused_from = canonical
            origin = component_by_resref[canonical]
            copy_component_for_resref(origin, component_path, resref)
            frame_manifest = copy.deepcopy(manifests_by_resref[canonical])
            manifests_by_resref[resref] = frame_manifest
        component_by_resref[resref] = component_path
        validate_started = time.perf_counter()
        registry_info = validate_component_registry(
            component_path,
            animation_id=animation_id,
            resource=resource,
            frame_manifest=manifests_by_resref[resref],
        )
        timings["internal_verification_seconds"] += time.perf_counter() - validate_started
        cycles = ordered_cycles(resource)
        registry_info.pop("resource_records", None)
        resource_reports.append(
            {
                "resref": resref,
                "source": relative(resource["source_path"]),
                "source_sha256": sha256_file(resource["source_path"]),
                "canonical_bam_sha256": sha256_file(resource["bam_path"]),
                "reused_render_from": reused_from,
                "frames": len(resource["frames"]),
                "null_frames": sum(is_null_frame(frame, marker_index) for frame in resource["frames"]),
                "cycles": len(cycles),
                "cycle_slots": sum(len(item["frame_indices"]) for item in cycles),
                "frame_records": manifests_by_resref[resref],
                "component": {
                    "path": relative(component_path),
                    "sha256": sha256_file(component_path),
                    "registry": registry_info,
                },
            }
        )


    qa_results: dict[tuple[str, int], dict[str, Any]] = {}
    for group in groups:
        resref = str(group["resref"]).upper()
        canonical = canonical_by_resref[resref]
        target_frames = {frame.index: frame for frame in resource_by_resref[resref]["frames"]}
        for index in [int(value) for value in group["frames"]]:
            record = copy.copy(qa_records_by_canonical[canonical][index])
            record["frame"] = target_frames[index]
            qa_results[(resref, index)] = record
    qa = [
        make_group_comparison(
            group,
            qa_results,
            temporary / "qa" / f"{group['name']}.gif",
        )
        for group in groups
    ]

    all_records = [record for report in resource_reports for record in report["frame_records"]]
    visible = sum(int(record["visible_pixels"]) for record in all_records)
    evaluated_records = [record for record in all_records if not record["model_bypassed"]]
    evaluated_visible = sum(int(record["visible_pixels"]) for record in evaluated_records)
    weighted_error = sum(
        float(record["oklab_error_mean"]) * int(record["visible_pixels"])
        for record in evaluated_records
    )
    manifest = {
        "schema": RUN_SCHEMA,
        "status": "completed-pending-human-review",
        "installable": False,
        "scope": "full-animation",
        "job": relative(job_path),
        "job_sha256": sha256_file(job_path),
        "source_manifest": relative(source_manifest_path),
        "source_manifest_sha256": sha256_file(source_manifest_path),
        "animation_id": job["animation_id"],
        "runtime_profile": job.get("runtime_profile"),
        "layer": job.get("layer"),
        "model_sha256": sha256_file(model_path),
        "target_scale": 2,
        "versions": versions,
        "semantic_classes_id": classes_id,
        "semantic_classes": classes,
        "palette_reference": palette_evidence,
        "render_contract_sha256": contract_digest,
        "code": {
            "reboutcx_full": {"path": relative(Path(__file__)), "sha256": sha256_file(Path(__file__))},
            "reboutcx_batch": {"path": relative(SCRIPT_DIR / "reboutcx_batch.py"), "sha256": sha256_file(SCRIPT_DIR / "reboutcx_batch.py")},
            "reboutcx_quantize": {"path": relative(SCRIPT_DIR / "reboutcx_quantize.py"), "sha256": sha256_file(SCRIPT_DIR / "reboutcx_quantize.py")},
            "creature_sprite_x2": {"path": relative(SCRIPT_DIR / "run_creature_sprite_x2.py"), "sha256": sha256_file(SCRIPT_DIR / "run_creature_sprite_x2.py")},
            "bam_export": {"path": relative(SCRIPT_DIR / "bam_export.py"), "sha256": sha256_file(SCRIPT_DIR / "bam_export.py")},
            "xbr_adapter": {"path": relative(SCRIPT_DIR / "xbr2x_batch.js"), "sha256": sha256_file(SCRIPT_DIR / "xbr2x_batch.js")},
            "scalepix": {"path": str(job["paths"]["scalepix"]), "sha256": sha256_file(scalepix)},
            "chainner_python": {"path": str(job["paths"]["chainner_python"]), "sha256": sha256_file(Path(sys.executable))},
        },
        "method": {
            "provider": "chaiNNer-integrated-python",
            "model_scale": 4,
            "device": job["reboutcx"]["device"],
            "fp16": job["reboutcx"]["fp16"],
            "tiling": "none",
            "padding": BATCH_CONTRACT["padding"],
            "batch": BATCH_CONTRACT,
            "resource_groups": [[str(r["source"]["name"]).upper() for r in group] for group in resource_groups],
            "pipeline": runtime.settings,
            "downscale": "chainner_ext ResizeFilter.Box float32 before u8 rounding",
            "rgb_under_transparency": "scipy distance_transform_edt nearest opaque",
            "alpha": "xbr2x-mask-v1",
            "quantizer": QUANTIZER_ID,
            "palette_rgb": (
                palette_evidence["id"] if palette_evidence is not None else "source-bam"
            ),
            "dither": False,
            "duplicate_source_policy": (
                "render once per BAM/BAMC/render-contract digest; clone component payload; "
                "verify each resref"
            ),
        },
        "coverage": {
            "resources": len(resources),
            "frames": len(frames),
            "null_frames": sum(is_null_frame(frame, marker_index) for frame in frames),
            "cycles": sum(len(resource["cycles"]) for resource in resources),
            "cycle_slots": sum(
                len(cycle["frame_indices"])
                for resource in resources
                for cycle in resource["cycles"]
            ),
            "unique_source_payloads": len(canonical_by_key),
            "unique_model_frames": int(timings["model_frames"]),
        },
        "timing_seconds": {**dict(timings), "source_decode_seconds": decode_seconds,
                           "execute_before_manifest_seconds": time.perf_counter() - started},
        "timing_semantics": "stage wall sums overlap; model_cuda_seconds uses CUDA events; process_cpu excludes queue/IPC; use controller through verification for throughput",
        "metrics": {
            "visible_pixels": visible,
            "model_evaluated_visible_pixels": evaluated_visible,
            "weighted_oklab_error_mean": (
                weighted_error / evaluated_visible if evaluated_visible else 0.0
            ),
            "worst_frame_p95": max(
                (float(record["oklab_error_p95"]) for record in evaluated_records),
                default=0.0,
            ),
            "worst_frame_max": max(
                (float(record["oklab_error_max"]) for record in evaluated_records),
                default=0.0,
            ),
        },
        "qa_contract": job["qa"],
        "qa": qa,
        "resources": resource_reports,
        "components": {
            "count": len(resource_reports),
            "total_bytes": sum(Path(report["component"]["path"]).stat().st_size if Path(report["component"]["path"]).is_absolute() else component_by_resref[report["resref"]].stat().st_size for report in resource_reports),
            "format": "IEECSXN V3 x2 raw; one non-installable component per resref",
        },
    }
    # Pin every imported historical helper as well as every P11 stage.
    for filename in ("reboutcx_full.py", "reboutcx_batch_p10.py", "reboutcx_cpu_p10.py",
                     "reboutcx_runtime_p10.py", "reboutcx_runtime_p11.py",
                     "reboutcx_playable_p11.py", "workspace_paths.py"):
        path = SCRIPT_DIR / filename
        manifest["code"][filename] = {"path": relative(path), "sha256": sha256_file(path)}
    for report in resource_reports:
        report["component"]["path"] = relative(output / "components" / (report["resref"] + ".registry"))
    for evidence in qa:
        evidence["path"] = relative(output / "qa" / Path(evidence["path"]).name)
    serialize_started = time.perf_counter()
    (temporary / "manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    serialize_seconds = time.perf_counter() - serialize_started
    temporary.rename(output)
    final_manifest = output / "manifest.json"
    runtime.execution_reports[str(job_path.resolve())] = {
        "execute_wall_seconds": time.perf_counter() - started,
        "serialize_write_seconds": serialize_seconds,
        "stage_seconds": manifest["timing_seconds"],
    }
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "execute_wall_seconds": time.perf_counter() - started,
                "serialize_write_seconds": serialize_seconds,
                "run": relative(output),
                "manifest_sha256": sha256_file(final_manifest),
                "resources": len(resources),
                "frames": len(frames),
                "components": len(resource_reports),
            },
            indent=2,
        )
    )
    return manifest


def verify(job_path: Path) -> dict[str, Any]:
    job = read_json(job_path)
    validate_job(job)
    output = resolve_path_reference(job["paths"]["run_dir"], required=True, root=PROJECT_ROOT)
    manifest_path = output / "manifest.json"
    manifest = read_json(manifest_path)
    if manifest.get("method", {}).get("batch") != BATCH_CONTRACT:
        raise RuntimeError("P11 manifest batch contract differs")
    if (
        manifest.get("schema") != RUN_SCHEMA
        or manifest.get("status") != "completed-pending-human-review"
        or manifest.get("installable") is not False
        or manifest.get("scope") != "full-animation"
        or int(manifest.get("target_scale", 0)) != 2
    ):
        raise RuntimeError("invalid ReboutCX full manifest")
    if manifest.get("job_sha256") != sha256_file(job_path):
        raise RuntimeError("full job hash differs")
    if manifest.get("source_manifest_sha256") != sha256_file(
        resolve_path_reference(job["paths"]["source_manifest"], required=True, root=PROJECT_ROOT)
    ):
        raise RuntimeError("source manifest hash differs")
    classes, classes_id = semantic_classes_for_job(job)
    _palette_profiles, palette_evidence = load_palette_profiles(job)
    if classes_id is not None:
        if (
            manifest.get("semantic_classes_id") != classes_id
            or manifest.get("semantic_classes") != classes
            or manifest.get("palette_reference") != palette_evidence
            or manifest.get("render_contract_sha256")
            != render_contract_digest(job, classes, palette_evidence)
        ):
            raise RuntimeError("Character render contract differs")
    for evidence in manifest["code"].values():
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != str(evidence["sha256"]):
            raise RuntimeError(f"full code/input hash differs: {evidence['path']}")
    _, resources, source_manifest = load_source_frames(
        resolve_path_reference(manifest["source_manifest"], required=True, root=PROJECT_ROOT)
    )
    report_by_resref = {report["resref"]: report for report in manifest["resources"]}
    expected_inventory = [str(resource["source"]["name"]).upper() for resource in resources]
    if ([report["resref"] for report in manifest["resources"]] != expected_inventory
            or expected_inventory != [str(item["name"]).upper() for item in job["source_inventory"]]):
        raise RuntimeError("P11 resource inventory differs")
    checked = 0
    for resource in resources:
        resref = str(resource["source"]["name"]).upper()
        report = report_by_resref[resref]
        path = resolve_path_reference(report["component"]["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != report["component"]["sha256"]:
            raise RuntimeError(f"{resref}: component hash differs")
        info = validate_component_registry(
            path,
            animation_id=int(source_manifest["animation_id"], 16),
            resource=resource,
            frame_manifest=report["frame_records"],
        )
        for key in ("version", "scale", "animation_id", "resource_count", "frame_count", "index_bytes", "registry_bytes", "sha256", "crc32"):
            if info[key] != report["component"]["registry"][key]:
                raise RuntimeError(f"{resref}: component inspection differs: {key}")
        checked += 1
    for evidence in manifest["qa"]:
        path = resolve_path_reference(evidence["path"], required=True, root=PROJECT_ROOT)
        if sha256_file(path) != evidence["sha256"]:
            raise RuntimeError(f"QA hash differs: {evidence['path']}")
        checked += 1
    result = {
        "status": "verified",
        "run": relative(output),
        "manifest_sha256": sha256_file(manifest_path),
        "resources": manifest["coverage"]["resources"],
        "frames": manifest["coverage"]["frames"],
        "checked_files": checked + 2,
    }
    print(json.dumps(result, indent=2))
    return result


def execute(job_path: Path, runtime: Runtime) -> dict:
    windows = []
    try:
        return _execute_payload(job_path, runtime, windows)
    finally:
        for window in windows:
            window.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    derive = sub.add_parser("derive-job")
    derive.add_argument("source", type=Path)
    derive.add_argument("--output", type=Path)
    for name in ("verify", "run"):
        cmd = sub.add_parser(name)
        cmd.add_argument("job", type=Path)
    args = parser.parse_args()
    if args.command == "derive-job":
        print(relative(derive_job(args.source, args.output)))
    elif args.command == "verify":
        verify(args.job)
    else:
        with Runtime(memory_mib=4096) as runtime:
            execute(args.job, runtime)
        verify(args.job)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
