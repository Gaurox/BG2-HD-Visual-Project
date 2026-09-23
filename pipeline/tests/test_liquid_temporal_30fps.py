"""Synthetic checks of the 30 fps liquid recipe; no game files, GPU or run dependencies."""
import sys
from pathlib import Path
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_liquid_temporal_30fps as t


class TemporalRecipeTests(unittest.TestCase):
    def test_trig_interpolation_keeps_anchors_and_closes_loop(self):
        rng = np.random.default_rng(1)
        for keys, phases in ((6, 72), (8, 128), (11, 44), (12, 24)):
            with self.subTest(keys=keys):
                source = rng.uniform(0, 255, (keys, 4, 4, 3))
                out = t.trig_interpolate(source, phases)
                self.assertEqual(out.shape[0], phases)
                np.testing.assert_allclose(out[::phases // keys], source, atol=1e-9)
                steps = np.abs(np.diff(np.concatenate([out, out[:1]]), axis=0)).mean(axis=(1, 2, 3))
                self.assertLess(steps.max() / np.median(steps), 2.5)

    def test_phase_count_is_30fps_multiple_of_keys_and_fits_one_page(self):
        self.assertEqual(t.phase_count(6, 2.4), 72)
        self.assertEqual(t.phase_count(8, 8 * 8 / 15), 128)
        self.assertEqual(t.phase_count(12, 0.1), 12)
        with self.assertRaises(ValueError):
            t.phase_count(12, 12 * 12 / 15)

    def test_ambiguous_wed_speeds_need_an_explicit_cycle(self):
        agree = [{"lookup": list(range(6)), "speed_divisor": 6}]
        self.assertAlmostEqual(t.native_cycle(agree), 2.4)
        teal = agree + [{"lookup": list(range(6)), "speed_divisor": 0}]
        self.assertIsNone(t.native_cycle(teal))

    def test_wrap_order_is_one_4n_plus_1_chunk_around_the_loop(self):
        for phases in (24, 72, 128):
            order = t.wrap_order(phases)
            self.assertEqual((len(order) - 1) % 4, 0)
            head = order.index(0)
            self.assertEqual(order[head:head + phases], list(range(phases)))
            self.assertEqual(order[head + phases:head + phases + head], list(range(head)))

    def test_variance_preserving_mix_keeps_detail(self):
        rng = np.random.default_rng(2)
        a, b = rng.normal(128, 20, (2, 64, 64, 3))
        plain = t.split_detail(0.5 * a + 0.5 * b)[1].std()
        kept = t.split_detail(t.variance_preserving_mix(a, b, 0.5))[1].std()
        self.assertLess(plain, 0.8 * t.split_detail(a)[1].std())
        self.assertGreater(kept, 0.95 * t.split_detail(a)[1].std())

    def test_atlas_round_trip_and_page_name_budget(self):
        frames = [np.full((256, 256, 4), (i * 40, 90, 200 - i * 30, 255), np.uint8) for i in range(3)]
        with tempfile.TemporaryDirectory() as folder:
            tis, page = t.export_tiles(frames, "QTEST0", Path(folder))
            self.assertEqual(page.name, "QEST000.PVRZ")
            decoded = t.decode_tiles(tis, Path(folder))
        for got, want in zip(decoded, frames):
            self.assertTrue(np.array_equal(got[:, :, 3], want[:, :, 3]))
            self.assertLess(np.abs(got[:, :, :3].astype(int) - want[:, :, :3]).max(), 9)  # RGB565


if __name__ == "__main__":
    unittest.main()
