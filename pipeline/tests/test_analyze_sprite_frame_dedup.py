"""Selection reuse and native geometry regressions for the all-profile source plan."""
import contextlib
import io
import json
from pathlib import Path
import sqlite3
import struct
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import analyze_sprite_frame_dedup as analysis


class SourceDedupTests(unittest.TestCase):
    def test_pixel_identity_keeps_used_colours_but_ignores_centres(self):
        pixels = np.array([[3, 4]], dtype=np.uint8)
        palette = np.zeros((256, 3), np.uint8)
        a = analysis.identities(pixels, palette, 0)
        palette[17] = [99, 98, 97]
        b = analysis.identities(pixels, palette, 0)
        self.assertEqual(a[:2], b[:2])
        palette[3] = [1, 2, 3]
        c = analysis.identities(pixels, palette, 0)
        self.assertEqual(a[0], c[0])
        self.assertNotEqual(a[1], c[1])
        self.assertNotEqual(a[0], analysis.identities(pixels.reshape(2, 1), palette, 0)[0])

    def test_native_cycle_sentinel_and_signed_centres_are_retained(self):
        # Pixel decoding must not invent a frame for the 0xffff native lookup.
        frame_offset, palette_offset, lookup_offset, pixel_offset = 24, 40, 1064, 1068
        raw = (b"BAM V1  " + struct.pack("<HBBIII", 1, 1, 0, frame_offset, palette_offset, lookup_offset)
               + struct.pack("<HHhhI", 2, 1, -9, 12, pixel_offset | 0x80000000)
               + struct.pack("<HH", 2, 0) + bytes(1024) + struct.pack("<HH", 0, 65535) + b"\x03\x04")
        original = bytes(raw)
        bam, sentinel_count = analysis.read_source(raw)
        self.assertEqual(raw, original)
        self.assertEqual(sentinel_count, 1)
        self.assertEqual(bam["cycles"][0]["frame_indices"], [0, 65535])
        self.assertEqual((bam["frames"][0]["center_x"], bam["frames"][0]["center_y"]), (-9, 12))
        np.testing.assert_array_equal(bam["frames"][0]["indices"], [[3, 4]])

    def test_combined_selection_counts_shared_work_once_and_does_not_claim_gpu_hits(self):
        with tempfile.TemporaryDirectory(dir=analysis.ROOT) as directory:
            root = Path(directory)
            path = root / "processing-plan.sqlite"
            db = sqlite3.connect(path)
            db.executescript(analysis.DDL)
            for aid in ("0x7000", "0x7001"):
                db.execute("INSERT INTO animations VALUES(?,?,?)", (aid, "monster_old", "{}"))
            for rid in (1, 2):
                db.execute("INSERT INTO resources VALUES(?,?,?,?,?,?,?,?,?,?,?)", (rid, f"R{rid}", "a", "b", "native", bytes(1024), 0, 2, 0, 0, "{}"))
                db.execute("INSERT INTO animation_resources VALUES(?,?)", (f"0x{0x6FFF+rid:04X}", rid))
            for wid in (1, 2, 3):
                db.execute("INSERT INTO inputs VALUES(?,?,?,?,?,?,?)", (wid, bytes([wid])*32, 2, 1, 0, b"", 1))
                db.execute("INSERT INTO source_work VALUES(?,?,?,?,?,?)", (wid, bytes([wid])*32, wid, b"", 1, 0))
            for rid, work_ids in ((1, (1, 2)), (2, (2, 3))):
                for fi, wid in enumerate(work_ids):
                    db.execute("INSERT INTO frames VALUES(?,?,?,?,?,?,?,?)", (rid, fi, wid, rid*10, -rid, 0, 0, 1))
            db.execute("INSERT INTO character_work_matches VALUES(?,?,1)", (2, 42))
            db.commit()
            db.close()
            descriptor = root / "plan.json"
            descriptor.write_text(json.dumps(dict(schema=analysis.SCHEMA, path=path.relative_to(analysis.ROOT).as_posix(), bytes=path.stat().st_size)), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                analysis.plan(descriptor, ["0x7000", "0x7001", "0x7000"])
            report = json.loads(out.getvalue())
            self.assertEqual(report["unique_source_work"], 3)
            self.assertEqual(report["source_work_shared_with_character"], 1)
            self.assertIsNone(report["remaining_gpu_work"])
            self.assertFalse(report["production_started"])
            db = sqlite3.connect(path)
            self.assertEqual(db.execute("SELECT center_x,center_y FROM frame_map WHERE work_id=2 ORDER BY resource_id").fetchall(), [(10, -1), (20, -2)])
            db.close()


if __name__ == "__main__":
    unittest.main()
