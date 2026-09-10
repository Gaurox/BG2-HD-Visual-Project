from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_joint_animation_rgb_seam as builder  # noqa: E402
import run_animation_upscale_30fps_v2 as runtime  # noqa: E402


class JointAnimationRgbSeamTests(unittest.TestCase):
    def make_pack(self, root: Path, resref: str, value: int, centre: tuple[int, int]) -> Path:
        pack = root / resref
        pack.mkdir(parents=True)
        frames = []
        assets = []
        for index in range(2):
            pixels = np.full((8, 12, 4), value + index, dtype=np.uint8)
            pixels[:, :, 3] = 255
            name = runtime.asset_name(resref, index)
            path = pack / name
            path.write_bytes(pixels.tobytes())
            record = {
                "frame": index,
                "logical_size_x1": [3, 2],
                "physical_size_x4": [12, 8],
                "centre_x1": list(centre),
                "asset": name,
                "sha256": runtime.sha256_file(path),
                "bytes": path.stat().st_size,
            }
            frames.append(record)
            assets.append({"name": name, "sha256": record["sha256"], "bytes": record["bytes"]})
        resource = {
            "resref": resref,
            "variant_index": 0,
            "frame_count": 2,
            "cycle_count": 1,
            "playback_mode": "TimedTimeline",
            "native_fps": {"numerator": 15, "denominator": 1},
            "target_fps": {"numerator": 30, "denominator": 1},
            "frames": frames,
            "assets": assets,
            "cycles": [{"cycle": 0, "native_frame_indices": [0],
                        "timeline_frame_indices": [0, 1]}],
        }
        registry = runtime.registry_v2_from_resources([resource])
        (pack / runtime.REGISTRY_NAME).write_bytes(registry)
        manifest = {
            "schema": runtime.PACK_SCHEMA,
            "status": "completed",
            "created_utc": runtime.utc_now(),
            "scale": 4,
            "registry_version": runtime.REGISTRY_VERSION,
            "runtime_contract": {"feature": "TimedTimeline", "clock": "QPC-pause-aware",
                                 "registry_version": runtime.REGISTRY_VERSION},
            "registry": runtime.REGISTRY_NAME,
            "registry_sha256": runtime.sha256_file(pack / runtime.REGISTRY_NAME),
            "registry_bytes": len(registry),
            "resource_count": 1,
            "frame_count": 2,
            "timed_resources": [resref],
            "raw_bytes": sum(item["bytes"] for item in assets),
            "runtime_budget_enforced": True,
            "resources": [resource],
        }
        runtime.write_json(pack / "manifest.json", manifest)
        runtime.validate_v2_pack(pack)
        return pack

    def test_repairs_joint_row_without_touching_alpha_or_outer_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            top_pack = self.make_pack(root, "TOP", 40, (1, 2))
            bottom_pack = self.make_pack(root, "BOTTOM", 180, (1, 1))
            top = builder.load_single_resource_pack(top_pack, (10, 20))
            bottom = builder.load_single_resource_pack(bottom_pack, (10, 21))
            output = root / "batch"

            report = builder.build(top, bottom, output, seam_depth_x4=4,
                                   alpha_threshold=128, write=True, resume=False)

            self.assertEqual(report["status"], "completed")
            self.assertLess(
                report["frame_reports"][0]["rgb_mae_after"],
                report["frame_reports"][0]["rgb_mae_before"],
            )
            for ref, source, value in (("TOP", top_pack, 40), ("BOTTOM", bottom_pack, 180)):
                result_pack = output / ref / "03_runtime_pack"
                _manifest, resources = runtime.validate_v2_pack(result_pack)
                for frame in resources[0]["frames"]:
                    name = frame["asset"]
                    original = np.frombuffer((source / name).read_bytes(), dtype=np.uint8).reshape(8, 12, 4)
                    repaired = np.frombuffer((result_pack / name).read_bytes(), dtype=np.uint8).reshape(8, 12, 4)
                    self.assertTrue(np.array_equal(original[:, :, 3], repaired[:, :, 3]))
                    if ref == "TOP":
                        self.assertTrue(np.array_equal(original[0, :, :3], repaired[0, :, :3]))
                    else:
                        self.assertTrue(np.array_equal(original[-1, :, :3], repaired[-1, :, :3]))
            top_boundary = np.frombuffer(
                (output / "TOP" / "03_runtime_pack" / runtime.asset_name("TOP", 0)).read_bytes(),
                dtype=np.uint8,
            ).reshape(8, 12, 4)[-1, :, :3]
            bottom_boundary = np.frombuffer(
                (output / "BOTTOM" / "03_runtime_pack" / runtime.asset_name("BOTTOM", 0)).read_bytes(),
                dtype=np.uint8,
            ).reshape(8, 12, 4)[0, :, :3]
            self.assertTrue(np.array_equal(top_boundary, bottom_boundary))

    def test_rejects_non_adjacent_world_geometry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            top = builder.load_single_resource_pack(self.make_pack(root, "TOP", 40, (1, 2)), (10, 20))
            bottom = builder.load_single_resource_pack(self.make_pack(root, "BOTTOM", 180, (1, 1)), (10, 22))
            with self.assertRaisesRegex(RuntimeError, "jointifs"):
                builder.build(top, bottom, root / "batch", seam_depth_x4=4,
                              alpha_threshold=128, write=False, resume=False)

    def test_restores_only_large_removed_alpha_component(self) -> None:
        current = np.zeros((20, 20, 4), dtype=np.uint8)
        reference = current.copy()
        reference[2:14, 2:14, 3] = 255
        reference[18, 18, 3] = 255

        restored, report = builder.restore_large_removed_alpha(current, reference, 100)

        self.assertEqual(report["selected_components"], 1)
        self.assertEqual(report["restored_alpha_pixels"], 144)
        self.assertTrue(np.all(restored[2:14, 2:14, 3] == 255))
        self.assertEqual(int(restored[18, 18, 3]), 0)

    def test_continue_top_into_bottom_preserves_top_rgb(self) -> None:
        top = np.full((8, 12, 4), 40, dtype=np.uint8)
        bottom = np.full((8, 12, 4), 180, dtype=np.uint8)
        top[:, :, 3] = 255
        bottom[:, :, 3] = 255
        layout_top = builder.FrameLayout(12, 8, 0, 0)
        layout_bottom = builder.FrameLayout(12, 8, 0, 8)

        repaired_top, repaired_bottom, _report = builder.repair_frame(
            top, bottom, top_layout=layout_top, bottom_layout=layout_bottom,
            seam_depth_x4=4, alpha_threshold=128,
            blend_mode="continue-top-into-bottom",
        )

        self.assertTrue(np.array_equal(repaired_top, top))
        self.assertTrue(np.array_equal(repaired_bottom[0, :, :3], top[-1, :, :3]))

    def test_top_overlap_fades_new_rows_and_preserves_existing_bottom(self) -> None:
        top = np.full((8, 12, 4), 40, dtype=np.uint8)
        bottom = np.full((8, 12, 4), 180, dtype=np.uint8)
        top[:, :, 3] = 255
        bottom[:, :, 3] = 200
        top_layout = builder.FrameLayout(12, 8, 0, 0)
        bottom_layout = builder.FrameLayout(12, 8, 0, 8)

        result, layout, report = builder.add_top_overlap(
            top, bottom, top_layout=top_layout, bottom_layout=bottom_layout,
            overlap_x4=4,
        )

        self.assertEqual(result.shape, (12, 12, 4))
        self.assertTrue(np.array_equal(result[4:], bottom))
        self.assertTrue(np.all(result[0, :, 3] == 0))
        self.assertTrue(np.all(result[1:4, :, 3] > 0))
        self.assertTrue(np.all(result[:4, :, :3] == 40))
        self.assertEqual(layout, builder.FrameLayout(12, 12, 0, 4))
        self.assertEqual(report["top_overlap_x1"], 1)

    def test_bilateral_overlap_preserves_source_over_colour_and_opacity(self) -> None:
        top = np.full((12, 12, 4), 40, dtype=np.uint8)
        bottom = np.full((12, 12, 4), 180, dtype=np.uint8)
        top[:, :, 3] = 200
        bottom[:, :, 3] = 200
        top_layout = builder.FrameLayout(12, 12, 0, 0)
        bottom_layout = builder.FrameLayout(12, 12, 0, 12)

        (result_top, result_bottom, layout_top, layout_bottom,
         report) = builder.add_bilateral_overlap(
            top, bottom, top_layout=top_layout, bottom_layout=bottom_layout,
            extension_x4=4,
        )

        self.assertEqual(result_top.shape, (16, 12, 4))
        self.assertEqual(result_bottom.shape, (16, 12, 4))
        self.assertTrue(np.all(result_bottom[0, :, 3] == 0))
        self.assertTrue(np.all(result_top[-1, :, 3] == 0))
        self.assertTrue(np.array_equal(result_top[:8], top[:8]))
        self.assertTrue(np.array_equal(result_bottom[8:], bottom[4:]))
        top_alpha = result_top[8:, :, 3].astype(np.float32)
        bottom_alpha = result_bottom[:8, :, 3].astype(np.float32)
        composite_alpha = bottom_alpha + top_alpha * (1.0 - bottom_alpha / 255.0)
        self.assertLessEqual(float(np.abs(composite_alpha - 200.0).max()), 1.0)
        self.assertTrue(np.array_equal(result_top[8:, :, :3],
                                       result_bottom[:8, :, :3]))
        self.assertEqual(layout_top, builder.FrameLayout(12, 16, 0, 0))
        self.assertEqual(layout_bottom, builder.FrameLayout(12, 16, 0, 8))
        self.assertEqual(report["total_overlap_x1"], 2)
        self.assertLessEqual(report["composite_alpha_max_error_u8"], 1.0)


if __name__ == "__main__":
    unittest.main()
