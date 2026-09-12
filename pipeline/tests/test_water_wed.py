"""Synthetic regression fixtures: no game files or existing run dependencies."""
import struct
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from water_wed import replace_overlay_timeline, validate_polygons


def fixture():
    data = bytearray(320)
    data[:8] = b"WED V1.3"
    struct.pack_into("<6I", data, 8, 2, 1, 32, 200, 240, 280)
    struct.pack_into("<HH8sHHII", data, 32, 1, 1, b"ARTEST", 1, 0, 90, 102)
    struct.pack_into("<HH8sHHII", data, 56, 1, 1, b"WTLAKE", 6, 0, 104, 114)
    struct.pack_into("<HHHB3x", data, 90, 0, 1, 65535, 2)
    struct.pack_into("<H", data, 102, 0)
    struct.pack_into("<HHHB3x", data, 104, 0, 6, 65535, 0)
    struct.pack_into("<6H", data, 114, *range(6))
    struct.pack_into("<5I", data, 200, 0, 220, 300, 284, 288)
    struct.pack_into("<8s5H2I", data, 240, b"DOOR01", 1, 0, 1, 1, 0, 220, 238)
    struct.pack_into("<II", data, 220, 0, 2)
    struct.pack_into("<4H", data, 300, 10, 20, 30, 40)
    return bytes(data)


class WaterWedTests(unittest.TestCase):
    def test_door_table_and_point_list_relocate_together(self):
        before = fixture()
        after = replace_overlay_timeline(before, 1, 36)
        self.assertEqual(struct.unpack_from("<I", after, 24)[0], 300)
        self.assertEqual(struct.unpack_from("<II", after, 318), (280, 298))
        self.assertEqual(after[360:368], before[300:308])
        self.assertEqual(validate_polygons(after)["object_polygons"], 1)

    def test_growing_then_restoring_recovers_exact_file(self):
        before = fixture()
        after = replace_overlay_timeline(before, 1, 36)
        self.assertEqual(replace_overlay_timeline(after, 1, 6, 0), before)

    def test_stale_door_pointer_cannot_pass_polygon_validation(self):
        after = bytearray(replace_overlay_timeline(fixture(), 1, 36))
        struct.pack_into("<I", after, 318, 240)
        struct.pack_into("<II", after, 240, 10000, 10)
        with self.assertRaises(ValueError):
            validate_polygons(bytes(after))

    def test_unknown_layout_and_truncated_source_are_rejected(self):
        with self.assertRaises(ValueError):
            replace_overlay_timeline(b"WED V1.3", 1, 36)
        source = bytearray(fixture())
        struct.pack_into("<H", source, 114, 99)
        with self.assertRaises(ValueError):
            replace_overlay_timeline(bytes(source), 1, 36)


if __name__ == "__main__":
    unittest.main()
