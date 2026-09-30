"""Finalize offline P0: independent/native oracles and historical E3b reproduction.

Use config://chainner_python. Commands write a NEW versioned research directory;
no production, QA, installation or release mutation.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import shutil
import sys
import time

import numpy as np
from PIL import Image

from palette_oracle import EXE_SHA256, NativeMix, read_bam_p8, scalar_palette
from workspace_paths import get_path

ROOT = Path(__file__).resolve().parents[2]
STUDIES = ROOT / "sprite/Etudes_Sprite_codex_claude"
CODEX = STUDIES / "CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29"
CLAUDE = STUDIES / "ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere"
FAMILY = ROOT / "sprite/families/playable-characters/6110-human-female-fighter"
E3B_SHA256 = "7566a7d62f6eb89b9a1270526d1f9c678837b8800819f281bac124e4669c75b6"
MODEL_SHA256 = "c36a14ddb51ae094324a53b67c345da2d6b6bbf6a2249726056d5b94bdedab05"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def write_json(path, value):
    if path.exists():
        raise ValueError(f"refusing to overwrite a result: {path}")
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def audit(output):
    from bam_export import decode_bam
    from bg2lib import KEY_PATH, load_key, resolve_resource
    from palette_eval import corpus, native_resources, palette_plan
    from reboutcx_batch import load_palette_profiles
    from reboutcx_quantize import character_chmb1_palette_rgb
    from run_creature_sprite_x2 import bam_cycles, canonical_bam

    started = time.monotonic()
    resources, identities = native_resources()
    gradients = np.asarray(Image.open(io.BytesIO(resources["MPALETTE"])).convert("RGB"))
    plan, _, _ = palette_plan(resources)
    rng = np.random.default_rng(6110)
    cases = [(record["name"], gradients[record["rows"]]) for record in plan]
    cases += [(f"random-{n}", rng.integers(0, 256, (7, 12, 3), dtype=np.uint8)) for n in range(512)]
    exe = get_path("bg2ee_game_root", required=True) / "BaldurReal.exe"
    with NativeMix(exe) as native:
        for name, ramps in cases:
            expected = native(ramps)
            if not np.array_equal(expected, scalar_palette(ramps)):
                raise ValueError(f"scalar/native palette mismatch: {name}")
            if not np.array_equal(expected, character_chmb1_palette_rgb(ramps)):
                raise ValueError(f"production/native palette mismatch: {name}")
        # Every byte sum (including odd sums and >255) through native code.
        ramps = np.zeros((7, 12, 3), np.uint8)
        for a in range(256):
            ramps[0] = a
            for b in range(256):
                ramps[1] = b
                if not np.all(native(ramps)[88:96] == (a + b) // 2):
                    raise ValueError(f"native average mismatch: {a},{b}")
        fragment_sha = native.fragment_sha256
    np.savez_compressed(output / "neutral-palette-golden.npz",
                        ramps=np.stack([ramps for _, ramps in cases]),
                        expected_rgb=np.stack([scalar_palette(ramps) for _, ramps in cases]))

    # New jobs use MPALETTE; old pinned jobs keep their exact evidence/cache key.
    original = json.loads((FAMILY / "chff4/jobs/reboutcx-p12-cache86-v1.json").read_text())
    legacy_profiles, legacy_evidence = load_palette_profiles(original)
    canonical = json.loads(json.dumps(original))
    native_identity = identities["MPALETTE"]
    canonical["palette_reference"]["source"] = {
        "resource": "MPALETTE", "type": 1, **native_identity,
        "locator": f"0x{int(native_identity['locator'], 16):08X}",
        "bif": native_identity["bif"].replace("\\", "/"),
    }
    profiles, evidence = load_palette_profiles(canonical)
    if profiles[0]["sha256"] != legacy_profiles[0]["sha256"]:
        raise ValueError("canonical palette changes legacy pixels")
    if any(legacy_evidence[key] != original["palette_reference"][key] for key in ("id", "profiles")):
        raise ValueError("legacy profile evidence differs")
    expected_source = {**original["palette_reference"]["source"], "dimensions": [12, 256]}
    if legacy_evidence["source"] != expected_source:
        raise ValueError("legacy provenance/cache identity differs")

    stats, records, clipped = Counter(), [], []
    bifs, key_entries = load_key()
    # Native stock resources already extracted by the study, no extraction edits.
    for path in sorted((CODEX / "vanilla_inventory").glob("*.BAM")):
        raw = path.read_bytes()
        oracle = read_bam_p8(raw)
        entries = [entry for entry in key_entries if entry[0].upper() == path.stem.upper() and entry[1] == 1000]
        if len(entries) != 1:
            raise ValueError(f"native BAM identity differs: {path.name}")
        native_raw, bif = resolve_resource(bifs, entries[0][2])
        if canonical_bam(native_raw)[0] != oracle["canonical"]:
            raise ValueError(f"stock BAM bytes differ: {path.name}")
        legacy_frames, palette, transparent = decode_bam(oracle["canonical"])
        if transparent != oracle["transparent"] or not np.array_equal(palette, oracle["palette_rgb"]):
            raise ValueError(f"BAM palette differs: {path.name}")
        if oracle["cycles"] != bam_cycles(oracle["canonical"]):
            raise ValueError(f"BAM topology differs: {path.name}")
        for frame, (pixels, cx, cy, _) in zip(oracle["frames"], legacy_frames, strict=True):
            stats["frames"] += 1
            stats["rle_frames" if frame["compressed"] else "raw_frames"] += 1
            if frame["rle_tail_overflow"]:
                stats["clipped_rle_frames"] += 1
                clipped.append({"resource": path.stem, "frame": frame["index"],
                                "excess_transparent_pixels": frame["rle_tail_overflow"]})
            if not frame["width"] or not frame["height"]:
                stats["zero_geometry_frames"] += 1
                # Legacy decoder intentionally substitutes a 1x1 marker.
                continue
            stats["pixels"] += frame["width"] * frame["height"]
            stats["negative_centres"] += int(frame["center_x"] < 0 or frame["center_y"] < 0)
            stats["one_by_one_frames"] += int(frame["width"] == frame["height"] == 1)
            if (cx, cy) != (frame["center_x"], frame["center_y"]) or not np.array_equal(pixels, frame["indices"]):
                raise ValueError(f"BAM frame differs: {path.name}/{frame['index']}")
        cycles = oracle["cycles"]
        slots = sum(len(cycle["frame_indices"]) for cycle in cycles)
        repeated = sum(sum(a == b for a, b in zip(cycle["frame_indices"], cycle["frame_indices"][1:])) for cycle in cycles)
        stats.update({"resources": 1, "cycles": len(cycles), "lookup_slots": slots,
                      "repeated_adjacent_slots": repeated,
                      "empty_cycles": sum(not cycle["frame_indices"] for cycle in cycles),
                      "bamc_resources": int(oracle["packed"])})
        records.append({"path": relative(path), "sha256": hashlib.sha256(raw).hexdigest(),
                        "native_locator": f"0x{entries[0][2]:08X}", "bif": bif,
                        "native_raw_sha256": hashlib.sha256(native_raw).hexdigest(),
                        "frames": len(oracle["frames"]), "cycles": len(cycles), "slots": slots})
    if not records:
        raise ValueError("empty BAM corpus")
    _, _, occurrences, corpus_sources = corpus()
    idle_durations = {}
    for layer in ("body", "helmet", "shield", "weapon"):
        idle_durations[layer] = [item["dwell_slots"] for item in occurrences
                                if item["group"] == "E3b" and item["sequence"] == "idle_s" and item["layer"] == layer]
    write_json(output / "bam-resources.json", records)
    write_json(output / "audit.json", {
        "schema": "bg2-upscale-palette-p0-audit-v1", "status": "passed",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "0x6110 stock BAM study inventory + P1 corpus; offline only",
        "key_sha256": digest(Path(KEY_PATH)), "exe_sha256": EXE_SHA256,
        "resources": identities,
        "neutral_rgb_oracle": {"palettes": len(cases), "rgb_bytes_per_palette": 768,
                               "native_scalar_production_differing_bytes": 0,
                               "exhaustive_native_byte_pairs": 65536,
                               "fragment_rva": [hex(0x421F7B), hex(0x42201E)],
                               "fragment_sha256": fragment_sha,
                               "excludes": ["RealizeRange lighting/effects", "final colour packing/green-key avoidance", "runtime alpha", "post-palette effects"]},
        "provenance": {"new_source": evidence["source"], "legacy_evidence_unchanged": True,
                       "legacy_and_canonical_rgb_equal": True, "aliases_byte_identical": True},
        "bam": dict(stats), "bam_differences": 0, "clipped_native_rle": clipped,
        "timing": {"unit": "native lookup slot; no time/FPS field in BAM V1",
                   "e3b_idle_dwell_slots": idle_durations,
                   "runtime_seconds": None, "runtime_clock_validation_phase": "P3"},
        "p1_corpus_sources": corpus_sources, "elapsed_seconds": time.monotonic() - started,
    })
    print(json.dumps(dict(stats)), flush=True)


def compare_json(expected, actual, prefix="") -> dict:
    """All legacy leaves/keys must agree; report max numerical delta and count."""
    stats = {"numeric_leaves": 0, "different_leaves": 0, "max_abs_delta": 0.0}

    def visit(a, b, path):
        if isinstance(a, dict) and isinstance(b, dict):
            if a.keys() != b.keys():
                raise ValueError(f"JSON keys differ at {path}")
            for key in a:
                visit(a[key], b[key], f"{path}/{key}")
        elif isinstance(a, list) and isinstance(b, list):
            if len(a) != len(b):
                raise ValueError(f"JSON lengths differ at {path}")
            for index, (aa, bb) in enumerate(zip(a, b)):
                visit(aa, bb, f"{path}/{index}")
        elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
            stats["numeric_leaves"] += 1
            stats["max_abs_delta"] = max(stats["max_abs_delta"], abs(a - b))
            stats["different_leaves"] += int(a != b)
        else:
            stats["different_leaves"] += int(a != b)
    visit(expected, actual, prefix)
    return stats


def e3b(output):
    source = CLAUDE / "outils/e3b_experiment.py"
    expected_path = CLAUDE / "donnees_v2/e3b_results.json"
    if digest(source) != E3B_SHA256 or digest(get_path("reboutcx_model", required=True)) != MODEL_SHA256:
        raise ValueError("historical source or model hash differs")
    from palette_eval import native_resources
    raw, identities = native_resources()
    ramps = np.asarray(Image.open(io.BytesIO(raw["MPALETTE"])).convert("RGB"))
    np.save(output / "mpalette.npy", ramps)
    text = source.read_text(encoding="utf-8")
    begin = '    for frame_sel in [("idle_s", 0), ("walk_s", 3)]:'
    end = '    # display simulation (zoom z, NEAREST vs area) for REF idle 0'
    png_begin = '            if z in (1.3, 2.0) and m in ("xBR", "Q0_used_nodither", "Q2_bayer4", "Q8_frac_multipal_boundary"):'
    png_end = '    res = json.load(open(OUT / "e3_results.json"))'
    if any(text.count(anchor) != 1 for anchor in (begin, end, png_begin, png_end)):
        raise ValueError("historical instrumentation anchor differs")
    # Skip sheets/tiles/GIF output, retaining composite + display simulation
    # so ALL historical JSON metrics, including display MAE, are reproduced.
    instrumented = text[:text.index(begin)] + text[text.index(end):]
    instrumented = instrumented[:instrumented.index(png_begin)] + instrumented[instrumented.index(png_end):]
    instrumented = instrumented.replace("G:/AI/BG2_Upscale", ROOT.as_posix())
    (output / "provenance/e3b_no_visuals.py").write_text(instrumented, encoding="utf-8")
    previous = sys.argv
    try:
        sys.argv = [str(source), str(output), str(output / "mpalette.npy")]
        namespace = {"__name__": "p0_e3b", "__file__": str(source)}
        exec(compile(instrumented, str(source), "exec"), namespace)
        namespace["main"]()
    finally:
        sys.argv = previous
    actual_path = output / "e3_results.json"
    actual = json.loads(actual_path.read_text())
    expected = json.loads(expected_path.read_text())
    comparison = compare_json(expected, actual)
    write_json(output / "e3b-reproduction.json", {
        "status": "passed" if not comparison["different_leaves"] else "failed",
        "source": relative(source), "source_sha256": E3B_SHA256,
        "historical_results": relative(expected_path), "historical_results_sha256": digest(expected_path),
        "new_results_sha256": digest(actual_path), "model_sha256": MODEL_SHA256,
        "mpalette": identities["MPALETTE"], "comparison": comparison,
        "protocol": "original E3b: CUDA0 fp16 batch1 unpadded; x4 RGB u8 + BOX x2 RGB u8; 4-bit Q3m/Q8; original temporal sign",
        "corrected_evaluation": "P1 palette_eval.py; do not use E3b original flicker for P2 selection",
    })
    print(json.dumps(comparison), flush=True)
    if comparison["different_leaves"]:
        raise ValueError("historical E3b reproduction differs")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("audit", "e3b"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.relative_to((FAMILY / "research").resolve())
    targets = ("audit.json", "bam-resources.json", "neutral-palette-golden.npz") if args.command == "audit" else (
        "e3_results.json", "e3b-reproduction.json", "mpalette.npy", "provenance/e3b_no_visuals.py")
    if any((output / name).exists() for name in targets):
        raise ValueError("use a new run; existing result is immutable")
    (output / "provenance").mkdir(parents=True, exist_ok=True)
    for name in ("palette_oracle.py", "palette_p0.py", "reboutcx_batch.py", "reboutcx_quantize.py"):
        target = output / "provenance" / name
        if not target.exists():
            shutil.copyfile(ROOT / "pipeline/scripts" / name, target)
        elif digest(target) != digest(ROOT / "pipeline/scripts" / name):
            raise ValueError(f"run code snapshot changed: {name}")
    {"audit": audit, "e3b": e3b}[args.command](output)


if __name__ == "__main__":
    main()
