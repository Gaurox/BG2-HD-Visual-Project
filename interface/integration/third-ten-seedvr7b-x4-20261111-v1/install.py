"""Install/restore ten additional 7B UI compositions transactionally, game closed."""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def stopped():
    tasks = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], check=True, capture_output=True)
    names = {r[0].lower() for r in csv.reader(io.StringIO(tasks.stdout.decode('cp1252', errors='replace'))) if r}
    active = names & {'baldur.exe', 'baldurreal.exe', 'baldurii.exe', 'infinityloader.exe'}
    if active:
        raise RuntimeError('Quitter jeu et InfinityLoader : ' + ', '.join(sorted(active)))


def replace(path, data):
    temp = path.with_name(path.name + '.four-menus-stage')
    if temp.exists():
        raise RuntimeError(f'Staging exists: {temp}')
    try:
        temp.write_bytes(data)
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path)
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    game = get_path('bg2ee_game_root').resolve()
    stopped()
    if args.restore:
        receipt = json.loads(args.restore.read_text(encoding='utf-8'))
        snapshot = args.restore.parent
        for name, row in receipt['files'].items():
            target = (game / name).resolve()
            if not target.is_relative_to(game) or digest(target.read_bytes()) != row['installed_sha256']:
                raise RuntimeError(f'Installed state changed: {name}')
            if row['before_sha256'] is not None and digest((snapshot / name).read_bytes()) != row['before_sha256']:
                raise RuntimeError(f'Backup changed: {name}')
        stopped()
        for name, row in receipt['files'].items():
            if row['before_sha256'] is None:
                (game / name).unlink()
            else:
                replace(game / name, (snapshot / name).read_bytes())
        print('Exact prior DLL/INI/atlases restored.')
        return
    if not args.dll:
        parser.error('--dll required')
    dll = args.dll.read_bytes()
    if dll[:2] != b'MZ' or b'EnableGameplayMenusX4' not in dll:
        raise RuntimeError('Expected four-menu DLL')
    ini = (game / 'InfinityEngine-Enhancer.ini').read_bytes()
    if re.search(br'(?im)^\s*EnableMenuX2Test\s*=\s*(true|1)\s*$', ini):
        raise RuntimeError('x2 menu mode would hide the x4 test')
    key = br'(?im)^([ \t]*EnableGameplayMenusX4[ \t]*=[ \t]*)([^\r\n]*)'
    if re.search(key, ini):
        candidate, count = re.subn(key, lambda m: m[1] + b'true', ini)
        if count != 1:
            raise RuntimeError('Duplicate gameplay flag')
    else:
        header = re.search(br'(?im)^\[Shaders\][ \t]*(\r?\n)', ini)
        if not header:
            raise RuntimeError('Missing Shaders section')
        addition = b'EnableGameplayMenusX4 = true' + header[1]
        candidate = ini[:header.end()] + addition + ini[header.end():]
        assert candidate.replace(addition, b'', 1) == ini
    changes = {'InfinityEngine-Enhancer.dll': dll, 'InfinityEngine-Enhancer.ini': candidate}
    assets = json.loads((HERE / 'assets.json').read_text())
    for asset in assets:
        content = (HERE / 'assets' / asset['asset']).read_bytes()
        assert digest(content) == asset['sha256']
        if asset.get('baseline') == 'installed active x4':
            assert digest((game / 'iee-assets' / asset['asset']).read_bytes()) == asset['baseline_sha256'], 'Accepted shared atlas changed since build'
        changes['iee-assets/' + asset['asset']] = content
    before = {name: (game / name).read_bytes() if (game / name).exists() else None for name in changes}
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    snapshot = HERE / 'backups' / stamp
    snapshot.mkdir(parents=True, exist_ok=False)
    for name, data in before.items():
        if data is not None:
            path = snapshot / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    stopped()
    for name, data in before.items():
        assert ((game / name).read_bytes() if (game / name).exists() else None) == data, 'Live state changed during preparation'
    try:
        for name, content in changes.items():
            replace(game / name, content)
        assert all((game / name).read_bytes() == content for name, content in changes.items())
    except BaseException:
        for name, data in before.items():
            if data is None:
                (game / name).unlink(missing_ok=True)
            else:
                replace(game / name, data)
        raise
    receipt = dict(schema='bg2-four-menus-install-v1', time_utc=stamp, game='config://bg2ee_game_root',
                   files={n: dict(before_sha256=digest(before[n]) if before[n] is not None else None,
                                  installed_sha256=digest(data)) for n, data in changes.items()},
                   scope=['GUISTBSC', 'GUISTDOB', 'GUISTIDB', 'GUISTROB', 'GUIMAPWB', 'GUICREDT', 'GUISAVEB', 'GUICGB', 'GUIHSB', 'GMPWMSG0'],
                   qa='awaiting-user-ingame-test', release='unchanged')
    (snapshot / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(receipt=str(snapshot / 'receipt.json'), files=len(changes))))


if __name__ == '__main__':
    main()
