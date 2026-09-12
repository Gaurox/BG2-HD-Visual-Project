from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_cross_cycle_seam_30fps_v2 as builder  # noqa: E402


class CrossCycleSeamTests(unittest.TestCase):
    def test_axis_weights_cover_both_axes_and_leave_outer_corners_unchanged(self) -> None:
        restore = builder.axis_restore_weight((64, 64), (32, 32), protected=8, transition=16)
        rgb = builder.axis_rgb_weight((64, 64), (32, 32), depth=24, strength=0.55)

        self.assertEqual(float(restore[31, 4]), 1.0)
        self.assertEqual(float(restore[4, 31]), 1.0)
        self.assertEqual(float(restore[4, 4]), 0.0)
        self.assertGreater(float(rgb[31, 31]), 0.54)
        self.assertLessEqual(float(rgb.max()), 0.55)
        self.assertEqual(float(rgb[4, 4]), 0.0)

    def test_joint_filter_reduces_rgb_jump_and_restores_axis_alpha(self) -> None:
        raw = np.zeros((64, 64, 4), dtype=np.uint8)
        raw[:, :32, :3] = [40, 80, 120]
        raw[:, 32:, :3] = [120, 160, 200]
        raw[:, :, 3] = 255

        result, report = builder.repair_canvas(
            raw, (32, 32), threshold=127, fit_error=1.0, spacing=1.5,
            supersample=2, padding=8, inner_feather=2,
            alpha_protected=4, alpha_transition=8, rgb_sigma=3.0, rgb_depth=16,
        )

        self.assertLess(
            report["after"]["vertical_rgb_mae"],
            report["before"]["vertical_rgb_mae"],
        )
        np.testing.assert_array_equal(result[:, 30:34, 3], raw[:, 30:34, 3])
        np.testing.assert_array_equal(result[0, 0, :3], raw[0, 0, :3])
        self.assertTrue(np.all(result[:, :, 3] <= raw[:, :, 3]))

    def test_four_cycle_geometry_is_a_complete_cross(self) -> None:
        frames = []
        centres = ([2, 2], [0, 2], [2, 0], [0, 0])
        for index, centre in enumerate(centres):
            frames.append({
                "frame": index,
                "asset": f"frame{index}.rgba",
                "logical_size_x1": [2, 2],
                "physical_size_x4": [8, 8],
                "centre_x1": list(centre),
            })
        resource = {
            "resref": "TEST",
            "playback_mode": "TimedTimeline",
            "frame_count": 4,
            "frames": frames,
            "cycles": [
                {"cycle": index, "timeline_frame_indices": [index]}
                for index in range(4)
            ],
        }

        validated, phases = builder.validate_quadrants(resource)

        self.assertEqual(len(validated), 4)
        self.assertEqual(phases, [[0, 1, 2, 3]])


if __name__ == "__main__":
    unittest.main()
