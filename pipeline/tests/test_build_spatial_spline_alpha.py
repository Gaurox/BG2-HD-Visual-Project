from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_spatial_spline_alpha as builder  # noqa: E402


class SpatialSplineAlphaTests(unittest.TestCase):
    def test_reconstruction_never_changes_alpha_outside_its_bounded_region(self) -> None:
        source = np.zeros((32, 32), dtype=np.uint8)
        source[4:20, 4:20] = 255
        source[8:12, 10:14] = 0
        spline = source.copy()

        result, report = builder.reconstruct_local_alpha(
            spline,
            source,
            region=(0, 0, 24, 24),
            sigma=2.0,
            minimum_alpha=1,
            transition=4,
        )

        np.testing.assert_array_equal(result[:, 24:], spline[:, 24:])
        np.testing.assert_array_equal(result[24:, :], spline[24:, :])
        self.assertGreater(result[9, 11], 0)
        self.assertGreater(report["raised_over_source_pixels"], 0)

    def test_reconstruction_gate_rejects_an_out_of_frame_region(self) -> None:
        with self.assertRaisesRegex(SystemExit, "hors frame"):
            builder.reconstruction_gate(20, 20, (0, 0, 21, 10), 2)

    def test_safe_boundary_preserves_core_and_limits_outset(self) -> None:
        source = np.zeros((48, 48), dtype=np.uint8)
        source[8:40, 8:40] = 255

        result, report = builder.safe_boundary_spline_alpha(
            source,
            threshold=127,
            fit_error=1.0,
            spacing=1.5,
            supersample=4,
            padding=8,
            inner_band=6.0,
            outer_band=4.0,
        )

        self.assertEqual(int(result[24, 24]), 255)
        outside_distance = builder.ndimage.distance_transform_edt(source == 0)
        self.assertFalse(np.any((result > source) & (outside_distance > 4.0)))
        self.assertEqual(report["mode"], "safe-boundary")

    def test_left_edge_blur_is_limited_to_left_band(self) -> None:
        source = np.zeros((32, 32), dtype=np.uint8)
        source[4:28, 10:24] = 255

        result, report = builder.blur_left_edge(
            source,
            source,
            threshold=127,
            sigma=2.0,
            inner_band=5,
            outer_band=4,
        )

        np.testing.assert_array_equal(result[:, 16:], source[:, 16:])
        self.assertGreater(report["changed_alpha_pixels"], 0)

    def test_local_reinforcement_keeps_a_canvas_touching_tip_opaque(self) -> None:
        source = np.zeros((32, 32), dtype=np.uint8)
        source[24:32, 14:18] = 255
        spline = source.copy()
        spline[31, 14:18] = 24

        result, report = builder.reinforce_local_alpha(
            spline,
            source,
            region=(8, 20, 24, 32),
            threshold=127,
            outset=2.0,
            feather=2.0,
            transition=0,
        )

        np.testing.assert_array_equal(result[31, 14:18], np.full(4, 255, dtype=np.uint8))
        np.testing.assert_array_equal(result[:20, :], spline[:20, :])
        self.assertGreater(report["raised_over_spline_pixels"], 0)
        self.assertGreater(report["raised_over_source_pixels"], 0)
