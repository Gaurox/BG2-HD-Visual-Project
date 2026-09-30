from __future__ import annotations
import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
import palette_frac_encode as encoder


class FractionEncoderTests(unittest.TestCase):
    def test_successor_never_crosses_any_class_or_special(self):
        for i in range(256):
            successor = int(encoder.successors()[i])
            self.assertEqual(encoder.CLASS_TABLE[i], encoder.CLASS_TABLE[successor])
        for i in (0, 1, 2, 3, 15, 27, 87, 95, 255):
            self.assertEqual(int(encoder.successors()[i]), i)
        self.assertEqual(len(encoder.candidates(4)[0]), 89)
        self.assertEqual(len(encoder.candidates(11)[0]), 57)

    def test_integer_rounding_and_alpha_copy(self):
        palette = np.zeros((256, 4), np.uint8)
        palette[4], palette[5] = (0, 8, 16, 123), (4, 12, 20, 255)
        np.testing.assert_array_equal(encoder.decode([[4]], [[1]], palette), [[[1, 9, 17, 123]]])

    def test_f_zero_identity_all_indices_and_native_alpha(self):
        rng = np.random.default_rng(6)
        palette = rng.integers(0, 256, (256, 4), dtype=np.uint8)
        indices = np.arange(256, dtype=np.uint8).reshape(16, 16)
        np.testing.assert_array_equal(encoder.decode(indices, np.zeros_like(indices), palette), palette[indices])

    def test_dependencies_include_fractional_successor_only_when_read(self):
        mask = encoder.dependency_mask([[4, 15, 1]], [[3, 0, 0]])
        bits = np.flatnonzero(np.unpackbits(mask, bitorder="little"))
        np.testing.assert_array_equal(bits, [1, 4, 5, 15])
        palette = np.zeros((256, 3), np.uint8)
        old = encoder.decode([[4, 15, 1]], [[3, 0, 0]], palette)
        palette[6] = 255
        np.testing.assert_array_equal(old, encoder.decode([[4, 15, 1]], [[3, 0, 0]], palette))
        palette[5] = 255
        self.assertFalse(np.array_equal(old, encoder.decode([[4, 15, 1]], [[3, 0, 0]], palette)))

    def test_invalid_fractions_and_wrapped_inputs_rejected(self):
        for indices, fractions in (([[15]], [[1]]), ([[1]], [[1]]), ([[4]], [[8]]),
                                   ([[256]], [[0]]), ([[4]], [[-1]])):
            with self.assertRaises(ValueError):
                encoder.validate_planes(indices, fractions)

    def test_class_leaks_and_changed_reserved_indices_rejected(self):
        for i in (16, 2):
            with self.assertRaises(ValueError):
                encoder.check_contract([[4]], [[i]], [[0]])
        with self.assertRaises(ValueError):
            encoder.check_contract([[2]], [[3]], [[0]])

    def test_multi_palette_exact_fraction_and_specials(self):
        palettes = np.zeros((2, 256, 3), np.uint8)
        for k in range(2):
            palettes[k, 4:16] = np.array([0, 80, 160, 200, 210, 220, 230, 240, 245, 250, 253, 255])[:, None]
        palettes[1, 4:16] = np.minimum(palettes[1, 4:16].astype(int)+20, 255)
        guide = np.array([[0, 1, 2, 3, 4]], np.uint8)
        targets = np.zeros((2, 1, 5, 3), np.float64)
        targets[0, 0, 4] = 30/255
        targets[1, 0, 4] = 50/255
        results = encoder.encode_variants(guide, targets, palettes, ks=(1, 2), chunk_pixels=1)
        for k in (1, 2):
            fractional = results[f"Q3m-k{k}"]
            np.testing.assert_array_equal(fractional["I"], guide)
            np.testing.assert_array_equal(fractional["F"], [[0, 0, 0, 0, 3]])
            self.assertFalse(np.any(results[f"Q6-k{k}"]["F"]))

    def test_duplicate_rgb_tie_is_lowest_i_then_f(self):
        palettes = np.full((3, 256, 3), 80, np.uint8)
        result = encoder.encode_variants([[14]], np.full((3, 1, 1, 3), 80/255), palettes, ks=(3,))
        self.assertEqual(int(result["Q3m-k3"]["I"][0, 0]), 4)
        self.assertEqual(int(result["Q3m-k3"]["F"][0, 0]), 0)

    def test_chunk_size_does_not_change_encoded_bytes(self):
        rng = np.random.default_rng(6110)
        guide = rng.integers(0, 256, (5, 11), dtype=np.uint8)
        palettes = rng.integers(0, 256, (3, 256, 3), dtype=np.uint8)
        targets = rng.random((3, 5, 11, 3))
        one = encoder.encode_variants(guide, targets, palettes, ks=(1, 3), chunk_pixels=1)
        many = encoder.encode_variants(guide, targets, palettes, ks=(1, 3), chunk_pixels=100)
        for method in one:
            for plane in ("I", "F", "dep_mask"):
                np.testing.assert_array_equal(one[method][plane], many[method][plane])


if __name__ == "__main__":
    unittest.main()
