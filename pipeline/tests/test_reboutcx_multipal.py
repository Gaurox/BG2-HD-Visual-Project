from __future__ import annotations
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "pipeline/scripts"))
from reboutcx_cache_p12 import frame_key
from reboutcx_multipal import save_npz
from run_creature_sprite_x2 import SourceFrame


class MultipaletteCacheTests(unittest.TestCase):
    def test_cache_key_tracks_palette_and_pixels_but_not_anchor(self):
        palette = np.zeros((256, 3), np.uint8)
        idx = np.array([[4, 5]], np.uint8)
        frame = SourceFrame("TEST", 0, 2, 1, 0, 0, 0, idx, palette, bytes(8))
        shifted = SourceFrame("OTHER", 7, 2, 1, 5, -1, 0, idx, palette, bytes(8))
        self.assertEqual(frame_key(frame, palette, b"contract"), frame_key(shifted, palette, b"contract"))
        other = palette.copy()
        other[5] = 255
        self.assertNotEqual(frame_key(frame, palette, b"contract"), frame_key(frame, other, b"contract"))
        self.assertNotEqual(frame_key(frame, palette, b"contract"), frame_key(frame, palette, b"new"))

    def test_float_targets_round_trip_without_u8_quantization(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cache.npz"
            target = np.array([[[.001, .12345, .9999]]], np.float32)
            save_npz(path, x4=target)
            with np.load(path, allow_pickle=False) as data:
                np.testing.assert_array_equal(data["x4"], target)
            self.assertFalse(path.with_suffix(".part").exists())


if __name__ == "__main__":
    unittest.main()
