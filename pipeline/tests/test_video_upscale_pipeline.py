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
    "run_video_upscale", SCRIPTS / "run_video_upscale.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class VideoUpscalePipelineTests(unittest.TestCase):
    def test_canonical_workflow_is_sealed_and_temporally_chunked(self) -> None:
        _, summary = MODULE.validate_workflow(MODULE.DEFAULT_WORKFLOW)
        self.assertEqual(summary["model"], "seedvr2_3b_int8_convrot.safetensors")
        self.assertEqual(summary["vae_encode"]["tile_size"], 512)
        self.assertEqual(summary["vae_decode"]["overlap"], 128)
        self.assertEqual(
            summary["temporal_chunking"],
            {"enabled": True, "mode": "auto", "overlap": 0},
        )
        self.assertEqual(
            (summary["target_width"], summary["target_height"]), (1920, 1080)
        )
        self.assertEqual(summary["color_correction"], "lab")

    def test_workflow_hash_drift_is_rejected(self) -> None:
        payload = json.loads(MODULE.DEFAULT_WORKFLOW.read_text(encoding="utf-8"))
        payload["66:54"]["inputs"]["seed"] += 1
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "workflow.json"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "workflow non approuvé"):
                MODULE.validate_workflow(path)

    def test_asset_scope_accepts_cinematic_and_rejects_tutorial(self) -> None:
        asset = MODULE.load_asset("movie:default:FLYTHR03")
        self.assertEqual(asset["role"], "cinematic")
        self.assertEqual(MODULE.stable_video_asset_id(asset["asset_key"]),
                         "videos:movie-default-flythr03")
        self.assertEqual(MODULE.asset_directory(asset), ROOT / "video/flythr03")
        with self.assertRaisesRegex(RuntimeError, "cinématiques"):
            MODULE.load_asset("tutorial:engine:TUT01")

    def test_output_contract_proves_no_interpolation(self) -> None:
        source = {
            "width": 1280,
            "height": 720,
            "frame_rate": "15/1",
            "frame_count": 261,
            "field_order": "progressive",
        }
        output = {
            "width": 1920,
            "height": 1080,
            "frame_rate": "15/1",
            "frame_count": 261,
            "field_order": "progressive",
        }
        checks = MODULE.validate_output_probe(source, output)
        self.assertTrue(checks["frame_count_preserved"])
        self.assertIn("absent", checks["interpolation"])

        changed = dict(output, frame_count=522)
        with self.assertRaisesRegex(RuntimeError, "frame_count_preserved"):
            MODULE.validate_output_probe(source, changed)

    def test_run_descriptor_keeps_later_stages_out_of_scope(self) -> None:
        source = ROOT / "video" / "flythr03" / "flythr03.wbm"
        descriptor = MODULE.run_descriptor(
            run_id="flythr03-test-v1",
            asset_id="videos:movie-default-flythr03",
            source=source,
            workflow=MODULE.DEFAULT_WORKFLOW,
            status="completed",
            sealed=True,
            completed_at="2026-08-31T00:00:00Z",
            notes="upscale uniquement",
        )
        self.assertEqual(descriptor["$schema"], "docs/workspace-run.schema.json")
        self.assertEqual(descriptor["domain"], "videos")
        self.assertTrue(descriptor["result"]["sealed"])
        self.assertNotIn("selection", descriptor)
        self.assertNotIn("qa", descriptor)

if __name__ == "__main__":
    unittest.main()
