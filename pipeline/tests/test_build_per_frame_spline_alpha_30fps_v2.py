from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_per_frame_spline_alpha_30fps_v2 as builder  # noqa: E402


class PerFrameSplineAlphaTests(unittest.TestCase):
    def test_review_timeline_preserves_each_cycle_and_phase(self) -> None:
        cycles = [
            {"cycle": 1, "timeline_frame_indices": [4, 5]},
            {"cycle": 0, "timeline_frame_indices": [0, 2]},
        ]

        self.assertEqual(
            builder.review_timeline(cycles),
            [(0, 0, 0), (0, 1, 2), (1, 0, 4), (1, 1, 5)],
        )

    def test_preserve_rgb_policy_changes_only_alpha(self) -> None:
        raw = np.array([[[90, 120, 180, 255], [15, 30, 45, 255]]], dtype=np.uint8)
        alpha = np.array([[64, 0]], dtype=np.uint8)

        result = builder.apply_rgb_policy(raw, alpha, "preserve")

        np.testing.assert_array_equal(result[:, :, :3], raw[:, :, :3])
        np.testing.assert_array_equal(result[:, :, 3], alpha)

    def test_premultiplied_rgb_policy_multiplies_final_alpha(self) -> None:
        raw = np.array([[[100, 200, 50, 255]]], dtype=np.uint8)

        result = builder.apply_rgb_policy(raw, np.array([[128]], dtype=np.uint8), "premultiplied")

        np.testing.assert_array_equal(result, np.array([[[50, 100, 25, 128]]], dtype=np.uint8))

    def test_bottom_seam_restores_source_alpha_without_expansion(self) -> None:
        source = np.full((24, 8), 180, dtype=np.uint8)
        faded = np.full((24, 8), 30, dtype=np.uint8)

        result, report = builder.restore_bottom_seam(
            faded, source, protected_depth=4, transition=8
        )

        np.testing.assert_array_equal(result[:12], faded[:12])
        self.assertGreater(int(result[16, 3]), int(faded[16, 3]))
        np.testing.assert_array_equal(result[-4:], source[-4:])
        self.assertTrue(np.all(result <= source))
        self.assertGreater(report["changed_alpha_pixels"], 0)

    def test_top_seam_restores_source_alpha_without_expansion(self) -> None:
        source = np.full((24, 8), 180, dtype=np.uint8)
        faded = np.full((24, 8), 30, dtype=np.uint8)

        result, report = builder.restore_top_seam(
            faded, source, protected_depth=4, transition=8
        )

        np.testing.assert_array_equal(result[:4], source[:4])
        self.assertGreater(int(result[7, 3]), int(faded[7, 3]))
        np.testing.assert_array_equal(result[12:], faded[12:])
        self.assertTrue(np.all(result <= source))
        self.assertGreater(report["changed_alpha_pixels"], 0)
