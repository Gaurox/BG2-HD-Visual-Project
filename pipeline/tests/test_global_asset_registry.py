from __future__ import annotations

import csv
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import asset_tracking_contract as contract  # noqa: E402
import build_global_asset_registry as registry  # noqa: E402


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
            self.by_id["animations:bam:AM0033AB"]["states"]["qa"], "passed"
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
