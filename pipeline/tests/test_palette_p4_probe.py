from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from palette_p4_probe import summarize


class P4SessionTests(unittest.TestCase):
    def test_stable_windows_only_and_weighted_cadence(self):
        base = dict(view_valid=1, memory_valid=1, view_mixed=0, target_successes=60,
                    target_calls=60, frame_samples=60, frame_dropped=0, frames=60,
                    window_s=1, viewport_w=2528, viewport_h=1339, scale=4,
                    min_filter=9728, mag_filter=9728, zoom_x=2, zoom_y=2,
                    frame_avg_ms=1000/60, frame_p95_ms=17, elapsed_s=10,
                    target_cpu_ms=6, pixel_cpu_ms=2, upload_cpu_ms=3, upload_bytes=4096,
                    working_set_bytes=10000, private_bytes=20000)
        second = dict(base, frame_samples=30, frames=30, frame_avg_ms=1000/30,
                      target_successes=30, target_calls=31, elapsed_s=11, frame_p95_ms=34)
        excluded = [dict(base, **update) for update in (
            dict(view_mixed=1), dict(view_valid=0), dict(target_successes=0),
            dict(frame_dropped=1), dict(window_s=.1), dict(zoom_x="nan"))]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "synthetic.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(base))
                writer.writeheader()
                writer.writerows([base, second, *excluded])
            result = summarize(path)
        self.assertEqual(result["ignored_windows"], 6)
        group, = result["groups"]
        self.assertEqual(group["windows"], 2)
        self.assertAlmostEqual(group["cadence_fps"], 45)
        self.assertAlmostEqual(group["target_cpu_ms_per_frame"], 12/90)
        self.assertEqual(group["target_failures"], 1)
        self.assertEqual(group["window_p95_median_ms"], 25.5)
        self.assertNotIn("aggregate_p95_ms", group)

    def test_no_target_produces_no_measurement(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "empty.csv"
            path.write_text("view_valid,memory_valid\n0,0\n", encoding="utf-8")
            self.assertEqual(summarize(path)["groups"], [])

    def test_box_is_distinct_from_nearest_and_mip_sizes_do_not_split_animation(self):
        base = dict(view_valid=1, memory_valid=1, view_mixed=0, target_successes=60,
                    target_calls=60, frame_samples=60, frame_dropped=0, frames=60,
                    window_s=1, viewport_w=2528, viewport_h=1339, scale=4,
                    min_filter=9728, mag_filter=9728, zoom_x=2, zoom_y=2,
                    frame_avg_ms=16.7, frame_p95_ms=17, elapsed_s=10,
                    target_cpu_ms=6, pixel_cpu_ms=2, upload_cpu_ms=3, upload_bytes=4096,
                    working_set_bytes=10000, private_bytes=20000, filter_mode=0, max_mip_level=0)
        rows = [base, dict(base, filter_mode=3),
                dict(base, filter_mode=4, min_filter=9987, max_mip_level=7),
                dict(base, filter_mode=4, min_filter=9987, max_mip_level=8)]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "modes.csv"
            with path.open("w", newline="", encoding="utf-8") as stream:
                writer = csv.DictWriter(stream, fieldnames=list(base))
                writer.writeheader()
                writer.writerows(rows)
            result = summarize(path)
        self.assertEqual([g["filter_mode"] for g in result["groups"]], [0, 3, 4])
        self.assertEqual(result["groups"][-1]["windows"], 2)
        self.assertEqual(result["groups"][-1]["max_mip_level_range"], [7, 8])


if __name__ == "__main__":
    unittest.main()
