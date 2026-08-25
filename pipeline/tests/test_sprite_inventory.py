from __future__ import annotations

import csv
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "sprite" / "index"
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import build_sprite_inventory as inventory  # noqa: E402


def rows(name: str) -> list[dict[str, str]]:
    with (INDEX / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


class SpriteInventoryTests(unittest.TestCase):
    def test_project_documentation_routes_agents_through_inventory(self) -> None:
        required = {
            ROOT / "README.md": ("sprite/README.md", "sprite/index/"),
            ROOT / "pipeline" / "README.md": ("../sprite/README.md",),
            ROOT / "HANDOVER.md": ("sprite/index/README.md", "build_sprite_inventory.py"),
            ROOT / "CHANTIERS_OUVERTS.md": ("sprite/index/sprite_families.csv", "blocker"),
            ROOT / "sprite" / "SPRITE_UPSCALE_PIPELINE.md": ("Gate I0", "pipeline_ready=yes"),
            ROOT / "sprite" / "UPSCALE_XBR2X.md": ("index/README.md", "family_id"),
            ROOT
            / "engine"
            / "InfinityEngine-Enhancer"
            / "source-patchee"
            / "CLAUDE.md": ("Runtime Facts — Creature Sprites", "sprite_families.csv"),
        }
        for path, markers in required.items():
            content = path.read_text(encoding="utf-8-sig")
            for marker in markers:
                self.assertIn(marker, content, f"{path} must reference {marker}")

    def test_runtime_classification_is_explicit(self) -> None:
        self.assertEqual(
            inventory.current_runtime(0x6102, "6000", "character"),
            ("character-bg2ee-2.7.3.0", True),
        )
        self.assertEqual(
            inventory.current_runtime(0xE400, "E000", "monster_icewind"),
            ("monster-icewind-bg2ee-2.7.3.0", True),
        )
        self.assertEqual(inventory.current_runtime(0x7F07, "7000", "monster"), ("", False))

    def test_generated_relations_are_closed(self) -> None:
        animations = rows("sprite_animations.csv")
        families = rows("sprite_families.csv")
        resources = rows("sprite_resources.csv")
        items = rows("sprite_items.csv")
        inventory.verify_inventory(animations, families, resources, items)

    def test_known_golem_and_goblin_families(self) -> None:
        families = {row["family_id"]: row for row in rows("sprite_families.csv")}
        golem = families["0x7F07:body:base-resref:MGLC:MGLC"]
        self.assertEqual(golem["resource_count"], "13")
        self.assertEqual(golem["frame_count"], "5994")
        self.assertEqual(golem["runtime_supported"], "no")
        self.assertEqual(golem["blocker"], "runtime-profile-unsupported")

        goblin = families["0xE400:body:base-resref:MGO1:MGO1"]
        self.assertEqual(goblin["resource_count"], "20")
        self.assertEqual(goblin["pipeline_ready"], "yes")

    def test_known_dwarf_character_anomalies(self) -> None:
        selected = {
            row["bam_prefix"]: row
            for row in rows("sprite_families.csv")
            if row["animation_id"] == "0x6102"
            and row["bam_prefix"] in {"CDMF4", "WQSJ6", "WQSC1", "WQSAX"}
        }
        self.assertGreater(int(selected["CDMF4"]["duplicate_used_rgba_frames"]), 0)
        self.assertIn("duplicate-used-rgba-indices", selected["CDMF4"]["blocker"])
        self.assertEqual(selected["WQSJ6"]["pipeline_ready"], "yes")
        self.assertEqual(selected["WQSC1"]["pipeline_ready"], "yes")
        self.assertEqual(selected["WQSAX"]["unexpected_suffixes"], "OA7;OA8;OA9;OG1")

    def test_known_items_resolve_from_stock_itm(self) -> None:
        items = {row["item_resref"]: row for row in rows("sprite_items.csv")}
        self.assertEqual(items["PLAT04"]["body_armor_code"], "4")
        self.assertEqual(items["HELM01"]["animation_code"], "J6")
        self.assertEqual(items["SHLD13"]["animation_code"], "C1")
        self.assertEqual(items["AX1H13"]["animation_code"], "AX")


if __name__ == "__main__":
    unittest.main()
