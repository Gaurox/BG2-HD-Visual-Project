from __future__ import annotations

import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
import effect_authority as authority


class EffectAuthorityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_read_only_guard_does_not_write_and_concurrent_writer_is_refused(self):
        with authority.guard(self.root, False):
            self.assertEqual(list(self.root.iterdir()), [])
        with authority.guard(self.root, True):
            with self.assertRaises(authority.AuthorityError):
                with authority.guard(self.root, True):
                    pass
        # OS releases ownership when the handle closes; persistent file is safe.
        with authority.guard(self.root, True):
            authority.commit(self.root, {"effects/index/test.json": b"one"})

    def test_interrupted_multifile_commit_is_replayed_before_next_writer(self):
        first, second = "effects/index/first.json", "effects/index/second.json"
        original = authority.atomic_write
        with authority.guard(self.root, True):
            def interrupted(path, data):
                if path == self.root / second:
                    raise OSError("simulated process interruption")
                return original(path, data)
            with mock.patch.object(authority, "atomic_write", side_effect=interrupted):
                with self.assertRaises(authority.AuthorityError):
                    authority.commit(self.root, {first: b"one", second: b"two"})
        self.assertEqual((self.root / first).read_bytes(), b"one")
        with self.assertRaisesRegex(authority.AuthorityError, "interrompue"):
            with authority.guard(self.root, False):
                pass
        with authority.guard(self.root, True):
            self.assertEqual((self.root / second).read_bytes(), b"two")
        self.assertFalse((self.root / authority.JOURNAL).exists())

    def test_recovery_never_overwrites_an_external_edit_or_immutable_qa(self):
        relative = "effects/index/test.json"
        with authority.guard(self.root, True):
            authority.commit(self.root, {relative: b"original"}, immutable=(relative,))
            with self.assertRaisesRegex(authority.AuthorityError, "immuable"):
                authority.commit(self.root, {relative: b"changed"}, immutable=(relative,))
        target = self.root / relative
        journal = {"schema": "bg2-effects-authority-transaction-v1", "files": [{
            "path": relative, "before": authority.digest(b"original"), "after": authority.digest(b"desired"),
            "content": base64.b64encode(b"desired").decode(), "immutable": False,
        }]}
        path = self.root / authority.JOURNAL
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(journal), encoding="utf-8")
        target.write_bytes(b"user edit")
        with self.assertRaisesRegex(authority.AuthorityError, "modifiée"):
            with authority.guard(self.root, True):
                pass
        self.assertEqual(target.read_bytes(), b"user edit")

    def test_transaction_cannot_touch_game_or_release_paths(self):
        with authority.guard(self.root, True):
            for path in ("releases/content.json", "effects/index/../../game/file", "effects/ressources/FX/source.bam"):
                with self.assertRaises(authority.AuthorityError):
                    authority.commit(self.root, {path: b"invalid"})


if __name__ == "__main__":
    unittest.main()
