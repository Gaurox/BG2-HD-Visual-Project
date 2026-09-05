from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_spline_top_reconstructed_alpha as builder  # noqa: E402


class ReconstructedTopAlphaTests(unittest.TestCase):
    def test_replaces_only_bounded_region_and_fills_a_small_hole(self) -> None:
        alpha = np.zeros((64, 64), dtype=np.uint8)
        alpha[12:40, 12:52] = 255
        alpha[20:24, 28:32] = 0

        base = alpha.copy()
        result, report = builder.rebuild_top_region(
            base, alpha, sigma=3.0, top_height=32, left_x=8, minimum_alpha=2
        )

        self.assertEqual(result.dtype, np.uint8)
        np.testing.assert_array_equal(result[32:], alpha[32:])
        self.assertGreater(result[21, 30], 0)
        self.assertGreater(report["raised_alpha_pixels"], 0)
        self.assertGreater(report["changed_alpha_pixels"], 0)

    def test_rejects_out_of_canvas_region(self) -> None:
        alpha = np.zeros((16, 16), dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "hors canvas"):
            builder.rebuild_top_region(alpha, alpha, sigma=1.0, top_height=17, left_x=0, minimum_alpha=0)

    def test_spline_replaces_only_the_main_connected_silhouette(self) -> None:
        alpha = np.zeros((48, 48), dtype=np.uint8)
        alpha[8:40, 8:40] = 255
        alpha[2:4, 42:44] = 255

        result, report = builder.spline_main_silhouette(
            alpha, threshold=127, fit_error=1.0, spacing=1.5, supersample=4, padding=8
        )

        self.assertEqual(report["source_components"], 2)
        self.assertEqual(report["discarded_components"], 1)
        self.assertEqual(result[2, 42], 0)
        self.assertGreater(result[24, 24], 0)
