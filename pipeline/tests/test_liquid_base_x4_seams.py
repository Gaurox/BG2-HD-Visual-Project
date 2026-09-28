"""Base x4 interface masks: A-D pavings put different slots of one family side by side."""
import sys
from pathlib import Path
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import build_liquid_base_x4_trial as b


def parsed_pair():
    """Central water cell (slot 1, tile 0) left of a primary/secondary pair (slot 2)."""
    return {"layers": [{"width": 2, "height": 1}],
            "cells": [{"x": 0, "y": 0, "primary": [0], "secondary": 65535, "flags": 1 << 1, "count": 1},
                      {"x": 1, "y": 0, "primary": [1], "secondary": 2, "flags": 1 << 2, "count": 1}]}


def stock_tile(tile):
    rgba = np.zeros((64, 64, 4), np.uint8)
    rgba[:, :, 3] = {0: 255, 1: 0, 2: 255}[tile]     # pair: transparent primary, opaque secondary
    return rgba


class BaseSeamMaskTests(unittest.TestCase):
    def test_family_group_finds_the_interface_between_different_slots(self):
        _, _, _, interfaces = b.seam_masks(parsed_pair(), [[1, 2]], {(0, 0): 0}, stock_tile, {0, 1}, {2})
        self.assertEqual([(i["cell"], i["neighbor"], i["side"]) for i in interfaces], [([0, 0], [1, 0], "right")])

    def test_per_slot_groups_keep_materials_apart(self):
        _, _, _, interfaces = b.seam_masks(parsed_pair(), [[1], [2]], {(0, 0): 0}, stock_tile, {0, 1}, {2})
        self.assertEqual(interfaces, [])



class IsolatedPageIndexTests(unittest.TestCase):
    def test_skips_archived_and_override_pages(self):
        import tempfile
        with tempfile.TemporaryDirectory() as live:
            live = Path(live)
            (live / "A041320.PVRZ").write_bytes(b"")
            reserved = {f"A0413{i:02d}" for i in range(20)}
            self.assertEqual(b.free_page_index("A0413", 16, reserved, live), 21)
            self.assertEqual(b.free_page_index("A0503", 6, reserved, live), 6)


class FlatColourBlockTests(unittest.TestCase):
    def test_flat_block_decodes_to_the_rgb565_colour(self):
        import struct
        block = bytes(b.dxt_color_block((14, 13, 7)))
        c0, c1, indices = struct.unpack("<HHI", block)
        self.assertEqual((c0, c1, indices), (c0, c0, 0))
        self.assertEqual(((c0 >> 11) & 31, (c0 >> 5) & 63, c0 & 31), (2, 3, 1))


if __name__ == "__main__":
    unittest.main()
