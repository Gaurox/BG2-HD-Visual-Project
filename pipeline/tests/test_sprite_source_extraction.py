from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import extract_sprite_sources as extraction  # noqa: E402
from sprite_layout import GROUP_FIELDS  # noqa: E402


class SpriteSourceExtractionTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def test_family_plan_deduplicates_shared_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            families = root / "sprite/index/sprite_families.csv"
            resources = root / "sprite/index/sprite_resources.csv"
            groups = root / "sprite/index/family-groups.csv"
            family_rows = [
                {
                    "family_id": f"family-{index}",
                    "animation_id": f"0x610{index}",
                    "engine_section": "character",
                    "pipeline_ready": "yes",
                }
                for index in range(2)
            ]
            self.write_csv(
                families,
                ("family_id", "animation_id", "engine_section", "pipeline_ready"),
                family_rows,
            )
            self.write_csv(
                resources,
                ("bam_resref", "family_ids", "blocker"),
                [
                    {"bam_resref": "SHARED", "family_ids": "family-0;family-1", "blocker": ""},
                    {"bam_resref": "ONLY0", "family_ids": "family-0", "blocker": ""},
                ],
            )
            self.write_csv(
                groups,
                GROUP_FIELDS,
                [
                    {
                        "engine_section": "character",
                        "macro_group": "characters",
                        "directory": "playable-characters",
                        "layout_kind": "character-components",
                        "bucket_policy": "none",
                    }
                ],
            )
            with (
                mock.patch.object(extraction, "FAMILIES", families),
                mock.patch.object(extraction, "RESOURCES", resources),
                mock.patch.object(extraction, "GROUPS", groups),
            ):
                selected_families, selected_resources = extraction.select_inventory(
                    macro_groups=["characters"]
                )
                animation_families, animation_resources = extraction.select_inventory(
                    animation_ids=["0x6100"]
                )
            self.assertEqual(len(selected_families), 2)
            self.assertEqual(
                [row["bam_resref"] for row in selected_resources], ["SHARED", "ONLY0"]
            )
            self.assertEqual(
                [row["family_id"] for row in animation_families], ["family-0"]
            )
            self.assertEqual(
                [row["bam_resref"] for row in animation_resources], ["SHARED", "ONLY0"]
            )

    def test_selector_is_mandatory(self) -> None:
        with self.assertRaisesRegex(ValueError, "sélecteur requis"):
            extraction.select_inventory()


if __name__ == "__main__":
    unittest.main()
