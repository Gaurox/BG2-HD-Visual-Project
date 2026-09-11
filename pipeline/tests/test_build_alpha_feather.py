from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_alpha_feather as feather  # noqa: E402


class TopGaussianAlphaTests(unittest.TestCase):
    def test_smooths_upper_island_without_expanding_or_touching_lower_rows(self) -> None:
        alpha = np.zeros((20, 20), dtype=np.uint8)
        alpha[2:6, 8:12] = 255
        alpha[12:16, 8:12] = 255

        corrected = feather.top_gaussian_alpha(alpha, sigma=2.0, full_height=8, transition=4)

        self.assertTrue(np.all(corrected <= alpha))
        self.assertLess(corrected[3, 9], 255)
        self.assertEqual(corrected[2, 7], 0)
        np.testing.assert_array_equal(corrected[12:], alpha[12:].astype(np.float32))

    def test_transition_is_continuous_and_stays_inside_source(self) -> None:
        alpha = np.full((16, 16), 255, dtype=np.uint8)
        corrected = feather.top_gaussian_alpha(alpha, sigma=1.5, full_height=6, transition=4)

        self.assertTrue(np.all(corrected <= alpha))
        self.assertLess(corrected[6, 8], 255)
        self.assertGreater(corrected[6, 8], corrected[5, 8])
        np.testing.assert_array_equal(corrected[10:], alpha[10:].astype(np.float32))


class CanvasEdgeRampTests(unittest.TestCase):
    def test_selected_edges_leave_bottom_center_intact(self) -> None:
        ramp = feather.canvas_edge_ramp(12, 12, 4.0, ("top", "right", "left"))

        self.assertEqual(ramp[0, 6], 0.0)
        self.assertEqual(ramp[6, 0], 0.0)
        self.assertEqual(ramp[6, 11], 0.0)
        self.assertEqual(ramp[11, 6], 1.0)
        self.assertEqual(ramp[10, 6], 1.0)
