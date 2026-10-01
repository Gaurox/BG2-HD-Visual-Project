"""Summarize a user-designated P4 session; never selects or measures a live session."""
from __future__ import annotations

import argparse
import csv
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import median


def summarize(path: Path) -> dict:
    groups = defaultdict(list)
    ignored = 0
    with path.open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream):
            try:
                values = {k: float(v) for k, v in row.items()}
                if not all(math.isfinite(v) for v in values.values()):
                    ignored += 1
                    continue
                if any(values[k] != 1 for k in ("view_valid", "memory_valid")) or \
                        values["view_mixed"] or values["target_successes"] <= 0 or \
                        values["frame_samples"] < 15 or values["frame_dropped"] or \
                        values["window_s"] < 0.9:
                    ignored += 1
                    continue
                key = tuple(values[k] for k in ("viewport_w", "viewport_h", "scale", "min_filter", "mag_filter")) + \
                    (round(values["zoom_x"], 4), round(values["zoom_y"], 4),
                     values.get("filter_mode", -1))
                groups[key].append(values)
            except (ValueError, TypeError, KeyError):
                ignored += 1
    results = []
    for key, rows in sorted(groups.items()):
        frames = sum(r["frames"] for r in rows)
        frame_samples = sum(r["frame_samples"] for r in rows)
        frame_ms = sum(r["frame_samples"] * r["frame_avg_ms"] for r in rows)
        results.append({
            "viewport": [int(key[0]), int(key[1])], "scale": int(key[2]),
            "min_filter": int(key[3]), "mag_filter": int(key[4]), "zoom": list(key[5:7]),
            "filter_mode": int(key[7]),
            "max_mip_level_range": [int(min(r.get("max_mip_level", 0) for r in rows)),
                                    int(max(r.get("max_mip_level", 0) for r in rows))],
            "windows": len(rows), "seconds": sum(r["window_s"] for r in rows),
            "cadence_fps": 1000 * frame_samples / frame_ms if frame_ms else None,
            "window_p95_median_ms": median(r["frame_p95_ms"] for r in rows),
            "window_p95_max_ms": max(r["frame_p95_ms"] for r in rows),
            "target_cpu_ms_per_frame": sum(r["target_cpu_ms"] for r in rows) / frames,
            "pixel_cpu_ms_per_frame": sum(r["pixel_cpu_ms"] for r in rows) / frames,
            "upload_cpu_ms_per_frame": sum(r["upload_cpu_ms"] for r in rows) / frames,
            "mask_cpu_ms_per_frame": sum(r.get("mask_cpu_ms", 0) for r in rows) / frames,
            "mask_failures": int(sum(r.get("mask_calls", 0) - r.get("mask_successes", 0) for r in rows)),
            "successful_upload_bytes": int(sum(r["upload_bytes"] for r in rows)),
            "target_failures": int(sum(r["target_calls"] - r["target_successes"] for r in rows)),
            "peak_working_set_bytes": int(max(r["working_set_bytes"] for r in rows)),
            "peak_private_bytes": int(max(r["private_bytes"] for r in rows)),
            "first_elapsed_s": rows[0]["elapsed_s"], "last_elapsed_s": rows[-1]["elapsed_s"],
        })
    return {"schema": "bg2-sprite-p4-session-summary-v1", "input": str(path.resolve()),
            "ignored_windows": ignored, "groups": results,
            "limits": ["CPU upload time includes driver submission, not GPU execution.",
                       "Process memory includes all game systems; uploaded bytes are traffic, not resident VRAM.",
                       "p95 is summarized per window; no aggregate p95 can be reconstructed.",
                       "Measured zoom extrema are accessible bounds only if the user reached both stops."]}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = json.dumps(summarize(args.input), ensure_ascii=False, indent=2)
    if args.output:
        # Session and previous analysis files remain immutable.
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(result + "\n")
    else:
        print(result)


if __name__ == "__main__":
    main()
