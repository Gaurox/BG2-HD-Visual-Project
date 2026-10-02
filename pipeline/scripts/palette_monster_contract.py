"""Frozen phase-1 fixed Monster profiles; CPU-only, no Character kernel edits."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np

from palette_frac_encode import checked_u8
from reboutcx_quantize import srgb_u8_to_oklab

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "docs/measurements/q3m-monster-contract-x2-20261002-v1/contract.json"
RULE_ID = 2
ENCODER_ID = "monster-fixed-exhaustive-oklab-f64-integer-k6-v1"


@lru_cache(maxsize=1)
def documents():
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    raw = (CONTRACT.parent / contract["profiles_file"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != contract["profiles_file_sha256"]:
        raise ValueError("frozen Monster profiles changed")
    return contract, {p["palette_profile_id"]: p for p in json.loads(raw)["profiles"]}


class Profile:
    def __init__(self, profile_id, rule_id=RULE_ID):
        contract, profiles = documents()
        if rule_id != RULE_ID or profile_id not in profiles:
            raise ValueError("unknown Monster profile/rule")
        self.profile_id, self.rule_id = int(profile_id), int(rule_id)
        self.document = profiles[profile_id]
        self.succ = np.frombuffer(bytes.fromhex(self.document["successor_u8_hex"]), np.uint8)
        self.fitting = np.stack([np.frombuffer(bytes.fromhex(p["rgba_hex"]), np.uint8).reshape(256, 4)
                                 for p in self.document["fits"]])
        self.sources = {r["resref"]: r for r in contract["resources"] if r["palette_profile_id"] == profile_id}
        self.animation_ids = {r["animation_id"] for r in self.sources.values()}
        self.fitting.setflags(write=False)
        assert self.succ[:3].tolist() == [0, 1, 2] and np.all(self.succ[3:] >= 3)

    def accepts(self, owner, animation_id):
        return owner == 3 and f"0x{int(animation_id, 16):04X}" in self.animation_ids

    def check_resource(self, resref, source_sha256):
        expected = self.sources.get(resref)
        if expected is None or expected["canonical_sha256_registered"].lower() != source_sha256.lower():
            raise ValueError("Monster resource/source identity differs from frozen profile")

    def validate_planes(self, indices, fractions):
        i, f = checked_u8(indices, "I"), checked_u8(fractions, "F")
        if i.ndim != 2 or not i.size or f.shape != i.shape or np.any(f > 7) or np.any((i < 3) & (f != 0)):
            raise ValueError("invalid Monster I/F or fractional special")
        return i, f

    def dependency_mask(self, indices, fractions):
        i, f = self.validate_planes(indices, fractions)
        bits = np.zeros(256, np.uint8)
        bits[np.unique(i)] = 1
        bits[np.unique(self.succ[i[f > 0]])] = 1
        return np.packbits(bits, bitorder="little")

    def check_contract(self, guide, indices, fractions, dep_mask=None):
        i, f = self.validate_planes(indices, fractions)
        g = checked_u8(guide, "guide")
        if g.shape != i.shape:
            raise ValueError("Monster guide shape differs")
        gc, ic = np.minimum(g, 3), np.minimum(i, 3)
        if np.any(gc != ic) or np.any((g < 3) & ((g != i) | (f != 0))):
            raise ValueError("Monster semantic leak or changed special")
        if dep_mask is not None and not np.array_equal(dep_mask, self.dependency_mask(i, f)):
            raise ValueError("Monster dependency mask is not exact")

    def decode(self, indices, fractions, palette):
        i, f = self.validate_planes(indices, fractions)
        p = checked_u8(palette, "palette")
        if p.shape not in ((256, 3), (256, 4)):
            raise ValueError("Monster palette shape differs")
        if p.shape[1] == 4 and np.any((f > 0) & (p[i, 3] != p[self.succ[i], 3])):
            raise ValueError("Monster positive material pair has unequal live alpha")
        a, b = p[i, :3].astype(np.uint16), p[self.succ[i], :3].astype(np.uint16)
        fraction = f[..., None].astype(np.uint16)
        rgb = ((a * (8 - fraction) + b * fraction + 4) >> 3).astype(np.uint8)
        if p.shape[1] == 3:
            return rgb
        return np.dstack((rgb, np.where(i == 0, 0, p[i, 3]).astype(np.uint8)))

    def encode(self, guide, targets, *, chunk_pixels=128):
        g = checked_u8(guide, "guide")
        t = np.asarray(targets, dtype=np.float64)
        if (g.ndim != 2 or not g.size or t.shape != (6, *g.shape, 3) or chunk_pixels < 1
                or not np.isfinite(t).all() or np.any(t < 0) or np.any(t > 1)):
            raise ValueError("invalid Monster K6 inputs")
        i, f = g.copy(), np.zeros_like(g)
        ci, cf, labs = self.candidates()
        target_lab = srgb_u8_to_oklab(t * 255).reshape(6, -1, 3)
        positions = np.flatnonzero(g.reshape(-1) >= 3)
        for start in range(0, len(positions), chunk_pixels):
            loc = positions[start:start + chunk_pixels]
            cost = np.zeros((len(loc), len(ci)), dtype=np.float64)
            for k in range(6):
                delta = target_lab[k, loc, None, :] - labs[k, None, :, :]
                cost += np.einsum("nci,nci->nc", delta, delta, optimize=True)
            choice = np.argmin(cost, axis=1)  # I ascending, then F; no projected distance.
            i.reshape(-1)[loc], f.reshape(-1)[loc] = ci[choice], cf[choice]
        dep = self.dependency_mask(i, f)
        self.check_contract(g, i, f, dep)
        return dict(guide=g.copy(), I=i, F=f, dep=dep)

    @lru_cache(maxsize=6)
    def candidates(self):
        ci = np.repeat(np.arange(3, 256, dtype=np.uint8), 8)
        cf = np.tile(np.arange(8, dtype=np.uint8), 253)
        labs = np.stack([srgb_u8_to_oklab(self.decode(ci[None], cf[None], p)[0, :, :3]) for p in self.fitting])
        for a in (ci, cf, labs): a.setflags(write=False)
        return ci, cf, labs


@lru_cache(maxsize=6)
def get_profile(profile_id, rule_id=RULE_ID):
    return Profile(profile_id, rule_id)
