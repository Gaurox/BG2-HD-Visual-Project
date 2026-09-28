"""Refined BC3 encoder: valid payload, exact flat blocks, better than Pillow on smooth texture."""
import io
import struct
import sys
import unittest
import zlib
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from bc3_refined import encode_bc3  # noqa: E402
from mos_decode import decode_pvrz_page  # noqa: E402


def decode(payload, w, h):
    header = struct.pack("<13I", 0x03525650, 0, 11, 0, 0, 0, w, h, 1, 1, 1, 1, 0)
    pvr = header + payload
    return np.asarray(decode_pvrz_page(struct.pack("<I", len(pvr)) + zlib.compress(pvr))).astype(float)


def smooth_texture(size=64):
    y, x = np.mgrid[0:size, 0:size] / size
    rgb = np.stack([60 + 30 * np.sin(6 * x + 3 * y), 160 + 20 * np.cos(5 * y - 2 * x),
                    170 + 15 * np.sin(4 * x * y + 1)], -1)
    alpha = np.full((size, size, 1), 255.0)
    return np.clip(np.dstack([rgb, alpha]), 0, 255).astype(np.uint8)


class RefinedBc3Tests(unittest.TestCase):
    def test_flat_block_is_exact_and_alpha_kept(self):
        img = np.zeros((8, 8, 4), np.uint8)
        img[..., :3] = (16, 12, 8)
        img[..., 3] = 128
        out = decode(encode_bc3(img), 8, 8)
        self.assertTrue(np.all(out[..., 3] == 128))
        self.assertLess(np.abs(out[..., :3] - [16, 12, 8]).max(), 5)

    def test_beats_pillow_on_smooth_texture(self):
        img = smooth_texture()
        ref = decode(encode_bc3(img), 64, 64)
        buf = io.BytesIO()
        Image.fromarray(img, "RGBA").save(buf, format="DDS", pixel_format="DXT5")
        pil = decode(buf.getvalue()[128:], 64, 64)
        err = lambda d: np.abs(d[..., :3] - img[..., :3]).mean()
        self.assertLessEqual(err(ref), err(pil))


if __name__ == "__main__":
    unittest.main()
