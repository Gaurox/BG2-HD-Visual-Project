from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import workspace  # noqa: E402


class WorkspaceCommandTests(unittest.TestCase):
    def test_refresh_orders_existing_generators_then_documentation(self) -> None:
        names = [stage.name for stage in workspace.stages("refresh", "python")]
        self.assertEqual(
            names,
            [
                "inventaires graphiques complémentaires",
                "registre global",
                "intégrité physique et index des runs",
                "documentation canonique",
            ],
        )
        commands = [stage.command for stage in workspace.stages("refresh", "python")]
        self.assertIn("build_graphics_inventory.py", commands[0][1])
        self.assertIn("build_global_asset_registry.py", commands[1][1])
        self.assertIn("audit_workspace_integrity.py", commands[2][1])
        for command in commands[:3]:
            self.assertIn("--verify-determinism", command)
            self.assertNotIn("--check", command)

    def test_check_is_read_only_for_all_generators(self) -> None:
        commands = [stage.command for stage in workspace.stages("check", "python")]
        for command in commands[:3]:
            self.assertIn("--verify-determinism", command)
            self.assertIn("--check", command)
        self.assertEqual(
            commands[3],
            ("python", "-m", "unittest", "pipeline.tests.test_repository_docs"),
        )
        after_full = [
            stage.command
            for stage in workspace.stages(
                "check",
                "python",
                verify_determinism=False,
                include_documentation=False,
            )
        ]
        self.assertEqual(len(after_full), 3)
        for command in after_full:
            self.assertIn("--check", command)
            self.assertNotIn("--verify-determinism", command)

    def test_run_is_fail_fast_and_uses_workspace_root(self) -> None:
        runner = Mock(side_effect=[None, subprocess.CalledProcessError(9, "registry")])
        with self.assertRaises(subprocess.CalledProcessError):
            workspace.run("check", runner=runner)
        self.assertEqual(runner.call_count, 2)
        for call in runner.call_args_list:
            self.assertEqual(call.kwargs, {"cwd": workspace.ROOT, "check": True})

    def test_unknown_mode_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            workspace.stages("other")


if __name__ == "__main__":
    unittest.main()
