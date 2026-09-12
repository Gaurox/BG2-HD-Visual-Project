"""Structural tests for the water release-preparation authority."""

import copy
import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
from audit_water_release_tracking import release_gate_reasons, validate_tracking


class WaterReleaseTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            (ROOT / "pipeline/water/release-tracking-v1.json").read_text(encoding="utf-8")
        )

    def test_current_authority_is_structurally_valid(self):
        errors, summary = validate_tracking(
            self.data, ROOT, verify_files=False, verify_git=False
        )
        self.assertEqual(errors, [])
        self.assertEqual(summary["targets"], 18)
        self.assertFalse(summary["release_candidate_ready"])

    def test_duplicate_target_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["targets"].append(copy.deepcopy(data["targets"][0]))
        errors, _ = validate_tracking(data, ROOT, verify_files=False, verify_git=False)
        self.assertTrue(any("duplicate target" in error for error in errors))

    def test_tracking_cannot_approve_release(self):
        data = copy.deepcopy(self.data)
        data["targets"][0]["release_state"] = "approved"
        errors, _ = validate_tracking(data, ROOT, verify_files=False, verify_git=False)
        self.assertTrue(any("cannot approve release" in error for error in errors))

    def test_release_gate_reports_expected_open_work(self):
        reasons = release_gate_reasons(self.data)
        self.assertTrue(any("AR0512" in reason for reason in reasons))
        self.assertTrue(any(reason.startswith("runtime:") for reason in reasons))


if __name__ == "__main__":
    unittest.main()
