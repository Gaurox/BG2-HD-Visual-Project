from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import derive_animation_visual_treatment as derive  # noqa: E402


class FillSmallAlphaHolesTests(unittest.TestCase):
    def test_fills_interior_dither_holes_but_keeps_large_and_border_transparency(self) -> None:
        rgba = np.zeros((40, 40, 4), dtype=np.uint8)
        rgba[:, :, :3] = 100
        rgba[:, :, 3] = 255
        rgba[10:12, 10:12, 3] = 0          # small interior hole
        rgba[10:12, 10:12, :3] = 0         # dark hidden RGB, must be repainted
        rgba[20:32, 20:32, 3] = 0          # 144 px interior hole, above the limit
        rgba[0:3, 30:33, 3] = 0            # small hole touching the canvas

        output, filled = derive.fill_small_alpha_holes(rgba, 64)

        self.assertEqual(filled, 4)
        self.assertTrue((output[10:12, 10:12, 3] == 255).all())
        self.assertTrue((output[10:12, 10:12, :3] == 100).all())
        self.assertTrue((output[20:32, 20:32, 3] == 0).all())
        self.assertTrue((output[0:3, 30:33, 3] == 0).all())

    def test_frame_without_holes_is_returned_unchanged(self) -> None:
        rgba = np.full((8, 8, 4), 255, dtype=np.uint8)

        output, filled = derive.fill_small_alpha_holes(rgba, 64)

        self.assertEqual(filled, 0)
        self.assertTrue(np.array_equal(output, rgba))


if __name__ == "__main__":
    unittest.main()
