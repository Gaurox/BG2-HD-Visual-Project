from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import progress_ui  # noqa: E402


class ProgressUiTests(unittest.TestCase):
    def test_planning_choices_remain_independent_and_plan_only(self) -> None:
        requests = progress_ui.planning_requests(
            "targeted",
            "all",
            verify_determinism=True,
            python="python-test",
        )
        self.assertEqual([request.source for request in requests], ["tests", "reconstructions"])
        self.assertEqual(
            requests[0].argv,
            (
                "python-test",
                str(progress_ui.TEST_PLANNER),
                "--targeted",
                "--json",
            ),
        )
        self.assertIn("--scope", requests[1].argv)
        self.assertIn("all", requests[1].argv)
        self.assertIn("--verify-determinism", requests[1].argv)
        self.assertNotIn("--run", requests[0].argv + requests[1].argv)

    def test_no_reconstruction_omits_determinism_and_workspace_plan(self) -> None:
        requests = progress_ui.planning_requests(
            "full",
            "none",
            verify_determinism=True,
            python="python-test",
        )
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].source, "tests")
        self.assertIn("--full", requests[0].argv)
        self.assertNotIn("--verify-determinism", requests[0].argv)

    def test_steps_are_taken_from_canonical_payload_without_rewriting(self) -> None:
        payload = {
            "commands": [
                {
                    "scope": "registry",
                    "label": "registre global",
                    "argv": ["python", "build_global_asset_registry.py"],
                }
            ]
        }
        steps = progress_ui.steps_from_payload(payload, "reconstructions")
        self.assertEqual(
            steps,
            (
                progress_ui.ExecutionStep(
                    "reconstructions",
                    "registry",
                    "registre global",
                    ("python", "build_global_asset_registry.py"),
                ),
            ),
        )

    def test_invalid_command_is_rejected_before_execution(self) -> None:
        with self.assertRaises(ValueError):
            progress_ui.steps_from_payload({"commands": [{"argv": []}]}, "tests")
        with self.assertRaises(ValueError):
            progress_ui.steps_from_payload({}, "tests")

    def test_summaries_expose_scope_and_determinism(self) -> None:
        self.assertEqual(
            progress_ui.summarize_payload(
                {
                    "scopes": ["registry", "integrity"],
                    "verify_determinism": True,
                },
                "reconstructions",
            ),
            "Reconstructions : registry, integrity ; déterminisme ×2",
        )

    def test_duration_format_stays_compact(self) -> None:
        self.assertEqual(progress_ui.ProgressApplication._format_duration(0), "00:00")
        self.assertEqual(progress_ui.ProgressApplication._format_duration(125), "02:05")
        self.assertEqual(progress_ui.ProgressApplication._format_duration(3661), "01:01:01")


if __name__ == "__main__":
    unittest.main()
