"""Recompute saved P1 Q0/Q3m-K6 color metrics; no encoding or inference."""
from collections import defaultdict
from datetime import datetime, timezone
import csv
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

ROOT = next(p for p in Path(__file__).resolve().parents if (p / "pipeline/scripts").is_dir())
OUTPUT = Path(__file__).resolve().parents[1]
P1 = OUTPUT.parent / "palette-q3m-p1-20260930-v1"
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from palette_eval import color_errors, native_resources, palette_plan
from palette_frac_encode import decode


def main():
    destination = OUTPUT / "metrics.json"
    assert not destination.exists(), "Completed audit is immutable"
    start = time.monotonic()
    experiment = json.loads((P1 / "experiment.json").read_text())
    references = json.loads((P1 / "target-index.json").read_text())["references"]
    plan, palettes, _ = palette_plan(native_resources()[0])
    methods = ("Q0", "Q3m-k6")
    frames = {(r["key"], int(r["scale"]), r["method"], r["palette"], r["mask"]): r
              for r in csv.DictReader((P1 / "color-frames.csv").open(newline=""))
              if r["method"] in methods}
    summary = {(int(r["scale"]), r["method"], r["palette"], r["mask"]): r
               for r in csv.DictReader((P1 / "color-summary.csv").open(newline=""))
               if r["method"] in methods}
    groups = defaultdict(list)
    checked = 0
    max_delta = 0.0

    def compare(actual, recorded):
        nonlocal max_delta
        expected = float(recorded) if recorded != "" else None
        if actual is None or expected is None:
            assert actual is expected
        else:
            max_delta = max(max_delta, abs(actual - expected))
            assert math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), (actual, expected)

    for key in experiment["frames"]:
        targets = {}
        for record in plan:
            name = record["name"]
            with np.load(P1 / references[name][key], allow_pickle=False) as z:
                targets[name] = {s: z[f"x{s}"] for s in (2, 4)}
        for scale in (2, 4):
            with np.load(P1 / "guides" / f"{key}-x{scale}.npz", allow_pickle=False) as z:
                guide = z["guide"]
            with np.load(P1 / "encoded" / f"{key}-x{scale}.npz", allow_pickle=False) as z:
                for method in methods:
                    i, f = z[f"{method}_I"], z[f"{method}_F"]
                    for name, palette in palettes.items():
                        metrics = color_errors(decode(i, f, palette), targets[name][scale], guide)
                        for mask, measured in metrics.items():
                            old = frames[(key, scale, method, name, mask)]
                            assert measured["pixels"] == int(old["pixels"])
                            compare(measured["sum"], old["sum"])
                            compare(measured["mean"], old["mean"])
                            groups[(scale, method, name, mask)].append((int(old["occurrences"]), measured))
                            checked += 1
    assert checked == len(frames)
    means = {}
    for identity, rows in groups.items():
        pixels = sum(w*m["pixels"] for w,m in rows)
        total = sum(w*m["sum"] for w,m in rows)
        supported = [(w,m) for w,m in rows if m["pixels"]]
        average = total/pixels if pixels else None
        frame_average = sum(w*m["mean"] for w,m in supported)/sum(w for w,m in supported) if supported else None
        old = summary[identity]
        assert pixels == int(old["pixels"])
        compare(average, old["pixel_weighted_mean"])
        compare(frame_average, old["frame_unweighted_mean"])
        means[identity] = average
    assert len(groups) == len(summary)
    for (scale, method, name, mask), average in means.items():
        baseline = means[(scale, "Q0", name, mask)]
        gain = 100*(1-average/baseline) if baseline else None
        compare(gain, summary[(scale, method, name, mask)]["gain_vs_Q0_percent"])
    regressions = {str(s): 100*(means[(s, "Q3m-k6", "REF", "recolorable")]/
                               means[(s, "Q0", "REF", "recolorable")]-1) for s in (2,4)}
    validation = {str(s): all(means[(s, "Q3m-k6", r["name"], "recolorable")] <
                             means[(s, "Q0", r["name"], "recolorable")]
                             for r in plan if r["role"] == "validation") for s in (2,4)}
    assert all(validation.values())
    report = {"schema": "bg2-upscale-character-pre-p2-metrics-v1", "status": "passed",
              "created_utc": datetime.now(timezone.utc).isoformat(), "elapsed_seconds": time.monotonic()-start,
              "scope": "Saved P1 inputs only; no optimization, inference or runtime execution",
              "methods": methods, "frame_metric_rows": checked, "summary_rows": len(summary),
              "maximum_absolute_difference": max_delta, "relative_and_absolute_tolerance": 1e-12,
              "all_ten_disjoint_validation_palettes_improve": validation,
              "ref_error_increase_percent": regressions}
    destination.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
