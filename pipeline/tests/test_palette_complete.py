from __future__ import annotations
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
from palette_complete import independent_lut, verify_inference_context
from palette_p2 import P1, golden, sha
from palette_p3_catalog import write_complete_x4_catalog
import palette_registry as v6
import run_creature_sprite_x2 as registry


class CompletePaletteTests(unittest.TestCase):
    def test_complete_x4_catalog_requires_exact_unique_V6_coverage(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            plane=np.full((8,8),4,np.uint8)
            reps=np.full(256,65535,np.uint16);reps[4]=0
            frame=dict(geometry=(2,2,-3,5,0),representatives=reps,I=plane,F=np.full_like(plane,3),guide=plane)
            resource=dict(resref="TEST",source_sha256="12"*32,frames=[frame],cycles=[[0,0],[]])
            leaf=root/"input";v6.write(leaf,4,[resource],compress=False)
            result,proof=write_complete_x4_catalog([leaf],root/"good",expected_resrefs=["TEST"])
            self.assertEqual(result["scale"],4)
            self.assertEqual(result["shard_registry_version"],6)
            self.assertEqual(result["animation_resources"],{"0x6110":["TEST"]})
            self.assertTrue(proof["all_resources_v6"])
            self.assertEqual(registry.inspect_registry_catalog(root/"good"/registry.XN_REGISTRY_CATALOG_FILENAME)["shard_registry_version"],6)
            for leaves,expected in (([leaf,leaf],["TEST"]),([leaf],["TEST","MISSING"])):
                with self.assertRaisesRegex(ValueError,"coverage"):
                    write_complete_x4_catalog(leaves,root/"bad",expected_resrefs=expected)
                self.assertFalse((root/"bad").exists())

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
