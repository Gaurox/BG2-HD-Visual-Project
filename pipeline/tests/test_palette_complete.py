from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
from palette_complete import independent_lut, verify_inference_context
from palette_p2 import P1, golden, sha


class CompletePaletteTests(unittest.TestCase):
    def test_independent_oracle_matches_all_frozen_decoder_pairs(self):
        palettes, indices, fractions, expected = golden()
        self.assertTrue(np.array_equal(independent_lut(palettes)[:, indices, fractions], expected))

    def test_oracle_keeps_primary_alpha_and_class_terminal(self):
        palette = np.zeros((1, 256, 4), np.uint8)
        palette[0, 4] = (0, 80, 160, 37)
        palette[0, 5] = (80, 0, 0, 255)
        palette[0, 15] = (43, 51, 72, 19)
        palette[0, 16] = (255, 255, 255, 255)
        lut = independent_lut(palette)
        self.assertEqual(lut[0, 4, 3].tolist(), [30, 50, 100, 37])
        self.assertEqual(lut[0, 15, 7].tolist(), [43, 51, 72, 19])

    def test_only_uninvoked_palette_job_loader_may_differ_from_p1(self):
        frozen = json.loads((P1 / "experiment.json").read_text())["inference"]
        current = copy.deepcopy(frozen)
        current["kernels"]["reboutcx_batch.py"] = sha(Path(__file__).resolve().parents[2] / "pipeline/scripts/reboutcx_batch.py")
        self.assertTrue(verify_inference_context(current, frozen)["other_ast_nodes_identical"])
        current["batch_size"] = 32
        with self.assertRaisesRegex(ValueError, "environment changed"):
            verify_inference_context(current, frozen)


if __name__ == "__main__":
    unittest.main()
