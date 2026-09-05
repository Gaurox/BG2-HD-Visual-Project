from __future__ import annotations

import csv
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import asset_tracking_contract as contract  # noqa: E402
import build_global_asset_registry as registry  # noqa: E402


def write_json(path: Path, value: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


class GlobalAssetRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.outputs = registry.build_outputs(ROOT)
        cls.repeated_outputs = registry.build_outputs(ROOT)
        cls.records = cls.outputs["registry"]["assets"]
        cls.by_id = {record["asset_id"]: record for record in cls.records}

    def test_two_generations_are_byte_identical(self) -> None:
        self.assertEqual(
            registry.rendered_outputs(self.outputs),
            registry.rendered_outputs(self.repeated_outputs),
        )

    def test_checked_in_outputs_are_current(self) -> None:
        self.assertEqual(registry.check_outputs(self.outputs), [])

    def test_registry_csv_matches_json_exactly(self) -> None:
        rendered = registry.rendered_outputs(self.outputs)
        csv_bytes = rendered[registry.REGISTRY_CSV_NAME]
        self.assertTrue(csv_bytes.startswith(b"\xef\xbb\xbf"))
        reader = csv.DictReader(io.StringIO(csv_bytes.decode("utf-8-sig"), newline=""))
        rows = list(reader)

        self.assertEqual(reader.fieldnames, list(registry.REGISTRY_CSV_COLUMNS))
        self.assertEqual(len(rows), len(self.records))
        self.assertEqual(
            [row["asset_id"] for row in rows],
            [record["asset_id"] for record in self.records],
        )
        self.assertEqual(len({row["asset_id"] for row in rows}), len(rows))

        for row, record in zip(rows, self.records, strict=True):
            states = record["states"]
            self.assertEqual(row["domain"], record["domain"])
            self.assertEqual(row["asset_type"], record["asset_type"])
            for axis in ("source", "production", "qa", "installation", "release"):
                self.assertEqual(row[f"{axis}_state"], states[axis])
            self.assertEqual(row["provenance_state"], record["provenance"]["state"])
            self.assertEqual(
                row["selection"],
                " | ".join(
                    sorted(
                        (
                            f"{selection['role']}:{selection['id']}"
                            for selection in record.get("selections", [])
                        ),
                        key=str.casefold,
                    )
                ),
            )
            self.assertEqual(
                row["canonical_source_path"], record["canonical_source"]["path"]
            )
            self.assertEqual(
                row["canonical_source_locator"],
                record["canonical_source"]["locator"],
            )
            self.assertEqual(
                row["evidence_count"],
                str(len(record["provenance"].get("evidence", []))),
            )
            self.assertEqual(row["adapter"], record["adapter"])
            self.assertEqual(row["observed_at_utc"], record["observed_at_utc"])

    def test_all_records_conform_to_phase_2_contract(self) -> None:
        self.assertEqual(len(self.records), len(self.by_id))
        self.assertEqual(self.outputs["registry"]["asset_count"], len(self.records))
        for record in self.records:
            self.assertEqual(contract.validate_record(record), [], record["asset_id"])

    def test_reports_are_linked_to_the_exact_registry(self) -> None:
        expected_hash = hashlib.sha256(
            registry.json_bytes(self.records)
        ).hexdigest().upper()
        self.assertEqual(
            self.outputs["registry"]["asset_records_sha256"], expected_hash
        )
        for report_name in ("coverage", "anomalies"):
            report = self.outputs[report_name]
            self.assertEqual(report["asset_records_sha256"], expected_hash)
            self.assertEqual(
                report["source_fingerprint_sha256"],
                self.outputs["registry"]["source_fingerprint_sha256"],
            )

    def test_every_declared_input_hash_matches_the_source(self) -> None:
        for item in self.outputs["registry"]["inputs"]:
            path = ROOT / item["path"]
            self.assertTrue(path.is_file(), item["path"])
            self.assertEqual(registry.sha256_file(path), item["sha256"], item["path"])

    def test_expected_domains_are_projected_without_errors(self) -> None:
        coverage = self.outputs["coverage"]
        domain_counts = {
            item["domain"]: item["asset_count"] for item in coverage["domains"]
        }
        self.assertEqual(
            set(domain_counts),
            {
                "maps",
                "animations",
                "sprites",
                "ui",
                "portraits",
                "videos",
                "icons",
                "cursors",
                "effects",
                "projectiles",
            },
        )
        self.assertTrue(all(count > 0 for count in domain_counts.values()))
        self.assertEqual(sum(domain_counts.values()), coverage["metrics"]["known_assets"])
        self.assertEqual(
            self.outputs["anomalies"]["summary"]["by_severity"]["error"], 0
        )

    def test_representative_domain_mappings_remain_conservative(self) -> None:
        ar0404 = self.by_id["maps:AR0404:day"]
        self.assertEqual(
            ar0404["states"],
            {
                "source": "extracted",
                "production": "produced",
                "qa": "pending",
                "installation": "installed",
                "release": "not-evaluated",
            },
        )
        self.assertEqual(
            self.by_id["maps:AR0300:day"]["states"]["release"], "integrated"
        )
        self.assertEqual(
            self.by_id["maps:AR0516:day"]["states"]["release"], "integrated"
        )
        am0033ab = self.by_id["animations:bam:AM0033AB"]
        self.assertEqual(am0033ab["states"]["qa"], "not-assessed")
        self.assertFalse(
            any(
                item["path"].startswith("animations/runs/")
                and item["path"].endswith("/qa-approval.json")
                for item in am0033ab["provenance"]["evidence"]
            )
        )
        legacy_release = self.by_id["animations:bam:AM0602AA"]
        self.assertEqual(legacy_release["states"]["qa"], "passed")
        self.assertTrue(
            any(
                item["path"]
                == "releases/BG2-HD-Upscale/manifests/animation-release-candidates.json"
                for item in legacy_release["provenance"]["evidence"]
            )
        )
        self.assertEqual(
            self.by_id["animations:pack:AR0602"]["states"]["release"],
            "integrated",
        )
        sprite = self.by_id["sprites:family:0x6102:body:armor-code:1:CDMB1"]
        self.assertEqual(sprite["states"]["production"], "verified")
        self.assertEqual(sprite["states"]["qa"], "pending")
        self.assertEqual(sprite["states"]["installation"], "installed")
        self.assertEqual(
            self.by_id["ui:component:main-menu-x4"]["states"]["release"],
            "integrated",
        )
        portrait = self.by_id["portraits:AJANTIS"]
        self.assertEqual(portrait["states"]["source"], "verified")
        self.assertEqual(portrait["states"]["production"], "not-applicable")
        self.assertEqual(portrait["states"]["qa"], "not-applicable")
        self.assertEqual(portrait["states"]["release"], "not-applicable")
        self.assertEqual(portrait["provenance"]["state"], "verified")
        self.assertEqual(
            self.by_id["animations:wbm:oh4200md"]["states"]["production"],
            "not-started",
        )
        flythr03 = self.by_id["videos:movie-default-flythr03"]
        self.assertEqual(
            flythr03["states"],
            {
                "source": "verified",
                "production": "verified",
                "qa": "passed",
                "installation": "not-installed",
                "release": "not-evaluated",
            },
        )
        self.assertEqual(flythr03["provenance"]["state"], "complete")
        self.assertEqual(
            [selection["id"] for selection in flythr03["selections"]],
            [
                "flythr03-upscale-seedvr2-lab-prototype-v1",
                "flythr03-lab-interpolation-apollo8-30fps-v1",
            ],
        )
        self.assertIn(
            "video/index/processing.csv",
            {item["path"] for item in self.outputs["registry"]["inputs"]},
        )
        self.assertEqual(
            self.by_id["cursors:cursor-set-cursors"]["states"]["source"],
            "verified",
        )
        self.assertEqual(
            self.by_id["projectiles:projectile-fireball"]["states"]["qa"],
            "not-assessed",
        )

    def test_uninventoried_scopes_are_unknown_not_zero(self) -> None:
        scopes = self.outputs["coverage"]["uninventoried_scopes"]
        self.assertGreater(len(scopes), 0)
        self.assertTrue(all(scope["asset_count"] is None for scope in scopes))

    def test_current_animation_qa_requires_hashed_selection_decision_and_final_run(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_path = root / "animations/ressources/AMTEST/runs/final-v1"
            manifest_path = run_path / "manifest.json"
            write_json(manifest_path, {"schema": "run-v1", "status": "completed"})
            manifest_hash = registry.sha256_file(manifest_path)
            artifact = {
                "path": "animations/ressources/AMTEST/runs/final-v1",
                "manifest_path": "animations/ressources/AMTEST/runs/final-v1/manifest.json",
                "manifest_sha256": manifest_hash,
                "schema": "run-v1",
                "status": "completed",
            }
            lineage = {"source_runs": [], "source_packs": []}
            source_pack = {
                "path": "animations/packs-par-zone/amtest",
                "manifest_path": "animations/packs-par-zone/amtest/manifest.json",
                "manifest_sha256": "A" * 64,
                "schema": "pack-v1",
                "status": "completed",
                "areas": [
                    {
                        "area": "AR0001",
                        "path": "animations/packs-par-zone/amtest/AR0001",
                        "manifest_path": "animations/packs-par-zone/amtest/AR0001/manifest.json",
                        "manifest_sha256": "B" * 64,
                        "registry_sha256": "C" * 64,
                        "resource_entries": 1,
                    }
                ],
            }
            decision_path = root / "animations/index/qa-decisions/AMTEST/accepted.json"
            decision = {
                "schema_version": 1,
                "decision_id": "accepted",
                "asset_id": "animations:bam:AMTEST",
                "resref": "AMTEST",
                "status": "accepted",
                "decision_origin": "explicit-user-ingame-qa",
                "decision_date": "2026-09-02",
                "recorded_at_utc": "2026-09-02T12:00:00Z",
                "decision": "QA ingame explicite",
                "result_kind": "x4",
                "final_run": artifact,
                "lineage": lineage,
                "source_pack": source_pack,
                "tested_areas": ["AR0001"],
            }
            write_json(decision_path, decision)
            decision_hash = registry.sha256_file(decision_path)
            selection_path = root / "animations/index/selections/AMTEST.json"
            write_json(
                selection_path,
                {
                    "schema_version": 1,
                    "asset_id": "animations:bam:AMTEST",
                    "resref": "AMTEST",
                    "updated_at_utc": "2026-09-02T12:00:00Z",
                    "result_kind": "x4",
                    "selected_run": artifact,
                    "lineage": lineage,
                    "qa_decision": {
                        "path": "animations/index/qa-decisions/AMTEST/accepted.json",
                        "sha256": decision_hash,
                        "status": "accepted",
                        "decision_date": "2026-09-02",
                    },
                    "source_pack": source_pack,
                    "tested_areas": ["AR0001"],
                },
            )

            builder = registry.RegistryBuilder(root)
            with mock.patch.object(
                registry,
                "check_animation_workspace",
                return_value={"ok": True, "errors": []},
            ):
                selected, declared = registry.load_current_animation_qa(builder)
            self.assertEqual(declared, {"AMTEST"})
            self.assertEqual(selected["AMTEST"]["selection_path"], "animations/index/selections/AMTEST.json")
            self.assertEqual(
                selected["AMTEST"]["decision_path"],
                "animations/index/qa-decisions/AMTEST/accepted.json",
            )
            self.assertEqual(
                selected["AMTEST"]["final_manifest_path"],
                "animations/ressources/AMTEST/runs/final-v1/manifest.json",
            )
            self.assertEqual(builder._anomalies, [])

            selection = json.loads(selection_path.read_text(encoding="utf-8"))
            selection["qa_decision"]["sha256"] = "0" * 64
            write_json(selection_path, selection)
            invalid_builder = registry.RegistryBuilder(root)
            invalid, still_declared = registry.load_current_animation_qa(invalid_builder)
            self.assertEqual(invalid, {})
            self.assertEqual(still_declared, {"AMTEST"})
            self.assertEqual(
                [item["code"] for item in invalid_builder._anomalies],
                ["invalid-animation-selection"],
            )

    def test_generated_files_can_be_recreated_and_checked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            registry.write_outputs(self.outputs, output_dir)
            first = {
                path.name: path.read_bytes() for path in output_dir.iterdir()
            }
            registry.write_outputs(self.repeated_outputs, output_dir)
            second = {
                path.name: path.read_bytes() for path in output_dir.iterdir()
            }
            self.assertEqual(first, second)
            self.assertEqual(registry.check_outputs(self.outputs, output_dir), [])


if __name__ == "__main__":
    unittest.main()
