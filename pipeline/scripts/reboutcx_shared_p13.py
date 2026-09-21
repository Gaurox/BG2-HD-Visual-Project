"""P13: one GPU session and one frame cache shared by many Character families.

Scheduling only. Rendering, verification and the pixel contract are the sealed P12 stages
(`execute`, `verify`, `Runtime`), so manifests stay valid P12 runs. Composants of all selected
families form one queue ordered by shared-BAM cohorts; the admission plan covers every repeated
pixel identity of the session, so each identical frame is computed once and reused by every family.

    prepare  : bootstrap missing P8 family jobs, prepare P12 jobs, write plan.json + queue.json
    plan     : read-only admission pass (order, weights, retention peak, prediction)
    run      : produce + verify every missing component; progress.json / milestones.log
    status   : print the latest progress record
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import multiprocessing
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait
from pathlib import Path

import numpy as np

from reboutcx_cache_p12 import FrameCache, context_key, frame_key
from reboutcx_full import (is_null_frame, load_palette_profiles, read_json, relative,
                           resolve_path_reference, semantic_classes_for_job, sha256_file)
from reboutcx_full_p12 import execute, validate_job, verify
from reboutcx_playable_p12 import QUEUE_SCHEMA
from reboutcx_runtime_p12 import Runtime
from run_creature_sprite_x2 import SourceFrame, decode_bam

ROOT = Path(__file__).resolve().parents[2]
WORK = ROOT / "sprite/.work/reboutcx-p13-production"
FAMILIES = ROOT / "sprite/families/playable-characters"
PROGRESS_SNAPSHOT = ROOT / "sprite/catalogs/creature-x2-reboutcx/jobs/playable-characters-reboutcx-progress-p12-v1.json"
Q32 = 32
# Calibration of docs/measurements/reboutcx-pending-frame-groups-20260915-v1/work-estimate.json
ACTIVE_S_PER_Q32_PIXEL = 7.541020724174957e-07
RESIDUAL_S_PER_SOURCE_FRAME = 0.00038653581525404556
BYTES_PER_NATIVE_PIXEL = 20      # guide + indices + RGB at x2
ENTRY_OVERHEAD_BYTES = 6144      # metrics, key, Future, dict slots (P12 charges 4096 + payload)
SHARED_CACHE_CAP_MIB = 28 * 1024
# The main process (decode, write, internal verification, hydration) is GIL-bound, so its cost tracks pixels.
FRAME_OVERHEAD_PIXELS = 300


BIG_CANVAS_PIXELS = 128 * 128   # a fixed batch of 86 at this canvas already needs several GiB; 224x224 needs > 17 GiB


class GpuBigCanvasLock:
    """Cross-process Windows mutex: only one shard runs a large-canvas batch at a time."""

    def __init__(self):
        import ctypes
        self._k32 = ctypes.windll.kernel32
        self._k32.CreateMutexW.restype = ctypes.c_void_p
        self._k32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_wchar_p]
        self._k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        self._k32.ReleaseMutex.argtypes = [ctypes.c_void_p]
        self.handle = self._k32.CreateMutexW(None, 0, "Local\bg2_p13_gpu_big_canvas")

    def __enter__(self):
        self._k32.WaitForSingleObject(self.handle, 0xFFFFFFFF)   # abandoned (0x80) also grants ownership
        return self

    def __exit__(self, *_):
        self._k32.ReleaseMutex(self.handle)


class LockedRuntime(Runtime):
    """P12 runtime; large canvases are serialized across shards and release their CUDA cache afterwards."""

    def _infer(self, rgbs, canvas, fp16, submitted):
        if canvas[0] * canvas[1] < BIG_CANVAS_PIXELS:
            return super()._infer(rgbs, canvas, fp16, submitted)
        if not hasattr(self, "_big_lock"):
            self._big_lock = GpuBigCanvasLock()
        with self._big_lock:
            try:
                return super()._infer(rgbs, canvas, fp16, submitted)
            finally:
                import torch
                torch.cuda.empty_cache()


class SharedFrameCache(FrameCache):
    """P12 cache whose admission table holds every repeated identity of the whole session."""

    def declare_counts(self, counts):
        with self.lock:
            if self.inflight or self.ready or self.stats:
                raise RuntimeError("cache plan must precede frame claims")
            self.remaining = {key: int(n) for key, n in counts.items() if n > 1}
            self.plan_used = 256 * len(self.remaining)
            self.used = self.plan_used
            self.peak = self.used
            self.stats["planned_repeated_keys"] = len(self.remaining)


# --------------------------------------------------------------------------- preparation

def pending_ids(previous: Path = PROGRESS_SNAPSHOT) -> list[str]:
    return list(read_json(previous)["pending_animation_ids"])


def family_directory(animation_id: str) -> Path:
    matches = sorted(FAMILIES.glob(animation_id[2:].lower() + "-*"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one family directory for {animation_id}: {matches}")
    return matches[0]


def prepare_all(output_dir: Path, ids: list[str], previous: Path = PROGRESS_SNAPSHOT) -> dict:
    from reboutcx_character_family import DEFAULT_TEMPLATE_JOB, bootstrap_family
    from reboutcx_prepare_sources_p12 import prepare, write_new

    started = time.perf_counter()
    families, members = [], []
    blocked = []
    for animation_id in ids:
        root = family_directory(animation_id)
        try:
            p8 = sorted(root.glob("family-runs/complete-reboutcx-p8-v1/jobs/*.json"))
            if not p8:
                xbr = sorted(root.glob("family-runs/complete-xn-xbr2x/jobs/*.json"))
                if len(xbr) != 1:
                    raise RuntimeError(f"expected one xBR aggregate, found {len(xbr)}")
                bootstrap_family(xbr[0], template_path=Path(DEFAULT_TEMPLATE_JOB), run=True)
                p8 = sorted(root.glob("family-runs/complete-reboutcx-p8-v1/jobs/*.json"))
            if len(p8) != 1:
                raise RuntimeError("expected one P8 family job")
            prepared_path = root / "family-runs/complete-reboutcx-p12-v1/prepared.json"
            if not prepared_path.is_file():
                try:
                    prepare(p8[0])
                except KeyError as error:
                    if error.args != ("layer",):
                        raise
                    prepare_with_derived_layer(p8[0])
            prepared = read_json(prepared_path)
            if prepared["animation_id"] != animation_id:
                raise RuntimeError("prepared.json belongs to another family")
        except Exception as error:  # a family that cannot be prepared is reported, never silently dropped
            blocked.append({"animation_id": animation_id, "family": relative(root), "error": repr(error)})
            continue
        families.append({"animation_id": animation_id, "family": relative(root), "queue": prepared["queue"],
                         "queue_sha256": prepared["queue_sha256"], "components": prepared["components"],
                         "source_frames": prepared["source_frames"]})
        members.extend({"job": m["job"], "sha256": m["sha256"]} for m in prepared["members"])
    queue = {"schema": QUEUE_SCHEMA, "installable": False, "members": members}
    write_new(output_dir / "queue.json", queue)
    plan = {"schema": "reboutcx-p13-shared-family-set-v1", "status": "prepared", "families": families, "blocked": blocked,
            "components": len(members), "source_frames": sum(f["source_frames"] for f in families),
            "queue": relative(output_dir / "queue.json"), "queue_sha256": sha256_file(output_dir / "queue.json"),
            "progress_before": relative(previous), "progress_before_sha256": sha256_file(previous),
            "prepare_seconds": time.perf_counter() - started}
    write_new(output_dir / "plan.json", plan)
    return {k: v for k, v in plan.items() if k != "families"} | {"families": len(families), "blocked": blocked}


def derived_layer_manifest(source_manifest: Path, layer: str) -> Path:
    """Sibling manifest for a sealed source lacking `layer`; the xBR pipeline defaults that field to body.

    BAMs, payloads and hashes stay in the sealed directory (paths point back to it); only `layer` is added.
    """
    import copy
    from reboutcx_prepare_sources_p12 import write_new
    if layer != "body":
        raise RuntimeError("derived layer manifests are only defined for the xBR default (body)")
    manifest = read_json(source_manifest)
    derived = copy.deepcopy(manifest)
    derived["layer"] = {"kind": "body"}
    prefix = "../" + source_manifest.parent.name + "/"
    for bam in derived["bams"]:
        bam["canonical_bam"] = prefix + bam["canonical_bam"]
        bam["source"] = prefix + bam["source"]
        for frame in bam.get("frames") or []:
            frame["file"] = prefix + frame["file"]
    derived["p13_derived_from"] = {"path": relative(source_manifest), "sha256": sha256_file(source_manifest),
                                   "added_fields": ["layer"], "layer_rule": "absent layer means body (run_creature_sprite_x2)"}
    target = source_manifest.parent.parent / "source-p13-layer" / "manifest.json"
    write_new(target, derived)
    return target


def prepare_with_derived_layer(family_job_path: Path) -> dict:
    """reboutcx_prepare_sources_p12.prepare, unchanged except that a source without `layer` is read through
    a derived manifest (see derived_layer_manifest). Jobs, queue and prepared.json keep the P12 shape."""
    import copy
    from reboutcx_catalog import animation_component_resrefs
    from reboutcx_character_family import load_template, member_layer, parent_context_for_family
    from reboutcx_full_p12 import BATCH_CONTRACT, RUN_ID
    from reboutcx_playable_p12 import load_queue
    from reboutcx_prepare_sources_p12 import write_new

    started = time.perf_counter()
    family = read_json(family_job_path)
    animation = family["animation_id"]
    source_path = resolve_path_reference(family["source_family_job"], required=True)
    if sha256_file(source_path) != family["source_family_job_sha256"]:
        raise RuntimeError("source family job changed")
    source = read_json(source_path)
    root = source_path.parents[3]
    if source["animation"]["id"] != animation or root.name.split('-')[0].lower() != animation[2:].lower():
        raise RuntimeError("source family identity differs")
    template_path, template = load_template(family)
    parent = parent_context_for_family(family)
    if sha256_file(resolve_path_reference(family["parent_catalog_pointer"])) != family["parent_catalog_pointer_sha256"]:
        raise RuntimeError("source parent pointer changed")
    if parent["pointer"]["generation_id"] != family["parent"]["generation_id"]:
        raise RuntimeError("source parent generation differs")
    by_resrefs = {frozenset(names): index for index, names in animation_component_resrefs(parent, animation).items()}
    if len(by_resrefs) != len(source["members"]):
        raise RuntimeError("ambiguous source component membership")
    records, seen, derived_count = [], set(), 0
    for reference in source["members"]:
        member_path = resolve_path_reference(reference, required=True)
        member = read_json(member_path)
        if member["animation"]["id"] != animation:
            raise RuntimeError("component has another animation")
        layer, armor, item = member_layer(member)
        prefix = str(member["animation"]["bam_prefix"]).upper()
        source_manifest = resolve_path_reference(member["paths"]["source_dir"], required=True) / "manifest.json"
        manifest = read_json(source_manifest)
        if "layer" not in manifest:
            source_manifest = derived_layer_manifest(source_manifest, layer)
            manifest = read_json(source_manifest)
            derived_count += 1
        if (manifest["animation_id"] != animation or manifest["runtime_profile"] != "character-bg2ee-2.7.3.0"
                or manifest["layer"]["kind"] != layer or manifest["bam_prefix"].upper() != prefix):
            raise RuntimeError("source manifest contract differs")
        inventory = [{"name": b["name"].upper()} for b in manifest["bams"]]
        index = by_resrefs.get(frozenset(b["name"] for b in inventory))
        if index is None or index in seen:
            raise RuntimeError("source RESREF set missing or duplicated in parent")
        seen.add(index)
        witness = None
        for bam in manifest["bams"]:
            bam_path = source_manifest.parent / bam["canonical_bam"]
            if sha256_file(bam_path) != bam["canonical_bam_sha256"]:
                raise RuntimeError("witness BAM changed")
            decoded, _palette, _tr = decode_bam(bam_path.read_bytes())
            for frame, (indices, _cx, _cy, tr) in enumerate(decoded):
                marker = indices.size == 1 and int(indices.flat[0]) == template["null_frame_marker"]
                if not marker and np.any(indices != tr):
                    witness = (bam["name"].upper(), frame)
                    break
            if witness is not None:
                break
        if witness is None:
            raise RuntimeError("component has no visible comparison frame")
        component_root = source_manifest.parent.parent
        job = {"schema": template["schema"], "job_id": f"character-{animation[2:].lower()}-{component_root.name}-{prefix.lower()}-{RUN_ID}",
               "installable": False, "scope": "full-animation", "animation_id": animation, "runtime_profile": "character-bg2ee-2.7.3.0",
               "layer": layer, "source_inventory": inventory, "source_manifest_sha256": sha256_file(source_manifest),
               "paths": {"source_manifest": relative(source_manifest), "run_dir": relative(component_root / "runs" / RUN_ID),
                         **{k: template["paths"][k] for k in ("chainner_python", "reboutcx_model", "scalepix")}},
               **{k: copy.deepcopy(template[k]) for k in ("tools", "reboutcx", "semantic_classes_id", "null_frame_marker", "palette_reference")},
               "reboutcx_batch": copy.deepcopy(BATCH_CONTRACT),
               "p12_source_job": {"path": relative(member_path), "sha256": sha256_file(member_path), "kind": "sealed-xbr-source-job"},
               "preparation": {"contract_template": relative(template_path), "contract_template_sha256": sha256_file(template_path),
                               "source_family_job": relative(source_path), "source_family_job_sha256": sha256_file(source_path),
                               "script": relative(Path(__file__)), "script_sha256": sha256_file(Path(__file__)),
                               "reference_inference": "not-required-by-P12; comparison frame selected from native source",
                               "derived_layer_manifest": source_manifest.parent.name == "source-p13-layer"},
               "qa": {"background": "dark-light-green-checkerboard-quadrants", "groups": [{"name": prefix.lower() + "-reference",
                      "resref": witness[0], "frames": [witness[1]], "duration_ms": 400}]}}
        job["armor_code" if layer == "body" else "item_resref"] = armor if layer == "body" else item
        validate_job(job)
        path = component_root / "jobs" / (RUN_ID + ".json")
        if resolve_path_reference(job["paths"]["run_dir"]).exists():
            raise RuntimeError("new-family preparation requires new P12 output directories")
        write_new(path, job)
        records.append({"bam_prefix": prefix, "component_index": index, "job": relative(path), "sha256": sha256_file(path),
                        "source_frames": int(manifest["total_frames"]), "source_manifest": relative(source_manifest),
                        "source_manifest_sha256": sha256_file(source_manifest)})
    destination = root / "family-runs/complete-reboutcx-p12-v1"
    queue = destination / "jobs" / (root.name + "-p12-v1.json")
    write_new(queue, {"schema": QUEUE_SCHEMA, "installable": False, "members": [{"job": r["job"], "sha256": r["sha256"]} for r in records]})
    assert len(load_queue(queue)) == len(records)
    prepared = {"schema": "bg2-upscale-reboutcx-p12-source-preparation-v1", "animation_id": animation, "family": relative(root),
                "queue": relative(queue), "queue_sha256": sha256_file(queue), "parent_generation": parent["pointer"]["generation_id"],
                "source_family_job": relative(source_path), "source_family_job_sha256": sha256_file(source_path),
                "components": len(records), "source_frames": sum(r["source_frames"] for r in records),
                "derived_layer_manifests": derived_count, "members": records}
    write_new(destination / "prepared.json", prepared)
    return {k: v for k, v in prepared.items() if k != "members"} | {"prepare_seconds": time.perf_counter() - started}


def load_jobs(path: Path) -> list[Path]:
    queue = read_json(path)
    if queue.get("schema") != QUEUE_SCHEMA or queue.get("installable") is not False:
        raise RuntimeError("invalid queue")
    jobs, outputs, contract = [], set(), None
    for member in queue["members"]:
        job_path = resolve_path_reference(member["job"], required=True).resolve()
        if sha256_file(job_path) != member["sha256"]:
            raise RuntimeError(f"queue job hash differs: {member['job']}")
        job = read_json(job_path)
        validate_job(job)
        if job.get("runtime_profile") != "character-bg2ee-2.7.3.0":
            raise RuntimeError("queue is restricted to Character jobs")
        model = (str(resolve_path_reference(job["paths"]["reboutcx_model"]).resolve()),
                 job["reboutcx"]["model_sha256"], job["reboutcx"]["device"], job["reboutcx"]["fp16"])
        if contract is not None and contract != model:
            raise RuntimeError("queue contains multiple model/device/precision contracts")
        contract = model
        output = resolve_path_reference(job["paths"]["run_dir"]).resolve()
        if output in outputs:
            raise RuntimeError("queue contains duplicate output directories")
        outputs.add(output)
        jobs.append(job_path)
    return jobs


# --------------------------------------------------------------------------- admission plan

_tool_hashes: dict = {}


def plan_job(job_path: str) -> dict:
    """Same pass as reboutcx_plan_p12.plan_cache for one job, plus size information."""
    job_path = Path(job_path)
    job = read_json(job_path)
    source = resolve_path_reference(job["paths"]["source_manifest"], required=True)
    if sha256_file(source) != job["source_manifest_sha256"]:
        raise RuntimeError("source manifest changed before P13 planning")
    source_manifest = read_json(source)
    if [b["name"].upper() for b in source_manifest["bams"]] != [b["name"].upper() for b in job["source_inventory"]]:
        raise RuntimeError("P13 plan source inventory differs")
    classes, _ = semantic_classes_for_job(job)
    profiles, _ = load_palette_profiles(job)
    palette = profiles[0]["palette"] if profiles else None
    scalepix = resolve_path_reference(job["paths"]["scalepix"], required=True)
    if scalepix not in _tool_hashes:
        _tool_hashes[scalepix] = sha256_file(scalepix)
    context = context_key(job, classes, _tool_hashes[scalepix])
    counts, native, quantized = Counter(), {}, {}
    seen = set()
    for bam in source_manifest["bams"]:
        raw = (source.parent / bam["canonical_bam"]).read_bytes()
        identity = (hashlib.sha256(raw).hexdigest().upper(), sha256_file(source.parent / bam["source"]))
        if identity in seen:
            continue
        seen.add(identity)
        decoded, native_palette, _tr = decode_bam(raw)
        for index, (indices, cx, cy, tr) in enumerate(decoded):
            h, w = indices.shape
            if not (1 <= w <= 4096 and 1 <= h <= 4096):
                raise RuntimeError("invalid frame dimensions in P13 plan")
            rgba = np.empty((h, w, 4), dtype=np.uint8)
            rgba[:, :, :3] = native_palette[indices]
            rgba[:, :, 3] = np.where(indices == tr, 0, 255).astype(np.uint8)
            frame = SourceFrame(bam["name"], index, w, h, cx, cy, tr, indices, native_palette, rgba.tobytes())
            if not is_null_frame(frame, int(job["null_frame_marker"])):
                key = frame_key(frame, palette, context)
                counts[key] += 1
                native[key] = w * h
                quantized[key] = ((h + Q32 - 1) // Q32 * Q32) * ((w + Q32 - 1) // Q32 * Q32)
    cost = sum(native[key] * n for key, n in counts.items()) + FRAME_OVERHEAD_PIXELS * sum(counts.values())
    return {"job": str(job_path), "signature": tuple(sorted(b["name"].upper() for b in job["source_inventory"])),
            "frames": int(source_manifest["total_frames"]), "cost": int(cost), "counts": counts, "native": native,
            "q32": quantized}


class Plan:
    """Session-wide admission table, cohort order, per-job work weights and retention estimate."""

    def __init__(self, jobs: list[Path], workers: int):
        started = time.perf_counter()
        state = {j: (resolve_path_reference(read_json(j)["paths"]["run_dir"]) / "manifest.json").is_file() for j in jobs}
        todo = [j for j in jobs if not state[j]]
        self.existing = [j for j in jobs if state[j]]
        context = multiprocessing.get_context("spawn")
        ids, native, q32, per_job = {}, [], [], []
        with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
            for result in pool.map(plan_job, [str(j) for j in todo], chunksize=4):
                keys, cnt = [], []
                for key, n in result["counts"].items():
                    ident = ids.get(key)
                    if ident is None:
                        ident = ids[key] = len(ids)
                        native.append(result["native"][key])
                        q32.append(result["q32"][key])
                    keys.append(ident)
                    cnt.append(n)
                per_job.append({"job": Path(result["job"]), "signature": result["signature"], "frames": result["frames"],
                                "cost": result["cost"],
                                "ids": np.asarray(keys, dtype=np.int64), "n": np.asarray(cnt, dtype=np.int64)})
                del result
        self.key_bytes = {ident: key for key, ident in ids.items()}
        self.unique_keys = len(ids)
        native = np.asarray(native, dtype=np.int64)
        q32 = np.asarray(q32, dtype=np.int64)
        # Cohorts: components with the same BAM resource set, heaviest (most distinct pixels) first.
        cohorts = defaultdict(list)
        for entry in per_job:
            cohorts[entry["signature"]].append(entry)
        weight_of_cohort = {}
        for signature, entries in cohorts.items():
            union = np.unique(np.concatenate([e["ids"] for e in entries]))
            weight_of_cohort[signature] = int(q32[union].sum())
        ordered = []
        for signature in sorted(cohorts, key=lambda s: (-weight_of_cohort[s], s)):
            ordered.extend(sorted(cohorts[signature], key=lambda e: str(e["job"])))
        self.order = [e["job"] for e in ordered]
        self.cohort_info = {sig: {"jobs": [e["job"] for e in entries], "ids": np.unique(np.concatenate([e["ids"] for e in entries])),
                                  "cost": sum(e["cost"] for e in entries), "frames": sum(e["frames"] for e in entries)}
                            for sig, entries in cohorts.items()}
        # First-owner attribution in the planned order, then retention sweep.
        first = np.full(self.unique_keys, -1, dtype=np.int64)
        last = np.full(self.unique_keys, -1, dtype=np.int64)
        total = np.zeros(self.unique_keys, dtype=np.int64)
        self.weights, self.new_q32, self.new_model = {}, {}, {}
        self.model_seconds = 0.0
        for position, entry in enumerate(ordered):
            fresh = first[entry["ids"]] < 0
            first[entry["ids"][fresh]] = position
            last[entry["ids"]] = position
            total[entry["ids"]] += entry["n"]
            new_pixels = int(q32[entry["ids"][fresh]].sum())
            self.new_q32[entry["job"]] = new_pixels
            self.new_model[entry["job"]] = int(fresh.sum())
            self.weights[entry["job"]] = float(entry["cost"])
            self.model_seconds += ACTIVE_S_PER_Q32_PIXEL * new_pixels + RESIDUAL_S_PER_SOURCE_FRAME * entry["frames"]
        shared = total > 1
        size = native * BYTES_PER_NATIVE_PIXEL + ENTRY_OVERHEAD_BYTES
        delta = np.zeros(len(ordered) + 2, dtype=np.int64)
        np.add.at(delta, first[shared], size[shared])
        np.add.at(delta, last[shared] + 1, -size[shared])
        self.retention_peak_bytes = int(np.cumsum(delta).max())
        self.counts = Counter({self.key_bytes[i]: int(total[i]) for i in np.nonzero(shared)[0]})
        self.repeated_keys = int(shared.sum())
        self.total_claims = int(total.sum())
        self.source_frames = sum(e["frames"] for e in ordered)
        self.total_weight = sum(self.weights.values())
        self.predicted_seconds = self.model_seconds
        self.cohorts = len(cohorts)
        self.seconds = time.perf_counter() - started
        del per_job, first, last

    def partition(self, shards: int) -> list[list[Path]]:
        """Whole cohorts per shard: identical BAMs stay together, so their frames are still computed once."""
        signatures = sorted(self.cohort_info, key=lambda s: (-self.cohort_info[s]["cost"], s))
        target = sum(self.cohort_info[s]["cost"] for s in signatures) / shards
        masks = [np.zeros(self.unique_keys, dtype=bool) for _ in range(shards)]
        loads, groups = [0.0] * shards, [[] for _ in range(shards)]
        for signature in signatures:
            info = self.cohort_info[signature]
            open_shards = [i for i in range(shards) if loads[i] + info["cost"] <= 1.10 * target]
            if open_shards:
                choice = max(open_shards, key=lambda i: (int(masks[i][info["ids"]].sum()), -loads[i]))
            else:
                choice = min(range(shards), key=lambda i: loads[i])
            masks[choice][info["ids"]] = True
            loads[choice] += info["cost"]
            groups[choice].extend(info["jobs"])
        self.shard_unique_keys = [int(mask.sum()) for mask in masks]
        self.shard_loads = loads
        return groups

    def summary(self) -> dict:
        return {"jobs_to_render": len(self.order), "existing_jobs": len(self.existing), "cohorts": self.cohorts,
                "unique_pixel_identities": self.unique_keys, "repeated_identities": self.repeated_keys,
                "logical_claims": self.total_claims, "duplicate_claims_avoided": self.total_claims - self.unique_keys,
                "source_frames": self.source_frames,
                "retention_peak_gib": self.retention_peak_bytes / 2**30,
                "predicted_seconds": self.predicted_seconds, "plan_seconds": self.seconds}


def cache_limit_mib(plan: Plan, requested: int | None) -> int:
    if requested is not None:
        return requested
    wanted = int(plan.retention_peak_bytes * 1.35 / 2**20) + 2048
    return max(2048, min(SHARED_CACHE_CAP_MIB, wanted))


# --------------------------------------------------------------------------- execution

def execute_with_rename_retry(job_path: Path, runtime: Runtime) -> dict:
    """P12 execute; a transient Windows lock on the final directory rename is retried, never skipped."""
    try:
        return execute(job_path, runtime)
    except PermissionError:
        job = read_json(job_path)
        output = resolve_path_reference(job["paths"]["run_dir"])
        temporary = output.with_name(f".{output.name}.tmp-{os.getpid()}")
        if output.exists() or not (temporary / "manifest.json").is_file():
            raise
        for delay in (1, 2, 4, 8, 15, 30):
            time.sleep(delay)
            try:
                temporary.rename(output)
                return read_json(output / "manifest.json")
            except PermissionError:
                continue
        raise


def rss_gib() -> float | None:
    try:
        import psutil
        process = psutil.Process()
        total = process.memory_info().rss + sum(c.memory_info().rss for c in process.children(recursive=True))
        return total / 2**30
    except Exception:
        return None


def replace_best_effort(source: Path, destination: Path) -> None:
    """Progress files are advisory; a reader holding the destination open must never stop a run."""
    for _ in range(20):
        try:
            os.replace(source, destination)
            return
        except PermissionError:
            time.sleep(0.05)


def fmt(seconds: float | None) -> str:
    if seconds is None:
        return "?"
    seconds = int(seconds)
    return f"{seconds // 3600}h{seconds % 3600 // 60:02d}" if seconds >= 3600 else f"{seconds // 60}min{seconds % 60:02d}"


def run_shared(queue_path: Path, *, components: int, pre_workers: int, post_workers: int, memory_mib: int,
               cache_mib: int | None, plan_workers: int, verify_workers: int, milestone_step: float,
               tag: str = "", gpu_fraction: float | None = None) -> dict:
    work = WORK / tag if tag else WORK
    work.mkdir(parents=True, exist_ok=True)
    if gpu_fraction:
        import torch
        torch.cuda.set_per_process_memory_fraction(gpu_fraction, 0)
    jobs = load_jobs(queue_path)
    plan = Plan(jobs, plan_workers)
    limit_mib = cache_limit_mib(plan, cache_mib)
    session = time.time_ns()
    log_path = work / f"session-{session}.jsonl"
    progress_path = work / "progress.json"
    milestones = work / "milestones.log"
    started = time.perf_counter()
    context = multiprocessing.get_context("spawn")
    new_model = logical = source_frames = gpu_slots = filler = 0
    done_weight, verified_new, verified_existing = 0.0, 0, 0
    next_milestone = milestone_step
    first_render = None
    order = [*plan.existing, *plan.order]
    with log_path.open("x", encoding="utf-8") as log, LockedRuntime(
            pre_workers=pre_workers, post_workers=post_workers, memory_mib=memory_mib, cache_mib=limit_mib) as runtime, \
            ThreadPoolExecutor(max_workers=components) as renders, \
            ProcessPoolExecutor(max_workers=verify_workers, mp_context=context) as verifier:
        runtime.cache = SharedFrameCache(limit_mib * 1024 * 1024)
        runtime.settings.update(shared_cache_mib=limit_mib, components=components, scheduler="p13-shared-cohorts")

        def emit(event: str, **fields):
            record = {"event": event, "elapsed_seconds": time.perf_counter() - started, **fields}
            line = json.dumps(record)
            log.write(line + "\n")
            log.flush()
            print(line, flush=True)

        def snapshot() -> dict:
            elapsed = time.perf_counter() - started
            render_elapsed = time.perf_counter() - first_render if first_render else 0.0
            fraction = done_weight / plan.total_weight if plan.total_weight else 1.0
            eta = None
            if fraction >= 0.02 and render_elapsed:
                eta = (plan.total_weight - done_weight) * render_elapsed / done_weight
            return {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "elapsed_seconds": elapsed,
                    "render_elapsed_seconds": render_elapsed, "work_percent": 100 * fraction,
                    "jobs_rendered": verified_new, "jobs_existing_verified": verified_existing,
                    "jobs_total_in_session": len(order), "model_frames_computed": new_model,
                    "model_frames_planned": plan.unique_keys, "logical_model_frames": logical,
                    "source_frames_done": source_frames, "eta_seconds": eta,
                    "done_weight": done_weight, "total_weight": plan.total_weight,
                    "source_frames_total": plan.source_frames,
                    "predicted_total_seconds": plan.predicted_seconds, "cache": runtime.cache.snapshot(),
                    "rss_gib": rss_gib()}

        def publish_progress():
            nonlocal next_milestone
            record = snapshot()
            tmp = progress_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(record, indent=1), encoding="utf-8")
            replace_best_effort(tmp, progress_path)
            if record["work_percent"] >= next_milestone or verified_new + verified_existing == len(order):
                while next_milestone <= record["work_percent"]:
                    next_milestone += milestone_step
                cache = record["cache"]
                line = (f"[{fmt(record['elapsed_seconds'])}] {record['work_percent']:.1f}% du travail | "
                        f"{verified_new}/{len(plan.order)} composants | inférences {record['model_frames_computed']:,}/"
                        f"{record['model_frames_planned']:,} | reste ≈ {fmt(record['eta_seconds'])} | "
                        f"cache {cache['retained_bytes'] / 2**30:.1f} Gio (pic {cache['peak_retained_bytes'] / 2**30:.1f}), "
                        f"évictions {cache.get('evictions', 0)} | RAM {record['rss_gib'] or 0:.1f} Gio")
                with milestones.open("a", encoding="utf-8") as stream:
                    stream.write(line + "\n")

        emit("start", queue=relative(queue_path), queue_sha256=sha256_file(queue_path), plan=plan.summary(),
             cache_mib=limit_mib, components=components, pre_workers=pre_workers, post_workers=post_workers,
             memory_mib=memory_mib)
        publish_progress()
        active, checks, index = {}, {}, 0
        try:
            admission = plan.counts
            runtime.cache.declare_counts(admission)
            emit("cache-plan", repeated_keys=len(admission), plan_seconds=plan.seconds)
            del admission
            while index < len(order) or active or checks:
                while index < len(order) and len(active) < components and len(checks) < 2 * verify_workers:
                    job_path = order[index]
                    index += 1
                    output = resolve_path_reference(read_json(job_path)["paths"]["run_dir"])
                    if (output / "manifest.json").is_file():
                        checks[verifier.submit(verify, job_path)] = (job_path, time.perf_counter(), True)
                    else:
                        if first_render is None:
                            first_render = time.perf_counter()
                        active[renders.submit(execute_with_rename_retry, job_path, runtime)] = job_path
                        emit("render-start", job=relative(job_path))
                done, _ = wait([*active, *checks], return_when=FIRST_COMPLETED)
                for future in done:
                    if future in active:
                        job_path = active.pop(future)
                        manifest = future.result()
                        coverage = manifest["coverage"]
                        new_model += coverage["unique_model_frames"]
                        logical += coverage["logical_model_frames"]
                        source_frames += coverage["frames"]
                        gpu_slots += coverage["gpu_slots"]
                        filler += coverage["gpu_filler_frames"]
                        checks[verifier.submit(verify, job_path)] = (job_path, time.perf_counter(), False)
                        report = runtime.execution_reports.pop(str(job_path.resolve()), {})
                        emit("render-finished", job=relative(job_path), **report)
                    else:
                        job_path, tick, existing = checks.pop(future)
                        result = future.result()
                        if existing:
                            verified_existing += 1
                        else:
                            verified_new += 1
                            done_weight += plan.weights[job_path]
                        emit("verified", job=relative(job_path), existing=existing,
                             verification_queue_and_wall_seconds=time.perf_counter() - tick,
                             manifest_sha256=result["manifest_sha256"])
                        publish_progress()
        except BaseException as error:
            import traceback
            for future in [*active, *checks]:
                future.cancel()
            # The exception surfaced first can be a follower's; record every finished job's own error.
            causes = []
            wait(list(active), timeout=20)
            for future, job_path in active.items():
                if future.done() and not future.cancelled() and future.exception() is not None:
                    causes.append({"job": relative(job_path), "error": repr(future.exception()),
                                   "traceback": "".join(traceback.format_exception(future.exception()))[-3000:]})
            emit("failed", error=repr(error), verified=verified_new + verified_existing, causes=causes)
            raise
        elapsed = time.perf_counter() - started
        report = {"completed": verified_new + verified_existing, "rendered": verified_new,
                  "existing_verified": verified_existing, "new_model_frames": new_model,
                  "logical_model_frames": logical, "source_frames": source_frames, "gpu_slots": gpu_slots,
                  "gpu_filler_frames": filler, "wall_through_verification_seconds": elapsed,
                  "cache": runtime.cache.snapshot(), "plan": plan.summary(), "cache_mib": limit_mib,
                  "model_load_seconds_once": runtime.model_load_seconds,
                  "peak_reserved_resource_bytes": runtime.memory.peak, "log": relative(log_path)}
        emit("complete", **report)
        publish_progress()
        return report


def final_check(job_path: str) -> dict:
    """Independent P12 verification of one sealed run plus its coverage numbers."""
    import contextlib
    import io
    job_path = Path(job_path)
    with contextlib.redirect_stdout(io.StringIO()):
        result = verify(job_path)
    job = read_json(job_path)
    output = resolve_path_reference(job["paths"]["run_dir"])
    manifest = read_json(output / "manifest.json")
    coverage = manifest["coverage"]
    return {"job": relative(job_path), "animation_id": job["animation_id"], "manifest": relative(output / "manifest.json"),
            "manifest_sha256": result["manifest_sha256"], "frames": coverage["frames"],
            "logical_model_frames": coverage["logical_model_frames"], "computed_model_frames": coverage["unique_model_frames"],
            "cache_hit_frames": coverage["model_cache_hit_frames"], "gpu_slots": coverage["gpu_slots"],
            "gpu_filler_frames": coverage["gpu_filler_frames"]}


def finish(queue_path: Path, report_path: Path, workers: int) -> dict:
    """Verify every queued run again, prove no temporary output remains, write an immutable report."""
    from reboutcx_prepare_sources_p12 import write_new
    started = time.perf_counter()
    jobs = load_jobs(queue_path)
    missing = [relative(j) for j in jobs
               if not (resolve_path_reference(read_json(j)["paths"]["run_dir"]) / "manifest.json").is_file()]
    if missing:
        raise RuntimeError(f"{len(missing)} queued runs have no manifest, first: {missing[0]}")
    context = multiprocessing.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        records = list(pool.map(final_check, [str(j) for j in jobs], chunksize=8))
    leftovers = sorted(relative(p) for p in FAMILIES.glob("*/*/runs/.reboutcx-p12-cache86-v1.tmp-*"))
    per_family = defaultdict(lambda: Counter())
    for record in records:
        per_family[record["animation_id"]].update(components=1, frames=record["frames"],
                                                  logical=record["logical_model_frames"], computed=record["computed_model_frames"])
    totals = Counter()
    for record in records:
        totals.update(frames=record["frames"], logical=record["logical_model_frames"],
                      computed=record["computed_model_frames"], hits=record["cache_hit_frames"])
    sessions = []
    for path in sorted(WORK.rglob("session-*.jsonl")):
        events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        terminal = events[-1]
        sessions.append({"session": relative(path), "sha256": sha256_file(path), "terminal_event": terminal["event"],
                         "verified": sum(e["event"] == "verified" for e in events),
                         "error": terminal.get("error") if terminal["event"] == "failed" else None})
    report = {"schema": "reboutcx-p13-shared-production-report-v1", "status": "all-queued-runs-verified" if not leftovers else "leftover-temporary-outputs",
              "queue": relative(queue_path), "queue_sha256": sha256_file(queue_path), "components": len(records),
              "families": {k: dict(v) for k, v in sorted(per_family.items())}, "totals": dict(totals),
              "reuse_fraction": 1 - totals["computed"] / totals["logical"] if totals["logical"] else 0.0,
              "records": records, "leftover_temporary_outputs": leftovers, "sessions": sessions,
              "final_verification_seconds": time.perf_counter() - started}
    write_new(report_path, report)
    return {k: v for k, v in report.items() if k not in ("records", "families", "sessions")}


def write_snapshot(plan_path: Path, report_path: Path, snapshot_id: str) -> dict:
    """New immutable progress snapshot: previous completed families + every family of the verified P13 set."""
    import copy
    from reboutcx_full_p12 import RUN_ID
    from reboutcx_prepare_sources_p12 import write_new
    plan, report = read_json(plan_path), read_json(report_path)
    if report["status"] != "all-queued-runs-verified" or report["queue_sha256"] != plan["queue_sha256"]:
        raise RuntimeError("production report does not verify this plan")
    previous_path = resolve_path_reference(plan["progress_before"], required=True)
    previous = read_json(previous_path)
    if sha256_file(previous_path) != plan["progress_before_sha256"]:
        raise RuntimeError("previous snapshot changed since preparation")
    by_job = {r["job"]: r for r in report["records"]}
    completed = copy.deepcopy(previous["completed"])
    done = set()
    for family in plan["families"]:
        root = resolve_path_reference(family["family"])
        prepared = read_json(root / "family-runs/complete-reboutcx-p12-v1/prepared.json")
        components = []
        for member in prepared["members"]:
            record = by_job[member["job"]]
            manifest_path = resolve_path_reference(record["manifest"])
            if sha256_file(manifest_path) != record["manifest_sha256"] or record["animation_id"] != family["animation_id"]:
                raise RuntimeError(f"manifest differs from the verification report: {member['job']}")
            components.append({"component_index": member["component_index"], "manifest": record["manifest"],
                               "manifest_sha256": record["manifest_sha256"]})
        if len({c["component_index"] for c in components}) != len(components) or len(components) != family["components"]:
            raise RuntimeError(f"{family['animation_id']}: component set incomplete")
        completed.append({"animation_id": family["animation_id"], "family": family["family"], "method": RUN_ID,
                          "components": components, "verification_report": relative(report_path),
                          "verification_report_sha256": sha256_file(report_path)})
        done.add(family["animation_id"])
    snapshot = copy.deepcopy(previous)
    snapshot["snapshot_id"] = snapshot_id
    snapshot["completed"] = sorted(completed, key=lambda f: int(f["animation_id"], 16))
    snapshot["pending_animation_ids"] = [a for a in previous["pending_animation_ids"] if a not in done]
    snapshot["totals"].update(completed_families=len(completed), pending_families=len(snapshot["pending_animation_ids"]),
                              reboutcx_components=sum(len(f["components"]) for f in completed))
    if len(completed) + len(snapshot["pending_animation_ids"]) != snapshot["totals"]["playable_families"]:
        raise RuntimeError("family totals do not add up")
    snapshot["previous_snapshot"] = {"path": relative(previous_path), "sha256": sha256_file(previous_path)}
    snapshot["production_batch"] = {"path": relative(report_path), "sha256": sha256_file(report_path)}
    destination = previous_path.with_name(f"playable-characters-reboutcx-progress-{snapshot_id}.json")
    write_new(destination, snapshot)
    return {"snapshot": relative(destination), "totals": snapshot["totals"], "pending": snapshot["pending_animation_ids"]}


def write_catalog_job(snapshot_path: Path, seed_path: Path, job_id: str) -> dict:
    """Cumulative derived-catalog job: every seed replacement kept, every produced playable component added.

    Selection is by (animation_id, component_index) with the parent's exact RESREF set, so a shared xBR
    RESREF stays xBR for every animation that is not replaced.
    """
    from reboutcx_catalog import animation_component_resrefs, parent_context
    from reboutcx_character_family import CATALOG_JOB_SCHEMA, CATALOG_OWNER_CHARACTER, catalog_replacement

    snapshot = read_json(snapshot_path)
    seed = read_json(seed_path)
    if seed.get("schema") != CATALOG_JOB_SCHEMA or seed.get("installable") is not False:
        raise RuntimeError("invalid derived catalog seed job")
    if snapshot["totals"]["pending_families"] != 0:
        raise RuntimeError("snapshot still has pending families")
    parent = parent_context(seed)
    animations = {a["animation_id"]: a for a in parent["index"]["animations"]}
    components = {int(c["index"]): c for c in parent["index"]["components"]}
    replacements = {(r["animation_id"], int(r["expected_component_indices"][0])): r for r in seed["replacements"]}
    kept = len(replacements)
    added = Counter()
    for family in snapshot["completed"]:
        animation_id = family["animation_id"]
        record = animations[animation_id]
        if int(record.get("owner", -1)) != CATALOG_OWNER_CHARACTER:
            raise RuntimeError(f"{animation_id}: parent owner is not Character")
        by_index = animation_component_resrefs(parent, animation_id)
        for member in family["components"]:
            index = int(member["component_index"])
            key = (animation_id, index)
            if key in replacements:
                continue
            manifest_path = resolve_path_reference(member["manifest"], required=True)
            if sha256_file(manifest_path) != member["manifest_sha256"]:
                raise RuntimeError(f"{animation_id}/{index}: manifest hash differs")
            manifest = read_json(manifest_path)
            if (manifest.get("status") != "completed-pending-human-review" or manifest.get("animation_id") != animation_id
                    or {r["resref"].upper() for r in manifest["resources"]} != by_index[index]):
                raise RuntimeError(f"{animation_id}/{index}: manifest does not match the parent component")
            component = components[index]
            start = int(component["shard_start"])
            replacements[key] = catalog_replacement(
                animation=record, component=component, logical_digest=parent["logical_digests"][index],
                shards=parent["index"]["shards"][start:start + int(component["shard_count"])],
                manifest_path=manifest_path, manifest=manifest)
            added[animation_id] += 1
    job = {"schema": CATALOG_JOB_SCHEMA, "job_id": job_id, "installable": False, "target_scale": 2,
           "paths": {"parent_pointer": seed["paths"]["parent_pointer"],
                     "run_dir": relative(ROOT / "sprite/catalogs/creature-x2-reboutcx/runs" / job_id)},
           "parent": seed["parent"],
           "replacements": [replacements[k] for k in sorted(replacements, key=lambda v: (int(v[0], 16), v[1]))]}
    destination = ROOT / "sprite/catalogs/creature-x2-reboutcx/jobs" / f"{job_id}.json"
    from reboutcx_prepare_sources_p12 import write_new
    write_new(destination, job)
    return {"job": relative(destination), "job_sha256": sha256_file(destination), "replacements": len(job["replacements"]),
            "kept_from_seed": kept, "added": sum(added.values()), "animations_added": len(added)}


def write_shards(queue_path: Path, shards: int, plan_workers: int) -> dict:
    from reboutcx_prepare_sources_p12 import write_new
    queue = read_json(queue_path)
    plan = Plan(load_jobs(queue_path), plan_workers)
    by_job = {resolve_path_reference(m["job"], required=True).resolve(): m for m in queue["members"]}
    groups = plan.partition(shards)
    written = []
    for index, jobs in enumerate(groups, 1):
        path = queue_path.with_name(f"queue-shard-{index}of{shards}.json")
        write_new(path, {"schema": QUEUE_SCHEMA, "installable": False, "members": [by_job[j] for j in jobs]})
        written.append({"queue": relative(path), "jobs": len(jobs), "cost_share": plan.shard_loads[index - 1] / sum(plan.shard_loads),
                        "unique_identities": plan.shard_unique_keys[index - 1]})
    return {"shards": written, "global_unique_identities": plan.unique_keys,
            "identities_computed_if_sharded": sum(plan.shard_unique_keys),
            "sharing_loss_percent": 100 * (sum(plan.shard_unique_keys) / plan.unique_keys - 1)}


def aggregate(step: float, interval: float) -> None:
    """Combine shard progress.json files into progress.json + milestones.log until every shard is complete."""
    next_milestone = step
    while True:
        records = []
        for path in sorted(WORK.glob("shard-*/progress.json")):
            try:
                records.append(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
        if records:
            done = sum(r["done_weight"] for r in records)
            total = sum(r["total_weight"] for r in records)
            fraction = done / total if total else 0.0
            elapsed = max(r["render_elapsed_seconds"] for r in records)
            eta = (total - done) * elapsed / done if fraction >= 0.02 and done else None
            rendered = sum(r["jobs_rendered"] + r["jobs_existing_verified"] for r in records)
            jobs = sum(r["jobs_total_in_session"] for r in records)
            computed = sum(r["model_frames_computed"] for r in records)
            frames = sum(r["source_frames_done"] for r in records)
            combined = {"updated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "shards_reporting": len(records),
                        "work_percent": 100 * fraction, "elapsed_seconds": elapsed, "eta_seconds": eta,
                        "jobs_done": rendered, "jobs_total": jobs, "model_frames_computed": computed,
                        "source_frames_done": frames, "rss_gib": sum((r["rss_gib"] or 0) for r in records),
                        "evictions": sum(r["cache"].get("evictions", 0) for r in records)}
            (WORK / "progress.tmp").write_text(json.dumps(combined, indent=1), encoding="utf-8")
            replace_best_effort(WORK / "progress.tmp", WORK / "progress.json")
            finished = bool(jobs) and rendered >= jobs and len(records) >= 2
            if 100 * fraction >= next_milestone or finished:
                while next_milestone <= 100 * fraction:
                    next_milestone += step
                line = (f"[{fmt(elapsed)}] {100 * fraction:.1f}% du travail | {rendered}/{jobs} composants | "
                        f"inférences {computed:,} | frames source {frames:,} | reste ≈ {fmt(eta)} | "
                        f"RAM {combined['rss_gib']:.1f} Gio | évictions {combined['evictions']}")
                with (WORK / "milestones.log").open("a", encoding="utf-8") as stream:
                    stream.write(line + "\n")
            if finished:
                return
        time.sleep(interval)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prepare_cmd = commands.add_parser("prepare")
    prepare_cmd.add_argument("output_dir", type=Path)
    prepare_cmd.add_argument("--id", action="append", help="default: every pending id of the previous snapshot")
    prepare_cmd.add_argument("--previous", type=Path, default=PROGRESS_SNAPSHOT)
    for name in ("plan", "run"):
        cmd = commands.add_parser(name)
        cmd.add_argument("queue", type=Path)
        cmd.add_argument("--plan-workers", type=int, default=12)
        if name == "run":
            cmd.add_argument("--components", type=int, default=5)
            cmd.add_argument("--pre-workers", type=int, default=3)
            cmd.add_argument("--post-workers", type=int, default=4)
            cmd.add_argument("--verify-workers", type=int, default=2)
            cmd.add_argument("--memory-mib", type=int, default=8192)
            cmd.add_argument("--cache-mib", type=int, default=None, help="default: retention estimate x1.35")
            cmd.add_argument("--milestone-percent", type=float, default=5.0)
            cmd.add_argument("--tag", default="")
            cmd.add_argument("--gpu-fraction", type=float, default=None)
    shard_cmd = commands.add_parser("shard")
    shard_cmd.add_argument("queue", type=Path)
    shard_cmd.add_argument("shards", type=int)
    shard_cmd.add_argument("--plan-workers", type=int, default=12)
    aggregate_cmd = commands.add_parser("aggregate")
    aggregate_cmd.add_argument("--milestone-percent", type=float, default=5.0)
    aggregate_cmd.add_argument("--interval", type=float, default=20.0)
    finish_cmd = commands.add_parser("finish")
    finish_cmd.add_argument("queue", type=Path)
    finish_cmd.add_argument("--report", type=Path, required=True)
    finish_cmd.add_argument("--workers", type=int, default=12)
    snapshot_cmd = commands.add_parser("snapshot")
    snapshot_cmd.add_argument("plan", type=Path)
    snapshot_cmd.add_argument("--report", type=Path, required=True)
    snapshot_cmd.add_argument("--id", default="p13-v1")
    catalog_cmd = commands.add_parser("catalog")
    catalog_cmd.add_argument("snapshot", type=Path)
    catalog_cmd.add_argument("--seed", type=Path, required=True)
    catalog_cmd.add_argument("--job-id", required=True)
    commands.add_parser("status")
    args = parser.parse_args()
    if args.command == "prepare":
        print(json.dumps(prepare_all(args.output_dir, args.id or pending_ids(args.previous), args.previous)))
    elif args.command == "plan":
        plan = Plan(load_jobs(args.queue), args.plan_workers)
        print(json.dumps({**plan.summary(), "cache_mib_auto": cache_limit_mib(plan, None)}, indent=2))
    elif args.command == "run":
        run_shared(args.queue, components=args.components, pre_workers=args.pre_workers, post_workers=args.post_workers,
                   memory_mib=args.memory_mib, cache_mib=args.cache_mib, plan_workers=args.plan_workers,
                   verify_workers=args.verify_workers, milestone_step=args.milestone_percent,
                   tag=args.tag, gpu_fraction=args.gpu_fraction)
    elif args.command == "shard":
        print(json.dumps(write_shards(args.queue, args.shards, args.plan_workers), indent=2))
    elif args.command == "finish":
        print(json.dumps(finish(args.queue, args.report, args.workers), indent=2))
    elif args.command == "snapshot":
        print(json.dumps(write_snapshot(args.plan, args.report, args.id), indent=2))
    elif args.command == "catalog":
        print(json.dumps(write_catalog_job(args.snapshot, args.seed, args.job_id), indent=2))
    elif args.command == "aggregate":
        aggregate(args.milestone_percent, args.interval)
    else:
        print((WORK / "progress.json").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
