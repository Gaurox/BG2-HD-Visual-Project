from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import test_changed as selector  # noqa: E402


class ChangedTestSelectorTests(unittest.TestCase):
    def plan(self, path: str, status: str = "M") -> selector.SelectionPlan:
        return selector.select_paths((selector.ChangedPath(status, path),))

    def test_maps_select_smoke_and_maps_without_sprites(self) -> None:
        plan = self.plan("pipeline/scripts/inject_build.py")
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("smoke", "maps"))
        self.assertFalse(any(name.startswith("sprite-") for name in plan.groups))

    def test_animation_selects_no_map_or_sprite_group(self) -> None:
        plan = self.plan("pipeline/scripts/run_animation_upscale_30fps_v2.py")
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("smoke", "animations"))
        self.assertNotIn("maps", plan.groups)
        self.assertFalse(any(name.startswith("sprite-") for name in plan.groups))

    def test_sprite_generator_does_not_select_formats_or_installation(self) -> None:
        plan = self.plan("pipeline/scripts/generate_sprite_family_append.py")
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("smoke", "sprite-inventory"))
        self.assertNotIn("sprite-formats", plan.groups)
        self.assertNotIn("sprite-installation", plan.groups)

    def test_sprite_formats_do_not_select_slow_installation(self) -> None:
        plan = self.plan("pipeline/scripts/run_creature_sprite_x2.py")
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("smoke", "sprite-formats"))
        self.assertNotIn("sprite-installation", plan.groups)

    def test_sprite_installer_requires_transaction_tests(self) -> None:
        plan = self.plan("pipeline/scripts/Install-CreatureSprite-XN-Catalog-Test.ps1")
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("smoke", "sprite-installation"))
        self.assertIn(
            "pipeline.tests.test_creature_sprite_xn_catalog_install",
            selector.python_modules_for(plan),
        )

    def test_documentation_selects_only_smoke_and_docs(self) -> None:
        plan = self.plan("pipeline/README.md")
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("smoke", "documentation"))

    def test_unknown_path_falls_back_to_full(self) -> None:
        plan = self.plan("pipeline/scripts/new_unclassified_tool.mjs")
        self.assertTrue(plan.full)
        self.assertTrue(any("chemin inconnu" in reason for reason in plan.reasons))

    def test_rename_and_delete_fall_back_to_full(self) -> None:
        for status in ("R100", "C100", "D"):
            with self.subTest(status=status):
                plan = selector.select_paths(
                    (selector.ChangedPath(status, "maps/new.json", "maps/old.json"),)
                )
                self.assertTrue(plan.full)

    def test_release_engine_and_test_infrastructure_force_full(self) -> None:
        for path in (
            "releases/BG2-HD-Upscale/manifests/release.json",
            "engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/config.cpp",
            "pipeline/tests/test_map_build_transaction.py",
        ):
            with self.subTest(path=path):
                self.assertTrue(self.plan(path).full)

    def test_full_plan_keeps_all_scopes_and_uses_single_pass_workspace_check(self) -> None:
        plan = selector.full_plan("test")
        commands = selector.commands_for(plan)
        labels = [command.label for command in commands]
        self.assertIn("suite Python complète", labels)
        self.assertIn("gate release Phase 2", labels)
        self.assertIn("tests moteur", labels)
        workspace = next(
            command for command in commands if command.label == "sorties workspace après tests complets"
        )
        self.assertIn("--after-full-tests", workspace.argv)
        release = next(command for command in commands if command.label == "gate release Phase 2")
        self.assertIn("-ReleaseRoot", release.argv)
        engine = next(command for command in commands if command.label == "tests moteur")
        if selector.os.name == "nt":
            self.assertIn("-C", engine.argv)
            self.assertIn("Debug", engine.argv)


if __name__ == "__main__":
    unittest.main()
