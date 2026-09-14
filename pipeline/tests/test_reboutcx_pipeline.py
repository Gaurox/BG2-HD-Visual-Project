from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import reboutcx_batch as batch  # noqa: E402
import reboutcx_quantize as quantize  # noqa: E402
from run_creature_sprite_x2 import SourceFrame  # noqa: E402


def source_frame(indices: np.ndarray, palette: np.ndarray, *, center=(0, 0)) -> SourceFrame:
    indices = np.asarray(indices, dtype=np.uint8)
    height, width = indices.shape
    rgba = np.empty((height, width, 4), dtype=np.uint8)
    rgba[..., :3] = palette[indices]
    rgba[..., 3] = np.where(indices == 0, 0, 255).astype(np.uint8)
    return SourceFrame(
        "TEST",
        7,
        width,
        height,
        int(center[0]),
        int(center[1]),
        0,
        indices,
        palette,
        rgba.tobytes(),
    )


class ReboutCXQuantizerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.palette = np.zeros((256, 3), dtype=np.uint8)
        self.palette[0] = (0, 255, 0)
        self.palette[1] = (0, 0, 0)
        self.palette[2] = (255, 128, 0)
        self.palette[3] = (255, 0, 0)
        self.palette[4] = (0, 0, 255)
        self.classes = {
            "transparent": [0],
            "shadow": [1],
            "null": [2],
            "material": list(range(3, 256)),
        }

    def test_classed_quantizer_preserves_transparency_shadow_and_material(self) -> None:
        guide = np.asarray([[0, 1, 3, 4]], dtype=np.uint8)
        target = np.asarray([[[0, 0, 255], [255, 0, 0], [0, 0, 255], [255, 0, 0]]], dtype=np.uint8)
        result, metrics = quantize.quantize_classed_oklab(
            target,
            guide,
            self.palette,
            [0, 1, 2, 3, 4],
            self.classes,
            transparent_index=0,
            chunk_pixels=1,
        )
        np.testing.assert_array_equal(result, np.asarray([[0, 1, 4, 3]], dtype=np.uint8))
        self.assertEqual(metrics["quantizer"], quantize.QUANTIZER_ID)
        self.assertEqual(metrics["visible_pixels"], 3)

    def test_equal_distance_uses_lowest_palette_index(self) -> None:
        self.palette[3] = self.palette[4] = (80, 90, 100)
        result, _metrics = quantize.quantize_classed_oklab(
            np.asarray([[[80, 90, 100]]], dtype=np.uint8),
            np.asarray([[4]], dtype=np.uint8),
            self.palette,
            [3, 4],
            self.classes,
            transparent_index=0,
        )
        self.assertEqual(int(result[0, 0]), 3)

    def test_unknown_class_and_empty_candidate_fail_closed(self) -> None:
        classes = {"transparent": [0], "material": list(range(3, 256))}
        with self.assertRaisesRegex(RuntimeError, "no semantic class"):
            quantize.quantize_classed_oklab(
                np.zeros((1, 1, 3), dtype=np.uint8),
                np.asarray([[2]], dtype=np.uint8),
                self.palette,
                [2],
                classes,
                transparent_index=0,
            )
        with self.assertRaisesRegex(RuntimeError, "no used palette candidate"):
            quantize.quantize_classed_oklab(
                np.zeros((1, 1, 3), dtype=np.uint8),
                np.asarray([[3]], dtype=np.uint8),
                self.palette,
                [0, 1],
                classes,
                transparent_index=0,
            )

    def test_oklab_black_and_white_reference(self) -> None:
        values = quantize.srgb_u8_to_oklab(
            np.asarray([[0, 0, 0], [255, 255, 255]], dtype=np.uint8)
        )
        np.testing.assert_allclose(values[0], (0, 0, 0), atol=1e-12)
        np.testing.assert_allclose(values[1], (1, 0, 0), atol=2e-7)


class ReboutCXBatchContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.palette = np.zeros((256, 3), dtype=np.uint8)
        self.palette[0] = (0, 255, 0)
        self.palette[2] = (255, 128, 0)
        self.palette[3] = (255, 0, 0)
        self.palette[4] = (0, 0, 255)

    def test_nearest_opaque_fill_has_no_wrap_and_keeps_opaque_pixels(self) -> None:
        frame = source_frame(np.asarray([[3, 0, 0, 4]], dtype=np.uint8), self.palette)
        filled = batch.prepare_inference_rgb(frame)
        self.assertIsNotNone(filled)
        np.testing.assert_array_equal(
            filled,
            np.asarray([[[255, 0, 0], [255, 0, 0], [0, 0, 255], [0, 0, 255]]], dtype=np.uint8),
        )

    def test_null_frame_contract_is_exact(self) -> None:
        frame = source_frame(np.asarray([[2]], dtype=np.uint8), self.palette)
        self.assertTrue(batch.is_null_frame(frame, 2))
        self.assertFalse(batch.is_null_frame(frame, 1))
        shifted = source_frame(np.asarray([[2]], dtype=np.uint8), self.palette, center=(1, 0))
        self.assertFalse(batch.is_null_frame(shifted, 2))

    def test_partial_registry_round_trip_preserves_indices_and_geometry(self) -> None:
        frame = source_frame(np.asarray([[0, 3]], dtype=np.uint8), self.palette, center=(1, -2))
        mapped = np.asarray([[0, 0, 3, 3], [0, 0, 3, 3]], dtype=np.uint8)
        resources = [
            {
                "resref": "TEST",
                "source_sha256": "00" * 32,
                "frames": [{"frame": frame, "quantized_indices": mapped}],
            }
        ]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "CreatureSprites-XN.registry"
            info = batch.write_prototype_registry(path, animation_id=0x7F02, resources=resources)
            batch.verify_prototype_registry(path, resources)
        self.assertEqual(info["registry_magic"], "IEECSXN")
        self.assertEqual(info["version"], 3)
        self.assertEqual(info["scale"], 2)
        self.assertEqual(info["animation_id"], "0x7F02")
        self.assertEqual(info["frame_count"], 1)


if __name__ == "__main__":
    unittest.main()
