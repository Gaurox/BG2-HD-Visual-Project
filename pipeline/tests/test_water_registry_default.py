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
    def test_declared_registry_and_dll_fingerprint_must_match(self):
        path = GENERATOR.default_input()
        with tempfile.TemporaryDirectory() as directory:
            dll = Path(directory) / 'test.dll'
            expected = GENERATOR.build_contract(path)
            dll.write_bytes(b'MZfixture' + expected.encode('ascii') + b'\0')
            self.assertEqual(GENERATOR.verify_dll_contract(dll, path), expected)
            dll.write_bytes(b'MZfixtureIEE_WATER_ROUTE2_V1:' + b'0' * 64 + b':2:1\0')
            with self.assertRaisesRegex(RuntimeError, 'fingerprint'):
                GENERATOR.verify_dll_contract(dll, path)

    def test_unidentified_dll_cannot_be_registered_as_current(self):
        with tempfile.TemporaryDirectory() as directory:
            dll = Path(directory) / 'test.dll'
            dll.write_bytes(b'MZlegacy-without-proof')
            with self.assertRaisesRegex(RuntimeError, 'fingerprint'):
                GENERATOR.verify_dll_contract(dll, GENERATOR.default_input())

    def test_cached_legacy_override_cannot_bypass_current_authority(self):
        stale = GENERATOR.SOURCE_ROOT / "assets/water-route2/registry-v2.json"
        with self.assertRaisesRegex(RuntimeError, "override differs"):
            GENERATOR.resolve_input(stale)

    def test_explicit_water_authoring_can_choose_a_different_registry(self):
        historical = GENERATOR.SOURCE_ROOT / "assets/water-route2/registry-v2.json"
        self.assertEqual(GENERATOR.resolve_input(historical, allow_registry_change=True), historical.resolve())

    def test_current_build_embeds_the_registry_fingerprint(self):
        path = GENERATOR.default_input()
        output = GENERATOR.generate(path)
        self.assertIn(f"IEE_WATER_ROUTE2_V1:{GENERATOR.registry_sha256_lf(path)}:3:188", output)

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
