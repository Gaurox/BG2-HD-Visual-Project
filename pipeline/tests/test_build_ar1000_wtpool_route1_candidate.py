"""Pure artifact tests for the isolated AR1000 WTPOOL producer."""
import struct
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
from build_ar1000_wtpool_route1_candidate import (
    FRAME_COUNT,
    OVERLAY_ALIAS,
    PAGE_ALIAS,
    TILE_SIZE,
    build_overlay,
)
from build_wtlake_timeline_batch import pvrz_metadata
from build_wtlake_timeline_batch import expected_page_name


class Ar1000WtpoolRoute1CandidateTests(unittest.TestCase):
    def test_aliases_fit_cresref_and_remain_pool_classifiable(self):
        self.assertLessEqual(len(OVERLAY_ALIAS), 8)
        self.assertLessEqual(len(PAGE_ALIAS), 8)
        self.assertTrue(OVERLAY_ALIAS.startswith("WTPOOL"))
        self.assertEqual(PAGE_ALIAS + ".PVRZ", expected_page_name(OVERLAY_ALIAS, 0))

    def test_overlay_builder_writes_complete_x4_timeline(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            frames = []
            for index in range(FRAME_COUNT):
                path = root / f"frame-{index:03d}.png"
                Image.new("RGBA", (TILE_SIZE, TILE_SIZE), (index, 80, 120, 255)).save(path)
                frames.append(path)
            tis, pvrz = build_overlay(frames, root / "candidate")
            payload = tis.read_bytes()
            self.assertEqual(payload[:8], b"TIS V1  ")
            self.assertEqual(struct.unpack_from("<4I", payload, 8),
                             (FRAME_COUNT, 12, 24, TILE_SIZE))
            self.assertEqual(len(payload), 24 + FRAME_COUNT * 12)
            self.assertTrue(all(
                struct.unpack_from("<I", payload, 24 + index * 12)[0] == 0
                for index in range(FRAME_COUNT)
            ))
            metadata = pvrz_metadata(pvrz)
            self.assertEqual(metadata["resref"], PAGE_ALIAS)
            self.assertEqual((metadata["width"], metadata["height"]), (2048, 2048))


if __name__ == "__main__":
    unittest.main()
