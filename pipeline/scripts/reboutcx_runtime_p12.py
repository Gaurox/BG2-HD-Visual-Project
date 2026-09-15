"""P12 shared pure-frame cache, current-group reservations and fixed-size CUDA."""
from __future__ import annotations
from collections import defaultdict, deque
import time
import numpy as np
import reboutcx_full as legacy
from reboutcx_runtime_p10 import Runtime as PreviousRuntime, prepare_resource, postprocess_batch
from reboutcx_runtime_p11 import plan_groups, group_key, group_bytes as previous_group_bytes
from reboutcx_runtime_p11 import CANVAS_QUANTUM, GROUP_MAX_RESOURCES, GROUP_NATIVE_PIXEL_CAP
from reboutcx_cache_p12 import FrameCache, frame_key
from reboutcx_batch_p12 import infer_float_crops


class Runtime(PreviousRuntime):
    def __init__(self, *, cache_mib=1024, memory_mib=4096, **kwargs):
        cache = FrameCache(cache_mib * 1024 * 1024)
        super().__init__(memory_mib=memory_mib, **kwargs)
        self.cache = cache
        self.settings.update(cache_mib=cache_mib, prefetch_groups=0, fixed_gpu_batch=86)

    def _infer(self, rgbs, canvas, fp16, submitted):
        waited = time.perf_counter()-submitted
        crops, timing = infer_float_crops(self.descriptor, rgbs, canvas=canvas, fp16=fp16)
        timing["gpu_queue_wait_seconds"] = waited
        return crops, timing

    def close(self):
        try:
            super().close()
        finally:
            self.cache.clear()


def group_bytes(resources):
    q = CANVAS_QUANTUM
    canvas = max((((f.height+q-1)//q*q)*((f.width+q-1)//q*q)
                  for r in resources for f in r["frames"]), default=q*q)
    # P11 accounts real output crops; P12 also packs all 86 GPU input slots.
    return previous_group_bytes(resources) + 86 * canvas * 3 * 4


class GroupWindow:
    """Claim only a current, already-reserved group; never claim deferred prefetch.

    This guarantees every cache owner has RAM and a runnable preparation. Consumers
    perform all work they own before waiting on another group, breaking wait cycles.
    """
    def __init__(self, runtime, *, scalepix, node, marker, palette, classes, cache_context):
        self.runtime = runtime
        self.arguments = (scalepix, node, marker, palette, classes)
        self.context = cache_context
        self.marker, self.palette = marker, palette
        self.pending = {}

    def get(self, resources):
        key = group_key(resources)
        if key in self.pending:
            raise RuntimeError("P12 group already active")
        size = group_bytes(resources)
        self.runtime.memory.acquire(size)
        record = {"size":size,"futures":[],"tickets":[]}
        self.pending[key] = record
        all_states, timing = {}, defaultdict(float)
        tick = time.perf_counter()
        for resource in resources:
            name = str(resource["source"]["name"]).upper()
            states, selected = {}, []
            all_states[name] = states
            for frame in resource["frames"]:
                state = {"frame":frame, "palette":frame.palette if self.palette is None else self.palette}
                states[frame.index] = state
                if legacy.is_null_frame(frame, self.marker):
                    selected.append(frame)
                    continue
                ticket = self.runtime.cache.claim(frame_key(frame, self.palette, self.context))
                record["tickets"].append(ticket)
                state["cache_ticket"] = ticket
                timing["cache_requests"] += 1
                timing["cache_" + ticket.hit] += 1
                if ticket.owner:
                    selected.append(frame)
            if selected:
                reduced = {**resource, "frames": selected}
                future = self.runtime.pre.submit(prepare_resource, reduced, *self.arguments)
                record["futures"].append((name, future, time.perf_counter()))
        timing["cache_key_and_claim_seconds"] += time.perf_counter()-tick
        for name, future, submitted in record["futures"]:
            prepared, elapsed = future.result()
            for index, state in prepared.items():
                original = all_states[name][index]["frame"]
                all_states[name][index].update(state)
                all_states[name][index]["frame"] = original
            for label, value in elapsed.items():
                timing[label] += value
            timing["prepare_queue_ipc_and_wait_seconds"] += time.perf_counter()-submitted
        return all_states, dict(timing)

    def release(self, resources):
        self._release_key(group_key(resources))

    def _release_key(self, key):
        record = self.pending.pop(key)
        first_error = None
        for ticket in record["tickets"]:
            self.runtime.cache.fail(ticket, RuntimeError("P12 group closed before its cache owner completed"))
        try:
            for _name, future, _submitted in record["futures"]:
                try:
                    if not future.cancel():
                        future.result()
                except BaseException as error:
                    first_error = first_error or error
        finally:
            self.runtime.memory.release(record["size"])
        if first_error is not None:
            raise first_error

    def close(self):
        first_error = None
        for key in list(self.pending):
            try:
                self._release_key(key)
            except BaseException as error:
                first_error = first_error or error
        if first_error is not None:
            raise first_error


def process_group(runtime, resources, states, *, fp16, classes, required_qa):
    timing = defaultdict(float)
    buckets, bypass, pending = defaultdict(list), [], deque()

    def publish(state):
        ticket = state.get("cache_ticket")
        if ticket is not None and ticket.owner:
            payload = {k:state[k] for k in ("guide","quantized","metrics","target_rgb")}
            if "representatives" in state:
                payload["representatives"] = state["representatives"]
            runtime.cache.publish(ticket, payload)

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
                h,w = state["rgb"].shape[:2]
                q = CANVAS_QUANTUM
                buckets[((h+q-1)//q*q,(w+q-1)//q*q)].append((name,frame.index))

    def collect():
        tick = time.perf_counter()
        results, elapsed = pending.popleft().result()
        timing["post_wait_seconds"] += time.perf_counter()-tick
        for key,value in elapsed.items():
            timing[key] += value
        for (name,index), quantized, metrics, target in results:
            state = states[name][index]
            state.update(quantized=quantized, metrics=metrics, target_rgb=target)
            publish(state)

    def submit(tokens, crops):
        requests = []
        for (name,index),crop in zip(tokens,crops,strict=True):
            state = states[name][index]
            frame = state["frame"]
            # A follower may need comparison pixels even when the owner does not.
            requests.append(((name,index),state["guide"],state["palette"],np.unique(frame.indices),
                             frame.transparent,crop,True))
        pending.append(runtime.post.submit(postprocess_batch, requests, classes))
        if len(pending) >= 2:
            collect()

    try:
        for start in range(0,len(bypass),86):
            batch = bypass[start:start+86]
            submit(batch,[None]*len(batch))
        for canvas,tokens in buckets.items():
            for start in range(0,len(tokens),86):
                batch = tokens[start:start+86]
                rgbs = [states[name][index]["rgb"] for name,index in batch]
                crops,elapsed = runtime.infer(rgbs,canvas,fp16).result()
                for key,value in elapsed.items():
                    timing[key] += value
                timing["reboutcx"] += elapsed["dispatch_wall_seconds"]
                timing["model_frames"] += len(batch)
                timing["batches"] += 1
                timing["full_batches"] += len(batch)==86
                timing["cross_resource_batches"] += len({name for name,_ in batch}) > 1
                timing["padded_model_pixels"] += len(batch)*canvas[0]*canvas[1]
                timing["gpu_slot_pixels"] += 86*canvas[0]*canvas[1]
                timing["native_model_pixels"] += sum(rgb.shape[0]*rgb.shape[1] for rgb in rgbs)
                submit(batch,crops)
                del crops
        while pending:
            collect()
        # All work owned by this group is published before any follower waits.
        tick = time.perf_counter()
        for resource in resources:
            name = str(resource["source"]["name"]).upper()
            for frame in resource["frames"]:
                state = states[name][frame.index]
                ticket = state.get("cache_ticket")
                if ticket is not None:
                    state.update(ticket.future.result())
                    state["cache_reused"] = not ticket.owner
                if frame.index in required_qa.get(name,set()):
                    state["xbr_rgba"] = legacy.reconstruct_rgba(state["guide"],state["palette"],frame.transparent)
                timing["logical_model_frames"] += not state["metrics"].get("model_bypassed",False)
                state.pop("rgb",None)
        timing["cache_wait_and_hydrate_seconds"] += time.perf_counter()-tick
    finally:
        for future in pending:
            if not future.cancel():
                try:
                    future.result()
                except Exception:
                    pass
    timing["resource_groups"] += 1
    return dict(timing)
