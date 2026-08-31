from __future__ import annotations

import csv
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from extract_character_portraits import parse_selectable_portraits  # noqa: E402


class PortraitInventoryTests(unittest.TestCase):
    def test_bgee_lua_parser_reads_only_portrait_table(self) -> None:
        source = """portraits =
{
    {'hero1', 1},
    {\"HERO2\", 2},
}
movies =
{
    {'NOT_A_PORTRAIT', 1},
}
"""
        self.assertEqual(parse_selectable_portraits(source), {"HERO1", "HERO2"})

    def test_inventory_is_logical_unique_and_fully_hashed(self) -> None:
        with (ROOT / "portraits" / "inventaire_portraits.csv").open(
            newline="", encoding="utf-8-sig"
        ) as handle:
            rows = list(csv.DictReader(handle))

        self.assertEqual(len(rows), 105)
        self.assertEqual(len({row["portrait"] for row in rows}), len(rows))
        self.assertEqual(sum(len(row["tailles"]) for row in rows), 285)
        self.assertTrue(
            all(
                "yes" in (row["selectable"], row["recrutable"], row["rencontre"])
                for row in rows
            )
        )
        for row in rows:
            for suffix in row["tailles"].lower():
                self.assertEqual(len(row[f"sha256_{suffix}"]), 64)
                self.assertTrue(row[f"fichier_{suffix}"])
                self.assertTrue(row[f"ressource_{suffix}"])


if __name__ == "__main__":
    unittest.main()
