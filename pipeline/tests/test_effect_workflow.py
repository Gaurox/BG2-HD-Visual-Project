from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import effect_workflow as workflow  # noqa: E402


def sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()


class EffectWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.resref = "TESTFX"
        self.asset_id = f"effects:bam:{self.resref}"
        self.source = self.root / f"effects/ressources/{self.resref}/source.bam"
        self.source.parent.mkdir(parents=True)
        self.source.write_bytes(b"stock-effect-bam")
        self.recipe = self.root / "recipes/effect.json"
        self.recipe.parent.mkdir(parents=True)
        self.recipe.write_text('{"recipe":"test"}\n', encoding="utf-8")
        self._write_authorities()

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _write_authorities(self) -> None:
        inventory_path = self.root / "effects/index/bam-assets.csv"
        inventory_path.parent.mkdir(parents=True, exist_ok=True)
        fields = (
            "asset_key", "resref", "source_state", "source_sha256", "source_size",
            "extracted_path",
        )
        stream = io.StringIO(newline="")
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\r\n")
        writer.writeheader()
        writer.writerow(
            {
                "asset_key": self.asset_id,
                "resref": self.resref,
                "source_state": "available",
                "source_sha256": workflow.sha256_file(self.source),
                "source_size": self.source.stat().st_size,
                "extracted_path": f"effects/ressources/{self.resref}/source.bam",
            }
        )
        inventory_path.write_text(stream.getvalue(), encoding="utf-8")
        processing = {
            "asset_key": self.asset_id,
            "asset_directory": f"effects/ressources/{self.resref}",
            "spatial_run": "",
            "spatial_state": "not-started",
            "interpolation_run": "",
            "interpolation_state": "not-started",
            "selected_run": "",
            "qa_state": "not-assessed",
            "qa_evidence": "",
            "installation_state": "not-installed",
            "installation_receipt": "",
            "release_state": "not-evaluated",
            "release_candidate": "",
            "notes": "",
        }
        (self.root / "effects/index/processing.csv").write_bytes(workflow.csv_bytes([processing]))

    def _evidence(self, role: str, path: Path) -> dict[str, object]:
        return {
            "role": role,
            "path": path.relative_to(self.root).as_posix(),
            "sha256": workflow.sha256_file(path),
            "bytes": path.stat().st_size,
        }

    def _write_run(
        self,
        run_id: str,
        stage: str,
        *,
        parent_output: Path | None = None,
        sealed: bool = True,
    ) -> Path:
        run_root = self.root / f"effects/ressources/{self.resref}/runs/{run_id}"
        output = run_root / "output/manifest.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps({"run": run_id}) + "\n", encoding="utf-8")
        inputs = [self._evidence("source-bam", self.source)] if stage == "spatial" else [
            self._evidence("parent-spatial-output", parent_output)  # type: ignore[arg-type]
        ]
        descriptor = {
            "$schema": "docs/workspace-run.schema.json",
            "schema_version": 1,
            "run_id": run_id,
            "domain": "effects",
            "asset_ids": [self.asset_id],
            "pipeline": {
                "id": workflow.STAGES[stage],
                "recipe_path": self.recipe.relative_to(self.root).as_posix(),
                "recipe_sha256": workflow.sha256_file(self.recipe),
            },
            "inputs": inputs,
            "outputs": [self._evidence("runtime-manifest", output)],
            "provenance": {
                "created_at_utc": "2026-09-07T12:00:00Z",
                "generator": "pipeline/tests/test_effect_workflow.py",
                **({"parents": ["spatial-a"]} if stage == "interpolation" else {}),
            },
            "result": {
                "status": "completed",
                "sealed": sealed,
                "completed_at_utc": "2026-09-07T12:01:00Z",
            },
        }
        descriptor_path = run_root / "run.json"
        descriptor_path.write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
        return output

    def _processing_row(self) -> dict[str, str]:
        return workflow.read_csv(
            self.root / "effects/index/processing.csv", workflow.PROCESSING_FIELDS
        )[0]

    def test_new_run_is_plan_only_until_explicitly_reserved(self) -> None:
        plan = workflow.new_run(
            self.root, self.resref, "spatial", "seedvr", "spatial-a", write=False
        )
        self.assertEqual(plan["pipeline_id"], "effects.spatial-x4.v1")
        self.assertFalse((self.root / plan["reservation"]).exists())

        reserved = workflow.new_run(
            self.root, self.resref, "spatial", "seedvr", "spatial-b", write=True
        )
        reservation = self.root / reserved["reservation"]
        self.assertTrue(reservation.is_file())
        payload = json.loads(reservation.read_text(encoding="utf-8"))
        self.assertEqual(payload["asset_id"], self.asset_id)
        self.assertEqual(payload["stage"], "spatial")

    def test_registers_spatial_then_derived_interpolation_without_selecting_it(self) -> None:
        spatial_output = self._write_run("spatial-a", "spatial")
        before = (self.root / "effects/index/processing.csv").read_bytes()
        planned = workflow.register_run(
            self.root, self.resref, "spatial", "spatial-a", write=False
        )
        self.assertEqual(planned["production_state"], "produced")
        self.assertEqual((self.root / "effects/index/processing.csv").read_bytes(), before)

        workflow.register_run(self.root, self.resref, "spatial", "spatial-a", write=True)
        spatial_row = self._processing_row()
        self.assertEqual(spatial_row["spatial_run"], "spatial-a")
        self.assertEqual(spatial_row["spatial_state"], "produced")
        self.assertEqual(spatial_row["selected_run"], "")

        self._write_run("temporal-a", "interpolation", parent_output=spatial_output)
        workflow.register_run(self.root, self.resref, "interpolation", "temporal-a", write=True)
        final = self._processing_row()
        self.assertEqual(final["interpolation_run"], "temporal-a")
        self.assertEqual(final["interpolation_state"], "produced")
        self.assertEqual(final["selected_run"], "")
        self.assertTrue(workflow.check_workspace(self.root, self.resref)["ok"])

    def test_rejects_unsealed_or_unbound_runs(self) -> None:
        self._write_run("spatial-a", "spatial", sealed=False)
        with self.assertRaisesRegex(workflow.WorkflowError, "completed et scellé"):
            workflow.register_run(self.root, self.resref, "spatial", "spatial-a", write=True)

        spatial_output = self._write_run("spatial-b", "spatial")
        workflow.register_run(self.root, self.resref, "spatial", "spatial-b", write=True)
        self._write_run("temporal-a", "interpolation", parent_output=spatial_output)
        descriptor = self.root / f"effects/ressources/{self.resref}/runs/temporal-a/run.json"
        payload = json.loads(descriptor.read_text(encoding="utf-8"))
        payload["inputs"][0]["sha256"] = sha256(b"different")
        descriptor.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(workflow.WorkflowError, "hash différent"):
            workflow.register_run(self.root, self.resref, "interpolation", "temporal-a", write=True)


if __name__ == "__main__":
    unittest.main()
