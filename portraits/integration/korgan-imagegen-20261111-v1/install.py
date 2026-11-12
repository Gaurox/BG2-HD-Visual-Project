"""Install/verify/restore only Korgan's three BMP overrides, game closed."""
import argparse
import csv
import hashlib
import io
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

NAMES = ('NKORGANL.bmp', 'NKORGANM.bmp', 'NKORGANS.bmp')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_optional(path):
    if path.is_symlink():
        raise RuntimeError('Symlink refused: ' + str(path))
    return path.read_bytes() if path.exists() else None


def stopped():
    result = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], check=True, capture_output=True)
    names = {row[0].lower() for row in csv.reader(io.StringIO(result.stdout.decode('cp1252', errors='replace'))) if row}
    active = names & {'baldur.exe', 'baldurreal.exe', 'baldurii.exe', 'infinityloader.exe'}
    if active:
        raise RuntimeError('Close BG2EE and InfinityLoader: ' + ', '.join(sorted(active)))


def replace(path, data):
    if data is None:
        path.unlink(missing_ok=True)
        return
    temporary = path.with_name(path.name + '.korgan-install-stage')
    with temporary.open('xb') as handle:
        handle.write(data)
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json(path, value):
    replace(path, (json.dumps(value, indent=2) + '\n').encode('utf-8'))


def transact(override, before, after):
    stopped()
    for name, data in before.items():
        if read_optional(override / name) != data:
            raise RuntimeError('Live state changed: ' + name)
    try:
        for name, data in after.items():
            replace(override / name, data)
        for name, data in after.items():
            assert read_optional(override / name) == data, name
    except BaseException:
        for name, data in before.items():
            replace(override / name, data)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'verify', 'restore'))
    parser.add_argument('--receipt', type=Path)
    args = parser.parse_args()
    game = get_path('bg2ee_game_root', required=True).resolve()
    override = game / 'override'
    if override.is_symlink() or not override.is_dir():
        raise RuntimeError('Expected ordinary game override directory')
    if args.action != 'install':
        if args.receipt is None:
            parser.error('--receipt required')
        receipt_path = args.receipt.resolve()
        receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
        if receipt['schema'] != 'bg2-korgan-portrait-test-install-v1' or set(receipt['files']) != set(NAMES):
            raise RuntimeError('Wrong receipt scope')
        if receipt['game'] != 'config://bg2ee_game_root' or receipt['status'] != 'installed':
            raise RuntimeError('Receipt is not an active installed test')
        installed = {name: read_optional(override / name) for name in NAMES}
        for name, row in receipt['files'].items():
            if installed[name] is None or digest(installed[name]) != row['installed_sha256']:
                raise RuntimeError('Installed file diverged: ' + name)
        if args.action == 'verify':
            print('Verified: all three installed Korgan BMPs match the receipt.')
            return
        before = {}
        for name, row in receipt['files'].items():
            data = (receipt_path.parent / 'before' / name).read_bytes() if row['before_sha256'] else None
            if data is not None and digest(data) != row['before_sha256']:
                raise RuntimeError('Backup diverged: ' + name)
            before[name] = data
        transact(override, installed, before)
        write_json(receipt_path.parent / 'restoration.json', dict(status='restored',
            time_utc=datetime.now(timezone.utc).isoformat(), receipt=receipt_path.name))
        print('Restored exact prior Korgan overrides; native BIF resources remain intact.')
        return
    stopped()
    manifest = json.loads((HERE / 'assets.json').read_text(encoding='utf-8'))
    changes = {}
    for row in manifest['assets']:
        name = row['resource'] + '.bmp'
        if name not in NAMES or row['file'] != 'assets/' + name:
            raise RuntimeError('Unexpected portrait asset')
        data = (HERE / row['file']).read_bytes()
        if digest(data) != row['sha256']:
            raise RuntimeError('Asset changed: ' + name)
        changes[name] = data
    if set(changes) != set(NAMES):
        raise RuntimeError('Incomplete Korgan set')
    before = {name: read_optional(override / name) for name in NAMES}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    snapshot = HERE / 'backups' / stamp
    (snapshot / 'before').mkdir(parents=True, exist_ok=False)
    for name, data in before.items():
        if data is not None:
            (snapshot / 'before' / name).write_bytes(data)
    receipt = dict(schema='bg2-korgan-portrait-test-install-v1', status='prepared',
        time_utc=stamp, game='config://bg2ee_game_root',
        files={name: dict(before_sha256=digest(before[name]) if before[name] is not None else None,
                         installed_sha256=digest(data)) for name, data in changes.items()},
        qa='awaiting-user-ingame-test', release='unchanged')
    receipt_path = snapshot / 'receipt.json'
    write_json(receipt_path, receipt)
    try:
        transact(override, before, changes)
    except BaseException:
        receipt['status'] = 'not-installed'
        write_json(receipt_path, receipt)
        raise
    receipt['status'] = 'installed'
    write_json(receipt_path, receipt)
    print(json.dumps(dict(receipt=str(receipt_path), files=list(changes)), indent=2))


if __name__ == '__main__':
    main()
