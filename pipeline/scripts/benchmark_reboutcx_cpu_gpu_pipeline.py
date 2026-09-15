"""Measure bounded CPU xBR/quantization overlap with one ReboutCX GPU batcher."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from pathlib import Path

import numpy as np

from reboutcx_batch import (
    infer_x4_box_x2_padded_batch,
    is_null_frame,
    load_model,
    load_palette_profiles,
    prepare_inference_rgb,
)
from reboutcx_full import xbr_batches
from reboutcx_quantize import quantize_classed_oklab, semantic_classes_for_job
from run_creature_sprite_x2 import (
    has_duplicate_used_rgba_indices,
    load_source_frames,
    map_output,
    xbr_provenance_indices,
)
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def configured_python(job: dict) -> Path:
    path = resolve_path_reference(job["paths"]["chainner_python"], required=True, root=PROJECT_ROOT)
    expected = str(job["tools"].get("chainner_python_sha256", ""))
    if expected and sha256_file(path) != expected:
        raise RuntimeError("configured chaiNNer Python hash differs")
    return path.resolve()


def preprocess_resource(resource: dict, *, scalepix: Path, node: str, marker: int, palette: np.ndarray) -> dict:
    started = time.perf_counter()
    xbr_seconds = 0.0
    items: list[tuple] = []
    non_null = [frame for frame in resource["frames"] if not is_null_frame(frame, marker)]
    iterator = iter(xbr_batches(non_null, scalepix, node))
    for frame in resource["frames"]:
        if is_null_frame(frame, marker):
            continue
        tick = time.perf_counter()
        xbr_frame, (width, height, xbr_bytes) = next(iterator)
        xbr_seconds += time.perf_counter() - tick
        if xbr_frame is not frame or (width, height) != (frame.width * 2, frame.height * 2):
            raise RuntimeError(f"{frame.resref} frame ordering or geometry differs")
        provenance = xbr_provenance_indices(frame, 2) if has_duplicate_used_rgba_indices(frame) else None
        guide_flat, _representatives = map_output(frame, xbr_bytes, provenance)
        rgb = prepare_inference_rgb(frame, palette)
        if rgb is not None:
            items.append((frame, guide_flat.reshape(height, width), rgb))
    return {"items": items, "xbr_seconds": xbr_seconds, "wall_seconds": time.perf_counter() - started}


def quantize_item(item: tuple, target_rgb: np.ndarray, *, palette: np.ndarray, classes: dict[str, list[int]]) -> float:
    frame, guide, _rgb = item
    started = time.perf_counter()
    quantize_classed_oklab(
        target_rgb,
        guide,
        palette,
        np.unique(frame.indices),
        classes,
        transparent_index=frame.transparent,
    )
    return time.perf_counter() - started


def run_pipeline(job_path: Path, source_path: Path, *, batch_size: int, cpu_workers: int, bucket_quantum: int) -> dict:
    job = read_json(job_path)
    source = source_path.resolve()
    frames, resources, source_manifest = load_source_frames(source)
    if source_manifest.get("runtime_profile") != job.get("runtime_profile"):
        raise RuntimeError("source runtime profile differs from benchmark model job")
    classes, _classes_id = semantic_classes_for_job(job)
    profiles, _evidence = load_palette_profiles(job)
    palette = profiles[0]["palette"] if profiles else None
    if palette is None:
        raise RuntimeError("Character benchmark requires a reference palette")
    scalepix = resolve_path_reference(job["paths"]["scalepix"], required=True, root=PROJECT_ROOT)
    model_path = resolve_path_reference(job["paths"]["reboutcx_model"], required=True, root=PROJECT_ROOT)
    descriptor, _versions = load_model(model_path, device=str(job["reboutcx"]["device"]), fp16=bool(job["reboutcx"]["fp16"]))

    marker = int(job["null_frame_marker"])
    started = time.perf_counter()
    buckets: dict[tuple[int, int, int], list[tuple]] = defaultdict(list)
    post_futures = []
    timing = defaultdict(float)
    batches: list[int] = []

    def dispatch(items: list[tuple], canvas: tuple[int, int], post_pool: ThreadPoolExecutor) -> None:
        gpu_started = time.perf_counter()
        outputs = infer_x4_box_x2_padded_batch(
            descriptor,
            [item[2] for item in items],
            canvas_height=canvas[0],
            canvas_width=canvas[1],
            fp16=bool(job["reboutcx"]["fp16"]),
        )
        timing["gpu_seconds"] += time.perf_counter() - gpu_started
        batches.append(len(items))
        for item, (_x4, x2) in zip(items, outputs, strict=True):
            post_futures.append(post_pool.submit(quantize_item, item, x2, palette=palette, classes=classes))

    with ThreadPoolExecutor(max_workers=cpu_workers) as pre_pool, ThreadPoolExecutor(max_workers=cpu_workers) as post_pool:
        pending = {
            pre_pool.submit(
                preprocess_resource,
                resource,
                scalepix=scalepix,
                node=str(job["tools"].get("node", "node")),
                marker=marker,
                palette=palette,
            )
            for resource in resources
        }
        while pending:
            done, pending = wait(pending, return_when=FIRST_COMPLETED)
            for future in done:
                report = future.result()
                timing["preprocess_cpu_seconds"] += report["wall_seconds"]
                timing["xbr_seconds"] += report["xbr_seconds"]
                for item in report["items"]:
                    height, width = item[2].shape[:2]
                    canvas = (
                        ((height + bucket_quantum - 1) // bucket_quantum) * bucket_quantum,
                        ((width + bucket_quantum - 1) // bucket_quantum) * bucket_quantum,
                    )
                    bucket = buckets[canvas]
                    bucket.append(item)
                    if len(bucket) == batch_size:
                        dispatch(bucket, canvas, post_pool)
                        buckets[canvas] = []
        for canvas, bucket in buckets.items():
            if bucket:
                dispatch(bucket, canvas, post_pool)
        timing["quantize_cpu_seconds"] = sum(future.result() for future in post_futures)

    wall = time.perf_counter() - started
    model_frames = sum(batches)
    return {
        "job": str(job_path),
        "source_manifest": str(source),
        "status": "benchmark-only-no-output",
        "resources": len(resources),
        "source_frames": len(frames),
        "model_frames": model_frames,
        "batch_size_cap": batch_size,
        "bucket_quantum": bucket_quantum,
        "batches": len(batches),
        "full_batches": sum(size == batch_size for size in batches),
        "tail_batches": sum(size != batch_size for size in batches),
        "cpu_workers_pre": cpu_workers,
        "cpu_workers_post": cpu_workers,
        "wall_seconds": round(wall, 3),
        "model_frames_per_second": round(model_frames / wall, 3),
        "timing_seconds": {key: round(value, 3) for key, value in sorted(timing.items())},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path, help="P8 Character job providing model/palette contract")
    parser.add_argument("source_manifest", type=Path, help="unprocessed compatible Character source")
    parser.add_argument("--batch-size", type=int, default=86)
    parser.add_argument("--cpu-workers", type=int, default=6)
    parser.add_argument("--bucket-quantum", type=int, default=64)
    parser.add_argument("--configured", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1 or args.cpu_workers < 1 or args.bucket_quantum < 1:
        raise RuntimeError("batch size, CPU workers and bucket quantum must be positive")
    job_path = args.job.resolve()
    source_path = args.source_manifest.resolve()
    job = read_json(job_path)
    python = configured_python(job)
    if not args.configured and Path(sys.executable).resolve() != python:
        return subprocess.run(
            [str(python), str(Path(__file__).resolve()), str(job_path), str(source_path), "--configured", "--batch-size", str(args.batch_size), "--cpu-workers", str(args.cpu_workers), "--bucket-quantum", str(args.bucket_quantum)],
            check=False,
        ).returncode
    print(json.dumps(run_pipeline(job_path, source_path, batch_size=args.batch_size, cpu_workers=args.cpu_workers, bucket_quantum=args.bucket_quantum), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
