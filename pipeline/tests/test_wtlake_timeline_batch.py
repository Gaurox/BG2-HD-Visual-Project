from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline/scripts"
ENGINE = ROOT / "engine/InfinityEngine-Enhancer/source-patchee"
sys.path.insert(0, str(SCRIPTS))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


batch = load_module("build_wtlake_timeline_batch_test", SCRIPTS / "build_wtlake_timeline_batch.py")
generator = load_module(
    "generate_water_route2_registry_test",
    ENGINE / "tools/generate_water_route2_registry.py",
)


class WtlakeTimelineBatchTests(unittest.TestCase):
    def test_selection_is_exactly_wtlake_q070(self) -> None:
        path = ROOT / "pipeline/water/manifests/wtlake-timeline30-q070-20260912-v1.json"
        selection = json.loads(path.read_text(encoding="utf-8"))
        targets = selection["targets"]
        self.assertEqual([item["wed"] for item in targets], list(batch.AREAS))
        self.assertEqual(selection["parameters"]["route2_strength"], 0.7)
        self.assertEqual(selection["parameters"]["timeline_frames"], 36)
        self.assertEqual(selection["parameters"]["native_fps"], 15.0)
        self.assertEqual(selection["parameters"]["render_fps"], 30.0)
        self.assertEqual(selection["parameters"]["new_seedvr_color_correction_method"], "none")
        self.assertEqual(
            [item["wed"] for item in targets if item["state"] == "corrected-validated-reference"],
            ["AR0900"],
        )

    def test_v3_registry_retains_parent_and_generates_fail_closed_table(self) -> None:
        active = ENGINE / "assets/water-route2/registry-v2.json"
        _child, resolved = generator.load_registry(active)
        entry = resolved["entries"][0]
        registry = {
            "schema": "bg2-water-route2-registry-v3",
            "version": 3,
            "parent": {
                "path": "engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json",
                "sha256": hashlib.sha256(active.read_bytes()).hexdigest().upper(),
            },
            "entries": [entry],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry-v3.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            generated = generator.generate(path)
        self.assertIn("kRegistryVersion = 3", generated)
        self.assertIn("std::array<RegistryEntry, 1>", generated)
        self.assertIn("AR0900", generated)

    def test_v3_registry_rejects_loss_of_parent_identity(self) -> None:
        active = ENGINE / "assets/water-route2/registry-v2.json"
        registry = {
            "schema": "bg2-water-route2-registry-v3",
            "version": 3,
            "parent": {
                "path": "engine/InfinityEngine-Enhancer/source-patchee/assets/water-route2/registry-v2.json",
                "sha256": hashlib.sha256(active.read_bytes()).hexdigest().upper(),
            },
            "entries": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry-v3.json"
            path.write_text(json.dumps(registry), encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "retain every active parent id"):
                generator.load_registry(path)


if __name__ == "__main__":
    unittest.main()
