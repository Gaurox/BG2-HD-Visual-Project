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
