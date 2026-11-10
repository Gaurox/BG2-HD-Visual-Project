"""Installer backup preserves old H: data and refuses incomplete/corrupt snapshots."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import backup_installer as backup


class InstallerBackupTests(unittest.TestCase):
    def setUp(self):
        fixture = Path(__file__).resolve().parents[2] / '.tmp/installer-backup-tests'
        fixture.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=fixture)
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / 'source'
        self.backups = Path(temporary.name) / 'backup'
        self.root.mkdir()
        self.backups.mkdir()
        (self.root / 'payload.bin').write_bytes(b'final asset')
        (self.root / 'cache.bin').write_bytes(b'ignored intermediate')
        self.entry = backup.describe(self.root, 'payload.bin', sha256=hashlib.sha256(b'final asset').hexdigest())
        self.metadata = {'release_version': 'test-v1', 'source_commit': 'fixture'}
        self.silent = patch.object(backup, 'emit')
        self.silent.start()
        self.addCleanup(self.silent.stop)

    def run_backup(self, entries=None):
        return backup.snapshot(self.root, self.backups, entries or [self.entry], self.metadata, workers=2)

    def test_selected_bytes_verified_old_data_and_prior_snapshots_preserved(self):
        old = self.backups / 'projet'
        old.mkdir()
        (old / 'old.bin').write_bytes(b'old backup')
        first = self.run_backup()
        second = self.run_backup()
        self.assertNotEqual(first, second)
        self.assertEqual((old / 'old.bin').read_bytes(), b'old backup')
        for snapshot in (first, second):
            self.assertEqual((snapshot / 'files/payload.bin').read_bytes(), b'final asset')
            self.assertFalse((snapshot / 'files/cache.bin').exists())
            receipt = json.loads((snapshot / 'completed.json').read_text())
            record = json.loads((snapshot / 'inventory.jsonl').read_text())
            self.assertEqual(receipt['status'], 'complete')
            self.assertEqual(receipt['verified_files'], 1)
            self.assertEqual(record['sha256'], self.entry.sha256)

    def test_wrong_manifest_hash_cannot_produce_success(self):
        entry = backup.describe(self.root, 'payload.bin', sha256='0' * 64)
        with self.assertRaisesRegex(ValueError, 'content.json'):
            self.run_backup([entry])
        self.assertEqual(len(list(self.backups.rglob('failed.json'))), 1)
        self.assertFalse(list(self.backups.rglob('completed.json')))

    def test_source_modified_after_planning_cannot_produce_success(self):
        (self.root / 'payload.bin').write_bytes(b'changed production')
        with self.assertRaisesRegex(RuntimeError, 'changed since planning'):
            self.run_backup()
        self.assertFalse(list(self.backups.rglob('completed.json')))

    def test_traversal_and_nested_destination_refused(self):
        with self.assertRaises(ValueError):
            backup.describe(self.root, '../outside.bin')
        nested = self.root / 'backup'
        nested.mkdir()
        with self.assertRaisesRegex(ValueError, 'non-nested'):
            backup.snapshot(self.root, nested, [self.entry], self.metadata)

    def test_plan_uses_delivered_payload_and_excludes_archives_and_production_inputs(self):
        content = {'entries': [{'payload_group': 'effect-test', 'source': 'effects/run/frame.rgba',
                                'bytes': self.entry.size, 'sha256': self.entry.sha256}]}
        files = {
            backup.RELEASE + '/manifests/content.json': json.dumps(content).encode(),
            backup.RELEASE + '/manifests/release.json': json.dumps(
                {'version': 'test-v1', 'release_status': 'blocked'}).encode(),
            backup.PAYLOAD + '/effect-test/frame.rgba': b'final asset',
            backup.PAYLOAD + '/effect-test/unselected.rgba': b'not selected',
            backup.RELEASE + '/archive/old.bin': b'historical',
            backup.RELEASE + '/release-inputs/effects/raw.bin': b'production source',
            backup.RELEASE + '/bg2hd/renderer/renderer.dll': b'current renderer',
            backup.RELEASE + '/release-inputs/weidu/setup-bg2hd.exe': b'weidu',
            backup.RELEASE + '/release-inputs/weidu/weidu-v249.00.tar.gz': b'source',
        }
        for relative, data in files.items():
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        with patch.object(backup.subprocess, 'check_output', return_value=(
                '\0'.join(files) + '\0').encode()), patch.object(backup, 'git_head', return_value='fixture'):
            plan, metadata = backup.build_plan(self.root)
        selected = {entry.relative for entry in plan}
        self.assertIn(backup.PAYLOAD + '/effect-test/frame.rgba', selected)
        self.assertIn(backup.RELEASE + '/bg2hd/renderer/renderer.dll', selected)
        self.assertFalse(any('/archive/' in path or '/release-inputs/effects/' in path
                             or 'unselected.rgba' in path for path in selected))
        self.assertEqual(metadata['payload_files'], 1)


if __name__ == '__main__':
    unittest.main()
