from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import test_changed as selector  # noqa: E402


class ChangedTestSelectorTests(unittest.TestCase):
    def targeted(self, *paths: str) -> selector.SelectionPlan:
        return selector.select_paths(
            tuple(selector.ChangedPath("M", path) for path in paths),
            strict_targeted=True,
        )

    def test_authorities_projections_and_docs_select_no_python_tests(self) -> None:
        for path in (
            "areas.csv",
            "maps/AR2300/builds.json",
            "animations/index/selections/FALL1A.json",
            "sprite/index/inventory.json",
            "asset-tracking/registry.json",
            "docs/TEST_SELECTION.md",
        ):
            with self.subTest(path=path):
                plan = self.targeted(path)
                self.assertEqual(selector.python_modules_for(plan), ())
                self.assertEqual(selector.commands_for(plan, "python"), ())

    def test_python_script_selects_only_homonymous_test(self) -> None:
        cases = {
            "pipeline/scripts/build_alpha_feather.py": (
                "pipeline.tests.test_build_alpha_feather",
            ),
            "pipeline/scripts/progress_ui.py": ("pipeline.tests.test_progress_ui",),
            "pipeline/scripts/workspace.py": ("pipeline.tests.test_workspace_command",),
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(selector.python_modules_for(self.targeted(path)), expected)

    def test_compositor_package_selects_its_single_targeted_test(self) -> None:
        self.assertEqual(
            selector.python_modules_for(
                self.targeted("pipeline/map_patch_compositor/core.py")
            ),
            ("pipeline.tests.test_map_patch_compositor",),
        )

    def test_explicit_aliases_remain_narrow(self) -> None:
        cases = {
            "pipeline/scripts/inject_build.py": ("pipeline.tests.test_map_build_transaction",),
            "pipeline/scripts/split_animation_pack_by_area.py": (
                "pipeline.tests.test_animation_pack_area_split",
            ),
            "pipeline/scripts/animation_release.py": (
                "pipeline.tests.test_animation_release",
                "pipeline.tests.test_release_animation_delta",
            ),
            "pipeline/scripts/build_spline_top_reconstructed_alpha.py": (
                "pipeline.tests.test_spline_top_reconstructed_alpha",
            ),
            "pipeline/scripts/Install-CreatureSprite-XN-Test.ps1": (
                "pipeline.tests.test_creature_sprite_x2_pipeline",
            ),
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertEqual(selector.python_modules_for(self.targeted(path)), expected)

    def test_changed_test_file_selects_itself(self) -> None:
        plan = self.targeted("pipeline/tests/test_map_build_transaction.py")
        self.assertEqual(
            selector.python_modules_for(plan),
            ("pipeline.tests.test_map_build_transaction",),
        )

    def test_explicit_paths_are_normalized_deduplicated_and_isolated(self) -> None:
        paths = selector.explicit_changed_paths(
            ("./pipeline/scripts/build_alpha_feather.py", "pipeline\\scripts\\build_alpha_feather.py")
        )
        self.assertEqual(
            paths,
            (selector.ChangedPath("M", "pipeline/scripts/build_alpha_feather.py"),),
        )
        with self.assertRaises(ValueError):
            selector.explicit_changed_paths(("../outside.py",))

    def test_release_qa_approval_selects_only_its_area_gate(self) -> None:
        plan = self.targeted(
            "releases/BG2-HD-Upscale/manifests/animation-qa-approvals/AR0602/qa-approval.json"
        )
        self.assertEqual(plan.animation_areas, ("AR0602",))
        self.assertEqual(selector.python_modules_for(plan), ())
        commands = selector.commands_for(plan, "release")
        self.assertEqual(len(commands), 1)
        self.assertIn("AR0602", commands[0].argv)
        self.assertNotIn(str(selector.RELEASE_PHASE2), commands[0].argv)

    def test_candidate_register_targets_semantically_changed_areas(self) -> None:
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
            ],
        }
        changes = selector.candidate_area_changes(before, after)
        plan = selector.select_paths(
            (selector.ChangedPath("M", selector.ANIMATION_CANDIDATES_PATH),),
            strict_targeted=True,
            candidate_changes=changes,
        )
        self.assertEqual(plan.animation_areas, ("AR0900",))
        self.assertNotIn("release", plan.groups)

    def test_candidate_removal_or_unknown_diff_keeps_global_release_gate(self) -> None:
        for changes in (selector.CandidateAreaChanges((), ("AR0602",)), None):
            with self.subTest(changes=changes):
                plan = selector.select_paths(
                    (selector.ChangedPath("M", selector.ANIMATION_CANDIDATES_PATH),),
                    strict_targeted=True,
                    candidate_changes=changes,
                )
                self.assertIn("release", plan.groups)
                command = selector.commands_for(plan, "release")[0]
                self.assertIn(str(selector.RELEASE_PHASE2), command.argv)

    def test_release_engine_and_unknown_paths_keep_safe_boundaries(self) -> None:
        self.assertEqual(
            self.targeted("releases/BG2-HD-Upscale/manifests/release.json").groups,
            ("release",),
        )
        self.assertEqual(
            self.targeted(
                "engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/config.cpp"
            ).groups,
            ("engine",),
        )
        strict = self.targeted("pipeline/scripts/new_unclassified_tool.mjs")
        self.assertFalse(strict.full)
        self.assertEqual(selector.commands_for(strict), ())
        changed = selector.select_paths(
            (selector.ChangedPath("M", "pipeline/scripts/new_unclassified_tool.mjs"),)
        )
        self.assertTrue(changed.full)

    def test_full_plan_keeps_all_release_controls(self) -> None:
        labels = [command.label for command in selector.commands_for(selector.full_plan("test"))]
        self.assertIn("suite Python complète", labels)
        self.assertIn("gate release Phase 2", labels)
        self.assertIn("tests moteur", labels)

    def test_cli_requires_explicit_mode_and_valid_path_scope(self) -> None:
        self.assertFalse(selector.parse_args([]).run)
        args = selector.parse_args(
            ["--targeted", "--path", "areas.csv", "--path", "maps/AR2300/builds.json"]
        )
        self.assertEqual(args.path, ["areas.csv", "maps/AR2300/builds.json"])
        for argv in (
            ["--path", "areas.csv"],
            ["--targeted", "--path", "../outside.py"],
            ["--targeted", "--path", "areas.csv", "--base", "HEAD~1"],
            ["--run"],
            ["--targeted", "--keep-going"],
        ):
            with self.subTest(argv=argv), self.assertRaises(SystemExit):
                selector.parse_args(argv)

    def test_keep_going_aggregates_failures_while_default_stops(self) -> None:
        commands = (
            selector.Command("one", "python", ("one",)),
            selector.Command("two", "release", ("two",)),
        )

        def run_with(keep_going: bool) -> tuple[int, list[str]]:
            calls: list[str] = []

            def runner(argv: tuple[str, ...], **_kwargs: object) -> object:
                calls.append(argv[0])
                return type("Completed", (), {"returncode": 7 if argv[0] == "one" else 0})()

            with mock.patch.object(selector, "commands_for", return_value=commands):
                code = selector.execute_plan(
                    selector.full_plan("test"),
                    keep_going=keep_going,
                    runner=runner,
                )
            return code, calls

        self.assertEqual(run_with(False), (7, ["one"]))
        self.assertEqual(run_with(True), (7, ["one", "two"]))


if __name__ == "__main__":
    unittest.main()
