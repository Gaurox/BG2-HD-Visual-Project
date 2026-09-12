from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "test_changed_script", ROOT / "pipeline" / "scripts" / "test_changed.py"
)
assert SPEC and SPEC.loader
selector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(selector)


class TestChangedTests(unittest.TestCase):
    def test_only_direct_python_test_matches_are_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tests = root / "pipeline" / "tests"
            tests.mkdir(parents=True)
            (tests / "test_tool.py").write_text("", encoding="utf-8")
            with mock.patch.object(selector, "ROOT", root):
                self.assertEqual(
                    selector.modules_for(
                        [
                            "pipeline/scripts/tool.py",
                            "areas.csv",
                            "releases/BG2-HD-Upscale/manifests/content.json",
                        ]
                    ),
                    ["pipeline.tests.test_tool"],
                )

    def test_explicit_test_file_is_selected(self) -> None:
        self.assertEqual(
            selector.modules_for(["pipeline/tests/test_animation_release.py"]),
            ["pipeline.tests.test_animation_release"],
        )

    def test_paths_cannot_escape_repository(self) -> None:
        with self.assertRaises(ValueError):
            selector.normalize("../outside.py")


if __name__ == "__main__":
    unittest.main()
