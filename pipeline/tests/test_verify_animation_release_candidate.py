"""Batch CLI must verify every candidate under one lease and fail closed."""
from contextlib import contextmanager, redirect_stderr, redirect_stdout
import importlib.util
import io
import json
from pathlib import Path
import sys
import types
import unittest
from unittest import mock

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("release_verifier_cli", SCRIPTS / "verify_animation_release_candidate.py")
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)


class BatchVerificationTests(unittest.TestCase):
    def run_batch(self, fail_last=False, targeted=False):
        release = cli.animation_release
        leased = False
        checked = []

        @contextmanager
        def lease():
            nonlocal leased
            leased = True
            try:
                yield
            finally:
                leased = False

        def verify(**kwargs):
            self.assertTrue(leased)
            checked.append(kwargs["area"])
            if fail_last and kwargs["area"] == "AR1235":
                raise release.ReleasePromotionError("corrupted final candidate")
            return {"area": kwargs["area"], "legacy_qa": False}

        original_hash = release.sha256_file
        workflow = types.SimpleNamespace(sha256=lambda p: "hash", _validate_runtime_pack=lambda p: {})
        output = io.StringIO()
        with mock.patch.object(release, "configure_workspace_root"), mock.patch.object(release, "workflow_lock", lease), mock.patch.object(release, "load_json", return_value={"candidates": [{"area": "AR1235"}, {"area": "AR1234"}]}), mock.patch.object(release, "verify_release_candidate", verify), mock.patch.object(release, "workflow_module", return_value=workflow), mock.patch.object(Path, "exists", return_value=False), redirect_stdout(output), redirect_stderr(output):
            scope = ["--area", "AR1234", "--area", "AR1235"] if targeted else ["--all"]
            code = cli.main(["--workspace-root", str(SCRIPTS.parents[1]), "--animation-candidates-path", "candidates.json", *scope, "--json"])
        self.assertFalse(leased)
        self.assertIs(release.sha256_file, original_hash)
        self.assertEqual(checked, ["AR1234", "AR1235"])
        return code, output.getvalue()

    def test_all_candidates_verified_and_cache_released(self):
        code, output = self.run_batch()
        self.assertEqual(code, 0)
        result = json.loads(output)
        self.assertEqual(result["count"], 2)
        self.assertTrue(result["ok"])

    def test_corrupt_last_candidate_fails_whole_batch(self):
        code, output = self.run_batch(fail_last=True)
        self.assertEqual(code, 2)
        self.assertIn("corrupted final candidate", output)
        self.assertNotIn('"ok": true', output)

    def test_targeted_batch_keeps_all_requested_checks(self):
        code, output = self.run_batch(targeted=True)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output)["count"], 2)

    def test_batch_rejects_individual_approval_override(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cli.parse_args(["--workspace-root", ".", "--animation-candidates-path", "candidates.json", "--all", "--animation-qa-approval-override-path", "other.json"])


if __name__ == "__main__":
    unittest.main()
