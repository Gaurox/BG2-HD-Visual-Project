"""Install or restore the local atlas trial with verified, per-file backups."""
import argparse
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from zipfile import ZipFile

import test_atlas as trial
from workspace_paths import get_path

RUN = trial.HERE / 'run'
HISTORY = RUN / 'installation'
RECEIPT = HISTORY / 'installed.json'
PACK = RUN / 'maps-shared-atlas-test.zip'
STOCK_REPORT = trial.HERE / 'results.json'


def require_closed():
    result = subprocess.run(['powershell.exe', '-NoLogo', '-NoProfile', '-NonInteractive', '-Command',
        'if (Get-Process -Name Baldur,BaldurReal,BaldurII,InfinityLoader -ErrorAction SilentlyContinue) { exit 3 }'],
        check=False)
    if result.returncode == 3:
        raise RuntimeError('Fermer BG2EE et InfinityLoader avant la substitution.')
    result.check_returncode()


def is_link(path):
    return bool(path.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT)


def paths():
    game = get_path('bg2ee_game_root').resolve(strict=True)
    override = game / 'override'
    if not override.is_dir() or is_link(override) or override.resolve(strict=True).parent != game:
        raise RuntimeError('Dossier override inattendu.')
    return game, override


def exact_paths(override):
    return {path.name.upper(): path for path in override.iterdir()}


def atomic_write(path, data):
    descriptor, name = tempfile.mkstemp(prefix=f'.{path.name}.atlas-', dir=path.parent)
    pending = Path(name)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
        os.replace(pending, path)
    finally:
        pending.unlink(missing_ok=True)


def save_state(receipt, state):
    receipt['state'] = state
    raw = json.dumps(receipt, indent=2, ensure_ascii=False) + '\n'
    atomic_write(RECEIPT, raw.encode('utf-8'))


def switch(destination, current, target):
    require_closed()
    changed = []
    try:
        for name, previous in current.items():
            path = destination[name]
            if is_link(path) or path.read_bytes() != previous:
                raise RuntimeError(f'Fichier modifié pendant la préparation: {name}')
        for name, data in target.items():
            atomic_write(destination[name], data)
            changed.append(name)
        for name, data in target.items():
            if destination[name].read_bytes() != data:
                raise RuntimeError(f'Échec de la relecture: {name}')
    except Exception:
        for name in reversed(changed):
            atomic_write(destination[name], current[name])
        raise


def candidate():
    report = json.loads(STOCK_REPORT.read_bytes())
    if trial.pvrz.file_sha(PACK) != report['shared_atlas_zip_sha256']:
        raise RuntimeError('Empreinte du pack de test différente du rapport.')
    files = {}
    with ZipFile(PACK) as pack:
        aliases = json.loads(pack.read(trial.INDEX))
        for name, digest in aliases.items():
            trial.pvrz.path_for(trial.ROOT, name)
            files[Path(name).name.upper()] = pack.read(trial.pvrz.blob_name(digest))
        for family in trial.FAMILIES:
            for area in family:
                files[f'{area}.TIS'] = pack.read(f'override/{area}.TIS')
    if len(files) != report['restored_files']:
        raise RuntimeError('Inventaire inattendu dans le ZIP de test.')
    return files, report


def install(game, override):
    if HISTORY.exists():
        raise RuntimeError('Un essai local existe déjà.')
    require_closed()
    ini = (game / 'InfinityEngine-Enhancer.ini').read_text(encoding='utf-8-sig', errors='replace')
    if re.search(r'^\s*Enable(?:TileMipmaps|AnisotropicFiltering)\s*=\s*(?:true|yes|1|on)\b', ini, re.I | re.M):
        raise RuntimeError('Réglage de filtrage hors du test à marge de 4 pixels.')
    new, report = candidate()
    active = exact_paths(override)
    manifest = json.loads(trial.pvrz.CONTENT.read_bytes())
    baseline = {Path(r['destination']).name.upper(): r['sha256'].lower()
                for r in manifest['entries'] if r['kind'] == 'map'}
    bifs, key_entries = trial.load_key()
    wed_key = {name.upper(): loc for name, kind, loc in key_entries if kind == 0x03e9}
    for family in report['families']:
        for area, check in family['checks'].items():
            local = active.get(f'{area}.WED')
            if local and is_link(local):
                raise RuntimeError(f'WED actif irrégulier: {area}')
            wed = local.read_bytes() if local else trial.resolve_resource(bifs, wed_key[area])[0]
            if trial.pvrz.sha(wed) != check['wed']['sha256']:
                raise RuntimeError(f'WED actif différent de la référence vérifiée: {area}')
    originals = {}
    for name in new:
        path = active.get(name)
        if path is None or not path.is_file() or is_link(path):
            raise RuntimeError(f'Fichier actif absent ou irrégulier: {name}')
        originals[name] = path.read_bytes()
        if trial.pvrz.sha(originals[name]) != baseline[name]:
            raise RuntimeError(f'Fichier actif différent de la référence alpha.11: {name}')
    changed = {name: data for name, data in new.items() if data != originals[name]}
    if not changed:
        raise RuntimeError('Le pack ne présente aucun changement à installer.')
    backup = HISTORY / 'before'
    backup.mkdir(parents=True, exist_ok=False)
    records = {}
    for name, data in changed.items():
        with (backup / name).open('xb') as stream:
            stream.write(originals[name])
        if (backup / name).read_bytes() != originals[name]:
            raise RuntimeError(f'Copie de retour arrière invalide: {name}')
        records[name] = dict(before=baseline[name], after=trial.pvrz.sha(data))
    receipt = dict(pack_sha256=report['shared_atlas_zip_sha256'], checked_files=len(new), files=records)
    save_state(receipt, 'prepared')
    switch(active, {name: originals[name] for name in changed}, changed)
    save_state(receipt, 'installed-awaiting-ingame-test')
    print(f'{len(changed)} PVRZ installés. Retour arrière disponible.')


def restore(override):
    receipt = json.loads(RECEIPT.read_bytes())
    if receipt['state'] not in ('prepared', 'installed-awaiting-ingame-test'):
        raise RuntimeError('Aucun essai à restaurer.')
    require_closed()
    active = exact_paths(override)
    current, originals = {}, {}
    for name, hashes in receipt['files'].items():
        trial.pvrz.path_for(trial.ROOT, f'override/{name}')
        path = active[name]
        data = (HISTORY / 'before' / name).read_bytes()
        if trial.pvrz.sha(data) != hashes['before'] or is_link(path):
            raise RuntimeError(f'Sauvegarde ou destination invalide: {name}')
        now = path.read_bytes()
        if trial.pvrz.sha(now) not in (hashes['before'], hashes['after']):
            raise RuntimeError(f'Fichier actif modifié depuis l’essai: {name}')
        if data != now:
            current[name], originals[name] = now, data
    switch(active, current, originals)
    save_state(receipt, 'restored')
    print(f'{len(originals)} fichiers restaurés.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('install', 'restore'))
    args = parser.parse_args()
    game, override = paths()
    if args.action == 'install':
        install(game, override)
    else:
        restore(override)
