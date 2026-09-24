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

    def test_torus_pairs_accept_lava_adjacency_only(self):
        pairs = t.torus_pairs([["A", "B"], ["C", "D"]])
        self.assertEqual(len(pairs), 8)
        self.assertIn(("B", "A", "x"), pairs)
        self.assertIn(("D", "B", "y"), pairs)
        self.assertNotIn(("A", "A", "x"), pairs)
        self.assertNotIn(("A", "C", "x"), pairs)

    def test_defaults_refuse_any_adjacency_outside_the_torus(self):
        self.assertEqual(t.TORUS_DEFAULTS["max_non_torus_share"], 0.0)
        self.assertEqual((t.TORUS_DEFAULTS["temporal_harmonics"], t.TORUS_DEFAULTS["equalize_detail"]), (0, False))

    def test_heal_torus_seams_flattens_a_border_step_and_keeps_texture(self):
        rng = np.random.default_rng(3)
        motif = rng.normal(128, 6, (128, 128, 3))
        stepped = motif.copy()
        stepped[:, 64:] += 12          # one tile brighter: steps at x=64 and at the wrap
        before = t.border_step_ratio(stepped)[0]
        healed = t.heal_torus_seams(stepped, band=4, sigma=3.0, gain=1.0)
        self.assertGreater(before, 1.5)
        self.assertLess(t.border_step_ratio(healed)[0], 1.15)
        interior = (slice(8, 56), slice(8, 56))
        np.testing.assert_allclose(healed[interior], stepped[interior])

    def test_deridge_removes_a_border_line_and_keeps_texture(self):
        rng = np.random.default_rng(7)
        motif = rng.normal(128, 4, (128, 128, 3))
        lined = motif.copy()
        lined[[63, 64, 127, 0]] += 3.0             # bright line on every horizontal tile border
        self.assertGreater(t.border_line_profile(lined)[1], 1.0)
        cleaned = t.deridge_torus_seams(lined, band=2, sigma=6.0)
        self.assertLess(t.border_line_profile(cleaned)[1], 0.4)
        interior = (slice(8, 56), slice(8, 56))
        np.testing.assert_allclose(cleaned[interior], lined[interior])
        self.assertLess(np.abs(cleaned - motif).mean(), 0.2 * np.abs(lined - motif).mean() + 0.2)

    def test_periodic_component_removes_wrap_step_and_keeps_mean(self):
        rng = np.random.default_rng(4)
        ramp = np.linspace(0, 60, 64)[None, :, None] + rng.normal(0, 3, (64, 64, 3))
        periodic = t.periodic_component(ramp)
        self.assertGreater(t.border_step_ratio(ramp, 64)[0], 5)
        self.assertLess(t.border_step_ratio(periodic, 64)[0], 1.5)
        self.assertAlmostEqual(periodic.mean(), ramp.mean(), places=6)

    def test_temporal_lowpass_keeps_interpolated_motion_and_drops_latent_cadence(self):
        rng = np.random.default_rng(5)
        keys = rng.uniform(0, 255, (6, 8, 8, 3))
        motion = t.trig_interpolate(keys, 72)
        cadence = np.zeros_like(motion)
        cadence[::4] = 5.0                          # SeedVR 4-frame latent pattern
        cadence -= cadence.mean(axis=0)             # its mean is not motion
        noisy = motion + cadence + rng.normal(0, 3, motion.shape)
        filtered = t.temporal_lowpass(noisy, 9)
        np.testing.assert_allclose(t.temporal_lowpass(motion, 9), motion, atol=1e-9)
        self.assertLess(np.abs(filtered - motion).mean(), 0.5 * np.abs(noisy - motion).mean())
        profile = t.loop_metrics(filtered)["cadence4"]
        self.assertLess(max(profile) - min(profile), 0.1)

    def test_equalize_detail_flattens_sharpness_pulse(self):
        rng = np.random.default_rng(6)
        base = rng.normal(128, 20, (64, 64, 3))
        frames = np.stack([128 + (base - 128) * (0.85 + 0.3 * (i % 2)) for i in range(8)])
        self.assertGreater(t.loop_metrics(frames)["sharpness_max_min"], 1.3)
        self.assertLess(t.loop_metrics(t.equalize_detail(frames))["sharpness_max_min"], 1.1)

    def test_torus_tiles_margin_reads_the_neighbour_and_survives_export(self):
        motif = np.zeros((512, 512, 4), np.uint8)
        motif[..., 3] = 255
        motif[:, :256, 0] = 200         # A and C red, B and D blue
        motif[:, 256:, 2] = 200
        tiles = t.torus_tiles(motif, [["A", "B"], ["C", "D"]])
        self.assertEqual(tiles["A"].shape, (t.STRIDE, t.STRIDE, 4))
        self.assertEqual(tiles["A"][100, -1, 2], 200)   # right margin of A = B
        self.assertEqual(tiles["A"][100, 0, 2], 200)    # left margin of A = B (wrap)
        with tempfile.TemporaryDirectory() as folder:
            tis, _ = t.export_tiles([tiles["A"]], "QTEST0", Path(folder))
            decoded = t.decode_tiles(tis, Path(folder))
        self.assertLess(np.abs(decoded[0][:, :, :3].astype(int) - tiles["A"][4:-4, 4:-4, :3]).max(), 9)


if __name__ == "__main__":
    unittest.main()
