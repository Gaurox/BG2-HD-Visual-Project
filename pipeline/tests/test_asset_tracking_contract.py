from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import asset_tracking_contract as contract  # noqa: E402


def valid_record() -> dict:
    return {
        "$schema": "docs/asset-tracking-record.schema.json",
        "schema_version": 1,
        "asset_id": "maps:AR0404:day",
        "domain": "maps",
        "asset_type": "area-map",
        "canonical_source": {
            "path": "areas.csv",
            "locator": "csv:area_id=AR0404;variant=day",
        },
        "states": {
            "source": "extracted",
            "production": "verified",
            "qa": "passed",
            "installation": "installed",
            "release": "approved",
        },
        "provenance": {
            "state": "verified",
            "evidence": [
                {
                    "path": "areas.csv",
                    "locator": "csv:area_id=AR0404;field=build",
                    "sha256": "A" * 64,
                }
            ],
        },
        "selections": [
            {
                "role": "build",
                "id": "AR0404-x4",
                "source": {
                    "path": "areas.csv",
                    "locator": "csv:area_id=AR0404;field=build",
                },
            }
        ],
        "legacy": [
            {
                "field": "status",
                "value": "validated-installed",
                "mapping": "maps.areas.status.v1",
            }
        ],
        "adapter": "maps.areas.v1",
        "observed_at_utc": "2026-08-30T12:00:00Z",
    }


class AssetTrackingContractTests(unittest.TestCase):
    def test_schema_and_python_enums_stay_aligned(self) -> None:
        schema = json.loads(
            (ROOT / "docs" / "asset-tracking-record.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], contract.SCHEMA_VERSION)
        self.assertEqual(tuple(schema["properties"]["domain"]["enum"]), contract.DOMAINS)
        schema_states = schema["properties"]["states"]["properties"]
        for axis, values in contract.STATE_VALUES.items():
            self.assertEqual(tuple(schema_states[axis]["enum"]), values)
        self.assertEqual(
            tuple(schema["properties"]["provenance"]["properties"]["state"]["enum"]),
            contract.PROVENANCE_VALUES,
        )

    def test_valid_record_is_accepted(self) -> None:
        self.assertEqual(contract.validate_record(valid_record()), [])
        contract.assert_valid_record(valid_record())

    def test_combined_map_status_is_split_without_release_inference(self) -> None:
        self.assertEqual(
            contract.map_legacy_status("maps.areas.status.v1", "source-pending"),
            {"source": "available", "production": "not-started"},
        )
        self.assertEqual(
            contract.map_legacy_status("maps.areas.status.v1", "installed-pending-qa"),
            {
                "production": "produced",
                "qa": "pending",
                "installation": "installed",
            },
        )
        projected = contract.map_legacy_status(
            "maps.areas.status.v1", "validated-installed"
        )
        self.assertEqual(projected["qa"], "passed")
        self.assertNotIn("release", projected)

    def test_animation_spatial_validation_does_not_imply_temporal_qa(self) -> None:
        self.assertEqual(
            contract.map_legacy_status(
                "animations.index.upscale-status.v1", "validé-x4"
            ),
            {"production": "verified"},
        )
        self.assertEqual(
            contract.map_legacy_status(
                "animations.index.upscale-status.v1", "validé-natif"
            ),
            {"production": "verified"},
        )
        self.assertEqual(
            contract.map_legacy_status(
                "animations.qa-approval.status.v1", "accepted"
            ),
            {"qa": "passed"},
        )

    def test_sprite_readiness_does_not_imply_qa_or_installation(self) -> None:
        self.assertEqual(
            contract.map_legacy_status("sprites.index.pipeline-ready.v1", "yes"),
            {"production": "ready"},
        )
        self.assertEqual(
            contract.map_legacy_status(
                "sprites.installation.status.v1", "installed-pending-qa"
            ),
            {"qa": "pending", "installation": "installed"},
        )

    def test_unknown_legacy_status_fails_closed(self) -> None:
        with self.assertRaises(contract.ContractError):
            contract.map_legacy_status("maps.areas.status.v1", "probably-valid")

    def test_combined_status_is_not_a_valid_common_axis_value(self) -> None:
        record = valid_record()
        record["states"]["qa"] = "installed-pending-qa"
        self.assertTrue(
            any("states.qa" in error for error in contract.validate_record(record))
        )

    def test_release_progress_requires_qa_provenance_and_selection(self) -> None:
        record = valid_record()
        record["states"]["qa"] = "pending"
        record["provenance"] = {"state": "partial", "evidence": []}
        record["selections"] = []
        errors = contract.validate_record(record)
        self.assertTrue(any("requires qa passed" in error for error in errors))
        self.assertTrue(any("requires complete provenance" in error for error in errors))
        self.assertTrue(any("requires an explicit selection" in error for error in errors))

    def test_verified_provenance_requires_hashes(self) -> None:
        record = deepcopy(valid_record())
        del record["provenance"]["evidence"][0]["sha256"]
        self.assertTrue(
            any("sha256 on every evidence" in error for error in contract.validate_record(record))
        )

    def test_authority_paths_are_repository_relative(self) -> None:
        record = valid_record()
        record["canonical_source"]["path"] = "G:\\AI\\BG2_Upscale\\areas.csv"
        self.assertTrue(
            any("repository-relative POSIX" in error for error in contract.validate_record(record))
        )


if __name__ == "__main__":
    unittest.main()
