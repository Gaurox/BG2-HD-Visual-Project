"""Install the verified canonical maps locally, using hardlinks for equal pages."""
import argparse
from collections import defaultdict
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

import build as pack

spec = importlib.util.spec_from_file_location('atlas_install',
    pack.HERE.parent / 'map-atlas-sharing-20261121-v1/install_test.py')
atlas_path = str(Path(spec.origin).parent)
sys.path.insert(0, atlas_path)
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
sys.path.remove(atlas_path)

HISTORY = pack.RUN / 'installation'
RECEIPT = HISTORY / 'installed.json'
BEFORE = HISTORY / 'before'
PRIOR = pack.HERE.parent / 'map-atlas-sharing-20261121-v1/run/installation/installed.json'


def load_report():
    report = json.loads((pack.HERE/'results.json').read_bytes())
    if pack.pvrz.file_sha(pack.ZIP) != report['pack_sha256']:
        raise ValueError('Le ZIP local a changé.')
    return report


def state(receipt, status):
    receipt['state'] = status
    local.atomic_write(RECEIPT, (json.dumps(receipt, indent=2)+'\n').encode('utf-8'))


def identity(path):
    stat = path.stat()
    return stat.st_dev, stat.st_ino


def payload_size(paths):
    return sum({identity(path):path.stat().st_size for path in paths}.values())


def get_files(report, directory):
    files = {}
    for name, metadata in report['files'].items():
        path = pack.pvrz.path_for(directory, f'override/{name}')
        raw = path.read_bytes()
        if pack.sha(raw) != metadata['sha256'] or len(raw) != metadata['bytes']:
            raise ValueError(f'La projection locale a changé: {name}')
        files[name] = raw
    return files


def validate_unchanged_refs(report, active):
    bifs, entries = pack.bg2lib.load_key()
    key = {a.upper():loc for a,kind,loc in entries if kind==0x03e9}
    for area, required in report['wed_and_tis_checks'].items():
        wed = active.get(f'{area}.WED')
        tis = active[f'{area}.TIS']
        source = wed.read_bytes() if wed else pack.bg2lib.resolve_resource(bifs,key[area])[0]
        if pack.sha(source) != required['sha256'] or pack.pvrz.file_sha(tis) != required['tis_sha256']:
            raise ValueError(f'WED ou TIS actif hors référence: {area}')


def stage_groups(override, grouped, active, original, changed):
    # Create one backing per digest in a sibling of the live files, then use
    # atomic replacements. No active alias is opened for in-place writing.
    staged = Path(tempfile.mkdtemp(prefix='.shared-original-maps-', dir=override))
    if staged.resolve().parent != override.resolve():
        raise RuntimeError('Dossier local de préparation inattendu.')
    paths = []
    switched = []
    try:
        for i, (data, names) in enumerate(grouped):
            master = staged/f'{i}.pvrz'
            master.write_bytes(data)
            paths.append(master)
            for name in names:
                path = staged/name
                os.link(master, path)
                paths.append(path)
        local.require_closed()
        for name in changed:
            if local.is_link(active[name]) or active[name].read_bytes() != original[name]:
                raise RuntimeError(f'Fichier modifié pendant la préparation: {name}')
        for name in changed:
            os.replace(staged/name, active[name])
            switched.append(name)
        for data, names in grouped:
            if any(active[n].read_bytes() != data or not os.path.samefile(active[names[0]],active[n]) for n in names):
                raise RuntimeError(f'Le partage réel a échoué: {names[0]}')
    except Exception:
        for name in reversed(switched):
            local.atomic_write(active[name], original[name])
        raise
    finally:
        for path in reversed(paths):
            path.unlink(missing_ok=True)
        staged.rmdir()


def install(override):
    if HISTORY.exists():
        raise RuntimeError('Un essai local existe déjà.')
    local.require_closed()
    report = load_report()
    active = local.exact_paths(override)
    validate_unchanged_refs(report, active)
    expected = get_files(report, pack.RUN/'restored')
    prior = json.loads(PRIOR.read_bytes())['files'] if PRIOR.exists() else {}
    original = {}
    for name, metadata in report['files'].items():
        path = active[name]
        if not path.is_file() or local.is_link(path):
            raise ValueError(f'Page active irrégulière: {name}')
        raw = path.read_bytes()
        if pack.sha(raw) not in (metadata['baseline_sha256'], prior.get(name,{}).get('after')):
            raise ValueError(f'Page active hors référence: {name}')
        original[name] = raw
    groups = defaultdict(list)
    for name, metadata in report['files'].items():
        groups[metadata['sha256']].append(name)
    changed = {}
    grouped = []
    for names in groups.values():
        data = expected[names[0]]
        if any(original[n] != data or not os.path.samefile(active[names[0]],active[n]) for n in names):
            grouped.append((data,names))
            changed.update({name:dict(before=pack.sha(original[name]),after=pack.sha(data)) for name in names})
    before_bytes = payload_size(active[name] for name in expected)
    BEFORE.mkdir(parents=True, exist_ok=False)
    for name in changed:
        (BEFORE/name).write_bytes(original[name])
        if (BEFORE/name).read_bytes() != original[name]:
            raise ValueError(f'Sauvegarde illisible: {name}')
    receipt = dict(pack_sha256=report['pack_sha256'], files=changed, checked_pages=len(expected),
                   common_groups=sum(len(names)>1 for names in groups.values()), active_bytes_before=before_bytes)
    state(receipt,'prepared')
    stage_groups(override, grouped, active, original, changed)
    validate_unchanged_refs(report, active)
    for names in groups.values():
        if any(active[n].read_bytes() != expected[n] or not os.path.samefile(active[names[0]],active[n]) for n in names):
            raise ValueError(f'Post-installation vérification échouée: {names[0]}')
    receipt['active_bytes_after'] = payload_size(active[name] for name in expected)
    receipt['visual_changes'] = sum(original[name] != expected[name] for name in expected)
    state(receipt,'installed-awaiting-ingame-test')
    print(len(changed),'installed names;',receipt['visual_changes'],'pages with different bytes;',
          before_bytes-receipt['active_bytes_after'],'unique active bytes saved')


def restore(override):
    local.require_closed()
    receipt = json.loads(RECEIPT.read_bytes())
    if receipt['state'] not in ('prepared','installed-awaiting-ingame-test'):
        raise ValueError('Aucun essai à restaurer.')
    active = local.exact_paths(override)
    current, original = {}, {}
    for name, proof in receipt['files'].items():
        pack.pvrz.path_for(pack.ROOT, f'override/{name}')
        data = (BEFORE/name).read_bytes()
        now = active[name].read_bytes()
        if pack.sha(data) != proof['before'] or pack.sha(now) not in (proof['before'],proof['after']):
            raise ValueError(f'Page ou sauvegarde modifiée: {name}')
        current[name], original[name] = now, data
    local.switch(active,current,original)
    state(receipt,'restored')
    print(len(original),'textures restored')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('install','restore'))
    args = parser.parse_args()
    _, override = local.paths()
    if args.action=='install':
        install(override)
    else:
        restore(override)
