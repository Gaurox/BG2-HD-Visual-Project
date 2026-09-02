from __future__ import annotations

import queue
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

    def test_keep_going_attempts_every_step_and_reports_all_failures(self) -> None:
        steps = tuple(
            progress_ui.ExecutionStep("tests", "python", label, (label,))
            for label in ("one", "two", "three")
        )
        codes = iter((3, 0, 5))

        class Process:
            stdout: tuple[str, ...] = ()

            def __init__(self, code: int) -> None:
                self.code = code

            def wait(self) -> int:
                return self.code

        calls: list[str] = []

        def popen(argv: tuple[str, ...], **_kwargs: object) -> Process:
            calls.append(argv[0])
            return Process(next(codes))

        events: queue.Queue[tuple[object, ...]] = queue.Queue()
        progress_ui.run_execution_steps(
            steps,
            events,
            keep_going=True,
            popen_factory=popen,
        )
        emitted: list[tuple[object, ...]] = []
        while not events.empty():
            emitted.append(events.get_nowait())
        self.assertEqual(calls, ["one", "two", "three"])
        self.assertEqual([event[0] for event in emitted].count("failed"), 2)
        terminal = emitted[-1]
        self.assertEqual(terminal[0], "finished-with-failures")
        self.assertEqual([failure[1] for failure in terminal[1]], ["one", "three"])

    def test_default_execution_stops_on_first_failure(self) -> None:
        steps = (
            progress_ui.ExecutionStep("tests", "python", "one", ("one",)),
            progress_ui.ExecutionStep("tests", "python", "two", ("two",)),
        )

        class Process:
            stdout: tuple[str, ...] = ()

            @staticmethod
            def wait() -> int:
                return 4

        calls: list[str] = []

        def popen(argv: tuple[str, ...], **_kwargs: object) -> Process:
            calls.append(argv[0])
            return Process()

        events: queue.Queue[tuple[object, ...]] = queue.Queue()
        progress_ui.run_execution_steps(steps, events, popen_factory=popen)
        emitted: list[tuple[object, ...]] = []
        while not events.empty():
            emitted.append(events.get_nowait())
        self.assertEqual(calls, ["one"])
        self.assertEqual(emitted[-1][0], "failed")
        self.assertFalse(emitted[-1][3])


if __name__ == "__main__":
    unittest.main()
