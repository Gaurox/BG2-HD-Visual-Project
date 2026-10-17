"""Reversible lot26 delta: preserve active225, add SDF zero-inset and alpha routing."""
from pathlib import Path
from dataclasses import asdict
import argparse
import copy
import importlib.util
import json
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_authority as authority
import effect_workflow as workflow
import install_renderer_candidate as tx
from workspace_paths import get_path

BATCH = ROOT / 'effects/batches/lot26-sdf-no-inset-20261017-v1'
OUT = ROOT / 'effects/installations/lot26-sdf-no-inset-20261017-v1'
CANDIDATE = OUT / 'candidate'
GAME = get_path('bg2ee_game_root', required=True)
PROBE = ROOT / 'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
BASE_INSTALL = ROOT / 'effects/installations/cloud-palettealpha-20261017-v1'
PRESERVED = ['InfinityEngine-Enhancer.dll', 'BaldurReal.exe', 'override/fpDraw.glsl',
             'override/fpSprite.glsl', 'override/fpSELECT.glsl',
             'iee-assets/creature-sprites/CreatureSprites-XN.catalog']
spec = importlib.util.spec_from_file_location('lot58_builder', ROOT / 'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
load, save, rel, digest = builder.load, builder.save, builder.rel, builder.digest
sha = workflow.sha256_file


def write(p, raw):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        assert p.read_bytes() == raw, p
    else:
        p.write_bytes(raw)


def probe(target, name):
    with (OUT / name).open('x', encoding='utf-8') as log:
        subprocess.run([str(PROBE), '--catalogue-only', str(target), str(OUT / 'runtime-contracts.tsv')],
                       stdout=log, stderr=subprocess.STDOUT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def prepare():
    assert not (OUT / 'plan.json').exists(), 'Do not overwrite an installation plan'
    assets = load(BATCH / 'batch.json')['assets']
    assert len(assets) == 26 and load(BATCH / 'production.json')['sdf_phases'] == 404
    active = GAME / 'iee-assets/effects'
    old = load(active / 'manifest.json')
    assert old['resource_count'] == 225
    assert sha(active / 'manifest.json') == load(BASE_INSTALL / 'installation.json')['manifest_sha256']
    old_registry = (active / 'EffectAnimations-X4.registry').read_bytes()
    assert digest(old_registry) == old['registry_sha256']
    assert not ({a['resref'] for a in assets} & {r['resref'] for r in old['resources']})
    before = {'manifest_sha256': sha(active / 'manifest.json'), 'registry_sha256': digest(old_registry),
              'ini': asdict(tx.snapshot_file(GAME / 'InfinityEngine-Enhancer.ini')),
              'preserved': {n: asdict(tx.snapshot_file(GAME / n)) for n in PRESERVED}}
    save(OUT / 'before.json', before)
    ini = (GAME / 'InfinityEngine-Enhancer.ini').read_bytes()
    assert ini.count(b'EffectMetadataMiB = 16') == 1
    new_ini = ini.replace(b'EffectMetadataMiB = 16', b'EffectMetadataMiB = 32')
    assert new_ini.replace(b'EffectMetadataMiB = 32', b'EffectMetadataMiB = 16') == ini
    manifest = copy.deepcopy(old)
    records, files, contracts = bytearray(), [], (BASE_INSTALL / 'runtime-contracts.tsv').read_text(encoding='ascii').splitlines()
    routing, clua, profiles, provenance = [], [], [], []
    target = CANDIDATE / 'iee-assets/effects'
    target.mkdir(parents=True, exist_ok=True)

    def add(name, raw=None, source=None):
        dest = tx.managed_path(CANDIDATE, name, create_parents=True)
        if source is not None:
            expected = tx.snapshot_file(source)
            if dest.exists():
                assert tx.snapshot_file(dest) == expected
            else:
                shutil.copy2(source, dest)
        else:
            write(dest, raw)
            expected = tx.snapshot_file(dest)
        files.append({'name': name, **asdict(expected)})

    def vvc(name, ref, raw, purpose):
        file = f'override/{name}.vvc'
        assert not (GAME / file).exists(), file
        add(file, raw)
        manifest['runtime_vvc_controllers'].append({'asset': file, 'bam': ref, 'sha256': digest(raw),
                                                  'bytes': len(raw), 'purpose': purpose})

    normal_refs = set()
    for a in assets:
        modes = {('normal' if not (json.loads(c['flags_json'])['display'] & 8) else 'blended')
                 for c in a['consumers'] if c['owner_route'] == 'vvc'}
        has_pro = any(c['owner_route'] == 'projectile' for c in a['consumers'])
        if modes == {'normal'} and not has_pro:
            normal_refs.add(a['resref'])
    assert len(normal_refs) == 15
    review = {a['resref']: a for a in load(ROOT / 'effects/batches/lot26-seedvr7b-apollo30-20261017-v2/review/review.json')['assets']}
    profile_number = 0
    for a in assets:
        ref = a['resref']
        assert sha(ROOT / a['pack'] / 'manifest.json') == load(BATCH / 'checks' / f'{ref}.json')['pack_manifest_sha256']
        variants = [(ref, ref in normal_refs)]
        if ref == 'SPIPLAAI':
            variants.extend([('SPIPLARI', False), ('X26PLAA', True)])
        main = None
        for runtime_ref, straight in variants:
            assert runtime_ref not in {r['resref'] for r in manifest['resources']}
            raw, resource, frames, copies, checks, m = builder.build_resource(a, runtime_ref, straight)
            main = m
            records.extend(raw)
            manifest['resources'].append(resource)
            contracts.extend(checks)
            for f in frames:
                f['frame'] = len(manifest['frames'])
                manifest['frames'].append(f)
            for source, name in copies:
                add('iee-assets/effects/' + name, source=source)
            carrier = ROOT / m['runtime_carrier']['path']
            assert sha(carrier) == m['runtime_carrier']['sha256']
            assert not (GAME / f'override/{runtime_ref}.bam').exists()
            add(f'override/{runtime_ref}.bam', source=carrier)
            manifest['runtime_bam_carriers'].append({'resref': runtime_ref, 'asset': f'override/{runtime_ref}.bam',
                'sha256': sha(carrier), 'bytes': carrier.stat().st_size, 'production_bam': ref,
                'policy': 'native indices/palette/cycles/world centres retained; transparent carrier padding'})
        test_ref = 'X26PLAA' if ref == 'SPIPLAAI' else ref
        straight = ref in normal_refs or ref == 'SPIPLAAI'
        rate = (a['native_fps'] or [15])[0]
        for profile in main['timing']['cycles']:
            profile_number += 1
            name = f'Z26P{profile_number:04d}'
            raw = builder.make_vvc(test_ref, profile['cycle'], profile['loop_closed'], rate,
                                   len(profile['native_slots']), not straight)
            vvc(name, test_ref, raw, 'lot26 isolated cycle visual test')
            record = {'bam': ref, 'runtime_bam': test_ref, 'profile': profile['id'], 'vvc': name,
                      'clua': f'C:Eval(\'CreateVisualEffectObject("{name}",Player1)\',0)'}
            profiles.append(record)
            if profile['id'] == review[ref]['default']:
                primary = f'Z26T{a["ordinal"]:02d}'
                vvc(primary, test_ref, raw, 'lot26 primary visual test, matching review profile')
                clua.append({**record, 'vvc': primary, 'ordinal': a['ordinal'],
                             'clua': f'C:Eval(\'CreateVisualEffectObject("{primary}",Player1)\',0)'})
        provenance.append({'resref': ref, 'pack': a['pack'], 'manifest_sha256': sha(ROOT / a['pack'] / 'manifest.json'),
                           'interpolation_run': a['interpolation_run'], 'rgb_encoding': 'straight' if ref in normal_refs else 'premultiplied'})
        print(ref, 'prepared', flush=True)
    # Preserve both original spell/PRO aliases; only normal VVC BAM references change.
    for name, original in [('ICINHIT', 'SPIPLAAI'), ('ICINTRAV', 'SPIPLARI')]:
        source = ROOT / f'effects/source/vvc/{name}.vvc'
        raw = source.read_bytes()
        assert raw[8:16].rstrip(b'\0').decode() == original
        changed = raw[:8] + b'X26PLAA\0' + raw[16:]
        assert changed[:8] + raw[8:16] + changed[16:] == raw
        vvc(name, 'X26PLAA', changed, 'native normal consumer; reference-only routing to straight alias')
        routing.append(f'override/{name}.vvc')
    assert len(clua) == 26 and len(profiles) == 60 and len(manifest['resources']) == 253
    assert manifest['resources'][:225] == old['resources'] and manifest['frames'][:len(old['frames'])] == old['frames']
    registry = struct.pack('<8sIIII', b'IEEEFX4\0', 3, 4, len(manifest['resources']), 0) + old_registry[24:] + records
    assert registry[24:len(old_registry)] == old_registry[24:]
    manifest.update(resource_count=len(manifest['resources']), frame_count=len(manifest['frames']),
                    registry_bytes=len(registry), registry_sha256=digest(registry))
    manifest.setdefault('source_packs', []).extend(provenance)
    add('iee-assets/effects/EffectAnimations-X4.registry', registry)
    add('iee-assets/effects/manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
    add('InfinityEngine-Enhancer.ini', new_ini)
    write(OUT / 'runtime-contracts.tsv', ('\n'.join(contracts) + '\n').encode('ascii'))
    save(OUT / 'clua.json', clua)
    save(OUT / 'clua-all-profiles.json', profiles)
    text = '# Lot26 — commandes CLUA\n\nLancer le jeu via InfinityLoader. Une commande à la fois ; tests visuels sans dégâts, boucles bornées à au moins4s. Les contrôleurs isolés ne reproduisent pas les trajectoires PRO. SDF sans retrait pour les8désignés ; les18autres v2 conservés.\n\n```lua\n'
    for r in clua:
        text += f'-- {r["ordinal"]:02d} {r["bam"]} / {r["profile"]}\n{r["clua"]}\n'
    text += '```\n\nSPIPLARI réutilise SPIPLAAI ; son alias natif est installé. [Tous les cycles/modes](CLUA-tous-profils.md).\n'
    write(OUT / 'CLUA.md', text.encode())
    text = '# Lot26 — 60 profils isolés\n\nUne commande à la fois.\n\n'
    for a in assets:
        text += f'## {a["resref"]}\n\n```lua\n'
        for r in profiles:
            if r['bam'] == a['resref']:
                text += f'-- {r["profile"]}\n{r["clua"]}\n'
        text += '```\n\n'
    write(OUT / 'CLUA-tous-profils.md', text.encode())
    probe(target, 'candidate-native-loader.log')
    save(OUT / 'plan.json', {'count': 26, 'production_assets_total': 245, 'runtime_resources': 253,
        'existing_resources_unchanged': 225, 'existing_frames_unchanged': len(old['frames']),
        'new_backings': len(manifest['frames']) - len(old['frames']), 'native_contracts': len(contracts),
        'primary_tests': 26, 'profiles': 60, 'native_normal_routing': routing,
        'normal_resources': sorted(normal_refs), 'aliases': {'SPIPLARI': 'SPIPLAAI', 'X26PLAA': 'SPIPLAAI-normal'},
        'metadata_mib': 32, 'ini_change': 'EffectMetadataMiB16->32 only',
        'manifest_sha256': sha(target / 'manifest.json'), 'sdf_inset_x4': 0,
        'files': files, 'candidate_kind': 'append-only-resource-delta-plus-INI-budget',
        'visual_qa': 'pending-user-test', 'release_changed': False})
    print('READY', len(files), 'managed targets;', len(contracts), 'native contracts', flush=True)


def preserved(before):
    assert all(asdict(tx.snapshot_file(GAME / n)) == value for n, value in before['preserved'].items())


def rollback(receipt):
    assert Path(receipt['game_root']).resolve() == GAME.resolve()
    for item in reversed(receipt['files']):
        target = tx.managed_path(GAME, item['name'], create_parents=True)
        current = tx.optional_snapshot(target)
        expected = tx.FileSnapshot(item['bytes'], item['sha256'])
        old = tx.FileSnapshot(**item['before']) if item['before'] else None
        assert current in (old, expected), target
        if current == old:
            continue
        if old:
            tx.atomic_copy(OUT / 'before' / item['name'], target, old)
        else:
            tx.safe_unlink(target, expected)
    receipt['status'] = 'restored'
    tx.write_json_atomic(OUT / 'transaction.json', receipt)


def install():
    assert not (OUT / 'transaction.json').exists()
    tx.ensure_game_stopped(tx.running_game_processes)
    (OUT / 'before').mkdir(exist_ok=True)
    before, plan = load(OUT / 'before.json'), load(OUT / 'plan.json')
    preserved(before)
    assert asdict(tx.snapshot_file(GAME / 'InfinityEngine-Enhancer.ini')) == before['ini']
    assert sha(GAME / 'iee-assets/effects/manifest.json') == before['manifest_sha256']
    assert sha(GAME / 'iee-assets/effects/EffectAnimations-X4.registry') == before['registry_sha256']
    entries = []
    for item in plan['files']:
        expected = tx.FileSnapshot(item['bytes'], item['sha256'])
        assert tx.snapshot_file(tx.managed_path(CANDIDATE, item['name'])) == expected
        target = tx.managed_path(GAME, item['name'])
        old = tx.optional_snapshot(target)
        if old:
            assert item['name'] in ['InfinityEngine-Enhancer.ini', 'iee-assets/effects/manifest.json', 'iee-assets/effects/EffectAnimations-X4.registry']
            tx.atomic_copy(target, tx.managed_path(OUT / 'before', item['name'], create_parents=True), old)
        entries.append({**item, 'before': asdict(old) if old else None})
    receipt = {'schema': 'bg2-effects-resource-delta-transaction-v1', 'status': 'prepared',
               'game_root': str(GAME), 'candidate_root': rel(CANDIDATE), 'created_utc': tx.utc_now(), 'files': entries}
    tx.write_json_atomic(OUT / 'transaction.json', receipt)
    try:
        receipt['status'] = 'installing'
        tx.write_json_atomic(OUT / 'transaction.json', receipt)
        for item in entries:
            target = tx.managed_path(GAME, item['name'], create_parents=True)
            old = tx.FileSnapshot(**item['before']) if item['before'] else None
            assert tx.optional_snapshot(target) == old
            tx.atomic_copy(tx.managed_path(CANDIDATE, item['name']), target, tx.FileSnapshot(item['bytes'], item['sha256']))
        for item in entries:
            assert tx.snapshot_file(tx.managed_path(GAME, item['name'])) == tx.FileSnapshot(item['bytes'], item['sha256'])
        preserved(before)
        probe(GAME / 'iee-assets/effects', 'installed-native-loader.log')
        receipt['status'] = 'installed'
        receipt['installed_utc'] = tx.utc_now()
        tx.write_json_atomic(OUT / 'transaction.json', receipt)
    except Exception:
        rollback(receipt)
        raise
    with authority.guard(ROOT, write=True):
        rows = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
        save(OUT / 'processing-before.json', rows)
        refs = {a['resref'] for a in load(BATCH / 'batch.json')['assets']} | {'SPIPLARI'}
        for row in rows:
            if row['asset_key'].rsplit(':', 1)[-1] in refs:
                row['installation_state'] = 'installed'
                row['installation_receipt'] = rel(OUT / 'transaction.json')
        authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(rows)})
    save(OUT / 'installation.json', {k: v for k, v in plan.items() if k != 'files'} | {
        'status': 'installed-offline-verified', 'transaction': rel(OUT / 'transaction.json'),
        'dll_and_character_profile_byte_identical': True, 'game_and_loader_stopped': True,
        'game_launched': False, 'qa_accepted': False,
        'installed_ini_sha256': sha(GAME / 'InfinityEngine-Enhancer.ini')})
    print('INSTALLED 26 effects; SDF zero inset; 27 original RESREF +normal alias; 26 CLUA tests', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'install', 'restore'])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.action == 'prepare':
        prepare()
    elif args.action == 'install':
        install()
    else:
        tx.ensure_game_stopped(tx.running_game_processes)
        rollback(load(OUT / 'transaction.json'))
