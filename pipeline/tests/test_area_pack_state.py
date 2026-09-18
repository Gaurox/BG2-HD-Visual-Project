from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import area_pack_state as state  # noqa: E402


class AreaPackStateTests(unittest.TestCase):
    def make_zone(self, root: Path) -> tuple[Path, Path]:
        zone = root / "installed" / "AR0001"
        leaf = root / "packs" / "AR0001"
        zone.mkdir(parents=True)
        leaf.mkdir(parents=True)
        assets = []
        for resref, marker in (("AAA", 1), ("BBB-v1", 2)):
            for frame in range(2):
                name = f"AAX4-{resref}-frame{frame:03d}.rgba"
                payload = bytes([marker + frame]) * 16
                (zone / name).write_bytes(payload)
                (leaf / name).write_bytes(payload)
                assets.append({"name": name, "sha256": hashlib.sha256(payload).hexdigest()})
        (zone / "AreaAnimations-X4.registry").write_bytes(b"reg")
        manifest = {"resources": [{"resref": "AAA", "assets": assets[:2]},
                                  {"resref": "BBB", "assets": assets[2:]}]}
        (leaf / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return zone, leaf

    def test_installed_zone_and_stored_leaf_share_signatures(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            zone, leaf = self.make_zone(Path(raw))
            installed = state.zone_signatures(zone)
            self.assertEqual(set(installed), {"AAA", "BBB-v1"})
            self.assertEqual(installed, state.leaf_signatures(leaf))

    def test_fingerprint_changes_when_a_frame_is_rewritten(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            zone, _leaf = self.make_zone(Path(raw))
            before = state.zone_fingerprint(zone)
            (zone / "AAX4-AAA-frame000.rgba").write_bytes(b"\x09" * 17)
            self.assertNotEqual(state.zone_fingerprint(zone), before)

    def test_recipe_signatures_match_the_lock_for_both_recipe_kinds(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            zone, leaf = self.make_zone(root)
            locked = {key: info["sig"] for key, info in state.zone_signatures(zone).items()}
            original = state.ROOT
            try:
                state.ROOT = root
                entry = {"resources": state.zone_signatures(zone),
                         "build": {"leaf": "packs/AR0001"}}
                self.assertEqual(state.recipe_signatures(entry), locked)
                self.assertEqual(state.recipe_sources(entry), ["packs/AR0001"])
                merged = {"resources": entry["resources"],
                          "build": {"merged_from": ["packs/AR0001::AAA", "packs/AR0001::BBB::4,5"]}}
                self.assertEqual(state.recipe_signatures(merged), locked)
                self.assertEqual(state.recipe_sources(merged), ["packs/AR0001", "packs/AR0001"])
                # `CHEMIN::X,Y` lie une position sans sélectionner de ressource.
                bound = {"resources": entry["resources"],
                         "build": {"merged_from": ["packs/AR0001::483,368"]}}
                self.assertEqual(state.recipe_signatures(bound), locked)
                self.assertIsNone(state.recipe_signatures({"build": {"leaf": "packs/absent"}}))
                self.assertIsNone(state.recipe_signatures({"build": None}))
            finally:
                state.ROOT = original

    def test_resource_helpers_and_exceptions(self) -> None:
        self.assertEqual(state.base_resref("AM2300A-v2"), "AM2300A")
        self.assertEqual(state.resource_key("AAX4-FIRE_4-frame013.rgba"), "FIRE_4")
        self.assertIsNone(state.resource_key("AreaAnimations-X4.registry"))
        exceptions = [{"resref": "X", "areas": ["AR1"], "reason": ""}]
        self.assertTrue(state.is_exception(exceptions, "X", "AR1"))
        self.assertFalse(state.is_exception(exceptions, "X", "AR2"))


if __name__ == "__main__":
    unittest.main()
