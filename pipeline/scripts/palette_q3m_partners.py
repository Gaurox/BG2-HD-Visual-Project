"""Q3m V7: four class-preserving blend partners, K6 and live native palettes."""
from __future__ import annotations

import hashlib
import struct
import numpy as np
from palette_frac_encode import CLASS_TABLE, checked_u8, successors
from reboutcx_quantize import srgb_u8_to_oklab

RULE = 3
FIXED_PROFILE, RANGE_PROFILE = 8, 9
PROFILE_BYTES = 2052


class Profile:
    def __init__(self, kind, source_bgra, fitting, table=None):
        self.kind = int(kind)
        if self.kind not in (0, 1): raise ValueError("native palette kind must be 0/1")
        self.id = FIXED_PROFILE if self.kind == 0 else RANGE_PROFILE
        self.source = checked_u8(source_bgra, "native BGRA").reshape(256, 4).copy()
        self.fitting = checked_u8(fitting, "K6 RGB")
        if self.fitting.shape != (6, 256, 3): raise ValueError("six RGB palettes required")
        self.classes = np.minimum(np.arange(256), 3).astype(np.uint8) if self.kind == 0 else CLASS_TABLE
        self.table = self.build_table() if table is None else checked_u8(table, "partners").reshape(256, 4).copy()
        self.validate_table()
        self.candidate_cache = {}
        # Source BGRA is per-resource runtime metadata; source_work already hashes
        # every used native RGB entry. Unused BGRA/alpha must not duplicate fits.
        self.identity = hashlib.sha256(struct.pack('<I', self.kind) + self.table.tobytes() + self.fitting.tobytes()).hexdigest()

    def build_table(self):
        labs = srgb_u8_to_oklab(self.fitting)
        table = np.repeat(np.arange(256, dtype=np.uint8)[:, None], 4, axis=1)
        for i in range(3 if self.kind == 0 else 4, 256):
            same = self.classes == self.classes[i]
            distinct = ~np.all(self.fitting == self.fitting[:, i, None, :], axis=(0, 2))
            distance = np.einsum('kic,kic->i', labs - labs[:, i, None], labs - labs[:, i, None]) / 6
            distance[~(same & distinct)] = np.inf
            ranked = [int(j) for j in np.argsort(distance, kind='stable') if np.isfinite(distance[j])]
            # Partner zero preserves V6's ramp successor or nearest fixed RGB partner.
            first = int(successors()[i]) if self.kind == 1 else (ranked[0] if ranked else i)
            choices = [first] + [j for j in ranked if j != first]
            table[i] = (choices[:4] + [i]*4)[:4]
        return table

    def validate_table(self):
        if np.any(self.classes[:, None] != self.classes[self.table]): raise ValueError("partner crosses semantic class")
        limit = 3 if self.kind == 0 else 4
        if np.any(self.table[:limit] != np.arange(limit)[:, None]): raise ValueError("special partner differs")

    def metadata(self):
        return struct.pack('<I', self.kind) + self.source.tobytes() + self.table.tobytes()

    def validate(self, i, code, guide=None, dep=None):
        i, code = checked_u8(i, "I"), checked_u8(code, "partner/fraction")
        if i.ndim != 2 or not i.size or i.shape != code.shape or np.any(code > 31): raise ValueError("invalid V7 planes")
        f, b = code & 7, code >> 3
        if np.any((f == 0) & (b != 0)) or np.any((f > 0) & (self.table[i, b] == i)): raise ValueError("noncanonical or self blend")
        if guide is not None:
            g = checked_u8(guide, 'guide')
            if g.shape != i.shape or np.any(self.classes[g] != self.classes[i]): raise ValueError("semantic leak")
            special = self.classes[g] < (3 if self.kind == 0 else 4)
            if np.any(special & ((g != i) | (code != 0))): raise ValueError("special changed")
        if dep is not None and not np.array_equal(dep, self.dependencies(i, code)): raise ValueError("inexact V7 dependencies")
        return i, code

    def dependencies(self, i, code):
        i, code = self.validate(i, code)
        bits = np.zeros(256, np.uint8); bits[np.unique(i)] = 1
        blend = (code & 7) > 0
        bits[np.unique(self.table[i[blend], code[blend] >> 3])] = 1
        return np.packbits(bits, bitorder='little')

    def decode(self, i, code, palette):
        i, code = self.validate(i, code); p = checked_u8(palette, 'palette')
        j = self.table[i, code >> 3]; f = (code & 7)[..., None].astype(np.uint16)
        if p.shape not in ((256, 3), (256, 4)): raise ValueError('palette shape')
        rgb = ((p[i, :3].astype(np.uint16)*(8-f) + p[j, :3].astype(np.uint16)*f + 4) >> 3).astype(np.uint8)
        if p.shape[1] == 3: return rgb
        if np.any(((code & 7) > 0) & (p[i, 3] != p[j, 3])): raise ValueError('partner alpha differs')
        alpha = p[i, 3].copy()
        if self.kind == 0: alpha[i == 0] = 0
        return np.dstack((rgb, alpha))

    def candidates(self, cls):
        if cls not in self.candidate_cache:
            # Preserve old I/F tie order, then introduce partners 1..3.
            values = [int(i) for i in np.flatnonzero(self.classes == cls)]
            pairs = [(i, (b << 3) | f) for b in range(4) for i in values
                     for f in (range(8) if b == 0 else range(1, 8))
                     if (f == 0 or self.table[i, b] != i)]
            ci = np.array([i for i, _ in pairs], np.uint8); cc = np.array([c for _, c in pairs], np.uint8)
            labs = np.stack([srgb_u8_to_oklab(self.decode(ci[None], cc[None], p)[0]) for p in self.fitting])
            features = np.ascontiguousarray(labs.transpose(1, 0, 2).reshape(len(ci), 18))
            norm = np.einsum('nc,nc->n', features, features)
            self.candidate_cache[cls] = ci, cc, features, norm
        return self.candidate_cache[cls]

    def encode(self, guide, targets):
        g = checked_u8(guide, 'guide'); t = np.asarray(targets)
        if t.shape != (6, *g.shape, 3) or not np.isfinite(t).all() or np.any((t < 0) | (t > 1)): raise ValueError('float targets differ')
        tf = np.ascontiguousarray(srgb_u8_to_oklab(t.astype(np.float64)*255).reshape(6, -1, 3).transpose(1, 0, 2).reshape(-1, 18))
        i, code = g.copy(), np.zeros_like(g)
        for cls in np.unique(self.classes[g]):
            if cls < (3 if self.kind == 0 else 4): continue
            locs = np.flatnonzero(self.classes[g].reshape(-1) == cls)
            ci, cc, features, norm = self.candidates(int(cls))
            for start in range(0, len(locs), 256):
                loc = locs[start:start+256]; choice = np.argmin(norm[None] - 2*(tf[loc] @ features.T), axis=1)
                i.reshape(-1)[loc] = ci[choice]; code.reshape(-1)[loc] = cc[choice]
        dep = self.dependencies(i, code); self.validate(i, code, g, dep)
        return dict(guide=g.copy(), I=i, F=code, dep=dep)
