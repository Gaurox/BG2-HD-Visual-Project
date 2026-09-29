"""Completeness tests for the one-map-at-a-time liquid ingame tracker."""

import copy
import json
import sys
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
from audit_water_ingame_tracking import validate_tracking


class WaterIngameTrackingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            (ROOT / "pipeline/water/ingame-map-tracking-v1.json").read_text(encoding="utf-8")
        )
        cls.matrix = json.loads(
            (ROOT / "pipeline/water/manifests/liquid-target-matrix-v1.json").read_text(
                encoding="utf-8"
            )
        )
        cls.release = json.loads(
            (ROOT / "pipeline/water/release-tracking-v1.json").read_text(encoding="utf-8")
        )

    def validate(self, data):
        return validate_tracking(
            data, self.matrix, self.release, ROOT, verify_files=False
        )

    def test_current_tracker_is_exhaustive(self):
        errors, summary = self.validate(self.data)
        self.assertEqual(errors, [])
        self.assertTrue(summary["complete_inventory"])
        self.assertEqual(summary["maps"], 67)
        self.assertEqual(summary["overlay_targets"], 98)
        self.assertEqual(summary["night_maps"], 7)
        self.assertIsNone(summary["active_map_id"])

    def test_missing_map_is_rejected(self):
        data = copy.deepcopy(self.data)
        data["maps"] = [item for item in data["maps"] if item["wed"] != "AR0500N"]
        errors, _ = self.validate(data)
        self.assertTrue(any("missing map from tracking: AR0500N" in error for error in errors))

    def test_overlay_omission_is_rejected(self):
        data = copy.deepcopy(self.data)
        target = next(item for item in data["maps"] if item["wed"] == "AR3000")
        target["overlays"].pop()
        errors, _ = self.validate(data)
        self.assertTrue(any("overlays disagree with matrix" in error for error in errors))

    def test_release_selection_link_omission_is_rejected(self):
        data = copy.deepcopy(self.data)
        target = next(item for item in data["maps"] if item["wed"] == "AR0046N")
        target["release_target_ids"] = []
        errors, _ = self.validate(data)
        self.assertTrue(any("release target absent" in error for error in errors))

    def test_only_one_map_can_be_active(self):
        data = copy.deepcopy(self.data)
        first, second = data["maps"][1:3]
        first["work_state"] = "active"
        second["work_state"] = "active"
        data["workflow"]["active_map_id"] = first["id"]
        errors, _ = self.validate(data)
        self.assertTrue(any("single active map" in error for error in errors))

    def test_review_campaign_covers_every_active_liquid_map(self):
        errors, summary = self.validate(self.data)
        self.assertEqual(errors, [])
        self.assertEqual(self.data["campaign"]["treatment"]["state"], "all-treated")
        q = summary["review_states"]["q"]
        self.assertEqual(q.get("pending", 0) + q.get("validated", 0), 63)
        self.assertEqual(sum(summary["review_states"]["night"].values()), 67)

    def test_rain_review_needs_a_weather_area(self):
        data = copy.deepcopy(self.data)
        target = next(item for item in data["maps"] if not item["review"]["rain"]["weather"])
        target["review"]["rain"]["state"] = "pending"
        errors, _ = self.validate(data)
        self.assertTrue(any("rain review applies only to weather areas" in error for error in errors))

    def test_night_review_only_on_night_weds(self):
        data = copy.deepcopy(self.data)
        target = next(item for item in data["maps"] if item["variant"] != "night")
        target["review"]["night"]["state"] = "pending"
        errors, _ = self.validate(data)
        self.assertTrue(any("night review applies only to night WEDs" in error for error in errors))

    def test_validated_review_needs_evidence(self):
        data = copy.deepcopy(self.data)
        target = next(item for item in data["maps"] if item["review"]["q"]["state"] == "pending")
        target["review"]["q"]["state"] = "validated"
        errors, _ = self.validate(data)
        self.assertTrue(any("validated q review needs evidence" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
