"""E5 — validation croisée : méthodes Claude Code (Q0..Q8) sur le corpus et les palettes de Codex.

Corpus Codex : cycle 0 complet (14 frames) de CHFB1A1 + WQNS0A1 + WQNC0A1 + WQNJ6A1.
Palettes d'apprentissage (Claude) : REF, B, C. Palettes de test jamais vues : D (Claude),
CX_B et CX_C (profils « contrast » et « pale » de Codex).
Ajouts : interpolation en lumière linéaire (proposition Codex) et variante Codex
« interpolation continue sous la seule palette de référence ».
Offline ; lit les sources scellées ; écrit seulement sous OUT.
"""
from __future__ import annotations

import json
import sys
import time
import zlib
from pathlib import Path

import numpy as np

OUT = Path(sys.argv[1]); OUT.mkdir(parents=True, exist_ok=True)
E3B = Path(sys.argv[3])
sys.argv = [sys.argv[0], str(OUT / "_unused"), sys.argv[2]]
sys.path.insert(0, str(E3B.parent))
import importlib.util
spec = importlib.util.spec_from_file_location("e3b", E3B)
E = importlib.util.module_from_spec(spec); spec.loader.exec_module(E)

_cx = importlib.util.spec_from_file_location("codex_palette_lab", r"C:/Users/Adrien/Desktop/CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/palette/palette_lab.py")
CX = importlib.util.module_from_spec(_cx); _cx.loader.exec_module(CX)   # lecture seule : fonction quantize_modes de Codex
from reboutcx_quantize import character_chmb1_palette_rgb, quantize_classed_oklab, srgb_u8_to_oklab  # noqa: E402

PALETTES = {
    "REF": [30, 47, 57, 12, 39, 21, 3],
    "B": [21, 57, 47, 8, 66, 30, 0],
    "C": [19, 63, 66, 15, 39, 26, 4],
    "D_heldout": [67, 68, 47, 84, 25, 57, 2],
    "CX_B_heldout": [30, 63, 3, 12, 39, 21, 57],
    "CX_C_heldout": [30, 55, 30, 0, 39, 30, 0],
}
TRAIN = ["REF", "B", "C"]
E.PAL = {k: character_chmb1_palette_rgb(E.RANGES[v]) for k, v in PALETTES.items()}
E.PAL_LAB = {k: srgb_u8_to_oklab(v) for k, v in E.PAL.items()}
PAL, CLASSES, CLASS_NAMES, CLS_OF, SPECIAL = E.PAL, E.CLASSES, E.CLASS_NAMES, E.CLS_OF, E.SPECIAL
LAYERS = [("body", "chfb1", "CHFB1A1"), ("weapon", "sw1h01-wqns0", "WQNS0A1"),
          ("shield", "shld01-wqnc0", "WQNC0A1"), ("helmet", "helm01-wqnj6", "WQNJ6A1")]


def lin(u8):
    v = np.asarray(u8, np.float64) / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def enc(v):
    v = np.clip(v, 0, 1)
    return np.clip(np.rint(255 * np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055)), 0, 255).astype(np.uint8)


def render(cls_map, t_map, pal_rgb, mode, c2=None, t2=None, w=None):
    """mode 'srgb' (lerp octets) or 'linear' (lerp lumière linéaire)."""
    h, wd = cls_map.shape
    acc = np.zeros((h, wd, 3))
    def ramp(cm, tm):
        out = np.zeros(cm.shape + (3,))
        for ci in np.unique(cm):
            if ci < 0:
                continue
            m = cm == ci
            idx = np.asarray(CLASSES[CLASS_NAMES[ci]])
            lo = np.clip(np.floor(tm[m]).astype(int), 0, len(idx) - 1); hi = np.clip(lo + 1, 0, len(idx) - 1)
            f = (tm[m] - lo)[:, None]
            a = pal_rgb[idx[lo]].astype(np.float64); b = pal_rgb[idx[hi]].astype(np.float64)
            out[m] = (1 - f) * a + f * b if mode == "srgb" else (1 - f) * lin(a) + f * lin(b)
        return out
    acc = ramp(cls_map, t_map)
    if c2 is not None:
        bnd = (c2 >= 0) & (w < 1)
        if bnd.any():
            sec = ramp(np.where(bnd, c2, -1), np.where(bnd, t2, 0))
            ww = np.where(bnd, w, 1.0)[..., None]
            acc = ww * acc + (1 - ww) * sec
    return np.clip(np.rint(acc), 0, 255).astype(np.uint8) if mode == "srgb" else enc(acc)


def levels(ci, pal, mode, bits=3):
    idx = np.asarray(CLASSES[CLASS_NAMES[ci]]); n = len(idx)
    if n == 1:
        return np.array([0.0]), pal[idx][:1].astype(np.float64)
    ts = np.arange(0, (n - 1) * (1 << bits) + 1) / (1 << bits)
    lo = np.clip(np.floor(ts).astype(int), 0, n - 1); hi = np.clip(lo + 1, 0, n - 1); f = (ts - lo)[:, None]
    a = pal[idx[lo]].astype(np.float64); b = pal[idx[hi]].astype(np.float64)
    col = (1 - f) * a + f * b if mode == "srgb" else (1 - f) * lin(a) + f * lin(b)
    u8 = np.clip(np.rint(col), 0, 255).astype(np.uint8) if mode == "srgb" else enc(col)
    return ts, u8


def encode_levels(gt_labs, guide, names, mode, boundary):
    """Exact 1/8 encoder (nearest level on all training palettes), optional two-range boundary blend."""
    h, w = guide.shape
    g = guide.reshape(-1); gc = CLS_OF[g]
    q = np.concatenate(gt_labs, axis=2).reshape(-1, 3 * len(names))
    cls_map = np.where(g == 0, -1, gc).astype(np.int16); t_map = np.zeros(h * w)
    lv = {}
    for c in np.unique(gc[g != 0]):
        ts, _ = levels(c, PAL["REF"], mode)
        pts = np.concatenate([srgb_u8_to_oklab(levels(c, PAL[p], mode)[1]) for p in names], axis=1)
        lv[c] = (ts, pts)
        sel = np.flatnonzero((gc == c) & (g != 0))
        for s in range(0, sel.size, 4096):
            cur = sel[s:s + 4096]
            d = ((q[cur][:, None, :] - pts[None]) ** 2).sum(2)
            t_map[cur] = ts[d.argmin(1)]
    cls_map = cls_map.reshape(h, w); t_map = t_map.reshape(h, w)
    if not boundary:
        return cls_map, t_map, None, None, None
    special = {CLASS_NAMES.index(n) for n in SPECIAL}
    valid = (cls_map >= 0) & ~np.isin(cls_map, list(special))
    c2 = np.full((h, w), -1, np.int16)
    pad = np.pad(np.where(valid, cls_map, -1), 1, constant_values=-1)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dy or dx:
                nb = pad[1 + dy:1 + dy + h, 1 + dx:1 + dx + w]
                take = (c2 < 0) & valid & (nb >= 0) & (nb != cls_map)
                c2[take] = nb[take]
    t2 = np.zeros((h, w)); wmap = np.ones((h, w))
    bnd = c2 >= 0
    if not bnd.any():
        return cls_map, t_map, c2, t2, wmap
    qb = q.reshape(h, w, -1)[bnd]
    c2v = c2[bnd]
    t2v = np.zeros(len(c2v))
    for c in np.unique(c2v):
        if c not in lv:
            ts, _ = levels(c, PAL["REF"], mode)
            lv[c] = (ts, np.concatenate([srgb_u8_to_oklab(levels(c, PAL[p], mode)[1]) for p in names], axis=1))
        ts, pts = lv[c]; m = c2v == c
        d = ((qb[m][:, None, :] - pts[None]) ** 2).sum(2)
        t2v[m] = ts[d.argmin(1)]
    t2[bnd] = t2v
    # weight: try the 9 weights k/8 exactly on all training palettes
    best = np.full(bnd.sum(), np.inf); bw = np.ones(bnd.sum())
    rend = {}
    for p in names:
        prim = render(cls_map, t_map, PAL[p], mode)[bnd]
        sec = render(np.where(bnd, c2, -1), np.where(bnd, t2, 0), PAL[p], mode)[bnd]
        rend[p] = (prim, sec)
    for k in range(9):
        wk = k / 8.0
        err = np.zeros(bnd.sum())
        for j, p in enumerate(names):
            prim, sec = rend[p]
            if mode == "srgb":
                mix = np.clip(np.rint(wk * prim + (1 - wk) * sec), 0, 255).astype(np.uint8)
            else:
                mix = enc(wk * lin(prim) + (1 - wk) * lin(sec))
            err += ((srgb_u8_to_oklab(mix[None])[0] - qb[:, 3 * j:3 * j + 3]) ** 2).sum(1)
        better = err < best
        best[better] = err[better]; bw[better] = wk
    wmap[bnd] = bw
    return cls_map, t_map, c2, t2, wmap


def main():
    t0 = time.time()
    desc, env = E.load_model(Path(E.get_path("reboutcx_model")), device="cuda:0", fp16=True)
    data = {}
    for lname, comp, resref in LAYERS:
        res = E.load_layer(comp, resref)
        idx = res["cycles"][0]["frame_indices"]
        frames = [res["frames"][i] for i in idx]
        g2 = E.xbr_guides(frames, 2); g4 = E.xbr_guides(frames, 4)
        items = []
        for p, (fr, a2, a4) in enumerate(zip(frames, g2, g4)):
            gt = {pn: E.infer(desc, E.prepare_inference_rgb(fr, PAL[pn])) for pn in PALETTES}
            items.append(dict(pos=p, frame=fr, g2=a2, g4=a4, gt=gt))
        data[lname] = items
    print("inference", round(time.time() - t0, 1), "s", flush=True)
    methods = ["xBR", "Q0_actuel", "Q1_classe", "Q6_idx_multi", "Q3_frac_ref", "CX_interp_ref_lin", "CX_codex_exact", "CX_codex_bayer",
               "Q8_srgb", "Q8x_srgb_exact", "Q8x_lin_exact"]
    stats, store = {}, {}
    sizes = {}
    for lname, items in data.items():
        for it in items:
            fr = it["frame"]
            for scale in (2, 4):
                si = 0 if scale == 4 else 1
                guide = it[f"g{scale}"]; mask = guide != 0
                gl = {p: srgb_u8_to_oklab(it["gt"][p][si]) for p in PALETTES}
                gref = it["gt"]["REF"][si]
                encs = {}
                encs["xBR"] = lambda pal, g=guide: pal[g]
                q0, _ = quantize_classed_oklab(gref, guide, PAL["REF"], np.unique(fr.indices), CLASSES, transparent_index=0)
                encs["Q0_actuel"] = lambda pal, q=q0: pal[q]
                q1, _ = quantize_classed_oklab(gref, guide, PAL["REF"], np.arange(256), CLASSES, transparent_index=0)
                encs["Q1_classe"] = lambda pal, q=q1: pal[q]
                q6 = E.nearest_index_multipal([gl[p] for p in TRAIN], guide, TRAIN)
                encs["Q6_idx_multi"] = lambda pal, q=q6: pal[q]
                c3, t3 = E.encode_frac([gl["REF"]], guide, ("guide", ["REF"]), 0)
                encs["Q3_frac_ref"] = lambda pal, c=c3, t=t3: render(c, t, pal, "srgb")
                # Codex-like: continuous weight, linear light, fitted on REF only (projection in linear RGB)
                cx_c = np.where(guide == 0, -1, CLS_OF[guide]).astype(np.int16); cx_t = np.zeros(guide.shape)
                tl = lin(gref).reshape(-1, 3)
                for c in np.unique(cx_c[cx_c >= 0]):
                    ids = np.asarray(CLASSES[CLASS_NAMES[c]])
                    m = (cx_c == c).reshape(-1)
                    tt, _ = E.project(tl[m], lin(PAL["REF"][ids]))
                    cx_t.reshape(-1)[m] = np.round(tt * 256) / 256
                encs["CX_interp_ref_lin"] = lambda pal, c=cx_c, t=cx_t: render(c, t, pal, "linear")
                qm = CX.quantize_modes(gref, guide, PAL["REF"], anchor=(fr.center_x * scale, fr.center_y * scale))
                encs["CX_codex_exact"] = lambda pal, q=qm: np.where((q["lo"] == 0)[..., None], 0, CX.encode(CX.linear(pal[q["lo"]]) * (1 - q["weight"][..., None]) + CX.linear(pal[q["hi"]]) * q["weight"][..., None]))
                encs["CX_codex_bayer"] = lambda pal, q=qm: pal[q["ordered"]]
                c8, t8 = E.encode_frac([gl[p] for p in TRAIN], guide, ("guide", TRAIN), 0)
                bb = E.boundary_blend([gl[p] for p in TRAIN], c8, t8, TRAIN)
                encs["Q8_srgb"] = lambda pal, b=bb: E.frac2_render(b, pal)
                for mode, name in (("srgb", "Q8x_srgb_exact"), ("linear", "Q8x_lin_exact")):
                    cm, tm, c2, t2, wm = encode_levels([gl[p] for p in TRAIN], guide, TRAIN, mode, True)
                    encs[name] = lambda pal, a=(cm, tm, c2, t2, wm), md=mode: render(a[0], a[1], pal, md, a[2], a[3], a[4])
                for m in methods:
                    for pn in PALETTES:
                        rec = encs[m](PAL[pn])
                        mu, _ = E.de(rec, it["gt"][pn][si], mask)
                        stats.setdefault(f"x{scale}|{m}|{pn}", []).append((mu, int(mask.sum())))
                        store[(lname, it["pos"], scale, m, pn)] = rec
        print("encoded", lname, round(time.time() - t0, 1), flush=True)
    summary = {k: float(sum(a * n for a, n in v) / max(1, sum(n for _, n in v))) * 1000 for k, v in stats.items()}
    # temporal: consecutive frames, aligned on centre, static where GT change < 0.01
    flick = {}
    for lname, items in data.items():
        for scale in (2, 4):
            si = 0 if scale == 4 else 1
            for m in methods:
                for pn in ["REF", "CX_B_heldout", "CX_C_heldout"]:
                    tot = fl = 0
                    for a, b in zip(items[:-1], items[1:]):
                        fa, fb = a["frame"], b["frame"]
                        ma = a[f"g{scale}"] != 0; mb = b[f"g{scale}"] != 0
                        ox = (fb.center_x - fa.center_x) * scale; oy = (fb.center_y - fa.center_y) * scale
                        ha, wa = ma.shape; hb, wb = mb.shape
                        x0, y0 = max(0, ox), max(0, oy); x1, y1 = min(wa, wb + ox), min(ha, hb + oy)
                        if x1 <= x0 or y1 <= y0:
                            continue
                        sa = (slice(y0, y1), slice(x0, x1)); sb = (slice(y0 - oy, y1 - oy), slice(x0 - ox, x1 - ox))
                        ga = srgb_u8_to_oklab(a["gt"][pn][si])[sa]; gb = srgb_u8_to_oklab(b["gt"][pn][si])[sb]
                        st = ma[sa] & mb[sb] & (np.sqrt(((ga - gb) ** 2).sum(2)) < 0.01)
                        ra = srgb_u8_to_oklab(store[(lname, a["pos"], scale, m, pn)])[sa]
                        rb = srgb_u8_to_oklab(store[(lname, b["pos"], scale, m, pn)])[sb]
                        tot += int(st.sum()); fl += int((st & (np.sqrt(((ra - rb) ** 2).sum(2)) > 0.02)).sum())
                    flick[f"{lname}|x{scale}|{m}|{pn}"] = [tot, fl]
    json.dump({"palettes": PALETTES, "train": TRAIN, "layers": LAYERS, "summary_de_x1000": summary, "flicker": flick},
              open(OUT / "e5_results.json", "w"), indent=1)
    # visual: body frame 6, x4, palettes CX_B / CX_C
    from PIL import Image, ImageDraw
    for pn in ["REF", "CX_B_heldout", "CX_C_heldout", "D_heldout"]:
        sel = ["Q0_actuel", "Q6_idx_multi", "CX_codex_exact", "Q8_srgb", "Q8x_lin_exact"]
        tiles = [store[("body", 6, 4, m, pn)] for m in sel] + [data["body"][6]["gt"][pn][0]]
        labels = ["Q0 actuel", "Q6 multi", "Interp. Codex", "Q8 Claude", "Q8 exact lin.", "Sortie modele"]
        g = data["body"][6]["g4"]
        h, w = g.shape
        sheet = Image.new("RGB", (w * len(tiles), h + 16), (30, 30, 30)); d = ImageDraw.Draw(sheet)
        for i, t in enumerate(tiles):
            im = np.zeros((h, w, 3), np.uint8); im[:] = (58, 52, 44)
            m = g != 0; sh = g == 1
            im[m & ~sh] = t[m & ~sh]; im[sh] = (im[sh] * 0.5).astype(np.uint8)
            sheet.paste(Image.fromarray(im), (i * w, 16)); d.text((i * w + 3, 2), labels[i], fill=(255, 255, 255))
        sheet.resize((sheet.width * 2, sheet.height * 2), Image.Resampling.NEAREST).save(OUT / f"cross_body6_{pn}.png")
    print("done", round(time.time() - t0, 1), "s", flush=True)


if __name__ == "__main__":
    main()
