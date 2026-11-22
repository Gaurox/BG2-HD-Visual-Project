from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import sync_icon_processing as processing  # noqa: E402


class IconProcessingTests(unittest.TestCase):
    def write_resources(self, path: Path, roles: str = "item-description") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.with_name("production-scope.json").write_text(
            json.dumps({
                "active_families": ["item-description", "item-ground"],
                "excluded_tracking_families": ["spellbook"],
            }),
            encoding="utf-8",
        )
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=("asset_key", "resref", "roles", "source_sha256", "extracted_path"),
            )
            writer.writeheader()
            writer.writerow(
                {
                    "asset_key": "icon:SPWI101C",
                    "resref": "SPWI101C",
                    "roles": roles,
                    "source_sha256": "A" * 64,
                    "extracted_path": "icons/ressources/SPWI101C/source.bam",
                }
            )

    def test_initializes_conservative_asset_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "icons/index/resources.csv"
            output = root / "icons/index/processing.csv"
            self.write_resources(resources)
            with (
                mock.patch.object(processing, "ROOT", root),
                mock.patch.object(processing, "RESOURCES", resources),
                mock.patch.object(processing, "PROCESSING", output),
            ):
                rows, additions = processing.build_rows()
            self.assertEqual(additions, 1)
            self.assertEqual(
                rows[0],
                {
                    "asset_key": "icon:SPWI101C",
                    "asset_id": "icons:icon-spwi101c",
                    "asset_directory": "icons/ressources/SPWI101C",
                    "upscale_run": "",
                    "upscale_state": "not-started",
                    "selected_run": "",
                    "qa_state": "not-assessed",
                    "qa_evidence": "",
                    "installation_state": "not-installed",
                    "installation_receipt": "",
                    "release_state": "not-evaluated",
                    "release_candidate": "",
                    "notes": "",
                },
            )

    def test_preserves_existing_lifecycle_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "icons/index/resources.csv"
            output = root / "icons/index/processing.csv"
            self.write_resources(resources)
            existing = processing.default_row(
                {"asset_key": "icon:SPWI101C", "resref": "SPWI101C"}
            )
            existing["upscale_run"] = "spwi101c-example-x4-v1"
            existing["upscale_state"] = "produced"
            output.write_bytes(processing.csv_bytes([existing]).rstrip(b"\r\n") + b"legacy, note\r\n")
            with (
                mock.patch.object(processing, "ROOT", root),
                mock.patch.object(processing, "RESOURCES", resources),
                mock.patch.object(processing, "PROCESSING", output),
            ):
                rows, additions = processing.build_rows()
            self.assertEqual(additions, 0)
            self.assertEqual(rows[0]["upscale_run"], "spwi101c-example-x4-v1")
            self.assertEqual(rows[0]["upscale_state"], "produced")
            self.assertEqual(rows[0]["notes"], "legacy, note")

    def test_spellbook_asset_requires_an_active_family_for_tracking(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            resources = root / "icons/index/resources.csv"
            output = root / "icons/index/processing.csv"
            with (
                mock.patch.object(processing, "ROOT", root),
                mock.patch.object(processing, "RESOURCES", resources),
                mock.patch.object(processing, "PROCESSING", output),
            ):
                for roles in ("spellbook", "item-inventory;spellbook"):
                    self.write_resources(resources, roles)
                    self.assertEqual(processing.build_rows(), ([], 0))

                self.write_resources(resources, "item-description;spellbook")
                rows, additions = processing.build_rows()
                self.assertEqual(additions, 1)
                self.assertEqual([row["asset_key"] for row in rows], ["icon:SPWI101C"])


if __name__ == "__main__":
    unittest.main()
