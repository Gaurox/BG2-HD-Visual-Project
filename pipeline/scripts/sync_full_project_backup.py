"""Verified full filesystem backup; Git ignore rules never select backup contents."""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import sys
import time
import uuid
from collections import deque
from pathlib import Path

from workspace_paths import ROOT, get_path


def emit(event, **values):
    print(json.dumps({'event': event, **values}, ensure_ascii=True), flush=True)


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def fingerprint(info):
    return info.st_size, info.st_mtime_ns, info.st_dev, info.st_ino


def git_head(root):
    environment = os.environ.copy()
    for key in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES'):
        environment.pop(key, None)
    return subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                                   env=environment, text=True).strip()


def validate_roots(source, backup_root):
    source, backup_root = source.resolve(), backup_root.resolve()
    if source == backup_root or source in backup_root.parents or backup_root in source.parents:
        raise ValueError('Source and backup root must be separate, non-nested directories.')
    if not (source / '.git').is_dir():
        raise ValueError('Source must be the complete primary Git checkout.')
    if not backup_root.is_dir():
        raise ValueError('Configured backup root must already exist.')
    return source, backup_root


class BackupLock:
    def __init__(self, path):
        self.path = path

    def __enter__(self):
        self.stream = self.path.open('a+b')
        if self.stream.tell() == 0:
            self.stream.write(b'0')
            self.stream.flush()
        self.stream.seek(0)
        try:
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.stream.close()
            raise RuntimeError('Another complete backup is already running.')
        return self

    def __exit__(self, *unused):
        self.stream.close()


def ensure_directory(path, boundary):
    current = path
    missing = []
    while current != boundary:
        if boundary not in current.parents:
            raise ValueError('Destination escaped the backup boundary.')
        if current.exists():
            info = current.lstat()
            if getattr(info, 'st_file_attributes', 0) & 0x400 or current.is_symlink():
                raise ValueError('Destination traverses a link: ' + str(current))
            if not stat.S_ISDIR(info.st_mode):
                raise ValueError('Destination parent is not a directory: ' + str(current))
            break
        missing.append(current)
        current = current.parent
    for directory in reversed(missing):
        directory.mkdir(exist_ok=True)


def archive_existing(path, relative, history, boundary):
    if not path.exists():
        return
    if not path.is_file() or path.is_symlink():
        raise ValueError('Refusing to replace a non-file destination: ' + str(path))
    previous = history / relative
    ensure_directory(previous.parent, boundary)
    if previous.exists():
        previous = previous.with_name(previous.name + '.' + uuid.uuid4().hex)
    path.chmod(path.stat().st_mode | stat.S_IWRITE)
    os.replace(path, previous)


def install_file(source, relative, info, destination, history, backup_root,
                 previous=None, owner=None, full_verify=False):
    target = destination / relative
    identity = f'{info.st_dev}:{info.st_ino}'
    cached = (previous and previous['size'] == info.st_size
              and previous['mtime'] == info.st_mtime_ns
              and previous['identity'] == identity)
    if cached and target.is_file() and not target.is_symlink():
        target_info = target.stat()
        if target_info.st_size == previous['size'] and target_info.st_mtime_ns == previous['dest_mtime']:
            if not full_verify or digest(source) == digest(target) == previous['sha256']:
                return {'relative': relative, 'size': info.st_size, 'mtime': info.st_mtime_ns,
                        'identity': identity, 'sha256': previous['sha256'],
                        'dest_mtime': target_info.st_mtime_ns, 'action': 'unchanged'}
    ensure_directory(target.parent, backup_root)
    temporary = target.parent / ('.backup-copy-' + uuid.uuid4().hex)
    try:
        if owner is not None:
            original = owner.result()
            os.link(destination / original['relative'], temporary)
            checksum = original['sha256']
            action = 'hardlink'
        else:
            calculated = hashlib.sha256()
            with source.open('rb') as input_stream, temporary.open('xb') as output_stream:
                while chunk := input_stream.read(4 * 1024 * 1024):
                    output_stream.write(chunk)
                    calculated.update(chunk)
            checksum = calculated.hexdigest()
            if digest(temporary) != checksum:
                raise ValueError('Destination checksum mismatch: ' + relative)
            shutil.copystat(source, temporary, follow_symlinks=False)
            action = 'copied'
        if fingerprint(source.stat()) != fingerprint(info):
            raise RuntimeError('Source changed during backup: ' + relative)
        archive_existing(target, relative, history, backup_root)
        os.replace(temporary, target)
        return {'relative': relative, 'size': info.st_size, 'mtime': info.st_mtime_ns,
                'identity': identity, 'sha256': checksum,
                'dest_mtime': target.stat().st_mtime_ns, 'action': action}
    finally:
        if temporary.exists():
            temporary.chmod(temporary.stat().st_mode | stat.S_IWRITE)
            temporary.unlink()


def write_json(path, value):
    temporary = path.with_name(path.name + '.partial')
    temporary.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    os.replace(temporary, path)


def sync(source, backup_root, workers=12, full_verify=False):
    source, backup_root = validate_roots(source, backup_root)
    state = backup_root / '.backup-state'
    state.mkdir(exist_ok=True)
    with BackupLock(state / 'sync.lock'):
        return sync_locked(source, backup_root, state, workers, full_verify)


def sync_locked(source, backup_root, state, workers, full_verify):
    run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
    initial = not (state / 'completed.json').exists()
    destination = state / 'incoming-project' if initial else backup_root / 'projet'
    destination.mkdir(exist_ok=True)
    history = backup_root / 'historique' / ('changed-' + run_id)
    started = time.monotonic()
    receipt = {'schema': 'bg2-full-project-backup-v1', 'run_id': run_id,
               'source': str(source), 'destination': str(destination),
               'source_commit': git_head(source), 'status': 'running',
               'verification': 'SHA-256 for every copied distinct file; verified ledger for unchanged files',
               'full_verify': full_verify, 'files': 0, 'logical_bytes': 0,
               'copied_bytes': 0, 'copied_files': 0, 'hardlink_paths': 0,
               'unchanged_files': 0, 'external_links': [], 'errors': []}
    receipt_path = state / ('run-' + run_id + '.json')
    write_json(receipt_path, receipt)
    database = sqlite3.connect(state / 'verified-files.sqlite3')
    database.execute('PRAGMA journal_mode=WAL')
    database.execute('CREATE TABLE IF NOT EXISTS files (relative TEXT PRIMARY KEY, size INTEGER, '
                     'mtime INTEGER, identity TEXT, sha256 TEXT, dest_mtime INTEGER, run_id TEXT)')
    prior = {row[0]: dict(zip(('size','mtime','identity','sha256','dest_mtime'), row[1:]))
             for row in database.execute('SELECT relative,size,mtime,identity,sha256,dest_mtime FROM files')}
    owners = {}
    pending = deque()
    batch = []
    next_progress = started + 15
    def accept(result):
        nonlocal next_progress
        receipt['files'] += 1
        receipt['logical_bytes'] += result['size']
        field = {'copied': 'copied_files', 'hardlink': 'hardlink_paths', 'unchanged': 'unchanged_files'}[result['action']]
        receipt[field] += 1
        if result['action'] == 'copied':
            receipt['copied_bytes'] += result['size']
        batch.append((result['relative'], result['size'], result['mtime'], result['identity'],
                      result['sha256'], result['dest_mtime'], run_id))
        if len(batch) >= 2000:
            database.executemany('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?)', batch)
            database.commit()
            batch.clear()
        now = time.monotonic()
        if now >= next_progress:
            receipt['elapsed_seconds'] = round(now-started, 1)
            write_json(receipt_path, receipt)
            emit('progress', files=receipt['files'], copied_GB=round(receipt['copied_bytes']/1e9, 3),
                 logical_GB=round(receipt['logical_bytes']/1e9, 3),
                 hardlink_paths=receipt['hardlink_paths'], seconds=receipt['elapsed_seconds'])
            next_progress = now + 15

    def take(task):
        while True:
            try:
                return task.result(timeout=5)
            except futures.TimeoutError:
                receipt['elapsed_seconds'] = round(time.monotonic()-started, 1)
                write_json(receipt_path, receipt)
                emit('working', files=receipt['files'], copied_GB=round(receipt['copied_bytes']/1e9,3),
                     seconds=receipt['elapsed_seconds'])

    try:
        # Use logical size as a conservative bound: hardlink preservation needs less space.
        if initial:
            planned_bytes = 0
            stack = [source]
            while stack:
                directory = stack.pop()
                with os.scandir(directory) as entries:
                    for entry in entries:
                        info = entry.stat(follow_symlinks=False)
                        if getattr(info, 'st_file_attributes', 0) & 0x400 or stat.S_ISLNK(info.st_mode):
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            stack.append(Path(entry.path))
                        elif stat.S_ISREG(info.st_mode):
                            planned_bytes += info.st_size
            receipt['planned_logical_bytes'] = planned_bytes
            required = int(planned_bytes * 1.1) + 100 * 1024 * 1024
            if shutil.disk_usage(backup_root).free < required:
                raise RuntimeError(f'Insufficient free space: conservative requirement {required} bytes.')
            emit('copy-starting', planned_GB=round(planned_bytes/1e9,3), destination=str(destination))
        with futures.ThreadPoolExecutor(max_workers=workers) as pool:
            stack = [source]
            while stack:
                directory = stack.pop()
                relative_directory = directory.relative_to(source)
                ensure_directory(destination / relative_directory, backup_root)
                with os.scandir(directory) as entries:
                    for entry in entries:
                        info = os.stat(entry.path, follow_symlinks=False)
                        path = Path(entry.path)
                        relative = path.relative_to(source).as_posix()
                        if getattr(info, 'st_file_attributes', 0) & 0x400 or stat.S_ISLNK(info.st_mode):
                            receipt['external_links'].append({'path': relative, 'target': os.readlink(path)})
                            continue
                        if stat.S_ISDIR(info.st_mode):
                            stack.append(path)
                        elif stat.S_ISREG(info.st_mode):
                            if relative.startswith('.git/') and relative.endswith('.lock'):
                                continue
                            key = (info.st_dev, info.st_ino) if info.st_ino else ('path', relative)
                            owner = owners.get(key) if info.st_nlink > 1 else None
                            task = pool.submit(install_file, path, relative, info, destination, history,
                                               backup_root, prior.get(relative), owner, full_verify)
                            if info.st_nlink > 1:
                                owners.setdefault(key, task)
                            pending.append(task)
                            if len(pending) >= workers * 4:
                                accept(take(pending.popleft()))
            while pending:
                accept(take(pending.popleft()))
        database.executemany('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?,?,?)', batch)
        database.commit()
        if git_head(source) != receipt['source_commit']:
            raise RuntimeError('Source Git HEAD changed during backup; repeat synchronization.')
        # Re-enumerate source metadata to catch files added/changed/deleted after their copy.
        expected = {row[0]: (row[1], row[2]) for row in database.execute(
            'SELECT relative,size,mtime FROM files WHERE run_id=?', (run_id,))}
        actual = {}
        stack = [source]
        while stack:
            directory = stack.pop()
            with os.scandir(directory) as entries:
                for entry in entries:
                    info = entry.stat(follow_symlinks=False)
                    relative = Path(entry.path).relative_to(source).as_posix()
                    if getattr(info, 'st_file_attributes', 0) & 0x400 or stat.S_ISLNK(info.st_mode):
                        continue
                    if stat.S_ISDIR(info.st_mode):
                        stack.append(Path(entry.path))
                    elif stat.S_ISREG(info.st_mode) and not (relative.startswith('.git/') and relative.endswith('.lock')):
                        actual[relative] = (info.st_size, info.st_mtime_ns)
        if actual != expected:
            differences = list(set(actual) ^ set(expected))
            differences.extend(p for p in actual.keys() & expected.keys() if actual[p] != expected[p])
            raise RuntimeError('Source tree changed during backup: ' + ', '.join(differences[:20]))
        if initial:
            project = backup_root / 'projet'
            baseline = backup_root / 'historique' / ('projet-before-full-backup-' + run_id)
            ensure_directory(baseline.parent, backup_root)
            for move_path in (project, baseline, destination):
                if backup_root not in move_path.resolve().parents:
                    raise ValueError('Project promotion escaped the configured backup root.')
            if project.exists():
                os.replace(project, baseline)
                receipt['previous_project_preserved'] = str(baseline)
            try:
                os.replace(destination, project)
            except BaseException:
                if baseline.exists() and not project.exists():
                    os.replace(baseline, project)
                raise
            destination = project
        receipt.update(status='complete', destination=str(destination),
                       elapsed_seconds=round(time.monotonic()-started, 1))
        write_json(receipt_path, receipt)
        write_json(state / 'completed.json', receipt)
        emit('complete', **receipt)
        return receipt
    except BaseException as exc:
        receipt['status'] = 'incomplete'
        receipt['errors'].append(str(exc))
        receipt['elapsed_seconds'] = round(time.monotonic()-started, 1)
        write_json(receipt_path, receipt)
        emit('incomplete', error=str(exc), receipt=str(receipt_path))
        raise
    finally:
        database.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT)
    parser.add_argument('--backup-root', type=Path)
    parser.add_argument('--workers', type=int, default=12)
    parser.add_argument('--full-verify', action='store_true')
    parser.add_argument('--from-git-hook', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.workers <= 32:
        parser.error('--workers must be between 1 and 32')
    if args.from_git_hook:
        canonical = get_path('full_project_backup_source', required=True)
        if args.source.resolve() != canonical.resolve():
            emit('skipped', reason='This checkout is not the configured backup source.')
            return
    backup_root = args.backup_root or get_path('full_project_backup_root', required=True)
    sync(args.source, backup_root, args.workers, args.full_verify)


if __name__ == '__main__':
    main()
