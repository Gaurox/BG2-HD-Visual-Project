"""Optional FP64 palette ranking; near ties use original CPU 256-row blocks.

No neural inference changes. Existing CPU cache keys/bytes remain acquired.
Torch is imported only for an actual missing encoded key, never a cache hit.
"""
import os
import threading
import numpy as np
from palette_frac_encode import checked_u8
from reboutcx_quantize import srgb_u8_to_oklab

MODE = 'gpu-grouped-guarded-v1'
_lock = threading.RLock()
_encoder = None


class Encoder:
    def __init__(self):
        import torch
        self.torch = torch
        self.cache = {}
        self.stats = dict(pixels=0, ambiguous_pixels=0, cpu_blocks=0,
                          total_blocks=0, collapsed_candidates=0)
        torch.backends.cuda.matmul.allow_tf32 = False

    def encode(self, profile, guide, targets):
        g = checked_u8(guide, 'guide'); t = np.asarray(targets)
        if t.shape != (6, *g.shape, 3) or not np.isfinite(t).all() or np.any((t < 0) | (t > 1)):
            raise ValueError('float targets differ')
        tf = np.ascontiguousarray(srgb_u8_to_oklab(t.astype(np.float64)*255)
            .reshape(6, -1, 3).transpose(1, 0, 2).reshape(-1, 18))
        i, code = g.copy(), np.zeros_like(g)
        torch = self.torch
        for cls in np.unique(profile.classes[g]):
            if cls < (3 if profile.kind == 0 else 4): continue
            locs = np.flatnonzero(profile.classes[g].reshape(-1) == cls)
            ci, cc, features, norm = profile.candidates(int(cls)); vectors = tf[locs]
            choice = np.empty(len(locs), np.int64); ambiguous = np.zeros(len(locs), bool)
            zero = np.all(vectors == 0, axis=1); choice[zero] = np.argmin(norm)
            active = np.flatnonzero(~zero)
            # Conservative roundoff guard for 18 bounded FP64 terms, subtraction
            # and CPU/GPU reduction order. Full original CPU rows resolve ties.
            bound = 256*np.finfo(np.float64).eps*(1+float(norm.max())+
                36*float(np.abs(features).max())*float(np.abs(vectors).max()))
            tolerance = max(1e-10, 2*bound)
            key = (profile.identity, int(cls))
            if key not in self.cache:
                _, mapping = np.unique(np.column_stack((features, norm)), axis=0, return_index=True)
                self.stats['collapsed_candidates'] += len(features)-len(mapping)
                self.cache[key] = (torch.from_numpy(np.ascontiguousarray(features[mapping])).cuda().T,
                                  torch.from_numpy(norm[mapping]).cuda(), mapping)
            ft, nt, mapping = self.cache[key]
            for start in range(0, len(active), 4096):
                off = active[start:start+4096]
                v = torch.from_numpy(np.ascontiguousarray(vectors[off])).cuda()
                d = nt[None]-2*(v@ft)
                values, indices = d.min(dim=1)
                choice[off] = mapping[indices.cpu().numpy()]
                d[torch.arange(len(off), device='cuda'), indices] = float('inf')
                gap = (d.min(dim=1).values-values).cpu().numpy()
                ambiguous[off] = (gap <= tolerance) | ~np.isfinite(gap)
                del v, d, values, indices
            self.stats['pixels'] += len(locs)
            self.stats['ambiguous_pixels'] += int(ambiguous.sum())
            for start in range(0, len(locs), 256):
                self.stats['total_blocks'] += 1
                if ambiguous[start:start+256].any():
                    off = locs[start:start+256]
                    choice[start:start+len(off)] = np.argmin(norm[None]-2*(tf[off]@features.T), axis=1)
                    self.stats['cpu_blocks'] += 1
            i.reshape(-1)[locs] = ci[choice]; code.reshape(-1)[locs] = cc[choice]
        dep = profile.dependencies(i, code); profile.validate(i, code, g, dep)
        return dict(guide=g.copy(), I=i, F=code, dep=dep)


def encode(profile, guide, targets):
    global _encoder
    mode = os.environ.get('Q3M_PALETTE_ENCODER', 'cpu')
    if mode == 'cpu': return profile.encode(guide, targets)
    if mode != MODE: raise ValueError('Unknown Q3M_PALETTE_ENCODER: '+mode)
    # Bound GPU allocations and cold candidate construction across I/O threads.
    with _lock:
        if _encoder is None: _encoder = Encoder()
        return _encoder.encode(profile, guide, targets)


def statistics():
    with _lock:
        return {} if _encoder is None else dict(_encoder.stats)
