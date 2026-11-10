"""Snapshot only current installer inputs; never overwrite or purge existing backups."""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import functools
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import time
import uuid
from collections import deque
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from workspace_paths import ROOT, get_path
from sync_full_project_backup import digest, ensure_directory, fingerprint, git_head


RELEASE = 'releases/BG2-HD-Upscale'
PAYLOAD = RELEASE + '/bg2hd/payload-allvalidated'
METADATA_DIRS = {'bg2hd', 'manifests', 'tools', 'bootstrap', 'schemas', 'docs'}


def emit(event, **values):
    print(json.dumps({'event': event, **values}, ensure_ascii=True), flush=True)


def safe_relative(value):
    path = PurePosixPath(value)
    if (not value or '\\' in value or ':' in value or path.is_absolute()
            or any(part in ('..', '.') for part in value.split('/'))):
        raise ValueError('Unsafe relative path: ' + value)
    return path.as_posix()


@dataclass(frozen=True)
class Entry:
    relative: str
    size: int
    signature: tuple
    sha256: str | None = None


@functools.lru_cache(maxsize=4096)
def check_source_parent(root, parent):
    # Resolve directories once, rather than walking every ancestor for every frame.
    if not parent.resolve().is_relative_to(root.resolve()):
        raise ValueError('Source escaped workspace: ' + str(parent))


def describe(root, relative, expected_size=None, sha256=None):
    relative = safe_relative(relative)
    source = root / relative
    check_source_parent(root, source.parent)
    info = source.lstat()
    if (not stat.S_ISREG(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400):
        raise ValueError('Expected a regular source file: ' + relative)
    if expected_size is not None and info.st_size != expected_size:
        raise ValueError('Payload size differs from content.json: ' + relative)
    if sha256 is not None and not re.fullmatch('[0-9a-fA-F]{64}', sha256):
        raise ValueError('Invalid manifest SHA-256: ' + relative)
    return Entry(relative, info.st_size, fingerprint(info), sha256)


def build_plan(root):
    root = root.resolve()
    content_path = root / RELEASE / 'manifests/content.json'
    content_bytes = content_path.read_bytes()
    content = json.loads(content_bytes)
    release = json.loads((root / RELEASE / 'manifests/release.json').read_bytes())
    entries = {}
    for item in content['entries']:
        group = safe_relative(item['payload_group'])
        name = PurePosixPath(safe_relative(item['source'])).name
        relative = f'{PAYLOAD}/{group}/{name}'
        key = relative.casefold()
        if key in entries:
            raise ValueError('Duplicate payload path: ' + relative)
        entries[key] = describe(root, relative, item['bytes'], item['sha256'])
    if not entries:
        raise ValueError('Empty installer payload')
    payload_files = len(entries)
    payload_bytes = sum(item.size for item in entries.values())
    tracked = subprocess.check_output(
        ['git', '-C', str(root), 'ls-files', '-z', '--', RELEASE,
         'LICENSE', 'THIRD_PARTY_NOTICES.md', 'licenses'])
    metadata = []
    for value in tracked.split(b'\0'):
        if not value:
            continue
        relative = value.decode('utf-8')
        if relative.startswith(RELEASE + '/'):
            parts = relative[len(RELEASE) + 1:].split('/')
            if len(parts) > 1 and parts[0] not in METADATA_DIRS:
                continue
            if parts[:2] in (['bg2hd', 'payload'], ['bg2hd', 'payload-allvalidated']):
                continue
        metadata.append(relative)
    # These delivered prerequisites may be ignored by Git.
    metadata.extend(RELEASE + '/release-inputs/weidu/' + name
                    for name in ('setup-bg2hd.exe', 'weidu-v249.00.tar.gz'))
    for relative in metadata:
        key = relative.casefold()
        if key not in entries:
            entries[key] = describe(root, relative)
    manifest_relative = RELEASE + '/manifests/content.json'
    pinned_manifest = hashlib.sha256(content_bytes).hexdigest()
    entry = entries[manifest_relative.casefold()]
    entries[manifest_relative.casefold()] = Entry(
        entry.relative, entry.size, entry.signature, pinned_manifest)
    return list(entries.values()), {
        'release_version': release['version'], 'release_status': release['release_status'],
        'source_commit': git_head(root), 'content_manifest_sha256': pinned_manifest,
        'payload_files': payload_files, 'payload_bytes': payload_bytes,
    }


def copy_verified(root, destination, entry):
    source = root / entry.relative
    if fingerprint(source.stat()) != entry.signature:
        raise RuntimeError('Source changed since planning: ' + entry.relative)
    target = destination / entry.relative
    calculated = hashlib.sha256()
    copied = 0
    # Exclusive creation: cannot replace an existing file, even on an incomplete run.
    with source.open('rb') as input_stream, target.open('xb') as output_stream:
        while chunk := input_stream.read(4 * 1024 * 1024):
            output_stream.write(chunk)
            calculated.update(chunk)
            copied += len(chunk)
    checksum = calculated.hexdigest()
    if copied != entry.size or (entry.sha256 and checksum.lower() != entry.sha256.lower()):
        raise ValueError('Source differs from content.json: ' + entry.relative)
    if digest(target) != checksum:
        raise ValueError('Destination SHA-256 mismatch: ' + entry.relative)
    if fingerprint(source.stat()) != entry.signature:
        raise RuntimeError('Source changed during copy: ' + entry.relative)
    shutil.copystat(source, target, follow_symlinks=False)
    return {'relative': entry.relative, 'bytes': copied, 'sha256': checksum}


def write_new_json(path, value):
    with path.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def snapshot(root, backup_root, entries, metadata, workers=4):
    root, backup_root = root.resolve(), backup_root.resolve()
    if (root == backup_root or backup_root.is_relative_to(root)
            or root.is_relative_to(backup_root)):
        raise ValueError('Backup and source must be separate, non-nested directories')
    total = sum(item.size for item in entries)
    if shutil.disk_usage(backup_root).free < total + 1024**3:
        raise ValueError('Insufficient free space for a new installer snapshot')
    version = safe_relative(metadata['release_version'])
    if '/' in version:
        raise ValueError('Release version must be a single directory name')
    parent = backup_root / 'installateur' / version
    ensure_directory(parent, backup_root)
    run_id = time.strftime('%Y%m%dT%H%M%SZ', time.gmtime()) + '-' + uuid.uuid4().hex[:8]
    target = parent / run_id
    target.mkdir()  # No exist_ok: an existing snapshot is never reused or overwritten.
    destination = target / 'files'
    destination.mkdir()
    receipt = dict(metadata, schema='bg2-installer-backup-v1', status='running',
                   run_id=run_id, source=str(root), destination=str(target),
                   planned_files=len(entries), planned_bytes=total,
                   verified_files=0, verified_bytes=0,
                   verification='source copy SHA-256; destination reread; payload manifest SHA-256')
    write_new_json(target / 'running.json', receipt)
    started = time.monotonic()
    emit('copy-starting', destination=str(target), files=len(entries), GB=round(total / 1e9, 3))
    try:
        directories = sorted({(destination / entry.relative).parent for entry in entries})
        for directory in directories:
            ensure_directory(directory, backup_root)
        next_progress = started + 15
        with (target / 'inventory.jsonl').open('x', encoding='utf-8') as inventory:
            with futures.ThreadPoolExecutor(max_workers=workers) as pool:
                pending = deque()

                def accept(task):
                    nonlocal next_progress
                    result = task.result()
                    inventory.write(json.dumps(result) + '\n')
                    receipt['verified_files'] += 1
                    receipt['verified_bytes'] += result['bytes']
                    now = time.monotonic()
                    if now >= next_progress:
                        inventory.flush()
                        emit('progress', files=receipt['verified_files'], total_files=len(entries),
                             verified_GB=round(receipt['verified_bytes'] / 1e9, 3),
                             total_GB=round(total / 1e9, 3), seconds=round(now - started))
                        next_progress = now + 15

                for entry in entries:
                    pending.append(pool.submit(copy_verified, root, destination, entry))
                    if len(pending) >= workers * 2:
                        accept(pending.popleft())
                while pending:
                    accept(pending.popleft())
        for entry in entries:
            if fingerprint((root / entry.relative).stat()) != entry.signature:
                raise RuntimeError('Source changed before completion: ' + entry.relative)
        receipt.update(status='complete', elapsed_seconds=round(time.monotonic() - started, 1),
                       inventory_sha256=digest(target / 'inventory.jsonl'))
        write_new_json(target / 'completed.json', receipt)
        emit('complete', **receipt)
        return target
    except BaseException as error:
        receipt.update(status='incomplete', error=str(error),
                       elapsed_seconds=round(time.monotonic() - started, 1))
        write_new_json(target / 'failed.json', receipt)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', action='store_true', help='Read selected source metadata only; no H: writes')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.workers <= 16:
        parser.error('--workers must be between 1 and 16')
    entries, metadata = build_plan(ROOT)
    backup_root = get_path('installer_backup_root', required=True)
    emit('plan', **metadata, files=len(entries), bytes=sum(item.size for item in entries),
         GB=round(sum(item.size for item in entries) / 1e9, 3), backup_root=str(backup_root))
    if not args.plan:
        snapshot(ROOT, backup_root, entries, metadata, args.workers)


if __name__ == '__main__':
    main()
