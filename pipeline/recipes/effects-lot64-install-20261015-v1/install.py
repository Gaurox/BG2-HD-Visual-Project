"""Install 64 sealed productions; retain all 97 existing effects and character profile."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from compose_effect_runtime_packs import validate_pack, compose, write_pack, sha256_file
from workspace_paths import get_path
import install_renderer_candidate as installer
import effect_workflow as workflow
import effect_authority as authority

BATCH = ROOT / 'effects/batches/lot64-seedvr7b-apollo30-strict-20261015-v3'
OUT = ROOT / 'effects/installations/lot64-7b-x4-nearest30-20261015-v1'
CANDIDATE = OUT / 'candidate'
BUILD = ROOT / 'build/iee-map-first-frame-refresh-20261014-v1'
PRESERVED = ['InfinityEngine-Enhancer.ini', 'override/fpDraw.glsl', 'override/fpSprite.glsl',
             'override/fpSELECT.glsl', 'iee-assets/creature-sprites/CreatureSprites-XN.catalog']

def load(p): return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def rel(p): return p.relative_to(ROOT).as_posix()
def profile(game): return {n: sha256_file(game / n) for n in PRESERVED}

def records(raw):
    """Parse v2 resource boundaries without changing any existing mapping."""
    magic, version, scale, count, reserved = struct.unpack_from('<8sIIII', raw)
    assert (magic, version, scale, reserved) == (b'IEEEFX4\0', 2, 4, 0)
    pos = 24
    for _ in range(count):
        start = pos
        ref = raw[pos:pos+8].rstrip(b'\0').decode('ascii'); pos += 8
        nf, nc = struct.unpack_from('<II', raw, pos); pos += 8
        dims = [struct.unpack_from('<II', raw, pos + i*8) for i in range(nf)]; pos += nf*8
        native = []
        for _ in range(nc):
            n, = struct.unpack_from('<I', raw, pos); pos += 4
            native.append(list(struct.unpack_from(f'<{n}I', raw, pos))); pos += n*4
        timing = struct.unpack_from('<IIIII', raw, pos); pos += 20
        assert timing[:4] == (15, 1, 30, 1)
        phases = []
        for _ in range(nc):
            n = timing[4]
            phases.append(list(struct.unpack_from(f'<{n}I', raw, pos))); pos += n*4
        yield ref, raw[start:pos], dims, native, phases
    assert pos == len(raw)

def alternate(asset, pack):
    timing = pack.resources[0]['timeline']
    if not timing.get('alternate_profiles'): return []
    m = load(ROOT / 'effects/ressources' / asset['resref'] / 'runs' /
             asset['interpolation_run'] / '02-interpolation/manifest.json')
    backing = {(f['sha256'], tuple(f['physical_size_x4'])): f['resource_frame'] for f in pack.frames}
    output = []
    for v in m['timing']['cycles']:
        if v['id'] not in timing['alternate_profiles']: continue
        assert not v['loop_closed']
        table = [backing[(m['frames'][i]['raw_rgba_x4_sha256'], tuple(m['frames'][i]['physical_size_x4']))]
                 for i in v['timeline_frame_indices']]
        output.append((v['cycle'], table))
    assert len(output) == len(timing['alternate_profiles'])
    return output

def clua(assets):
    controllers = {r['asset_key']: r for r in csv.DictReader(
        (ROOT / 'effects/index/resources.csv').open(encoding='utf-8-sig', newline=''))}
    tests = []
    for a in assets:
        choices = []
        for c in a['consumers']:
            key = c['consumer_key']
            if key.startswith('effect:vvc:'):
                record = controllers[key]
                source = ROOT / record['extracted_path']
                assert sha256_file(source) == record['source_sha256']
                data = source.read_bytes()
                assert data[:8] == b'VVC V1.0' and data[8:16].rstrip(b'\0').decode().upper() == a['resref']
                choices.append(record['resref'])
        assert choices, a['resref']
        choice = a['resref'] if a['resref'] in choices else choices[0]
        tests.append({'bam': a['resref'], 'vvc': choice, 'all_native_vvcs': sorted(set(choices)),
                      'clua': f'C:Eval(\'CreateVisualEffectObject("{choice}",Player1)\',0)'})
    save(OUT / 'clua.json', tests)
    text = '# Lot64 — CLUA\n\nUne commande par effet ; à lancer séparément.\n\n'
    for i in range(0, 64, 16):
        text += f'## {i+1}–{i+16}\n\n```lua\n' + '\n'.join(t['clua'] for t in tests[i:i+16]) + '\n```\n\n'
    text += '## Autres contrôleurs natifs (cycles, variantes et boucles)\n\n'
    for t in tests:
        others = [v for v in t['all_native_vvcs'] if v != t['vvc']]
        if others:
            text += t['bam'] + '\n\n```lua\n' + '\n'.join(
                f'C:Eval(\'CreateVisualEffectObject("{v}",Player1)\',0)' for v in others) + '\n```\n\n'
    (OUT / 'CLUA.md').write_text(text.rstrip()+'\n', encoding='utf-8')

def prepare():
    assert not (OUT / 'installation.json').exists()
    assets = load(BATCH / 'batch.json')['assets']; assert len(assets) == 64
    production = load(BATCH / 'production.json')
    assert production['count'] == 64 and production['visible_adjacent_duplicates'] == 0
    assert all(load(BATCH / 'verification' / (a['resref']+'.json'))['passed'] for a in assets)
    game = get_path('bg2ee_game_root', required=True)
    old = validate_pack(game / 'iee-assets/effects'); assert old.resource_count == 97
    expected = load(BATCH / 'installation-preserved-final.json')['files']
    assert profile(game) == {n: expected[n] for n in PRESERVED}
    before = {'dll_sha256': sha256_file(game/'InfinityEngine-Enhancer.dll'),
              'manifest_sha256': old.manifest_sha256, 'profile_sha256': profile(game),
              'carriers': {c['asset']: sha256_file(game/c['asset']) for c in old.manifest['runtime_bam_carriers']}}
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT/'before.json').exists(): assert load(OUT/'before.json') == before
    else: save(OUT/'before.json', before)
    CANDIDATE.mkdir(exist_ok=True)
    shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll', CANDIDATE/'InfinityEngine-Enhancer.dll')
    shutil.copy2(game/'InfinityEngine-Enhancer.ini', CANDIDATE/'InfinityEngine-Enhancer.ini')
    units = [validate_pack(ROOT / a['pack']) for a in assets]
    base = validate_pack(ROOT/'effects/installations/lot33-retimed-7b-x4-nearest-20261014-v2/candidate/iee-assets/effects')
    assert base.manifest_sha256 == old.manifest_sha256
    registry, manifest, copies = compose([base] + units)
    alternates = {a['resref']: alternate(a, p) for a, p in zip(assets, units)}
    routed = bytearray(struct.pack('<8sIIII', b'IEEEFX4\0', 3, 4, 161, 0))
    contracts = []; verified = []
    for ref, original, dims, native, phases in records(registry):
        routed.extend(original)
        extra = alternates.get(ref, [])
        routed.extend(struct.pack('<I', len(extra)))
        for cycle, table in extra:
            routed.extend(struct.pack(f'<II{len(table)}I', cycle, len(table), *table))
        profiles = [(i, t[:2*len(native[i])], False) for i, t in enumerate(phases)] + [(i,t,True) for i,t in extra]
        rows = 0
        for cycle, table, once in profiles:
            assert len(table) == 2*len(native[cycle])
            for phase, target in enumerate(table):
                slot = phase//2; fallback = table[slot*2] if once else native[cycle][slot]
                assert dims[fallback] == dims[target], (ref, cycle, phase)
                width, height = dims[target]
                for name in (ref, ref.lower()):
                    contracts.append(f'{name}\t{slot}\t{width}\t{height}\t{phase}\t{cycle}\t{fallback}\t{target}\t{int(once)}')
                    rows += 1
        verified.append({'resref': ref, 'native_cycles': len(native), 'once_alternates': len(extra), 'contracts': rows})
    manifest.update(registry_version=3, registry_bytes=len(routed),
                    registry_sha256=hashlib.sha256(routed).hexdigest().upper())
    manifest['runtime_bam_carriers'] = list(old.manifest['runtime_bam_carriers'])
    (CANDIDATE / 'override').mkdir(exist_ok=True)
    for c in manifest['runtime_bam_carriers']:
        shutil.copy2(game/c['asset'], CANDIDATE/c['asset'])
    for a in assets:
        c = load(BATCH/'checks'/(a['resref']+'.json'))['runtime_carrier']
        source = ROOT / c['path']; assert sha256_file(source) == c['sha256']
        name = f'override/{a["resref"]}.bam'
        shutil.copy2(source, CANDIDATE/name)
        manifest['runtime_bam_carriers'].append({'resref': a['resref'], 'asset': name, 'sha256': c['sha256'],
            'bytes': source.stat().st_size, 'policy': 'transparent padding only; native world geometry and cycles unchanged'})
    target = CANDIDATE/'iee-assets/effects'
    if not target.exists(): write_pack(target, bytes(routed), manifest, copies)
    pack = validate_pack(target)
    assert pack.resource_count == 161 and pack.registry_version == 3
    assert pack.resources[:97] == old.resources
    assert {f['asset']: f['sha256'] for f in pack.frames[:len(old.frames)]} == {f['asset']: f['sha256'] for f in old.frames}
    raw_bytes = sum(f['bytes'] for f in pack.frames)
    assert raw_bytes == 8208516864 and raw_bytes < 8192*1024*1024
    (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n', encoding='ascii')
    probe(target, OUT/'candidate-native-loader.log')
    installer.install_candidate(CANDIDATE, game_root=game, backup_root=OUT/'backups', verify_only=True)
    clua(assets)
    save(OUT/'plan.json', {'count': 64, 'total_resources':161, 'carriers':97, 'registry_version':3,
        'model':'seedvr2_7b_int8_convrot.safetensors', 'scale':4, 'filter':'NEAREST', 'target_fps':[30,1],
        'native_world_geometry_and_durations_preserved':True, 'existing_resources_unchanged':97,
        'profile_sha256':before['profile_sha256'], 'raw_bytes':raw_bytes, 'gpu_cache_slots':64,
        'dll_sha256':sha256_file(CANDIDATE/'InfinityEngine-Enhancer.dll'),
        'manifest_sha256':pack.manifest_sha256, 'contracts':len(contracts), 'resources':verified,
        'alternate_profiles':{k:len(v) for k,v in alternates.items() if v},
        'visual_qa':'pending-user-controlled-game'})
    print('Candidate prepared, complete 161-resource native loader passed.', flush=True)

def probe(pack, log):
    with log.open('w', encoding='utf-8') as stream:
        subprocess.run([str(BUILD/'Release/iee_effect_animation_x4_registry_tests.exe'), str(pack),
                        str(OUT/'runtime-contracts.tsv')], stdout=stream, stderr=subprocess.STDOUT, check=True)

def install():
    assert not (OUT/'installation.json').exists()
    game = get_path('bg2ee_game_root', required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    before = load(OUT/'before.json'); plan = load(OUT/'plan.json')
    assert profile(game) == before['profile_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.dll') == before['dll_sha256']
    assert sha256_file(game/'iee-assets/effects/manifest.json') == before['manifest_sha256']
    assert all(sha256_file(game/n) == h for n,h in before['carriers'].items())
    result = installer.install_candidate(CANDIDATE, game_root=game, backup_root=OUT/'backups')
    installer.verify_transaction(result.receipt_path, game_root=game)
    installed = validate_pack(game/'iee-assets/effects')
    assert installed.manifest_sha256 == plan['manifest_sha256']
    assert profile(game) == plan['profile_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.dll') == plan['dll_sha256']
    assert all(sha256_file(game/c['asset']) == c['sha256'] for c in installed.manifest['runtime_bam_carriers'])
    probe(installed.root, OUT/'installed-native-loader.log')
    names = {a['resref'] for a in load(BATCH/'batch.json')['assets']}
    receipt = rel(result.receipt_path)
    with authority.guard(ROOT, write=True):
        rows = workflow.read_csv(ROOT/'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
        save(OUT/'processing-before.json', rows)
        for row in rows:
            if row['asset_key'].rsplit(':',1)[-1] in names:
                row['installation_state']='installed'; row['installation_receipt']=receipt
        authority.commit(ROOT, {'effects/index/processing.csv':workflow.csv_bytes(rows)})
    final = {**plan, 'status':'installed-offline-verified', 'receipt':receipt,
             'character_profile':'NearestRGB-SilhouetteAlphaAA', 'character_files_byte_identical':True,
             'maps_and_vvc_controllers_changed':False, 'game_launched_by_agent':False,
             'qa_accepted':False, 'release_changed':False}
    save(OUT/'installation.json', final)
    print(json.dumps({k:v for k,v in final.items() if k != 'resources'}, ensure_ascii=False, indent=2), flush=True)

if __name__ == '__main__':
    p = argparse.ArgumentParser(); p.add_argument('action', choices=['prepare','install']); a=p.parse_args()
    {'prepare':prepare, 'install':install}[a.action]()
