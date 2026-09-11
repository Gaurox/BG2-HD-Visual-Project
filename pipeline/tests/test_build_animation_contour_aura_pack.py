from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_animation_contour_aura_pack as aura  # noqa: E402


class ContourAuraTests(unittest.TestCase):
    def test_aura_expands_from_faded_core_and_rgb_is_premultiplied(self) -> None:
        pixels = np.zeros((41, 41, 4), dtype=np.uint8)
        pixels[18:23, 18:23, :3] = [200, 100, 50]
        pixels[18:23, 18:23, 3] = 255
        result, stats = aura.transform_pixels(
            pixels.tobytes(), 41, 41, inner_feather_x4=2, aura_sigma_x4=2,
            aura_gain=0.9, border_margin_x4=3,
        )
        output = np.frombuffer(result, dtype=np.uint8).reshape(41, 41, 4)
        self.assertGreater(stats["aura_expanded_pixels"], 0)
        self.assertGreater(output[17, 20, 3], 0)
        self.assertEqual(output[0, 20, 3], 0)
        self.assertTrue(np.all(output[..., :3] <= pixels[..., :3]))
        self.assertTrue(np.all(output[output[..., 3] == 0, :3] == 0))

    def test_aura_replaces_hidden_green_chroma_with_nearest_opaque_rgb(self) -> None:
        pixels = np.zeros((41, 41, 4), dtype=np.uint8)
        pixels[..., 1] = 255  # palette chroma retained under alpha 0
        pixels[18:23, 18:23, :3] = [220, 80, 20]
        pixels[18:23, 18:23, 3] = 255

        result, stats = aura.transform_pixels(
            pixels.tobytes(), 41, 41, inner_feather_x4=2, aura_sigma_x4=2,
            aura_gain=0.9, border_margin_x4=3,
        )
        output = np.frombuffer(result, dtype=np.uint8).reshape(41, 41, 4)
        aura_only = (output[..., 3] > 0) & (pixels[..., 3] == 0)

        self.assertEqual(stats["aura_rgb_dilated_pixels"], int(aura_only.sum()))
        self.assertTrue(np.all(output[aura_only, 0] > output[aura_only, 1]))
        self.assertTrue(np.all(output[aura_only, 1] > output[aura_only, 2]))
