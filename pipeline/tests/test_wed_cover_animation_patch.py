from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_wed_cover_animation_patch as patcher  # noqa: E402


def make_wed(flags: tuple[int, ...] = (0x05, 0x09)) -> bytes:
    secondary_offset = 0x2C
    polygon_offset = 0x40
    data = bytearray(polygon_offset + len(flags) * patcher.POLYGON_SIZE)
    data[:8] = patcher.WED_SIGNATURE
    struct.pack_into("<I", data, 0x14, secondary_offset)
    struct.pack_into("<IIIII", data, secondary_offset, len(flags), polygon_offset, 0, 0, 0)
    for index, value in enumerate(flags):
        data[polygon_offset + index * patcher.POLYGON_SIZE + patcher.POLYGON_FLAG_OFFSET] = value
    return bytes(data)


class WedCoverAnimationPatchTests(unittest.TestCase):
    def test_adds_only_cover_animation_flag_byte(self) -> None:
        source = make_wed()
        output, changes = patcher.add_cover_animations(source, [(0, 0x05)])

        expected_offset = 0x40 + patcher.POLYGON_FLAG_OFFSET
        self.assertEqual(output[expected_offset], 0x0D)
        self.assertEqual(
            [index for index, (before, after) in enumerate(zip(source, output)) if before != after],
            [expected_offset],
        )
        self.assertEqual(changes[0]["polygon_index"], 0)
        self.assertEqual(changes[0]["original_flags_hex"], "0x05")
        self.assertEqual(changes[0]["patched_flags_hex"], "0x0D")

    def test_rejects_changed_source_flags(self) -> None:
        with self.assertRaisesRegex(ValueError, "flags 0x05, 0x01 attendus"):
            patcher.add_cover_animations(make_wed(), [(0, 0x01)])

    def test_rejects_already_covered_polygon(self) -> None:
        with self.assertRaisesRegex(ValueError, "déjà actif"):
            patcher.add_cover_animations(make_wed(), [(1, 0x09)])

    def test_rejects_duplicate_or_out_of_range_index(self) -> None:
        with self.assertRaisesRegex(ValueError, "plusieurs fois"):
            patcher.add_cover_animations(make_wed(), [(0, 0x05), (0, 0x05)])
        with self.assertRaisesRegex(ValueError, "hors table"):
            patcher.add_cover_animations(make_wed(), [(2, 0x05)])

    def test_rejects_invalid_wed(self) -> None:
        with self.assertRaisesRegex(ValueError, "signature"):
            patcher.add_cover_animations(b"not a WED", [(0, 0x05)])


if __name__ == "__main__":
    unittest.main()
