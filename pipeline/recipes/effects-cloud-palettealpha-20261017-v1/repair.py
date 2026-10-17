"""Repair four normal-alpha cloud aliases; leave the original PRO resources intact."""
from dataclasses import asdict
from functools import lru_cache
import argparse
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.insert(0, str(ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from workspace_paths import get_path
from bam_export import decode_bam, native_palette_alpha
from derive_animation_visual_treatment import smoothstep
from compose_effect_runtime_packs import sha256_file
import install_renderer_candidate as tx

OUT = ROOT / 'effects/installations/cloud-palettealpha-20261017-v1'
CANDIDATE = OUT / 'candidate'
GAME = get_path('bg2ee_game_root', required=True)
ALIASES = {'BDWOFOGA': 'X58WFOG', 'SPCLOUDK': 'X58CLK', 'SPCLOUDS': 'X58CLS', 'SPDFOGA': 'X58DFOG'}
RUN_SUFFIX = '-palettealpha-normal-x4-30fps-20261017-v1'
BASE = ROOT / 'effects/installations/lot58-7b-x4-nearest30-20261017-v1'
PROBE = ROOT / 'build/iee-effects-gl-flush-state-20261017-v1/Release/iee_effect_animation_x4_registry_tests.exe'
PRESERVED = ['InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini', 'BaldurReal.exe',
             'override/fpDraw.glsl', 'override/fpSprite.glsl', 'override/fpSELECT.glsl',
             'iee-assets/creature-sprites/CreatureSprites-XN.catalog']


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rel(path):
    return path.relative_to(ROOT).as_posix()


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        assert path.read_bytes() == raw, path
    else:
        path.write_bytes(raw)


def save(path, value):
    write(path, (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode())


def produce(ref):
    run_id = ref.lower() + RUN_SUFFIX
    run = ROOT / 'effects/ressources' / ref / 'runs' / run_id
    stage = run / '02-interpolation'
    if (run / 'run.json').exists():
        assert load(run / 'run.json')['result']['sealed']
        return
    old_resource = next(r for r in load(GAME / 'iee-assets/effects/manifest.json')['resources'] if r['resref'] == ref)
    parent = ROOT / 'effects/ressources' / ref / 'runs' / old_resource['interpolation_run']
    original_path = parent / '02-interpolation/manifest.json'
    original = load(original_path)
    descriptor = load(parent / 'run.json')
    spatial_path = ROOT / descriptor['inputs'][0]['path']
    assert sha256_file(spatial_path) == descriptor['inputs'][0]['sha256'].upper()
    spatial = load(spatial_path)
    source = ROOT / 'effects/ressources' / ref / 'source.bam'
    raw = source.read_bytes()
    data = zlib.decompress(raw[12:]) if raw[:4] == b'BAMC' else raw
    frames, _, transparent = decode_bam(data)
    alpha_palette = native_palette_alpha(data, transparent)
    cw, ch = spatial['aligned_canvas_size_x1']

    @lru_cache(maxsize=20)
    def aligned(index):
        indices = frames[index][0]
        x, y = spatial['frames'][index]['canvas_offset_x1']
        alpha = np.zeros((ch, cw), np.uint8)
        binary = np.zeros((ch, cw), np.uint8)
        alpha[y:y+indices.shape[0], x:x+indices.shape[1]] = alpha_palette[indices]
        binary[y:y+indices.shape[0], x:x+indices.shape[1]] = np.where(indices == transparent, 0, 255)
        return (np.repeat(np.repeat(alpha, 4, axis=0), 4, axis=1),
                np.repeat(np.repeat(binary, 4, axis=0), 4, axis=1))

    records, checked, changed, max_error = [], 0, 0, 0
    samples = {}
    for f in original['frames']:
        left, right = f['temporal_source_frames']; t = f['temporal_fraction']
        al, bl = aligned(left); ar, br = aligned(right)
        binary = np.rint(bl.astype(np.float32) * (1-t) + br.astype(np.float32) * t).astype(np.uint8)
        alpha = np.rint(al.astype(np.float32) * (1-t) + ar.astype(np.float32) * t).astype(np.uint8)
        distance = distance_transform_edt(np.pad(binary > 0, 1))[1:-1, 1:-1]
        factor = smoothstep((distance - 1.0) / 12)
        expected_old = np.rint(binary.astype(np.float32) * factor).astype(np.uint8)
        corrected = np.rint(alpha.astype(np.float32) * factor).astype(np.uint8)
        l, top, r, b = f['runtime_crop_box_x4']
        w, h = f['physical_size_x4']
        assert (r-l, b-top) == (w, h)
        old_raw = (original_path.parent / f['straight_raw_rgba_x4']).read_bytes()
        assert digest(old_raw) == f['straight_raw_rgba_x4_sha256']
        rgba = np.frombuffer(old_raw, np.uint8).reshape(h, w, 4).copy()
        error = int(np.abs(rgba[:, :, 3].astype(int) - expected_old[top:b, l:r]).max())
        assert error == 0, (ref, f['frame'], error)
        assert np.all(corrected <= expected_old)
        rgb_digest = digest(rgba[:, :, :3].tobytes())
        rgba[:, :, 3] = corrected[top:b, l:r]
        assert digest(rgba[:, :, :3].tobytes()) == rgb_digest
        payload = rgba.tobytes(); name = f'frames-rgba/frame_{f["frame"]:04d}.rgba'
        write(stage / name, payload)
        record = copy.deepcopy(f)
        for key in ['rgba_x4', 'rgba_x4_sha256', 'anchored_rgba_sha256', 'anchored_rgb_sha256']:
            record.pop(key, None)
        record.update({'raw_rgba_x4': name, 'raw_rgba_x4_sha256': digest(payload),
                       'straight_raw_rgba_x4': name, 'straight_raw_rgba_x4_sha256': digest(payload),
                       'rgb_sha256': rgb_digest, 'parent_rgba_sha256': digest(old_raw)})
        records.append(record)
        checked += 1; changed += int(np.any(rgba[:, :, 3] != expected_old[top:b, l:r]))
        max_error = max(max_error, error)
        key = (f['cycle'], f['mode'])
        if key not in samples and int(f['phase']) >= 20 and rgba[:, :, 3].max() > 30:
            old_rgba = np.frombuffer(old_raw, np.uint8).reshape(h, w, 4)
            panels = []
            for pixels in [old_rgba, rgba]:
                bg = Image.new('RGBA', (w, h), (110, 94, 70, 255))
                bg = Image.alpha_composite(bg, Image.fromarray(pixels)).convert('RGB')
                bg.thumbnail((440, 350))
                panels.append(bg)
            proof = Image.new('RGB', (sum(p.width for p in panels), max(p.height for p in panels)), (110, 94, 70))
            proof.paste(panels[0], (0, 0)); proof.paste(panels[1], (panels[0].width, 0))
            preview = run / 'verification' / f'cycle{f["cycle"]:03d}-{f["mode"]}-before-after.png'
            preview.parent.mkdir(exist_ok=True)
            proof.save(preview); samples[key] = rel(preview)
        if checked % 150 == 0:
            print(ref, checked, '/', len(original['frames']), flush=True)
    result = copy.deepcopy(original)
    result.update({'created_utc': tx.utc_now(), 'rgb_encoding': 'straight', 'frames': records,
                   'alpha_policy': 'native palette A1..254, A0/255 opaque compatibility, transparent index0; nearest x4; original temporal fractions and inner feather12',
                   'parent': {'manifest': rel(original_path), 'sha256': sha256_file(original_path)},
                   'rgb_policy': 'byte-identical straight RGB from existing SeedVR7B/Apollo30/gauss1.2 outputs'})
    for c in result['timing']['cycles']:
        c['unique_rgba'] = len({f['raw_rgba_x4_sha256'] for f in records if f['cycle'] == c['cycle'] and f['mode'] == ('loop' if c['loop_closed'] else 'once')})
    save(stage / 'manifest.json', result)
    verification = {'resref': ref, 'frames': checked, 'changed_alpha_frames': changed,
                    'rgb_byte_identical_frames': checked, 'old_alpha_reconstruction_max_error': max_error,
                    'geometry_and_temporal_sources_unchanged': True, 'source_bam_sha256': digest(raw),
                    'native_palette_max_alpha': int(alpha_palette[1:].max()),
                    'previews_before_left_after_right': list(samples.values()), 'neural_inference_runs': 0}
    save(run / 'verification.json', verification)
    d = copy.deepcopy(descriptor)
    d['run_id'] = run_id
    d['pipeline'].update({'id': 'effect-normal-palette-alpha-repair', 'version': 'v1'})
    d['inputs'] = [{'role': 'parent-interpolation-manifest', 'path': rel(original_path), 'sha256': sha256_file(original_path), 'bytes': original_path.stat().st_size},
                   {'role': 'native-bam', 'path': rel(source), 'sha256': digest(raw), 'bytes': len(raw)}]
    d['outputs'] = [{'role': 'interpolation-manifest', 'path': rel(stage / 'manifest.json'), 'sha256': sha256_file(stage / 'manifest.json'), 'bytes': (stage / 'manifest.json').stat().st_size}]
    d['provenance'].update({'generator': rel(Path(__file__)), 'created_at_utc': tx.utc_now(), 'parents': [descriptor['run_id']],
                            'command': ['repair.py', 'produce'], 'rgb_reused': True})
    d['result'] = {'status': 'completed', 'sealed': True, 'completed_at_utc': tx.utc_now()}
    save(run / 'run.json', d)
    print(ref, 'SEALED', checked, 'frames, exact RGB preserved', flush=True)


def prepare():
    assert not (OUT / 'plan.json').exists()
    active = GAME / 'iee-assets/effects'
    old = load(active / 'manifest.json')
    registry = (active / 'EffectAnimations-X4.registry').read_bytes()
    assert digest(registry) == old['registry_sha256'] and old['resource_count'] == 221
    before = {'manifest_sha256': sha256_file(active / 'manifest.json'), 'registry_sha256': digest(registry),
              'preserved': {n: asdict(tx.snapshot_file(GAME / n)) for n in PRESERVED}}
    save(OUT / 'before.json', before)
    spec = importlib.util.spec_from_file_location('lot58_installer_source', ROOT / 'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
    producer = importlib.util.module_from_spec(spec); spec.loader.exec_module(producer)
    assets = {a['resref']: a for a in load(ROOT / 'effects/batches/lot58-seedvr7b-apollo30-20261016-v1/batch.json')['assets']}
    manifest = copy.deepcopy(old); new_records = bytearray(); contracts = (BASE / 'runtime-contracts.tsv').read_text().splitlines()
    delta = []; new_frames = 0
    target = CANDIDATE / 'iee-assets/effects'; target.mkdir(parents=True, exist_ok=True)
    def add(name, raw):
        write(CANDIDATE / name, raw)
        delta.append({'name': name, 'bytes': len(raw), 'sha256': digest(raw)})
    for ref, alias in ALIASES.items():
        assert alias not in {r['resref'] for r in old['resources']}
        assert not (GAME / f'override/{alias}.bam').exists()
        a = copy.deepcopy(assets[ref]); a['interpolation_run'] = ref.lower() + RUN_SUFFIX
        raw, resource, frames, copies, checks, _ = producer.build_resource(a, alias, True)
        new_records.extend(raw); manifest['resources'].append(resource); contracts.extend(checks)
        for source, name in copies:
            # Hard links are immutable sealed outputs; installation copies bytes.
            dest = target / name
            if not dest.exists(): os.link(source, dest)
        for f in frames:
            f['frame'] = len(manifest['frames']); manifest['frames'].append(f)
            delta.append({'name': 'iee-assets/effects/' + f['asset'], 'bytes': f['bytes'], 'sha256': f['sha256']})
        new_frames += len(frames)
        carrier = (GAME / f'override/{ref}.bam').read_bytes()
        add(f'override/{alias}.bam', carrier)
        manifest['runtime_bam_carriers'].append({'resref': alias, 'asset': f'override/{alias}.bam', 'bytes': len(carrier),
             'sha256': digest(carrier), 'production_bam': ref, 'policy': 'normal-alpha alias; native carrier bytes unchanged'})
    routed = []
    for controller in manifest['runtime_vvc_controllers']:
        ref = controller['bam']
        if ref not in ALIASES: continue
        name = controller['asset']; original = (GAME / name).read_bytes()
        assert digest(original) == controller['sha256']
        assert original[8:16].rstrip(b'\0').decode() == ref and struct.unpack_from('<H', original, 0x18)[0] == 0
        raw = original[:8] + ALIASES[ref].encode().ljust(8, b'\0') + original[16:]
        add(name, raw); routed.append(name)
        controller.update({'bam': ALIASES[ref], 'sha256': digest(raw), 'purpose': 'isolated normal-alpha cloud test; native palette alpha restored'})
    registry = struct.pack('<8sIIII', b'IEEEFX4\0', 3, 4, 225, 0) + registry[24:] + new_records
    manifest.update({'created_utc': tx.utc_now(), 'resource_count': 225, 'frame_count': len(manifest['frames']),
                     'registry_bytes': len(registry), 'registry_sha256': digest(registry)})
    add('iee-assets/effects/EffectAnimations-X4.registry', registry)
    add('iee-assets/effects/manifest.json', (json.dumps(manifest, indent=2) + '\n').encode())
    write(OUT / 'runtime-contracts.tsv', ('\n'.join(contracts) + '\n').encode('ascii'))
    save(OUT / 'plan.json', {'aliases': ALIASES, 'old_resources_unchanged': 221, 'new_frames': new_frames,
         'kind': 'alias-delta', 'base_manifest_sha256': before['manifest_sha256'],
         'routed_controllers': routed, 'native_contracts': len(contracts), 'files': delta,
         'candidate_manifest_sha256': sha256_file(target / 'manifest.json')})
    probe(target, 'candidate-native-loader.log')
    print('READY', new_frames, 'new backings;', len(routed), 'VVC refs;', len(contracts), 'native contracts', flush=True)


def probe(path, name):
    with (OUT / name).open('x', encoding='utf-8') as log:
        subprocess.run([str(PROBE), '--catalogue-only', str(path), str(OUT / 'runtime-contracts.tsv')],
                        stdout=log, stderr=subprocess.STDOUT, check=True, creationflags=subprocess.CREATE_NO_WINDOW)


def verify_preserved(before):
    assert all(asdict(tx.snapshot_file(GAME / name)) == value for name, value in before['preserved'].items())


def rollback(receipt):
    assert Path(receipt['game_root']).resolve() == GAME.resolve()
    for entry in reversed(receipt['files']):
        target = tx.managed_path(GAME, entry['name'], create_parents=True)
        actual = tx.optional_snapshot(target)
        expected = tx.FileSnapshot(entry['bytes'], entry['sha256'])
        old = tx.FileSnapshot(**entry['before']) if entry['before'] else None
        assert actual in (old, expected), target
        if actual == old: continue
        if old:
            tx.atomic_copy(OUT / 'before' / entry['name'], target, old)
        else:
            tx.safe_unlink(target, expected)
    receipt['status'] = 'restored'
    tx.write_json_atomic(OUT / 'transaction.json', receipt)


def install():
    assert not (OUT / 'transaction.json').exists()
    tx.ensure_game_stopped(tx.running_game_processes)
    before, plan = load(OUT / 'before.json'), load(OUT / 'plan.json')
    verify_preserved(before)
    assert sha256_file(GAME / 'iee-assets/effects/manifest.json') == before['manifest_sha256']
    assert sha256_file(GAME / 'iee-assets/effects/EffectAnimations-X4.registry') == before['registry_sha256']
    (OUT / 'before').mkdir()
    entries = []
    for entry in plan['files']:
        name = entry['name']; source = tx.managed_path(CANDIDATE, name)
        expected = tx.FileSnapshot(entry['bytes'], entry['sha256'])
        assert tx.snapshot_file(source) == expected
        target = tx.managed_path(GAME, name)
        old = tx.optional_snapshot(target)
        if old:
            # Only references + catalogue are replacements; all RGBA/carriers are new names.
            assert name in plan['routed_controllers'] or name.endswith('/manifest.json') or name.endswith('/EffectAnimations-X4.registry')
            backup = tx.managed_path(OUT / 'before', name, create_parents=True)
            tx.atomic_copy(target, backup, old)
        entries.append({**entry, 'before': asdict(old) if old else None})
    receipt = {'schema': 'bg2-effects-alias-delta-transaction-v1', 'status': 'prepared', 'game_root': str(GAME),
               'created_utc': tx.utc_now(), 'files': entries, 'candidate_root': rel(CANDIDATE)}
    tx.write_json_atomic(OUT / 'transaction.json', receipt)
    try:
        receipt['status'] = 'installing'; tx.write_json_atomic(OUT / 'transaction.json', receipt)
        for entry in entries:
            target = tx.managed_path(GAME, entry['name'], create_parents=True)
            old = tx.FileSnapshot(**entry['before']) if entry['before'] else None
            assert tx.optional_snapshot(target) == old
            tx.atomic_copy(tx.managed_path(CANDIDATE, entry['name']), target, tx.FileSnapshot(entry['bytes'], entry['sha256']))
        for entry in entries:
            assert tx.snapshot_file(tx.managed_path(GAME, entry['name'])) == tx.FileSnapshot(entry['bytes'], entry['sha256'])
        verify_preserved(before)
        probe(GAME / 'iee-assets/effects', 'installed-native-loader.log')
        receipt['status'] = 'installed'; receipt['installed_utc'] = tx.utc_now()
        tx.write_json_atomic(OUT / 'transaction.json', receipt)
    except Exception:
        rollback(receipt)
        raise
    save(OUT / 'installation.json', {'status': 'installed-offline-verified', 'aliases': ALIASES,
         'resources': 225, 'existing_resources_unchanged': 221, 'new_backings': plan['new_frames'],
         'routed_controllers': len(plan['routed_controllers']), 'native_contracts': plan['native_contracts'],
         'transaction': rel(OUT / 'transaction.json'), 'dll_ini_character_shaders_unchanged': True,
         'old_pro_resources_unchanged': True, 'game_and_loader_stopped': True,
         'game_launched': False, 'visual_qa': 'pending-user', 'release_changed': False,
         'manifest_sha256': sha256_file(GAME / 'iee-assets/effects/manifest.json')})
    print('INSTALLED; exact RGB reused; native palette alpha restored; original PRO resources retained', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['produce', 'prepare', 'install', 'restore'])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.action == 'produce':
        for ref in ALIASES: produce(ref)
    elif args.action == 'prepare': prepare()
    elif args.action == 'install': install()
    else:
        tx.ensure_game_stopped(tx.running_game_processes)
        rollback(load(OUT / 'transaction.json'))
