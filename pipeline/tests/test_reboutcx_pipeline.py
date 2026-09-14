from __future__ import annotations

import hashlib
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
        # CHMB1 also uses reserved index 2 inside real frames (142 in the audit).
        real_frame = source_frame(np.asarray([[2, 3]], dtype=np.uint8), self.palette)
        self.assertFalse(batch.is_null_frame(real_frame, 2))

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


class ReboutCXCharacterAuditTests(unittest.TestCase):
    # Independent native basic-block witnesses, not generated by the new mapping.
    # BaldurReal.exe B51093A4...; RVA [0x421F7B, 0x42201E), 3,557 interpreted
    # instructions/case, without executing the game. Full provenance in the guide.
    def test_palette_matches_native_mixing_witnesses(self) -> None:
        linear = np.arange(252, dtype=np.uint8).reshape(7, 12, 3)
        nonlinear = (
            (
                np.arange(252, dtype=np.uint16).reshape(7, 12, 3) * 73
                + 19
                + np.arange(7, dtype=np.uint16)[:, None, None]
            )
            % 256
        ).astype(np.uint8)
        for ramps, expected in (
            (linear, "1b8666695293997f8ef20bee51ae0ebac9563550d656615db9bdffaf1c428d19"),
            (nonlinear, "4dd5c15a3b5d3442995cc54528d67e8396aacf69b800fe63f472807111bbeef5"),
        ):
            with self.subTest(expected=expected):
                before = ramps.copy()
                palette = quantize.character_chmb1_palette_rgb(ramps)
                self.assertEqual(hashlib.sha256(palette.tobytes()).hexdigest(), expected)
                np.testing.assert_array_equal(ramps, before)

    def test_complete_partition_and_independent_color_dependencies(self) -> None:
        classes = quantize.character_chmb1_classes()
        table, _ = quantize.index_class_table(classes)
        self.assertEqual(len(classes), 32)
        self.assertTrue(np.all(table >= 0))
        self.assertEqual(len(set(table[:4].tolist())), 4)
        # Literal destinations checked against the native pair loop / SetRange;
        # deliberately do not derive expected dependencies from the class builder.
        mixed_starts = (
            (88, 96, 104, 112, 120, 128),
            (88, 136, 144, 152, 160, 168),
            (96, 136, 176, 184, 192, 200),
            (104, 144, 176, 208, 216, 224),
            (112, 152, 184, 208, 232, 240),
            (120, 160, 192, 216, 232, 248),
            (128, 168, 200, 224, 240, 248),
        )
        baseline = quantize.character_chmb1_palette_rgb(np.zeros((7, 12, 3), dtype=np.uint8))
        for color, starts in enumerate(mixed_starts):
            ramps = np.zeros((7, 12, 3), dtype=np.uint8)
            ramps[color] = 255
            palette = quantize.character_chmb1_palette_rgb(ramps)
            expected = set(range(4 + 12 * color, 16 + 12 * color))
            for start in starts:
                expected.update(range(start, start + 8))
                np.testing.assert_array_equal(palette[start : start + 8], np.full((8, 3), 127))
                self.assertEqual(len(set(table[start : start + 8].tolist())), 1)
            changed = set(np.flatnonzero(np.any(palette != baseline, axis=1)).tolist())
            self.assertEqual(changed, expected)

    def test_equal_colors_do_not_merge_classes_and_indices_recolor_without_requantizing(self) -> None:
        classes = quantize.character_chmb1_classes()
        palette = quantize.character_chmb1_palette_rgb(np.full((7, 12, 3), 64, dtype=np.uint8))
        # 156=minor/leather, 204=major/hair, 220=skin/armor: same source RGB,
        # different engine dependencies. Only same-frame candidates are allowed.
        guide = np.asarray([[0, 1, 2, 3, 156, 204, 220]], dtype=np.uint8)
        used = [0, 1, 2, 3, 152, 156, 200, 204, 216, 220]
        target = palette[guide]
        result, _ = quantize.quantize_classed_oklab(
            target, guide, palette, used, classes, transparent_index=0
        )
        np.testing.assert_array_equal(result, [[0, 1, 2, 3, 152, 200, 216]])
        repeated, _ = quantize.quantize_classed_oklab(
            target, guide, palette, used, classes, transparent_index=0, chunk_pixels=1
        )
        np.testing.assert_array_equal(result, repeated)
        frozen = result.tobytes()
        # Three contrasting recolorings of these SAME indices, including a tie.
        for a, b, c in ((200, 20, 100), (0, 255, 64), (128, 128, 0)):
            ramps = np.zeros((7, 12, 3), dtype=np.uint8)
            ramps[1] = ramps[4] = a
            ramps[2] = ramps[6] = b
            ramps[3] = ramps[5] = c
            realized_rgb = quantize.character_chmb1_palette_rgb(ramps)
            np.testing.assert_array_equal(realized_rgb[result][0, 4:], [[a]*3, [b]*3, [c]*3])
            self.assertEqual(result.tobytes(), frozen)

    def test_unresolved_or_invalid_ramps_are_rejected(self) -> None:
        for ramps in (
            np.zeros((7, 8, 3), dtype=np.uint8),
            np.zeros((7, 12, 3), dtype=float),
            np.full((7, 12, 3), 256, dtype=np.int16),
            np.full((7, 12, 3), -1, dtype=np.int16),
        ):
            with self.assertRaisesRegex(RuntimeError, "seven resolved"):
                quantize.character_chmb1_palette_rgb(ramps)


if __name__ == "__main__":
    unittest.main()
