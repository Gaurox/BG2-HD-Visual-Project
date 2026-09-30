"""Pre-P2 checks only: existing P0/P1 inputs; no writer, DLL decoder or inference."""
from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time

import numpy as np
from PIL import Image

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pipeline/scripts").is_dir())
OUTPUT = Path(__file__).resolve().parents[1]
P1 = OUTPUT.parent / "palette-q3m-p1-20260930-v1"
P0 = OUTPUT.parent / "palette-oracles-p0-20260930-v4"
sys.path.insert(0, str(ROOT / "pipeline/scripts"))

import palette_frac_encode as encoder
import palette_eval as evaluation
from palette_oracle import read_bam_p8, scalar_palette
from bam_export import decode_bam
from run_creature_sprite_x2 import WindowsXpressHuffCodec


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def scalar_successor(i):
    if i < 4:
        return i
    start, size = (4, 12) if i < 88 else (88, 8)
    return i if (i - start) % size == size - 1 else i + 1


def scalar_decode(palette, pairs):
    rows = []
    for i, f in pairs:
        a, b = palette[i], palette[scalar_successor(i)]
        rows.append([((8-f)*int(a[c]) + f*int(b[c]) + 4)//8 for c in range(3)] + [int(a[3])])
    return np.asarray(rows, dtype=np.uint8)


def main():
    result_path = OUTPUT / "inputs.json"
    require(not result_path.exists(), "completed input audit is immutable")
    started = time.monotonic()
    experiment = json.loads((P1 / "experiment.json").read_text())
    result = json.loads((P1 / "result.json").read_text())
    target_index = json.loads((P1 / "target-index.json").read_text())
    historical = json.loads((P0 / "verification.json").read_text())
    proof_hashes = {}
    for name, expected in historical["result_sha256"].items():
        actual = digest(P0 / name)
        require(actual == expected, f"historical P0 proof changed: {name}")
        proof_hashes[f"P0/{name}"] = actual
    for name, expected in json.loads((P1 / "verification.json").read_text())["new_files"].items():
        actual = digest(P1 / name)
        require(actual == expected, f"historical P1 proof changed: {name}")
        proof_hashes[f"P1/{name}"] = actual
    script_hashes = {}
    for name, expected in experiment["code_sha256"].items():
        actual = digest(ROOT / "pipeline/scripts" / name)
        script_hashes[name] = {"p1_sha256": expected, "current_sha256": actual,
                               "same": expected == actual}
    require(script_hashes["palette_frac_encode.py"]["same"], "P1 encoder bytes changed")

    raw, native_ids = evaluation.native_resources()
    require(native_ids == experiment["native_resources"], "native resource provenance changed")
    plan, palettes, palette_checks = evaluation.palette_plan(raw)
    require(plan == experiment["palettes"], "palette plan changed")
    require(palette_checks == experiment["palette_checks"], "palette disjointness changed")
    gradients = np.asarray(Image.open(io.BytesIO(raw["MPALETTE"])).convert("RGB"))
    for record in plan:
        require(np.array_equal(palettes[record["name"]], scalar_palette(gradients[record["rows"]])),
                f"neutral scalar palette differs: {record['name']}")

    with np.load(P1 / "decoder-golden.npz", allow_pickle=False) as z:
        gp, gi, gf, ge = (z[name].copy() for name in ("palettes_rgba", "I", "F", "expected_rgba"))
    require(gp.shape == (18, 256, 4) and gi.shape == gf.shape == (1824,) and
            ge.shape == (18, 1824, 4), "golden shapes")
    require(all(a.dtype == np.uint8 for a in (gp, gi, gf, ge)), "golden dtypes")
    pairs = [(i, f) for i in range(256) for f in (range(8) if scalar_successor(i) != i else (0,))]
    require(pairs == list(zip(gi.tolist(), gf.tolist())), "golden is not the complete ordered legal pair set")
    for n, record in enumerate(plan):
        expected_palette = np.column_stack((palettes[record["name"]], np.full(256, 255, np.uint8)))
        expected_palette[0] = 0  # Runtime forces the transparent DWORD to zero.
        expected_palette[1, 3] = 128  # Fixture shadow alpha is synthetic, not captured.
        require(np.array_equal(gp[n], expected_palette), "golden palette provenance/alpha")
        require(np.array_equal(ge[n], scalar_decode(gp[n], pairs)), "golden scalar RGBA mismatch")
        require(np.array_equal(ge[n], encoder.decode(gi[None], gf[None], gp[n])[0]),
                "golden NumPy RGBA mismatch")
    # Synthetic arbitrary alpha and BGRA cases, without claiming runtime captures.
    rng = np.random.default_rng(6110)
    synthetic_cases = 0
    for _ in range(32):
        p = rng.integers(0, 256, (256, 4), dtype=np.uint8)
        for order in ((0, 1, 2, 3), (2, 1, 0, 3)):
            native = p[:, order].copy()
            require(np.array_equal(encoder.decode(gi[None], gf[None], native)[0],
                                   scalar_decode(native, pairs)), "synthetic alpha/BGRA mismatch")
            synthetic_cases += len(pairs)
        all_i = np.arange(256, dtype=np.uint8)[None]
        require(np.array_equal(encoder.decode(all_i, np.zeros_like(all_i), p)[0], p), "F zero identity")

    sources = {}
    frame_total = pixels_total = 0
    for resref, meta in experiment["sources"].items():
        path = ROOT / meta["canonical_bam"]
        require(digest(path) == meta["sha256"], f"BAM source bytes changed: {resref}")
        bam = read_bam_p8(path.read_bytes())
        require(bam["cycles"] == meta["cycles"], f"BAM cycle topology: {resref}")
        old_frames, rgb, transparent = decode_bam(bam["canonical"])
        require(transparent == bam["transparent"] and np.array_equal(rgb, bam["palette_rgb"]),
                f"BAM palette/transparency: {resref}")
        require(len(old_frames) == len(bam["frames"]), "BAM frame counts")
        for old, frame in zip(old_frames, bam["frames"], strict=True):
            # This corpus has no declared zero-size frames; no normalization is introduced.
            require((old[0].shape[1], old[0].shape[0], old[1], old[2]) ==
                    (frame["width"], frame["height"], frame["center_x"], frame["center_y"]),
                    f"BAM geometry: {resref}/{frame['index']}")
            require(np.array_equal(old[0], frame["indices"]), "BAM index plane differs")
        sources[resref] = bam
        frame_total += len(bam["frames"])
        pixels_total += sum(f["indices"].size for f in bam["frames"])

    size_rows = {(r["key"], int(r["scale"]), r["method"]): r for r in
                 csv.DictReader((P1 / "sizes.csv").open(newline=""))}
    methods = ("xBR", "Q0", "Q6-k3", "Q3m-k3", "Q6-k4", "Q3m-k4", "Q6-k6", "Q3m-k6")
    checks = {"frames_scales": 0, "variants": 0, "class_leaks": 0, "changed_specials": 0,
              "xpress_roundtrips": 0, "unrepresented_primary_pixels_q3m_k6": 0,
              "unrepresented_successor_pixels_q3m_k6": 0, "target_arrays": 0,
              "fractional_pixels_all_q3m": 0, "dependency_entries_q3m_k6": 0}
    local_hashes = {}
    source_coverage = {}
    with WindowsXpressHuffCodec(compress=True) as compressor, WindowsXpressHuffCodec(compress=False) as decompressor:
        for key, info in experiment["frames"].items():
            source = sources[info["resref"]]["frames"][info["frame"]]
            require(info["size"] == [source["width"], source["height"]] and
                    info["center"] == [source["center_x"], source["center_y"]], "P1 frame identity")
            source_coverage.setdefault(info["resref"], set()).add(info["frame"])
            used = np.zeros(256, bool)
            used[np.unique(source["indices"])] = True
            for scale in (2, 4):
                shape = (source["height"]*scale, source["width"]*scale)
                ep = P1 / "encoded" / f"{key}-x{scale}.npz"
                gp_path = P1 / "guides" / f"{key}-x{scale}.npz"
                local_hashes[ep.relative_to(P1).as_posix()] = digest(ep)
                local_hashes[gp_path.relative_to(P1).as_posix()] = digest(gp_path)
                with np.load(gp_path, allow_pickle=False) as z:
                    guide = z["guide"].copy()
                require(guide.shape == shape and guide.dtype == np.uint8, "guide geometry/type")
                with np.load(ep, allow_pickle=False) as z:
                    require(set(z.files) == {f"{m}_{s}" for m in methods for s in ("I", "F", "dep")},
                            "encoded fields differ")
                    for method in methods:
                        i, f, mask = (z[f"{method}_{s}"] for s in ("I", "F", "dep"))
                        require(i.shape == f.shape == shape and i.dtype == f.dtype == mask.dtype == np.uint8 and
                                mask.shape == (32,), "encoded geometry/type")
                        c = encoder.check_contract(guide, i, f, mask)
                        for label in ("class_leaks", "changed_specials"):
                            checks[label] += c[label]
                        if method.startswith("Q3m"):
                            checks["fractional_pixels_all_q3m"] += c["fractional_pixels"]
                        if method == "Q3m-k6":
                            checks["unrepresented_primary_pixels_q3m_k6"] += int(np.count_nonzero(~used[i]))
                            checks["unrepresented_successor_pixels_q3m_k6"] += int(np.count_nonzero(
                                (f > 0) & ~used[encoder.successors()[i]]))
                            checks["dependency_entries_q3m_k6"] += c["dependency_entries"]
                        if not method.startswith("Q3m"):
                            require(not np.any(f), "indexed method has fractions")
                        row = size_rows[(key, scale, method)]
                        data = {"I": i.tobytes(), "F": f.tobytes() if np.any(f) else b""}
                        lengths = {}
                        for plane, payload in data.items():
                            compressed = compressor.encode(payload) if payload else b""
                            lengths[plane] = (len(payload), len(compressed))
                            require(len(payload) == int(row[f"{plane}_raw"]) and
                                    len(compressed) == int(row[f"{plane}_xpress"]), "recorded plane size differs")
                            if payload:
                                require(decompressor.decode(compressed, len(payload)) == payload, "XPRESS roundtrip")
                                checks["xpress_roundtrips"] += 1
                        require(sum(min(a,b) for a,b in lengths.values()) == int(row["stored_plane_bytes"]),
                                "stored size policy differs")
                        checks["variants"] += 1
                checks["frames_scales"] += 1
            for name, refs in target_index["references"].items():
                path = P1 / refs[key]
                local_hashes[path.relative_to(P1).as_posix()] = digest(path)
                with np.load(path, allow_pickle=False) as z:
                    for scale in (2,4):
                        t = z[f"x{scale}"]
                        require(t.shape == (source["height"]*scale, source["width"]*scale, 3) and
                                t.dtype == np.float32 and np.isfinite(t).all() and
                                np.all((t >= 0) & (t <= 1)), "target shape/type/range")
                        checks["target_arrays"] += 1
    require(checks["fractional_pixels_all_q3m"] == result["checks"]["fractional_pixels"], "fractional pixel count")
    require(len(size_rows) == checks["variants"], "sizes CSV completeness")
    with (P1 / "color-summary.csv").open(newline="") as stream:
        summary = list(csv.DictReader(stream))
    for row in summary:
        row["scale"] = int(row["scale"])
        for field in ("pixel_weighted_mean", "gain_vs_Q0_percent"):
            row[field] = float(row[field]) if row[field] else None
    decisions = evaluation.choose_k(summary)
    require(json.loads(json.dumps(decisions)) == result["decisions"], "K selection differs from P1")
    q3_rows = [r for r in summary if r["method"] == "Q3m-k6" and r["mask"] == "recolorable"]
    require(all(float(r["gain_vs_Q0_percent"]) > 0 for r in q3_rows if r["role"] == "validation"),
            "Q3m does not improve every validation")
    coverage = {r: {"source_frames": len(b["frames"]), "p1_unique_frames": len(source_coverage.get(r, set())),
                     "unsampled_frames": len(b["frames"])-len(source_coverage.get(r, set())),
                     "cycles": len(b["cycles"]),
                     "null_1x1_index2": sum(f["indices"].shape == (1,1) and int(f["indices"][0,0]) == 2
                                             for f in b["frames"]),
                     "negative_centres": sum(f["center_x"] < 0 or f["center_y"] < 0 for f in b["frames"])}
                for r,b in sources.items()}
    report = {"schema": "bg2-upscale-character-pre-p2-inputs-v1", "status": "passed",
              "created_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic()-started,
              "scope": "existing P0/P1 inputs only; no inference, registry, DLL decoder or game execution",
              "proof_hashes": proof_hashes, "script_provenance": script_hashes,
              "native_resources": native_ids, "palette_checks": palette_checks,
              "golden": {"reference_decodings": len(plan)*len(pairs), "different_bytes": 0,
                         "synthetic_alpha_bgra_cases": synthetic_cases, "native_cpp_comparison": "P2 pending",
                         "runtime_alpha_effects": "P3 pending"},
              "source_bams": {"resources": len(sources), "frames": frame_total, "pixels": pixels_total,
                              "coverage": coverage}, "checks": checks,
              "decisions": decisions, "q3m_k6_color_summary": q3_rows,
              "local_inputs_sha256": local_hashes,
              "remaining_p2": ["binary writer/reader", "golden C++ comparison", "native Q3m cache/reset tests",
                               "experimental pack and compatible DLL"]}
    result_path.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("status", "elapsed_seconds", "golden", "checks")}, indent=2))


if __name__ == "__main__":
    main()
