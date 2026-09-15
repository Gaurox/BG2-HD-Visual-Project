"""P9 Character runner: one CUDA model process, variable-size micro-batches.

P8 files are evidence-bearing and intentionally untouched.  P9 writes only to
new run directories named by its job, and records both this runner and its
batch helper in the usual full-run manifest.
"""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

import reboutcx_full as p8
from reboutcx_batch_p9 import infer_x4_box_x2_padded_batch, prepare_inference_rgb


SCRIPT_PATH = Path(__file__).resolve()
P9_BATCH_SIZE = 86
P9_CPU_WORKERS = 3
P9_BUCKET_QUANTUM = 64


def canvas_for(rgb: np.ndarray) -> tuple[int, int]:
    height, width = rgb.shape[:2]
    quantum = P9_BUCKET_QUANTUM
    return (
        ((height + quantum - 1) // quantum) * quantum,
        ((width + quantum - 1) // quantum) * quantum,
    )


def p9_quantize(
    state: dict[str, Any],
    target_rgb: np.ndarray,
    *,
    classes: dict[str, list[int]],
) -> tuple[np.ndarray, dict[str, Any], float]:
    frame = state["frame"]
    started = time.perf_counter()
    quantized, metrics = p8.quantize_classed_oklab(
        target_rgb,
        state["guide"],
        state["palette"],
        np.unique(frame.indices),
        classes,
        transparent_index=frame.transparent,
    )
    return quantized, metrics, time.perf_counter() - started


def render_resource_p9(
    *,
    resource: dict[str, Any],
    component_path: Path,
    animation_id: int,
    descriptor: Any,
    fp16: bool,
    scalepix: Path,
    node: str,
    classes: dict[str, list[int]],
    marker_index: int,
    reference_palette: np.ndarray | None,
    qa_indices: set[int],
    reference: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[int, dict[str, Any]], dict[str, float | int]]:
    """Render one resource, batching model-ready frames by 64px canvas.

    ``reference`` is deliberately unused: P9's batched floating-point result is
    its own versioned pixel contract, rather than P8's single-frame witness.
    """
    del reference
    frames = resource["frames"]
    cycles = p8.ordered_cycles(resource)
    resref = str(resource["source"]["name"]).upper()
    states: dict[int, dict[str, Any]] = {}
    buckets: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    timing: dict[str, float | int] = {
        "xbr": 0.0,
        "reboutcx": 0.0,
        "quantization": 0.0,
        "model_frames": 0,
        "null_frames": 0,
    }
    non_null = [frame for frame in frames if not p8.is_null_frame(frame, marker_index)]
    xbr_iterator = iter(p8.xbr_batches(non_null, scalepix, node))

    for frame in frames:
        palette = frame.palette if reference_palette is None else reference_palette
        state: dict[str, Any] = {"frame": frame, "palette": palette}
        if p8.is_null_frame(frame, marker_index):
            guide = np.full((2, 2), marker_index, dtype=np.uint8)
            marker_classes = [name for name, indices in classes.items() if marker_index in indices]
            if len(marker_classes) != 1:
                raise RuntimeError("null marker must belong to exactly one semantic class")
            state.update(
                {
                    "guide": guide,
                    "xbr_rgba": p8.reconstruct_rgba(guide, palette, frame.transparent),
                    "target_rgb": np.full((2, 2, 3), palette[marker_index], dtype=np.uint8),
                    "quantized": guide.copy(),
                    "metrics": {
                        "visible_pixels": 4 if reference_palette is not None else 0,
                        "class_pixels": {marker_classes[0]: 4},
                        "oklab_error_mean": 0.0,
                        "oklab_error_p95": 0.0,
                        "oklab_error_max": 0.0,
                        "model_bypassed": True,
                    },
                }
            )
            timing["null_frames"] = int(timing["null_frames"]) + 1
            states[frame.index] = state
            continue

        started = time.perf_counter()
        xbr_frame, (scaled_width, scaled_height, xbr_bytes) = next(xbr_iterator)
        timing["xbr"] = float(timing["xbr"]) + time.perf_counter() - started
        if xbr_frame is not frame or (scaled_width, scaled_height) != (frame.width * 2, frame.height * 2):
            raise RuntimeError(f"{resref} frame ordering or xBR geometry differs")
        provenance = p8.xbr_provenance_indices(frame, 2) if p8.has_duplicate_used_rgba_indices(frame) else None
        guide_flat, _representatives = p8.map_output(frame, xbr_bytes, provenance)
        guide = guide_flat.reshape(scaled_height, scaled_width)
        xbr_rgba = (
            np.frombuffer(xbr_bytes, dtype=np.uint8).reshape(scaled_height, scaled_width, 4)
            if reference_palette is None
            else p8.reconstruct_rgba(guide, palette, frame.transparent)
        )
        rgb = prepare_inference_rgb(frame, palette)
        state.update({"guide": guide, "xbr_rgba": xbr_rgba if frame.index in qa_indices else None})
        if rgb is None:
            target = np.full((scaled_height, scaled_width, 3), palette[frame.transparent], dtype=np.uint8)
            quantized, metrics, elapsed = p9_quantize(state, target, classes=classes)
            timing["quantization"] = float(timing["quantization"]) + elapsed
            state.update({"target_rgb": target if frame.index in qa_indices else None, "quantized": quantized, "metrics": metrics})
        else:
            state["rgb"] = rgb
            buckets[canvas_for(rgb)].append(state)
        states[frame.index] = state
    try:
        next(xbr_iterator)
    except StopIteration:
        pass
    else:
        raise RuntimeError(f"{resref}: extra xBR output")

    def dispatch(items: list[dict[str, Any]], canvas: tuple[int, int], pool: ThreadPoolExecutor) -> list[Any]:
        started = time.perf_counter()
        outputs = infer_x4_box_x2_padded_batch(
            descriptor,
            [item["rgb"] for item in items],
            canvas_height=canvas[0],
            canvas_width=canvas[1],
            fp16=fp16,
        )
        timing["reboutcx"] = float(timing["reboutcx"]) + time.perf_counter() - started
        timing["model_frames"] = int(timing["model_frames"]) + len(items)
        futures = []
        for item, (x4, target) in zip(items, outputs, strict=True):
            futures.append((item, x4, target, pool.submit(p9_quantize, item, target, classes=classes)))
        return futures

    pending: list[Any] = []
    with ThreadPoolExecutor(max_workers=P9_CPU_WORKERS) as pool:
        for canvas, all_items in buckets.items():
            for start in range(0, len(all_items), P9_BATCH_SIZE):
                pending.extend(dispatch(all_items[start : start + P9_BATCH_SIZE], canvas, pool))
        for state, x4, target, future in pending:
            quantized, metrics, elapsed = future.result()
            timing["quantization"] = float(timing["quantization"]) + elapsed
            state.update(
                {
                    "quantized": quantized,
                    "metrics": metrics,
                    "target_rgb": target if state["frame"].index in qa_indices else None,
                    "x4": x4 if state["frame"].index in qa_indices else None,
                }
            )

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
            p8.write_frame_record(stream, frame, quantized)
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
                    raise RuntimeError(f"{resref} frame {frame.index}: missing P9 QA pixels")
                qa_records[frame.index] = {
                    "frame": frame,
                    "native_rgba": native_rgba,
                    "xbr_rgba": np.asarray(state["xbr_rgba"], dtype=np.uint8).copy(),
                    "raw_masked_rgba": np.dstack((target, np.where(state["guide"] == frame.transparent, 0, 255).astype(np.uint8))),
                    "quantized_rgba": p8.reconstruct_rgba(quantized, palette, frame.transparent),
                }
        p8.write_cycles(stream, cycles)
    return frame_manifest, qa_records, timing


def patch_manifest(job_path: Path) -> dict[str, Any]:
    job = p8.read_json(job_path)
    manifest_path = p8.resolve_path_reference(job["paths"]["run_dir"], root=p8.PROJECT_ROOT) / "manifest.json"
    manifest = p8.read_json(manifest_path)
    manifest["code"]["reboutcx_full"] = {"path": p8.relative(SCRIPT_PATH), "sha256": p8.sha256_file(SCRIPT_PATH)}
    helper = SCRIPT_PATH.with_name("reboutcx_batch_p9.py")
    manifest["code"]["reboutcx_batch"] = {"path": p8.relative(helper), "sha256": p8.sha256_file(helper)}
    manifest["method"]["batch"] = {
        "id": "p9-cuda-padded-microbatch-v1",
        "max_frames": P9_BATCH_SIZE,
        "canvas_quantum": P9_BUCKET_QUANTUM,
        "cpu_quantization_workers": P9_CPU_WORKERS,
        "padding": "zero-top-left-before-model; crop-to-source-after-model",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def execute(job_path: Path) -> dict[str, Any]:
    p8.render_resource = render_resource_p9
    p8.execute(job_path)
    return patch_manifest(job_path)


def configured_python(job: dict[str, Any]) -> Path:
    return p8.resolve_path_reference(job["paths"]["chainner_python"], required=True, root=p8.PROJECT_ROOT).resolve()


def derive_job(source_path: Path, destination: Path | None) -> Path:
    """Clone a prepared P8 component contract into an independent P9 run."""
    source = source_path.resolve()
    job = p8.read_json(source)
    if job.get("schema") != p8.JOB_SCHEMA or job.get("installable") is not False:
        raise RuntimeError("P9 source must be a non-installable prepared full job")
    suffix_from = "reboutcx-p8-full-v1"
    suffix_to = "reboutcx-p9-batch86-v1"
    if suffix_from not in str(job.get("job_id", "")) or suffix_from not in str(job["paths"].get("run_dir", "")):
        raise RuntimeError("P9 source job does not have the expected P8 identity")
    derived = copy.deepcopy(job)
    derived["job_id"] = str(derived["job_id"]).replace(suffix_from, suffix_to)
    derived["paths"]["run_dir"] = str(derived["paths"]["run_dir"]).replace(suffix_from, suffix_to)
    derived["reboutcx_batch"] = {
        "id": "p9-cuda-padded-microbatch-v1",
        "max_frames": 86,
        "canvas_quantum": 64,
        "cpu_quantization_workers": 3,
    }
    output = destination.resolve() if destination is not None else source.with_name(f"{suffix_to}.json")
    if output.exists():
        if p8.read_json(output) != derived:
            raise RuntimeError(f"existing P9 job differs: {p8.relative(output)}")
        return output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(derived, indent=2) + "\n", encoding="utf-8")
    return output


def main() -> int:
    global P9_BATCH_SIZE, P9_CPU_WORKERS, P9_BUCKET_QUANTUM
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("run", "_execute", "verify"):
        command = commands.add_parser(name)
        command.add_argument("job", type=Path)
        if name != "verify":
            command.add_argument("--batch-size", type=int, default=86)
            command.add_argument("--cpu-workers", type=int, default=3)
            command.add_argument("--bucket-quantum", type=int, default=64)
    derive = commands.add_parser("derive-job")
    derive.add_argument("source", type=Path)
    derive.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.command == "derive-job":
        print(p8.relative(derive_job(args.source, args.output)))
        return 0
    job_path = args.job.resolve()
    if args.command == "run":
        job = p8.read_json(job_path)
        python = configured_python(job)
        command = [str(python), str(SCRIPT_PATH), "_execute", str(job_path), "--batch-size", str(args.batch_size), "--cpu-workers", str(args.cpu_workers), "--bucket-quantum", str(args.bucket_quantum)]
        return subprocess.run(command, check=False).returncode
    if args.command == "verify":
        p8.verify(job_path)
        return 0
    if args.batch_size < 1 or args.cpu_workers < 1 or args.bucket_quantum < 1:
        raise RuntimeError("P9 batch, CPU worker and quantum values must be positive")
    P9_BATCH_SIZE = args.batch_size
    P9_CPU_WORKERS = args.cpu_workers
    P9_BUCKET_QUANTUM = args.bucket_quantum
    execute(job_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
