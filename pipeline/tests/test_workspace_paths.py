from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import workspace_paths  # noqa: E402


class WorkspacePathTests(unittest.TestCase):
    def make_root(self, directory: str) -> Path:
        root = Path(directory)
        (root / "config").mkdir()
        (root / "config/workspace-paths.json").write_text(
            json.dumps(
                {
                    "local_override": "config/workspace-paths.local.json",
                    "paths": {
                        "tool": {
                            "environment": "BG2_TEST_TOOL",
                            "legacy_environments": ["BG2_TEST_TOOL_LEGACY"],
                            "kind": "file",
                        },
                    },
                    "services": {
                        "endpoint": {"environment": "BG2_TEST_ENDPOINT", "default": "local"},
                    },
                }
            ),
            encoding="utf-8",
        )
        return root

    def test_environment_overrides_local_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            local_tool = root / "local.exe"
            env_tool = root / "env.exe"
            local_tool.touch()
            env_tool.touch()
            (root / "config/workspace-paths.local.json").write_text(
                json.dumps({"paths": {"tool": str(local_tool)}}), encoding="utf-8"
            )
            self.assertEqual(
                workspace_paths.get_path(
                    "tool", required=True, root=root, environ={"BG2_TEST_TOOL": str(env_tool)}
                ),
                env_tool,
            )

    def test_config_reference_and_relative_legacy_paths_resolve(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            tool = root / "tool.exe"
            tool.touch()
            environment = {"BG2_TEST_TOOL": str(tool)}
            self.assertEqual(
                workspace_paths.resolve_path_reference(
                    "config://tool", required=True, root=root, environ=environment
                ),
                tool,
            )
            self.assertEqual(
                workspace_paths.resolve_path_reference("relative/file", root=root),
                root / "relative/file",
            )

    def test_legacy_environment_name_remains_supported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            tool = root / "legacy.exe"
            tool.touch()
            self.assertEqual(
                workspace_paths.get_path(
                    "tool", required=True, root=root, environ={"BG2_TEST_TOOL_LEGACY": str(tool)}
                ),
                tool,
            )

    def test_missing_required_path_has_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            with self.assertRaisesRegex(workspace_paths.WorkspacePathError, "BG2_TEST_TOOL"):
                workspace_paths.get_path("tool", required=True, root=root, environ={})

    def test_service_falls_back_to_tracked_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = self.make_root(directory)
            self.assertEqual(
                workspace_paths.get_service("endpoint", root=root, environ={}),
                "local",
            )


if __name__ == "__main__":
    unittest.main()
