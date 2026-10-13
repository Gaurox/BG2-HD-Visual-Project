from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import effect_workflow as workflow  # noqa: E402
import run_effect_interpolation as interpolation  # noqa: E402


class EffectInterpolationManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.stage = self.root / "effects/ressources/TESTFX/runs/spatial/01-spatial-x4"
        self.stage.mkdir(parents=True)
        self.x1_manifest = self.stage.parent / "00-frames-x1/manifest.json"
        self.x1_manifest.parent.mkdir()
        self.x1_manifest.write_text(json.dumps({"cycles": [{"frame_indices": [0, 1]}]}), encoding="utf-8")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def test_variable_geometry_stays_on_the_current_native_slot(self) -> None:
        self.assertEqual(
            [interpolation.geometry_source_slot(phase, 2, 3) for phase in range(6)],
            [0, 0, 1, 1, 2, 2],
        )

    def test_one_shot_nearest_alpha_does_not_restart_at_the_final_phase(self) -> None:
        self.assertEqual(interpolation.alpha_source_slot(99, 50, 100), 0)
        self.assertEqual(
            interpolation.alpha_source_slot(99, 50, 100, loop_closed=False), 49
        )

    def test_left_alpha_keeps_the_last_visible_slot_for_both_target_phases(self) -> None:
        slots = [interpolation.alpha_source_slot(phase, 50, 100,
                                                loop_closed=False, policy="left")
                 for phase in (36, 37, 38, 99)]
        self.assertEqual(slots, [18, 18, 19, 49])

    def test_duplicate_digest_ignores_hidden_rgb_but_keeps_visible_position(self) -> None:
        left = Image.new("RGBA", (2, 2), (255, 0, 0, 0))
        left.putpixel((1, 1), (0, 100, 255, 255))
        right = Image.new("RGBA", (2, 2), (0, 255, 0, 0))
        right.putpixel((1, 1), (0, 100, 255, 255))
        digest = interpolation.visible_frame_digest(left, (8, 8), (2, 3))
        self.assertEqual(digest, interpolation.visible_frame_digest(right, (8, 8), (2, 3)))
        self.assertNotEqual(digest, interpolation.visible_frame_digest(right, (8, 8), (3, 3)))
        self.assertIsNone(interpolation.visible_frame_digest(
            Image.new("RGBA", (2, 2), (255, 255, 255, 0)), (8, 8), (2, 3)))

    def test_native_pause_and_one_shot_endpoint_are_preserved(self) -> None:
        poses = ["red", "red", "blue"]
        self.assertEqual([interpolation.native_hold_identity(p, 2, poses, loop_closed=False)
                          for p in range(6)], ["red", "red", "red", None, "blue", "blue"])

    def test_interpolated_motion_and_loop_wrap_cannot_claim_a_native_hold(self) -> None:
        poses = ["red", "green", "blue"]
        self.assertEqual([interpolation.native_hold_identity(p, 2, poses, loop_closed=True)
                          for p in range(6)], ["red", None, "green", None, "blue", None])

    def test_repeated_native_subsequence_allows_the_same_transition_not_a_freeze(self) -> None:
        poses = ["red", "green", "blue", "red", "green", "blue"]
        lineage = lambda p: interpolation.native_phase_lineage(p, 2, poses, loop_closed=False)
        self.assertEqual(lineage(1), lineage(7))
        self.assertNotEqual(lineage(1), lineage(3))
        self.assertNotEqual(lineage(1), lineage(0))

    def test_variable_frames_use_the_common_aligned_canvas(self) -> None:
        frames = []
        for index, logical, crop in ((0, [1, 1], [4, 0, 8, 4]), (1, [2, 1], [0, 0, 8, 4])):
            physical = [logical[0] * 4, logical[1] * 4]
            raw = self.stage / f"raw/frame_{index:03d}.rgba"
            alpha = self.stage / f"alpha/frame_{index:03d}.png"
            aligned = self.stage / f"aligned/frame_{index:03d}.png"
            raw.parent.mkdir(exist_ok=True)
            alpha.parent.mkdir(exist_ok=True)
            aligned.parent.mkdir(exist_ok=True)
            raw.write_bytes(b"\0" * (physical[0] * physical[1] * 4))
            alpha.write_bytes(b"alpha")
            Image.new("RGBA", (12, 8), (0, 0, 0, 0)).save(aligned, format="PNG")
            frames.append({
                "frame": index,
                "logical_size_x1": logical,
                "physical_size_xn": physical,
                "raw_rgba_xn": raw.relative_to(self.stage).as_posix(),
                "raw_rgba_xn_sha256": workflow.sha256_file(raw),
                "alpha_xn": alpha.relative_to(self.stage).as_posix(),
                "alpha_xn_sha256": workflow.sha256_file(alpha),
                "aligned_size_x1": [3, 2],
                "aligned_rgba_xn": aligned.relative_to(self.stage).as_posix(),
                "aligned_rgba_xn_sha256": workflow.sha256_file(aligned),
                "runtime_crop_box_xn": crop,
            })
        manifest = self.stage / "manifest.json"
        manifest.write_text(json.dumps({
            "schema": interpolation.SPATIAL_SCHEMA,
            "status": "completed",
            "scale": 4,
            "frames": frames,
            "source": {
                "frame_manifest": self.x1_manifest.relative_to(self.root).as_posix(),
                "frame_manifest_sha256": workflow.sha256_file(self.x1_manifest),
            },
        }), encoding="utf-8")
        plan = interpolation.InterpolationPlan(
            root=self.root, resref="TESTFX", asset={}, spatial_run="spatial", run_id="interpolation",
            run_root=self.stage.parent / "interpolation", parent_descriptor=self.stage.parent / "run.json",
            parent_output={}, spatial_manifest=manifest, recipe_id="apollo8", native_fps=15,
            target_fps=30, tvai_ffmpeg=Path("ffmpeg"), tvai_model_dir=Path("models"), model="apo-8", device="-2",
        )
        validated = interpolation.validate_spatial_manifest(plan)
        self.assertEqual(validated["_interpolation_input"], "aligned")
        self.assertEqual(validated["_interpolation_physical"], (12, 8))


if __name__ == "__main__":
    unittest.main()
