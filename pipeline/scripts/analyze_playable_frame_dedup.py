"""Exact indexed-frame work plan for all inventoried playable Characters.

CPU-only source analysis. Creates a fresh SQLite plan, never invokes upscale,
changes a producer, installs assets or assigns QA. `verify` opens it read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import time
import zlib

import numpy as np

from palette_oracle import read_bam_p8

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "playable-palettized-exact-frame-plan-v1"
INPUT_DOMAIN = b"BG2-INDEXED-FRAME-INPUT-v1\0"
WORK_DOMAIN = b"BG2-Q3M-USED-NATIVE-RGB-WORK-v1\0"
ANCHOR = (ROOT / "sprite/families/playable-characters/6110-human-female-fighter/research"
          / "palette-q3m-p3-20261001-v5-full-x4-6110/recipe.json")
GOLDEN = (ANCHOR.parent.parent / "palette-q3m-p1-20260930-v1/decoder-golden.npz")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def identities(indices, palette_rgb, transparent):
    """Full indexed raster + geometry; guide identity adds only RGB actually read.

    Cycles, centres, resource names, model, item and layer do not affect pixels.
    BAM's fourth palette byte is ignored: production derives alpha from index.
    Used transparent RGB is retained, because xBR receives its actual RGBA bytes.
    No crop, mirror, rotation, index remap or tolerance is applied.
    """
    require(indices.dtype == np.uint8 and indices.ndim == 2, "indexed u8 plane required")
    require(palette_rgb.dtype == np.uint8 and palette_rgb.shape == (256, 3), "RGB palette required")
    require(0 <= transparent <= 255, "invalid transparent index")
    h, w = indices.shape
    payload = np.ascontiguousarray(indices).tobytes()
    header = struct.pack("<IIB", w, h, transparent)
    input_key = hashlib.sha256(INPUT_DOMAIN + header + payload).digest()
    used = np.flatnonzero(np.bincount(indices.ravel(), minlength=256)).astype(np.uint8)
    used_rgb = np.column_stack((used, palette_rgb[used])).astype(np.uint8).tobytes()
    work_key = hashlib.sha256(WORK_DOMAIN + input_key + used_rgb).digest()
    special = (not payload or not np.any(indices != transparent)
               or (w == h == 1 and payload == b"\x02"))
    return input_key, work_key, payload, used_rgb, not special


DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE models(model_id INTEGER PRIMARY KEY,animation_id TEXT UNIQUE NOT NULL,
 symbol TEXT NOT NULL,source_json TEXT NOT NULL);
CREATE TABLE families(family_id TEXT PRIMARY KEY,model_id INTEGER NOT NULL REFERENCES models,
 layer TEXT NOT NULL,variant_kind TEXT NOT NULL,variant_value TEXT NOT NULL,
 bam_prefix TEXT NOT NULL,source_status TEXT NOT NULL,source_json TEXT NOT NULL) WITHOUT ROWID;
CREATE TABLE resources(resource_id INTEGER PRIMARY KEY,resref TEXT UNIQUE NOT NULL,
 canonical_path TEXT NOT NULL,source_path TEXT NOT NULL,canonical_sha256 TEXT NOT NULL,
 source_sha256 TEXT NOT NULL,palette_bgra BLOB NOT NULL,rgb_palette_sha256 TEXT NOT NULL,
 transparent_index INTEGER NOT NULL,frame_count INTEGER NOT NULL,cycle_count INTEGER NOT NULL,
 cycle_slot_count INTEGER NOT NULL,source_json TEXT NOT NULL);
CREATE TABLE family_resources(family_id TEXT NOT NULL REFERENCES families,
 resource_id INTEGER NOT NULL REFERENCES resources,PRIMARY KEY(family_id,resource_id)) WITHOUT ROWID;
CREATE TABLE model_resources(model_id INTEGER NOT NULL REFERENCES models,
 resource_id INTEGER NOT NULL REFERENCES resources,PRIMARY KEY(model_id,resource_id)) WITHOUT ROWID;
CREATE TABLE inputs(input_id INTEGER PRIMARY KEY,input_key BLOB UNIQUE NOT NULL,
 width INTEGER NOT NULL,height INTEGER NOT NULL,transparent_index INTEGER NOT NULL,
 native_pixels INTEGER NOT NULL,padded_width INTEGER NOT NULL,padded_height INTEGER NOT NULL,
 needs_model INTEGER NOT NULL,current_q3m_processable INTEGER NOT NULL,indices_zlib BLOB NOT NULL);
CREATE TABLE work_items(work_id INTEGER PRIMARY KEY,work_key BLOB UNIQUE NOT NULL,
 input_id INTEGER NOT NULL REFERENCES inputs,used_native_rgb BLOB NOT NULL,
 representative_resource_id INTEGER NOT NULL REFERENCES resources,
 representative_frame_index INTEGER NOT NULL,
 source_occurrences INTEGER NOT NULL DEFAULT 0,model_occurrences INTEGER NOT NULL DEFAULT 0,
 consumer_model_count INTEGER NOT NULL DEFAULT 0,consumer_models_le_bitset BLOB,
 different_centres INTEGER NOT NULL DEFAULT 0);
CREATE TABLE frames(resource_id INTEGER NOT NULL REFERENCES resources,frame_index INTEGER NOT NULL,
 work_id INTEGER NOT NULL REFERENCES work_items,center_x INTEGER NOT NULL,center_y INTEGER NOT NULL,
 original_rle INTEGER NOT NULL,rle_tail_overflow INTEGER NOT NULL,cycle_referenced INTEGER NOT NULL,
 PRIMARY KEY(resource_id,frame_index)) WITHOUT ROWID;
CREATE TABLE cycles(resource_id INTEGER NOT NULL REFERENCES resources,cycle_index INTEGER NOT NULL,
 lookup_start INTEGER NOT NULL,slot_count INTEGER NOT NULL,frame_indices_le_u16 BLOB NOT NULL,
 PRIMARY KEY(resource_id,cycle_index)) WITHOUT ROWID;
CREATE TABLE profile_palettes(palette_ordinal INTEGER PRIMARY KEY,name TEXT NOT NULL,
 rgb_u8_256x3 BLOB NOT NULL,sha256 TEXT NOT NULL);
CREATE TABLE model_statistics(model_id INTEGER PRIMARY KEY REFERENCES models,statistics_json TEXT NOT NULL);
CREATE VIEW frame_map AS SELECT m.animation_id,f.family_id,f.layer,f.variant_kind,f.variant_value,
 r.resref,fr.frame_index,fr.center_x,fr.center_y,fr.cycle_referenced,fr.work_id,
 w.input_id,lower(hex(w.work_key)) AS work_key,i.width,i.height,i.transparent_index,
 r.source_sha256,r.canonical_sha256,r.canonical_path
 FROM families f JOIN models m USING(model_id) JOIN family_resources fa USING(family_id)
 JOIN resources r USING(resource_id) JOIN frames fr USING(resource_id)
 JOIN work_items w USING(work_id) JOIN inputs i USING(input_id);
CREATE VIEW processing_queue AS SELECT w.work_id,lower(hex(w.work_key)) AS work_key,w.input_id,
 i.width,i.height,i.transparent_index,i.needs_model,i.current_q3m_processable,
 i.padded_width,i.padded_height,i.indices_zlib,r.palette_bgra,w.used_native_rgb,
 r.resref AS representative_resref,w.representative_frame_index,r.canonical_path,
 r.source_sha256,r.canonical_sha256,w.source_occurrences,w.model_occurrences,w.consumer_model_count
 FROM work_items w JOIN inputs i USING(input_id)
 JOIN resources r ON r.resource_id=w.representative_resource_id;
CREATE VIEW neural_queue AS SELECT input_id,lower(hex(input_key)) AS input_key,width,height,
 padded_width,padded_height,transparent_index,indices_zlib FROM inputs
 WHERE needs_model=1 AND current_q3m_processable=1;
CREATE VIEW absent_families AS SELECT m.animation_id,f.family_id,f.layer,f.variant_value,f.bam_prefix
 FROM families f JOIN models m USING(model_id) WHERE f.source_status='no-native-bam';
"""


def put_meta(db, key, value):
    db.execute("INSERT INTO metadata VALUES(?,?)", (key, dump(value)))


def load_inventory(root):
    index = root / "sprite/index"
    animations = rows(index / "sprite_animations.csv")
    models = sorted((x for x in animations if x["engine_section"] == "character"),
                    key=lambda x: int(x["animation_id"], 16))
    require(models and all(x["false_color"] == "1" for x in models), "Character scope is not all palettized")
    require(all(x["runtime_profile"] == "character-bg2ee-2.7.3.0" for x in models), "mixed class profiles")
    mids = {x["animation_id"]: i for i, x in enumerate(models)}
    families = {x["family_id"]: x for x in rows(index / "sprite_families.csv") if x["animation_id"] in mids}
    resources = []
    for x in rows(index / "sprite_resources.csv"):
        owners = sorted(set(x["family_ids"].split(";")) & families.keys())
        if owners:
            require(x["bam_version"] == "V1" and x["decode_status"] == "ok", f"unsupported source {x['bam_resref']}")
            require(x["override_collision"] in ("", "no") and not x["blocker"], f"source blocker {x['bam_resref']}")
            derived = {families[f]["animation_id"] for f in owners}
            require(derived == set(x["animation_ids"].split(";")) & mids.keys(), "model/family membership disagrees")
            resources.append((x, owners))
    extractions = {x["bam_resref"]: x for x in rows(index / "extractions.csv")}
    for x, _ in resources:
        e = extractions[x["bam_resref"]]
        require(e["extraction_state"] == "verified", "unverified extraction")
        for field in ("source_sha256", "canonical_sha256"):
            require(e[field].lower() == x[field].lower(), "extraction/inventory hash differs")
        require((root / e["canonical_file"]).is_file(), f"missing canonical {x['bam_resref']}")
        require((root / e["source_file"]).is_file(), f"missing stock container {x['bam_resref']}")
    excluded = dict(
        other_sections=[{k: x[k] for k in ("animation_id", "ids_symbol", "engine_section", "false_color")}
                        for x in animations if x["engine_section"] == "character_old"],
        inventory_paperdoll_ui_resources=sorted({p for x in families.values()
                                               for p in x["paperdoll_resources"].split(";") if p}),
        note="Scope: all engine_section=character / false_color=1 animated assets, including LOW aliases and equipment. "
             "character_old NPC/legacy models and static inventory paperdolls are different domains; not processed by this Q3m Character plan.")
    return models, mids, families, sorted(resources, key=lambda v: v[0]["bam_resref"]), extractions, excluded


def profile(root):
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    require((anchor["method"], anchor["k"], anchor["boundary_mixing"], anchor["dithering"]) ==
            ("Q3m", 6, False, False), "unexpected current recipe")
    require(sha(GOLDEN.read_bytes()) == "12171974b2df6423b928b880529fa277bf5ee7517e278d8d9554efa762910e4b", "golden changed")
    with np.load(GOLDEN, allow_pickle=False) as z:
        fitting = z["palettes_rgba"][:6, :, :3].copy()
    fitting[:, 0] = (0, 255, 0)
    scripts = ["palette_complete.py", "palette_frac_encode.py", "reboutcx_quantize.py",
               "run_creature_sprite_x2.py", "xbr2x_batch.js", "reboutcx_batch.py",
               "reboutcx_batch_p10.py", "reboutcx_batch_p12.py", "reboutcx_multipal.py"]
    kernels = {name: sha((root / "pipeline/scripts" / name).read_bytes()) for name in scripts}
    for name, expected in anchor["inference"]["kernels"].items():
        require(kernels[name] == expected, f"anchor inference kernel changed: {name}")
    config = json.loads((root / "config/workspace-paths.local.json").read_text(encoding="utf-8-sig"))
    scalepix = Path(config["paths"]["mmpx_scalepix"])
    value = dict(method="Q3m", k=6, fractions=list(range(8)), boundary_mixing=False, dithering=False,
                 class_profile="character-bg2ee-2.7.3.0", decode_rule="ramp-lerp-srgb8-v1",
                 palette_names=[p["name"] for p in anchor["palettes"]], equal_weights=True,
                 fitting_rgb_sha256=sha(fitting.tobytes()), inference=anchor["inference"],
                 code_sha256=kernels, scalepix_sha256=sha(scalepix.read_bytes()),
                 guide="native used-RGB RGBA xBR2X/xBR4X; no blend; native indexed provenance",
                 identity="scale/profile namespace + work_key; never work_key alone",
                 neural_identity="inference/fitting namespace + input_key; six fitting palettes; optional two-stage reuse",
                 output_scale_rules={"2": "xBR2X guide + BOX float32 neural x4 to x2",
                                     "4": "xBR4X guide + direct float32 neural x4"})
    value["namespace_by_scale"] = {str(s): sha(dump(value).encode() + bytes([s])) for s in (2, 4)}
    return value, fitting


def scan(destination):
    start = time.perf_counter()
    destination = destination.resolve()
    destination.relative_to(ROOT / "docs/measurements")
    require(not destination.exists(), "fresh output directory required; existing analysis is immutable")
    models, mids, families, resources, extractions, excluded = load_inventory(ROOT)
    recipe, fitting = profile(ROOT)
    pin_paths = [ROOT / "sprite/index" / n for n in
                 ("sprite_animations.csv", "sprite_families.csv", "sprite_resources.csv", "extractions.csv", "manifest.json")]
    pin_paths += [Path(__file__), ROOT / "pipeline/scripts/palette_oracle.py", ANCHOR, GOLDEN]
    pins = {p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in pin_paths}
    destination.mkdir(parents=True)
    path = destination / "processing-plan.sqlite"
    db = sqlite3.connect(path)
    db.executescript(DDL)
    db.execute("PRAGMA cache_size=-131072")
    put_meta(db, "schema", SCHEMA)
    put_meta(db, "status", "source-analysis-in-progress")
    put_meta(db, "source_root", str(ROOT))
    put_meta(db, "source_pins", pins)
    put_meta(db, "profile", recipe)
    put_meta(db, "excluded_scope", excluded)
    put_meta(db, "contract", dict(
        input_key="sha256(INPUT_DOMAIN + LE uint32 width,height + uint8 transparent + row-major indices)",
        work_key="sha256(WORK_DOMAIN + 32-byte input_key + sorted used [index,R,G,B] bytes)",
        input_domain=INPUT_DOMAIN.decode().rstrip("\0"), work_domain=WORK_DOMAIN.decode().rstrip("\0"),
        indices_codec="zlib; uint8 [height,width]; never a PNG/RGB quantization",
        used_native_rgb="4-byte records: index,R,G,B; ascending indices; includes transparent if used",
        palette_bgra="original 256x4 BAM palette; RGB=BGRA[:,[2,1,0]], alpha synthesized from transparent index",
        cycles="LE uint16 frame indices; original sequence order, slot count and lookup_start retained",
        model_bitset="little-endian; bit position=models.model_id",
        centres="per frames row at native x1; never taken from work representative",
        consumption="one work_items row per common profile/scale; decode indices_zlib and representative native palette; "
                    "persist encoded I/F/dep by namespace+work_key, then fan out via frame_map; "
                    "retain each resource identity, centres and cycles; no cache-eviction-driven recomputation",
        completion="processing_queue is an exhaustive task list, not a modified production runner or completed upscale",
        batching="group padded_width,height; pinned fixed86/q32/fp16 and filler rule; scale2/4 outputs are distinct",
        runtime="reuse encoded indexed I/F only; owner/layer palette snapshots, colored pixels and runtime cache remain independent"))
    db.executemany("INSERT INTO models VALUES(?,?,?,?)", [(i, m["animation_id"], m["ids_symbol"], dump(m)) for i, m in enumerate(models)])
    db.executemany("INSERT INTO families VALUES(?,?,?,?,?,?,?,?)", [
        (fid, mids[f["animation_id"]], f["layer_kind"], f["variant_kind"], f["variant_value"], f["bam_prefix"],
         "available" if int(f["resource_count"]) else "no-native-bam", dump(f)) for fid, f in sorted(families.items())])
    db.executemany("INSERT INTO profile_palettes VALUES(?,?,?,?)", [
        (i, recipe["palette_names"][i], p.tobytes(), sha(p.tobytes())) for i, p in enumerate(fitting)])
    input_groups, work_groups, strict_groups = {}, {}, {}
    family_coverage = defaultdict(Counter)
    totals = Counter()
    model_stats = [Counter() for _ in models]
    layer_stats = defaultdict(Counter)
    bit_bytes = (len(models) + 7) // 8
    for rid, (resource, owners) in enumerate(resources):
        ref = resource["bam_resref"]
        extraction = extractions[ref]
        raw = (ROOT / extraction["canonical_file"]).read_bytes()
        require(sha(raw) == resource["canonical_sha256"].lower(), f"canonical hash differs: {ref}")
        stock = (ROOT / extraction["source_file"]).read_bytes()
        require(sha(stock) == resource["source_sha256"].lower(), f"stock hash differs: {ref}")
        bam = read_bam_p8(raw)
        rgb = np.ascontiguousarray(bam["palette_rgb"])
        palette_key = hashlib.sha256(rgb.tobytes()).digest()
        nf, nc = len(bam["frames"]), len(bam["cycles"])
        slots = sum(len(c["frame_indices"]) for c in bam["cycles"])
        require((nf, nc, slots, bam["transparent"]) == tuple(int(resource[k]) for k in
                ("frame_count", "cycle_count", "cycle_slot_count", "transparent_palette_index")), f"inventory counts differ: {ref}")
        db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            rid, ref, extraction["canonical_file"], extraction["source_file"], sha(raw), sha(stock),
            bam["palette_bgra"].tobytes(), palette_key.hex(), bam["transparent"], nf, nc, slots, dump(resource)))
        db.executemany("INSERT INTO family_resources VALUES(?,?)", [(fid, rid) for fid in owners])
        owner_models = sorted({mids[families[f]["animation_id"]] for f in owners})
        mask = sum(1 << i for i in owner_models)
        db.executemany("INSERT INTO model_resources VALUES(?,?)", [(i, rid) for i in owner_models])
        for fid in owners:
            family_coverage[fid].update(resources=1, frames=nf, cycles=nc)
        referenced = set()
        for c in bam["cycles"]:
            referenced.update(c["frame_indices"])
            packed = struct.pack(f"<{len(c['frame_indices'])}H", *c["frame_indices"])
            db.execute("INSERT INTO cycles VALUES(?,?,?,?,?)", (rid, c["index"], c["lookup_start"], len(c["frame_indices"]), packed))
        inserts = []
        resource_native = 0
        for f in bam["frames"]:
            plane = f["indices"]
            ik, wk, payload, used_rgb, model = identities(plane, rgb, bam["transparent"])
            h, w = plane.shape
            native = w * h
            pw, ph = (w + 31) // 32 * 32, (h + 31) // 32 * 32
            padded = pw * ph
            processable = w > 0 and h > 0 and native < 65535 and bam["transparent"] == 0
            old_input = input_groups.get(ik)
            if old_input is None:
                iid = len(input_groups)
                compressed = zlib.compress(payload, 6)
                # Retaining compressed witnesses allows actual equality checks on EVERY reuse,
                # instead of assuming equal hashes prove equal source planes.
                input_groups[ik] = (iid, w, h, bam["transparent"], compressed)
                db.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (
                    iid, ik, w, h, bam["transparent"], native, pw, ph, int(model), int(processable), compressed))
                totals.update(unique_indexed_inputs=1, unique_neural_inputs=int(model),
                              unique_neural_q32_pixels=padded * model,
                              unique_neural_native_pixels=native * model)
            else:
                iid, ow, oh, ot, compressed = old_input
                require((w, h, bam["transparent"]) == (ow, oh, ot) and zlib.decompress(compressed) == payload,
                        "indexed input SHA256 collision")
                totals["input_reuses_byte_compared"] += 1
            group = work_groups.get(wk)
            if group is None:
                wid = len(work_groups)
                group = [wid, iid, used_rgb, mask, 0, 0, (f["center_x"], f["center_y"]), False, model, native, padded]
                work_groups[wk] = group
                db.execute("INSERT INTO work_items(work_id,work_key,input_id,used_native_rgb,representative_resource_id,representative_frame_index) VALUES(?,?,?,?,?,?)",
                           (wid, wk, iid, used_rgb, rid, f["index"]))
                totals.update(unique_work_items=1, unique_model_work_items=int(model),
                              unique_work_native_pixels=native, unique_model_native_pixels=native * model,
                              unique_model_q32_pixels=padded * model, unprocessable_work_items=int(not processable))
            else:
                require(group[1] == iid and group[2] == used_rgb, "guide work SHA256 collision")
                group[3] |= mask
                group[7] |= group[6] != (f["center_x"], f["center_y"])
                totals["work_reuses_byte_compared"] += 1
            wid = group[0]
            group[4] += 1
            group[5] += len(owner_models)
            strict = (ik, palette_key)
            strict_groups[strict] = strict_groups.get(strict, 0) | mask
            inserts.append((rid, f["index"], wid, f["center_x"], f["center_y"], int(f["compressed"]), f["rle_tail_overflow"], int(f["index"] in referenced)))
            resource_native += native
            totals.update(distinct_bam_frames=1, distinct_bam_model_frames=int(model),
                          distinct_bam_native_pixels=native, distinct_bam_model_q32_pixels=padded * model,
                          logical_frames=len(owner_models), logical_model_frames=model * len(owner_models),
                          logical_native_pixels=native * len(owner_models),
                          logical_model_q32_pixels=padded * model * len(owner_models),
                          unreferenced_source_frames=int(f["index"] not in referenced),
                          original_rle_tail_overflow_frames=int(bool(f["rle_tail_overflow"])))
            for mi in owner_models:
                model_stats[mi].update(logical_frames=1, logical_model_frames=int(model),
                                       logical_native_pixels=native, logical_model_q32_pixels=padded * model)
            for layer in {families[fid]["layer_kind"] for fid in owners}:
                layer_stats[layer].update(source_frames=1, source_model_frames=int(model))
        require(resource_native == int(resource["native_pixel_count"]), f"inventory pixel count differs: {ref}")
        db.executemany("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?)", inserts)
        totals.update(resources=1, source_bytes=len(stock), canonical_bytes=len(raw), cycles=nc, cycle_slots=slots)
        for mi in owner_models:
            model_stats[mi]["resources"] += 1
        if (rid + 1) % 100 == 0 or rid + 1 == len(resources):
            db.commit()
            print(dump(dict(phase="scan", resources=rid + 1, total=len(resources),
                            unique_work=len(work_groups), unique_inputs=len(input_groups), seconds=round(time.perf_counter()-start, 2))), flush=True)
    for fid, f in families.items():
        actual = family_coverage[fid]
        require((actual["resources"], actual["frames"], actual["cycles"]) ==
                tuple(int(f[k]) for k in ("resource_count", "frame_count", "cycle_count")), f"family coverage differs: {fid}")
    updates = []
    for group in work_groups.values():
        wid, _, _, mask, count, logical, _, different_centres, model, native, padded = group
        n = mask.bit_count()
        updates.append((count, logical, n, mask.to_bytes(bit_bytes, "little"), int(different_centres), wid))
        totals.update(model_local_unique_work_items=n, model_local_unique_model_work_items=n * model,
                      model_local_unique_model_q32_pixels=n * padded * model,
                      shared_between_models_work_items=int(n > 1),
                      shared_between_models_model_work_items=int(n > 1 and model),
                      shared_between_models_source_occurrences=count * int(n > 1),
                      work_items_with_different_centres=int(different_centres))
        while mask:
            bit = mask & -mask
            mi = bit.bit_length() - 1
            model_stats[mi].update(unique_work_items=1, unique_model_work_items=int(model),
                                   unique_model_q32_pixels=padded * model)
            mask ^= bit
    db.executemany("UPDATE work_items SET source_occurrences=?,model_occurrences=?,consumer_model_count=?,consumer_models_le_bitset=?,different_centres=? WHERE work_id=?", updates)
    totals.update(models=len(models), families=len(families), available_families=sum(int(f["resource_count"]) > 0 for f in families.values()),
                  absent_families=sum(int(f["resource_count"]) == 0 for f in families.values()),
                  strict_full_palette_work_items=len(strict_groups))
    for (_, _), mask in strict_groups.items():
        while mask:
            bit = mask & -mask
            model_stats[bit.bit_length() - 1]["strict_full_palette_work_items"] += 1
            mask ^= bit
    totals["logical_frame_work_avoided"] = totals["logical_frames"] - totals["unique_work_items"]
    totals["logical_model_work_avoided"] = totals["logical_model_frames"] - totals["unique_model_work_items"]
    totals["logical_model_q32_pixels_avoided"] = totals["logical_model_q32_pixels"] - totals["unique_model_q32_pixels"]
    totals["within_model_model_work_avoided"] = totals["logical_model_frames"] - totals["model_local_unique_model_work_items"]
    totals["cross_model_additional_model_work_avoided"] = totals["model_local_unique_model_work_items"] - totals["unique_model_work_items"]
    totals["cross_model_additional_q32_pixels_avoided"] = totals["model_local_unique_model_q32_pixels"] - totals["unique_model_q32_pixels"]
    totals["six_palette_targets_naive"] = totals["logical_model_frames"] * 6
    totals["six_palette_targets_unique_work"] = totals["unique_model_work_items"] * 6
    totals["six_palette_targets_unique_indexed_input"] = totals["unique_neural_inputs"] * 6
    totals["unused_native_palette_additional_work_avoided"] = totals["strict_full_palette_work_items"] - totals["unique_work_items"]
    totals["source_frames_avoided_after_bam_sharing"] = totals["distinct_bam_frames"] - totals["unique_work_items"]
    totals["source_model_frames_avoided_after_bam_sharing"] = totals["distinct_bam_model_frames"] - totals["unique_model_work_items"]
    stats = []
    for mi, m in enumerate(models):
        stat = dict(animation_id=m["animation_id"], symbol=m["ids_symbol"], **model_stats[mi])
        stats.append(stat)
        db.execute("INSERT INTO model_statistics VALUES(?,?)", (mi, dump(stat)))
    existing_test = next(s for s in stats if s["animation_id"] == "0x6110")
    require(existing_test["logical_frames"] == 178360 and existing_test["strict_full_palette_work_items"] == 94099,
            "0x6110 disagrees with the completed Q3m x4 production source/key count")
    def percent(saved, baseline):
        return round(saved * 100 / baseline, 6) if baseline else 0
    summary = dict(schema=SCHEMA, status="complete-source-analysis-not-generated", counts=dict(totals),
                   reductions_percent=dict(
                       all_frame_work=percent(totals["logical_frame_work_avoided"], totals["logical_frames"]),
                       model_frame_work=percent(totals["logical_model_work_avoided"], totals["logical_model_frames"]),
                       model_q32_pixels=percent(totals["logical_model_q32_pixels_avoided"], totals["logical_model_q32_pixels"]),
                       after_distinct_bam_frames=percent(totals["source_frames_avoided_after_bam_sharing"], totals["distinct_bam_frames"]),
                       cross_model_additional_model_work=percent(totals["cross_model_additional_model_work_avoided"], totals["model_local_unique_model_work_items"]),
                       cross_model_additional_q32_pixels=percent(totals["cross_model_additional_q32_pixels_avoided"], totals["model_local_unique_model_q32_pixels"])),
                   layer_source_counts=dict(layer_stats), cross_check_6110=existing_test,
                   seconds=round(time.perf_counter()-start, 3),
                   limitations=["Sufficient identical-input proof, not a search for merely equal-looking images or coincidentally equal future encoded outputs.",
                                "No inference, upscale, install or ingame QA. Existing runners are not automatically redirected to this plan.",
                                "q32 pixels exclude fixed86 filler slots; percentages are work-volume savings, not measured elapsed-time speedups.",
                                "All originally declared frames are retained, including unreferenced and special frames; no dead-frame pruning.",
                                "x2 and x4 encoded results and different processing profiles must use distinct namespaces.",
                                "optional neural_queue avoids repeating neural targets for identical indexed inputs with different native guides; six palettes per input."])
    put_meta(db, "summary", summary)
    for relative, expected in pins.items():
        require(sha((ROOT / relative).read_bytes()) == expected, f"pinned input changed: {relative}")
    db.execute("UPDATE metadata SET value_json=? WHERE key='status'", (dump("complete-source-analysis-not-generated"),))
    db.execute("CREATE INDEX frames_by_work ON frames(work_id)")
    db.execute("CREATE INDEX resources_by_family ON family_resources(resource_id)")
    db.execute("CREATE INDEX resources_by_model ON model_resources(resource_id)")
    db.execute("CREATE INDEX work_by_input ON work_items(input_id)")
    db.commit()
    require(db.execute("PRAGMA integrity_check").fetchall() == [("ok",)], "SQLite integrity failed")
    require(not db.execute("PRAGMA foreign_key_check").fetchall(), "SQLite foreign keys failed")
    db.close()
    summary["artifact"] = dict(path=path.relative_to(ROOT).as_posix(), bytes=path.stat().st_size,
                               sha256=sha(path.read_bytes()))
    (destination / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(dump(summary), flush=True)


def verify(path):
    """Independent second traversal: source, metadata, cycles and every equality."""
    start = time.perf_counter()
    db = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    require(db.execute("PRAGMA integrity_check").fetchall()[0][0] == "ok", "SQLite integrity failed")
    require(not db.execute("PRAGMA foreign_key_check").fetchall(), "foreign key check failed")
    meta = {x["key"]: json.loads(x["value_json"]) for x in db.execute("SELECT * FROM metadata")}
    require(meta["schema"] == SCHEMA and meta["status"] == "complete-source-analysis-not-generated", "unfinished or unsupported plan")
    for relative, expected in meta["source_pins"].items():
        require(sha((ROOT / relative).read_bytes()) == expected, f"source pin changed: {relative}")
    # This production reader is separate from palette_oracle's parser. Importing
    # it does not run an upscale; avoid importing any torch/GPU inference module.
    from bam_export import decode_bam
    counts = Counter()
    expected = meta["summary"]["counts"]
    for resource in db.execute("SELECT * FROM resources ORDER BY resource_id"):
        rid, ref = resource["resource_id"], resource["resref"]
        raw = (ROOT / resource["canonical_path"]).read_bytes()
        require(sha(raw) == resource["canonical_sha256"], f"source changed: {ref}")
        decoded, palette, transparent = decode_bam(raw)
        palette = np.ascontiguousarray(palette)
        require(transparent == resource["transparent_index"], "transparency changed")
        stored_rgb = np.frombuffer(resource["palette_bgra"], np.uint8).reshape(256, 4)[:, [2, 1, 0]]
        require(np.array_equal(palette, stored_rgb), f"independent palette differs: {ref}")
        mapped = db.execute("""SELECT fr.*,w.work_key,w.used_native_rgb,w.input_id,i.*
            FROM frames fr JOIN work_items w USING(work_id) JOIN inputs i USING(input_id)
            WHERE resource_id=? ORDER BY frame_index""", (rid,)).fetchall()
        require(len(mapped) == len(decoded) == resource["frame_count"], f"frame count differs: {ref}")
        frame_offset = struct.unpack_from("<I", raw, 12)[0]
        for fi, (f, row) in enumerate(zip(decoded, mapped, strict=True)):
            source_plane, cx, cy, tr = f
            width, height, declared_cx, declared_cy = struct.unpack_from("<HHhh", raw, frame_offset + fi * 12)
            require((width, height, declared_cx, declared_cy) ==
                    (row["width"], row["height"], row["center_x"], row["center_y"]), f"geometry differs: {ref}/{row['frame_index']}")
            if width and height:
                require(source_plane.shape == (height, width) and (cx, cy, tr) == (declared_cx, declared_cy, transparent), "independent frame metadata differs")
            else:
                # bam_export normalizes zero geometry to 1x1; this work plan retains
                # the declared geometry and empty plane rather than inheriting that normalization.
                source_plane = np.empty((height, width), np.uint8)
            stored_plane = zlib.decompress(row["indices_zlib"])
            require(source_plane.tobytes() == stored_plane, f"indexed pixels differ: {ref}/{row['frame_index']}")
            # Verify the guide RGBA from expanded pixels directly, not by calling
            # identities() again: compare the native colors to the stored used-RGB map.
            records = np.frombuffer(row["used_native_rgb"], np.uint8).reshape(-1, 4)
            reconstructed = np.zeros((256, 3), np.uint8)
            reconstructed[records[:, 0]] = records[:, 1:]
            require(np.array_equal(palette[source_plane], reconstructed[source_plane]), f"used RGB differs: {ref}/{row['frame_index']}")
            require(records[:, 0].tolist() == sorted(set(stored_plane)), "used RGB index coverage differs")
            alpha_source = np.where(source_plane == transparent, 0, 255).astype(np.uint8)
            alpha_stored = np.where(np.frombuffer(stored_plane, np.uint8).reshape(source_plane.shape) == row["transparent_index"], 0, 255).astype(np.uint8)
            require(np.array_equal(alpha_source, alpha_stored), "alpha differs")
            counts["frames_byte_verified_with_independent_reader"] += 1
            counts["native_pixels_byte_verified"] += source_plane.size
        # Read raw cycle tables independently of either decoder's cycle implementation.
        nf, nc = struct.unpack_from("<HB", raw, 8)
        frame_offset, _, lookup_offset = struct.unpack_from("<III", raw, 12)
        cyclic = db.execute("SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index", (rid,)).fetchall()
        require(len(cyclic) == nc, "cycle count differs")
        referenced = set()
        for ci, row in enumerate(cyclic):
            count, first = struct.unpack_from("<HH", raw, frame_offset + nf * 12 + ci * 4)
            original = raw[lookup_offset + first * 2:lookup_offset + (first + count) * 2]
            require((ci, count, first, original) == (row["cycle_index"], row["slot_count"], row["lookup_start"], row["frame_indices_le_u16"]), "cycle or lookup differs")
            referenced.update(struct.unpack(f"<{count}H", original))
            counts["cycle_slots_verified"] += count
        require([int(row["frame_index"] in referenced) for row in mapped] == [row["cycle_referenced"] for row in mapped], "cycle reference status differs")
        counts["resources_independently_decoded"] += 1
        if (rid + 1) % 100 == 0 or rid + 1 == expected["resources"]:
            print(dump(dict(phase="verify", resources=rid + 1, total=expected["resources"], seconds=round(time.perf_counter()-start, 2))), flush=True)
    require(counts["frames_byte_verified_with_independent_reader"] == expected["distinct_bam_frames"], "frame coverage differs")
    require(counts["native_pixels_byte_verified"] == expected["distinct_bam_native_pixels"], "pixel coverage differs")
    require(counts["cycle_slots_verified"] == expected["cycle_slots"], "slot coverage differs")
    # Coverage is also checked relationally; no missing mappings / phantom work.
    require(db.execute("SELECT count(*) FROM frame_map").fetchone()[0] == expected["logical_frames"], "logical mappings differ")
    require(db.execute("SELECT count(*) FROM processing_queue").fetchone()[0] == expected["unique_work_items"], "work queue differs")
    require(not db.execute("SELECT w.work_id FROM work_items w LEFT JOIN frames f USING(work_id) WHERE f.work_id IS NULL LIMIT 1").fetchone(), "unused work item")
    require(not db.execute("""SELECT w.work_id FROM work_items w JOIN frames f
        ON f.resource_id=w.representative_resource_id AND f.frame_index=w.representative_frame_index
        WHERE f.work_id!=w.work_id LIMIT 1""").fetchone(), "representative belongs to another work item")
    for w in db.execute("""SELECT w.*,i.input_key,i.width,i.height,i.transparent_index,i.indices_zlib
        FROM work_items w JOIN inputs i USING(input_id)"""):
        plane = zlib.decompress(w["indices_zlib"])
        header = struct.pack("<IIB", w["width"], w["height"], w["transparent_index"])
        require(hashlib.sha256(INPUT_DOMAIN + header + plane).digest() == w["input_key"], "input content key differs")
        require(hashlib.sha256(WORK_DOMAIN + w["input_key"] + w["used_native_rgb"]).digest() == w["work_key"], "work content key differs")
        counts["unique_work_keys_recomputed"] += 1
    db.close()
    result = dict(schema=SCHEMA, status="verified-read-only", checks=dict(counts), seconds=round(time.perf_counter()-start, 3))
    print(dump(result), flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("scan", "verify"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    (scan if args.command == "scan" else verify)(args.path)
