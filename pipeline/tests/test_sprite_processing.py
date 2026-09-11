from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import sync_sprite_processing as processing  # noqa: E402
from sprite_layout import GROUP_FIELDS  # noqa: E402


class SpriteProcessingTests(unittest.TestCase):
    def write_csv(self, path: Path, fields: tuple[str, ...], rows: list[dict[str, str]]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def configure(self, root: Path) -> tuple[Path, Path, Path, Path]:
        families = root / "sprite/index/sprite_families.csv"
        animations = root / "sprite/index/sprite_animations.csv"
        groups = root / "sprite/index/family-groups.csv"
        output = root / "sprite/index/processing.csv"
        self.write_csv(
            families,
            (
                "family_id",
                "animation_id",
                "ids_symbol",
                "engine_section",
                "layer_kind",
                "variant_value",
                "item_resrefs",
                "bam_prefix",
                "pipeline_ready",
            ),
            [
                {
                    "family_id": "0xE400:body:base-resref:MGO1:MGO1",
                    "animation_id": "0xE400",
                    "ids_symbol": "GOBLIN_AXE",
                    "engine_section": "monster_icewind",
                    "layer_kind": "body",
                    "variant_value": "MGO1",
                    "item_resrefs": "",
                    "bam_prefix": "MGO1",
                    "pipeline_ready": "yes",
                }
            ],
        )
        self.write_csv(
            animations,
            ("animation_id", "ids_symbol", "symbol_race", "symbol_gender", "symbol_class", "symbol_variant"),
            [
                {
                    "animation_id": "0xE400",
                    "ids_symbol": "GOBLIN_AXE",
                    "symbol_race": "",
                    "symbol_gender": "",
                    "symbol_class": "GOBLIN_AXE",
                    "symbol_variant": "",
                }
            ],
        )
        self.write_csv(
            groups,
            GROUP_FIELDS,
            [
                {
                    "engine_section": "monster_icewind",
                    "macro_group": "monsters",
                    "directory": "monster-icewind",
                    "layout_kind": "single-family",
                    "bucket_policy": "named-high-byte",
                }
            ],
        )
        return families, animations, groups, output

    def patches(self, root: Path, families: Path, animations: Path, groups: Path, output: Path):
        return (
            mock.patch.object(processing, "ROOT", root),
            mock.patch.object(processing, "FAMILIES", families),
            mock.patch.object(processing, "ANIMATIONS", animations),
            mock.patch.object(processing, "GROUPS", groups),
            mock.patch.object(processing, "PROCESSING", output),
            mock.patch.object(processing, "CURRENT", root / "missing-current.json"),
            mock.patch.object(processing, "ACTIVE", root / "missing-active.json"),
        )

    def test_initializes_conservative_family_row(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            families, animations, groups, output = self.configure(root)
            patches = self.patches(root, families, animations, groups, output)
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                rows, additions, seeded = processing.build_rows()
            self.assertEqual((additions, seeded), (1, 0))
            self.assertEqual(rows[0]["production_state"], "ready")
            self.assertEqual(rows[0]["qa_state"], "not-assessed")
            self.assertEqual(rows[0]["installation_state"], "not-installed")
            self.assertEqual(
                rows[0]["asset_directory"],
                "sprite/families/monster-icewind/e4xx-goblins/e400-mgo1-goblin-axe",
            )

    def test_preserves_existing_lifecycle_values(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            families, animations, groups, output = self.configure(root)
            patches = self.patches(root, families, animations, groups, output)
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                rows, _, _ = processing.build_rows()
                rows[0]["production_run"] = "sprite/example/run.json"
                rows[0]["production_state"] = "produced"
                output.write_bytes(processing.csv_bytes(rows))
                updated, additions, _ = processing.build_rows()
            self.assertEqual(additions, 0)
            self.assertEqual(updated[0]["production_state"], "produced")
            self.assertEqual(updated[0]["production_run"], "sprite/example/run.json")

    def test_reconcile_active_updates_only_sealed_lifecycle_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            families, animations, groups, output = self.configure(root)
            patches = self.patches(root, families, animations, groups, output)
            proof = {
                "production_run": "sprite/catalog/build.json",
                "production_run_sha256": "A" * 64,
                "production_state": "verified",
                "selected_run": "sprite/catalog/build.json",
                "selected_run_sha256": "A" * 64,
                "qa_state": "pending",
                "qa_evidence": "",
                "installation_state": "installed",
                "installation_receipt": "sprite/catalog/active-test.json",
                "catalog_generation": "B" * 64,
            }
            with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5], patches[6]:
                rows, _, _ = processing.build_rows()
                rows[0]["production_state"] = "produced"
                rows[0]["release_state"] = "candidate"
                output.write_bytes(processing.csv_bytes(rows))
                with mock.patch.object(
                    processing,
                    "active_members",
                    return_value={("0XE400", "MGO1"): proof},
                ):
                    updated, additions, reconciled = processing.build_rows(
                        reconcile_active=True
                    )
            self.assertEqual((additions, reconciled), (0, 1))
            self.assertEqual(updated[0]["production_state"], "verified")
            self.assertEqual(updated[0]["installation_state"], "installed")
            self.assertEqual(updated[0]["catalog_generation"], "B" * 64)
            self.assertEqual(updated[0]["release_state"], "candidate")


if __name__ == "__main__":
    unittest.main()
