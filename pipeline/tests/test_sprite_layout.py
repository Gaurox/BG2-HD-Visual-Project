from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import sprite_layout as layout  # noqa: E402


class SpriteLayoutTests(unittest.TestCase):
    def test_character_layout_preserves_current_family_shape(self) -> None:
        family = {
            "animation_id": "0x6102",
            "ids_symbol": "FIGHTER_MALE_DWARF",
            "engine_section": "character",
            "layer_kind": "weapon",
            "variant_value": "AX",
            "item_resrefs": "AX1H01;AX1H02",
            "bam_prefix": "WQSAX",
        }
        animation = {
            "ids_symbol": "FIGHTER_MALE_DWARF",
            "symbol_race": "DWARF",
            "symbol_gender": "MALE",
            "symbol_class": "FIGHTER",
            "symbol_variant": "",
        }
        self.assertEqual(
            layout.project_relative(layout.family_directory(family, animation)),
            "sprite/families/playable-characters/6102-dwarf-male-fighter/ax1h01-wqsax",
        )

    def test_monster_icewind_uses_named_high_byte_bucket(self) -> None:
        family = {
            "animation_id": "0xE400",
            "ids_symbol": "GOBLIN_AXE",
            "engine_section": "monster_icewind",
            "layer_kind": "body",
            "variant_value": "MGO1",
            "item_resrefs": "",
            "bam_prefix": "MGO1",
        }
        self.assertEqual(
            layout.project_relative(layout.family_directory(family, family)),
            "sprite/families/monster-icewind/e4xx-goblins/e400-mgo1-goblin-axe",
        )

    def test_generic_family_is_routed_through_macro_directory(self) -> None:
        family = {
            "animation_id": "0x7000",
            "ids_symbol": "CHICKEN",
            "engine_section": "monster",
            "layer_kind": "body",
            "variant_value": "MCHI",
            "item_resrefs": "",
            "bam_prefix": "MCHI",
        }
        self.assertEqual(
            layout.project_relative(layout.family_directory(family, family)),
            "sprite/families/monsters/70xx/7000-mchi-chicken",
        )


if __name__ == "__main__":
    unittest.main()
