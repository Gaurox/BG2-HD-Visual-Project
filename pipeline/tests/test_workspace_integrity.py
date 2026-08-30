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

import audit_workspace_integrity as integrity  # noqa: E402


class WorkspaceIntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = integrity.build_outputs(ROOT)
        cls.report = cls.outputs["workspace-integrity.json"]
        cls.run_index = cls.outputs["runs.json"]
        cls.runs = cls.run_index["runs"]

    def test_projection_is_deterministic(self) -> None:
        second = integrity.build_outputs(ROOT)
        self.assertEqual(
            integrity.rendered_outputs(self.outputs),
            integrity.rendered_outputs(second),
        )

    def test_generated_outputs_are_current_and_have_no_errors(self) -> None:
        self.assertEqual(self.report["registry_asset_count"], 18353)
        self.assertEqual(self.report["summary"]["by_severity"]["error"], 0)
        self.assertEqual(integrity.check_outputs(self.outputs), [])

    def test_run_csv_matches_json_exactly(self) -> None:
        csv_bytes = integrity.rendered_outputs(self.outputs)[integrity.RUN_CSV]
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))
        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"), newline=""))
        rows = list(reader)
        self.assertEqual(reader.fieldnames, list(integrity.RUN_COLUMNS))
        self.assertEqual(len(rows), len(self.runs))
        self.assertEqual(len({row["run_key"] for row in rows}), len(rows))
        for row, record in zip(rows, self.runs, strict=True):
            self.assertEqual(row["run_key"], record["run_key"])
            self.assertEqual(row["asset_count"], str(record["asset_count"]))
            self.assertEqual(row["asset_ids"], " | ".join(record["asset_ids"]))
            self.assertEqual(row["selection_state"], record["selection_state"])

    def test_every_run_asset_link_targets_the_global_registry(self) -> None:
        registry = json.loads((ROOT / "asset-tracking/registry.json").read_text(encoding="utf-8"))
        asset_ids = {record["asset_id"] for record in registry["assets"]}
        for run in self.runs:
            for asset_id in run["asset_ids"]:
                self.assertIn(asset_id, asset_ids, run["run_key"])
        unattached = [run for run in self.runs if not run["asset_ids"]]
        self.assertEqual(
            [run["run_key"] for run in unattached],
            ["animations:am0900dm-seedvr7b-lab-x4"],
        )

    def test_map_sources_and_selected_runs_are_locatable(self) -> None:
        maps = self.report["domain_audits"]["maps"]
        self.assertEqual(maps["extracted_source_count"], 800)
        self.assertEqual(maps["physical_run_count"], 292)
        self.assertEqual(maps["selected_run_count"], 292)
        self.assertEqual(maps["descriptor_count"], 291)
        self.assertEqual(maps["legacy_descriptor_count"], 1)
        map_runs = [run for run in self.runs if run["domain"] == "maps"]
        self.assertTrue(all(run["selection_state"] == "selected" for run in map_runs))
        self.assertTrue(all(run["outputs_state"] != "missing" for run in map_runs))

    def test_extracted_source_authorities_have_no_missing_or_changed_files(self) -> None:
        for audit in self.report["source_audits"]:
            self.assertEqual(audit["missing_file_count"], 0, audit["authority"])
            self.assertEqual(audit["hash_mismatch_count"], 0, audit["authority"])
            self.assertEqual(
                audit["manifest_asset_count"],
                audit["registry_projection_count"],
                audit["authority"],
            )
        video = next(
            audit
            for audit in self.report["source_audits"]
            if audit["authority"] == "video/index/resources.csv"
        )
        self.assertEqual(video["extra_file_count"], 314)

    def test_portrait_occurrences_resolve_to_canonical_assets(self) -> None:
        portraits = self.report["domain_audits"]["portraits"]
        self.assertEqual(portraits["logical_asset_count"], 3321)
        self.assertEqual(portraits["physical_file_count"], 3333)
        for audit in portraits["authorities"]:
            self.assertEqual(audit["missing_file_count"], 0, audit["authority"])
            self.assertEqual(audit["hash_mismatch_count"], 0, audit["authority"])
            self.assertEqual(audit["extra_file_count"], 0, audit["authority"])

    def test_animation_qa_and_sprite_restore_chains_remain_resolved(self) -> None:
        animations = self.report["domain_audits"]["animations"]
        self.assertEqual(animations["qa_attested_run_count"], 19)
        self.assertEqual(animations["approved_candidate_count"], 5)
        self.assertEqual(animations["physical_run_count"], 112)
        self.assertEqual(animations["legacy_proto_directory_migration_count"], 64)
        self.assertEqual(animations["legacy_proto_loose_file_migration_count"], 7)
        self.assertEqual(animations["legacy_proto_migrated_file_count"], 3030)
        self.assertEqual(animations["legacy_proto_migrated_bytes"], 1320761527)
        self.assertGreater(animations["legacy_proto_embedded_reference_count"], 0)
        self.assertEqual(animations["legacy_proto_run_count"], 65)
        self.assertEqual(animations["remaining_animation_proto_directory_count"], 0)
        self.assertEqual(animations["remaining_proto_directory_count"], 4)
        sprites = self.report["domain_audits"]["sprites"]
        self.assertEqual(sprites["current_generation_count"], 1)
        self.assertEqual(sprites["historical_pointer_resolved_count"], 7)
        self.assertEqual(sprites["historical_pointer_unresolved_count"], 0)

    def test_animation_proto_paths_are_migrated_without_status_inference(self) -> None:
        migration_path = ROOT / "animations/index/path-migrations.json"
        migration = json.loads(migration_path.read_text(encoding="utf-8"))
        self.assertEqual(migration["schema"], "bg2-upscale-animation-path-migrations-v1")
        self.assertIn("never grants", migration["authority_policy"])
        self.assertEqual(len(migration["migrations"]), 64)
        self.assertEqual(len(migration["loose_file_migrations"]), 7)
        self.assertEqual(len(migration["deprecated_output_roots"]), 2)

        for item in migration["migrations"]:
            self.assertFalse((ROOT / item["from"]).exists(), item["from"])
            self.assertTrue((ROOT / item["to"]).is_dir(), item["to"])
        for item in migration["loose_file_migrations"]:
            self.assertFalse((ROOT / item["from"]).exists(), item["from"])
            self.assertTrue((ROOT / item["to"]).is_file(), item["to"])

        retained = set(migration["retained_proto_directories"])
        present = {path.name for path in (ROOT / "proto").iterdir() if path.is_dir()}
        self.assertEqual(present, retained)
        self.assertEqual([path for path in (ROOT / "proto").iterdir() if path.is_file()], [])

        migrated_runs = [run for run in self.runs if run["domain"] == "animations" and run["legacy"]]
        self.assertEqual(len(migrated_runs), 65)
        canonical_prototypes = [
            run for run in migrated_runs if run["selection_state"] == "canonical-prototype"
        ]
        self.assertEqual(len(canonical_prototypes), 17)
        self.assertTrue(
            all(
                run["selection_authority"].endswith("animation_alpha_corrections.csv")
                for run in canonical_prototypes
            )
        )

    def test_new_run_contract_keeps_selection_external(self) -> None:
        schema = json.loads((ROOT / "docs/workspace-run.schema.json").read_text(encoding="utf-8"))
        required = set(schema["required"])
        self.assertTrue(
            {
                "run_id",
                "domain",
                "asset_ids",
                "pipeline",
                "inputs",
                "outputs",
                "provenance",
                "result",
            }.issubset(required)
        )
        self.assertNotIn("selection", schema["properties"])
        self.assertNotIn("selected", schema["properties"])
        self.assertTrue(schema["properties"]["asset_ids"]["uniqueItems"])
        self.assertEqual(
            set(schema["$defs"]["fileEvidence"]["required"]),
            {"role", "path", "sha256", "bytes"},
        )

    def test_outputs_can_be_deleted_and_recreated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            integrity.write_outputs(self.outputs, output_dir)
            self.assertEqual(integrity.check_outputs(self.outputs, output_dir), [])


if __name__ == "__main__":
    unittest.main()
