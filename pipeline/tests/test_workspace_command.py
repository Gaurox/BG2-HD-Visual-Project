from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import test_changed  # noqa: E402
import workspace  # noqa: E402


class WorkspaceCommandTests(unittest.TestCase):
    def test_all_scopes_are_single_pass_and_exclude_tests_by_default(self) -> None:
        stages = workspace.stages("refresh", "python")
        self.assertEqual(
            [stage.scope for stage in stages],
            ["graphics", "registry", "integrity"],
        )
        self.assertEqual(
            [stage.name for stage in stages],
            [
                "inventaires graphiques complémentaires",
                "registre global",
                "intégrité physique et index des runs",
            ],
        )
        for stage in stages:
            self.assertNotIn("--verify-determinism", stage.command)
            self.assertNotIn("unittest", stage.command)

    def test_scopes_are_exact_and_repeatable(self) -> None:
        stages = workspace.stages(
            "check",
            "python",
            scopes=("registry", "integrity"),
        )
        self.assertEqual([stage.scope for stage in stages], ["registry", "integrity"])
        for stage in stages:
            self.assertIn("--check", stage.command)
            self.assertNotIn("--verify-determinism", stage.command)

    def test_determinism_is_explicit(self) -> None:
        stages = workspace.stages(
            "refresh",
            "python",
            scopes=("graphics",),
            verify_determinism=True,
        )
        self.assertEqual(len(stages), 1)
        self.assertIn("--verify-determinism", stages[0].command)

    def test_changed_plan_skips_documentation_and_targets_authorities(self) -> None:
        documentation = workspace.select_changed(
            (test_changed.ChangedPath("M", "README.md"),)
        )
        self.assertEqual(documentation.scopes, ())

        maps = workspace.select_changed(
            (test_changed.ChangedPath("M", "areas.csv"),)
        )
        self.assertEqual(maps.scopes, ("registry", "integrity"))

        integrity = workspace.select_changed(
            (
                test_changed.ChangedPath(
                    "M", "pipeline/scripts/audit_workspace_integrity.py"
                ),
            )
        )
        self.assertEqual(integrity.scopes, ("integrity",))

    def test_changed_plan_classifies_both_sides_of_rename(self) -> None:
        plan = workspace.select_changed(
            (
                test_changed.ChangedPath(
                    "R100",
                    "docs/renamed.md",
                    "animations/index/path-migrations.json",
                ),
            )
        )
        self.assertEqual(plan.scopes, ("registry", "integrity"))

    def test_run_is_fail_fast_and_uses_workspace_root(self) -> None:
        runner = Mock(side_effect=[None, subprocess.CalledProcessError(9, "integrity")])
        with self.assertRaises(subprocess.CalledProcessError):
            workspace.run(
                "check",
                scopes=("registry", "integrity"),
                runner=runner,
            )
        self.assertEqual(runner.call_count, 2)
        for call in runner.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": workspace.ROOT, "check": True})

    def test_keep_going_runs_every_scope_and_returns_first_failure(self) -> None:
        runner = Mock(
            side_effect=[
                subprocess.CalledProcessError(7, "graphics"),
                None,
                subprocess.CalledProcessError(9, "integrity"),
            ]
        )
        code = workspace.run("check", keep_going=True, runner=runner)
        self.assertEqual(code, 7)
        self.assertEqual(runner.call_count, 3)

    def test_cli_is_plan_only_unless_run_is_explicit(self) -> None:
        args = workspace.parse_args(["refresh", "--changed"])
        self.assertFalse(args.run)
        self.assertFalse(args.verify_determinism)
        explicit = workspace.parse_args(
            ["refresh", "--scope", "registry", "--run"]
        )
        self.assertTrue(explicit.run)
        self.assertTrue(
            workspace.parse_args(
                ["refresh", "--scope", "registry", "--run", "--keep-going"]
            ).keep_going
        )
        with self.assertRaises(SystemExit):
            workspace.parse_args(["refresh", "--scope", "registry", "--keep-going"])
        with self.assertRaises(SystemExit):
            workspace.parse_args(["refresh", "--run"])

    def test_unknown_mode_and_scope_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            workspace.stages("other")
        with self.assertRaises(ValueError):
            workspace.normalize_scopes(("other",))


if __name__ == "__main__":
    unittest.main()
