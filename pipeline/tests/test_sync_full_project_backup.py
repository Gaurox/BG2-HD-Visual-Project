"""Backup tests exercise preservation, tampering, hardlinks and incomplete promotion."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import sync_full_project_backup as backup


class FullBackupTests(unittest.TestCase):
    def setUp(self):
        fixture_root = Path(__file__).resolve().parents[2] / '.tmp' / 'full-backup-tests'
        fixture_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=fixture_root)
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base / 'source'
        self.destination = base / 'backup'
        self.source.mkdir()
        (self.source / '.git').mkdir()
        (self.source / '.git' / 'HEAD').write_bytes(b'ref: refs/heads/main\n')
        self.destination.mkdir()
        self.head = patch.object(backup, 'git_head', return_value='fixture-commit')
        self.head.start()
        self.addCleanup(self.head.stop)

    def put(self, relative, data):
        path = self.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return path

    def run_backup(self, **options):
        with patch.object(backup, 'emit'):
            return backup.sync(self.source, self.destination, workers=2, **options)

    def test_ignored_outputs_git_and_hardlinks_are_backed_up_old_tree_retained(self):
        (self.source / '.gitignore').write_text('sprite/.work/\n', encoding='utf-8')
        first = self.put('sprite/.work/production.bin', b'GPU output')
        os.link(first, self.source / 'same-output.bin')
        old = self.destination / 'projet'
        old.mkdir()
        (old / 'old-only.bin').write_bytes(b'old work')
        receipt = self.run_backup()
        current = self.destination / 'projet'
        self.assertEqual((current / 'sprite/.work/production.bin').read_bytes(), b'GPU output')
        self.assertEqual((current / '.git/HEAD').read_bytes(), b'ref: refs/heads/main\n')
        self.assertEqual((Path(receipt['previous_project_preserved']) / 'old-only.bin').read_bytes(), b'old work')
        self.assertEqual(os.stat(current / 'same-output.bin').st_ino, os.stat(current / 'sprite/.work/production.bin').st_ino)
        self.assertEqual(receipt['hardlink_paths'], 1)

    def test_incremental_updates_keep_previous_bytes_and_deleted_source_files(self):
        current = self.put('asset.bin', b'old')
        self.put('retired.bin', b'retained')
        self.run_backup()
        current.write_bytes(b'new production')
        (self.source / 'retired.bin').unlink()
        receipt = self.run_backup()
        self.assertEqual((self.destination / 'projet/asset.bin').read_bytes(), b'new production')
        self.assertEqual((self.destination / 'projet/retired.bin').read_bytes(), b'retained')
        old = self.destination / 'historique' / ('changed-' + receipt['run_id']) / 'asset.bin'
        self.assertEqual(old.read_bytes(), b'old')

    def test_full_verification_detects_tampering_even_with_preserved_metadata(self):
        self.put('asset.bin', b'good')
        self.run_backup()
        target = self.destination / 'projet/asset.bin'
        original = target.stat()
        target.write_bytes(b'evil')
        os.utime(target, ns=(original.st_atime_ns, original.st_mtime_ns))
        self.run_backup(full_verify=True)
        self.assertEqual(target.read_bytes(), b'good')

    def test_source_changes_prevent_promotion_of_partial_initial_copy(self):
        self.put('asset.bin', b'first')
        old = self.destination / 'projet'
        old.mkdir()
        (old / 'old-only.bin').write_bytes(b'old')
        original = backup.install_file
        def changing(*args, **kwargs):
            result = original(*args, **kwargs)
            if result['relative'] == 'asset.bin':
                self.put('new-during-copy.bin', b'new')
            return result
        with patch.object(backup, 'install_file', side_effect=changing):
            with self.assertRaisesRegex(RuntimeError, 'Source tree changed'):
                self.run_backup()
        self.assertEqual((old / 'old-only.bin').read_bytes(), b'old')
        self.assertFalse((self.destination / '.backup-state/completed.json').exists())

    def test_nested_destination_is_refused(self):
        nested = self.source / 'nested'
        nested.mkdir()
        with self.assertRaisesRegex(ValueError, 'non-nested'):
            backup.sync(self.source, nested)

    def test_git_hook_runs_again_when_only_ignored_production_changes(self):
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.source), *args],
                                           stderr=subprocess.STDOUT, text=True)
        git('init', '-b', 'main')
        git('init', '--bare', str(self.destination.parent / 'remote.git'))
        git('remote', 'add', 'local', str(self.destination.parent / 'remote.git'))
        scripts = self.source / 'pipeline/scripts'
        scripts.mkdir(parents=True)
        real = Path(__file__).resolve().parents[1] / 'scripts'
        for name in ['sync_full_project_backup.py', 'workspace_paths.py']:
            shutil.copyfile(real / name, scripts / name)
        configuration = self.source / 'config'
        configuration.mkdir()
        template = Path(__file__).resolve().parents[2] / 'config/workspace-paths.json'
        shutil.copyfile(template, configuration / 'workspace-paths.json')
        (configuration / 'workspace-paths.local.json').write_text(json.dumps({'paths': {
            'full_project_backup_source': str(self.source),
            'full_project_backup_root': str(self.destination)}}), encoding='utf-8')
        (self.source / 'AGENTS.md').write_text('Backup fixture\n', encoding='utf-8')
        (self.source / '.gitignore').write_text('work/\nconfig/workspace-paths.local.json\n', encoding='utf-8')
        hooks = self.source / 'pipeline/git-hooks'
        hooks.mkdir()
        shutil.copyfile(Path(__file__).resolve().parents[1] / 'git-hooks/pre-push', hooks / 'pre-push')
        git('config', 'core.hooksPath', 'pipeline/git-hooks')
        self.put('work/production.bin', b'first production')
        git('add', '.')
        git('-c', 'user.name=BackupTest', '-c', 'user.email=backup@localhost', 'commit', '-m', 'fixture')
        git('push', 'local', 'main:main')
        self.assertEqual((self.destination / 'projet/work/production.bin').read_bytes(), b'first production')
        self.put('work/production.bin', b'second ignored production')
        output = git('push', 'local', 'main:main')
        self.assertIn('Everything up-to-date', output)
        self.assertEqual((self.destination / 'projet/work/production.bin').read_bytes(), b'second ignored production')


if __name__ == '__main__':
    unittest.main()
