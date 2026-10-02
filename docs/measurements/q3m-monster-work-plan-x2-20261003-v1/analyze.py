"""Scoped phase-2 CPU source plan; existing plans/runs/caches are read-only.

No inference, guide generation, production cache, build, QA or installation.
Reproduction refuses existing outputs. Python -B; numpy only.
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
import sys
import zlib

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from analyze_playable_frame_dedup import identities
from palette_oracle import read_bam_p8

CONTRACT = ROOT / "docs/measurements/q3m-monster-contract-x2-20261002-v1/contract.json"
DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
CREATE TABLE profiles(profile_id INTEGER PRIMARY KEY,contract_namespace TEXT NOT NULL,profile_json TEXT NOT NULL);
CREATE TABLE families(animation_id TEXT PRIMARY KEY,family_id TEXT NOT NULL,target TEXT NOT NULL,source_manifest TEXT NOT NULL);
CREATE TABLE resources(resource_id INTEGER PRIMARY KEY,resref TEXT UNIQUE NOT NULL,animation_id TEXT NOT NULL REFERENCES families,
 profile_id INTEGER NOT NULL REFERENCES profiles,canonical_path TEXT NOT NULL,canonical_sha256 TEXT NOT NULL,source_sha256 TEXT NOT NULL,
 frame_count INTEGER NOT NULL,cycle_count INTEGER NOT NULL,cycle_slots INTEGER NOT NULL,palette_bgra BLOB NOT NULL);
CREATE TABLE inputs(input_id INTEGER PRIMARY KEY,input_key BLOB UNIQUE NOT NULL,width INTEGER NOT NULL,height INTEGER NOT NULL,
 transparent_index INTEGER NOT NULL,indices_zlib BLOB NOT NULL,payload_sha256 TEXT NOT NULL,needs_model INTEGER NOT NULL,
 padded_width INTEGER NOT NULL,padded_height INTEGER NOT NULL);
CREATE TABLE guides(guide_id INTEGER PRIMARY KEY,source_work_key BLOB UNIQUE NOT NULL,input_id INTEGER NOT NULL REFERENCES inputs,
 used_native_rgb BLOB NOT NULL,representative_resource_id INTEGER NOT NULL REFERENCES resources,representative_frame_index INTEGER NOT NULL,
 locator_json TEXT,guide_sha256 TEXT,reuse_status TEXT NOT NULL DEFAULT 'pending');
CREATE TABLE work_items(work_id INTEGER PRIMARY KEY,work_key BLOB UNIQUE NOT NULL,profile_id INTEGER NOT NULL REFERENCES profiles,
 input_id INTEGER NOT NULL REFERENCES inputs,guide_id INTEGER NOT NULL REFERENCES guides,neural_key BLOB,
 classification TEXT NOT NULL,representative_resource_id INTEGER NOT NULL REFERENCES resources,
 representative_frame_index INTEGER NOT NULL,source_occurrences INTEGER NOT NULL DEFAULT 0);
CREATE TABLE frames(resource_id INTEGER NOT NULL REFERENCES resources,frame_index INTEGER NOT NULL,work_id INTEGER NOT NULL REFERENCES work_items,
 center_x INTEGER NOT NULL,center_y INTEGER NOT NULL,original_rle INTEGER NOT NULL,rle_tail_overflow INTEGER NOT NULL,
 cycle_referenced INTEGER NOT NULL,PRIMARY KEY(resource_id,frame_index)) WITHOUT ROWID;
CREATE TABLE cycles(resource_id INTEGER NOT NULL REFERENCES resources,cycle_index INTEGER NOT NULL,lookup_start INTEGER NOT NULL,
 slot_count INTEGER NOT NULL,frame_indices_le_u16 BLOB NOT NULL,PRIMARY KEY(resource_id,cycle_index)) WITHOUT ROWID;
CREATE TABLE character_input_matches(input_id INTEGER PRIMARY KEY REFERENCES inputs,character_input_id INTEGER NOT NULL,
 byte_compared INTEGER NOT NULL,character_needs_model INTEGER NOT NULL);
CREATE TABLE character_work_matches(guide_id INTEGER PRIMARY KEY REFERENCES guides,character_work_id INTEGER NOT NULL,
 used_rgb_byte_compared INTEGER NOT NULL,encoded_reusable INTEGER NOT NULL,reason TEXT NOT NULL);
CREATE TABLE historical_runs(run_id INTEGER PRIMARY KEY,manifest_path TEXT UNIQUE NOT NULL,manifest_sha256 TEXT NOT NULL,
 animation_id TEXT,schema TEXT NOT NULL,method TEXT NOT NULL,run_json TEXT NOT NULL);
CREATE TABLE historical_matches(run_id INTEGER NOT NULL REFERENCES historical_runs,resref TEXT NOT NULL,frame_index INTEGER NOT NULL,
 input_id INTEGER NOT NULL REFERENCES inputs,source_work_key BLOB NOT NULL,source_rgb_match INTEGER NOT NULL,
 byte_compared INTEGER NOT NULL,PRIMARY KEY(run_id,resref,frame_index)) WITHOUT ROWID;
CREATE INDEX work_by_input ON work_items(input_id);
CREATE INDEX frames_by_work ON frames(work_id);
CREATE INDEX historical_by_input ON historical_matches(input_id);
CREATE VIEW processing_queue AS SELECT w.*,lower(hex(w.work_key)) AS work_key_hex,p.contract_namespace,
 i.width,i.height,i.transparent_index,i.indices_zlib,i.padded_width,i.padded_height,i.needs_model,
 r.resref AS representative_resref,r.canonical_path,r.canonical_sha256,
 g.locator_json AS guide_locator_json,g.guide_sha256,g.reuse_status AS guide_reuse_status
 FROM work_items w JOIN profiles p USING(profile_id) JOIN inputs i USING(input_id)
 JOIN resources r ON r.resource_id=w.representative_resource_id JOIN guides g USING(guide_id);
CREATE VIEW frame_map AS SELECT r.animation_id,r.resref,f.*,w.profile_id,lower(hex(w.work_key)) AS work_key,
 i.width,i.height,i.transparent_index FROM frames f JOIN resources r USING(resource_id)
 JOIN work_items w USING(work_id) JOIN inputs i USING(input_id);
CREATE VIEW neural_queue AS SELECT lower(hex(neural_key)) AS neural_key,count(*) AS encoder_consumers,
 min(work_id) AS representative_work_id FROM work_items WHERE neural_key IS NOT NULL GROUP BY neural_key;
"""


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def relative(path):
    return Path(path).resolve().relative_to(ROOT).as_posix()


def csv_rows(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def selected_frame(raw, index):
    """Read only a matched historical frame, not every frame of its family."""
    if raw[:8] != b"BAM V1  ":
        raise ValueError("historical canonical BAM V1 required")
    nf, _, tr = struct.unpack_from("<HBB", raw, 8)
    fo, po, _ = struct.unpack_from("<III", raw, 12)
    if not 0 <= index < nf:
        raise ValueError("historical source frame outside BAM")
    w, h, cx, cy, tagged = struct.unpack_from("<HHhhI", raw, fo + index * 12)
    off, compressed = tagged & 0x7FFFFFFF, not bool(tagged & 0x80000000)
    need, pixels = w * h, bytearray()
    if compressed:
        while len(pixels) < need:
            value = raw[off]
            off += 1
            count = 1
            if value == tr:
                count = raw[off] + 1
                off += 1
            pixels.extend(bytes([value]) * min(count, need - len(pixels)))
    else:
        pixels.extend(raw[off:off + need])
    assert len(pixels) == need
    palette = np.frombuffer(raw[po:po + 1024], np.uint8).reshape(256, 4)[:, [2, 1, 0]].copy()
    return np.frombuffer(bytes(pixels), np.uint8).reshape(h, w), palette, tr, (cx, cy)


def old_guide_locations(manifest_path, resources, kernel, source_pins):
    """Adoption evidence for existing guides; no rerun of historical xBR/QA."""
    m = load(manifest_path)
    assert m["method"] == {"algorithm": "XBR/xbr2X", "scale": 2, "passes": 1,
                           "antialias": False, "xbr_blend": False}
    assert m["xbr_adapter_sha256"].lower() == kernel["xbr2x_batch.js"]
    assert m["scalepix_sha256"].lower() == kernel["config://mmpx_scalepix"]
    assert m["source_manifest_sha256"].lower() == source_pins[m["source_manifest"]]
    registry = manifest_path.parent / m["registry"]
    raw = registry.read_bytes()
    assert len(raw) == m["registry_bytes"] and sha(raw) == m["registry_sha256"].lower()
    magic, version, scale, count, animation = struct.unpack_from("<8sIIII", raw)
    assert magic == b"IEECSXN\0" and version == 3 and scale == 2
    assert animation == int(m["animation_id"], 16)
    locations, off = {}, 24
    for _ in range(count):
        ref = raw[off:off + 8].split(b"\0", 1)[0].decode("ascii")
        source_sha = raw[off + 8:off + 40].hex()
        nf, nc = struct.unpack_from("<II", raw, off + 40)
        expected = resources[ref]
        assert source_sha == expected["source_sha256"].lower()
        assert nf == expected["frame_count"] and nc == expected["cycle_count"]
        off += 48
        for fi in range(nf):
            w, h, cx, cy, tr, stored = struct.unpack_from("<HHhhB3xI", raw, off)
            assert raw[off + 9] == 0 and stored == w * h * 4
            off += 528
            assert off + stored <= len(raw)
            locations[(ref, fi)] = (off, stored, (w, h, cx, cy, tr))
            off += stored
        for _ in range(nc):
            slots = struct.unpack_from("<I", raw, off)[0]
            off += 4 + slots * 4
    assert off == len(raw) and set(ref for ref, _ in locations) == set(resources)
    return m, registry, raw, locations


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    out.relative_to(ROOT / "docs/measurements")
    names = ("processing-plan.sqlite", "plan.json", "summary.json", "verification.json")
    if any((out / n).exists() for n in names):
        raise ValueError("fresh outputs required; historical plans are immutable")
    contract_raw = CONTRACT.read_bytes()
    c = json.loads(contract_raw)
    profiles_path = CONTRACT.parent / c["profiles_file"]
    assert sha(profiles_path.read_bytes()) == c["profiles_file_sha256"]
    profiles = {p["palette_profile_id"]: p for p in load(profiles_path)["profiles"]}
    pointer_path = ROOT / "sprite/index/palette-work-plan.json"
    pointer = load(pointer_path)
    character_path = ROOT / pointer["path"]
    assert character_path.is_file() and character_path.stat().st_size == pointer["bytes"]
    character = sqlite3.connect(character_path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    character.row_factory = sqlite3.Row
    char_meta = {r[0]: json.loads(r[1]) for r in character.execute("SELECT * FROM metadata")}
    assert char_meta["schema"] == "playable-palettized-exact-frame-plan-v1"
    assert char_meta["status"] == "complete-source-analysis-not-generated"
    config = load(ROOT / "config/workspace-paths.local.json")
    kernel = {n: sha((ROOT / "pipeline/scripts" / n).read_bytes()) for n in
              ("xbr2x_batch.js", "reboutcx_batch_p12.py", "reboutcx_multipal.py", "reboutcx_quantize.py")}
    kernel["config://mmpx_scalepix"] = sha(Path(config["paths"]["mmpx_scalepix"]).read_bytes())
    inference_context = sha(dump({"inference": c["inference_parameters_retained"], "kernel": kernel,
                                  "source_alpha_mask": "transparent-index-0-only", "scale": 2}).encode())
    source_pins = {relative(CONTRACT): sha(contract_raw), relative(profiles_path): sha(profiles_path.read_bytes()),
                   relative(pointer_path): sha(pointer_path.read_bytes())}
    inventory = {r["bam_resref"]: r for r in csv_rows(ROOT / "sprite/index/sprite_resources.csv")}
    extracts = {r["bam_resref"]: r for r in csv_rows(ROOT / "sprite/index/extractions.csv")}
    out.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(out / names[0])
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    db.execute("PRAGMA journal_mode=DELETE")
    input_ids, guide_ids, work_ids = {}, {}, {}
    payloads, used_rgbs, representatives, manifests = {}, {}, {}, {}
    stats = defaultdict(Counter)
    native_same_hash = {}
    source_reuses = input_reuses = guide_reuses = work_reuses = 0
    for pid, profile in profiles.items():
        namespace = sha(dump({"contract_sha256": sha(contract_raw), "profile": profile, "scale": 2}).encode())
        db.execute("INSERT INTO profiles VALUES(?,?,?)", (pid, namespace, dump(profile)))
    for family in c["families"]:
        animation = family["animation_id"]
        mp = ROOT / family["source_manifest"]
        source_pins[family["source_manifest"]] = sha(mp.read_bytes())
        m = load(mp)
        manifests[animation] = m
        db.execute("INSERT INTO families VALUES(?,?,?,?)", (animation, family["family_id"], family["target"], family["source_manifest"]))
        by_ref = {b["name"]: b for b in m["bams"]}
        for selected in [r for r in c["resources"] if r["animation_id"] == animation]:
            ref, pid = selected["resref"], selected["palette_profile_id"]
            b = by_ref[ref]
            canonical_path = mp.parent / b["canonical_bam"]
            raw = canonical_path.read_bytes()
            canonical_sha = sha(raw)
            assert canonical_sha == b["canonical_bam_sha256"].lower() == selected["canonical_sha256_registered"].lower()
            indexed = inventory[ref]
            assert indexed["canonical_sha256"].lower() == canonical_sha
            assert family["family_id"] in indexed["family_ids"].split(";")
            if ref in extracts:
                assert extracts[ref]["extraction_state"] == "verified"
                assert extracts[ref]["canonical_sha256"].lower() == canonical_sha
            if canonical_sha in native_same_hash:
                previous_raw, decoded = native_same_hash[canonical_sha]
                assert previous_raw == raw
                source_reuses += 1
            else:
                decoded = read_bam_p8(raw)
                native_same_hash[canonical_sha] = (raw, decoded)
            assert decoded["transparent"] == 0
            assert decoded["palette_bgra"].tobytes().hex() == profiles[pid]["base_bgra_hex"]
            frames, cycles = decoded["frames"], decoded["cycles"]
            assert len(frames) == selected["frame_count_registered"] and len(cycles) == selected["cycle_count_registered"]
            rid = len(representatives) + 1
            slots = sum(len(x["frame_indices"]) for x in cycles)
            db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?)", (rid, ref, animation, pid,
                       relative(canonical_path), canonical_sha, b["source_sha256"].lower(), len(frames), len(cycles), slots,
                       decoded["palette_bgra"].tobytes()))
            representatives[ref] = rid
            referenced = {i for cycle in cycles for i in cycle["frame_indices"]}
            for cycle in cycles:
                db.execute("INSERT INTO cycles VALUES(?,?,?,?,?)", (rid, cycle["index"], cycle["lookup_start"],
                           len(cycle["frame_indices"]), np.asarray(cycle["frame_indices"], dtype="<u2").tobytes()))
            namespace = db.execute("SELECT contract_namespace FROM profiles WHERE profile_id=?", (pid,)).fetchone()[0]
            fits = np.stack([np.frombuffer(bytes.fromhex(p["rgba_hex"]), np.uint8).reshape(256, 4)[:, :3] for p in profiles[pid]["fits"]])
            for frame in frames:
                pixels = frame["indices"]
                w, h = frame["width"], frame["height"]
                assert 0 < w * h < 65535
                ik, sk, payload, used_rgb, needs_model = identities(pixels, decoded["palette_rgb"], 0)
                if np.any(pixels == 2):
                    stats[animation]["frames_with_index2"] += 1
                    assert (w, h, frame["center_x"], frame["center_y"], payload) == (1, 1, 0, 0, b"\x02")
                if ik in input_ids:
                    iid = input_ids[ik]
                    assert payloads[iid] == payload
                    input_reuses += 1
                else:
                    iid = len(input_ids) + 1
                    input_ids[ik], payloads[iid] = iid, payload
                    db.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?,?,?,?)", (iid, ik, w, h, 0, zlib.compress(payload),
                               sha(payload), int(needs_model), ((w + 31) // 32) * 32, ((h + 31) // 32) * 32))
                if sk in guide_ids:
                    gid = guide_ids[sk]
                    assert used_rgbs[gid] == used_rgb
                    guide_reuses += 1
                else:
                    gid = len(guide_ids) + 1
                    guide_ids[sk], used_rgbs[gid] = gid, used_rgb
                    db.execute("INSERT INTO guides(guide_id,source_work_key,input_id,used_native_rgb,representative_resource_id,representative_frame_index) VALUES(?,?,?,?,?,?)",
                               (gid, sk, iid, used_rgb, rid, frame["index"]))
                wk = hashlib.sha256(b"BG2-MONSTER-Q3M-CONTRACT-WORK-v1\0" + bytes.fromhex(namespace) + sk).digest()
                if wk in work_ids:
                    wid = work_ids[wk]
                    work_reuses += 1
                else:
                    wid = len(work_ids) + 1
                    work_ids[wk] = wid
                    used = np.unique(pixels)
                    fit_used = np.ascontiguousarray(fits[:, used]).tobytes()
                    nk = hashlib.sha256(b"BG2-MONSTER-K6-NEURAL-v1\0" + bytes.fromhex(inference_context) + ik + used.tobytes() + fit_used).digest() if needs_model else None
                    db.execute("INSERT INTO work_items VALUES(?,?,?,?,?,?,?,?,?,0)", (wid, wk, pid, iid, gid, nk,
                               "new_model" if needs_model else "new_special", rid, frame["index"]))
                db.execute("UPDATE work_items SET source_occurrences=source_occurrences+1 WHERE work_id=?", (wid,))
                db.execute("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?)", (rid, frame["index"], wid, frame["center_x"],
                           frame["center_y"], int(frame["compressed"]), frame["rle_tail_overflow"], int(frame["index"] in referenced)))
                stats[animation]["model_frame_occurrences"] += int(needs_model)
                stats[animation]["special_frame_occurrences"] += int(not needs_model)
                stats[animation]["native_pixels"] += w * h
                stats[animation]["unreferenced_frames"] += int(frame["index"] not in referenced)
            stats[animation].update(resources=1, frames=len(frames), cycles=len(cycles), cycle_slots=slots)
        print("sources", animation, dict(stats[animation]), flush=True)
    # Exact intersections with acquired Character DB: indexed/rgb hashes then byte comparison.
    for row in db.execute("SELECT * FROM inputs").fetchall():
        match = character.execute("SELECT * FROM inputs WHERE input_key=?", (row["input_key"],)).fetchone()
        if match:
            assert (row["width"], row["height"], row["transparent_index"]) == (match["width"], match["height"], match["transparent_index"])
            assert payloads[row["input_id"]] == zlib.decompress(match["indices_zlib"])
            db.execute("INSERT INTO character_input_matches VALUES(?,?,1,?)", (row["input_id"], match["input_id"], match["needs_model"]))
    for row in db.execute("SELECT * FROM guides").fetchall():
        match = character.execute("SELECT * FROM work_items WHERE work_key=?", (row["source_work_key"],)).fetchone()
        if match:
            assert row["used_native_rgb"] == match["used_native_rgb"]
            db.execute("INSERT INTO character_work_matches VALUES(?,?,1,0,?)", (row["guide_id"], match["work_id"],
                       "Character encoder classes/successors/fits/alpha/owner differ; no I/F/dep adoption"))
    # Reference historical Monster full-run manifests; only matching source frames read.
    candidate_geometry = {(r["width"], r["height"], r["transparent_index"])
                          for r in db.execute("SELECT * FROM inputs")}
    for macro in ("monsters", "monster-icewind", "composite-monsters"):
        for manifest_path in sorted((ROOT / "sprite/families" / macro).glob("**/runs/*/manifest.json")):
            if "rebout" not in manifest_path.parent.name:
                continue
            m = load(manifest_path)
            full = m.get("schema") == "bg2-upscale-reboutcx-full-run-v1"
            if not full:
                continue  # Prototype synthetic cycles are not production/source plans.
            run_id = db.execute("SELECT count(*) FROM historical_runs").fetchone()[0] + 1
            db.execute("INSERT INTO historical_runs VALUES(?,?,?,?,?,?,?)", (run_id, relative(manifest_path), sha(manifest_path.read_bytes()),
                       m.get("animation_id"), m["schema"], "ReboutCX-Q0-indexed-not-Q3m", dump({"method": m.get("method"), "coverage": m.get("coverage"),
                       "float_target_npz_files_present": len(list(manifest_path.parent.rglob("*.npz")))})))
            old_mp = ROOT / m["source_manifest"]
            old_m = load(old_mp)
            old_sources = {r["name"]: old_mp.parent / r["canonical_bam"] for r in old_m["bams"]}
            for resource in m["resources"]:
                matched = []
                for f in resource["frame_records"]:
                    # Historical indices_sha256 hashes the QUANTIZED x2 output.
                    # It must never be treated as a native-source raster hash.
                    key = (f["width"], f["height"], f["transparent_index"])
                    if key in candidate_geometry:
                        matched.append(f)
                if not matched:
                    continue
                old_raw = old_sources[resource["resref"]].read_bytes()
                old_sha = sha(old_raw)
                assert old_sha == resource["canonical_bam_sha256"].lower()
                old_decoded = native_same_hash.get(old_sha)
                for f in matched:
                    if old_decoded:
                        sf = old_decoded[1]["frames"][f["source_frame"]]
                        pixels, palette, tr = sf["indices"], old_decoded[1]["palette_rgb"], old_decoded[1]["transparent"]
                        centre = (sf["center_x"], sf["center_y"])
                    else:
                        pixels, palette, tr, centre = selected_frame(old_raw, f["source_frame"])
                    ik, sk, payload, used, _ = identities(pixels, palette, tr)
                    if ik not in input_ids:
                        continue
                    iid = input_ids[ik]
                    assert payloads[iid] == payload
                    assert centre == (f["center_x"], f["center_y"])
                    if sk in guide_ids:
                        assert used_rgbs[guide_ids[sk]] == used
                    db.execute("INSERT INTO historical_matches VALUES(?,?,?,?,?,?,1)", (run_id, resource["resref"], f["source_frame"], iid, sk, int(sk in guide_ids)))
    # Map representative guide requests to existing xBR planes with exact source/kernel contracts.
    guide_evidence = []
    for family in c["families"]:
        mp = ROOT / family["source_manifest"]
        build = mp.parent.parent.parent / "runs/x2-nearest-v1/build/build-manifest.json"
        expected = {b["name"]: b for b in manifests[family["animation_id"]]["bams"]}
        m, registry, raw, locations = old_guide_locations(build, expected, kernel, source_pins)
        guide_evidence.append({"animation_id": family["animation_id"], "manifest": relative(build),
                               "manifest_sha256": sha(build.read_bytes()), "registry": relative(registry),
                               "registry_sha256": m["registry_sha256"].lower(), "status": "compatible-xBR-guide-only"})
        query = """SELECT g.*,r.resref,i.width,i.height,f.center_x,f.center_y FROM guides g
                   JOIN resources r ON r.resource_id=g.representative_resource_id
                   JOIN inputs i USING(input_id) JOIN frames f ON f.resource_id=r.resource_id AND f.frame_index=g.representative_frame_index
                   WHERE r.animation_id=?"""
        for row in db.execute(query, (family["animation_id"],)).fetchall():
            off, count, geometry = locations[(row["resref"], row["representative_frame_index"])]
            assert geometry == (row["width"], row["height"], row["center_x"], row["center_y"], 0)
            payload = raw[off:off + count]
            used = np.frombuffer(row["used_native_rgb"], np.uint8).reshape(-1, 4)[:, 0]
            assert set(payload) <= set(used.tolist())
            locator = {"registry": relative(registry), "registry_sha256": m["registry_sha256"].lower(),
                       "offset": off, "bytes": count, "resref": row["resref"], "frame_index": row["representative_frame_index"],
                       "shape": [row["height"] * 2, row["width"] * 2]}
            db.execute("UPDATE guides SET locator_json=?,guide_sha256=?,reuse_status='reusable_xbr' WHERE guide_id=?",
                       (dump(locator), sha(payload), row["guide_id"]))
    assert not db.execute("SELECT 1 FROM guides WHERE reuse_status!='reusable_xbr'").fetchone()
    # Preserve current production: no final Monster writer exists, so no namespace-compatible encoded cache can exist yet.
    def scalar(sql, args=()):
        return db.execute(sql, args).fetchone()[0]
    totals = {"resources": scalar("SELECT count(*) FROM resources"), "frames": scalar("SELECT count(*) FROM frames"),
              "cycles": scalar("SELECT count(*) FROM cycles"), "cycle_slots": scalar("SELECT sum(slot_count) FROM cycles"),
              "unique_canonical_bams": len(native_same_hash), "unique_indexed_inputs": len(input_ids),
              "unique_native_rgb_guide_requests": len(guide_ids), "unique_contract_work_items": len(work_ids),
              "new_model_work_items": scalar("SELECT count(*) FROM work_items WHERE classification='new_model'"),
              "new_special_work_items": scalar("SELECT count(*) FROM work_items WHERE classification='new_special'"),
              "reused_q3m_encoded_work_items": 0, "reusable_old_xbr_guide_requests": len(guide_ids), "new_xbr_guide_requests": 0,
              "unique_neural_six_fit_requests": scalar("SELECT count(*) FROM neural_queue"),
              "character_indexed_input_intersections": scalar("SELECT count(*) FROM character_input_matches"),
              "character_native_rgb_work_intersections": scalar("SELECT count(*) FROM character_work_matches"),
              "historical_runs_compared": scalar("SELECT count(*) FROM historical_runs"),
              "historical_matching_frame_records": scalar("SELECT count(*) FROM historical_matches"),
              "historical_matching_unique_inputs": scalar("SELECT count(DISTINCT input_id) FROM historical_matches"),
              "bam_reuses_byte_compared": source_reuses, "input_reuses_byte_compared": input_reuses,
              "guide_key_reuses_byte_compared": guide_reuses, "contract_work_reuses": work_reuses}
    totals["six_fit_target_calls_without_cross_encoder_target_sharing"] = totals["new_model_work_items"] * 6
    totals["six_fit_target_calls_if_neural_queue_shared"] = totals["unique_neural_six_fit_requests"] * 6
    family_stats = []
    for family in c["families"]:
        animation = family["animation_id"]
        entry = dict(family, **dict(stats[animation]))
        entry["unique_work_items"] = scalar("SELECT count(DISTINCT work_id) FROM frames JOIN resources USING(resource_id) WHERE animation_id=?", (animation,))
        entry["new_model_work_items"] = scalar("SELECT count(*) FROM work_items w JOIN resources r ON r.resource_id=w.representative_resource_id WHERE r.animation_id=? AND classification='new_model'", (animation,))
        entry["new_special_work_items"] = entry["unique_work_items"] - entry["new_model_work_items"]
        entry["unique_canonical_bams"] = scalar("SELECT count(DISTINCT canonical_sha256) FROM resources WHERE animation_id=?", (animation,))
        family_stats.append(entry)
    pairwise = []
    for a, fa in enumerate(family_stats):
        for fb in family_stats[a + 1:]:
            params = (fa["animation_id"], fb["animation_id"])
            n = scalar("""SELECT count(*) FROM (SELECT DISTINCT w.input_id FROM frames f JOIN resources r USING(resource_id) JOIN work_items w USING(work_id) WHERE r.animation_id=?
                        INTERSECT SELECT DISTINCT w.input_id FROM frames f JOIN resources r USING(resource_id) JOIN work_items w USING(work_id) WHERE r.animation_id=?)""", params)
            pairwise.append({"animation_ids": list(params), "common_indexed_inputs": n,
                             "common_final_q3m_work_items": 0, "reason": "distinct frozen palette profiles/recipes"})
    char_evidence = dict(path=pointer["path"], registered_sha256=pointer["sha256"], bytes=pointer["bytes"],
                         mode="immutable-read-only; registered baseline reused, no global rehash/rebuild/validation",
                         namespace_x2=char_meta["profile"]["namespace_by_scale"]["2"], encoded_adopted=0)
    summary = {"schema": "bg2-monster-q3m-phase2-summary-v1", "status": "complete-cpu-plan-not-production",
               "totals": totals, "families": family_stats, "pairwise": pairwise,
               "character_reference": char_evidence, "guide_reuse_evidence": guide_evidence,
               "guide_alpha_policy": "Keep acquired xBR transport RGBA: source RGB, alpha 0 for index0, 255 otherwise. This mask is not the render alpha; decoder uses native live palette alpha.",
               "contract_namespace_policy": "CPU semantic namespaces frozen from phase1; final persistent cache namespaces require phase3 producer/encoder/kernel identities. Do not claim existing files as hits by key alone.",
               "neural_sharing_policy": "Potential sharing only with identical indexed raster and all six used fitting RGB arrays plus inference context; no neural-target persistent cache implemented or created.",
               "historical_scope": "Existing Monster/MonsterIcewind/composite full ReboutCX manifests only. Prototype synthetic cycles excluded; unrelated native BAMs read only for matching witnessed frames. No global native monster scan.",
               "historical_hash_semantics": "ReboutCX frame_records.indices_sha256 is the quantized x2 OUTPUT. Native intersections use the referenced canonical BAM raster and byte comparison; no inference from that output hash.",
               "pending": ["Implement scoped consumer and fixed profile V6 encode/read in phase3",
                           "Pilot visual/native live-palette QA remains separate from CPU source/guide correspondence"]}
    assert totals["frames"] == 20925 and totals["cycles"] == 2288 and totals["cycle_slots"] == 41217
    assert scalar("SELECT sum(source_occurrences) FROM work_items") == totals["frames"]
    assert not db.execute("PRAGMA foreign_key_check").fetchall()
    assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    verification = {"schema": "bg2-monster-q3m-phase2-verification-v1", "status": "passed", "totals": totals,
                    "complete_frame_cycle_mapping": True, "hash_matches_byte_compared": True,
                    "source_registry_identity_checked_for_guide_adoption": True,
                    "mbeh_index2_exclusivity": "all MBEH index2 frames are 1x1 at 0,0; confirmed while requested sources decoded",
                    "existing_authorities_modified": False, "gpu_initialized": False,
                    "scope": "new source plan and existing guide adoption evidence; not ingame QA or runtime validation"}
    metadata = {"schema": "bg2-monster-q3m-source-work-plan-v1", "status": "complete-source-analysis-not-generated",
                "contract": relative(CONTRACT), "contract_sha256": sha(contract_raw), "source_pins": source_pins,
                "kernels": kernel, "inference_context": inference_context, "character_reference": char_evidence,
                "summary": summary, "build_script_sha256": sha(Path(__file__).read_bytes())}
    for key, value in metadata.items():
        db.execute("INSERT INTO metadata VALUES(?,?)", (key, dump(value)))
    db.commit()
    db.close()
    character.close()
    plan_raw = (out / names[0]).read_bytes()
    descriptor = {"schema": "bg2-monster-q3m-local-plan-descriptor-v1", "role": "source-plan-not-production-or-QA",
                  "path": relative(out / names[0]), "bytes": len(plan_raw), "sha256": sha(plan_raw),
                  "contract": relative(CONTRACT), "contract_sha256": sha(contract_raw),
                  "summary": "summary.json", "consumer": "phase3 implementation required; Character WorkPlan is not compatible"}
    for name, value in (("plan.json", descriptor), ("summary.json", summary), ("verification.json", verification)):
        with (out / name).open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(totals), flush=True)


if __name__ == "__main__":
    main()
