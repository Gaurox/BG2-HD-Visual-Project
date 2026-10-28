"""Prepare/install one isolated QA spell; existing spell/PRO/images remain intact."""
from pathlib import Path
import hashlib
import json
import os
import struct
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'pipeline/scripts'),
               str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools')]
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
from projectile_tracking import ids_entries, ability_projectiles
from install_renderer_candidate import ensure_game_stopped, running_game_processes

GAME = get_path('bg2ee_game_root', required=True)
OUT = ROOT / 'projectiles/analysis/validation-feu-vert-20261028-v1'
NAME = 'XPGREEN'


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def save(path, data):
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def active(bifs, key, name, kind, ext):
    p = GAME / 'override' / (name + '.' + ext)
    return p.read_bytes() if p.exists() else resolve_resource(bifs, key[name, kind])[0]


def prepare():
    assert not OUT.exists(), 'Historical preparation exists'
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    assert (NAME, 1006) not in key
    assert not (GAME / 'override' / (NAME + '.spl')).exists()
    ids = ids_entries(active(bifs, key, 'PROJECTL', 1008, 'ids'))
    ids_for_green = [i for i, n in ids.items() if n == 'FIREBLGR']
    assert ids_for_green == [103], ids_for_green
    source = active(bifs, key, 'SPWI304', 1006, 'spl')
    candidate = bytearray(source)
    abilities = ability_projectiles(source, 'SPL')
    assert len(abilities) == 6 and all(v == 234 for _, _, v in abilities)
    for _, off, _ in abilities:
        struct.pack_into('<H', candidate, off, ids_for_green[0] + 1)
    changed = [i for i, (a, b) in enumerate(zip(source, candidate)) if a != b]
    allowed = {i for _, off, _ in abilities for i in (off, off + 1)}
    assert set(changed) <= allowed and len(changed) == 6
    assert all(v == 104 for _, _, v in ability_projectiles(candidate, 'SPL'))
    OUT.mkdir()
    (OUT / 'candidate').mkdir()
    (OUT / 'candidate' / (NAME + '.spl')).write_bytes(candidate)
    protected = {n: sha((GAME / n).read_bytes()) for n in (
        'InfinityEngine-Enhancer.dll', 'iee-assets/effects/EffectAnimations-X4.registry')}
    resource_hashes = {n + '.' + ext: sha(active(bifs, key, n, t, ext))
                       for n, t, ext in [('SPWI304', 1006, 'spl'),
                                         ('FIREBLGR', 1021, 'pro'),
                                         ('FIREBGRX', 1000, 'bam'),
                                         ('FIREBGRR', 1000, 'bam')]}
    save(OUT / 'prepare.json', {
        'utc': datetime.now(timezone.utc).isoformat(), 'resource': NAME,
        'source': 'active SPWI304.SPL', 'source_sha256': sha(source),
        'candidate_sha256': sha(candidate), 'bytes': len(candidate),
        'changed_byte_offsets': changed, 'ability_count': len(abilities),
        'only_projectile_words_changed': True, 'projectile_raw': 104,
        'owner': 'FIREBLGR', 'expected_assets': ['FIREBGRT', 'FIREBGRX', 'FIREBGRR', 'SPSMPUFF'],
        'gameplay': 'Isolated test spell inherits ordinary Fireball effects/damage; use test save. No existing spell changed.',
        'protected_files': protected, 'active_resource_hashes': resource_hashes,
        'no_new_images_or_engine_changes': True, 'QA': 'pending-user-and-runtime',
        'scope': 'Real FIREBLGR native dispatch; does not validate unregistered FBFLAMGR owner',
    })
    print('Prepared XPGREEN: 978 bytes, only six projectile words changed, FIREBLGR raw104')


def install():
    plan = json.loads((OUT / 'prepare.json').read_text(encoding='utf-8'))
    assert not (OUT / 'installation.json').exists()
    candidate = (OUT / 'candidate' / (NAME + '.spl')).read_bytes()
    assert sha(candidate) == plan['candidate_sha256']
    target = GAME / 'override' / (NAME + '.spl')
    assert target.resolve().parent == (GAME / 'override').resolve()
    assert not target.exists(), 'Never overwrite an existing resource'
    for n, digest in plan['protected_files'].items():
        assert sha((GAME / n).read_bytes()) == digest, n
    ensure_game_stopped(running_game_processes)
    save(OUT / 'transaction.json', {
        'status': 'prepared', 'target': str(target), 'before': None,
        'candidate_sha256': sha(candidate), 'rollback': 'Remove only this new file after SHA verification and game shutdown',
    })
    # Exclusive creation guarantees no existing file is replaced, even after a race.
    with target.open('xb') as f:
        f.write(candidate)
        f.flush()
        os.fsync(f.fileno())
    assert sha(target.read_bytes()) == plan['candidate_sha256']
    for n, digest in plan['protected_files'].items():
        assert sha((GAME / n).read_bytes()) == digest, n
    save(OUT / 'installation.json', {
        'status': 'installed-pending-test', 'utc': datetime.now(timezone.utc).isoformat(),
        'file': str(target), 'before': None, 'bytes': len(candidate),
        'sha256': sha(candidate), 'existing_files_replaced': 0,
        'new_files': 1, 'images_reprocessed': 0, 'renderer': 'V10 unchanged',
        'release_changed': False,
    })
    print('Installed only override/XPGREEN.spl; no existing resource replaced')


if __name__ == '__main__':
    {'prepare': prepare, 'install': install}[sys.argv[1]]()
