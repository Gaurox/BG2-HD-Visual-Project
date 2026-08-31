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
        self.assertEqual([run["run_key"] for run in unattached], [])

    def test_map_sources_and_selected_runs_are_locatable(self) -> None:
        maps = self.report["domain_audits"]["maps"]
        self.assertEqual(maps["extracted_source_count"], 800)
        self.assertEqual(maps["physical_run_count"], 293)
        self.assertEqual(maps["selected_run_count"], 292)
        self.assertEqual(maps["descriptor_count"], 291)
        self.assertEqual(maps["legacy_descriptor_count"], 2)
        map_runs = [run for run in self.runs if run["domain"] == "maps"]
        self.assertEqual(
            [run["run_key"] for run in map_runs if run["selection_state"] != "selected"],
            ["maps:AR0410:legacy-upscale-tests-20260818"],
        )
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
        self.assertEqual(video["extra_file_count"], 0)

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
        self.assertEqual(animations["physical_run_count"], 111)
        self.assertEqual(animations["legacy_proto_directory_migration_count"], 64)
        self.assertEqual(animations["legacy_proto_loose_file_migration_count"], 7)
        self.assertEqual(animations["legacy_proto_migrated_file_count"], 3030)
        self.assertEqual(animations["legacy_proto_migrated_bytes"], 1320761527)
        self.assertGreater(animations["legacy_proto_embedded_reference_count"], 0)
        self.assertEqual(animations["legacy_proto_run_count"], 65)
        self.assertEqual(animations["remaining_animation_proto_directory_count"], 0)
        self.assertEqual(animations["remaining_proto_directory_count"], 1)
        self.assertEqual(animations["historical_qa_evidence_adapted_count"], 9)
        self.assertEqual(animations["release_pack_indexed_count"], 5)
        release_packs = [
            run
            for run in self.runs
            if run["run_kind"] == "area-animation-release-pack"
        ]
        self.assertEqual(len(release_packs), 5)
        self.assertTrue(
            all(run["selection_state"] == "release-candidate" for run in release_packs)
        )
        self.assertTrue(all(run["provenance_state"] == "verified" for run in release_packs))
        sprites = self.report["domain_audits"]["sprites"]
        self.assertEqual(sprites["current_generation_count"], 1)
        self.assertEqual(sprites["historical_pointer_resolved_count"], 7)
        self.assertEqual(sprites["historical_pointer_unresolved_count"], 0)

    def test_controlled_cleanup_and_portability_are_verified(self) -> None:
        cleanup = self.report["domain_audits"]["workspace_cleanup"]
        self.assertEqual(cleanup["operation_count"], 7)
        self.assertEqual(cleanup["verified_operation_count"], 7)
        self.assertEqual(cleanup["preserved_file_count"], 445)
        self.assertEqual(cleanup["preserved_bytes"], 857233386)
        self.assertEqual(cleanup["removed_empty_directory_count"], 1)
        archive_p2 = self.report["domain_audits"]["workspace_archive_p2"]
        self.assertEqual(archive_p2["operation_count"], 15)
        self.assertEqual(archive_p2["verified_operation_count"], 15)
        self.assertEqual(archive_p2["archived_file_count"], 1771)
        self.assertEqual(archive_p2["archived_bytes"], 256200953)
        self.assertEqual(archive_p2["exact_duplicate_group_count"], 1)
        self.assertEqual(archive_p2["verified_exact_duplicate_group_count"], 1)
        self.assertEqual(archive_p2["exact_duplicate_removed_file_count"], 39)
        self.assertEqual(archive_p2["exact_duplicate_removed_bytes"], 1404117)
        archive_p3 = self.report["domain_audits"]["animation_pack_archive_p3"]
        self.assertTrue(archive_p3["verified"])
        self.assertEqual(archive_p3["pack_count"], 71)
        self.assertEqual(archive_p3["keep_active_count"], 6)
        self.assertEqual(archive_p3["archive_count"], 18)
        self.assertEqual(archive_p3["delete_safe_count"], 47)
        self.assertEqual(archive_p3["uncertain_count"], 0)
        self.assertEqual(archive_p3["original_file_count"], 152594)
        self.assertEqual(archive_p3["original_bytes"], 113882412618)
        self.assertEqual(archive_p3["reclaimed_bytes"], 85753026372)
        archive_manifest = json.loads(
            (ROOT / integrity.ARCHIVE_P2_MANIFEST).read_text(encoding="utf-8")
        )
        self.assertIn(
            {
                "historical_reference": "proto/goblin-mgo1-xbr2x-x2-ingame",
                "resolved_by": "docs/workspace-archive-p2-manifest.json",
                "target": "archive/legacy/workspace-p2-20260831/sprites/goblin-mgo1-xbr2x-x2-ingame",
            },
            archive_manifest["path_adapters"],
        )
        self.assertEqual(self.report["summary"]["candidate_cleanup"]["temporary_files"], 0)
        self.assertEqual(
            self.report["summary"]["candidate_cleanup"]["video_unindexed_work_products"],
            0,
        )

        portability = self.report["domain_audits"]["path_portability"]
        self.assertEqual(portability["configured_path_count"], 5)
        self.assertEqual(portability["missing_path_count"], 0)
        self.assertEqual(portability["active_absolute_path_violation_count"], 0)
        self.assertEqual(portability["historical_script_exception_count"], 0)
        self.assertEqual(portability["new_historical_absolute_path_file_count"], 0)
        self.assertEqual(portability["historical_descriptor_file_count"], 146)
        self.assertGreater(portability["active_script_file_count"], 0)
        self.assertTrue(
            integrity.WINDOWS_ABSOLUTE_PATH_LITERAL.search(
                r"C:\Users\Example\workspace\script.py"
            )
        )
        self.assertTrue(
            integrity.WINDOWS_ABSOLUTE_PATH_LITERAL.search(
                r'"G:\\AI\\BG2_Upscale\\sprite"'
            )
        )
        hygiene = self.report["domain_audits"]["workspace_hygiene"]
        self.assertEqual(hygiene["obsolete_p1_target_count"], 0)
        self.assertEqual(self.run_index["run_count"], 556)

    def test_animation_proto_paths_are_migrated_without_status_inference(self) -> None:
        migration_path = ROOT / "animations/index/path-migrations.json"
        migration = json.loads(migration_path.read_text(encoding="utf-8"))
        self.assertEqual(migration["schema"], "bg2-upscale-animation-path-migrations-v1")
        self.assertIn("never grants", migration["authority_policy"])
        self.assertEqual(len(migration["migrations"]), 64)
        self.assertEqual(len(migration["loose_file_migrations"]), 7)
        self.assertEqual(len(migration["deprecated_output_roots"]), 2)
        self.assertEqual(len(migration["pack_migrations"]), 6)

        for item in migration["migrations"]:
            self.assertFalse((ROOT / item["from"]).exists(), item["from"])
            self.assertTrue((ROOT / item["to"]).is_dir(), item["to"])
        for item in migration["loose_file_migrations"]:
            self.assertFalse((ROOT / item["from"]).exists(), item["from"])
            self.assertTrue((ROOT / item["to"]).is_file(), item["to"])
        for item in migration["pack_migrations"]:
            self.assertFalse((ROOT / item["from"]).exists(), item["from"])
            target = ROOT / item["to"]
            if item["resolution"] == "descriptor-only":
                self.assertTrue(target.is_file(), item["to"])
            else:
                self.assertTrue(target.is_dir(), item["to"])

        retained = set(migration["retained_proto_directories"])
        present = {path.name for path in (ROOT / "proto").iterdir() if path.is_dir()}
        self.assertEqual(present, retained)
        self.assertEqual(retained, {"install-backups"})
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
