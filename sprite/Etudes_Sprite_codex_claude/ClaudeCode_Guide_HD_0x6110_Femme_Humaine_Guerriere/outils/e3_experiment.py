"""E3 — palettisation HD 0x6110 : xBR x2/x4 vs ReboutCX x2/x4, 6 encodages, 5 palettes.

Offline only. Reads sealed sources; writes only under OUT.
Run with config://chainner_python.
"""
from __future__ import annotations

import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

SCRIPTS = Path(r"G:/AI/BG2_Upscale/pipeline/scripts")
sys.path.insert(0, str(SCRIPTS))

from run_creature_sprite_x2 import (  # noqa: E402
    direct_upscale_contract, has_duplicate_used_rgba_indices, load_source_frames,
    map_output, run_xbr, xbr_provenance_indices)
from reboutcx_quantize import (  # noqa: E402
    character_chmb1_classes, character_chmb1_palette_rgb, quantize_classed_oklab,
    srgb_u8_to_oklab)
from reboutcx_batch import load_model, prepare_inference_rgb  # noqa: E402
from workspace_paths import get_path  # noqa: E402

OUT = Path(sys.argv[1])
OUT.mkdir(parents=True, exist_ok=True)
FAMILY = Path(r"G:/AI/BG2_Upscale/sprite/families/playable-characters/6110-human-female-fighter")
LAYERS = [("body", "chff4", {"idle_s": "CHFF4G12", "walk_s": "CHFF4G11"}), ("helmet", "helm01-wqnj6", "WQNJ6G1"),
          ("shield", "ishld03-wqnd3", "WQND3G1"), ("weapon", "bdsw1h06-wqns1", "WQNS1G1")]
CYCLES = {"idle_s": (18, list(range(12))), "walk_s": (0, list(range(10)))}
RANGES = np.load(Path(sys.argv[2]))  # 256x12x3 RANGES12
PALETTES = {
    "REF": [30, 47, 57, 12, 39, 21, 3],
    "B": [21, 57, 47, 8, 66, 30, 0],
    "C": [19, 63, 66, 15, 39, 26, 4],
    "D_heldout": [67, 68, 47, 84, 25, 57, 2],
    "E_armorblue_heldout": [30, 47, 57, 12, 39, 68, 3],
}
TRAIN = ["REF", "B", "C"]
PAL = {k: character_chmb1_palette_rgb(RANGES[v]) for k, v in PALETTES.items()}
PAL_LAB = {k: srgb_u8_to_oklab(v) for k, v in PAL.items()}
CLASSES = character_chmb1_classes()
CLASS_NAMES = list(CLASSES)
CLS_OF = np.full(256, -1, np.int16)
for ci, n in enumerate(CLASS_NAMES):
    for v in CLASSES[n]:
        CLS_OF[v] = ci
SPECIAL = {"transparent", "shadow", "reserved_2", "reserved_3"}
BAYER4 = (np.array([[0, 8, 2, 10], [12, 4, 14, 6], [3, 11, 1, 9], [15, 7, 13, 5]]) + 0.5) / 16.0
FRAC_BITS = 4


def log(*a):
    print(time.strftime("%H:%M:%S"), *a, flush=True)


# ---------------------------------------------------------------- sources
def load_layer(comp, resref):
    frames, resources, _ = load_source_frames(FAMILY / comp / "source" / "manifest.json")
    res = next(r for r in resources if r["source"]["name"].upper() == resref)
    return res


def selected(comp, resref):
    out = []
    for cname, (ci, positions) in CYCLES.items():
        rr = resref[cname] if isinstance(resref, dict) else resref
        res = load_layer(comp, rr)
        idx = res["cycles"][ci]["frame_indices"]
        for p in positions:
            out.append((cname, p, res["frames"][idx[p]]))
    return out


def xbr_guides(frames, scale):
    scalepix = get_path("mmpx_scalepix")
    outs = run_xbr(frames, Path(scalepix), "node", direct_upscale_contract(scale))
    guides = []
    for fr, (w, h, rgba) in zip(frames, outs):
        prov = xbr_provenance_indices(fr, scale) if has_duplicate_used_rgba_indices(fr) else None
        g, _ = map_output(fr, rgba, prov)
        guides.append(g.reshape(h, w))
    return guides


# ---------------------------------------------------------------- model
def infer(desc, rgb_u8):
    import torch
    from chainner_ext import ResizeFilter, resize
    src = np.asarray(rgb_u8, np.float32) / 255.0
    t = torch.from_numpy(src.transpose(2, 0, 1)).unsqueeze(0).cuda().half()
    with torch.inference_mode():
        o = desc(t).float().clamp(0, 1).cpu().numpy()[0]
    x4 = np.ascontiguousarray(o.transpose(1, 2, 0), np.float32)
    h, w = src.shape[:2]
    x2 = resize(x4, (w * 2, h * 2), ResizeFilter.Box, False)
    return (np.rint(x4 * 255).astype(np.uint8), np.rint(np.clip(x2, 0, 1) * 255).astype(np.uint8))


# ---------------------------------------------------------------- polyline projection
def project(q, pts):
    """q (N,D) onto polyline pts (K,D). Returns t in [0,K-1], dist^2."""
    if len(pts) == 1:
        return np.zeros(len(q)), ((q - pts[0]) ** 2).sum(1)
    a = pts[:-1]
    d = pts[1:] - a
    dd = (d ** 2).sum(1)
    dd = np.where(dd < 1e-12, 1e-12, dd)
    best_t = np.zeros(len(q))
    best_e = np.full(len(q), np.inf)
    for k in range(len(a)):
        u = np.clip(((q - a[k]) @ d[k]) / dd[k], 0, 1)
        e = ((q - (a[k] + u[:, None] * d[k])) ** 2).sum(1)
        better = e < best_e
        best_e[better] = e[better]
        best_t[better] = k + u[better]
    return best_t, best_e


def quant_t(t):
    q = np.round(t * (1 << FRAC_BITS)) / (1 << FRAC_BITS)
    return q


def frac_render(cls_map, t_map, pal_rgb):
    """cls_map: class id per pixel (-1 transparent), t continuous. sRGB lerp like a cheap runtime."""
    h, w = cls_map.shape
    out = np.zeros((h, w, 3), np.float32)
    for ci in np.unique(cls_map):
        if ci < 0:
            continue
        m = cls_map == ci
        idx = np.asarray(CLASSES[CLASS_NAMES[ci]])
        t = t_map[m]
        lo = np.floor(t).astype(int)
        lo = np.clip(lo, 0, len(idx) - 1)
        hi = np.clip(lo + 1, 0, len(idx) - 1)
        f = (t - lo)[:, None]
        out[m] = (1 - f) * pal_rgb[idx[lo]].astype(np.float32) + f * pal_rgb[idx[hi]].astype(np.float32)
    return np.clip(np.rint(out), 0, 255).astype(np.uint8)


def encode_frac(gt_labs, guide, candidate_mode, radius):
    """Fit class+t on one or several palettes (gt_labs: list of (H,W,3) OKLab, palettes aligned with TRAIN subset).
    candidate_mode 'guide' keeps xBR class; 'neighbourhood' re-estimates class among guide classes within radius."""
    h, w = guide.shape
    gcls = CLS_OF[guide]
    cls_map = np.where(guide == 0, -1, gcls).astype(np.int16)
    t_map = np.zeros((h, w), np.float64)
    q = np.concatenate(gt_labs, axis=2).reshape(-1, 3 * len(gt_labs))
    opaque = (guide != 0).reshape(-1)
    names_pal = candidate_mode[1]
    special_ids = {CLASS_NAMES.index(n) for n in SPECIAL}
    # candidates
    if candidate_mode[0] == "guide":
        cand_sets = None
    else:
        from scipy.ndimage import maximum_filter
        present = [c for c in np.unique(gcls[guide != 0]) if c not in special_ids]
        cand_sets = {}
        for c in present:
            m = (gcls == c) & (guide != 0)
            cand_sets[c] = maximum_filter(m.astype(np.uint8), size=2 * radius + 1).astype(bool).reshape(-1)
    best_e = np.full(h * w, np.inf)
    best_c = gcls.reshape(-1).astype(np.int16).copy()
    best_t = np.zeros(h * w)
    classes_here = [c for c in np.unique(gcls[guide != 0])]
    for c in classes_here:
        idx = np.asarray(CLASSES[CLASS_NAMES[c]])
        pts = np.concatenate([PAL_LAB[p][idx] for p in names_pal], axis=1)
        if cand_sets is None or c in special_ids:
            sel = opaque & (gcls.reshape(-1) == c)
        else:
            sel = opaque & cand_sets[c] & ~np.isin(gcls.reshape(-1), list(special_ids))
        if not sel.any():
            continue
        t, e = project(q[sel], pts)
        cur = np.flatnonzero(sel)
        better = e < best_e[cur]
        best_e[cur[better]] = e[better]
        best_c[cur[better]] = c
        best_t[cur[better]] = t[better]
    cls_map = np.where(opaque.reshape(h, w), best_c.reshape(h, w), -1).astype(np.int16)
    t_map = quant_t(best_t.reshape(h, w))
    return cls_map, t_map


def dither_indices(cls_map, t_map, center, scale):
    h, w = cls_map.shape
    yy, xx = np.mgrid[0:h, 0:w]
    # anchor to BAM centre: world-stable pattern
    ax = (xx - center[0] * scale) % 4
    ay = (yy - center[1] * scale) % 4
    thr = BAYER4[ay, ax]
    out = np.zeros((h, w), np.uint8)
    for ci in np.unique(cls_map):
        if ci < 0:
            continue
        m = cls_map == ci
        idx = np.asarray(CLASSES[CLASS_NAMES[ci]])
        t = t_map[m]
        lo = np.clip(np.floor(t).astype(int), 0, len(idx) - 1)
        hi = np.clip(lo + 1, 0, len(idx) - 1)
        f = t - lo
        out[m] = np.where(f > thr[m], idx[hi], idx[lo])
    return out



def nearest_index_multipal(gt_labs, guide, names_pal):
    """Index-only (existing runtime): per class, index minimising summed OKLab error over several palettes."""
    h, w = guide.shape
    out = guide.copy()
    q = np.concatenate(gt_labs, axis=2).reshape(-1, 3 * len(gt_labs))
    g = guide.reshape(-1)
    gcls = CLS_OF[g]
    flat = out.reshape(-1)
    for c in np.unique(gcls[g != 0]):
        if CLASS_NAMES[c] in SPECIAL:
            continue
        idx = np.asarray(CLASSES[CLASS_NAMES[c]])
        pts = np.concatenate([PAL_LAB[p][idx] for p in names_pal], axis=1)
        sel = np.flatnonzero((gcls == c) & (g != 0))
        d = ((q[sel][:, None, :] - pts[None]) ** 2).sum(2)
        flat[sel] = idx[d.argmin(1)]
    return flat.reshape(h, w)


def error_diffusion(cls_map, t_raw):
    """1-D Floyd-Steinberg on the shade coordinate, restricted to same-class neighbours."""
    h, w = cls_map.shape
    t = t_raw.astype(np.float64).copy()
    out = np.zeros((h, w), np.uint8)
    for y in range(h):
        xs = range(w) if y % 2 == 0 else range(w - 1, -1, -1)
        dx = 1 if y % 2 == 0 else -1
        for x in xs:
            c = cls_map[y, x]
            if c < 0:
                continue
            idx = CLASSES[CLASS_NAMES[c]]
            k = int(np.clip(np.rint(t[y, x]), 0, len(idx) - 1))
            out[y, x] = idx[k]
            e = t[y, x] - k
            for (yy, xx, wt) in ((y, x + dx, 7 / 16), (y + 1, x - dx, 3 / 16), (y + 1, x, 5 / 16), (y + 1, x + dx, 1 / 16)):
                if 0 <= yy < h and 0 <= xx < w and cls_map[yy, xx] == c:
                    t[yy, xx] += e * wt
    return out


def ramp_point(cls_ids, t, pal_rgb_float):
    """sRGB point on the class ramp for arrays of class ids and t."""
    out = np.zeros((len(t), 3), np.float32)
    for ci in np.unique(cls_ids):
        m = cls_ids == ci
        idx = np.asarray(CLASSES[CLASS_NAMES[ci]])
        lo = np.clip(np.floor(t[m]).astype(int), 0, len(idx) - 1)
        hi = np.clip(lo + 1, 0, len(idx) - 1)
        f = (t[m] - lo)[:, None]
        out[m] = (1 - f) * pal_rgb_float[idx[lo]] + f * pal_rgb_float[idx[hi]]
    return out


def boundary_blend(gt_labs, cls_map, t_map, names_pal):
    """Two-class weighted blend on class-boundary pixels, fitted on several palettes (OKLab of sRGB lerp)."""
    h, w = cls_map.shape
    special_ids = {CLASS_NAMES.index(n) for n in SPECIAL}
    ok = cls_map >= 0
    valid = ok & ~np.isin(cls_map, list(special_ids))
    c2 = np.full((h, w), -1, np.int16)
    pad = np.pad(np.where(valid, cls_map, -1), 1, constant_values=-1)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy == 0 and dx == 0:
                continue
            nb = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
            take = (c2 < 0) & valid & (nb >= 0) & (nb != cls_map)
            c2[take] = nb[take]
    bnd = c2 >= 0
    t2 = np.zeros((h, w))
    wgt = np.ones((h, w))
    if not bnd.any():
        return (cls_map, t_map, c2, t2, wgt)
    q = np.concatenate(gt_labs, axis=2)[bnd]
    c1v = cls_map[bnd]; c2v = c2[bnd]; t1v = t_map[bnd]
    t2v = np.zeros(len(c2v))
    for c in np.unique(c2v):
        m = c2v == c
        idx = np.asarray(CLASSES[CLASS_NAMES[c]])
        pts = np.concatenate([PAL_LAB[p][idx] for p in names_pal], axis=1)
        t2v[m], _ = project(q[m], pts)
    t2v = quant_t(t2v)
    # A and B in OKLab (per palette, from sRGB lerp)
    A = np.concatenate([srgb_u8_to_oklab(np.clip(np.rint(ramp_point(c1v, t1v, PAL[p].astype(np.float32))), 0, 255).astype(np.uint8)[None])[0] for p in names_pal], axis=1)
    B = np.concatenate([srgb_u8_to_oklab(np.clip(np.rint(ramp_point(c2v, t2v, PAL[p].astype(np.float32))), 0, 255).astype(np.uint8)[None])[0] for p in names_pal], axis=1)
    d = A - B
    dd = (d ** 2).sum(1)
    wv = np.where(dd > 1e-9, ((q - B) * d).sum(1) / np.maximum(dd, 1e-9), 1.0)
    wv = np.clip(np.round(np.clip(wv, 0, 1) * 8) / 8, 0, 1)
    t2[bnd] = t2v; wgt[bnd] = wv
    return (cls_map, t_map, c2, t2, wgt)


def frac2_render(payload, pal_rgb):
    c1, t1, c2, t2, wgt = payload
    base = frac_render(c1, t1, pal_rgb).astype(np.float32)
    bnd = (c2 >= 0) & (wgt < 1)
    if bnd.any():
        B = ramp_point(c2[bnd], t2[bnd], pal_rgb.astype(np.float32))
        base[bnd] = wgt[bnd][:, None] * base[bnd] + (1 - wgt[bnd][:, None]) * B
    return np.clip(np.rint(base), 0, 255).astype(np.uint8)

# ---------------------------------------------------------------- metrics
def de(a_rgb, b_rgb, mask):
    if not mask.any():
        return 0.0, 0.0
    a = srgb_u8_to_oklab(a_rgb)[mask]
    b = srgb_u8_to_oklab(b_rgb)[mask]
    d = np.sqrt(((a - b) ** 2).sum(1))
    return float(d.mean()), float(np.percentile(d, 95))


def main():
    t0 = time.time()
    desc, env = load_model(Path(get_path("reboutcx_model")), device="cuda:0", fp16=True)
    log("model", env)
    data = {}
    for lname, comp, resref in LAYERS:
        sel = selected(comp, resref)
        frames = [f for _, _, f in sel]
        g2 = xbr_guides(frames, 2)
        g4 = xbr_guides(frames, 4)
        items = []
        for (cname, pos, fr), a2, a4 in zip(sel, g2, g4):
            gt = {}
            for pn in PALETTES:
                rgb = prepare_inference_rgb(fr, PAL[pn])
                if rgb is None:
                    gt[pn] = (np.zeros((fr.height * 4, fr.width * 4, 3), np.uint8), np.zeros((fr.height * 2, fr.width * 2, 3), np.uint8))
                else:
                    gt[pn] = infer(desc, rgb)
            items.append(dict(cycle=cname, pos=pos, frame=fr, g2=a2, g4=a4, gt=gt))
        data[lname] = items
        log("layer", lname, len(items), "frames")
    log("inference done", round(time.time() - t0, 1), "s")

    methods = ["xBR", "Q0_used_nodither", "Q1_fullclass", "Q2_bayer4", "Q3_frac_ref", "Q3_frac_ref_3bit", "Q3_frac_ref_2bit", "Q3m_frac_multipal", "Q5_multipal_reclass", "Q6_idx_multipal", "Q7_errdiff", "Q8_frac_multipal_boundary"]
    stats = {}  # (scale, method, palette) -> list
    recon_store = {}
    sizes = {}
    for lname, items in data.items():
        for it in items:
            fr = it["frame"]
            used = np.unique(fr.indices)
            for scale in (2, 4):
                guide = it[f"g{scale}"]
                mask = guide != 0
                si = 0 if scale == 4 else 1
                gt_ref = it["gt"]["REF"][si]
                gt_lab = {p: srgb_u8_to_oklab(it["gt"][p][si]) for p in PALETTES}
                enc = {}
                enc["xBR"] = ("idx", guide)
                q0, _ = quantize_classed_oklab(gt_ref, guide, PAL["REF"], used, CLASSES, transparent_index=0)
                enc["Q0_used_nodither"] = ("idx", q0)
                q1, _ = quantize_classed_oklab(gt_ref, guide, PAL["REF"], np.arange(256), CLASSES, transparent_index=0)
                enc["Q1_fullclass"] = ("idx", q1)
                c3, t3 = encode_frac([gt_lab["REF"]], guide, ("guide", ["REF"]), 0)
                enc["Q3_frac_ref"] = ("frac", (c3, t3))
                enc["Q3_frac_ref_3bit"] = ("frac", (c3, np.round(t3 * 8) / 8))
                enc["Q3_frac_ref_2bit"] = ("frac", (c3, np.round(t3 * 4) / 4))
                enc["Q2_bayer4"] = ("idx", dither_indices(c3, t3, (fr.center_x, fr.center_y), scale))
                enc["Q6_idx_multipal"] = ("idx", nearest_index_multipal([gt_lab[p] for p in TRAIN], guide, TRAIN))
                enc["Q7_errdiff"] = ("idx", error_diffusion(c3, t3))
                c3m, t3m = encode_frac([gt_lab[p] for p in TRAIN], guide, ("guide", TRAIN), 0)
                enc["Q3m_frac_multipal"] = ("frac", (c3m, t3m))
                enc["Q8_frac_multipal_boundary"] = ("frac2", boundary_blend([gt_lab[p] for p in TRAIN], c3m, t3m, TRAIN))
                c5, t5 = encode_frac([gt_lab[p] for p in TRAIN], guide, ("neighbourhood", TRAIN), 1 if scale == 2 else 2)
                enc["Q5_multipal_reclass"] = ("frac", (c5, t5))
                for m, (kind, payload) in enc.items():
                    for pn in PALETTES:
                        if kind == "idx":
                            rec = PAL[pn][payload]
                        elif kind == "frac2":
                            rec = frac2_render(payload, PAL[pn])
                            bm = (payload[2] >= 0) & mask
                            mu_b, _ = de(rec, it["gt"][pn][si], bm)
                            mu_b0, _ = de(frac_render(payload[0], payload[1], PAL[pn]), it["gt"][pn][si], bm)
                            stats.setdefault(f"x{scale}|boundary_only|{pn}", []).append((mu_b0, mu_b, int(bm.sum())))
                        else:
                            rec = frac_render(payload[0], payload[1], PAL[pn])
                        mu, p95 = de(rec, it["gt"][pn][si], mask)
                        stats.setdefault(f"x{scale}|{m}|{pn}", []).append((mu, p95, int(mask.sum())))
                        recon_store[(lname, it["cycle"], it["pos"], scale, m, pn)] = rec
                    # size estimate
                    if kind == "idx":
                        raw = payload.astype(np.uint8).tobytes()
                    else:
                        c, t = payload[0], payload[1]
                        base = np.zeros(c.shape, np.uint8)
                        for ci in np.unique(c):
                            if ci < 0:
                                continue
                            idx = np.asarray(CLASSES[CLASS_NAMES[ci]])
                            base[c == ci] = idx[np.clip(np.floor(t[c == ci]).astype(int), 0, len(idx) - 1)]
                        frac = np.rint((t - np.floor(t)) * (1 << FRAC_BITS)).astype(np.uint8)
                        raw = base.tobytes() + frac.tobytes()
                    if kind != "idx":
                        c, t = payload[0], payload[1]
                        cls_plane = np.where(c < 0, 255, c).astype(np.uint8)
                        t8 = np.clip(np.rint(t * 8), 0, 255).astype(np.uint8)  # 3-bit fraction, single scalar per pixel
                        dt = t8.astype(np.int16).copy(); dt[:, 1:] -= t8[:, :-1].astype(np.int16)
                        same = np.zeros_like(c, bool); same[:, 1:] = c[:, 1:] == c[:, :-1]
                        dt = np.where(same, dt, t8.astype(np.int16)).astype(np.uint8)
                        alt = cls_plane.tobytes() + dt.tobytes()
                        sizes.setdefault(f"x{scale}|{m}|class+t8delta", [0, 0])
                        sizes[f"x{scale}|{m}|class+t8delta"][0] += len(alt)
                        sizes[f"x{scale}|{m}|class+t8delta"][1] += len(zlib.compress(alt, 6))
                    sizes.setdefault(f"x{scale}|{m}", [0, 0])
                    sizes[f"x{scale}|{m}"][0] += len(raw)
                    sizes[f"x{scale}|{m}"][1] += len(zlib.compress(raw, 6))
                # store per-item encodings for temporal
                it[f"enc{scale}"] = enc
        log("encoded", lname)

    summary = {}
    for k, v in stats.items():
        a = np.array(v)
        wts = a[:, 2]
        summary[k] = {"de_mean": float((a[:, 0] * wts).sum() / wts.sum()), "de_p95_mean": float(a[:, 1].mean()), "de_second_weighted": float((a[:, 1] * wts).sum() / wts.sum()), "pixels": int(wts.sum())}

    # temporal flicker on idle cycle (body + all layers), REF and B
    flicker = {}
    for lname, items in data.items():
        idle = [it for it in items if it["cycle"] == "idle_s"]
        for scale in (2, 4):
            si = 0 if scale == 4 else 1
            for m in methods:
                for pn in ["REF", "B"]:
                    tot = 0
                    flick = 0
                    for a, b in zip(idle[:-1], idle[1:]):
                        fa, fb = a["frame"], b["frame"]
                        ra = recon_store[(lname, "idle_s", a["pos"], scale, m, pn)]
                        rb = recon_store[(lname, "idle_s", b["pos"], scale, m, pn)]
                        ga = srgb_u8_to_oklab(a["gt"][pn][si]); gb = srgb_u8_to_oklab(b["gt"][pn][si])
                        ma = a[f"g{scale}"] != 0; mb = b[f"g{scale}"] != 0
                        # align on world coordinates (pixel - centre*scale)
                        ox = (fb.center_x - fa.center_x) * scale
                        oy = (fb.center_y - fa.center_y) * scale
                        ha, wa = ma.shape; hb, wb = mb.shape
                        x0 = max(0, ox); y0 = max(0, oy)
                        x1 = min(wa, wb + ox); y1 = min(ha, hb + oy)
                        if x1 <= x0 or y1 <= y0:
                            continue
                        sa = (slice(y0, y1), slice(x0, x1)); sb = (slice(y0 - oy, y1 - oy), slice(x0 - ox, x1 - ox))
                        both = ma[sa] & mb[sb]
                        static = both & (np.sqrt(((ga[sa] - gb[sb]) ** 2).sum(2)) < 0.01)
                        la = srgb_u8_to_oklab(ra[sa]); lb = srgb_u8_to_oklab(rb[sb])
                        dd = np.sqrt(((la - lb) ** 2).sum(2))
                        tot += int(static.sum()); flick += int((static & (dd > 0.02)).sum())
                    flicker[f"{lname}|x{scale}|{m}|{pn}"] = {"static_px": tot, "flicker_ratio": flick / tot if tot else None}
    json.dump({"summary": summary, "flicker": flicker, "sizes": sizes, "palettes": PALETTES,
               "frac_bits": FRAC_BITS, "layers": LAYERS, "cycles": CYCLES}, open(OUT / "e3_results.json", "w"), indent=1)
    log("metrics written")

    # ------------------------------------------------ visuals: composite idle frame 0 and walk frame 3
    def composite(key_fn, scale, frame_sel):
        parts = []
        parts_shadow = []
        for lname in ["body", "helmet", "shield", "weapon"]:
            it = next(i for i in data[lname] if (i["cycle"], i["pos"]) == frame_sel)
            rgb = key_fn(lname, it, scale)
            g = it[f"g{scale}"]
            parts.append((it["frame"], rgb, g != 0))
            parts_shadow.append(g == 1)
        left = min(-p[0].center_x for p in parts); top = min(-p[0].center_y for p in parts)
        right = max(-p[0].center_x + p[0].width for p in parts); bot = max(-p[0].center_y + p[0].height for p in parts)
        W = (right - left) * 4; H = (bot - top) * 4
        canvas = np.zeros((H, W, 3), np.uint8); canvas[:] = (58, 52, 44)
        for fr, rgb, m in parts:
            if scale == 2:
                rgb = rgb.repeat(2, 0).repeat(2, 1); m = m.repeat(2, 0).repeat(2, 1)
            x = (-fr.center_x - left) * 4; y = (-fr.center_y - top) * 4
            sub = canvas[y:y + rgb.shape[0], x:x + rgb.shape[1]]
            sh = parts_shadow.pop(0)
            if scale == 2:
                sh = sh.repeat(2, 0).repeat(2, 1)
            body = m & ~sh
            sub[body] = rgb[body]
            sub[sh] = (sub[sh] * 0.5).astype(np.uint8)
        return canvas

    rows = [("xBR x2", 2, "xBR"), ("xBR x4", 4, "xBR"), ("RCX x2 actuel Q0", 2, "Q0_used_nodither"),
            ("RCX x4 actuel Q0", 4, "Q0_used_nodither"), ("RCX x4 Bayer Q2", 4, "Q2_bayer4"),
            ("RCX x4 idx multi Q6", 4, "Q6_idx_multipal"), ("RCX x2 frac+bord Q8", 2, "Q8_frac_multipal_boundary"),
            ("RCX x4 frac Q3", 4, "Q3_frac_ref"), ("RCX x4 frac+bord Q8", 4, "Q8_frac_multipal_boundary")]
    for frame_sel in [("idle_s", 0), ("walk_s", 3)]:
        for pn in ["REF", "B", "D_heldout", "E_armorblue_heldout"]:
            tiles = []
            for label, scale, m in rows:
                tiles.append((label, composite(lambda ln, it, s, m=m, pn=pn: recon_store[(ln, it["cycle"], it["pos"], s, m, pn)], scale, frame_sel)))
            tiles.append(("GT modèle x4", composite(lambda ln, it, s, pn=pn: it["gt"][pn][0], 4, frame_sel)))
            h = max(t[1].shape[0] for t in tiles); w = max(t[1].shape[1] for t in tiles)
            sheet = Image.new("RGB", (w * 5, (h + 18) * 2), (30, 30, 30))
            from PIL import ImageDraw
            dr = ImageDraw.Draw(sheet)
            for i, (label, img) in enumerate(tiles):
                x = (i % 5) * w; y = (i // 5) * (h + 18)
                sheet.paste(Image.fromarray(img), (x, y + 18))
                dr.text((x + 3, y + 3), label, fill=(255, 255, 255))
            sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST)
            sheet.save(OUT / f"sheet_{frame_sel[0]}{frame_sel[1]}_{pn}.png")

    # temporal GIF: idle cycle, palette B, x4, side by side
    frames_gif = []
    gif_methods = [("Q0 actuel", "Q0_used_nodither"), ("Q2 Bayer", "Q2_bayer4"), ("Q7 diffusion", "Q7_errdiff"), ("Q8 frac+bord", "Q8_frac_multipal_boundary")]
    from PIL import ImageDraw
    for pos in range(12):
        tiles = [composite(lambda ln, it, s_, m=m: recon_store[(ln, it["cycle"], it["pos"], s_, m, "B")], 4, ("idle_s", pos)) for _, m in gif_methods]
        h = max(t.shape[0] for t in tiles); w = max(t.shape[1] for t in tiles)
        im = Image.new("RGB", (w * len(tiles), h + 16), (30, 30, 30))
        dr = ImageDraw.Draw(im)
        for i, t in enumerate(tiles):
            im.paste(Image.fromarray(t), (i * w, 16)); dr.text((i * w + 3, 2), gif_methods[i][0], fill=(255, 255, 255))
        frames_gif.append(im.resize((im.width * 2, im.height * 2), Image.Resampling.NEAREST))
    frames_gif[0].save(OUT / "idle_temporal_B_x4.gif", save_all=True, append_images=frames_gif[1:], duration=100, loop=0)
    # display simulation (zoom z, NEAREST vs area) for REF idle 0
    def display_sim(img4, z, logical_scale=4, mode="nearest"):
        H, W = img4.shape[:2]
        lw, lh = W / logical_scale, H / logical_scale
        sw, sh = int(lw * z), int(lh * z)
        if mode == "nearest":
            ys = np.clip(((np.arange(sh) + 0.5) / z * logical_scale).astype(int), 0, H - 1)
            xs = np.clip(((np.arange(sw) + 0.5) / z * logical_scale).astype(int), 0, W - 1)
            return img4[ys][:, xs]
        return np.asarray(Image.fromarray(img4).resize((sw, sh), Image.Resampling.BOX))
    disp = {}
    for label, scale, m in rows:
        img = composite(lambda ln, it, s, m=m: recon_store[(ln, it["cycle"], it["pos"], s, m, "REF")], scale, ("idle_s", 0))
        for z in (1.0, 1.3, 2.0, 3.0):
            n = display_sim(img, z, 4, "nearest").astype(np.float32)
            a = display_sim(img, z, 4, "area").astype(np.float32)
            disp[f"{m}|x{scale}|z{z}"] = float(np.abs(n - a).mean())
            if z in (1.3, 2.0) and m in ("xBR", "Q0_used_nodither", "Q2_bayer4", "Q8_frac_multipal_boundary"):
                Image.fromarray(np.concatenate([n, a], 1).astype(np.uint8)).resize((int(n.shape[1] * 2 * 3), int(n.shape[0] * 3)), Image.Resampling.NEAREST).save(OUT / f"display_z{z}_{m}_x{scale}.png")
    res = json.load(open(OUT / "e3_results.json"))
    res["display_alias_mae_nearest_vs_area"] = disp
    json.dump(res, open(OUT / "e3_results.json", "w"), indent=1)
    log("done", round(time.time() - t0, 1), "s")


if __name__ == "__main__":
    main()
