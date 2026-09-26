"""Build a real x4 ReboutCX registry-set for the 0x6110 visual test.

The model output stays at x4.  A direct xBR4 guide supplies exact alpha and
palette-class provenance; classed OKLab quantization keeps Character recolors.
The result is streamed directly into runtime shards to avoid duplicate x4 data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import struct
import tempfile
import time
from collections import defaultdict, deque
from pathlib import Path

import numpy as np

import reboutcx_full as legacy
from reboutcx_batch import prepare_inference_rgb
from reboutcx_cache_p12 import frame_key
from reboutcx_cpu_p10 import map_output, quantize_classed_oklab, source_representatives
from reboutcx_full import (
    PROJECT_ROOT,
    is_null_frame,
    load_palette_profiles,
    load_source_frames,
    ordered_cycles,
    read_json,
    relative,
    resolve_path_reference,
    semantic_classes_for_job,
    sha256_file,
)
from reboutcx_runtime_p12 import Runtime, group_bytes, group_key, plan_groups
from run_creature_sprite_x2 import (
    MAX_REGISTRY_BYTES_BY_SCALE,
    MAX_RESOURCES,
    XN_REGISTRY_MAGIC,
    XN_REGISTRY_SHARD_FILENAME,
    XN_REGISTRY_VERSION,
    XN_REGISTRY_SET_FILENAME,
    direct_upscale_contract,
    has_duplicate_used_rgba_indices,
    inspect_registry,
    inspect_registry_set,
    run_xbr,
    write_registry_set_index,
    xbr_output_batch_ranges,
    xbr_provenance_indices,
)

SCALE = 4
ANIMATION_ID = 0x6110
RUN_ID = "reboutcx-x4-visual-v1"
REPORT = PROJECT_ROOT / "docs/measurements/reboutcx-p13-0x6110-20260921-v1/production-report.json"
OUTPUT = PROJECT_ROOT / (
    "sprite/families/playable-characters/6110-human-female-fighter/"
    "family-runs/reboutcx-x4-visual-v1"
)
XBR_BUDGET = 64 * 1024 * 1024
METHOD = {
    "algorithm": "ReboutCX",
    "model_scale": 4,
    "target_scale": 4,
    "downscale": None,
    "guide": "XBR/xbr4X one-pass antialias-off blend-off",
    "alpha": "xbr4x-mask-v1",
    "palette": "RANGES12; 32 semantic classes; classed OKLab; no dithering",
    "geometry": "native-x1",
    "sampling": "NEAREST",
}


def emit(event: str, **fields) -> None:
    print(json.dumps({"event": event, **fields}, ensure_ascii=False), flush=True)


def context_key(job: dict, classes: dict, scalepix_sha256: str) -> bytes:
    value = {
        "contract": METHOD,
        "model_sha256": job["reboutcx"]["model_sha256"],
        "fp16": bool(job["reboutcx"]["fp16"]),
        "classes": classes,
        "marker": int(job["null_frame_marker"]),
        "scalepix_sha256": scalepix_sha256,
        "node": job["tools"].get("node", "node"),
    }
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).digest()


def xbr4_batches(frames, scalepix: Path, node: str):
    contract = direct_upscale_contract(4)
    for start, end, _ in xbr_output_batch_ranges(frames, 4, XBR_BUDGET):
        batch = frames[start:end]
        for frame, output in zip(
            batch, run_xbr(batch, scalepix, node, contract), strict=True
        ):
            yield frame, output


def prepare_resource_x4(resource, scalepix, node, marker, palette, classes):
    started = time.perf_counter()
    frames = resource["frames"]
    non_null = [frame for frame in frames if not is_null_frame(frame, marker)]
    iterator = iter(xbr4_batches(non_null, scalepix, node)) if non_null else iter(())
    states = {}
    timing = defaultdict(float)
    for frame in frames:
        colors = frame.palette if palette is None else palette
        state = {"frame": frame, "palette": colors}
        if is_null_frame(frame, marker):
            names = [name for name, indices in classes.items() if marker in indices]
            if len(names) != 1:
                raise RuntimeError("null marker must belong to exactly one semantic class")
            guide = np.full((4, 4), marker, dtype=np.uint8)
            state.update(
                guide=guide,
                representatives=source_representatives(frame.indices),
                quantized=guide.copy(),
                rgb=None,
                metrics={
                    "visible_pixels": 16 if palette is not None else 0,
                    "class_pixels": {names[0]: 16},
                    "oklab_error_mean": 0.0,
                    "oklab_error_p95": 0.0,
                    "oklab_error_max": 0.0,
                    "model_bypassed": True,
                },
            )
            timing["null_frames"] += 1
        else:
            tick = time.perf_counter()
            returned, (width, height, rgba) = next(iterator)
            timing["xbr4_seconds"] += time.perf_counter() - tick
            if returned is not frame or (width, height) != (
                frame.width * 4,
                frame.height * 4,
            ):
                raise RuntimeError("xBR4 order or geometry differs")
            provenance = (
                xbr_provenance_indices(frame, 4)
                if has_duplicate_used_rgba_indices(frame)
                else None
            )
            guide, representatives = map_output(frame, rgba, provenance)
            state.update(
                guide=guide.reshape(height, width),
                representatives=representatives,
                rgb=prepare_inference_rgb(frame, colors),
            )
        states[frame.index] = state
    if next(iterator, None) is not None:
        raise RuntimeError("xBR4 returned extra frames")
    timing["prepare_wall_seconds"] = time.perf_counter() - started
    return states, dict(timing)


def postprocess_batch_x4(items, classes):
    started = time.perf_counter()
    results = []
    timing = defaultdict(float)
    for token, guide, palette, used, transparent, crop in items:
        tick = time.perf_counter()
        if crop is None:
            target = np.full((*guide.shape, 3), palette[transparent], dtype=np.uint8)
        else:
            if crop.shape[:2] != guide.shape:
                raise RuntimeError("ReboutCX x4 output and xBR4 guide differ")
            target = np.rint(np.clip(crop, 0, 1) * 255.0).astype(np.uint8)
        timing["round_x4_seconds"] += time.perf_counter() - tick
        tick = time.perf_counter()
        quantized, metrics = quantize_classed_oklab(
            target,
            guide,
            palette,
            used,
            classes,
            transparent_index=transparent,
        )
        if crop is None:
            metrics["model_bypassed"] = True
        timing["quantization_seconds"] += time.perf_counter() - tick
        results.append((token, quantized, metrics))
    timing["post_wall_seconds"] = time.perf_counter() - started
    return results, dict(timing)


class GroupWindowX4:
    def __init__(self, runtime, *, scalepix, node, marker, palette, classes, cache_context):
        self.runtime = runtime
        self.arguments = (scalepix, node, marker, palette, classes)
        self.context = cache_context
        self.palette = palette
        self.pending = {}

    def get(self, resources):
        key = group_key(resources)
        size = group_bytes(resources)
        self.runtime.memory.acquire(size)
        record = {"size": size, "futures": [], "tickets": []}
        self.pending[key] = record
        all_states = {}
        timing = defaultdict(float)
        for resource in resources:
            name = str(resource["source"]["name"]).upper()
            states = {}
            selected = []
            all_states[name] = states
            for frame in resource["frames"]:
                state = {
                    "frame": frame,
                    "palette": frame.palette if self.palette is None else self.palette,
                }
                states[frame.index] = state
                if is_null_frame(frame, self.arguments[2]):
                    selected.append(frame)
                    continue
                ticket = self.runtime.cache.claim(
                    frame_key(frame, self.palette, self.context)
                )
                record["tickets"].append(ticket)
                state["cache_ticket"] = ticket
                if ticket.owner:
                    selected.append(frame)
            if selected:
                reduced = {**resource, "frames": selected}
                future = self.runtime.pre.submit(
                    prepare_resource_x4, reduced, *self.arguments
                )
                record["futures"].append((name, future, time.perf_counter()))
        for name, future, submitted in record["futures"]:
            prepared, elapsed = future.result()
            for index, state in prepared.items():
                original = all_states[name][index]["frame"]
                all_states[name][index].update(state)
                all_states[name][index]["frame"] = original
            for label, value in elapsed.items():
                timing[label] += value
            timing["prepare_queue_wait_seconds"] += time.perf_counter() - submitted
        return all_states, dict(timing)

    def release(self, resources):
        record = self.pending.pop(group_key(resources))
        try:
            for ticket in record["tickets"]:
                self.runtime.cache.fail(ticket, RuntimeError("x4 group closed early"))
            for _name, future, _submitted in record["futures"]:
                if not future.cancel():
                    future.result()
        finally:
            self.runtime.memory.release(record["size"])


def process_group_x4(runtime, resources, states, *, fp16, classes):
    timing = defaultdict(float)
    buckets = defaultdict(list)
    bypass = []
    pending = deque()

    def publish(state):
        ticket = state.get("cache_ticket")
        if ticket is not None and ticket.owner:
            runtime.cache.publish(
                ticket,
                {
                    "guide": state["guide"],
                    "quantized": state["quantized"],
                    "metrics": state["metrics"],
                    "representatives": state["representatives"],
                },
            )

    for resource in resources:
        name = str(resource["source"]["name"]).upper()
        for frame in resource["frames"]:
            state = states[name][frame.index]
            ticket = state.get("cache_ticket")
            if ticket is not None and not ticket.owner:
                continue
            if "quantized" in state:
                publish(state)
            elif state["rgb"] is None:
                bypass.append((name, frame.index))
            else:
                height, width = state["rgb"].shape[:2]
                canvas = ((height + 31) // 32 * 32, (width + 31) // 32 * 32)
                buckets[canvas].append((name, frame.index))

    def collect():
        results, elapsed = pending.popleft().result()
        for label, value in elapsed.items():
            timing[label] += value
        for (name, index), quantized, metrics in results:
            state = states[name][index]
            state.update(quantized=quantized, metrics=metrics)
            publish(state)

    def submit(tokens, crops):
        requests = []
        for (name, index), crop in zip(tokens, crops, strict=True):
            state = states[name][index]
            frame = state["frame"]
            requests.append(
                (
                    (name, index),
                    state["guide"],
                    state["palette"],
                    np.unique(frame.indices),
                    frame.transparent,
                    crop,
                )
            )
        pending.append(runtime.post.submit(postprocess_batch_x4, requests, classes))
        if len(pending) >= 2:
            collect()

    for start in range(0, len(bypass), 86):
        batch = bypass[start : start + 86]
        submit(batch, [None] * len(batch))
    for canvas, tokens in buckets.items():
        for start in range(0, len(tokens), 86):
            batch = tokens[start : start + 86]
            rgbs = [states[name][index]["rgb"] for name, index in batch]
            crops, elapsed = runtime.infer(rgbs, canvas, fp16).result()
            for label, value in elapsed.items():
                timing[label] += value
            timing["model_frames"] += len(batch)
            timing["batches"] += 1
            submit(batch, crops)
            del crops
    while pending:
        collect()
    for resource in resources:
        name = str(resource["source"]["name"]).upper()
        for frame in resource["frames"]:
            state = states[name][frame.index]
            ticket = state.get("cache_ticket")
            if ticket is not None:
                state.update(ticket.future.result())
                state["cache_reused"] = not ticket.owner
            state.pop("rgb", None)
    return dict(timing)


def projected_resource_bytes(resource) -> int:
    frames = resource["frames"]
    cycles = ordered_cycles(resource)
    return 48 + sum(528 + frame.width * frame.height * 16 for frame in frames) + sum(
        4 + 4 * len(cycle["frame_indices"]) for cycle in cycles
    )


class ShardWriter:
    def __init__(self, root: Path):
        self.root = root
        self.index = -1
        self.stream = None
        self.path = None
        self.count = 0
        self.size = 0
        self.paths = []
        self.start()

    def start(self):
        self.index += 1
        self.path = self.root / XN_REGISTRY_SHARD_FILENAME.format(index=self.index)
        self.stream = self.path.open("xb")
        self.stream.write(XN_REGISTRY_MAGIC)
        self.stream.write(struct.pack("<IIII", XN_REGISTRY_VERSION, 4, 0, ANIMATION_ID))
        self.count = 0
        self.size = 24

    def ensure(self, resource_bytes: int):
        limit = MAX_REGISTRY_BYTES_BY_SCALE[4]
        if resource_bytes + 24 > limit:
            raise RuntimeError("one x4 resource exceeds the shard byte limit")
        if self.count and (self.count >= MAX_RESOURCES or self.size + resource_bytes > limit):
            self.finish_current()
            self.start()

    def write_resource(self, resource, states):
        expected = projected_resource_bytes(resource)
        self.ensure(expected)
        start = self.stream.tell()
        resref = str(resource["source"]["name"]).upper()
        cycles = ordered_cycles(resource)
        self.stream.write(resref.encode("ascii").ljust(8, b"\0"))
        self.stream.write(bytes.fromhex(sha256_file(resource["source_path"])))
        self.stream.write(struct.pack("<II", len(resource["frames"]), len(cycles)))
        for frame in resource["frames"]:
            state = states[frame.index]
            payload = np.ascontiguousarray(state["quantized"], dtype=np.uint8)
            if payload.shape != (frame.height * 4, frame.width * 4):
                raise RuntimeError(f"{resref} frame {frame.index}: invalid x4 payload")
            representatives = np.asarray(state["representatives"], dtype="<u2")
            if np.any(representatives[payload] == 0xFFFF):
                raise RuntimeError(f"{resref} frame {frame.index}: invalid palette index")
            self.stream.write(
                struct.pack(
                    "<HHhhB3xI",
                    frame.width,
                    frame.height,
                    frame.center_x,
                    frame.center_y,
                    frame.transparent,
                    payload.size,
                )
            )
            self.stream.write(representatives.tobytes())
            self.stream.write(payload.tobytes())
        legacy.write_cycles(self.stream, cycles)
        written = self.stream.tell() - start
        if written != expected:
            raise RuntimeError(f"{resref}: projected and written bytes differ")
        self.count += 1
        self.size += written

    def finish_current(self):
        if self.stream is None:
            return
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.stream.seek(8)
        self.stream.write(struct.pack("<IIII", XN_REGISTRY_VERSION, 4, self.count, ANIMATION_ID))
        self.stream.close()
        self.paths.append(self.path)
        self.stream = None

    def finish(self):
        self.finish_current()
        return self.paths


def load_jobs() -> list[Path]:
    report = read_json(REPORT)
    jobs = [resolve_path_reference(record["job"], required=True) for record in report["records"]]
    if len(jobs) != 65 or len(set(jobs)) != 65:
        raise RuntimeError("expected exactly 65 P13 source jobs")
    return jobs


def build(*, memory_mib: int, cache_mib: int) -> dict:
    if OUTPUT.exists():
        raise RuntimeError(f"x4 visual run already exists: {relative(OUTPUT)}")
    jobs = load_jobs()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".reboutcx-x4-visual-", dir=OUTPUT.parent))
    pack = temporary / "build/iee-assets/creature-sprites"
    pack.mkdir(parents=True)
    started = time.perf_counter()
    writer = ShardWriter(pack)
    totals = defaultdict(float)
    resource_count = frame_count = 0
    source_jobs = []
    seen_resrefs = set()
    emit("start", jobs=len(jobs), output=relative(OUTPUT), target_scale=4)
    try:
        with Runtime(memory_mib=memory_mib, cache_mib=cache_mib) as runtime:
            for number, job_path in enumerate(jobs, 1):
                job = read_json(job_path)
                if int(job["animation_id"], 16) != ANIMATION_ID:
                    raise RuntimeError("source job animation differs from 0x6110")
                source_manifest_path = resolve_path_reference(
                    job["paths"]["source_manifest"], required=True
                )
                if sha256_file(source_manifest_path) != job["source_manifest_sha256"]:
                    raise RuntimeError("source manifest hash differs")
                model = resolve_path_reference(job["paths"]["reboutcx_model"], required=True)
                if sha256_file(model) != job["reboutcx"]["model_sha256"]:
                    raise RuntimeError("ReboutCX model hash differs")
                scalepix = resolve_path_reference(job["paths"]["scalepix"], required=True)
                _frames, resources, source_manifest = load_source_frames(source_manifest_path)
                if int(source_manifest["animation_id"], 16) != ANIMATION_ID:
                    raise RuntimeError("source animation differs")
                inventory = [str(resource["source"]["name"]).upper() for resource in resources]
                if inventory != [str(item["name"]).upper() for item in job["source_inventory"]]:
                    raise RuntimeError("source inventory differs")
                duplicates = seen_resrefs.intersection(inventory)
                if duplicates:
                    raise RuntimeError(f"duplicate resources across components: {sorted(duplicates)}")
                seen_resrefs.update(inventory)
                classes, classes_id = semantic_classes_for_job(job)
                profiles, palette_evidence = load_palette_profiles(job)
                palette = profiles[0]["palette"] if profiles else None
                runtime.model_info(
                    model,
                    device=str(job["reboutcx"]["device"]),
                    fp16=bool(job["reboutcx"]["fp16"]),
                )
                window = GroupWindowX4(
                    runtime,
                    scalepix=scalepix,
                    node=str(job["tools"].get("node", "node")),
                    marker=int(job["null_frame_marker"]),
                    palette=palette,
                    classes=classes,
                    cache_context=context_key(job, classes, sha256_file(scalepix)),
                )
                for group in plan_groups(resources):
                    states, elapsed = window.get(group)
                    for key, value in elapsed.items():
                        totals[key] += value
                    elapsed = process_group_x4(
                        runtime,
                        group,
                        states,
                        fp16=bool(job["reboutcx"]["fp16"]),
                        classes=classes,
                    )
                    for key, value in elapsed.items():
                        totals[key] += value
                    for resource in group:
                        name = str(resource["source"]["name"]).upper()
                        writer.write_resource(resource, states[name])
                        resource_count += 1
                        frame_count += len(resource["frames"])
                    window.release(group)
                    del states
                source_jobs.append(
                    {
                        "job": relative(job_path),
                        "job_sha256": sha256_file(job_path),
                        "source_manifest": relative(source_manifest_path),
                        "source_manifest_sha256": sha256_file(source_manifest_path),
                        "layer": job.get("layer"),
                        "item_resref": job.get("item_resref"),
                        "resources": len(resources),
                        "frames": sum(len(resource["frames"]) for resource in resources),
                        "semantic_classes_id": classes_id,
                        "palette_reference": palette_evidence,
                    }
                )
                emit(
                    "component",
                    number=number,
                    total=len(jobs),
                    job=relative(job_path),
                    resources=len(resources),
                    frames=sum(len(resource["frames"]) for resource in resources),
                    elapsed_seconds=round(time.perf_counter() - started, 3),
                )
            shard_paths = writer.finish()
            shard_infos = []
            for path in shard_paths:
                info = inspect_registry(path)
                if info["scale"] != 4 or info["animation_id"].upper() != "0X6110":
                    raise RuntimeError("x4 shard identity differs")
                info["path"] = path
                shard_infos.append(info)
            set_path = pack / XN_REGISTRY_SET_FILENAME
            set_info = write_registry_set_index(set_path, 4, ANIMATION_ID, shard_infos)
            verified = inspect_registry_set(set_path)
            if verified != set_info:
                raise RuntimeError("registry-set verification differs")
            manifest = {
                "schema": "bg2-upscale-reboutcx-x4-visual-pack-v1",
                "status": "built-pending-ingame-qa",
                "installable": True,
                "test_only": True,
                "animation_id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "runtime_profile": "character-bg2ee-2.7.3.0",
                "target_scale": 4,
                "method": METHOD,
                "source_report": relative(REPORT),
                "source_report_sha256": sha256_file(REPORT),
                "source_jobs": source_jobs,
                "coverage": {
                    "components": len(jobs),
                    "resources": resource_count,
                    "frames": frame_count,
                },
                "registry_layout": "set",
                "registry_set": "iee-assets/creature-sprites/CreatureSprites-XN.set",
                "registry_set_sha256": set_info["sha256"],
                "registry_set_bytes": set_info["registry_set_bytes"],
                "shards": [
                    {
                        "index": index,
                        "path": f"iee-assets/creature-sprites/{path.name}",
                        "sha256": info["sha256"],
                        "crc32": info["crc32"],
                        "resources": info["resource_count"],
                        "frames": info["frame_count"],
                        "index_bytes": info["index_bytes"],
                        "bytes": info["registry_bytes"],
                    }
                    for index, (path, info) in enumerate(zip(shard_paths, shard_infos, strict=True))
                ],
                "totals": {
                    "resources": set_info["resource_count"],
                    "frames": set_info["frame_count"],
                    "index_bytes": set_info["index_bytes"],
                    "registry_bytes": set_info["registry_bytes"],
                    "shards": len(shard_infos),
                },
                "timing_seconds": {
                    **{key: float(value) for key, value in totals.items()},
                    "wall": time.perf_counter() - started,
                },
                "cache": runtime.cache.snapshot(),
                "code": {
                    "path": relative(Path(__file__)),
                    "sha256": sha256_file(Path(__file__)),
                },
            }
            (temporary / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        temporary.replace(OUTPUT)
        emit(
            "complete",
            output=relative(OUTPUT),
            manifest_sha256=sha256_file(OUTPUT / "manifest.json"),
            resources=resource_count,
            frames=frame_count,
            shards=len(shard_paths),
            registry_bytes=set_info["registry_bytes"],
            elapsed_seconds=round(time.perf_counter() - started, 3),
        )
        return manifest
    except BaseException:
        try:
            if writer.stream is not None:
                writer.stream.close()
        finally:
            shutil.rmtree(temporary, ignore_errors=True)
        raise


def verify() -> dict:
    manifest_path = OUTPUT / "manifest.json"
    manifest = read_json(manifest_path)
    if (
        manifest.get("schema") != "bg2-upscale-reboutcx-x4-visual-pack-v1"
        or manifest.get("target_scale") != 4
        or manifest.get("animation_id") != "0x6110"
        or manifest.get("method") != METHOD
    ):
        raise RuntimeError("invalid x4 visual manifest")
    pack = OUTPUT / "build/iee-assets/creature-sprites"
    set_path = pack / XN_REGISTRY_SET_FILENAME
    info = inspect_registry_set(set_path)
    if (
        info["scale"] != 4
        or info["animation_id"].upper() != "0X6110"
        or info["sha256"] != manifest["registry_set_sha256"]
        or info["resource_count"] != manifest["coverage"]["resources"]
        or info["frame_count"] != manifest["coverage"]["frames"]
    ):
        raise RuntimeError("x4 registry-set differs from manifest")
    result = {
        "status": "verified",
        "manifest": relative(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "scale": info["scale"],
        "animation_id": info["animation_id"],
        "resources": info["resource_count"],
        "frames": info["frame_count"],
        "registry_bytes": info["registry_bytes"],
        "shards": len(info["shards"]),
    }
    print(json.dumps(result, indent=2))
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--memory-mib", type=int, default=8192)
    run.add_argument("--cache-mib", type=int, default=2048)
    commands.add_parser("verify")
    args = parser.parse_args()
    if args.command == "run":
        build(memory_mib=args.memory_mib, cache_mib=args.cache_mib)
        verify()
    else:
        verify()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
