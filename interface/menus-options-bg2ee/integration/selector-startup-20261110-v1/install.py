"""Install only the selector renderer/INI change, with an exact guarded restore."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = next(p for p in Path(__file__).resolve().parents if (p / 'pipeline/scripts').is_dir())
sys.path.insert(0, str(REPO / 'pipeline/scripts'))
from workspace_paths import get_path

HERE = Path(__file__).resolve().parent
NAMES = ('InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stopped():
    result = subprocess.run(['tasklist', '/fo', 'csv', '/nh'], check=True, capture_output=True)
    tasks = {row[0].lower() for row in csv.reader(io.StringIO(result.stdout.decode('cp1252', errors='replace'))) if row}
    active = tasks & {'baldur.exe', 'baldurreal.exe', 'infinityloader.exe', 'baldurii.exe'}
    if active:
        raise RuntimeError('Quitter le jeu et InfinityLoader : ' + ', '.join(sorted(active)))


def replace(path, data):
    temporary = path.with_name(path.name + '.selector-stage')
    if temporary.exists():
        raise RuntimeError(f'Staging déjà présent : {temporary}')
    try:
        temporary.write_bytes(data)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dll', type=Path)
    parser.add_argument('--restore', type=Path)
    args = parser.parse_args()
    game = get_path('bg2ee_game_root')
    stopped()
    if args.restore:
        receipt = json.loads(args.restore.read_text(encoding='utf-8'))
        backup = args.restore.parent
        if any(sha(game / n) != receipt['installed'][n] for n in NAMES):
            raise RuntimeError('Installation modifiée depuis ce reçu ; restauration automatique refusée')
        if any(sha(backup / n) != receipt['before'][n] for n in NAMES):
            raise RuntimeError('Sauvegarde différente du reçu')
        for name in NAMES:
            replace(game / name, (backup / name).read_bytes())
        print('DLL et INI antérieurs restaurés exactement.')
        return
    if not args.dll or not args.dll.is_file():
        parser.error('--dll requis pour installer')
    dll = args.dll.read_bytes()
    if dll[:2] != b'MZ' or b'EnableSelectorX4' not in dll:
        raise RuntimeError('DLL sélecteur attendue')
    audit_path = REPO / 'interface/menus-options-bg2ee/analysis/selector-20261110-v1/evidence/audit.json'
    audit = json.loads(audit_path.read_text(encoding='utf-8'))
    asset_hashes = {}
    for page in audit['pages']:
        if page['production']:
            name = Path(page['production']).name
            asset_hashes[name] = sha(game / 'iee-assets' / name)
            if asset_hashes[name] != page['production_sha256']:
                raise RuntimeError(f'Atlas installé différent de la production analysée : {name}')
    ini = (game / NAMES[1]).read_bytes()
    if re.search(br'(?im)^\s*EnableMenuX2Test\s*=\s*(true|1)\s*$', ini):
        raise RuntimeError('Un mode x2 actif masquerait le sélecteur x4')
    key = br'(?im)^([ \t]*EnableSelectorX4[ \t]*=[ \t]*)([^\r\n]*)'
    if re.search(key, ini):
        candidate, count = re.subn(key, lambda m: m[1] + b'true', ini)
        if count != 1:
            raise RuntimeError('Clé sélecteur dupliquée')
    else:
        header = re.search(br'(?im)^\[Shaders\][ \t]*(\r?\n)', ini)
        if not header:
            raise RuntimeError('Section [Shaders] absente')
        addition = b'EnableSelectorX4 = true' + header[1]
        candidate = ini[:header.end()] + addition + ini[header.end():]
        assert candidate.replace(addition, b'', 1) == ini
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup = HERE / ('backup-' + stamp)
    backup.mkdir(exist_ok=False)
    for name in NAMES:
        shutil.copy2(game / name, backup / name)
    before = {name: sha(backup / name) for name in NAMES}
    stopped()
    if any(sha(game / name) != before[name] for name in NAMES):
        raise RuntimeError('Fichiers modifiés pendant la préparation')
    try:
        replace(game / NAMES[0], dll)
        replace(game / NAMES[1], candidate)
        assert (game / NAMES[0]).read_bytes() == dll
        assert (game / NAMES[1]).read_bytes() == candidate
        assert all(sha(game / 'iee-assets' / name) == digest for name, digest in asset_hashes.items())
    except BaseException:
        for name in NAMES:
            replace(game / name, (backup / name).read_bytes())
        raise
    receipt = dict(schema='bg2-selector-install-v1', time_utc=stamp,
                   game='config://bg2ee_game_root', before=before,
                   installed={name: sha(game / name) for name in NAMES},
                   assets_unchanged=asset_hashes, config_change='[Shaders] EnableSelectorX4=true only',
                   source_dll=str(args.dll.resolve()))
    (backup / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'receipt': str(backup / 'receipt.json'), 'installed': receipt['installed']}))


if __name__ == '__main__':
    main()
