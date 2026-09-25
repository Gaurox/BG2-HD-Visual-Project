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

    def test_pool_strength_from_ar1000_is_written_only_on_the_dry_group(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        temporal = next(f for f in standard["families"] if f["id"] == "pool")["temporal"]
        self.assertEqual((temporal["material_id"], temporal["approved_strength"]), (1, 0.70))
        self.assertEqual((temporal["cycle"], temporal["cycle_seconds"], temporal["status"]),
                         ("fixed", 2.4, "validated-ingame-AR0408-AR0703"))
        dry = p.temporal_plan_group("pool", {"WTPOOL": "YFTEST"}, temporal)
        rain = p.temporal_plan_group("pool_rain", {"WTPOOLR": "YFTESTR"}, temporal, "pool")
        self.assertEqual((dry["approved_strength"], dry["cycle_seconds"]), (0.70, 2.4))
        self.assertNotIn("approved_strength", rain)
        self.assertNotIn("cycle_seconds", rain)

    def test_swamp_rain_is_timing_only_while_dry_keeps_q070(self):
        # AR0500 2026-09-25: q0.70 on the rain group erased the WTSWAMR drop rings.
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        temporal = next(f for f in standard["families"] if f["id"] == "swamp")["temporal"]
        self.assertEqual(
            (temporal["material_id"], temporal["cycle_seconds"],
             temporal["approved_strength"], temporal["approved_rain_strength"]),
            (5, 2.4, 0.70, 0.0),
        )
        dry = p.temporal_plan_group("swamp", {"WTSWAM": "YFTEST"}, temporal)
        rain = p.temporal_plan_group("swamp_rain", {"WTSWAMR": "YFTESTR"}, temporal, "swamp")
        self.assertEqual((dry["approved_strength"], dry["cycle_seconds"]), (0.70, 2.4))
        self.assertEqual((rain["approved_strength"], rain["rain_of"]), (0.0, "swamp"))
        self.assertNotIn("cycle_seconds", rain)

    def test_lava_torus_method_and_keys_are_written_only_on_the_dry_group(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        temporal = next(f for f in standard["families"] if f["id"] == "lava")["temporal"]
        self.assertEqual((temporal["method"], temporal["cycle_seconds"], temporal["keyframes"]),
                         ("seedvr-torus", 7.2, list(range(12))))
        refs = {r: "YFTST" + r[-1] for r in ("WTLAVA", "WTLAVB", "WTLAVC", "WTLAVD")}
        dry = p.temporal_plan_group("lava", refs, temporal)
        rain = p.temporal_plan_group("lava_rain", {r + "R": a + "R" for r, a in refs.items()}, temporal, "lava")
        self.assertEqual((dry["method"], dry["keyframes"], dry["cycle_seconds"]),
                         ("seedvr-torus", list(range(12)), 7.2))
        for key in ("method", "keyframes", "cycle_seconds", "approved_strength"):
            self.assertNotIn(key, rain)

    def test_brown_flow_contract_from_ar5000_is_written_only_on_the_dry_group(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        temporal = next(f for f in standard["families"] if f["id"] == "brown_flow")["temporal"]
        refs = {r: "YFTST" + r[-1] for r in ("WT5000A", "WT5000B", "WT5000C", "WT5000D")}
        dry = p.temporal_plan_group("brown_flow", refs, temporal)
        rain = p.temporal_plan_group("brown_flow_rain", {r + "R": a + "R" for r, a in refs.items()},
                                     temporal, "brown_flow")
        self.assertEqual((dry["method"], dry["cycle_seconds"]), ("seedvr-torus", 4.2667))
        self.assertEqual({k: dry["torus"][k] for k in ("heal_gain", "periodic_sigma_x4", "deridge_band_x1",
                                                       "max_non_torus_share", "temporal_harmonics")},
                         {"heal_gain": 0.0, "periodic_sigma_x4": 2.0, "deridge_band_x1": 2,
                          "max_non_torus_share": 0.01, "temporal_harmonics": 12})
        self.assertNotIn("torus", rain)

    def test_lake_teal_contract_from_ar6300_keeps_deridge_off(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        temporal = next(f for f in standard["families"] if f["id"] == "lake_teal")["temporal"]
        dry = p.temporal_plan_group("lake_teal", {"WTLAKA": "YFTSTA"}, temporal)
        self.assertEqual((dry["method"], dry["cycle_seconds"]), ("seedvr-torus", 4.2667))
        self.assertNotIn("deridge_band_x1", dry["torus"])       # it drew a grid on AR6300
        self.assertEqual(dry["torus"]["periodic_sigma_x4"], 2.0)

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

    def test_direct_run_master_is_found_in_its_upscale_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            direct = root / "maps/AR0503/runs/direct-x4/tuiles-secondaires/01_upscale"
            grid = root / "maps/AR0600/runs/grid-x4/tuiles-secondaires"
            for target in (direct, grid / "01_upscale", grid / "03_assemble"):
                target.mkdir(parents=True)
                (target / "master.png").write_bytes(b"x")
            saved, p.ROOT = p.ROOT, root
            try:
                master, _ = p.secondary_master("AR0503", None)
                assembled, candidates = p.secondary_master("AR0600", None)
            finally:
                p.ROOT = saved
            self.assertIn("01_upscale", master.as_posix())
            self.assertIn("03_assemble", assembled.as_posix())
            self.assertEqual(len(candidates), 1)

    def test_oil_torus_filters_are_written_only_on_the_dry_group(self):
        standard = json.loads(p.STANDARD.read_text(encoding="utf-8"))
        temporal = next(f for f in standard["families"] if f["id"] == "oil")["temporal"]
        dry = p.temporal_plan_group("oil", {"WTOIL": "YFTEST"}, temporal)
        rain = p.temporal_plan_group("oil_rain", {"WTOILR": "YFTESTR"}, temporal, "oil")
        self.assertEqual((dry["method"], dry["torus"]),
                         ("seedvr-torus", {"temporal_harmonics": 9, "equalize_detail": True}))
        self.assertNotIn("torus", rain)


if __name__ == "__main__":
    unittest.main()
