from __future__ import annotations
import struct
import sys
import unittest
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
from palette_oracle import read_bam_p8, scalar_palette
from reboutcx_quantize import character_chmb1_palette_rgb


def fixture():
    # Two actual frames plus a declared empty frame with meaningful centres.
    # A gap in the lookup, repeated slots and an empty cycle test topology.
    frame_offset, palette_offset, lookup_offset, data_offset = 24, 72, 1096, 1106
    header = b"BAM V1  " + struct.pack("<HBBIII", 3, 3, 9, frame_offset, palette_offset, lookup_offset)
    frames = struct.pack("<HHhhI", 3, 1, -7, 11, data_offset)
    frames += struct.pack("<HHhhI", 2, 1, 5, -13, 0x80000000 | (data_offset + 3))
    frames += struct.pack("<HHhhI", 0, 4, -123, 321, 0)
    cycles = struct.pack("<HHHHHH", 3, 1, 0, 0, 1, 4)
    palette = np.arange(1024, dtype=np.uint16).astype(np.uint8).tobytes()
    lookup = struct.pack("<5H", 2, 0, 0, 1, 2)
    return header + frames + cycles + palette + lookup + bytes([4, 9, 1, 1, 9])


class PaletteOracleTests(unittest.TestCase):
    def test_rle_raw_signed_centres_palette_and_lookup_topology(self):
        bam = read_bam_p8(fixture())
        self.assertEqual(bam["transparent"], 9)
        self.assertEqual(bam["cycles"], [
            {"index": 0, "lookup_start": 1, "frame_indices": [0, 0, 1]},
            {"index": 1, "lookup_start": 0, "frame_indices": []},
            {"index": 2, "lookup_start": 4, "frame_indices": [2]}])
        a, b, empty = bam["frames"]
        np.testing.assert_array_equal(a["indices"], [[4, 9, 9]])
        np.testing.assert_array_equal(b["indices"], [[1, 9]])
        self.assertEqual((a["center_x"], a["center_y"]), (-7, 11))
        self.assertEqual((b["center_x"], b["center_y"]), (5, -13))
        self.assertEqual((empty["width"], empty["height"], empty["center_x"], empty["center_y"]), (0, 4, -123, 321))
        self.assertEqual(empty["indices"].shape, (4, 0))
        np.testing.assert_array_equal(bam["palette_rgb"][0], [2, 1, 0])
        self.assertEqual(bam["palette_bgra"][0, 3], 3)

    def test_bamc_roundtrip_and_declared_length(self):
        raw = fixture()
        compressed = b"BAMCV1  " + struct.pack("<I", len(raw)) + zlib.compress(raw)
        self.assertEqual(read_bam_p8(compressed)["canonical"], raw)
        self.assertTrue(read_bam_p8(compressed)["packed"])
        with self.assertRaisesRegex(ValueError, "length or stream"):
            read_bam_p8(compressed[:8] + struct.pack("<I", len(raw) + 1) + compressed[12:])

    def test_malformed_bam_rejected(self):
        raw = fixture()
        for bad in (raw[:23], b"BAM V2  " + raw[8:], raw[:-1]):
            with self.assertRaises(ValueError):
                read_bam_p8(bad)
        bad = bytearray(raw)
        struct.pack_into("<H", bad, 1098, 99)
        with self.assertRaisesRegex(ValueError, "missing frame"):
            read_bam_p8(bytes(bad))
        bad = bytearray(raw)
        bad[1108] = 3
        # A terminal transparent run may cross the declared pixel count.
        parsed = read_bam_p8(bytes(bad))
        np.testing.assert_array_equal(parsed["frames"][0]["indices"], [[4, 9, 9]])
        self.assertEqual(parsed["frames"][0]["rle_tail_overflow"], 2)

    def test_independent_address_oracle_matches_all_classes_and_shades(self):
        rng = np.random.default_rng(6110)
        for _ in range(32):
            ramps = rng.integers(0, 256, (7, 12, 3), dtype=np.uint8)
            np.testing.assert_array_equal(scalar_palette(ramps), character_chmb1_palette_rgb(ramps))

    def test_each_channel_has_exact_dependencies_and_floor_averages(self):
        # Distinguish all channels and each shade; endpoints 0/1/10/11 must not
        # participate in any mixed range. Changing one channel affects 6 pairs.
        ramps = np.zeros((7, 12, 3), np.uint8)
        base = scalar_palette(ramps)
        for channel in range(7):
            changed = ramps.copy()
            changed[channel, :, :] = 255
            realized = scalar_palette(changed)
            self.assertEqual(np.count_nonzero(np.any(realized[4:88] != base[4:88], axis=1)), 12)
            self.assertEqual(np.count_nonzero(np.any(realized[88:] != base[88:], axis=1)), 48)
            self.assertEqual(set(realized[88:].ravel()), {0, 127})
        for shade in (0, 1, 10, 11):
            changed = ramps.copy()
            changed[:, shade] = 255
            np.testing.assert_array_equal(scalar_palette(changed)[88:], base[88:])


if __name__ == "__main__":
    unittest.main()
