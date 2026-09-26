"""Synthetic checks of the x4 RGB matte contour recipe; no game files or runs."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build_water_contour_matte_trial import edge_rgb, silhouette


def scene():
    """Brown bar drawn thinner than its blocky native mask, light green rim, black matte."""
    rgb = np.zeros((96, 96, 3), np.uint8)
    native = np.zeros((96, 96), bool)
    native[20:76, 20:52] = True              # native x1 staircase, 4 px wider than the drawing
    rgb[20:76, 24:48] = (120, 80, 40)
    rgb[20:76, 24] = rgb[20:76, 47] = (150, 190, 150)   # SeedVR light rim
    return rgb, native


class ContourMatteTests(unittest.TestCase):
    def test_coverage_follows_the_drawn_edge_not_the_native_mask(self):
        rgb, native = scene()
        obj, coverage = silhouette(rgb, native)
        row = coverage[48]
        self.assertEqual(row[21], 0.0)        # native but black: now water
        self.assertEqual(row[30], 1.0)
        self.assertTrue(0 < row[23] < 1 or row[24] == 1.0)

    def test_light_rim_is_recoloured_and_colour_carried_outward(self):
        rgb, native = scene()
        obj, _ = silhouette(rgb, native)
        out, report = edge_rgb(rgb, obj)
        self.assertGreater(report['wide_rim_px'], 0)
        np.testing.assert_allclose(out[48, 24], (120, 80, 40), atol=3)
        self.assertGreater(out[48, 22].max(), 20)        # no black under partial coverage

    def test_dark_native_interior_stays_opaque(self):
        rgb, native = scene()
        rgb[40:44, 30:40] = 0                              # legitimate black detail
        _, coverage = silhouette(rgb, native)
        self.assertTrue(np.all(coverage[40:44, 30:40] == 1.0))

    def test_spline_fit_default_and_map_exceptions_come_from_the_standard(self):
        import build_water_contour_matte as m
        self.assertEqual(m.contour_spline_fit("AR1600"), 1.0)
        self.assertIsNone(m.contour_spline_fit("AR0408"))          # map exception: earlier matte
        self.assertIsNone(m.contour_spline_fit("AR0506"))
        self.assertIsNone(m.contour_spline_fit("AR0703"))
        self.assertIsNone(m.contour_spline_fit("AR1003"))
        self.assertIsNone(m.contour_spline_fit("AR1004"))
        self.assertIsNone(m.contour_spline_fit("AR1600", 0.0))     # explicit off
        self.assertEqual(m.contour_spline_fit("AR0408", 2.0), 2.0) # explicit wins
        self.assertEqual(m.contour_water_alpha("AR1600", 128), 128)
        self.assertEqual(m.contour_water_alpha("AR0300N", 128), 160)
        self.assertEqual(m.contour_action("AR1600"), "build")
        self.assertEqual(m.contour_action("AR0300N"), "preserve-base")
        self.assertEqual(m.contour_action("AR1604"), "build")
        self.assertEqual(m.contour_spline_constraint("AR1600"), "none")
        self.assertEqual(m.contour_spline_constraint("AR1604"), "protect-black")

    def test_black_void_is_frozen_but_visible_shore_can_be_refitted(self):
        import build_water_contour_matte as m
        rgb, native = scene()
        native[4:12, 4:12] = True           # disconnected black room/void border
        protected = m.protected_black_mask(rgb, native)
        self.assertTrue(protected[8, 8])
        self.assertFalse(protected[48, 21]) # black matte next to drawn visible shore
        secondary = np.where(native, 0, 255).astype(np.uint8)
        fitted = np.zeros(native.shape)
        safe, _ = m.constrain_spline_coverage(fitted, secondary, 'protect-black', protected)
        self.assertEqual(safe[8, 8], 1.0)
        self.assertEqual(safe[48, 21], 0.0)

    def test_no_new_secondary_constraint_only_raises_primary_coverage(self):
        import build_water_contour_matte as m
        fitted = np.array([[0.10, 0.75], [0.90, 0.20]])
        secondary = np.array([[0, 128], [255, 64]], np.uint8)
        safe, blocked = m.constrain_spline_coverage(
            fitted, secondary, "no-new-secondary")
        source_floor = 1.0 - secondary.astype(np.float64) / 255.0
        self.assertTrue(np.all(safe >= fitted))
        self.assertTrue(np.all(1.0 - safe <= secondary / 255.0))
        self.assertEqual(blocked, int((fitted < source_floor).sum()))

    def test_thin_black_panel_trim_is_not_exterior_void(self):
        import build_water_contour_matte as m
        rgb, native = scene()
        native[4:12, 4:12] = True            # broad opaque black component
        native[84:88, 20:76] = True          # disconnected thin black wooden cap
        protected = m.protected_black_mask(rgb, native)
        self.assertTrue(np.all(protected[4:12, 4:12]))
        self.assertFalse(protected[84:88, 20:76].any())

    def test_spline_coverage_keeps_bounds_and_smooths_a_staircase(self):
        import build_water_contour_matte as m
        native = np.zeros((96, 96), bool)
        for i in range(0, 64, 8):                                  # x1-like 8 px staircase
            native[16 + i:24 + i, 16:24 + i] = True
        coverage, report = m.spline_coverage(native.copy(), native, 1.0)
        self.assertGreater(report["rings"], 0)
        self.assertTrue(np.all(coverage[native & (np.pad(native, 5)[5:-5, 5:-5])] >= 0))
        self.assertEqual(coverage[0, 0], 0.0)                      # far outside stays water
        self.assertTrue(np.all(coverage[20:22, 18:20] == 1.0))     # deep interior opaque


if __name__ == "__main__":
    unittest.main()
