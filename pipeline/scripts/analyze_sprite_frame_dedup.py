"""CPU source deduplication for every non-Character sprite integration profile.

Keeps the acquired Character/Monster plans read-only. Source equality is not
permission to share an encoded result across different palette contracts.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
import struct
import time
import zlib

from analyze_playable_frame_dedup import identities, rows, require
from palette_oracle import read_bam_p8
from run_creature_sprite_x2 import BAM_TYPE, KeyIndex, bam_cycles, canonical_bam
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
POINTER = ROOT / "sprite/index/q3m-source-work-plan.json"
SCHEMA = "bg2-all-creature-source-dedup-v1"
DDL = """
PRAGMA foreign_keys=ON;
CREATE TABLE metadata(key TEXT PRIMARY KEY,value_json TEXT NOT NULL);
CREATE TABLE animations(animation_id TEXT PRIMARY KEY,engine_section TEXT NOT NULL,source_json TEXT NOT NULL);
CREATE TABLE resources(resource_id INTEGER PRIMARY KEY,resref TEXT UNIQUE NOT NULL,
 canonical_sha256 TEXT NOT NULL,source_sha256 TEXT NOT NULL,source_locator TEXT NOT NULL,
 palette_bgra BLOB NOT NULL,transparent_index INTEGER NOT NULL,frame_count INTEGER NOT NULL,
 cycle_count INTEGER NOT NULL,cycle_slot_count INTEGER NOT NULL,source_json TEXT NOT NULL);
CREATE TABLE animation_resources(animation_id TEXT REFERENCES animations,resource_id INTEGER REFERENCES resources,
 PRIMARY KEY(animation_id,resource_id)) WITHOUT ROWID;
CREATE TABLE inputs(input_id INTEGER PRIMARY KEY,input_key BLOB UNIQUE NOT NULL,width INTEGER NOT NULL,
 height INTEGER NOT NULL,transparent_index INTEGER NOT NULL,indices_zlib BLOB NOT NULL,
 model_candidate INTEGER NOT NULL);
CREATE TABLE source_work(work_id INTEGER PRIMARY KEY,work_key BLOB UNIQUE NOT NULL,input_id INTEGER REFERENCES inputs,
 used_native_rgb BLOB NOT NULL,representative_resource_id INTEGER REFERENCES resources,
 representative_frame_index INTEGER NOT NULL);
CREATE TABLE frames(resource_id INTEGER REFERENCES resources,frame_index INTEGER NOT NULL,work_id INTEGER REFERENCES source_work,
 center_x INTEGER NOT NULL,center_y INTEGER NOT NULL,original_rle INTEGER NOT NULL,
 rle_tail_overflow INTEGER NOT NULL,cycle_referenced INTEGER NOT NULL,
 PRIMARY KEY(resource_id,frame_index)) WITHOUT ROWID;
CREATE TABLE cycles(resource_id INTEGER REFERENCES resources,cycle_index INTEGER NOT NULL,lookup_start INTEGER NOT NULL,
 slot_count INTEGER NOT NULL,frame_indices_le_u16 BLOB NOT NULL,PRIMARY KEY(resource_id,cycle_index)) WITHOUT ROWID;
CREATE TABLE character_input_matches(input_id INTEGER PRIMARY KEY REFERENCES inputs,character_input_id INTEGER NOT NULL,
 byte_compared INTEGER NOT NULL CHECK(byte_compared=1));
CREATE TABLE character_work_matches(work_id INTEGER PRIMARY KEY REFERENCES source_work,character_work_id INTEGER NOT NULL,
 byte_compared INTEGER NOT NULL CHECK(byte_compared=1));
CREATE TABLE monster_work_matches(resource_id INTEGER NOT NULL,frame_index INTEGER NOT NULL,
 monster_work_id INTEGER NOT NULL,monster_profile_id INTEGER NOT NULL,
 PRIMARY KEY(resource_id,frame_index)) WITHOUT ROWID;
CREATE INDEX frames_work ON frames(work_id);
CREATE VIEW animation_work AS SELECT DISTINCT a.animation_id,f.work_id
 FROM animation_resources a JOIN frames f USING(resource_id);
CREATE VIEW source_work_queue AS SELECT w.work_id,lower(hex(w.work_key)) AS source_work_key,
 i.input_id,lower(hex(i.input_key)) AS input_key,i.width,i.height,i.transparent_index,
 i.model_candidate,i.indices_zlib,w.used_native_rgb,r.resref AS representative_resref,
 w.representative_frame_index,r.source_locator FROM source_work w JOIN inputs i USING(input_id)
 JOIN resources r ON r.resource_id=w.representative_resource_id;
CREATE VIEW frame_map AS SELECT a.animation_id,r.resref,f.*,i.width,i.height,i.transparent_index,
 lower(hex(w.work_key)) AS source_work_key FROM animation_resources a JOIN resources r USING(resource_id)
 JOIN frames f USING(resource_id) JOIN source_work w USING(work_id) JOIN inputs i USING(input_id);
"""


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ro(path):
    db = sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro&immutable=1", uri=True)
    db.row_factory = sqlite3.Row
    return db


def meta(db, key, value):
    db.execute("INSERT OR REPLACE INTO metadata VALUES(?,?)", (key, json.dumps(value, sort_keys=True)))


def read_source(raw):
    """Retain native cycle sentinels while decoding all declared pixel frames.

    Some old profiles use lookup values outside the frame table. Their runtime
    meaning is not decided here. The strict P8 pixel reader receives a temporary
    zero-cycle header in that case; original cycles/source bytes stay intact.
    """
    nf, nc = struct.unpack_from("<HB", raw, 8)
    lo = struct.unpack_from("<I", raw, 20)[0]
    cycles = bam_cycles(raw)
    require(all(lo + 2*(c["lookup_start"]+len(c["frame_indices"])) <= len(raw) for c in cycles), "cycle lookup outside source")
    outside = sum(i >= nf for c in cycles for i in c["frame_indices"])
    pixels_raw = raw[:10] + b"\0" + raw[11:] if outside else raw
    bam = read_bam_p8(pixels_raw)
    bam["cycles"] = cycles
    return bam, outside


def scan(output):
    started = time.perf_counter()
    output = output.resolve()
    output.relative_to(ROOT / "docs/measurements")
    require(not output.exists(), "fresh analysis destination required")
    tracking = load(ROOT / "sprite/index/q3m-work-tracking.json")
    sections = set(tracking["scope"]["included"]) - {"character"}
    animations = {a["animation_id"]: a for a in rows(ROOT / "sprite/index/sprite_animations.csv")
                  if a["engine_section"] in sections}
    families = {f["family_id"]: f for f in rows(ROOT / "sprite/index/sprite_families.csv")
                if f["animation_id"] in animations}
    resources = [(r, sorted(set(r["animation_ids"].split(";")) & animations.keys()))
                 for r in rows(ROOT / "sprite/index/sprite_resources.csv")
                 if set(r["family_ids"].split(";")) & families.keys()]
    extracts = {r["bam_resref"]: r for r in rows(ROOT / "sprite/index/extractions.csv")}
    character_descriptor = load(ROOT / "sprite/index/palette-work-plan.json")
    character_path = ROOT / character_descriptor["path"]
    require(character_path.stat().st_size == character_descriptor["bytes"], "Character plan size changed")
    character = ro(character_path)
    char_meta = {r["key"]: json.loads(r["value_json"]) for r in character.execute("SELECT * FROM metadata")}
    require(char_meta["schema"] == "playable-palettized-exact-frame-plan-v1" and
            char_meta["status"] == "complete-source-analysis-not-generated", "Character plan incomplete")
    monster_descriptor_path = ROOT / "docs/measurements/q3m-monster-work-plan-x2-20261003-v1/plan.json"
    monster_descriptor = load(monster_descriptor_path)
    monster_path = ROOT / monster_descriptor["path"]
    require(monster_path.stat().st_size == monster_descriptor["bytes"], "Monster plan size changed")
    monster = ro(monster_path)
    monster_resources = {r["resref"]: dict(r) for r in monster.execute("SELECT * FROM resources")}
    key_index = None
    output.mkdir(parents=True)
    db_path = output / "processing-plan.sqlite"
    db = sqlite3.connect(db_path)
    db.row_factory = sqlite3.Row
    db.executescript(DDL)
    db.execute("PRAGMA cache_size=-131072")
    meta(db, "schema", SCHEMA)
    meta(db, "status", "in-progress")
    meta(db, "character_descriptor", character_descriptor)
    meta(db, "monster_descriptor", monster_descriptor)
    meta(db, "source_pins", {p: sha((ROOT / p).read_bytes()) for p in (
        "sprite/index/sprite_animations.csv", "sprite/index/sprite_families.csv",
        "sprite/index/sprite_resources.csv", "sprite/index/extractions.csv",
        "pipeline/scripts/analyze_sprite_frame_dedup.py")})
    db.executemany("INSERT INTO animations VALUES(?,?,?)", [(aid, a["engine_section"], json.dumps(a, sort_keys=True))
                                                          for aid, a in animations.items()])
    input_groups, work_groups, canonical_seen = {}, {}, {}
    counts = Counter()
    for rid, (r, owners) in enumerate(sorted(resources, key=lambda pair: pair[0]["bam_resref"]), 1):
        ref = r["bam_resref"]
        require(r["bam_version"] == "V1" and r["decode_status"] == "ok", f"unsupported source: {ref}")
        extraction = extracts.get(ref)
        if extraction and (ROOT / extraction["canonical_file"]).is_file():
            require(extraction["extraction_state"] == "verified" and
                    extraction["canonical_sha256"].lower() == r["canonical_sha256"].lower(), "extraction mismatch")
            locator = extraction["canonical_file"]
            raw = (ROOT / locator).read_bytes()
            counts["resources_from_extraction"] += 1
        else:
            if key_index is None:
                game = get_path("bg2ee_game_root", required=True)
                require(sha((game / "chitin.key").read_bytes()) ==
                        load(ROOT / "sprite/index/manifest.json")["chitin_key_sha256"].lower(), "game KEY changed")
                key_index = KeyIndex(game)
                key_resources = key_index.resource_map(BAM_TYPE)
            stock, bif = key_index.resolve(key_resources[ref])
            require(sha(stock) == r["source_sha256"].lower(), f"stock changed: {ref}")
            raw, _ = canonical_bam(stock)
            locator = "config://bg2ee_game_root#stock-BAM/" + ref
            counts["resources_from_stock_read_only"] += 1
        digest = sha(raw)
        require(digest == r["canonical_sha256"].lower(), f"canonical source changed: {ref}")
        nf, nc, tr = struct.unpack_from("<HBB", raw, 8)
        po = struct.unpack_from("<I", raw, 16)[0]
        palette = raw[po:po+1024]
        require((nf, nc, tr) == tuple(int(r[k]) for k in
                ("frame_count", "cycle_count", "transparent_palette_index")), f"source inventory mismatch: {ref}")
        db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?)", (rid, ref, digest,
                   r["source_sha256"].lower(), locator, palette, tr, nf, nc, int(r["cycle_slot_count"]), json.dumps(r)))
        db.executemany("INSERT INTO animation_resources VALUES(?,?)", [(aid, rid) for aid in owners])
        previous = canonical_seen.get(digest)
        if previous:
            old_rid, old_raw = previous
            require(raw == old_raw, "canonical BAM hash collision")
            db.execute("INSERT INTO frames SELECT ?,frame_index,work_id,center_x,center_y,original_rle,rle_tail_overflow,cycle_referenced FROM frames WHERE resource_id=?", (rid, old_rid))
            db.execute("INSERT INTO cycles SELECT ?,cycle_index,lookup_start,slot_count,frame_indices_le_u16 FROM cycles WHERE resource_id=?", (rid, old_rid))
            counts["identical_bams_decoded_once"] += 1
        else:
            canonical_seen[digest] = (rid, raw)
            bam, outside = read_source(raw)
            counts["native_out_of_frame_cycle_slots"] += outside
            counts["distinct_bams_with_out_of_frame_cycle_slots"] += int(bool(outside))
            require(sum(len(c["frame_indices"]) for c in bam["cycles"]) == int(r["cycle_slot_count"]), "cycle slots changed")
            referenced = {i for c in bam["cycles"] for i in c["frame_indices"]}
            for c in bam["cycles"]:
                db.execute("INSERT INTO cycles VALUES(?,?,?,?,?)", (rid, c["index"], c["lookup_start"], len(c["frame_indices"]),
                           struct.pack(f"<{len(c['frame_indices'])}H", *c["frame_indices"])))
            inserts = []
            for frame in bam["frames"]:
                ik, wk, payload, used_rgb, model = identities(frame["indices"], bam["palette_rgb"], tr)
                w, h = frame["width"], frame["height"]
                previous_input = input_groups.get(ik)
                if previous_input:
                    iid, ow, oh, ot, compressed = previous_input
                    require((w, h, tr) == (ow, oh, ot) and zlib.decompress(compressed) == payload, "indexed source hash collision")
                    counts["input_reuses_byte_compared"] += 1
                else:
                    iid = len(input_groups) + 1
                    compressed = zlib.compress(payload)
                    input_groups[ik] = (iid, w, h, tr, compressed)
                    db.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?)", (iid, ik, w, h, tr, compressed, int(model)))
                    match = character.execute("SELECT input_id,width,height,transparent_index,indices_zlib FROM inputs WHERE input_key=?", (ik,)).fetchone()
                    if match:
                        require((w, h, tr) == (match["width"], match["height"], match["transparent_index"]) and
                                zlib.decompress(match["indices_zlib"]) == payload, "Character input hash collision")
                        db.execute("INSERT INTO character_input_matches VALUES(?,?,1)", (iid, match["input_id"]))
                previous_work = work_groups.get(wk)
                if previous_work:
                    wid, old_iid, old_rgb = previous_work
                    require(iid == old_iid and used_rgb == old_rgb, "used-RGB source hash collision")
                    counts["work_reuses_byte_compared"] += 1
                else:
                    wid = len(work_groups) + 1
                    work_groups[wk] = (wid, iid, used_rgb)
                    db.execute("INSERT INTO source_work VALUES(?,?,?,?,?,?)", (wid, wk, iid, used_rgb, rid, frame["index"]))
                    match = character.execute("SELECT work_id,input_id,used_native_rgb FROM work_items WHERE work_key=?", (wk,)).fetchone()
                    if match:
                        require(used_rgb == match["used_native_rgb"] and db.execute(
                            "SELECT character_input_id FROM character_input_matches WHERE input_id=?", (iid,)).fetchone()[0] == match["input_id"], "Character RGB hash collision")
                        db.execute("INSERT INTO character_work_matches VALUES(?,?,1)", (wid, match["work_id"]))
                inserts.append((rid, frame["index"], wid, frame["center_x"], frame["center_y"], int(frame["compressed"]),
                                frame["rle_tail_overflow"], int(frame["index"] in referenced)))
            db.executemany("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?)", inserts)
        if ref in monster_resources:
            mr = monster_resources[ref]
            require(mr["canonical_sha256"] == digest, "known Monster source changed")
            for mf in monster.execute("SELECT f.*,w.profile_id,g.source_work_key FROM frames f JOIN work_items w USING(work_id) JOIN guides g USING(guide_id) WHERE f.resource_id=?", (mr["resource_id"],)):
                current = db.execute("SELECT f.*,w.work_key FROM frames f JOIN source_work w USING(work_id) WHERE resource_id=? AND frame_index=?", (rid, mf["frame_index"])).fetchone()
                require(current["work_key"] == mf["source_work_key"] and
                        (current["center_x"], current["center_y"]) == (mf["center_x"], mf["center_y"]), "known Monster frame differs")
                db.execute("INSERT INTO monster_work_matches VALUES(?,?,?,?)", (rid, mf["frame_index"], mf["work_id"], mf["profile_id"]))
        counts.update(resources=1, distinct_bam_frames=nf, cycles=nc, cycle_slots=int(r["cycle_slot_count"]),
                      logical_frames=nf*len(owners))
        if rid % 100 == 0 or rid == len(resources):
            db.commit()
            print(json.dumps(dict(phase="source-dedup", resources=rid, total=len(resources), unique_source_work=len(work_groups),
                                  seconds=round(time.perf_counter()-started, 1))), flush=True)
    db.execute("CREATE TABLE animation_statistics AS SELECT a.animation_id,a.engine_section,"
               "(SELECT count(*) FROM animation_resources ar WHERE ar.animation_id=a.animation_id) AS resources,"
               "(SELECT count(*) FROM animation_resources ar JOIN frames f USING(resource_id) WHERE ar.animation_id=a.animation_id) AS frames,"
               "(SELECT count(*) FROM animation_work aw WHERE aw.animation_id=a.animation_id) AS unique_source_work,"
               "(SELECT count(*) FROM animation_work aw JOIN source_work w USING(work_id) JOIN inputs i USING(input_id) WHERE aw.animation_id=a.animation_id AND i.model_candidate=1) AS unique_model_candidate_work,"
               "(SELECT count(*) FROM animation_work aw JOIN character_work_matches c USING(work_id) WHERE aw.animation_id=a.animation_id) AS source_work_shared_with_character "
               "FROM animations a")
    require(counts["distinct_bam_frames"] == db.execute("SELECT count(*) FROM frames").fetchone()[0], "frame coverage incomplete")
    require(db.execute("SELECT count(*) FROM monster_work_matches").fetchone()[0] ==
            monster.execute("SELECT count(*) FROM frames").fetchone()[0], "known Monster coverage incomplete")
    char_counts = char_meta["summary"]["counts"]
    char_resources = {r["resref"]: r["frame_count"] for r in character.execute("SELECT resref,frame_count FROM resources")}
    overlapping_frames = sum(char_resources.get(r["bam_resref"], 0) for r, _ in resources)
    shared = db.execute("SELECT count(*) FROM character_work_matches").fetchone()[0]
    counts.update(defined_noncharacter_ids=len(animations),
                  with_bam_noncharacter_ids=db.execute("SELECT count(DISTINCT animation_id) FROM animation_resources").fetchone()[0],
                  unique_indexed_inputs=len(input_groups), unique_source_work=len(work_groups),
                  unique_model_candidate_work=db.execute("SELECT count(*) FROM source_work JOIN inputs USING(input_id) WHERE model_candidate=1").fetchone()[0],
                  source_work_shared_with_character=shared,
                  known_monster_encoded_work=db.execute("SELECT count(DISTINCT monster_work_id) FROM monster_work_matches").fetchone()[0],
                  source_frame_reuses=counts["distinct_bam_frames"]-len(work_groups),
                  logical_source_work_avoided=counts["logical_frames"]-len(work_groups))
    summary = dict(schema=SCHEMA, status="complete-source-analysis-no-inference", counts=dict(counts),
                   character_plan_reused_read_only=character_descriptor["path"],
                   all_creature_source_counts=dict(distinct_bam_frames=char_counts["distinct_bam_frames"]+counts["distinct_bam_frames"]-overlapping_frames,
                       unique_source_work=char_counts["unique_work_items"]+len(work_groups)-shared),
                   remaining_gpu_work=None,
                   limits=["Source equality only; no automatic I/F/dep adoption across palette/profile/scale/recipe contracts.",
                           "Unknown palette contracts prevent an exact total of GPU tasks; model_candidate is a source diagnostic.",
                           "Centres, cycles, quadrants, equipment and consumers remain per occurrence, outside pixel keys.",
                           "Fourth BAM palette byte retained verbatim; comparison used RGB is not an assertion of runtime alpha compatibility.",
                           "Out-of-frame native cycle lookups retained exactly; their runtime meaning requires the native profile contract.",
                           "No crop, mirror, rotation, index remap, tolerance, native-source rewrite or GPU work."],
                   seconds=round(time.perf_counter()-started, 3))
    meta(db, "summary", summary)
    meta(db, "status", summary["status"])
    db.commit()
    require(not list(db.execute("PRAGMA foreign_key_check")), "invalid source-plan relationships")
    dump(output / "summary.json", summary)
    with (output / "animation-summary.csv").open("w", encoding="utf-8", newline="") as stream:
        records = list(db.execute("SELECT * FROM animation_statistics ORDER BY animation_id"))
        writer = csv.DictWriter(stream, fieldnames=records[0].keys())
        writer.writeheader()
        writer.writerows(dict(r) for r in records)
    db.close()
    character.close()
    monster.close()
    descriptor = dict(schema=SCHEMA, role="source-plan-not-production-or-QA", path=db_path.relative_to(ROOT).as_posix(),
                      bytes=db_path.stat().st_size, sha256=sha(db_path.read_bytes()),
                      summary=(output / "summary.json").relative_to(ROOT).as_posix(),
                      character_descriptor="sprite/index/palette-work-plan.json", monster_descriptor=monster_descriptor_path.relative_to(ROOT).as_posix(),
                      consumer="analyze_sprite_frame_dedup.py plan; encoded work requires the demonstrated per-profile plan and shared cache")
    dump(output / "plan.json", descriptor)
    print(json.dumps(summary, ensure_ascii=False), flush=True)


def plan(descriptor_path, ids):
    d = load(descriptor_path)
    require(d["schema"] == SCHEMA, "unknown source plan")
    path = ROOT / d["path"]
    require(path.stat().st_size == d["bytes"], "source plan size changed")
    db = ro(path)
    selected = {f"0x{int(a, 16):04X}" for a in ids} if ids else {r[0] for r in db.execute("SELECT animation_id FROM animations")}
    known = {r[0] for r in db.execute("SELECT animation_id FROM animations")}
    require(selected <= known, "selection outside non-Character plan; use palette_playable.py for Character")
    marks = ",".join("?" for _ in selected)
    # DISTINCT across the whole selection, never a sum of per-animation work.
    work = list(db.execute(f"SELECT DISTINCT w.work_id,i.model_candidate,c.character_work_id FROM animation_work a JOIN source_work w USING(work_id) JOIN inputs i USING(input_id) LEFT JOIN character_work_matches c USING(work_id) WHERE a.animation_id IN ({marks})", sorted(selected)))
    result = dict(animation_ids=sorted(selected), unique_source_work=len(work),
                  unique_model_candidate_work=sum(r["model_candidate"] for r in work),
                  source_work_shared_with_character=sum(r["character_work_id"] is not None for r in work),
                  remaining_gpu_work=None, production_started=False,
                  rule="unique source keys; validate palette/recipe/scale and cache before GPU; unknown contracts cannot be inferred")
    db.close()
    print(json.dumps(result, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("scan", "plan"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--descriptor", type=Path, default=POINTER)
    parser.add_argument("--animation-id", action="append")
    args = parser.parse_args()
    if args.command == "scan":
        require(args.output is not None, "scan requires a new --output")
        scan(args.output)
    else:
        plan(args.descriptor, args.animation_id)


if __name__ == "__main__":
    main()
