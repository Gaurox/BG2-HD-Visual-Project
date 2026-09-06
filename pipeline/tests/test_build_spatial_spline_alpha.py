from __future__ import annotations

import sys
import unittest
from pathlib import Path

import numpy as np


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_spatial_spline_alpha as builder  # noqa: E402


class SpatialSplineAlphaTests(unittest.TestCase):
    def test_reconstruction_never_changes_alpha_outside_its_bounded_region(self) -> None:
        source = np.zeros((32, 32), dtype=np.uint8)
        source[4:20, 4:20] = 255
        source[8:12, 10:14] = 0
        spline = source.copy()

        result, report = builder.reconstruct_local_alpha(
            spline,
            source,
            region=(0, 0, 24, 24),
            sigma=2.0,
            minimum_alpha=1,
            transition=4,
        )

        np.testing.assert_array_equal(result[:, 24:], spline[:, 24:])
        np.testing.assert_array_equal(result[24:, :], spline[24:, :])
        self.assertGreater(result[9, 11], 0)
        self.assertGreater(report["raised_over_source_pixels"], 0)

    def test_reconstruction_gate_rejects_an_out_of_frame_region(self) -> None:
        with self.assertRaisesRegex(SystemExit, "hors frame"):
            builder.reconstruction_gate(20, 20, (0, 0, 21, 10), 2)

    def test_safe_boundary_preserves_core_and_limits_outset(self) -> None:
        source = np.zeros((48, 48), dtype=np.uint8)
        source[8:40, 8:40] = 255

        result, report = builder.safe_boundary_spline_alpha(
            source,
            threshold=127,
            fit_error=1.0,
            spacing=1.5,
            supersample=4,
            padding=8,
            inner_band=6.0,
            outer_band=4.0,
        )

        self.assertEqual(int(result[24, 24]), 255)
        outside_distance = builder.ndimage.distance_transform_edt(source == 0)
        self.assertFalse(np.any((result > source) & (outside_distance > 4.0)))
        self.assertEqual(report["mode"], "safe-boundary")

    def test_contour_gaussian_never_expands_alpha(self) -> None:
        alpha = np.zeros((48, 48), dtype=np.uint8)
        alpha[8:40, 8:40] = 255

        result, report = builder.blur_all_contours(alpha, sigma=2.0)

        self.assertTrue(np.all(result <= alpha))
        np.testing.assert_array_equal(result[alpha == 0], np.zeros(np.count_nonzero(alpha == 0), dtype=np.uint8))
        self.assertEqual(int(result[24, 24]), 255)
        self.assertGreater(report["changed_alpha_pixels"], 0)
        self.assertEqual(report["outside_alpha_pixels"], 0)

    def test_all_contour_fade_preserves_core_and_never_expands_alpha(self) -> None:
        alpha = np.zeros((96, 96), dtype=np.uint8)
        alpha[16:80, 16:80] = 255

        result, report = builder.fade_all_contours(
            alpha, threshold=127, fade_width=16.0
        )

        self.assertTrue(np.all(result <= alpha))
        self.assertEqual(int(result[16, 48]), 0)
        self.assertEqual(int(result[48, 48]), 255)
        self.assertGreater(report["changed_alpha_pixels"], 0)
        self.assertEqual(report["outside_alpha_pixels"], 0)

    def test_bottom_seam_restores_only_the_lower_fade_progressively(self) -> None:
        pre_fade = np.full((64, 24), 255, dtype=np.uint8)
        faded = np.full((64, 24), 32, dtype=np.uint8)

        result, report = builder.restore_bottom_seam(
            faded,
            pre_fade,
            protected_depth=8,
            transition=16,
        )

        np.testing.assert_array_equal(result[:39], faded[:39])
        self.assertGreater(int(result[48, 12]), 32)
        self.assertEqual(int(result[63, 12]), 255)
        self.assertGreater(report["changed_alpha_pixels"], 0)

    def test_world_aligned_protection_projects_by_frame_centre(self) -> None:
        mask = np.arange(100 * 120, dtype=np.float32).reshape((100, 120))

        projected, report = builder.project_fade_protection_mask(
            mask,
            mask_origin_x4=(-60, -80),
            centre_x1=(10, 15),
            frame_size_x4=(32, 24),
        )

        np.testing.assert_array_equal(projected, mask[20:44, 20:52])
        self.assertEqual(report["frame_origin_x4"], [-40, -60])
        self.assertEqual(report["mask_crop_x4"], [20, 20, 52, 44])

    def test_painted_protection_restores_only_its_coverage(self) -> None:
        pre_fade = np.full((16, 16), 240, dtype=np.uint8)
        faded = np.full((16, 16), 24, dtype=np.uint8)
        protection = np.zeros((16, 16), dtype=np.float32)
        protection[:, 8:] = 1.0

        result, report = builder.apply_fade_protection(faded, pre_fade, protection)

        np.testing.assert_array_equal(result[:, :8], faded[:, :8])
        np.testing.assert_array_equal(result[:, 8:], pre_fade[:, 8:])
        self.assertEqual(report["fully_protected_pixels"], 128)

    def test_painted_foreground_occlusion_clips_white_and_restores_outer_seam(self) -> None:
        pre_fade = np.full((32, 32), 240, dtype=np.uint8)
        faded = np.full((32, 32), 24, dtype=np.uint8)
        foreground = np.zeros((32, 32), dtype=np.float32)
        foreground[:, :12] = 1.0

        result, report = builder.apply_painted_foreground_occlusion(
            faded,
            pre_fade,
            foreground,
            protected_depth=2.0,
            transition=6.0,
            clip_feather=0.5,
        )

        self.assertEqual(int(result[16, 4]), 0)
        self.assertGreater(int(result[16, 13]), int(faded[16, 13]))
        self.assertEqual(int(result[16, 28]), int(faded[16, 28]))
        self.assertGreater(report["restored_over_fade_pixels"], 0)
        self.assertGreater(report["removed_from_fade_pixels"], 0)

    def test_painted_foreground_contact_can_preserve_a_native_cutout(self) -> None:
        pre_fade = np.full((32, 32), 240, dtype=np.uint8)
        faded = np.full((32, 32), 24, dtype=np.uint8)
        foreground = np.zeros((32, 32), dtype=np.float32)
        foreground[:, :12] = 1.0

        result, report = builder.apply_painted_foreground_occlusion(
            faded,
            pre_fade,
            foreground,
            protected_depth=0.0,
            transition=6.0,
            clip_feather=0.5,
            clip_foreground=False,
        )

        np.testing.assert_array_equal(result[:, :12], faded[:, :12])
        self.assertGreater(int(result[16, 12]), int(faded[16, 12]))
        self.assertEqual(int(result[16, 28]), int(faded[16, 28]))
        self.assertFalse(report["clip_foreground"])

    def test_premultiplied_rgb_gaussian_avoids_transparent_black_fringe(self) -> None:
        rgb = np.zeros((32, 32, 3), dtype=np.uint8)
        rgb[8:24, 8:24] = (220, 80, 40)
        rgb[12:20, 12:20] = (40, 180, 220)
        alpha = np.zeros((32, 32), dtype=np.uint8)
        alpha[8:24, 8:24] = 255

        result, report = builder.blur_rgb_premultiplied(rgb, alpha, sigma=2.0)

        self.assertGreater(int(result[8, 8, 0]), 200)
        np.testing.assert_array_equal(result[alpha == 0], rgb[alpha == 0])
        self.assertGreater(report["changed_rgb_pixels"], 0)

    def test_left_edge_blur_is_limited_to_left_band(self) -> None:
        source = np.zeros((32, 32), dtype=np.uint8)
        source[4:28, 10:24] = 255

        result, report = builder.blur_left_edge(
            source,
            source,
            threshold=127,
            sigma=2.0,
            inner_band=5,
            outer_band=4,
        )

        np.testing.assert_array_equal(result[:, 16:], source[:, 16:])
        self.assertGreater(report["changed_alpha_pixels"], 0)

    def test_local_reinforcement_keeps_a_canvas_touching_tip_opaque(self) -> None:
        source = np.zeros((32, 32), dtype=np.uint8)
        source[24:32, 14:18] = 255
        spline = source.copy()
        spline[31, 14:18] = 24

        result, report = builder.reinforce_local_alpha(
            spline,
            source,
            region=(8, 20, 24, 32),
            threshold=127,
            outset=2.0,
            feather=2.0,
            transition=0,
        )

        np.testing.assert_array_equal(result[31, 14:18], np.full(4, 255, dtype=np.uint8))
        np.testing.assert_array_equal(result[:20, :], spline[:20, :])
        self.assertGreater(report["raised_over_spline_pixels"], 0)
        self.assertGreater(report["raised_over_source_pixels"], 0)
