"""Pure checks for the non-generative AR1000 WTPOOL recipe."""
import sys
from pathlib import Path
import unittest

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))
from build_ar1000_wtpool_periodic_bilinear_candidate import (
    FRAME_COUNT,
    OVERLAY_ALIAS,
    PAGE_ALIAS,
    cyclic_linear_timeline,
    periodic_bilinear_x4,
)
from build_wtlake_timeline_batch import expected_page_name


class Ar1000WtpoolPeriodicBilinearTests(unittest.TestCase):
    def test_alias_uses_infinity_page_convention(self):
        self.assertEqual(PAGE_ALIAS + ".PVRZ", expected_page_name(OVERLAY_ALIAS, 0))

    def test_wrapped_resize_and_cyclic_timeline(self):
        source = np.zeros((64, 64, 4), dtype=np.uint8)
        source[:, :, 3] = 255
        source[:, :, 0] = np.arange(64, dtype=np.uint8)[None, :]
        anchors = [periodic_bilinear_x4(Image.fromarray(source, "RGBA")) for _ in range(6)]
        self.assertEqual(anchors[0].size, (256, 256))
        frames = cyclic_linear_timeline(anchors)
        self.assertEqual(len(frames), FRAME_COUNT)
        self.assertEqual(frames[0].tobytes(), frames[-1].tobytes())


if __name__ == "__main__":
    unittest.main()
