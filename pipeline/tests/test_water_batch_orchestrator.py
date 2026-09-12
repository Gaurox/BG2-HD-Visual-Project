from __future__ import annotations

import copy
import importlib.util
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


orchestrator = load_module("orchestrate_water_batch", SCRIPTS / "orchestrate_water_batch.py")
seedvr = load_module("run_seedvr_comfyui_water_test", SCRIPTS / "run_seedvr_comfyui.py")


class WaterBatchOrchestratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = json.loads(
            (ROOT / "pipeline/water/family-policy-v1.json").read_text(encoding="utf-8")
        )
        self.registry = json.loads(
            (ROOT / "pipeline/water/route2-registry-v1.json").read_text(encoding="utf-8")
        )

    def test_policy_is_none_and_overlay_mapping_is_total_unique(self) -> None:
        mapping = orchestrator.validate_family_policy(self.policy)
        self.assertEqual(
            self.policy["seedvr"]["new_processing_color_correction_method"], "none"
        )
        self.assertEqual(len(mapping), 17)
        self.assertEqual(mapping["WT5000A"]["id"], "brown-flowing-wt5000")

    def test_route2_registry_is_fail_closed_and_only_approves_reference(self) -> None:
        orchestrator.validate_route2_registry(self.registry)
        self.assertEqual(self.registry["fallback"]["strength"], 0.0)
        self.assertEqual(len(self.registry["entries"]), 1)
        entry = self.registry["entries"][0]
        self.assertEqual(entry["area_variant"], "AR0900:day")
        self.assertEqual(entry["approved_strength"], 1.0)

    def test_exact_reference_matches_but_any_hash_divergence_falls_back_q0(self) -> None:
        entry = self.registry["entries"][0]
        row = {
            "wed": entry["wed"]["resref"],
            "wed_sha256": entry["wed"]["sha256"],
            "grid": entry["wed"]["grid"],
            "all_layers": [{"resref": value} for value in entry["wed"]["overlay_slots"]],
            "base_tis": {
                "resref": entry["base_tis"]["resref"],
                "sha256": entry["base_tis"]["sha256"],
                "tile_count": entry["base_tis"]["tile_count"],
                "tile_dimension": entry["base_tis"]["tile_dimension"],
            },
            "overlay_slot": entry["overlay"]["slot"],
            "overlay_resref": entry["overlay"]["tis_resref"],
            "overlay_tis": {
                "sha256": entry["overlay"]["tis_sha256"],
                "tile_count": entry["overlay"]["tile_count"],
                "tile_dimension": entry["overlay"]["tile_dimension"],
                "pages": [page["resref"] for page in entry["overlay"]["pages"]],
            },
        }
        self.assertEqual(orchestrator.route2_decision(row, self.registry), (1.0, entry["id"]))
        divergent = copy.deepcopy(row)
        divergent["overlay_tis"]["sha256"] = "0" * 64
        self.assertEqual(orchestrator.route2_decision(divergent, self.registry), (0.0, None))

    def test_seedvr_plan_explicitly_requests_none(self) -> None:
        argv = orchestrator.seedvr_argv(
            area="AR0046",
            map_run="water-v1-ar0046",
            preflight="proof.json",
            tile_kind="tuiles-principales",
            split_args=["--split-grid", "2", "2"],
            append=False,
        )
        index = argv.index("--color-correction-method")
        self.assertEqual(argv[index + 1], "none")
        self.assertNotIn("lab", argv)

    def test_seedvr_runtime_override_changes_copy_not_approved_source(self) -> None:
        workflow_path = ROOT / "pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json"
        source = json.loads(workflow_path.read_text(encoding="utf-8"))
        runtime = copy.deepcopy(source)
        summary = seedvr.apply_runtime_overrides(
            runtime, scale=4, color_correction_method="none"
        )
        self.assertEqual(summary["color_correction_method"], "none")
        self.assertEqual(seedvr.workflow_summary(source)["color_correction_method"], "lab")


if __name__ == "__main__":
    unittest.main()
