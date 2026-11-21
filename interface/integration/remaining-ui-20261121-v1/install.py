"""Install and restore the UI review pack without staging or changing the release."""
import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('previous_install',
    HERE.parent / 'seventh-ten-seedvr7b-x4-20261111-v1/install.py')
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
from workspace_paths import get_path

GAME = get_path('bg2ee_game_root').resolve()
MANIFEST = HERE / 'pack.json'
RENDERER = (ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/build-ui-review-20261121-v1'
            / 'Release/InfinityEngine-Enhancer.dll')
DLL_NAME = 'InfinityEngine-Enhancer.dll'


def digest(path):
    if not path.is_file():
        return None
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(path)


def game_target(name):
    target = (GAME / name).resolve()
    if not target.is_relative_to(GAME) or not target.parent.is_dir():
        raise RuntimeError(f'Invalid game destination: {name}')
    return target


def replace(target, source):
    if source is None:
        target.unlink(missing_ok=True)
        return
    with tempfile.NamedTemporaryFile(dir=target.parent, prefix='bg2-ui-stage-', delete=False) as handle:
        temporary = Path(handle.name)
    try:
        shutil.copyfile(source, temporary)
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def transaction(targets, sources, rollback, expected):
    previous.stopped()
    changed = []
    try:
        for name, target in targets.items():
            replace(target, sources[name])
            changed.append(name)
        for name, target in targets.items():
            if digest(target) != expected[name]:
                raise RuntimeError(f'Installed hash mismatch: {name}')
    except BaseException:
        for name in reversed(changed):
            replace(targets[name], rollback[name])
        raise


def install():
    previous.stopped()
    pack = json.loads(MANIFEST.read_text(encoding='utf-8'))
    ini = (GAME / 'InfinityEngine-Enhancer.ini').read_bytes()
    if not re.search(br'(?im)^[ \t]*EnableGameplayMenusX4\s*=\s*(true|1)[ \t]*\r?$', ini):
        raise RuntimeError('EnableGameplayMenusX4 must be active in the installed renderer configuration.')
    if re.search(br'(?im)^[ \t]*EnableMenuX2Test\s*=\s*(true|1)[ \t]*\r?$', ini):
        raise RuntimeError('The renderer is configured to run an x2 menu test.')
    assert b'ui-review-atlases.txt' in RENDERER.read_bytes()
    expected = dict(pack['files'], **{DLL_NAME: digest(RENDERER)})
    sources = {name: HERE / 'pack' / name for name in pack['files']}
    sources[DLL_NAME] = RENDERER
    targets = {name: game_target(name) for name in sources}
    if (HERE / 'installed.json').exists():
        raise RuntimeError('Use the active receipt or restore it before another install.')
    replaceable = {r['path'] for r in pack['resources'].values()} | {DLL_NAME}
    before = {}
    for name in sources:
        if digest(sources[name]) != expected[name]:
            raise RuntimeError(f'Pack file mismatch: {name}')
        before[name] = digest(targets[name])
        if before[name] is not None and name not in replaceable:
            raise RuntimeError(f'New pack file would collide: {name}')

    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    snapshot = HERE / 'backups' / stamp
    snapshot.mkdir(parents=True)
    backup = {}
    for name, original_sha in before.items():
        path = snapshot / name if original_sha else None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(targets[name], path)
            assert digest(path) == original_sha, name
        backup[name] = path

    receipt = dict(schema='bg2-ui-review-install-v1', time_utc=stamp,
                   backup=(snapshot / 'receipt.json').relative_to(ROOT).as_posix(),
                   scope=sorted(pack['resources']),
                   files={name: dict(before_sha256=before[name], installed_sha256=expected[name])
                          for name in targets})
    write_json(snapshot / 'receipt.json', receipt)
    if any(digest(targets[name]) != prior for name, prior in before.items()):
        raise RuntimeError('The installation changed during backup.')
    transaction(targets, sources, backup, expected)
    write_json(HERE / 'installed.json', receipt)
    print(f'{len(targets)} files installed and verified. Receipt: {snapshot / "receipt.json"}')


def restore():
    previous.stopped()
    receipt_path = HERE / 'installed.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    snapshot = (ROOT / receipt['backup']).resolve().parent
    if not snapshot.is_relative_to(HERE / 'backups'):
        raise RuntimeError('Invalid backup receipt.')
    rows = receipt['files']
    targets = {name: game_target(name) for name in rows}
    expected = {name: row['before_sha256'] for name, row in rows.items()}
    sources = {name: snapshot / name if prior else None for name, prior in expected.items()}
    rollback = {name: HERE / 'pack' / name for name in rows}
    rollback[DLL_NAME] = RENDERER
    for name, row in rows.items():
        if digest(targets[name]) != row['installed_sha256'] or digest(rollback[name]) != row['installed_sha256']:
            raise RuntimeError(f'Installed bytes changed: {name}')
        if sources[name] and digest(sources[name]) != expected[name]:
            raise RuntimeError(f'Backup bytes changed: {name}')
    transaction(targets, sources, rollback, expected)
    receipt_path.replace(snapshot / 'restored.json')
    sys.path.insert(0, str(ROOT / 'interface/tracking'))
    from manage import TRACKER, export, read
    tracking = read()
    evidence = receipt_path.relative_to(ROOT).as_posix()
    for item in tracking['resources']:
        if evidence not in item['installation'].get('evidence', []):
            continue
        item['installation'] = {'state': 'not-reconciled'}
        if item['next_action'] == 'user-ingame-test-remaining-ui-campaign':
            item['next_action'] = 'review-remaining-ui-campaign'
    write_json(TRACKER, tracking)
    export(tracking)
    print(f'{len(targets)} files restored.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['install', 'restore'])
    args = parser.parse_args()
    {'install': install, 'restore': restore}[args.action]()


if __name__ == '__main__':
    main()
