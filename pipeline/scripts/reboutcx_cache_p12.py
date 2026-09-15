"""Ephemeral, bounded frame cache. Pixel identity excludes registry metadata."""
from __future__ import annotations
from collections import OrderedDict, Counter
from concurrent.futures import Future
from dataclasses import dataclass
import hashlib
import json
import struct
import sys
import threading
from types import MappingProxyType
import numpy as np

PIXEL_CONTRACT = {
    "id": "p12-frame-cache-fixed86-q32-v1", "batch_size": 86, "canvas_quantum": 32,
    "input": "uint8-float32-div255-fp16; zero-pad-bottom-right",
    "tail": "zero-filled-to-86; discard-fillers-before-CPU",
    "alpha": "xbr2x-mask-v1", "rgb_fill": "scipy-distance-transform-nearest-opaque",
    "downscale": "chainner_ext-box-float32-before-u8-rounding",
    "quantizer": "reboutcx_cpu_p10.quantize_classed_oklab",
    "deterministic_algorithms": True,
}


def context_key(job, classes, scalepix_sha256):
    # Item, layer, animation and centres label outputs; they do not transform pixels.
    value = {"pixel_contract": PIXEL_CONTRACT, "reboutcx": job["reboutcx"],
             "classes": classes, "marker": int(job["null_frame_marker"]),
             "scalepix_sha256": scalepix_sha256, "node": job["tools"].get("node", "node")}
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).digest()


def frame_key(frame, palette, context):
    digest = hashlib.sha256(context)
    digest.update(struct.pack("<IIB", frame.width, frame.height, frame.transparent))
    digest.update(np.ascontiguousarray(frame.indices))
    digest.update(np.ascontiguousarray(frame.palette))
    digest.update(frame.rgba)
    digest.update(b"native" if palette is None else b"reference" + np.ascontiguousarray(palette).tobytes())
    return digest.digest()


def freeze(value):
    if isinstance(value, np.ndarray):
        # Own the retained storage: never keep an entire batch alive through a view.
        if value.base is not None or not value.flags.c_contiguous:
            value = value.copy(order="C")
        value.setflags(write=False)
        return value
    if isinstance(value, dict):
        return MappingProxyType({k: freeze(v) for k, v in value.items()})
    if isinstance(value, (tuple, list)):
        return tuple(freeze(v) for v in value)
    return value


def retained_bytes(value):
    if isinstance(value, np.ndarray):
        return sys.getsizeof(value)  # Owned ndarray includes the data allocation.
    if isinstance(value, (dict, MappingProxyType)):
        return sys.getsizeof(dict(value)) + sum(retained_bytes(k) + retained_bytes(v) for k,v in value.items())
    if isinstance(value, (list, tuple)):
        return sys.getsizeof(value) + sum(retained_bytes(v) for v in value)
    return sys.getsizeof(value)


@dataclass
class Ticket:
    key: bytes
    future: Future
    owner: bool
    hit: str


class FrameCache:
    """Inflight tickets live in reserved active groups; only ready LRU entries persist.

    Never block on cache space. Owners finish their own work before awaiting followers.
    A queue may declare exact occurrence counts to retain repeated frames only and drop
    each result after its final scheduled use. Standalone execution uses bounded LRU.
    """
    def __init__(self, limit_bytes):
        if limit_bytes < 0:
            raise ValueError("cache size must be nonnegative")
        self.limit = limit_bytes
        self.lock = threading.RLock()
        self.inflight = {}
        self.ready = OrderedDict()
        self.remaining = None
        self.plan_used = 0
        self.used = self.peak = 0
        self.stats = Counter()

    def declare_counts(self, counts):
        with self.lock:
            if self.inflight or self.ready or self.stats:
                raise RuntimeError("cache plan must precede frame claims")
            # Bounded admission metadata (conservative 256 bytes per key/count).
            capacity = min(self.limit // 16, 32*1024*1024) // 256
            selected = sorted(((key,int(n)) for key,n in counts.items() if n>1), key=lambda p:(-p[1],p[0]))[:capacity]
            self.remaining = dict(selected)
            self.plan_used = 256*len(selected)
            self.used = self.plan_used
            self.peak = self.used
            self.stats["planned_repeated_keys"] = len(selected)

    def _drop_plan_key(self, key):
        if self.remaining is not None and key in self.remaining:
            del self.remaining[key]
            self.plan_used -= 256
            self.used -= 256
            # Release the table's backing capacity as it shrinks, not only its keys.
            if not self.remaining or len(self.remaining) & (len(self.remaining)-1) == 0:
                self.remaining = dict(self.remaining)

    def claim(self, key):
        with self.lock:
            if self.remaining is not None and key in self.remaining:
                self.remaining[key] -= 1
            self.stats["requests"] += 1
            if key in self.ready:
                future, size = self.ready.pop(key)
                if self.remaining is None or self.remaining.get(key, 0) > 0:
                    self.ready[key] = (future, size)
                else:
                    self.used -= size
                    self._drop_plan_key(key)
                self.stats["ready_hits"] += 1
                return Ticket(key, future, False, "ready")
            if key in self.inflight:
                self.stats["inflight_hits"] += 1
                return Ticket(key, self.inflight[key], False, "inflight")
            future = Future()
            self.inflight[key] = future
            self.stats["misses"] += 1
            return Ticket(key, future, True, "miss")

    def publish(self, ticket, payload):
        value = freeze(payload)
        # Future/Condition/waiter deque plus LRU and dictionary storage. This is
        # intentionally conservative; the retained payload is counted separately.
        size = retained_bytes(value) + 4096 + len(ticket.key)
        with self.lock:
            if not ticket.owner or self.inflight.get(ticket.key) is not ticket.future:
                raise RuntimeError("only the active cache owner may publish")
            del self.inflight[ticket.key]
            admit = self.remaining is None or self.remaining.get(ticket.key, 0) > 0
            if admit and size <= self.limit:
                while self.ready and self.used + size > self.limit:
                    _key, (_future, previous_size) = self.ready.popitem(last=False)
                    self.used -= previous_size
                    self.stats["evictions"] += 1
                if self.used + size <= self.limit:
                    self.ready[ticket.key] = (ticket.future, size)
                    self.used += size
                    self.peak = max(self.peak, self.used)
                else:
                    self.stats["not_retained"] += 1
            else:
                self.stats["not_retained"] += 1
                if self.remaining is not None and self.remaining.get(ticket.key, 0) <= 0:
                    self._drop_plan_key(ticket.key)
            ticket.future.set_result(value)

    def fail(self, ticket, error):
        with self.lock:
            if ticket.owner and self.inflight.get(ticket.key) is ticket.future:
                del self.inflight[ticket.key]
                self.stats["failed"] += 1
                ticket.future.set_exception(error)

    def snapshot(self):
        with self.lock:
            return {**dict(self.stats), "retained_bytes": self.used, "peak_retained_bytes": self.peak,
                    "limit_bytes": self.limit, "ready_entries": len(self.ready),
                    "inflight_entries": len(self.inflight),
                    "plan_reserved_bytes": self.plan_used,
                    "remaining_plan_keys": len(self.remaining or {})}

    def clear(self):
        with self.lock:
            for future in self.inflight.values():
                future.set_exception(RuntimeError("cache closed before owner completed"))
            self.inflight.clear()
            self.ready.clear()
            self.remaining = None
            self.plan_used = 0
            self.used = 0
