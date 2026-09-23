"""Receipts and QA decisions refuse bytes that are not live; versions never overwrite."""
import json
import sys
from pathlib import Path
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import record_water_decision as r


class RecordWaterDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        self.override = root / "override"
        self.override.mkdir()
        (self.override / "A040401.PVRZ").write_bytes(b"page")
        self.run = root / "run"
        (self.run / "override-candidate").mkdir(parents=True)
        (self.run / "override-candidate/manifest.json").write_text(json.dumps(
            {"files": {"A040401.PVRZ": {"sha256": r.sha(self.override / "A040401.PVRZ"), "bytes": 4}}}))
        self.backup = root / "backup"
        self.backup.mkdir()
        (self.backup / "install-backup.json").write_text("{}")

    def tearDown(self):
        self.tmp.cleanup()

    def test_install_then_qa(self):
        record = r.install_record("AR0404", "contour", self.run, self.override, self.backup)
        self.assertEqual(record["status"], "installed-pending-user-ingame-qa")
        selection = Path(self.tmp.name) / "sel.json"
        selection.write_text(json.dumps(record))
        qa = r.qa_record("AR0404", "contour", selection, "validé", "validated", self.override)
        self.assertEqual(qa["result"], "validated")

    def test_refuses_bytes_that_are_not_live(self):
        (self.override / "A040401.PVRZ").write_bytes(b"other")
        with self.assertRaises(SystemExit):
            r.install_record("AR0404", "contour", self.run, self.override, self.backup)

    def test_reserve_is_mandatory_and_versions_increment(self):
        record = r.install_record("AR0404", "contour", self.run, self.override, self.backup)
        selection = Path(self.tmp.name) / "sel.json"
        selection.write_text(json.dumps(record))
        with self.assertRaises(SystemExit):
            r.qa_record("AR0404", "contour", selection, "ok", "validated-with-reserve", self.override)
        folder = Path(self.tmp.name) / "m"
        first = r.save(r.next_path(folder, "AR0404", "contour", "installed", "20260924"), record)
        second = r.save(r.next_path(folder, "AR0404", "contour", "installed", "20260924"), record)
        self.assertEqual((first.name, second.name), ("ar0404-contour-installed-20260924-v1.json",
                                                     "ar0404-contour-installed-20260924-v2.json"))


if __name__ == "__main__":
    unittest.main()
