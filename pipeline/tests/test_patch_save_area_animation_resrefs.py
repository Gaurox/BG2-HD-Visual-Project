from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_fused_area_animation_carrier as carrier  # noqa: E402
import patch_save_area_animation_resrefs as patcher  # noqa: E402


def make_area() -> bytes:
    offset = 0x100
    payload = bytearray(offset + 4 * carrier.ARE_ANIMATION_SIZE)
    payload[:8] = b"AREAV1.0"
    struct.pack_into("<I", payload, 0xAC, 4)
    struct.pack_into("<I", payload, 0xB0, offset)
    for index, (resref, position, flags) in enumerate((
        ("OTHER", (0, 0), 0),
        ("AM2805B", (483, 368), 0x1151),
        ("AM2805B", (483, 368), 0x1000),
        ("AM2805C", (483, 553), 0x1151),
    )):
        entry = offset + index * carrier.ARE_ANIMATION_SIZE
        payload[entry:entry + 32] = f"entry-{index}".encode().ljust(32, b"\0")
        struct.pack_into("<hh", payload, entry + 0x20, *position)
        payload[entry + 0x28:entry + 0x30] = resref.encode().ljust(8, b"\0")
        struct.pack_into("<I", payload, entry + 0x34, flags)
    return bytes(payload)


def make_sav(entries: list[tuple[str, bytes]]) -> bytes:
    output = bytearray(patcher.SAV_SIGNATURE)
    for name, raw in entries:
        name_bytes = name.encode() + b"\0"
        compressed = zlib.compress(raw)
        output.extend(struct.pack("<I", len(name_bytes)))
        output.extend(name_bytes)
        output.extend(struct.pack("<II", len(raw), len(compressed)))
        output.extend(compressed)
    return bytes(output)


class PatchSaveAreaAnimationResrefsTests(unittest.TestCase):
    def test_patch_is_transactional_and_preserves_other_entries(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            save = root / "save"
            backup = root / "backup"
            save.mkdir()
            (save / "BALDUR.SAV").write_bytes(make_sav([
                ("AR2804.ARE", make_area()), ("WORLD.MAP", b"unchanged")
            ]))
            (save / "BALDUR.GAM").write_bytes(b"game")

            report = patcher.patch_save(
                save, backup, area="AR2804", carrier_resref="AM28ADD",
                null_resref="AM28NUL", carrier_occurrence=1, null_occurrence=3,
                write=True,
            )

            self.assertEqual(report["status"], "installed")
            entries = patcher.parse_sav((save / "BALDUR.SAV").read_bytes())
            area = next(entry["raw"] for entry in entries if entry["name"] == "AR2804.ARE")
            self.assertEqual(carrier.are_occurrence(area, 1)["resref"], "AM28ADD")
            self.assertEqual(carrier.are_occurrence(area, 3)["resref"], "AM28NUL")
            self.assertEqual(next(entry["raw"] for entry in entries
                                  if entry["name"] == "WORLD.MAP"), b"unchanged")
            self.assertTrue((backup / "BALDUR.SAV").is_file())
            self.assertTrue((backup / "patch-transaction.json").is_file())


if __name__ == "__main__":
    unittest.main()
