"""P1 0x6110 experiment: E3b + Codex, nested K, disjoint holdouts, no installation."""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import time

import numpy as np
from PIL import Image, ImageDraw

from bg2lib import load_key, resolve_resource
from palette_frac_encode import (
    CLASS_PROFILE, DECODE_RULE, ENCODER_ID, check_contract, decode,
    dependency_mask, encode_variants,
)
from reboutcx_multipal import (
    infer_targets, inference_context, prepare_guides, save_npz, sha256_file,
)
from reboutcx_quantize import (
    CHARACTER_CHMB1_REFERENCE_COLORS, character_chmb1_classes,
    character_chmb1_palette_rgb, quantize_classed_oklab, srgb_u8_to_oklab,
)
from run_creature_sprite_x2 import WindowsXpressHuffCodec, bam_cycles, load_source_frames
from sprite_layout import family_directory

ROOT = Path(__file__).resolve().parents[2]
KS = (3, 4, 6)
CHANNELS = ("metal", "minor", "major", "skin", "leather", "armor", "hair")
TRAIN_ROWS = [
    ("REF", list(CHARACTER_CHMB1_REFERENCE_COLORS)),
    ("DEFAULT", [30, 91, 93, 12, 23, 93, 2]),
    ("LATIN1", [21, 57, 46, 83, 55, 67, 44]),
    ("LATIN2", [3, 54, 60, 84, 45, 68, 20]),
    ("LATIN3", [58, 50, 69, 0, 33, 19, 71]),
    ("LATIN4", [73, 71, 18, 15, 67, 56, 66]),
]


def write_json(path: Path, value) -> None:
    temporary = path.with_suffix(".part")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def native_resources() -> tuple[dict, dict]:
    bifs, entries = load_key()
    raw, identities = {}, {}
    for name, kind in (("MPALETTE", 1), ("RANGES12", 1), ("RANDCOLR", 1012),
                       ("RACECOLR", 1012), ("CLASCOLR", 1012)):
        matches = [entry for entry in entries if entry[0].upper() == name and entry[1] == kind]
        if len(matches) != 1:
            raise ValueError(f"ambiguous native resource {name}")
        raw[name], bif = resolve_resource(bifs, matches[0][2])
        import hashlib
        identities[name] = {"bif": bif, "locator": hex(matches[0][2]),
                            "sha256": hashlib.sha256(raw[name]).hexdigest()}
    if raw["MPALETTE"] != raw["RANGES12"]:
        raise ValueError("MPALETTE/RANGES12 alias is not byte-identical")
    return raw, identities


def parse_2da(raw: bytes) -> tuple[list[str], dict]:
    lines = [line.strip() for line in raw.decode("cp1252").splitlines() if line.strip()]
    if lines[0].upper().split() != ["2DA", "V1.0"]:
        raise ValueError("2DA V1.0 required")
    columns, rows = lines[2].split(), {}
    for line in lines[3:]:
        fields = line.split()
        values = fields[1:]
        if len(values) > len(columns):
            raise ValueError("2DA row has excess columns")
        rows[fields[0]] = dict(zip(columns, values+[lines[1]]*(len(columns)-len(values)), strict=True))
    return columns, rows


def palette_plan(raw: dict) -> tuple[list[dict], dict, dict]:
    ramps = np.asarray(Image.open(io.BytesIO(raw["MPALETTE"])).convert("RGB"))
    if ramps.shape != (256, 12, 3):
        raise ValueError("MPALETTE shape differs")
    class_cols, class_rows = parse_2da(raw["CLASCOLR"])
    race_cols, race_rows = parse_2da(raw["RACECOLR"])
    random_cols, random_rows = parse_2da(raw["RANDCOLR"])
    random_sets = {int(random_rows["0"][col]): [int(row[col]) for label, row in random_rows.items()
                                             if label != "0"] for col in random_cols}

    def leaves(value: int, seen=()) -> list[int]:
        if value < 200:
            return [value]
        if value in seen:
            return []
        return [leaf for child in random_sets.get(value, [])
                for leaf in leaves(child, (*seen, value))]

    class_keys = ("METAL", "MINOR_CLOTH", "MAIN_CLOTH", "LEATHER", "ARMOR")
    fighter = [int(class_rows[key]["FIGHTER"]) for key in class_keys]
    human = [int(race_rows[key]["HUMAN"]) for key in ("SKIN", "HAIR")]
    real_default = fighter[:3] + human[:1] + fighter[3:] + human[1:]
    if real_default != TRAIN_ROWS[1][1]:
        raise ValueError(f"native human fighter defaults changed: {real_default}")
    records = [{"name": name, "rows": rows, "role": "fit",
                "origin": "production" if name == "REF" else
                          "CLASCOLR/RACECOLR" if name == "DEFAULT" else "designed hue/lightness rotation"}
               for name, rows in TRAIN_ROWS]
    blocked = [set(rows[c] for _, rows in TRAIN_ROWS) for c in range(7)]
    lab = srgb_u8_to_oklab(ramps.astype(np.float64).mean(axis=1))
    # Also exclude identical ramp bytes under a different numeric row ID.
    allowed = [[row for row in range(200) if row not in blocked[c] and
                not any(np.array_equal(ramps[row], ramps[old]) for old in blocked[c])]
               for c in range(7)]
    rng = np.random.default_rng(6110)
    templates = []
    classes = [col for col in class_cols if col != "FIGHTER"][:6]
    races = [col for col in race_cols if col != "HUMAN"]
    for number, cls in enumerate(classes):
        race = races[number % len(races)]
        vals = [int(class_rows[key][cls]) for key in class_keys]
        skin, hair = (int(race_rows[key][race]) for key in ("SKIN", "HAIR"))
        templates.append((f"VAL{number+1:02}", vals[:3]+[skin]+vals[3:]+[hair],
                          {"kind": "default-derived", "class": cls, "race": race}))
    for number in range(2):
        ids = [226, 209, 208, 201 if number == 0 else 219, 228, 244, 200 if number == 0 else 218]
        templates.append((f"VAL{len(templates)+1:02}", ids,
                          {"kind": "RANDCOLR-derived", "seed": 6110}))
    templates += [("VAL09", [67, 68, 0, 79, 25, 27, 14], {"kind": "extreme stress"}),
                  ("VAL10", [0, 67, 68, 80, 0, 0, 67], {"kind": "extreme stress"})]
    if len(templates) != 10:
        raise ValueError("ten validation templates required")
    for name, original, origin in templates:
        resolved, trace = [], []
        for c, value in enumerate(original):
            pool = leaves(value)
            if not pool:
                raise ValueError(f"unresolvable random color {value}")
            value = int(rng.choice(pool)) if value >= 200 else value
            target = value
            if value not in allowed[c]:
                value = min(allowed[c], key=lambda row: (float(np.sum((lab[row]-lab[target])**2)), row))
            resolved.append(value)
            trace.append({"requested": original[c], "random_resolved": target,
                          "disjoint_row": value})
        records.append({"name": name, "role": "validation", "rows": resolved,
                        "origin": origin, "resolution": trace,
                        "default_preserved": resolved == original})
    if len({tuple(r["rows"]) for r in records if r["role"] == "validation"}) != 10:
        raise ValueError("duplicate validation palette")
    for name, rows in (("LEGACY_D", [67, 68, 47, 84, 25, 57, 2]),
                       ("LEGACY_E", [30, 47, 57, 12, 39, 68, 3])):
        records.append({"name": name, "rows": rows, "role": "diagnostic", "origin": "E3b partially seen"})
    palettes = {r["name"]: character_chmb1_palette_rgb(ramps[r["rows"]]) for r in records}
    validation = [r for r in records if r["role"] == "validation"]
    checks = {"validation_count": len(validation), "same_channel_id_overlap":
              sum(row in blocked[c] for r in validation for c, row in enumerate(r["rows"])),
              "same_channel_ramp_overlap": sum(any(np.array_equal(ramps[row], ramps[old])
              for old in blocked[c]) for r in validation for c, row in enumerate(r["rows"])),
              "fit_mean_lightness_by_channel": {CHANNELS[c]: [float(lab[rows[c], 0])
              for _, rows in TRAIN_ROWS] for c in range(7)},
              "random_resolution": "deterministic native RANDCOLR traversal; cycles excluded; final rows <200"}
    if checks["same_channel_id_overlap"] or checks["same_channel_ramp_overlap"]:
        raise ValueError("validation overlaps fit")
    return records, palettes, checks


def corpus() -> tuple[Path, dict, list, dict]:
    animations = read_csv(ROOT / "sprite/index/sprite_animations.csv")
    animation = next(r for r in animations if r["animation_id"] == "0x6110")
    families = [r for r in read_csv(ROOT / "sprite/index/sprite_families.csv")
                if r["animation_id"] == "0x6110"]
    loaded, frames, occurrences, sources = {}, {}, [], {}

    def resource(prefix: str, resref: str):
        if prefix not in loaded:
            family = next(r for r in families if r["bam_prefix"] == prefix)
            directory = family_directory(family, animation)
            _, rr, _ = load_source_frames(directory / "source/manifest.json")
            loaded[prefix] = (directory, rr)
        rr = next(r for r in loaded[prefix][1] if r["source"]["name"].upper() == resref)
        if resref not in sources:
            raw = rr["bam_path"].read_bytes()
            if rr["cycles"] != bam_cycles(raw) or any(
                    idx >= len(rr["frames"]) for cyc in rr["cycles"] for idx in cyc["frame_indices"]):
                raise ValueError(f"cycle topology differs: {resref}")
            sources[resref] = {"canonical_bam": rr["bam_path"].relative_to(ROOT).as_posix(),
                               "sha256": sha256_file(rr["bam_path"]), "cycles": rr["cycles"]}
        return rr

    def add(rr, idx, *, layer, group, sequence, slot, dwell):
        frame = rr["frames"][idx]
        if frame.transparent != 0 or frame.width * frame.height <= 1:
            raise ValueError("unexpected special frame in corpus")
        key = f"{frame.resref}_{idx:04d}"
        frames.setdefault(key, frame)
        occurrences.append({"key": key, "layer": layer, "group": group,
                            "sequence": sequence, "slot": slot, "dwell_slots": dwell})

    idle = resource("CHFF4", "CHFF4G12")["cycles"][18]["frame_indices"]
    positions = [s for s in range(len(idle)) if s == 0 or idle[s] != idle[s-1]]
    if len(positions) != 20:
        raise ValueError("E3b requires 20 consecutive idle poses")
    for layer, prefix, idle_name, walk_name in (
            ("body", "CHFF4", "CHFF4G12", "CHFF4G11"),
            ("helmet", "WQNJ6", "WQNJ6G1", "WQNJ6G1"),
            ("shield", "WQND3", "WQND3G1", "WQND3G1"),
            ("weapon", "WQNS1", "WQNS1G1", "WQNS1G1")):
        rr = resource(prefix, idle_name)
        seq = rr["cycles"][18]["frame_indices"]
        if len(seq) != len(idle):
            raise ValueError("layer idle lookup lengths differ")
        for n, slot in enumerate(positions):
            end = positions[n+1] if n+1 < len(positions) else len(idle)
            add(rr, seq[slot], layer=layer, group="E3b", sequence="idle_s", slot=slot, dwell=end-slot)
        rr = resource(prefix, walk_name)
        for slot, idx in enumerate(rr["cycles"][0]["frame_indices"][:10]):
            add(rr, idx, layer=layer, group="E3b", sequence="walk_s", slot=slot, dwell=1)
    for prefix in ("CHFB1", "CHFB2", "CHFB3", "CHFF4"):
        rr = resource(prefix, prefix+"A1")
        idx = rr["cycles"][3]["frame_indices"][0]
        add(rr, idx, layer="body", group="Codex", sequence="armor_pose", slot=0, dwell=1)
    for layer, prefix in (("body", "CHFB1"), ("weapon", "WQNS0"),
                          ("shield", "WQNC0"), ("helmet", "WQNJ6")):
        rr = resource(prefix, prefix+"A1")
        seq = rr["cycles"][0]["frame_indices"]
        if len(seq) != 14:
            raise ValueError("Codex requires 14 attack slots")
        for slot, idx in enumerate(seq):
            add(rr, idx, layer=layer, group="Codex", sequence="attack_s", slot=slot, dwell=1)
    if len(occurrences) != 180:
        raise ValueError("180 corpus occurrences required")
    return loaded["CHFF4"][0].parent, frames, occurrences, sources


def aligned_slices(shape_a, shape_b, center_a, center_b, scale):
    ox, oy = [(int(a)-int(b))*scale for a, b in zip(center_a, center_b, strict=True)]
    ha, wa = shape_a[:2]
    hb, wb = shape_b[:2]
    x0, y0 = max(0, ox), max(0, oy)
    x1, y1 = min(wa, wb+ox), min(ha, hb+oy)
    if x1 <= x0 or y1 <= y0:
        return None
    return ((slice(y0, y1), slice(x0, x1)),
            (slice(y0-oy, y1-oy), slice(x0-ox, x1-ox)))


def masks(guide) -> dict:
    return {"visible": guide != 0, "recolorable": guide >= 4, "shadow": guide == 1}


def color_errors(rendered, target, guide) -> dict:
    error = np.linalg.norm(srgb_u8_to_oklab(rendered)-srgb_u8_to_oklab(target*255), axis=-1)
    return {name: {"pixels": int(mask.sum()), "sum": float(error[mask].sum()),
                   "mean": float(error[mask].mean()) if mask.any() else None}
            for name, mask in masks(guide).items()}


def temporal_pair(guide_a, guide_b, target_a, target_b, render_a, render_b,
                  center_a, center_b, scale) -> dict:
    return temporal_pair_labs(guide_a, guide_b, srgb_u8_to_oklab(target_a*255),
        srgb_u8_to_oklab(target_b*255), srgb_u8_to_oklab(render_a),
        srgb_u8_to_oklab(render_b), center_a, center_b, scale)


def temporal_pair_labs(guide_a, guide_b, target_a, target_b, render_a, render_b,
                       center_a, center_b, scale) -> dict:
    slices = aligned_slices(guide_a.shape, guide_b.shape, center_a, center_b, scale)
    if slices is None:
        return {mask: {"static_pixels": 0, "changed_pixels": 0} for mask in masks(guide_a)}
    sa, sb = slices
    target_delta = np.linalg.norm(target_a[sa]-target_b[sb], axis=-1)
    render_delta = np.linalg.norm(render_a[sa]-render_b[sb], axis=-1)
    result = {}
    for name in masks(guide_a):
        static = masks(guide_a)[name][sa] & masks(guide_b)[name][sb] & (target_delta < .01)
        result[name] = {"static_pixels": int(static.sum()),
                        "changed_pixels": int(np.count_nonzero(static & (render_delta > .02)))}
    return result


def evaluate(frames, occurrences, plan, palettes, refs, output):
    fit_names = [r["name"] for r in plan if r["role"] == "fit"]
    fitting = np.stack([palettes[name] for name in fit_names])
    weights = defaultdict(int)
    for occurrence in occurrences:
        weights[occurrence["key"]] += 1
    roles = {r["name"]: r["role"] for r in plan}
    color_rows, size_rows, checks = [], [], defaultdict(int)
    methods = ["xBR", "Q0"] + [f"{m}-k{k}" for k in KS for m in ("Q6", "Q3m")]
    with WindowsXpressHuffCodec(compress=True) as compressor:
        for number, (key, frame) in enumerate(frames.items(), 1):
            targets = {}
            for name in palettes:
                with np.load(output / refs[name][key], allow_pickle=False) as data:
                    targets[name] = {s: data[f"x{s}"] for s in (2, 4)}
            for scale in (2, 4):
                with np.load(output / "guides" / f"{key}-x{scale}.npz", allow_pickle=False) as data:
                    guide = data["guide"]
                variants = encode_variants(guide, np.stack([targets[n][scale] for n in fit_names]), fitting)
                q0, _ = quantize_classed_oklab(
                    np.rint(targets["REF"][scale]*255).astype(np.uint8), guide, palettes["REF"],
                    np.unique(frame.indices), character_chmb1_classes(), transparent_index=0)
                variants.update({"xBR": {"I": guide, "F": np.zeros_like(guide)},
                                 "Q0": {"I": q0, "F": np.zeros_like(q0)}})
                arrays = {}
                for method in methods:
                    v = variants[method]
                    dep = dependency_mask(v["I"], v["F"])
                    contract = check_contract(guide, v["I"], v["F"], dep)
                    for label in ("class_leaks", "changed_specials", "fractional_pixels"):
                        checks[label] += contract[label]
                    arrays[f"{method}_I"], arrays[f"{method}_F"], arrays[f"{method}_dep"] = v["I"], v["F"], dep
                    ib = v["I"].tobytes()
                    fb = v["F"].tobytes() if np.any(v["F"]) else b""
                    ic, fc = compressor.encode(ib), compressor.encode(fb) if fb else b""
                    size_rows.append({"key": key, "scale": scale, "method": method,
                                      "occurrences": weights[key], "I_raw": len(ib), "F_raw": len(fb),
                                      "I_xpress": len(ic), "F_xpress": len(fc),
                                      "stored_plane_bytes": min(len(ib), len(ic))+min(len(fb), len(fc)),
                                      "dep_mask_bytes": 32 if method.startswith(("Q6", "Q3m")) else 0})
                    for name, palette in palettes.items():
                        metrics = color_errors(decode(v["I"], v["F"], palette), targets[name][scale], guide)
                        for mask, measured in metrics.items():
                            color_rows.append({"key": key, "scale": scale, "method": method,
                                               "palette": name, "role": roles[name], "mask": mask,
                                               "occurrences": weights[key], **measured})
                save_npz(output / "encoded" / f"{key}-x{scale}.npz", **arrays)
            print(f"encoded {number}/{len(frames)} {key}", flush=True)
    return color_rows, size_rows, dict(checks), methods


def summarize_colors(rows) -> list:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["scale"], row["method"], row["palette"], row["role"], row["mask"])].append(row)
    summaries = []
    for (scale, method, palette, role, mask), group in grouped.items():
        pixels = sum(r["pixels"]*r["occurrences"] for r in group)
        total = sum(r["sum"]*r["occurrences"] for r in group)
        supported = [r for r in group if r["pixels"]]
        mean = sum(r["mean"]*r["occurrences"] for r in supported)/sum(r["occurrences"] for r in supported) if supported else None
        summaries.append({"scale": scale, "method": method, "palette": palette,
                          "role": role, "mask": mask, "pixels": pixels,
                          "pixel_weighted_mean": total/pixels if pixels else None,
                          "frame_unweighted_mean": mean})
    lookup = {(r["scale"], r["method"], r["palette"], r["mask"]): r for r in summaries}
    for row in summaries:
        baseline = lookup[(row["scale"], "Q0", row["palette"], row["mask"])]["pixel_weighted_mean"]
        row["gain_vs_Q0_percent"] = 100*(1-row["pixel_weighted_mean"]/baseline) if baseline else None
    return summaries


def temporal_eval(frames, occurrences, palettes, refs, output, methods):
    rows = []
    sequences = defaultdict(list)
    for occurrence in occurrences:
        if occurrence["sequence"] != "armor_pose":
            sequences[(occurrence["group"], occurrence["layer"], occurrence["sequence"])].append(occurrence)
    for (group, layer, sequence), items in sequences.items():
        for scale in (2, 4):
            guides, encoded = {}, {}
            for item in items:
                key = item["key"]
                with np.load(output / "guides" / f"{key}-x{scale}.npz", allow_pickle=False) as data:
                    guides[key] = data["guide"]
                with np.load(output / "encoded" / f"{key}-x{scale}.npz", allow_pickle=False) as data:
                    encoded[key] = {m: (data[f"{m}_I"], data[f"{m}_F"]) for m in methods}
            # Native slots preserve relative dwell only; actual seconds are unmeasured.
            timelines = {"distinct_poses": items,
                         "lookup_slots": [item for item in items for _ in range(item["dwell_slots"]) ]}
            for name, palette in palettes.items():
                targets = {}
                for item in items:
                    key = item["key"]
                    with np.load(output / refs[name][key], allow_pickle=False) as data:
                        targets[key] = srgb_u8_to_oklab(data[f"x{scale}"]*255)
                for method in methods:
                    renders = {key: srgb_u8_to_oklab(decode(*v[method], palette)) for key, v in encoded.items()}
                    pair_cache = {}
                    for timing, timeline in timelines.items():
                        totals = {mask: [0, 0] for mask in masks(next(iter(guides.values())))}
                        seam = None
                        for n, a in enumerate(timeline):
                            b = timeline[(n+1) % len(timeline)]
                            ka, kb = a["key"], b["key"]
                            fa, fb = frames[ka], frames[kb]
                            if (ka, kb) not in pair_cache:
                                pair_cache[ka, kb] = temporal_pair_labs(
                                    guides[ka], guides[kb], targets[ka], targets[kb],
                                    renders[ka], renders[kb], (fa.center_x, fa.center_y),
                                    (fb.center_x, fb.center_y), scale)
                            pair = pair_cache[ka, kb]
                            for mask, counts in pair.items():
                                totals[mask][0] += counts["static_pixels"]
                                totals[mask][1] += counts["changed_pixels"]
                            if n == len(timeline)-1:
                                seam = pair
                        for mask, (support, changed) in totals.items():
                            rows.append({"group": group, "layer": layer, "sequence": sequence,
                                         "scale": scale, "palette": name, "method": method,
                                         "timing": timing, "mask": mask, "pairs": len(timeline),
                                         "static_pixels": support, "changed_pixels": changed,
                                         "ratio": changed/support if support else None,
                                         "seam_static_pixels": seam[mask]["static_pixels"],
                                         "seam_changed_pixels": seam[mask]["changed_pixels"]})
    return rows


def summarize_temporal(rows) -> list:
    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["scale"], row["method"], row["palette"], row["timing"], row["mask"])].append(row)
    result = []
    for (scale, method, palette, timing, mask), group in grouped.items():
        support = sum(r["static_pixels"] for r in group)
        changed = sum(r["changed_pixels"] for r in group)
        ratios = [r["ratio"] for r in group if r["ratio"] is not None]
        result.append({"scale": scale, "method": method, "palette": palette, "timing": timing,
                       "mask": mask, "static_pixels": support, "changed_pixels": changed,
                       "pixel_weighted_ratio": changed/support if support else None,
                       "sequence_unweighted_ratio": float(np.mean(ratios)) if ratios else None})
    return result


def choose_k(summary) -> dict:
    result = {}
    for scale in (2, 4):
        by_method = defaultdict(list)
        for row in summary:
            if row["scale"] == scale and row["mask"] == "recolorable" and row["role"] == "validation":
                by_method[row["method"]].append(row)
        scores = {k: float(np.mean([r["pixel_weighted_mean"] for r in by_method[f"Q3m-k{k}"]])) for k in KS}
        best = min(scores.values())
        eligible = [k for k in KS if all(r["gain_vs_Q0_percent"] > 0 for r in by_method[f"Q3m-k{k}"]) and
                    scores[k] <= best*1.02]
        result[str(scale)] = {"selected_k": min(eligible) if eligible else None,
            "scores": scores, "best_score": best,
            "all_palettes_improved": {k: all(r["gain_vs_Q0_percent"] > 0 for r in by_method[f"Q3m-k{k}"]) for k in KS},
            "criterion": "recolorable pixel-weighted mean on EACH of 10 disjoint palettes; smallest K within 2% of best"}
    return result


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def previews(frames, palettes, refs, output, decisions):
    key = "CHFF4A1_0045"
    if key not in frames:
        key = next(iter(frames))
    scale = 2
    k = decisions["2"]["selected_k"] or min(KS, key=lambda n: decisions["2"]["scores"][n])
    methods = ["xBR", "Q0", f"Q6-k{k}", f"Q3m-k{k}"]
    frame = frames[key]
    with np.load(output / "guides" / f"{key}-x{scale}.npz", allow_pickle=False) as data:
        guide = data["guide"]
    with np.load(output / "encoded" / f"{key}-x{scale}.npz", allow_pickle=False) as data:
        encoded = {m: (data[f"{m}_I"], data[f"{m}_F"]) for m in methods}
    names = ["REF", "DEFAULT", "VAL01", "VAL09", "VAL10", "LEGACY_D"]
    cell_w, cell_h = guide.shape[1]*3+20, guide.shape[0]*3+36
    sheet = Image.new("RGB", (120+len(methods)*cell_w, 38+len(names)*cell_h), (26, 29, 34))
    draw = ImageDraw.Draw(sheet)
    draw.text((8, 8), f"P1 {key} x2; same logical size; nearest enlargement x3", fill="white")
    for row, name in enumerate(names):
        draw.text((8, 45+row*cell_h), name, fill="white")
        for col, method in enumerate(methods):
            rgb = decode(*encoded[method], palettes[name])
            alpha = np.where(guide == 0, 0, np.where(guide == 1, 128, 255)).astype(np.uint8)
            tile = Image.fromarray(np.dstack((rgb, alpha)), "RGBA").resize(
                (guide.shape[1]*3, guide.shape[0]*3), Image.Resampling.NEAREST)
            x, y = 120+col*cell_w, 38+row*cell_h
            draw.text((x, y), method, fill="white")
            sheet.paste(tile, (x, y+20), tile)
    sheet.save(output / "comparison-x2.png")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    started = time.perf_counter()
    workspace, frames, occurrences, sources = corpus()
    output = (args.output or workspace / "research/palette-q3m-p1-20260930-v1").resolve()
    relative = output.relative_to(ROOT / "sprite/families")
    if "research" not in relative.parts:
        raise ValueError("experiment output must be in a family research directory")
    if (output / "result.json").exists():
        raise FileExistsError("completed experiment is immutable; use a new version")
    if output.exists() and not args.resume:
        raise FileExistsError("existing experiment requires --resume")
    output.mkdir(parents=True, exist_ok=True)
    raw, identities = native_resources()
    plan, palettes, palette_checks = palette_plan(raw)
    context = inference_context()
    definition = {"schema": "bg2-upscale-character-palette-p1-v1", "animation_id": "0x6110",
                  "class_profile": CLASS_PROFILE, "decode_rule": DECODE_RULE, "encoder": ENCODER_ID,
                  "ks": list(KS), "palette_weights": "equal", "palettes": plan,
                  "palette_checks": palette_checks, "native_resources": identities,
                  "sources": sources, "occurrences": occurrences,
                  "frames": {key: {"resref": f.resref, "frame": f.index,
                  "size": [f.width, f.height], "center": [f.center_x, f.center_y]}
                  for key, f in frames.items()}, "inference": context,
                  "code_sha256": {name: sha256_file(Path(__file__).parent / name) for name in
                  ("palette_eval.py", "palette_frac_encode.py", "reboutcx_multipal.py")},
                  "timing": "lookup repetitions retained; native frame-step seconds unknown",
                  "scope": "offline only; logical I/F, no V6 binary, installation or release"}
    definition_path = output / "experiment.json"
    if definition_path.exists():
        if json.loads(definition_path.read_text(encoding="utf-8")) != definition:
            raise ValueError("resume experiment definition differs; use a new version")
    else:
        write_json(definition_path, definition)
    print(f"corpus {len(occurrences)} occurrences / {len(frames)} unique BAM frames; {len(plan)} palettes", flush=True)
    guides = prepare_guides(frames, output)
    refs, inference = infer_targets(frames, palettes, output, context)
    write_json(output / "target-index.json", {"references": refs, "inference": inference, "guides": guides})
    colors, sizes, checks, methods = evaluate(frames, occurrences, plan, palettes, refs, output)
    color_summary = summarize_colors(colors)
    temporal = temporal_eval(frames, occurrences, palettes, refs, output, methods)
    temporal_summary = summarize_temporal(temporal)
    decisions = choose_k(color_summary)
    previews(frames, palettes, refs, output, decisions)
    for name, rows in (("color-frames", colors), ("color-summary", color_summary),
                       ("sizes", sizes), ("temporal-sequences", temporal),
                       ("temporal-summary", temporal_summary)):
        write_csv(output / f"{name}.csv", rows)
    size_summary = {}
    for scale in (2, 4):
        size_summary[str(scale)] = {method: {label: sum(r[label]*r["occurrences"] for r in sizes
            if r["scale"] == scale and r["method"] == method)
            for label in ("I_raw", "F_raw", "I_xpress", "F_xpress", "stored_plane_bytes", "dep_mask_bytes")}
            for method in methods}
    result = {"schema": "bg2-upscale-character-palette-p1-result-v1",
              "created_utc": datetime.now(timezone.utc).isoformat(),
              "occurrences": len(occurrences), "unique_bam_frames": len(frames),
              "checks": checks, "palette_checks": palette_checks, "decisions": decisions,
              "p1_pass": all(r["selected_k"] is not None for r in decisions.values()),
              "inference": inference, "size_summary": size_summary,
              "size_scope": "real per-plane XPRESS_HUFF; min(raw,xpress) storage; dep_mask raw 32B; V6 header/representatives excluded",
              "metric": "OKLab Euclidean mean vs float ReboutCX target; recolorable primary; visible/shadow published separately",
              "temporal": "correct anchor sign; distinct and native lookup slots; seam included; no optical flow or measured seconds",
              "historical": "new P12 float/integer-Q3 protocol; historical E3b results not overwritten or claimed reproduced",
              "runtime_golden_tests": "Python/C++ comparison deferred to P2; no DLL changed",
              "qa_ingame": "not performed", "wall_seconds": time.perf_counter()-started}
    write_json(output / "result.json", result)
    print(json.dumps({"output": str(output), "p1_pass": result["p1_pass"], "decisions": decisions}, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
