"""Seal pre-P2 evidence and design recommendations; no runtime implementation."""
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pipeline/scripts").is_dir())
OUTPUT = Path(__file__).resolve().parents[1]
P1 = OUTPUT.parent / "palette-q3m-p1-20260930-v1"
P0 = OUTPUT.parent / "palette-oracles-p0-20260930-v4"
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from bg2lib import load_key, resolve_resource
from palette_oracle import read_bam_p8
from workspace_paths import get_path


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    destination = OUTPUT / "verification.json"
    assert not destination.exists(), "Completed evidence is immutable"
    inputs, native, metrics = [json.loads((OUTPUT / f"{name}.json").read_text(encoding="utf-8-sig"))
                               for name in ("inputs", "native", "metrics")]
    assert all(r["status"] == "passed" for r in (inputs,native,metrics))
    assert native["source_unchanged"]
    experiment = json.loads((P1 / "experiment.json").read_text())
    p0 = json.loads((P0 / "audit.json").read_text())
    historical = json.loads((P0 / "verification.json").read_text())
    for relative, expected in historical["dependencies_sha256"].items():
        assert sha(ROOT / relative) == expected, f"P0 dependency changed: {relative}"
    game = get_path("bg2ee_game_root", required=True)
    model = get_path("reboutcx_model", required=True)
    local = {"config://bg2ee_game_root/BaldurReal.exe": sha(game / "BaldurReal.exe"),
             "config://bg2ee_game_root/chitin.key": sha(game / "chitin.key"),
             "config://reboutcx_model": sha(model)}
    assert local["config://bg2ee_game_root/BaldurReal.exe"] == p0["exe_sha256"]
    assert local["config://bg2ee_game_root/chitin.key"] == p0["key_sha256"]
    assert local["config://reboutcx_model"] == experiment["inference"]["model_sha256"]
    bifs, entries = load_key()
    live_sources = {}
    for name, meta in experiment["sources"].items():
        matches = [e for e in entries if e[0].upper() == name and e[1] == 1000]
        assert len(matches) == 1, f"Ambiguous/missing native BAM: {name}"
        raw, bif = resolve_resource(bifs, matches[0][2])
        canonical = read_bam_p8(raw)["canonical"]
        actual = hashlib.sha256(canonical).hexdigest()
        assert actual == meta["sha256"], f"Native source differs: {name}"
        live_sources[name] = {"bif": bif, "locator": hex(matches[0][2]), "canonical_sha256": actual}
    weights = Counter(o["key"] for o in experiment["occurrences"])
    weighted_rows = {}
    for table in ("color-frames", "sizes"):
        rows = list(csv.DictReader((P1 / f"{table}.csv").open(newline="")))
        assert all(int(r["occurrences"]) == weights[r["key"]] for r in rows)
        weighted_rows[table] = len(rows)
    tests = []
    for log in ("python-tests.log", "python-pipeline-tests.log"):
        data = (OUTPUT / log).read_text()
        match = re.search(r"Ran (\d+) tests", data)
        assert match and "\nOK\n" in data
        tests.append({"log": log, "tests": int(match[1]), "status": "passed"})
    native_log = (OUTPUT / "native-ctest.log").read_text()
    assert "100% tests passed, 0 tests failed out of 3" in native_log
    guide = ROOT / "sprite/Etudes_Sprite_codex_claude/GUIDE_DEFINITIF_SPRITES_HD_BG2EE.md"
    runtime = ROOT / "engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp"
    constants = re.findall(r"constexpr std::uint32_t k(?:Legacy|Xn)\w*RegistryVersion = (\d+);", runtime.read_text())
    assert sorted(map(int, constants)) == [1,2,3,4,5]
    tracked_changes = subprocess.run(["git","-C",str(ROOT),"diff","--name-only","HEAD"],
                                     check=True, text=True, capture_output=True).stdout.splitlines()
    assert not tracked_changes, f"Tracked user/source changes appeared: {tracked_changes}"
    source = "engine/InfinityEngine-Enhancer/source-patchee"
    decisions = {
        "candidate": "Q3m K6; logical F=0..7; no dithering; experimental only; REF regression retained",
        "version": "Recommend registry V6 under IEECSXN; constants currently occupy 1..5. Recheck/reserve explicitly in P2; catalog version is independent",
        "delivery": "Isolated homogeneous catalog V2 + new-version shards, memberships 0x6110 only; no monolithic/set support required initially",
        "geometry": "Existing x1 u16 width/height, signed i16 centres, transparent byte, complete frames/cycles/slots retained; N=w*h*scale^2 with scale 2 or 4",
        "source_identity": "Keep resource resref, SHA-256 of canonical BAM, counts and full cycle lookup; producer checks source. Runtime currently does not compare BAM bytes; live geometry checks remain",
        "representatives": "Keep 256 u16 source offsets / 0xFFFF provenance; do not invent representatives for newly used shades; new version removes representative-presence requirement for I",
        "dependency_mask": "Exact 32 bytes, little bit order; union(I) plus succ(I) only for F>0. Includes specials as stored by P1; normalize transparent palette entry before fingerprint/decode",
        "planes": "I=u8[N]; F optional u8[N] values 0..7 (3 significant bits, no bit packing). Absent F=0; writer omits all-zero F; reader accepts explicit all-zero F for identity",
        "compression": "Per-plane raw codec 0 or Windows XPRESS_HUFF codec 1; compressed only if strictly smaller; exact N decoded bytes. No other codec or packed-F mode",
        "profiles": "Separate u32 class-profile and decode-rule IDs (recommend ID 1 in each namespace), mapped explicitly to character-bg2ee-2.7.3.0 and ramp-lerp-srgb8-v1; reject unknown. Encoder ID stays producer provenance",
        "binary_layout_proposal": "LE registry header 24+8 bytes; resource header unchanged 48 bytes. Frame prefix existing 528 bytes (codec I byte9, F-present flag byte10, zero byte11), then 32-byte dep_mask + u32 Fstored + u8 Fcodec + 3 zero bytes: total568 before I then optional F. Cycles unchanged. Confirm final offsets in P2 specification/tests",
        "frontiers": "B unsupported in first implementation; reject any B/unknown flag",
        "decode": "For three native color bytes: (a*(8-f)+b*f+4)>>3; alpha copied from P[I]. F0 direct P[I]; legal successors never cross classes; specials/last shades require F0",
        "lut": "CPU scratch table of at most2048 dwords/frame decode; fill only used (I,F) pairs. F0 reads only primary. Full-palette LUT reads beyond exact dep_mask and must be avoided",
        "cache": "Fingerprint normalized realized colors selected by dep_mask plus native encoding and decode IDs; retain frame/shard generation and geometry/layout cache keys. Layer/actor snapshots stay separate; no palette cache keyed only by resref",
        "invalidation": "Relevant palette/alpha changes invalidate texture/composite; unused changes do not. Pulse invalidation follows actual dependencies; graphics forget/reset/context-generation invalidates GPU entries. Same-handle reset remains to prove in P2/P3",
        "residency": "Atomically load and pin I+F as one cached frame; sum their decoded bytes in existing budget/limits, avoid evicting I while loading F. Catalog index_bytes retains I semantics; F accounting separate",
        "composition": "Preserve native order, centres, union/borders and nonzero-DWORD overwrite; no new inter-layer blending; keep native pixel encoding and alpha unchanged",
        "failure": "Reject malformed headers, lengths, overflows, F, masks, profiles, flags and streams before exposing a frame; quarantine bad component; retain current native-BAM fallback. Q0/xBR is an explicit parallel A/B pack, not an existing automatic V5 fallback",
        "experimental_completion": "Reuse P1 sampled encoded frames; full native frame/cycle tables; keep indexed fallback for unsampled frames, identically in Q0 and Q3m packs. Do not infer full-family coverage from 144 samples",
    }
    plan = [
        {"step":1,"work":"Reserve registry version and finalize byte layout/profile ID table; add checked Python inspector and format tests",
         "files":["pipeline/scripts/run_creature_sprite_x2.py: inspect_registry, iter_catalog_record_logical_chunks, catalog_source_component_sha256"]},
        {"step":2,"work":"Import immutable P1 planes/dep masks with source geometry and complete resource tables; write new shards; compute versioned logical digests including profiles/I/F/dep",
         "files":["pipeline/scripts/run_creature_sprite_x2.py: write_compressed_catalog_registry_records, inspect_registry_catalog, catalog_*_digest, write_registry_catalog_index",
                  "pipeline/scripts/reboutcx_catalog.py: resource_contract_digest",
                  "pipeline/scripts/reboutcx_full.py and reboutcx_cpu_p10.py: legacy V3/representative assumptions; new path must not silently relax old checks"]},
        {"step":3,"work":"Implement checked native reader/decompression and atomic I/F residency; preserve old reader versions",
         "files":[f"{source}/src/iee/creature_sprite_x2.cpp: Frame, registry_read_limit, parse_registry, catalog_shard_matches, frame_indices_locked"]},
        {"step":4,"work":"Implement integer decode, masked fingerprint, upload/composite and reset lifecycle with existing per-layer snapshots",
         "files":[f"{source}/src/iee/creature_sprite_x2.cpp: palette_fingerprint, upload_frame_locked, compose_composite_pixels_locked, forget_engine_textures",
                  f"{source}/src/iee/hooks.cpp: observe existing owner/generation snapshot path; modify only if a targeted test demonstrates necessity"]},
        {"step":5,"work":"Native golden/format/cache regression tests; small Q0/Q3m packs and compatible DLL, build/ctest plus pack inspections. Stop before installation/P3",
         "files":["pipeline/tests/test_*palette* and catalog tests",f"{source}/tests/iee_tests.cpp",f"{source}/CMakeLists.txt"]},
    ]
    future_tests = [
        "Compare actual native production Q3m decoder against all32832 golden outputs, then synthetic arbitrary alpha/BGRA/packed-native cases; fixture export/converter required",
        "Absent F and explicit all-zero F byte-identical to old indexed upload/composite, including transparent, shadow, reserved indices, negative centres and placeholders",
        "Raw/XPRESS I/F writer-reader roundtrip and canonical digests, streamed/lazy frame access, homogeneous catalog rules, memberships and same-BAM disjoint actor routing",
        "Reject truncated header/I/F/cycles; forged dimensions/counts/offsets/lengths and overflow; F8..255, nonzero F on special/terminal indices; missing/excess dep bits; unknown profile/rule/flags/codec; corrupted XPRESS and wrong decompressed size",
        "Mutating used primary/successor/alpha changes fingerprint/output; changing unused entry does neither; F0 successor excluded; per-layer and two actors with same BAM/different palettes stay independent",
        "Palette sequences simulating pulse effects, reset/context replacement/texture-ID reuse, payload/cache eviction and I+F pinning; composition retains order/borders/double layers",
        "Verify malformed experimental component falls back to native without using partial/stale output; no regression to V1..V5/catalog/set baseline",
        "Measure actual new-header/representatives/file size, CPU rebuild time and I+F/texture residency on small pack; P1 plane ratios exclude full binary overhead",
    ]
    risks = [
        "REF error regression is real and repeated; do not adopt globally before user P3 A/B. If unacceptable, new immutable P1 run with REF reweighting",
        "Synthetic golden alpha does not prove runtime shadows/invisibility/pulses or post-palette modulation, native layer order in real equipment scenes, cadence or graphical reset behaviour",
        "P1 covers144 distinct frames (180 occurrences), not full5175 source frames; full source topology/fallback must be preserved in experimental pack",
        "Catalog version/digest and source registry version have independent meanings; old producers/inspectors and legacy representative assumptions cannot be reused unchanged",
        "Runtime source SHA currently metadata only; decide separately whether to reject native-BAM mod mismatch beyond draw-time geometry checks",
        "ReboutCX distribution/license remains unresolved; does not block local pre-P2 checks, does block any inferred release authorization",
    ]
    report = {
        "schema":"bg2-upscale-character-pre-p2-verification-v1", "status":"passed",
        "created_utc":datetime.now(timezone.utc).isoformat(), "ready_to_begin_p2":True,
        "p2_started":False,"p3_started":False,"installation_performed":False,"committed":False,
        "tracked_sources_unchanged":True,"native_baseline_only":True,
        "python_tests":tests,"python_tests_total":sum(t["tests"] for t in tests),"native_ctest_suites_passed":3,
        "toolchain":{"cmake":"4.0.2","msvc":"19.29.30158.0","toolset":"v142","sdk":"10.0.19041.0","architecture":"x64","configuration":"Release","warnings_as_errors":False},
        "summary":{"reference_decodings":inputs["golden"]["reference_decodings"],
                   "synthetic_rgba_bgra_decodings":inputs["golden"]["synthetic_alpha_bgra_cases"],
                   "xpress_roundtrips":inputs["checks"]["xpress_roundtrips"],
                   "frame_scale_pairs":inputs["checks"]["frames_scales"],"encoded_variants":inputs["checks"]["variants"],
                   "metric_rows_recomputed":metrics["frame_metric_rows"],"summary_rows_recomputed":metrics["summary_rows"],
                   "metric_maximum_difference":metrics["maximum_absolute_difference"],
                   "ref_error_increase_percent":metrics["ref_error_increase_percent"]},
        "live_local_inputs_sha256":local,"native_bam_provenance":live_sources,
        "occurrence_weights":{"occurrences":len(experiment["occurrences"]),"unique_frames":len(weights),"rows_checked":weighted_rows},
        "guide":{"path":guide.relative_to(ROOT).as_posix(),"sha256":sha(guide),"modified":False,
                 "clarifications":["§8.5 full2048 LUT vs exact dep_mask: only populate actually used pairs",
                                   "§8.5 pulse every frame: conditional on changed dependencies",
                                   "§11 P2 fallback V5/xBR: current invalid-catalog fallback is native BAM",
                                   "§8 V6 logical specification: concrete byte layout/version allocation still required; no current implementation"]},
        "format_and_runtime_decisions":decisions,"p2_implementation_order":plan,
        "p2_offgame_tests_required_before_p3":future_tests,"risks_and_open_questions":risks,
        "evidence_sha256":{p.relative_to(OUTPUT).as_posix():sha(p) for p in sorted(OUTPUT.rglob("*")) if p.is_file() and p != destination},
    }
    destination.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("status","ready_to_begin_p2","p2_started","python_tests_total","native_ctest_suites_passed","summary")},indent=2))


if __name__ == "__main__":
    main()
