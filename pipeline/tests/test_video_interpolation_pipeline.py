from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "run_video_interpolation", SCRIPTS / "run_video_interpolation.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VideoInterpolationPipelineTests(unittest.TestCase):
    def test_recipe_is_sealed_as_apollo8_exact_2x(self) -> None:
        recipe = MODULE.load_recipe(MODULE.DEFAULT_RECIPE)
        self.assertEqual(recipe["topaz"]["model"], "apo-8")
        self.assertEqual(recipe["topaz"]["target_fps"], "30/1")
        self.assertEqual(recipe["topaz"]["replace_duplicate_threshold"], -0.01)
        self.assertFalse(recipe["topaz"]["approximate_duplicate_detection"])
        self.assertTrue(recipe["timeline"]["exact_duplicate_postpass"]["enabled"])
        self.assertEqual(recipe["timeline"]["audio"], "excluded")

    def test_recipe_hash_drift_is_rejected(self) -> None:
        payload = json.loads(MODULE.DEFAULT_RECIPE.read_text(encoding="utf-8"))
        payload["topaz"]["replace_duplicate_threshold"] = 0.01
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "recipe.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "recette non approuvée"):
                MODULE.load_recipe(path)

    def test_filter_disables_approximate_duplicate_detection(self) -> None:
        recipe = MODULE.load_recipe(MODULE.DEFAULT_RECIPE)
        filter_text = MODULE.topaz_filter(recipe)
        self.assertIn("model=apo-8", filter_text)
        self.assertIn("fps=30", filter_text)
        self.assertIn("rdt=-0.01", filter_text)
        self.assertIn("setpts=N/(30*TB)", filter_text)

    def test_exact_duplicate_indices_collapse_adjacent_runs_only(self) -> None:
        self.assertEqual(
            MODULE.exact_duplicate_indices(["a", "a", "a", "b", "a", "a"]),
            [1, 2, 5],
        )

    def test_parent_run_requires_sealed_upscale_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "video" / "source.mp4"
            descriptor_path = root / "video" / "flythr03" / "runs" / "upscale" / "run.json"
            descriptor_path.parent.mkdir(parents=True)
            source.write_bytes(b"sealed-upscale")
            descriptor = {
                "domain": "videos",
                "run_id": "upscale",
                "asset_ids": ["videos:movie-default-flythr03"],
                "outputs": [
                    {
                        "role": "upscale-technical-video",
                        "path": "video/runs/upscale/source.mp4",
                        "sha256": MODULE.sha256_file(source),
                        "bytes": source.stat().st_size,
                    }
                ],
                "result": {"status": "completed", "sealed": True},
            }
            descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
            original_root, original_video_root = MODULE.ROOT, MODULE.VIDEO_ROOT
            try:
                MODULE.ROOT = root
                MODULE.VIDEO_ROOT = root / "video"
                migrated_source = descriptor_path.parent / "source.mp4"
                source.replace(migrated_source)
                loaded = MODULE.load_upscale_run("upscale")
                self.assertEqual(loaded["source"], migrated_source)
                self.assertEqual(loaded["asset_dir"], root / "video/flythr03")
                descriptor["result"]["sealed"] = False
                descriptor_path.write_text(json.dumps(descriptor), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "non terminé"):
                    MODULE.load_upscale_run("upscale")
            finally:
                MODULE.ROOT = original_root
                MODULE.VIDEO_ROOT = original_video_root

    def test_output_contract_allows_only_exact_postpass_removals(self) -> None:
        source = {
            "width": 1920,
            "height": 1080,
            "frame_rate": "15/1",
            "frame_count": 261,
        }
        topaz = {
            "width": 1920,
            "height": 1080,
            "frame_rate": "30/1",
            "frame_count": 521,
        }
        output = {
            "width": 1920,
            "height": 1080,
            "frame_rate": "30/1",
            "frame_count": 519,
            "field_order": "progressive",
            "audio_codec": "",
            "video_codec": "prores",
        }
        checks = MODULE.validate_output_probe(source, topaz, output, 2)
        self.assertTrue(all(checks.values()))
        with self.assertRaisesRegex(RuntimeError, "output_frame_count"):
            MODULE.validate_output_probe(source, topaz, dict(output, frame_count=518), 2)

    def test_run_descriptor_links_parent_without_qa_or_selection(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "video" / "source.mp4"
            recipe = root / "pipeline" / "recipe.json"
            source.parent.mkdir(parents=True)
            recipe.parent.mkdir(parents=True)
            source.write_bytes(b"video")
            recipe.write_text("{}\n", encoding="utf-8")
            original_root = MODULE.ROOT
            try:
                MODULE.ROOT = root
                descriptor = MODULE.run_descriptor(
                    run_id="interpolation-test",
                    asset_id="videos:movie-default-flythr03",
                    parent_run_id="upscale-test",
                    source=source,
                    recipe=recipe,
                    status="completed",
                    sealed=True,
                    created_at="2026-08-31T00:00:00Z",
                )
            finally:
                MODULE.ROOT = original_root
            self.assertEqual(
                descriptor["provenance"]["parents"], ["videos:upscale-test"]
            )
            self.assertNotIn("qa", descriptor)
            self.assertNotIn("selection", descriptor)


if __name__ == "__main__":
    unittest.main()
