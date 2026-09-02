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
        registry = json.loads(
            (ROOT / "asset-tracking/registry.json").read_text(encoding="utf-8")
        )
        self.assertEqual(self.report["registry_asset_count"], registry["asset_count"])
        self.assertEqual(registry["asset_count"], len(registry["assets"]))
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
        map_runs = [run for run in self.runs if run["domain"] == "maps"]
        self.assertGreater(maps["extracted_source_count"], 0)
        self.assertEqual(maps["physical_run_count"], len(map_runs))
        self.assertEqual(
            maps["physical_run_count"],
            maps["descriptor_count"] + maps["legacy_descriptor_count"],
        )
        self.assertEqual(
            maps["selected_run_count"],
            sum(run["selection_state"] == "selected" for run in map_runs),
        )
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
        authorities = portraits["authorities"]
        asset_authority = next(
            audit for audit in authorities if audit["role"] == "asset-authority"
        )
        self.assertGreater(portraits["logical_asset_count"], 0)
        self.assertEqual(
            portraits["logical_asset_count"], asset_authority["asset_count"]
        )
        self.assertEqual(
            portraits["physical_file_count"], asset_authority["physical_file_count"]
        )
        self.assertEqual(
            portraits["source_resource_count"], asset_authority["occurrence_count"]
        )
        self.assertEqual(
            portraits["usage_view_physical_file_count"],
            sum(
                audit["physical_file_count"]
                for audit in authorities
                if audit["role"] == "usage-view"
            ),
        )
        self.assertEqual(
            portraits["external_reference_physical_file_count"],
            sum(
                audit["physical_file_count"]
                for audit in authorities
                if audit["role"] == "external-reference"
            ),
        )
        for audit in authorities:
            self.assertEqual(audit["missing_file_count"], 0, audit["authority"])
            self.assertEqual(audit["hash_mismatch_count"], 0, audit["authority"])
            self.assertEqual(audit["extra_file_count"], 0, audit["authority"])

    def test_animation_run_discovery_supports_all_layouts_without_id_collision(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected = {
                "animations/runs/shared-id": ("legacy", ""),
                "animations/ressources/AM0001A/runs/shared-id": (
                    "mono-asset",
                    "AM0001A",
                ),
                "animations/batches/shared-id": ("batch", ""),
            }
            for relative in expected:
                (root / relative).mkdir(parents=True)

            locations = integrity.animation_run_locations(root)
            actual = {
                location["path"].relative_to(root).as_posix(): (
                    location["layout"],
                    location["owner_resref"],
                )
                for location in locations
            }
            self.assertEqual(actual, expected)
            self.assertEqual(
                len({integrity.animation_run_key(location) for location in locations}),
                len(locations),
            )

    def test_animation_release_references_support_legacy_and_structured_layouts(self) -> None:
        candidates = [
            {
                "area": "AR0001",
                "source_run": (
                    "animations/runs/legacy-id + "
                    "animations/batches/batch-id + "
                    "animations/ressources/AM0001A/runs/mono-id"
                ),
            },
            {
                "area": "AR0002",
                "source_runs": [
                    {
                        "path": "animations/ressources/AM0001A/runs/mono-id",
                        "asset_ids": ["AM0001A"],
                    }
                ],
            },
        ]
        references = integrity.referenced_animation_runs(candidates)
        self.assertEqual(
            references,
            {
                "animations/runs/legacy-id": ["AR0001"],
                "animations/batches/batch-id": ["AR0001"],
                "animations/ressources/am0001a/runs/mono-id": ["AR0001", "AR0002"],
            },
        )
        self.assertEqual(
            integrity.referenced_animation_run_assets(candidates),
            {
                "animations/ressources/am0001a/runs/mono-id": [
                    "animations:bam:AM0001A"
                ]
            },
        )

    def test_animation_ingame_selection_must_match_manifest_and_mono_owner(self) -> None:
        template = {
            "decision": "animations/index/qa-decisions/AM0001A/accepted.json",
            "selection": "animations/index/selections/AM0001A.json",
        }
        cases = (
            (
                {
                    **template,
                    "asset_id": "animations:bam:AM0001A",
                    "resref": "AM0001A",
                },
                {"AM0001B"},
            ),
            (
                {
                    **template,
                    "asset_id": "animations:bam:AM0001B",
                    "resref": "AM0001B",
                },
                {"AM0001B"},
            ),
        )
        for record, manifest_resrefs in cases:
            with self.subTest(resref=record["resref"], manifest=manifest_resrefs):
                issues = []
                accepted = integrity.validate_animation_run_selections(
                    issues,
                    [record],
                    manifest_resrefs,
                    owner_resref="AM0001A",
                    run_path="animations/ressources/AM0001A/runs/final-v1",
                    run_id="final-v1",
                )
                self.assertEqual(accepted, [])
                self.assertEqual(
                    [issue["code"] for issue in issues],
                    ["animation-selection-run-resref-mismatch"],
                )

    def test_animation_qa_and_sprite_restore_chains_remain_resolved(self) -> None:
        animations = self.report["domain_audits"]["animations"]
        run_locations = integrity.animation_run_locations(ROOT)
        qa_directories = [
            location
            for location in run_locations
            if (location["path"] / "qa-approval.json").is_file()
        ]
        candidates = json.loads(
            (ROOT / "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json").read_text(
                encoding="utf-8"
            )
        )["candidates"]
        self.assertEqual(animations["run_preview_record_count"], len(qa_directories))
        selection_root = ROOT / "animations/index/selections"
        selection_files = (
            list(selection_root.glob("*.json")) if selection_root.is_dir() else []
        )
        self.assertEqual(
            animations["ingame_qa_selected_asset_count"], len(selection_files)
        )
        self.assertEqual(animations["approved_candidate_count"], len(candidates))
        self.assertEqual(animations["physical_run_count"], len(run_locations))
        self.assertEqual(
            animations["physical_run_count_by_layout"],
            dict(
                sorted(
                    {
                        layout: sum(
                            location["layout"] == layout for location in run_locations
                        )
                        for layout in {location["layout"] for location in run_locations}
                    }.items()
                )
            ),
        )
        runs_by_path = {
            run["path"]: run
            for run in self.runs
            if run["domain"] == "animations"
            and run["run_kind"] != "area-animation-release-pack"
        }
        for location in qa_directories:
            run = runs_by_path[location["path"].relative_to(ROOT).as_posix()]
            if run["selection_state"] != "selected":
                self.assertTrue(run["qa_state"].startswith("preview-"), run["run_key"])
            self.assertNotEqual(run["selection_state"], "qa-approved", run["run_key"])
            self.assertIn("aucune preuve de QA ingame", run["notes"], run["run_key"])
        self.assertEqual(animations["legacy_proto_directory_migration_count"], 64)
        self.assertEqual(animations["legacy_proto_loose_file_migration_count"], 7)
        self.assertEqual(animations["legacy_proto_migrated_file_count"], 3030)
        self.assertEqual(animations["legacy_proto_migrated_bytes"], 1320761527)
        self.assertGreater(animations["legacy_proto_embedded_reference_count"], 0)
        self.assertEqual(animations["legacy_proto_run_count"], 65)
        self.assertEqual(animations["remaining_animation_proto_directory_count"], 0)
        self.assertEqual(animations["remaining_proto_directory_count"], 0)
        adapted_evidence = animations["historical_qa_evidence_adapted_count"]
        adapted_issues = [
            issue
            for issue in self.report["issues"]
            if issue["code"] == "animation-historical-qa-evidence-adapted"
        ]
        self.assertEqual(len(adapted_issues), int(adapted_evidence > 0))
        if adapted_issues:
            self.assertEqual(
                adapted_issues[0]["details"]["evidence_reference_count"],
                adapted_evidence,
            )
            self.assertEqual(
                len(adapted_issues[0]["details"]["migrations"]), adapted_evidence
            )
        self.assertEqual(animations["release_pack_indexed_count"], len(candidates))
        release_packs = [
            run
            for run in self.runs
            if run["run_kind"] == "area-animation-release-pack"
        ]
        self.assertEqual(len(release_packs), len(candidates))
        self.assertTrue(
            all(run["selection_state"] == "release-candidate" for run in release_packs)
        )
        self.assertTrue(all(run["provenance_state"] == "verified" for run in release_packs))
        sprites = self.report["domain_audits"]["sprites"]
        sprite_runs = [run for run in self.runs if run["domain"] == "sprites"]
        self.assertEqual(
            sprites["current_generation_count"],
            sum(run["selection_state"] == "current-generation" for run in sprite_runs),
        )
        self.assertEqual(
            sprites["historical_pointer_resolved_count"]
            + sprites["historical_pointer_unresolved_count"],
            sprites["historical_active_test_count"],
        )
        self.assertEqual(sprites["historical_pointer_unresolved_count"], 0)

    def test_controlled_cleanup_and_portability_are_verified(self) -> None:
        cleanup = self.report["domain_audits"]["workspace_cleanup"]
        self.assertEqual(cleanup["operation_count"], 7)
        self.assertEqual(cleanup["verified_operation_count"], 7)
        self.assertEqual(cleanup["restored_after_cleanup_count"], 1)
        self.assertEqual(cleanup["preserved_file_count"], 445)
        self.assertEqual(cleanup["preserved_bytes"], 857233386)
        self.assertEqual(cleanup["removed_empty_directory_count"], 0)
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
        legacy_p4 = self.report["domain_audits"]["workspace_legacy_p4"]
        self.assertTrue(legacy_p4["verified"])
        self.assertEqual(legacy_p4["keep_active_count"], 11)
        self.assertEqual(legacy_p4["keep_compat_count"], 16)
        self.assertEqual(legacy_p4["archive_count"], 8)
        self.assertEqual(legacy_p4["verified_archive_count"], 8)
        self.assertEqual(legacy_p4["delete_safe_count"], 0)
        self.assertEqual(legacy_p4["archived_bytes"], 37249)
        self.assertEqual(legacy_p4["verified_archived_bytes"], 37249)
        backups_p5 = self.report["domain_audits"]["workspace_backups_p5"]
        self.assertTrue(backups_p5["verified"])
        self.assertEqual(backups_p5["keep_restore_count"], 8)
        self.assertEqual(backups_p5["keep_historical_count"], 9)
        self.assertEqual(backups_p5["archive_count"], 3)
        self.assertEqual(backups_p5["verified_archive_count"], 3)
        self.assertEqual(backups_p5["archived_file_count"], 27)
        self.assertEqual(backups_p5["archived_bytes"], 36243135)
        self.assertEqual(backups_p5["delete_safe_count"], 9)
        self.assertEqual(backups_p5["verified_delete_safe_count"], 9)
        self.assertEqual(backups_p5["deleted_duplicate_file_count"], 37)
        self.assertEqual(backups_p5["reclaimed_bytes"], 161259074)
        self.assertEqual(backups_p5["removed_empty_directory_count"], 7)
        self.assertEqual(backups_p5["uncertain_count"], 0)
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
        self.assertEqual(
            portability["configured_path_count"]
            + portability["missing_path_count"]
            + portability["unconfigured_path_count"],
            len(portability["path_states"]),
        )
        self.assertEqual(portability["missing_path_count"], 0)
        self.assertEqual(portability["unconfigured_path_count"], 0)
        self.assertEqual(portability["active_absolute_path_violation_count"], 0)
        self.assertEqual(portability["historical_script_exception_count"], 0)
        self.assertEqual(portability["new_historical_absolute_path_file_count"], 0)
        historical_path_issues = [
            issue
            for issue in self.report["issues"]
            if issue["code"] == "historical-absolute-paths-adapted"
        ]
        self.assertEqual(len(historical_path_issues), 1)
        self.assertEqual(
            historical_path_issues[0]["details"]["descriptor_file_count"],
            portability["historical_descriptor_file_count"],
        )
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
        self.assertEqual(self.run_index["run_count"], len(self.runs))
        self.assertEqual(
            self.run_index["run_count"],
            sum(self.run_index["summary"]["by_domain"].values()),
        )

    def test_animation_proto_paths_are_migrated_without_status_inference(self) -> None:
        migration_path = ROOT / "animations/index/path-migrations.json"
        migration = json.loads(migration_path.read_text(encoding="utf-8"))
        self.assertEqual(migration["schema"], "bg2-upscale-animation-path-migrations-v1")
        self.assertIn("never grants", migration["authority_policy"])
        self.assertEqual(len(migration["migrations"]), 64)
        self.assertEqual(len(migration["loose_file_migrations"]), 7)
        self.assertEqual(
            {item["from"] for item in migration["deprecated_output_roots"]},
            {
                "proto/AM0602C-eau-canvas-feather-x4",
                "proto/AM0602D-eau-canvas-feather-x4",
                "proto/AM0602E-eau-canvas-feather-x4",
                "proto/AM0602G-eau-canvas-feather-x4",
                "proto/FLAME2S-flamme-luminance-fade-x4",
                "proto/FLAME2S-flamme-radial-fade-x4",
                "proto/ar0602-portals-spline-fit1",
                "proto/ar0603-portal-spline-fit1",
            },
        )
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
        proto_root = ROOT / "proto"
        present = (
            {path.name for path in proto_root.iterdir() if path.is_dir()}
            if proto_root.is_dir()
            else set()
        )
        self.assertEqual(present, retained)
        self.assertEqual(retained, set())

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
