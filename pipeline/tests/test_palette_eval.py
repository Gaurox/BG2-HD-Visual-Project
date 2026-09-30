from __future__ import annotations
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
import palette_eval as evaluation


class PaletteEvaluationTests(unittest.TestCase):
    def test_2da_spaced_header_and_missing_cell_uses_default(self):
        columns, rows = evaluation.parse_2da(b"2DA       V1.0\n12\n FIRST SECOND\nHAIR 2\n")
        self.assertEqual(columns, ["FIRST", "SECOND"])
        self.assertEqual(rows["HAIR"], {"FIRST": "2", "SECOND": "12"})

    def test_same_world_different_crop_has_three_static_pixels(self):
        ga, gb = np.full((1, 4), 4, np.uint8), np.full((1, 3), 4, np.uint8)
        ta = np.repeat(np.array([[[.1], [.2], [.3], [.4]]]), 3, axis=2)
        tb = ta[:, 1:].copy()
        ra, rb = np.rint(ta*255).astype(np.uint8), np.rint(tb*255).astype(np.uint8)
        counts = evaluation.temporal_pair(ga, gb, ta, tb, ra, rb, (1, 0), (0, 0), 1)
        self.assertEqual(counts["recolorable"], {"static_pixels": 3, "changed_pixels": 0})
        self.assertEqual(counts["shadow"]["static_pixels"], 0)

    def test_mask_partition_does_not_mix_shadow_and_recolorable(self):
        guide = np.array([[0, 1, 2, 3, 4, 255]], np.uint8)
        counts = evaluation.color_errors(np.zeros((1, 6, 3), np.uint8), np.zeros((1, 6, 3)), guide)
        self.assertEqual(counts["visible"]["pixels"], 5)
        self.assertEqual(counts["recolorable"]["pixels"], 2)
        self.assertEqual(counts["shadow"]["pixels"], 1)

    def test_no_world_overlap(self):
        self.assertIsNone(evaluation.aligned_slices((3, 3), (3, 3), (100, 0), (0, 0), 4))

    def test_k_selection_requires_each_palette_and_two_percent(self):
        rows = [{"scale": s, "method": f"Q3m-k{k}", "mask": "recolorable",
                 "role": "validation", "pixel_weighted_mean": score,
                 "gain_vs_Q0_percent": 1.0} for s in (2, 4) for k, score in ((3, .098), (4, .097), (6, .096))
                 for _ in range(10)]
        decision = evaluation.choose_k(rows)
        self.assertEqual(decision["2"]["selected_k"], 4)
        for row in rows:
            if row["method"] == "Q3m-k4":
                row["gain_vs_Q0_percent"] = -1
        self.assertEqual(evaluation.choose_k(rows)["2"]["selected_k"], 6)
        for row in rows:
            row["gain_vs_Q0_percent"] = -1
        self.assertIsNone(evaluation.choose_k(rows)["2"]["selected_k"])

    def test_zero_support_remains_none_in_temporal_aggregation(self):
        row = {"scale": 2, "method": "Q0", "palette": "TEST", "timing": "distinct_poses",
               "mask": "shadow", "static_pixels": 0, "changed_pixels": 0, "ratio": None}
        summary = evaluation.summarize_temporal([row])[0]
        self.assertIsNone(summary["pixel_weighted_ratio"])
        self.assertIsNone(summary["sequence_unweighted_ratio"])


if __name__ == "__main__":
    unittest.main()
