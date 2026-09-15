"""P11 deterministic cross-resource windows; immutable P10 CPU/GPU kernels."""
from __future__ import annotations
from collections import defaultdict, deque
import time
import numpy as np
import reboutcx_full as legacy
from reboutcx_runtime_p10 import Runtime, prepare_resource, postprocess_batch

CANVAS_QUANTUM = 32
GROUP_MAX_RESOURCES = 8
GROUP_NATIVE_PIXEL_CAP = 8_000_000


def process_group(runtime: Runtime, resources: list[dict], states: dict, *, fp16: bool,
                  classes: dict, required_qa: dict) -> dict:
    """Dispatch stable geometry buckets across resources; route by (resref, index)."""
    timing = defaultdict(float)
    buckets, bypass = defaultdict(list), []
    for resource in resources:
        name = str(resource["source"]["name"]).upper()
        for frame in resource["frames"]:
            state = states[name][frame.index]
            token = (name, frame.index)
            if frame.index in required_qa.get(name, set()):
                state["xbr_rgba"] = legacy.reconstruct_rgba(state["guide"], state["palette"], frame.transparent)
            if "quantized" in state:
                continue
            if state["rgb"] is None:
                bypass.append(token)
            else:
                h, w = state["rgb"].shape[:2]
                q = CANVAS_QUANTUM
                buckets[((h + q - 1)//q*q, (w + q - 1)//q*q)].append(token)

    pending = deque()

    def collect():
        tick = time.perf_counter()
        results, elapsed = pending.popleft().result()
        timing["post_wait_seconds"] += time.perf_counter() - tick
        for key, value in elapsed.items():
            timing[key] += value
        for (name, index), quantized, metrics, target in results:
            states[name][index].update(quantized=quantized, metrics=metrics, target_rgb=target)

    def submit(tokens, crops):
        requests = []
        for (name, index), crop in zip(tokens, crops, strict=True):
            state = states[name][index]
            frame = state["frame"]
            requests.append(((name, index), state["guide"], state["palette"], np.unique(frame.indices),
                             frame.transparent, crop, index in required_qa.get(name, set())))
        pending.append(runtime.post.submit(postprocess_batch, requests, classes))
        if len(pending) >= 2:
            collect()

    try:
        for start in range(0, len(bypass), 86):
            batch = bypass[start:start + 86]
            submit(batch, [None] * len(batch))
        for canvas, tokens in buckets.items():
            for start in range(0, len(tokens), 86):
                batch = tokens[start:start + 86]
                rgbs = [states[name][index]["rgb"] for name, index in batch]
                crops, elapsed = runtime.infer(rgbs, canvas, fp16).result()
                for key, value in elapsed.items():
                    timing[key] += value
                timing["reboutcx"] += elapsed["dispatch_wall_seconds"]
                timing["model_frames"] += len(batch)
                timing["batches"] += 1
                timing["full_batches"] += len(batch) == 86
                timing["cross_resource_batches"] += len({name for name, _ in batch}) > 1
                timing["padded_model_pixels"] += len(batch) * canvas[0] * canvas[1]
                timing["native_model_pixels"] += sum(rgb.shape[0] * rgb.shape[1] for rgb in rgbs)
                submit(batch, crops)
                del crops
        while pending:
            collect()
    finally:
        for future in pending:
            if not future.cancel():
                try:
                    future.result()
                except Exception:
                    pass
    timing["resource_groups"] += 1
    return dict(timing)


def plan_groups(resources: list[dict]) -> list[list[dict]]:
    """Stable source-order groups, independent of scheduling and available RAM.

    A resource larger than the pixel cap is processed alone, never split/reordered.
    """
    result, group, pixels = [], [], 0
    for resource in resources:
        size = sum(f.width * f.height for f in resource["frames"])
        if group and (len(group) >= GROUP_MAX_RESOURCES or pixels + size > GROUP_NATIVE_PIXEL_CAP):
            result.append(group)
            group, pixels = [], 0
        group.append(resource)
        pixels += size
    if group:
        result.append(group)
    return result


def group_key(resources: list[dict]) -> tuple[str, ...]:
    return tuple(str(r["source"]["name"]).upper() for r in resources)


def group_bytes(resources: list[dict]) -> int:
    frames = [f for r in resources for f in r["frames"]]
    native = sum(f.width * f.height for f in frames)
    q = CANVAS_QUANTUM
    canvas = max((((f.height + q - 1)//q*q) * ((f.width + q - 1)//q*q) for f in frames), default=q*q)
    # One shared crop window for the group, plus source/guide/RGB and IPC copies.
    return native * 48 + len(frames) * 4096 + min(86, len(frames)) * canvas * 192 * 3


class GroupWindow:
    """Atomic reservation avoids deadlocks when several components prepare groups."""
    def __init__(self, runtime: Runtime, *, scalepix, node, marker, palette, classes):
        self.runtime = runtime
        self.arguments = (scalepix, node, marker, palette, classes)
        self.pending = {}

    def submit(self, resources: list[dict], *, blocking=True) -> bool:
        key = group_key(resources)
        if key in self.pending:
            return True
        size = group_bytes(resources)
        if not self.runtime.memory.acquire(size, blocking=blocking):
            return False
        futures = {}
        self.pending[key] = (futures, size)
        try:
            for name, resource in zip(key, resources, strict=True):
                future = self.runtime.pre.submit(prepare_resource, resource, *self.arguments)
                futures[name] = (future, time.perf_counter())
        except BaseException:
            self.release(resources)
            raise
        return True

    def get(self, resources: list[dict]) -> tuple[dict, dict]:
        self.submit(resources)
        futures, _ = self.pending[group_key(resources)]
        all_states, timing = {}, defaultdict(float)
        for name, (future, submitted) in futures.items():
            states, elapsed = future.result()
            all_states[name] = states
            for label, value in elapsed.items():
                timing[label] += value
            timing["prepare_queue_ipc_and_wait_seconds"] += time.perf_counter() - submitted
        return all_states, dict(timing)

    def release(self, resources: list[dict]) -> None:
        self._release_key(group_key(resources))

    def _release_key(self, key) -> None:
        futures, size = self.pending.pop(key)
        first_error = None
        try:
            for future, _ in futures.values():
                try:
                    if not future.cancel():
                        future.result()
                except BaseException as error:
                    first_error = first_error or error
        finally:
            self.runtime.memory.release(size)
        if first_error is not None:
            raise first_error

    def close(self) -> None:
        first_error = None
        for key in list(self.pending):
            try:
                self._release_key(key)
            except BaseException as error:
                first_error = first_error or error
        if first_error is not None:
            raise first_error
