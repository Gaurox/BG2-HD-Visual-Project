"""Persistent GPU owner, separate CPU stages and bounded resource prefetch for P10."""
from __future__ import annotations

import multiprocessing
import os
import threading
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np

import reboutcx_full as legacy
from reboutcx_batch import prepare_inference_rgb
from reboutcx_batch_p10 import infer_float_crops
from reboutcx_cpu_p10 import map_output, quantize_classed_oklab


def prepare_resource(resource: dict, scalepix: Path, node: str, marker: int,
                     palette: np.ndarray | None, classes: dict) -> tuple[dict, dict]:
    started, cpu_started = time.perf_counter(), time.process_time()
    frames = resource["frames"]
    non_null = [f for f in frames if not legacy.is_null_frame(f, marker)]
    iterator = iter(legacy.xbr_batches(non_null, scalepix, node)) if non_null else iter(())
    states, timing = {}, defaultdict(float)
    for frame in frames:
        colors = frame.palette if palette is None else palette
        state = {"frame": frame, "palette": colors}
        if legacy.is_null_frame(frame, marker):
            names = [name for name, indices in classes.items() if marker in indices]
            if len(names) != 1:
                raise RuntimeError("null marker must belong to exactly one class")
            guide = np.full((2, 2), marker, dtype=np.uint8)
            state.update(guide=guide, quantized=guide.copy(), rgb=None,
                         target_rgb=np.full((2, 2, 3), colors[marker], dtype=np.uint8),
                         metrics={"visible_pixels": 4 if palette is not None else 0,
                                  "class_pixels": {names[0]: 4}, "oklab_error_mean": 0.0,
                                  "oklab_error_p95": 0.0, "oklab_error_max": 0.0,
                                  "model_bypassed": True})
            timing["null_frames"] += 1
        else:
            tick = time.perf_counter()
            returned, (width, height, rgba) = next(iterator)
            timing["xbr"] += time.perf_counter() - tick
            if returned is not frame or (width, height) != (frame.width * 2, frame.height * 2):
                raise RuntimeError("P10 xBR order/geometry differs")
            tick = time.perf_counter()
            provenance = (legacy.xbr_provenance_indices(frame, 2)
                          if legacy.has_duplicate_used_rgba_indices(frame) else None)
            guide, representatives = map_output(frame, rgba, provenance)
            state.update(guide=guide.reshape(height, width), representatives=representatives)
            timing["mapping_seconds"] += time.perf_counter() - tick
            tick = time.perf_counter()
            state["rgb"] = prepare_inference_rgb(frame, colors)
            timing["rgb_fill_seconds"] += time.perf_counter() - tick
        states[frame.index] = state
    if next(iterator, None) is not None:
        raise RuntimeError("P10 received extra xBR frames")
    timing["prepare_wall_seconds"] = time.perf_counter() - started
    timing["prepare_process_cpu_seconds"] = time.process_time() - cpu_started
    return states, dict(timing)


def postprocess_batch(items: list[tuple], classes: dict) -> tuple[list, dict]:
    from chainner_ext import ResizeFilter, resize

    started, cpu_started = time.perf_counter(), time.process_time()
    results, timing = [], defaultdict(float)
    for index, guide, palette, used, transparent, crop, keep_target in items:
        tick = time.perf_counter()
        if crop is None:
            target = np.full((*guide.shape, 3), palette[transparent], dtype=np.uint8)
        else:
            x2 = resize(crop, (guide.shape[1], guide.shape[0]), ResizeFilter.Box, False)
            target = np.rint(np.clip(x2, 0, 1) * 255.0).astype(np.uint8)
        timing["box_and_round_seconds"] += time.perf_counter() - tick
        tick = time.perf_counter()
        quantized, metrics = quantize_classed_oklab(
            target, guide, palette, used, classes, transparent_index=transparent)
        timing["quantization"] += time.perf_counter() - tick
        if crop is None:
            metrics["model_bypassed"] = True
        results.append((index, quantized, metrics, target if keep_target else None))
    timing["post_wall_seconds"] = time.perf_counter() - started
    timing["post_process_cpu_seconds"] = time.process_time() - cpu_started
    return results, dict(timing)


class ByteBudget:
    def __init__(self, limit: int):
        if limit < 1:
            raise ValueError("memory budget must be positive")
        self.limit, self.used, self.peak = limit, 0, 0
        self.condition = threading.Condition()

    def acquire(self, size: int, *, blocking: bool = True) -> bool:
        if size < 0 or size > self.limit:
            raise RuntimeError(f"resource estimate {size} exceeds memory budget {self.limit}")
        with self.condition:
            if not blocking and self.used + size > self.limit:
                return False
            self.condition.wait_for(lambda: self.used + size <= self.limit)
            self.used += size
            self.peak = max(self.peak, self.used)
            return True

    def release(self, size: int) -> None:
        with self.condition:
            self.used -= size
            if self.used < 0:
                raise RuntimeError("P10 memory reservation underflow")
            self.condition.notify_all()


def resource_bytes(resource: dict) -> int:
    frames = resource["frames"]
    native = sum(f.width * f.height for f in frames)
    canvas = max((((f.height + 63) // 64 * 64) * ((f.width + 63) // 64 * 64)
                  for f in frames), default=4096)
    # Source/guide/RGB, IPC copies and two float32 x4 micro-lots; model VRAM excluded.
    return native * 48 + len(frames) * 4096 + min(86, len(frames)) * canvas * 192 * 3


class ResourceWindow:
    """One active resource and at most one prefetched resource per component."""
    def __init__(self, runtime: "Runtime", *, scalepix: Path, node: str, marker: int,
                 palette: np.ndarray | None, classes: dict):
        self.runtime = runtime
        self.arguments = (scalepix, node, marker, palette, classes)
        self.pending: dict[str, tuple] = {}

    def submit(self, resource: dict, *, blocking: bool = True) -> bool:
        name = str(resource["source"]["name"]).upper()
        if name in self.pending:
            return True
        size = resource_bytes(resource)
        if not self.runtime.memory.acquire(size, blocking=blocking):
            return False
        try:
            future = self.runtime.pre.submit(prepare_resource, resource, *self.arguments)
        except BaseException:
            self.runtime.memory.release(size)
            raise
        self.pending[name] = (future, size, time.perf_counter())
        return True

    def get(self, resource: dict) -> tuple[dict, dict]:
        self.submit(resource)
        future, _size, submitted = self.pending[str(resource["source"]["name"]).upper()]
        states, timing = future.result()
        timing["prepare_queue_ipc_and_wait_seconds"] = time.perf_counter() - submitted
        return states, timing

    def release(self, name: str) -> None:
        future, size, _submitted = self.pending.pop(name)
        try:
            if not future.cancel():
                future.result()
        finally:
            self.runtime.memory.release(size)

    def close(self) -> None:
        # Release every reservation even when a preparation failed.
        first_error = None
        for name in list(self.pending):
            try:
                self.release(name)
            except BaseException as error:
                first_error = first_error or error
        if first_error is not None:
            raise first_error


class Runtime:
    def __init__(self, *, pre_workers: int = 2, post_workers: int = 3,
                 memory_mib: int = 2048, process_pools: bool = True):
        if not 1 <= pre_workers <= 16 or not 1 <= post_workers <= 16:
            raise ValueError("CPU worker counts must be between one and sixteen")
        self.memory = ByteBudget(memory_mib * 1024 * 1024)
        self.settings = {"pre_workers": pre_workers, "post_workers": post_workers,
                         "estimated_resource_memory_mib": memory_mib,
                         "cpu_executor": "process" if process_pools else "thread-test-only"}
        context = multiprocessing.get_context("spawn")
        factory = ProcessPoolExecutor if process_pools else ThreadPoolExecutor
        kwargs = {"mp_context": context} if process_pools else {}
        self.pre = factory(max_workers=pre_workers, **kwargs)
        self.post = factory(max_workers=post_workers, **kwargs)
        self.gpu = ThreadPoolExecutor(max_workers=1, thread_name_prefix="p10-cuda-owner")
        self.model_lock = threading.Lock()
        self.model_key = self.model_future = self.descriptor = None
        self.model_load_seconds = 0.0
        self.execution_reports = {}

    def _load(self, path: Path, device: str, fp16: bool) -> dict:
        tick = time.perf_counter()
        os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
        import torch
        torch.backends.cudnn.deterministic = True
        torch.use_deterministic_algorithms(True)
        self.descriptor, versions = legacy.load_model(path, device=device, fp16=fp16)
        self.model_load_seconds = time.perf_counter() - tick
        return versions

    def model_info(self, path: Path, *, device: str, fp16: bool) -> dict:
        key = (str(path.resolve()), device, fp16)
        with self.model_lock:
            if self.model_key is None:
                self.model_key = key
                self.model_future = self.gpu.submit(self._load, path, device, fp16)
            elif key != self.model_key:
                raise RuntimeError("one P10 session requires one model/device/precision contract")
        return self.model_future.result()

    def _infer(self, rgbs: list, canvas: tuple, fp16: bool, submitted: float) -> tuple:
        wait = time.perf_counter() - submitted
        crops, timing = infer_float_crops(self.descriptor, rgbs, canvas=canvas, fp16=fp16)
        timing["gpu_queue_wait_seconds"] = wait
        return crops, timing

    def infer(self, rgbs: list, canvas: tuple, fp16: bool):
        if self.model_future is None:
            raise RuntimeError("model_info must precede inference")
        return self.gpu.submit(self._infer, rgbs, canvas, fp16, time.perf_counter())

    def close(self) -> None:
        for pool in (self.pre, self.gpu, self.post):
            pool.shutdown(wait=True, cancel_futures=True)

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
