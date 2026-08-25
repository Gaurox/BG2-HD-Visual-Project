from __future__ import annotations

import importlib.util
from pathlib import Path
import struct
import sys
import tempfile
import unittest

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "pipeline" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location(
    "creature_sprite_x2_aa", SCRIPTS / "run_creature_sprite_x2_aa.py"
)
assert SPEC and SPEC.loader
aa = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = aa
SPEC.loader.exec_module(aa)


class CreatureSpriteX2AntialiasTests(unittest.TestCase):
    def test_scalepix_integer_blends_include_transparent_rules(self) -> None:
        self.assertEqual(aa.interpolate_pixel(0xFF000000, 0xFFFFFFFF, 1), 0xFF3F3F3F)
        self.assertEqual(aa.interpolate_pixel(0x00010203, 0xFFABCDEF, 1), 0x3FABCDEF)
        self.assertEqual(aa.interpolate_pixel(0xFF123456, 0x00000000, 1), 0xBF123456)
        sequential = aa.interpolate_pixel(
            aa.interpolate_pixel(0xFF000000, 0xFFFFFFFF, 3), 0xFFFFFFFF, 3
        )
        self.assertEqual(sequential, 0xFFEFEFEF)

    def test_recipe_stream_preserves_order_and_source_indices(self) -> None:
        payload = aa.encode_recipes(
            [(3, ((156, 1), (204, 3))), (9, ((0, 2),))], 16
        )
        self.assertEqual(struct.unpack_from("<I", payload, 0)[0], 2)
        self.assertEqual(struct.unpack_from("<IBBB", payload, 4), (3, 2, 156, 1))
        self.assertIn(bytes((204, 3)), payload)
        with self.assertRaises(RuntimeError):
            aa.encode_recipes([(3, ((1, 1),)), (3, ((2, 1),))], 16)

    def test_v4_registry_inspector_is_separate_from_v3(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / aa.REGISTRY_FILENAME
            payload = bytearray(aa.REGISTRY_MAGIC)
            payload.extend(struct.pack("<IIII", 4, 2, 1, 0x6102))
            payload.extend(b"CDMB1A1\0")
            payload.extend(bytes(32))
            payload.extend(struct.pack("<II", 1, 1))
            payload.extend(struct.pack("<HHhhB3xI", 1, 1, 0, 0, 0, 4))
            representatives = np.full(256, 0xFFFF, dtype="<u2")
            representatives[1] = 0
            payload.extend(representatives.tobytes())
            payload.extend(bytes((1, 1, 1, 1)))
            recipes = aa.encode_recipes([(0, ((1, 2),))], 4)
            payload.extend(struct.pack("<I", len(recipes)))
            payload.extend(recipes)
            payload.extend(struct.pack("<II", 1, 0))
            registry.write_bytes(payload)
            info = aa.inspect_registry(registry)
            self.assertEqual(info["registry_version"], 4)
            self.assertEqual(info["index_bytes"], 4)
            self.assertEqual(info["recipe_count"], 1)
            self.assertEqual(info["operation_count"], 1)

    def test_aa_adapter_and_transaction_scripts_are_dedicated(self) -> None:
        adapter = (SCRIPTS / "xbr2x_antialias_batch.js").read_text(encoding="utf-8")
        legacy = (SCRIPTS / "xbr2x_batch.js").read_text(encoding="utf-8")
        self.assertIn("xbr_blend: {checked: true}", adapter)
        self.assertIn("xbr_blend: {checked: false}", legacy)
        installer = (SCRIPTS / "Install-CreatureSprite-AA-Variant-Test.ps1").read_text(
            encoding="utf-8"
        )
        restorer = (SCRIPTS / "Restore-CreatureSprite-AA-Variant-Test.ps1").read_text(
            encoding="utf-8"
        )
        self.assertIn("parent_active_tests", installer)
        self.assertIn("EnableCreatureSpriteLinearFiltering", installer)
        self.assertIn("installed-pending-qa", installer)
        self.assertIn("RecoverInterrupted", restorer)
        self.assertIn("VerifyOnly", restorer)
        self.assertIn("restore-preflight-verified", restorer)
        self.assertIn("Add-Member -NotePropertyName 'restore_started_at_utc'", restorer)
        self.assertIn("Add-Member -NotePropertyName 'restored_at_utc'", restorer)
        self.assertIn("original_sha256", restorer)


if __name__ == "__main__":
    unittest.main()
