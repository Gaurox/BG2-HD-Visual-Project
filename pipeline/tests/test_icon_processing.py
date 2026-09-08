from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import sync_icon_processing as processing  # noqa: E402


class IconProcessingTests(unittest.TestCase):
    def write_resources(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=("asset_key", "resref", "source_sha256", "extracted_path"),
            )
            writer.writeheader()
            writer.writerow(
                {
                    "asset_key": "icon:SPWI101C",
                    "resref": "SPWI101C",
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
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(processing.csv_bytes([existing]))
            with (
                mock.patch.object(processing, "ROOT", root),
                mock.patch.object(processing, "RESOURCES", resources),
                mock.patch.object(processing, "PROCESSING", output),
            ):
                rows, additions = processing.build_rows()
            self.assertEqual(additions, 0)
            self.assertEqual(rows[0]["upscale_run"], "spwi101c-example-x4-v1")
            self.assertEqual(rows[0]["upscale_state"], "produced")


if __name__ == "__main__":
    unittest.main()
