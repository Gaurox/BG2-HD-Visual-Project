from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import effect_workflow as workflow  # noqa: E402
import run_effect_spatial as spatial  # noqa: E402


class EffectSpatialRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.resref = "TESTFX"
        self.source = self.root / f"effects/ressources/{self.resref}/source.bam"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"stock-effect-bam")
        self.workflow_path = self.root / "workflows/seedvr.json"
        self.workflow_path.parent.mkdir(parents=True)
        self.workflow_path.write_text('{"workflow":"test"}\n', encoding="utf-8")
        self._write_authorities()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_authorities(self) -> None:
        inventory = self.root / "effects/index/bam-assets.csv"
        inventory.parent.mkdir(parents=True, exist_ok=True)
        fields = (
            "asset_key", "resref", "source_state", "source_sha256", "source_size",
            "extracted_path",
        )
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerow(
            {
                "asset_key": f"effects:bam:{self.resref}",
                "resref": self.resref,
                "source_state": "available",
                "source_sha256": workflow.sha256_file(self.source),
                "source_size": self.source.stat().st_size,
                "extracted_path": self.source.relative_to(self.root).as_posix(),
            }
        )
        inventory.write_text(stream.getvalue(), encoding="utf-8")
        processing = {
            "asset_key": f"effects:bam:{self.resref}",
            "asset_directory": f"effects/ressources/{self.resref}",
            "spatial_run": "", "spatial_state": "not-started",
            "interpolation_run": "", "interpolation_state": "not-started",
            "selected_run": "", "qa_state": "not-assessed", "qa_evidence": "",
            "installation_state": "not-installed", "installation_receipt": "",
            "release_state": "not-evaluated", "release_candidate": "", "notes": "",
        }
        (self.root / "effects/index/processing.csv").write_bytes(workflow.csv_bytes([processing]))

    def _plan(self, run_id: str = "spatial-test") -> spatial.SpatialPlan:
        return spatial.build_plan(
            self.root, self.resref, run_id, "seedvr-test", self.workflow_path,
            server="http://127.0.0.1:8188", pad=32, poll_seconds=2.0,
            timeout_seconds=900.0, upload_folder="BG2_Upscale/effect-runs",
        )

    def test_plan_is_non_writing_and_bound_to_one_effect_asset(self) -> None:
        plan = self._plan()
        payload = spatial.plan_payload(plan)
        self.assertEqual(payload["asset_id"], f"effects:bam:{self.resref}")
        self.assertEqual(payload["stages"], ["00-frames-x1", "01-spatial-x4"])
        self.assertFalse(plan.run_root.exists())
        self.assertFalse(workflow.reservation_path(plan.run_root.parent.parent, plan.run_id).exists())

    def test_reservation_is_created_only_by_the_execution_path(self) -> None:
        plan = self._plan("spatial-reserved")
        spatial.reserve_plan(plan)
        reservation = workflow.reservation_path(plan.run_root.parent.parent, plan.run_id)
        self.assertTrue(reservation.is_file())
        self.assertEqual(json.loads(reservation.read_text(encoding="utf-8"))["pipeline_id"], spatial.PIPELINE_ID)

    def test_descriptor_uses_generic_contract_and_relative_evidence(self) -> None:
        plan = self._plan()
        plan.run_root.mkdir(parents=True)
        recipe = {"schema": spatial.RECIPE_SCHEMA}
        spatial.write_json(plan.recipe_path, recipe)
        source = spatial.file_evidence(self.root, "source-bam", self.source)
        descriptor = spatial.build_descriptor(
            plan, recipe, source, status="running", sealed=False,
            created_at_utc="2026-09-07T12:00:00Z",
        )
        self.assertEqual(descriptor["$schema"], "docs/workspace-run.schema.json")
        self.assertEqual(descriptor["pipeline"]["id"], spatial.PIPELINE_ID)
        self.assertEqual(descriptor["inputs"], [source])
        self.assertFalse(descriptor["result"]["sealed"])
        self.assertFalse(descriptor["pipeline"]["recipe_path"].startswith("/"))

    def test_normalize_manifest_paths_only_rewrites_workspace_absolute_paths(self) -> None:
        manifest = self.root / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "workspace": (self.root / "effects/test").as_posix(),
                    "external": "http://127.0.0.1:8188",
                }
            ),
            encoding="utf-8",
        )
        normalized = spatial.normalize_manifest_paths(self.root, manifest)
        self.assertEqual(normalized["workspace"], "effects/test")
        self.assertEqual(normalized["external"], "http://127.0.0.1:8188")

    def test_spatial_manifest_contract_matches_the_existing_frame_upscaler(self) -> None:
        self.assertEqual(spatial.SPATIAL_SCHEMA, "bg2-upscale-animation-frames-v1")

    def test_spatial_lineage_hash_is_declared_under_source(self) -> None:
        run_root = self.root / "run"
        frame_root = run_root / "00-frames-x1"
        frame_root.mkdir(parents=True)
        frame_root.joinpath("manifest.json").write_text("{}\n", encoding="utf-8")
        stage = run_root / "01-spatial-x4"
        rgba = stage / "rgba/frame_000.png"
        raw = stage / "raw_rgba/frame_000.rgba"
        preview = stage / "preview/contact.png"
        for path, content in ((rgba, b"rgba"), (raw, b"raw"), (preview, b"preview")):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        spatial.write_json(
            stage / "manifest.json",
            {
                "schema": spatial.SPATIAL_SCHEMA,
                "status": "completed",
                "scale": 4,
                "source": {
                    "frame_manifest_sha256": workflow.sha256_file(frame_root / "manifest.json"),
                },
                "frames": [
                    {
                        "frame": 0,
                        "rgba_xn": "rgba/frame_000.png",
                        "rgba_xn_sha256": workflow.sha256_file(rgba),
                        "raw_rgba_xn": "raw_rgba/frame_000.rgba",
                        "raw_rgba_xn_sha256": workflow.sha256_file(raw),
                    }
                ],
                "preview": "preview/contact.png",
                "preview_sha256": workflow.sha256_file(preview),
            },
        )
        self.assertEqual(
            spatial.validate_spatial_stage(self.root, stage, {"frame_count": 1})["status"],
            "completed",
        )


if __name__ == "__main__":
    unittest.main()
