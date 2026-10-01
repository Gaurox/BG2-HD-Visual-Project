"""Guards against unsafe reuse when native Character frames are grouped."""
import sqlite3
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import analyze_playable_frame_dedup as plan


class ExactFrameIdentityTests(unittest.TestCase):
    def setUp(self):
        self.i = np.array([[0, 4, 5], [16, 17, 2]], np.uint8)
        self.p = np.arange(768, dtype=np.uint16).reshape(256, 3).astype(np.uint8)

    def key(self, i=None, p=None, t=0):
        return plan.identities(self.i if i is None else i, self.p if p is None else p, t)

    def test_identical_pixels_allow_different_resource_centres_cycles_and_layers(self):
        # None of these output metadata fields is an input to the pixel identity.
        self.assertEqual(self.key()[:2], self.key(self.i.copy(), self.p.copy())[:2])
        db = sqlite3.connect(":memory:")
        db.executescript(plan.DDL)
        db.execute("INSERT INTO models VALUES(0,'0x6110','FIGHTER','{}')")
        db.execute("INSERT INTO models VALUES(1,'0x6010','CLERIC','{}')")
        for n in range(2):
            db.execute("INSERT INTO families VALUES(?,?,?,?,?,?,?,?)", (f'f{n}', n, 'body' if n == 0 else 'helmet', 'v', '1', 'TEST', 'available', '{}'))
            db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (n, f'TEST{n}', 'source', 'source', 'hash', 'hash', b'palette', 'hash', 0, 1, 1, 1, '{}'))
            db.execute("INSERT INTO family_resources VALUES(?,?)", (f'f{n}', n))
        ik, wk, raw, used, needs = self.key()
        db.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?,?,?,?,?)", (0, ik, 3, 2, 0, 6, 32, 32, 1, 1, b'pixels'))
        db.execute("INSERT INTO work_items(work_id,work_key,input_id,used_native_rgb,representative_resource_id,representative_frame_index) VALUES(0,?,0,?,0,0)", (wk, used))
        for n in range(2):
            db.execute("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?)", (n, 0, 0, 1 + n, -2 - n, 0, 0, 1))
            db.execute("INSERT INTO cycles VALUES(?,?,?,?,?)", (n, 0, n, 1, b'\0\0'))
        self.assertEqual(db.execute("SELECT count(*) FROM processing_queue").fetchone()[0], 1)
        self.assertEqual(db.execute("SELECT animation_id,center_x,center_y,work_id FROM frame_map ORDER BY animation_id").fetchall(),
                         [('0x6010', 2, -3, 0), ('0x6110', 1, -2, 0)])
        db.close()

    def test_equal_rgb_different_indices_never_merge(self):
        p = self.p.copy()
        p[16] = p[4]
        i = self.i.copy()
        i[0, 1] = 16
        np.testing.assert_array_equal(p[self.i], p[i])
        self.assertNotEqual(self.key(p=p)[0], self.key(i=i, p=p)[0])
        self.assertNotEqual(self.key(p=p)[1], self.key(i=i, p=p)[1])

    def test_unused_palette_colours_allow_reuse(self):
        p = self.p.copy()
        p[100] ^= 255
        self.assertEqual(self.key()[:2], self.key(p=p)[:2])

    def test_used_colours_require_separate_guides_but_same_neural_indexed_input(self):
        p = self.p.copy()
        p[4] ^= 255
        self.assertEqual(self.key()[0], self.key(p=p)[0])
        self.assertNotEqual(self.key()[1], self.key(p=p)[1])

    def test_transparent_rgb_is_retained_for_actual_xbr_bytes(self):
        p = self.p.copy()
        p[0] ^= 255
        self.assertNotEqual(self.key()[1], self.key(p=p)[1])

    def test_dimensions_and_transparency_do_not_merge(self):
        self.assertNotEqual(self.key()[0], self.key(i=self.i.reshape(3, 2))[0])
        self.assertNotEqual(self.key()[0], self.key(t=255)[0])

    def test_mirroring_rotation_crop_and_single_pixel_changes_do_not_merge(self):
        for i in (self.i[:, ::-1], self.i[::-1], np.rot90(self.i), self.i[:, :2]):
            self.assertNotEqual(self.key()[0], self.key(i=i)[0])
        i = self.i.copy()
        i[1, 1] += 1
        self.assertNotEqual(self.key()[0], self.key(i=i)[0])

    def test_only_production_specials_skip_neural_work(self):
        self.assertFalse(self.key(i=np.zeros((4, 8), np.uint8))[4])
        self.assertFalse(self.key(i=np.array([[2]], np.uint8))[4])
        self.assertTrue(self.key(i=np.array([[1]], np.uint8))[4])
        self.assertTrue(self.key(i=np.array([[3]], np.uint8))[4])
        self.assertTrue(self.key(i=np.array([[2, 2]], np.uint8))[4])

    def test_sorted_used_palette_preserves_specials_and_classes(self):
        used = np.frombuffer(self.key()[3], np.uint8).reshape(-1, 4)
        self.assertEqual(used[:, 0].tolist(), [0, 2, 4, 5, 16, 17])
        np.testing.assert_array_equal(used[:, 1:], self.p[used[:, 0]])


if __name__ == "__main__":
    unittest.main()
