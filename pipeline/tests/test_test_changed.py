from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


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
        for path in (
            "pipeline/scripts/run_animation_upscale_30fps_v2.py",
            "pipeline/scripts/build_per_frame_spline_alpha_30fps_v2.py",
            "pipeline/scripts/animation_authority_lock.py",
            "pipeline/scripts/verify_animation_release_candidate.py",
        ):
            with self.subTest(path=path):
                plan = self.plan(path)
                self.assertFalse(plan.full)
                self.assertEqual(plan.groups, ("smoke", "animations"))
                self.assertNotIn("maps", plan.groups)
                self.assertFalse(any(name.startswith("sprite-") for name in plan.groups))

    def test_animation_release_transaction_keeps_scoped_test_groups(self) -> None:
        plan = self.plan("pipeline/scripts/animation_release.py")
        self.assertFalse(plan.full)
        self.assertEqual(
            plan.groups,
            ("smoke", "animations", "animation-release", "registry", "integrity"),
        )
        self.assertNotIn("release", plan.groups)
        self.assertIn(
            "pipeline.tests.test_animation_release",
            selector.python_modules_for(plan),
        )
        self.assertIn(
            "pipeline.tests.test_release_animation_delta",
            selector.python_modules_for(plan),
        )

    def test_animation_qa_authorities_select_integrity(self) -> None:
        for path in (
            "animations/index/qa-decisions/FPIT1S/2026-09-02-accepted.json",
            "animations/index/selections/FPIT1S.json",
        ):
            with self.subTest(path=path):
                plan = self.plan(path)
                self.assertIn("animations", plan.groups)
                self.assertIn("registry", plan.groups)
                self.assertIn("integrity", plan.groups)

    def test_release_qa_approval_selects_only_its_area_gate(self) -> None:
        for filename in ("qa-approval.json", "qa-v2-0123456789abcdef.json"):
            with self.subTest(filename=filename):
                plan = self.plan(
                    "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/"
                    f"AR0602/{filename}"
                )
                self.assertFalse(plan.full)
                self.assertEqual(plan.animation_areas, ("AR0602",))
                self.assertNotIn("release", plan.groups)
                release_commands = [
                    command for command in selector.commands_for(plan) if command.scope == "release"
                ]
                self.assertEqual(len(release_commands), 1)
                self.assertIn(str(selector.RELEASE_AREA_ANIMATION), release_commands[0].argv)
                self.assertIn("AR0602", release_commands[0].argv)
                self.assertNotIn(str(selector.RELEASE_PHASE2), release_commands[0].argv)

    def test_candidate_register_targets_only_semantically_changed_areas(self) -> None:
        before = {
            "schema_version": 2,
            "candidates": [
                {"area": "AR0602", "approval_status": "approved-for-release"},
                {"area": "AR0900", "approval_status": "approved-for-release"},
            ],
        }
        after = {
            "schema_version": 2,
            "candidates": [
                {"area": "AR0602", "approval_status": "approved-for-release"},
                {"area": "AR0900", "approval_status": "pending-qa"},
                {"area": "OH4000", "approval_status": "approved-for-release"},
            ],
        }
        changes = selector.candidate_area_changes(before, after)
        self.assertEqual(changes.changed, ("AR0900", "OH4000"))
        self.assertEqual(changes.removed, ())
        self.assertFalse(changes.shared_changed)
        plan = selector.select_paths(
            (selector.ChangedPath("M", selector.ANIMATION_CANDIDATES_PATH),),
            strict_targeted=True,
            candidate_changes=changes,
        )
        self.assertEqual(plan.animation_areas, ("AR0900", "OH4000"))
        self.assertNotIn("release", plan.groups)
        commands = selector.commands_for(plan, "release")
        self.assertEqual(len(commands), 2)
        self.assertTrue(all(str(selector.RELEASE_AREA_ANIMATION) in item.argv for item in commands))

    def test_candidate_removal_or_shared_change_keeps_global_phase2(self) -> None:
        for changes in (
            selector.CandidateAreaChanges((), ("AR0602",)),
            selector.CandidateAreaChanges((), (), shared_changed=True),
            None,
        ):
            with self.subTest(changes=changes):
                plan = selector.select_paths(
                    (selector.ChangedPath("M", selector.ANIMATION_CANDIDATES_PATH),),
                    strict_targeted=True,
                    candidate_changes=changes,
                )
                self.assertIn("release", plan.groups)
                commands = selector.commands_for(plan, "release")
                self.assertEqual(len(commands), 1)
                self.assertIn(str(selector.RELEASE_PHASE2), commands[0].argv)

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

    def test_strict_targeted_never_adds_smoke_or_becomes_full(self) -> None:
        plan = selector.select_paths(
            (selector.ChangedPath("M", "pipeline/README.md"),),
            strict_targeted=True,
        )
        self.assertFalse(plan.full)
        self.assertEqual(plan.selection_mode, "targeted")
        self.assertEqual(plan.groups, ("documentation",))
        self.assertEqual(
            selector.python_modules_for(plan),
            ("pipeline.tests.test_repository_docs",),
        )

    def test_strict_targeted_classifies_rename_without_full_fallback(self) -> None:
        plan = selector.select_paths(
            (selector.ChangedPath("R100", "maps/new.json", "maps/old.json"),),
            strict_targeted=True,
        )
        self.assertFalse(plan.full)
        self.assertEqual(plan.groups, ("maps",))

    def test_strict_targeted_release_engine_and_test_file_are_scoped(self) -> None:
        cases = (
            ("releases/BG2-HD-Upscale/manifests/release.json", ("release",)),
            (
                "engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/config.cpp",
                ("engine",),
            ),
        )
        for path, groups in cases:
            with self.subTest(path=path):
                plan = selector.select_paths(
                    (selector.ChangedPath("M", path),),
                    strict_targeted=True,
                )
                self.assertFalse(plan.full)
                self.assertEqual(plan.groups, groups)
        test_plan = selector.select_paths(
            (selector.ChangedPath("M", "pipeline/tests/test_map_build_transaction.py"),),
            strict_targeted=True,
        )
        self.assertFalse(test_plan.full)
        self.assertEqual(test_plan.groups, ())
        self.assertEqual(
            selector.python_modules_for(test_plan),
            ("pipeline.tests.test_map_build_transaction",),
        )

    def test_strict_targeted_unknown_path_selects_nothing(self) -> None:
        plan = selector.select_paths(
            (selector.ChangedPath("M", "pipeline/scripts/new_unclassified_tool.mjs"),),
            strict_targeted=True,
        )
        self.assertFalse(plan.full)
        self.assertEqual(selector.commands_for(plan), ())
        self.assertTrue(any("aucun test ciblé connu" in reason for reason in plan.reasons))

    def test_progress_ui_selects_its_own_module(self) -> None:
        for strict_targeted in (False, True):
            with self.subTest(strict_targeted=strict_targeted):
                plan = selector.select_paths(
                    (selector.ChangedPath("M", "pipeline/scripts/progress_ui.py"),),
                    strict_targeted=strict_targeted,
                )
                self.assertFalse(plan.full)
                self.assertIn(
                    "pipeline.tests.test_progress_ui",
                    selector.python_modules_for(plan),
                )

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
        self.assertIn("--run", workspace.argv)
        self.assertIn("all", workspace.argv)
        release = next(command for command in commands if command.label == "gate release Phase 2")
        self.assertIn("-ReleaseRoot", release.argv)
        engine = next(command for command in commands if command.label == "tests moteur")
        if selector.os.name == "nt":
            self.assertIn("-C", engine.argv)
            self.assertIn("Debug", engine.argv)

    def test_cli_is_plan_only_unless_run_is_explicit(self) -> None:
        self.assertFalse(selector.parse_args([]).run)
        self.assertTrue(selector.parse_args(["--targeted", "--run"]).run)
        self.assertTrue(
            selector.parse_args(["--targeted", "--run", "--keep-going"]).keep_going
        )
        with self.assertRaises(SystemExit):
            selector.parse_args(["--targeted", "--keep-going"])
        with self.assertRaises(SystemExit):
            selector.parse_args(["--run"])

    def test_keep_going_aggregates_failures_while_default_stops(self) -> None:
        commands = (
            selector.Command("one", "python", ("one",)),
            selector.Command("two", "release", ("two",)),
            selector.Command("three", "engine", ("three",)),
        )

        def run_with(codes: list[int], keep_going: bool) -> tuple[int, list[str]]:
            calls: list[str] = []

            def runner(argv: tuple[str, ...], **_kwargs: object) -> object:
                calls.append(argv[0])
                return type("Completed", (), {"returncode": codes[len(calls) - 1]})()

            with mock.patch.object(selector, "commands_for", return_value=commands):
                code = selector.execute_plan(
                    selector.full_plan("test"),
                    keep_going=keep_going,
                    runner=runner,
                )
            return code, calls

        self.assertEqual(run_with([7, 0, 9], False), (7, ["one"]))
        self.assertEqual(run_with([7, 0, 9], True), (7, ["one", "two", "three"]))


if __name__ == "__main__":
    unittest.main()
