"""Keep default renderer builds on the current water contract; fail closed on drift."""
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "water_registry_default_generator",
    ROOT / "engine/InfinityEngine-Enhancer/source-patchee/tools/generate_water_route2_registry.py",
)
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


class WaterRegistryDefaultTests(unittest.TestCase):
    def test_workspace_default_retains_ar3000_paving_and_opacity(self):
        output = GENERATOR.generate(GENERATOR.default_input())
        self.assertIn("kRegistryVersion = 3", output)
        for alias in ("YHTA30", "YHTB30", "YHTC30", "YHTD30",
                      "YHTA30R", "YHTB30R", "YHTC30R", "YHTD30R"):
            self.assertIn(f'resref_array("{alias}")', output)
        self.assertIn(", 128, 160}", output)

    def test_pointer_hash_drift_never_falls_back_to_legacy(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            registry = workspace / "registry.json"
            registry.write_text('{"version":3}\r\n', encoding="utf-8", newline="")
            pointer = workspace / "pipeline/water/route2-registry-current.json"
            pointer.parent.mkdir(parents=True)
            pointer.write_text(json.dumps({
                "schema": "bg2-water-route2-registry-current-v1",
                "registry": {"path": "registry.json", "sha256_lf": hashlib.sha256(
                    b'{"version":3}\n').hexdigest()},
            }), encoding="utf-8")
            self.assertEqual(GENERATOR.default_input(workspace), registry)
            registry.write_text('{"version":2}\n', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "divergent"):
                GENERATOR.default_input(workspace)

    def test_standalone_without_pointer_keeps_explicit_legacy_contract(self):
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            self.assertEqual(GENERATOR.default_input(workspace, workspace),
                             workspace / "assets/water-route2/registry-v2.json")


if __name__ == "__main__":
    unittest.main()
