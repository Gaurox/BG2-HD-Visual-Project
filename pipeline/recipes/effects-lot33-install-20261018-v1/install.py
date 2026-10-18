"""Install the33 sealed impacts: append-only catalogue, reversible scoped delta."""
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

BATCH = ROOT / 'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'
OUT = ROOT / 'effects/installations/lot33-native-impacts-20261018-v1'
CANDIDATE = OUT / 'candidate'
GAME = get_path('bg2ee_game_root', required=True)
PROBE = ROOT / 'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
BASE_CONTRACTS = ROOT / 'effects/installations/lot26-sdf-no-inset-20261017-v1/runtime-contracts.tsv'
PRESERVED = ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini', 'BaldurReal.exe',
             'override/fpDraw.glsl', 'override/fpSprite.glsl', 'override/fpSELECT.glsl',
             'iee-assets/creature-sprites/CreatureSprites-XN.catalog']
EXPECTED_BASE = '44A63CBDDC7609D9C89921C0BEBE148A577847AB28D2B400DB8AEDF91C34E924'
spec = importlib.util.spec_from_file_location('lot58_builder', ROOT / 'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
load, save, rel, digest = builder.load, builder.save, builder.rel, builder.digest
sha = workflow.sha256_file


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, path
    else:
        path.write_bytes(raw)


def probe(target, name):
    with (OUT / name).open('x', encoding='utf-8') as log:
        subprocess.run([str(PROBE), '--catalogue-only', str(target), str(OUT / 'runtime-contracts.tsv')],
                       stdout=log, stderr=subprocess.STDOUT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW)


def primary_blended(asset):
    # Isolated-test choice, never asserted as the native owner's measured flags.
    return asset['group'] in {'feu-explosions-souffles', 'froid-projections', 'lumiere-rayons-impacts'} or asset['resref'] == 'SPHORPUF'


def command(name):
    return f'C:Eval(\'CreateVisualEffectObject("{name}",Player1)\',0)'


def prepare():
    assert not (OUT / 'plan.json').exists(), 'New installation version required'
    assets = load(BATCH / 'batch.json')['assets']
    assert len(assets) == 33 and load(BATCH / 'verification.json')['passed'] == 33
    active = GAME / 'iee-assets/effects'
    old = load(active / 'manifest.json')
    assert old['resource_count'] == 253 and sha(active / 'manifest.json') == EXPECTED_BASE
    old_registry = (active / 'EffectAnimations-X4.registry').read_bytes()
    assert digest(old_registry) == old['registry_sha256']
    native_names = {n for a in assets for n in [a['resref']] + a['reuse_aliases']}
    assert len(native_names) == 36 and not native_names & {r['resref'] for r in old['resources']}
    assert b'EffectMetadataMiB = 32' in (GAME / 'InfinityEngine-Enhancer.ini').read_bytes()
    before = {'manifest_sha256': sha(active / 'manifest.json'), 'registry_sha256': digest(old_registry),
              'preserved': {n: asdict(tx.snapshot_file(GAME / n)) for n in PRESERVED}}
    save(OUT / 'before.json', before)
    manifest = copy.deepcopy(old)
    records, files = bytearray(), []
    contracts = BASE_CONTRACTS.read_text(encoding='ascii').splitlines()
    assert len(contracts) == 70888
    clua, profiles, comparison, provenance = [], [], [], []
    review = {a['resref']: a for a in load(BATCH / 'review/review.json')['assets']}
    target = CANDIDATE / 'iee-assets/effects'
    target.mkdir(parents=True, exist_ok=True)

    def add(name, raw=None, source=None):
        assert not (GAME / name).exists() or name in {
            'iee-assets/effects/manifest.json', 'iee-assets/effects/EffectAnimations-X4.registry'}, name
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
        assert len(name) <= 8 and not (GAME / file).exists()
        add(file, raw)
        manifest['runtime_vvc_controllers'].append({'asset': file, 'bam': ref, 'sha256': digest(raw),
                                                  'bytes': len(raw), 'purpose': purpose})

    for a in assets:
        ref, number = a['resref'], a['ordinal']
        pack_sha = sha(ROOT / a['pack'] / 'manifest.json')
        assert pack_sha == load(BATCH / 'checks' / f'{ref}.json')['pack_manifest_sha256']
        normal = f'X33N{number:02d}'
        # Native names retain the default premultiplied encoding. Straight test
        # aliases provide independent alpha-normal draws; source runs unchanged.
        variants = [(n, False) for n in [ref] + a['reuse_aliases']] + [(normal, True)]
        for runtime_ref, straight in variants:
            raw, resource, frames, copies, checks, main = builder.build_resource(a, runtime_ref, straight)
            records.extend(raw)
            manifest['resources'].append(resource)
            contracts.extend(checks)
            for f in frames:
                f['frame'] = len(manifest['frames'])
                manifest['frames'].append(f)
            for source, name in copies:
                add('iee-assets/effects/' + name, source=source)
            carrier = ROOT / main['runtime_carrier']['path']
            assert sha(carrier) == main['runtime_carrier']['sha256']
            add(f'override/{runtime_ref}.bam', source=carrier)
            manifest['runtime_bam_carriers'].append({'resref': runtime_ref, 'asset': f'override/{runtime_ref}.bam',
                'sha256': sha(carrier), 'bytes': carrier.stat().st_size, 'production_bam': ref,
                'policy': 'native indices/palette/cycles/world centres retained; transparent carrier padding'})
        rate = (a['native_fps'] or [15])[0]
        blended = primary_blended(a)
        test_ref = ref if blended else normal
        for profile in main['timing']['cycles']:
            name = f'Z33P{len(profiles)+1:04d}'
            raw = builder.make_vvc(test_ref, profile['cycle'], profile['loop_closed'], rate,
                                   len(profile['native_slots']), blended)
            vvc(name, test_ref, raw, 'lot33 isolated native cycle/profile; test blend choice, no gameplay')
            record = {'ordinal': number, 'bam': ref, 'runtime_bam': test_ref, 'profile': profile['id'],
                      'blend': 'blended' if blended else 'normal', 'vvc': name, 'clua': command(name)}
            profiles.append(record)
            if profile['id'] == review[ref]['default']:
                primary = f'Z33T{number:02d}'
                vvc(primary, test_ref, raw, 'lot33 primary isolated visual test')
                clua.append({**record, 'vvc': primary, 'group': a['group'], 'clua': command(primary)})
                for suffix, compare_ref, compare_blend in [('B', ref, True), ('N', normal, False)]:
                    name = f'Z33{suffix}{number:02d}'
                    compare_raw = builder.make_vvc(compare_ref, profile['cycle'], profile['loop_closed'], rate,
                                                   len(profile['native_slots']), compare_blend)
                    vvc(name, compare_ref, compare_raw, 'lot33 explicit blend comparison; not measured native owner')
                    comparison.append({**record, 'runtime_bam': compare_ref, 'vvc': name,
                                       'blend': 'blended' if compare_blend else 'normal', 'clua': command(name)})
        provenance.append({'resref': ref, 'pack': a['pack'], 'manifest_sha256': pack_sha,
                           'interpolation_run': a['interpolation_run'], 'rgb_encoding': 'premultiplied',
                           'native_aliases': a['reuse_aliases'], 'straight_test_alias': normal,
                           'primary_test_blend': 'blended' if blended else 'normal',
                           'native_owner_blend_measured': False})
        print(ref, 'prepared', 'blended' if blended else 'normal', flush=True)
    assert len(clua) == 33 and len(profiles) == 182 and len(comparison) == 66
    assert len(manifest['resources']) == 322
    assert manifest['resources'][:253] == old['resources']
    assert manifest['frames'][:len(old['frames'])] == old['frames']
    registry = struct.pack('<8sIIII', b'IEEEFX4\0', 3, 4, len(manifest['resources']), 0) + old_registry[24:] + records
    assert registry[24:len(old_registry)] == old_registry[24:]
    manifest.update(resource_count=len(manifest['resources']), frame_count=len(manifest['frames']),
                    registry_bytes=len(registry), registry_sha256=digest(registry))
    manifest.setdefault('source_packs', []).extend(provenance)
    add('iee-assets/effects/EffectAnimations-X4.registry', registry)
    add('iee-assets/effects/manifest.json', (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode())
    write(OUT / 'runtime-contracts.tsv', ('\n'.join(contracts) + '\n').encode('ascii'))
    save(OUT / 'clua.json', clua)
    save(OUT / 'clua-all-profiles.json', profiles)
    save(OUT / 'clua-blend-comparison.json', comparison)
    text = '# Lot33 — commandes CLUA\n\nRelancer via InfinityLoader ; console Ctrl+Espace. Une commande à la fois. Tests visuels sans dégâts ; boucles bornées à au moins4s. SeedVR7B x4/Apollo30 ; durée des cycles natifs conservée sur base15FPS de compatibilité.\n\nModes de test : lumineux pour feu/froid/rayons et SPHORPUF ; normal pour les autres fumées/matériaux/sang. Ces choix ne prouvent pas les flags natifs des vrais sorts.\n\n```lua\n'
    for r in clua:
        text += f'-- {r["ordinal"]:02d} {r["bam"]} / {r["profile"]} / {r["blend"]}\n{r["clua"]}\n'
    text += '```\n\n[Tous les182profils](CLUA-tous-profils.md) ; [comparaison normal/lumineux pour les33](CLUA-transparence.md). BURNHAND réutilise SPBRNHND ; SPPRISM3/SPPRISMT réutilisent SPPRISM2. Ces tests VVC passent par un owner pris en charge ; les chemins natifs des vrais sorts restent à observer.\n'
    write(OUT / 'CLUA.md', text.encode())
    text = '# Lot33 — tous les182profils\n\nUne commande à la fois ; modes de test identiques à la liste principale.\n\n'
    for a in assets:
        text += f'## {a["ordinal"]:02d} {a["resref"]}\n\n```lua\n'
        for r in profiles:
            if r['bam'] == a['resref']:
                text += f'-- {r["profile"]} / {r["blend"]}\n{r["clua"]}\n'
        text += '```\n\n'
    write(OUT / 'CLUA-tous-profils.md', text.encode())
    text = '# Lot33 — comparaison de transparence\n\nMême cycle, RGB/alpha issus de la même production ; normal=compagnon droit, lumineux=prémultiplié. Tests indépendants ; attendre disparition avant la deuxième commande. Le noir interne opaque peut apparaître en normal, selon la source ; aucune suppression automatique du noir. Le bon mode d’un vrai sort dépend de son consommateur natif.\n\n'
    for a in assets:
        text += f'## {a["ordinal"]:02d} {a["resref"]}\n\n```lua\n'
        for r in comparison:
            if r['bam'] == a['resref']:
                text += f'-- {r["blend"]}\n{r["clua"]}\n'
        text += '```\n\n'
    write(OUT / 'CLUA-transparence.md', text.encode())
    probe(target, 'candidate-native-loader.log')
    save(OUT / 'plan.json', {'count': 33, 'production_assets_total': 278, 'runtime_resources': 322,
        'existing_resources_unchanged': 253, 'existing_frames_unchanged': len(old['frames']),
        'new_backings': len(manifest['frames']) - len(old['frames']), 'total_backings': len(manifest['frames']),
        'new_bytes': sum(f['bytes'] for f in manifest['frames'][len(old['frames']):]),
        'native_contracts': len(contracts), 'primary_tests': 33, 'profiles': 182, 'blend_comparisons': 66,
        'new_native_names': 36, 'straight_test_aliases': 33, 'metadata_mib': 32,
        'ini_changed': False, 'manifest_sha256': sha(target / 'manifest.json'),
        'files': files, 'candidate_kind': 'append-only-resource-delta',
        'visual_qa': 'pending-user-test', 'native_owner_blend_captured': False,
        'natural_native_owner_coverage': 'not-proven; isolated VVC tests use existing supported owner',
        'release_changed': False})
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
    assert sha(GAME / 'iee-assets/effects/manifest.json') == before['manifest_sha256']
    assert sha(GAME / 'iee-assets/effects/EffectAnimations-X4.registry') == before['registry_sha256']
    entries = []
    for item in plan['files']:
        expected = tx.FileSnapshot(item['bytes'], item['sha256'])
        assert tx.snapshot_file(tx.managed_path(CANDIDATE, item['name'])) == expected
        target = tx.managed_path(GAME, item['name'])
        old = tx.optional_snapshot(target)
        if old:
            assert item['name'] in ['iee-assets/effects/manifest.json', 'iee-assets/effects/EffectAnimations-X4.registry']
            tx.atomic_copy(target, tx.managed_path(OUT / 'before', item['name'], create_parents=True), old)
        entries.append({**item, 'before': asdict(old) if old else None})
    receipt = {'schema': 'bg2-effects-resource-delta-transaction-v1', 'status': 'prepared',
               'game_root': str(GAME), 'candidate_root': rel(CANDIDATE), 'created_utc': tx.utc_now(), 'files': entries}
    tx.write_json_atomic(OUT / 'transaction.json', receipt)
    try:
        tx.ensure_game_stopped(tx.running_game_processes)
        receipt['status'] = 'installing'
        tx.write_json_atomic(OUT / 'transaction.json', receipt)
        for index, item in enumerate(entries):
            target = tx.managed_path(GAME, item['name'], create_parents=True)
            old = tx.FileSnapshot(**item['before']) if item['before'] else None
            assert tx.optional_snapshot(target) == old
            tx.atomic_copy(tx.managed_path(CANDIDATE, item['name']), target, tx.FileSnapshot(item['bytes'], item['sha256']))
            if index % 1500 == 0:
                print('copied', index+1, '/', len(entries), flush=True)
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
    finish()


def finish():
    receipt, plan, before = load(OUT / 'transaction.json'), load(OUT / 'plan.json'), load(OUT / 'before.json')
    assert receipt['status'] == 'installed'
    assert sha(GAME / 'iee-assets/effects/manifest.json') == plan['manifest_sha256']
    preserved(before)
    refs = {n for a in load(BATCH / 'batch.json')['assets'] for n in [a['resref']] + a['reuse_aliases']}
    with authority.guard(ROOT, write=True):
        rows = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
        if not (OUT / 'processing-before.json').exists():
            save(OUT / 'processing-before.json', rows)
        changed = 0
        for row in rows:
            if row['asset_key'].rsplit(':', 1)[-1] in refs:
                row['installation_state'] = 'installed'
                row['installation_receipt'] = rel(OUT / 'transaction.json')
                changed += 1
        assert changed >= 33
        authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(rows)})
    save(OUT / 'installation.json', {k: v for k, v in plan.items() if k != 'files'} | {
        'status': 'installed-offline-verified', 'transaction': rel(OUT / 'transaction.json'),
        'dll_ini_and_character_profile_byte_identical': True, 'game_and_loader_stopped': True,
        'game_launched': False, 'qa_accepted': False, 'installed_utc': receipt['installed_utc']})
    print('INSTALLED33; primary CLUA33; profile tests182; transparency controls66', flush=True)


def restore():
    tx.ensure_game_stopped(tx.running_game_processes)
    rollback(load(OUT / 'transaction.json'))
    if (OUT / 'processing-before.json').exists():
        previous = {r['asset_key']: r for r in load(OUT / 'processing-before.json')}
        with authority.guard(ROOT, write=True):
            rows = workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
            for r in rows:
                if r['installation_receipt'] == rel(OUT / 'transaction.json'):
                    for key in ['installation_state', 'installation_receipt']:
                        r[key] = previous[r['asset_key']][key]
            authority.commit(ROOT, {'effects/index/processing.csv': workflow.csv_bytes(rows)})
    save(OUT / 'restoration.json', {'status': 'restored', 'utc': tx.utc_now(), 'transaction': rel(OUT / 'transaction.json')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['prepare', 'install', 'finish', 'restore'])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    globals()[args.action]()
