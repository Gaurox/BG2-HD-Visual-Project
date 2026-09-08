from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import build_fused_area_animation_carrier as builder  # noqa: E402
import build_joint_animation_rgb_seam as joint  # noqa: E402


class FusedAreaAnimationCarrierTests(unittest.TestCase):
    def test_source_over_then_blended_premultiplication(self) -> None:
        top = np.array([[[200, 100, 50, 128]]], dtype=np.uint8)
        bottom = np.array([[[20, 40, 80, 128]]], dtype=np.uint8)

        straight = builder.source_over(bottom, top)
        blended = builder.premultiply_for_blended(straight)

        self.assertEqual(int(straight[0, 0, 3]), 192)
        expected = np.rint(straight[0, 0, :3].astype(np.float32) * (192 / 255.0))
        self.assertTrue(np.array_equal(blended[0, 0, :3], expected.astype(np.uint8)))
        self.assertEqual(int(blended[0, 0, 3]), 192)

    def test_fuse_frame_uses_one_world_canvas(self) -> None:
        top = np.full((8, 8, 4), 64, dtype=np.uint8)
        bottom = np.full((8, 8, 4), 192, dtype=np.uint8)
        top[:, :, 3] = 255
        bottom[:, :, 3] = 255

        straight, blended, layout = builder.fuse_frame(
            top,
            bottom,
            top_layout=joint.FrameLayout(8, 8, 0, 0),
            bottom_layout=joint.FrameLayout(8, 8, 0, 4),
        )

        self.assertEqual(layout, joint.FrameLayout(8, 12, 0, 0))
        self.assertEqual(straight.shape, (12, 8, 4))
        self.assertTrue(np.array_equal(straight, blended))
        self.assertTrue(np.all(straight[4:8, :, :3] == 192))

    def test_patch_area_changes_only_two_resrefs(self) -> None:
        offset = 0x100
        payload = bytearray(offset + 4 * builder.ARE_ANIMATION_SIZE)
        payload[:8] = b"AREAV1.0"
        struct.pack_into("<I", payload, 0xAC, 4)
        struct.pack_into("<I", payload, 0xB0, offset)
        for index, (resref, position, flags) in enumerate((
            ("OTHER", (0, 0), 0),
            ("AM2805B", (483, 368), 0x1151),
            ("AM2805B", (483, 368), 0x1000),
            ("AM2805C", (483, 553), 0x1151),
        )):
            entry = offset + index * builder.ARE_ANIMATION_SIZE
            payload[entry:entry + 32] = f"entry-{index}".encode("ascii").ljust(32, b"\0")
            struct.pack_into("<hh", payload, entry + 0x20, *position)
            payload[entry + 0x28:entry + 0x30] = resref.encode("ascii").ljust(8, b"\0")
            struct.pack_into("<I", payload, entry + 0x34, flags)

        patched, changes = builder.patch_area(
            bytes(payload), carrier_index=1, null_index=3,
            carrier_resref="AM28ADD", null_resref="AM28NUL",
        )

        self.assertEqual(changes[0]["after"]["resref"], "AM28ADD")
        self.assertEqual(changes[1]["after"]["resref"], "AM28NUL")
        self.assertEqual(builder.are_occurrence(patched, 2)["resref"], "AM2805B")


if __name__ == "__main__":
    unittest.main()
