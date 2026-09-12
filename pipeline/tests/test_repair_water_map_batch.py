"""Synthetic shoreline-selection regressions; no workspace assets required."""
import struct
import sys
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from repair_water_map_batch import masks_for, block_mask


def cells_wed(shared=False):
    data = bytearray(80)
    data[:8] = b"WED V1.3"
    struct.pack_into("<III", data, 8, 1, 0, 32)
    struct.pack_into("<HH8sHHII", data, 32, 2, 1, b"ARTEST", 2, 0, 56, 76)
    struct.pack_into("<HHHB3x", data, 56, 0, 1, 65535, 2)
    struct.pack_into("<HHHB3x", data, 66, 1, 1, 2, 2)
    struct.pack_into("<HH", data, 76, 0, 0 if shared else 1)
    return bytes(data)


class RepairWaterMapBatchTests(unittest.TestCase):
    def test_native_shore_guard_excludes_top_and_bottom(self):
        def tile(index):
            return Image.new("RGBA", (64, 64), (50, 60, 70, 0 if index == 1 else 255))
        rgb, alpha, coords, seams, _ = masks_for(cells_wed(), tile)
        self.assertEqual(len(seams), 1)
        self.assertEqual(set(rgb), {0})
        self.assertEqual(set(alpha), {2})
        self.assertFalse(rgb[0][:4].any())
        self.assertFalse(rgb[0][-4:].any())
        self.assertTrue((rgb[0][4:252, -4:] == 1).all())
        self.assertEqual(coords[2], (1, 0))

    def test_shared_primary_rejected(self):
        with self.assertRaisesRegex(RuntimeError, "shared tile"):
            masks_for(cells_wed(shared=True), lambda _: Image.new("RGBA", (64, 64)))

    def test_padding_tracks_only_selected_edge(self):
        mask = np.zeros((256, 256), bool)
        mask[4:8, -4:] = True
        blocks = block_mask(mask)
        self.assertEqual(blocks.shape, (66, 66))
        self.assertEqual(np.argwhere(blocks).tolist(), [[2, 64], [2, 65]])


if __name__ == "__main__":
    unittest.main()
