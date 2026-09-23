"""Standard water plan: family table, deterministic aliases, master discovery."""
import json
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import plan_water_map as p


class PlanWaterMapTests(unittest.TestCase):
    def test_family_standard_maps_each_overlay_once(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        refs = [r for f in standard["families"] for r in f["overlays"]]
        self.assertEqual(len(refs), len(set(refs)))
        for family in standard["families"]:
            self.assertEqual(sorted(r for row in family["layout"] for r in row), sorted(family["overlays"]))
            self.assertIn(family["spatial_method"], ("seedvr", "bilinear"))

    def test_sewage_contract_is_frozen_from_ar2100_validation(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        sewage = next(f for f in standard["families"] if f["id"] == "sewage")
        self.assertEqual(sewage["spatial_method"], "seedvr")
        self.assertEqual(sewage["spatial_status"], "validated-ingame-AR2100")
        self.assertEqual(sewage["temporal"], {
            "material_id": 4,
            "cycle": "fixed",
            "cycle_seconds": 2.4,
            "status": "validated-ingame-AR2100",
        })
        self.assertEqual(sewage["contour"]["method"], "rgb-x4-silhouette-matte")
        self.assertEqual(sewage["witness"], "AR2100")

    def test_frozen_cycle_is_written_only_on_the_dry_temporal_group(self):
        temporal = {"material_id": 4, "cycle_seconds": 2.4}
        dry = p.temporal_plan_group("sewage", {"WTSEW": "YFTEST"}, temporal)
        rain = p.temporal_plan_group("sewage_rain", {"WTSEWR": "YFTESTR"}, temporal, "sewage")
        self.assertEqual(dry["cycle_seconds"], 2.4)
        self.assertNotIn("cycle_seconds", rain)
        self.assertEqual(rain["rain_of"], "sewage")

    def test_aliases_are_deterministic_unique_and_page_safe(self):
        first = p.make_alias("AR0404", 1, "S", set())
        self.assertEqual(first, p.make_alias("AR0404", 1, "S", set()))
        self.assertRegex(first, p.STANDARD_ALIAS)
        taken = set()
        aliases = [p.make_alias("AR1100", slot, kind, taken) for slot in (1, 2) for kind in "SF"]
        pages = [p.page_name(a) for a in aliases] + [p.page_name(a + "R") for a in aliases]
        self.assertEqual(len(set(pages)), len(pages))
        self.assertTrue(all(len(a + "R") <= 8 and len(p.page_name(a + "R")) <= 8 for a in aliases))
        blocked = {first, first + "R", p.page_name(first), p.page_name(first + "R")}
        self.assertNotEqual(p.make_alias("AR0404", 1, "S", blocked), first)

    def test_earlier_alias_names_are_not_mistaken_for_the_standard_chain(self):
        for name in ("WSWPIL", "Q9LAKE", "QBLKV0", "WTPOOL2"):
            self.assertIsNone(p.STANDARD_ALIAS.match(name))

    def test_secondary_master_discovery_separates_day_and_night(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for run in ("grid-jour", "grid-nuit"):
                target = root / "maps/AR1000/runs" / run / "tuiles-secondaires/03_assemble"
                target.mkdir(parents=True)
                (target / "master.png").write_bytes(b"x")
            saved, p.ROOT = p.ROOT, root
            try:
                day, _ = p.secondary_master("AR1000", None)
                night, _ = p.secondary_master("AR1000N", None)
            finally:
                p.ROOT = saved
            self.assertIn("jour", day.as_posix())
            self.assertIn("nuit", night.as_posix())


if __name__ == "__main__":
    unittest.main()
