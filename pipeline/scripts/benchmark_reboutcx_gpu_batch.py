"""Measure P8 ReboutCX CUDA micro-batches against one real Character frame."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from reboutcx_batch import (
    infer_x4_box_x2,
    infer_x4_box_x2_batch,
    is_null_frame,
    load_model,
    prepare_inference_rgb,
)
from run_creature_sprite_x2 import load_source_frames
from workspace_paths import resolve_path_reference


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[1]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def sha256_array(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest().upper()


def configured_python(job: dict) -> Path:
    path = resolve_path_reference(job["paths"]["chainner_python"], required=True, root=PROJECT_ROOT)
    expected = str(job["tools"].get("chainner_python_sha256", ""))
    if expected and sha256_file(path) != expected:
        raise RuntimeError("configured chaiNNer Python hash differs")
    return path.resolve()


def sample_inputs(job: dict, *, source_override: Path | None, count: int) -> tuple[Path, list[tuple[np.ndarray, str, int]]]:
    source = (
        source_override.resolve()
        if source_override is not None
        else resolve_path_reference(job["paths"]["source_manifest"], required=True, root=PROJECT_ROOT)
    )
    frames, _resources, _manifest = load_source_frames(source)
    marker = int(job["null_frame_marker"])
    groups: dict[tuple[int, int, int], list[tuple[np.ndarray, str, int]]] = {}
    for frame in frames:
        if is_null_frame(frame, marker):
            continue
        rgb = prepare_inference_rgb(frame, frame.palette)
        if rgb is not None:
            groups.setdefault(tuple(rgb.shape), []).append((rgb, frame.resref, frame.index))
    if not groups:
        raise RuntimeError("sample job has no model-evaluated frame")
    _shape, selected = max(groups.items(), key=lambda item: (len(item[1]), item[0][0] * item[0][1]))
    if not selected:
        raise RuntimeError("sample job has no model-evaluated frame")
    selected = selected[:count]
    if len(selected) < count:
        selected = [selected[index % len(selected)] for index in range(count)]
    return source, selected


def benchmark(job_path: Path, batch_sizes: list[int], repeats: int, source_override: Path | None) -> dict:
    import torch

    job = read_json(job_path)
    torch.backends.cudnn.deterministic = True
    torch.use_deterministic_algorithms(True)
    model_path = resolve_path_reference(job["paths"]["reboutcx_model"], required=True, root=PROJECT_ROOT)
    descriptor, _versions = load_model(model_path, device=str(job["reboutcx"]["device"]), fp16=bool(job["reboutcx"]["fp16"]))
    source, samples = sample_inputs(job, source_override=source_override, count=max(batch_sizes))
    rows = []
    for batch_size in batch_sizes:
        chosen = samples[:batch_size]
        inputs = [item[0] for item in chosen]
        baseline = [
            infer_x4_box_x2(descriptor, rgb, fp16=bool(job["reboutcx"]["fp16"]))
            for rgb in inputs
        ]
        torch.cuda.reset_peak_memory_stats()
        check = infer_x4_box_x2_batch(descriptor, inputs, fp16=bool(job["reboutcx"]["fp16"]))
        exact = True
        changed_x4 = changed_x2 = max_delta_x4 = max_delta_x2 = 0
        for position, ((x4, x2), (baseline_x4, baseline_x2)) in enumerate(zip(check, baseline, strict=True)):
            if (sha256_array(x4), sha256_array(x2)) != (sha256_array(baseline_x4), sha256_array(baseline_x2)):
                exact = False
                changed_x4 = max(changed_x4, int(np.count_nonzero(x4 != baseline_x4)))
                changed_x2 = max(changed_x2, int(np.count_nonzero(x2 != baseline_x2)))
                max_delta_x4 = max(max_delta_x4, int(np.abs(x4.astype(np.int16) - baseline_x4.astype(np.int16)).max()))
                max_delta_x2 = max(max_delta_x2, int(np.abs(x2.astype(np.int16) - baseline_x2.astype(np.int16)).max()))
        torch.cuda.synchronize()
        started = time.perf_counter()
        for _ in range(repeats):
            infer_x4_box_x2_batch(descriptor, inputs, fp16=bool(job["reboutcx"]["fp16"]))
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - started
        rows.append(
            {
                "batch_size": batch_size,
                "frames": batch_size * repeats,
                "elapsed_seconds": round(elapsed, 6),
                "frames_per_second": round((batch_size * repeats) / elapsed, 3),
                "peak_cuda_mib": round(torch.cuda.max_memory_allocated() / (1024 * 1024), 1),
                "pixel_contract": "matches-batch-1" if exact else "differs-from-batch-1",
                "changed_x4_channels": changed_x4,
                "max_delta_x4": max_delta_x4,
                "changed_x2_channels": changed_x2,
                "max_delta_x2": max_delta_x2,
            }
        )
    return {
        "job": str(job_path),
        "sample_source_manifest": str(source),
        "sample_shape": list(samples[0][0].shape),
        "sample_frames_preview": [{"resref": resref, "frame": index} for _rgb, resref, index in samples[:8]],
        "sample_frame_count": len(samples),
        "distinct_sample_frames": len({(resref, index) for _rgb, resref, index in samples}),
        "repeats": repeats,
        "results": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job", type=Path)
    parser.add_argument("--batch-sizes", type=int, nargs="+", default=[1, 2, 4, 8, 16, 32])
    parser.add_argument("--repeats", type=int, default=12)
    parser.add_argument("--source-manifest", type=Path)
    parser.add_argument("--configured", action="store_true")
    args = parser.parse_args()
    job_path = args.job.resolve()
    job = read_json(job_path)
    python = configured_python(job)
    if not args.configured and Path(sys.executable).resolve() != python:
        command = [str(python), str(Path(__file__).resolve()), str(job_path), "--configured", "--batch-sizes", *map(str, args.batch_sizes), "--repeats", str(args.repeats)]
        if args.source_manifest is not None:
            command.extend(["--source-manifest", str(args.source_manifest.resolve())])
        return subprocess.run(command, check=False).returncode
    print(json.dumps(benchmark(job_path, args.batch_sizes, args.repeats, args.source_manifest), separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
