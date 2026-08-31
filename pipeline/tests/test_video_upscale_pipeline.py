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

import audit_workspace_integrity as AUDIT

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

    def test_workspace_audit_indexes_sealed_video_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "video/index").mkdir(parents=True)
            (root / "video/index/resources.csv").write_text(
                "asset_key\nmovie:default:FLYTHR03\n", encoding="utf-8"
            )
            (root / "docs").mkdir()
            (root / "docs/workspace-cleanup-manifest.json").write_text(
                '{"operations": []}\n', encoding="utf-8"
            )
            recipe = root / "pipeline/workflow.json"
            recipe.parent.mkdir()
            recipe.write_text("{}\n", encoding="utf-8")
            source = root / "video/source.wbm"
            output = root / "video/flythr03/runs/test/02_upscale/output.mp4"
            output.parent.mkdir(parents=True)
            source.write_bytes(b"source")
            output.write_bytes(b"output")

            def evidence(path: Path) -> dict[str, object]:
                return {
                    "path": path.relative_to(root).as_posix(),
                    "sha256": MODULE.sha256_file(path),
                    "bytes": path.stat().st_size,
                }

            descriptor = {
                "$schema": "docs/workspace-run.schema.json",
                "schema_version": 1,
                "run_id": "test",
                "domain": "videos",
                "asset_ids": ["videos:movie-default-flythr03"],
                "pipeline": {
                    "id": MODULE.PIPELINE_ID,
                    "recipe_path": "pipeline/workflow.json",
                    "recipe_sha256": MODULE.sha256_file(recipe),
                },
                "inputs": [evidence(source)],
                "outputs": [evidence(output)],
                "result": {"status": "completed", "sealed": True},
            }
            (root / "video/flythr03/runs/test/run.json").write_text(
                json.dumps(descriptor), encoding="utf-8"
            )
            (root / "video/index/processing.csv").write_text(
                "asset_key,asset_id,asset_directory,upscale_run,upscale_state,"
                "interpolation_run,interpolation_state,validation_scope,patch_run,"
                "patch_output_role,patch_state,notes\n"
                "movie:default:FLYTHR03,videos:movie-default-flythr03,video/flythr03,"
                "test,validated,,,pipeline-method,,,not-integrated,test\n",
                encoding="utf-8",
            )
            original_root = AUDIT.ROOT
            try:
                AUDIT.ROOT = root
                issues: list[dict[str, object]] = []
                runs: dict[str, dict[str, object]] = {}
                summary = AUDIT.audit_video_runs(issues, runs)
            finally:
                AUDIT.ROOT = original_root
            self.assertEqual(issues, [])
            self.assertEqual(summary["physical_run_count"], 1)
            self.assertEqual(runs["videos:test"]["provenance_state"], "verified")
            self.assertEqual(runs["videos:test"]["selection_state"], "validated-upscale")
            self.assertEqual(summary["method_validated_run_count"], 1)
            self.assertEqual(summary["patch_selected_run_count"], 0)


if __name__ == "__main__":
    unittest.main()
