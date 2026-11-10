"""Freeze retained final effect runtime, without reading or modifying the game."""
from __future__ import annotations

import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from compose_effect_runtime_packs import validate_pack

OUT = Path(__file__).resolve().parent
RELEASE = ROOT / 'releases/BG2-HD-Upscale'
PACK = RELEASE / 'release-inputs/effects/accepted-20261110-v1'
RUNTIME = RELEASE / 'release-inputs/effects/runtime-20261110-v1'
BASE = ROOT / 'effects/installations/cow-sprite-bridge-20261109-v1/candidate/iee-assets/effects'
EXCLUDE = {'M3BASN', 'M3BAST', 'M3ENTN', 'M3ENTT', 'M3SPCS', 'M3SPCX',
           'MFR13B', 'MFX06S', 'MFX34R', 'XMWN20'}


def load(p):
    return json.loads(Path(p).read_text(encoding='utf-8-sig'))


def save(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def rel(p):
    return p.resolve().relative_to(ROOT).as_posix()


def sha(p):
    with Path(p).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest().upper()


def evidence(p):
    return dict(path=rel(p), bytes=p.stat().st_size, sha256=sha(p))


def records(raw):
    magic, version, scale, count, reserved = struct.unpack_from('<8sIIII', raw)
    assert (magic, version, scale, reserved) == (b'IEEEFX4\0', 3, 4, 0)
    off = 24
    result = {}
    for _ in range(count):
        start = off
        name = raw[off:off+8].rstrip(b'\0').decode('ascii')
        nf, nc = struct.unpack_from('<II', raw, off+8)
        off += 16 + 8*nf
        for _ in range(nc):
            n, = struct.unpack_from('<I', raw, off)
            off += 4 + 4*n
        phases, = struct.unpack_from('<I', raw, off+16)
        off += 20 + 4*nc*phases
        alternates, = struct.unpack_from('<I', raw, off)
        off += 4
        for _ in range(alternates):
            _, n = struct.unpack_from('<II', raw, off)
            off += 8 + 4*n
        assert name not in result
        result[name] = raw[start:off]
    assert off == len(raw)
    return result


class Resolver:
    def __init__(self):
        # Retained candidates only. Never use the live game as a payload source.
        self.roots = []
        for domain in ('effects/installations', 'effects/batches', 'engine/InfinityEngine-Enhancer/installations'):
            for parent, dirs, files in os.walk(ROOT / domain):
                dirs[:] = [d for d in dirs if d not in ('before', 'backups', 'decoded-x2')]
                if 'candidate' in Path(parent).parts and files:
                    self.roots.append(Path(parent))
        self.cache = {}

    def find(self, name, size, digest, hints=()):
        key = (name, size, digest.upper())
        if key in self.cache:
            return self.cache[key]
        for p in [*(ROOT/h for h in hints if h), *(r/name for r in self.roots)]:
            if p.is_file() and p.stat().st_size == size and sha(p) == digest.upper():
                self.cache[key] = p
                return p
        raise RuntimeError(f'Retained payload missing: {name} {size} {digest}')


def main():
    assert not (OUT/'integration.json').exists(), 'Use a new version for a sealed build'
    base = load(BASE/'manifest.json')
    raw = (BASE/'EffectAnimations-X4.registry').read_bytes()
    assert hashlib.sha256(raw).hexdigest().upper() == base['registry_sha256']
    recs = records(raw)
    selections = {p.stem: load(p) for p in (ROOT/'effects/index/selections').glob('*.json')}
    accepted = {n: s for n, s in selections.items() if s['mode'] == 'x4'}
    assert len(accepted) == 424
    assert sum(s['mode'] == 'native' for s in selections.values()) == 6
    for n, s in accepted.items():
        for e in (s['qa_evidence'], s['runtime_pack']['manifest'], s['runtime_pack']['registry']):
            assert sha(ROOT/e['path']) == e['sha256'].upper(), (n, e['path'])
    resources = {r['resref']: r for r in base['resources']}
    assert set(accepted) <= set(resources)
    retained = sorted(set(resources) - EXCLUDE)
    # The accepted SeedVR test20 becomes canonical in this new release only.
    # Geometry, clocks, pixels and native BAM remain exact; replace identity only.
    remap = {'SPCSPRAI': 'M3SPCS'}
    frames_by_ref = {}
    for f in base['frames']:
        frames_by_ref.setdefault(f['resref'], []).append(f)
    resolver = Resolver()
    frozen_frames_ready = (PACK/'EffectAnimations-X4.registry').is_file()
    PACK.mkdir(parents=True, exist_ok=True)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    manifest = {k: copy.deepcopy(base[k]) for k in ('schema', 'status', 'scale', 'registry', 'registry_magic', 'registry_version')}
    manifest.update(resources=[], frames=[], source_packs=[dict(path=rel(BASE), manifest_sha256=sha(BASE/'manifest.json'))])
    blocks = []
    for i, name in enumerate(retained):
        origin = remap.get(name, name)
        r = copy.deepcopy(resources[origin])
        r['resref'] = name
        r['release_source_runtime_ref'] = origin
        manifest['resources'].append(r)
        blocks.append(name.encode().ljust(8, b'\0') + recs[origin][8:])
        for f in sorted(frames_by_ref[origin], key=lambda f: f['resource_frame']):
            oldname = f['asset']
            hints = [f.get('source'), str(Path(f['source_pack'])/oldname) if f.get('source_pack') else None,
                     str(BASE.relative_to(ROOT)/oldname)]
            target_name = re.sub(r'^EFX4-[A-Z0-9_]+-frame', f'EFX4-{name}-frame', oldname)
            target = PACK/target_name
            if frozen_frames_ready:
                # Registry is written only after every frame copy completes.
                # validate_pack below rehashes the retained output before sealing.
                assert target.is_file() and target.stat().st_size == f['bytes'], target
                source = target
            else:
                source = resolver.find(oldname, f['bytes'], f['sha256'], hints)
                if target.exists():
                    assert sha(target) == f['sha256'].upper(), target
                else:
                    shutil.copy2(source, target)
            item = copy.deepcopy(f)
            item.update(frame=len(manifest['frames']), resref=name, asset=target_name,
                        source=rel(source), source_pack=rel(BASE))
            manifest['frames'].append(item)
        if i % 75 == 0:
            print(f'Frozen {i+1}/{len(retained)} runtime resources', flush=True)
    registry = struct.pack('<8sIIII', b'IEEEFX4\0', 3, 4, len(retained), 0) + b''.join(blocks)
    (PACK/'EffectAnimations-X4.registry').write_bytes(registry)
    manifest.update(resource_count=len(retained), frame_count=len(manifest['frames']),
                    registry_bytes=len(registry), registry_sha256=sha(PACK/'EffectAnimations-X4.registry'))

    runtime_files = {}
    def runtime(record, destination=None):
        dest = destination or record['asset']
        old = record['asset']
        source = resolver.find(Path(old).name, record['bytes'], record['sha256'], [str(BASE.parent.parent.relative_to(ROOT)/old)])
        target = RUNTIME/Path(dest).name
        if target.exists():
            assert sha(target) == record['sha256'], dest
        else:
            shutil.copy2(source, target)
        item = dict(source=rel(target), destination=dest, bytes=target.stat().st_size, sha256=sha(target))
        assert dest not in runtime_files or runtime_files[dest] == item, dest
        runtime_files[dest] = item

    carriers = {c['resref']: c for c in base['runtime_bam_carriers']}
    for name in retained:
        origin = remap.get(name, name)
        if origin in carriers:
            runtime(carriers[origin], f'override/{name}.bam')
    for c in base['runtime_vvc_controllers']:
        if c['purpose'].startswith('native '):
            assert c['bam'] in retained
            runtime(c)
    # Exact stock PROs with only the travel BAM reference changed for lot31.
    routes = load(ROOT/'effects/installations/lot31-latest-20261019-v1/palette-routes.json')
    for route in routes:
        assert route['runtime_bam'] in retained
        if route['patched']:
            source = ROOT/'effects/installations/lot31-latest-20261019-v1/candidate/override'/(route['owner']+'.pro')
            data = source.read_bytes()
            assert data[:8] == b'PRO V1.0'
            assert data[0x104:0x10c].rstrip(b'\0').decode().upper() == route['runtime_bam']
            runtime(dict(asset=f'override/{source.name}', bytes=len(data), sha256=sha(source)))
    manifest['runtime_bam_carriers'] = [dict(c, asset=f'override/{name}.bam')
        for name in retained if (c := carriers.get(remap.get(name, name)))]
    manifest['runtime_vvc_controllers'] = [c for c in base['runtime_vvc_controllers'] if c['purpose'].startswith('native ')]
    save(PACK/'manifest.json', manifest)
    validate_pack(PACK)
    selected_evidence = []
    for name, s in sorted(accepted.items()):
        origin = s['contract']['source'].get('original_runtime_ref', name)
        if name == 'SPCSPRAI': origin = 'M3SPCS'
        assert origin in resources
        selected_evidence.append(dict(resref=name, selected_run=s['selected_run'],
            selection=evidence(ROOT/f'effects/index/selections/{name}.json'), qa_evidence=s['qa_evidence'],
            accepted_runtime_ref=origin, release_runtime_ref=name if name=='SPCSPRAI' else origin,
            scope='Acquired image QA; retained installed native geometry/timing/blend adapters and owner qualifications; no new exhaustive gameplay QA.'))
    proof = dict(schema='bg2-effects-release-finalization-v1', selected_assets=selected_evidence,
        accepted_x4=424, accepted_native=sorted(n for n,s in selections.items() if s['mode']=='native'),
        not_required=67, runtime_resources=len(retained), runtime_backings=len(manifest['frames']),
        excluded_comparison_runtime_refs=sorted(EXCLUDE), canonical_promotions=remap,
        runtime_files=list(runtime_files.values()), native_pro_routes=evidence(ROOT/'effects/installations/lot31-latest-20261019-v1/palette-routes.json'),
        projectile_closure=evidence(ROOT/'projectiles/analysis/images-routes-closed-20261110-v1/closure.json'),
        cow_qa=evidence(ROOT/'projectiles/analysis/cow-accepted-20261109-v1/acceptance.json'),
        game_modified=False, new_visual_qa=False, public_release_approved=False)
    save(OUT/'integration.json', proof)
    old = load(RELEASE/'manifests/effect-release-candidates.json')
    save(OUT/'effect-release-candidates-before.json', old)
    candidate = copy.deepcopy(old['candidates'][0])
    candidate.update(candidate_id='effects-accepted-native-routes-20261110-v1',
        resources=[dict(asset_id='effects:bam:'+n, resref=n, selected_run=s['selected_run'],
                        qa_evidence=s['qa_evidence']['path'], qa_evidence_sha256=s['qa_evidence']['sha256']) for n,s in sorted(accepted.items())],
        runtime_pack=dict(path=rel(PACK), manifest='manifest.json', manifest_sha256=sha(PACK/'manifest.json'),
            registry='EffectAnimations-X4.registry', registry_version=3, registry_sha256=manifest['registry_sha256'],
            registry_bytes=len(registry), scale=4, target_fps=30),
        runtime_files=list(runtime_files.values()), integration_evidence=evidence(OUT/'integration.json'),
        renderer_contract=dict(bundle_id='iee-0.1.0-alpha.10', dll_sha256='ED9A5E4EE34D695DB84448EE7E9A8E221D39E6DEBD340479F114AD4E9132A844',
            required_ini_key='Shaders.EnableEffectAnimationX4=true'),
        payload_projection=dict(status='integrated',content_manifest_integration=True,
            reason='424 accepted effects, retained runtime variants/native carriers/owner routing and accepted COW bridge; scoped acquired QA preserved.'))
    save(RELEASE/'manifests/effect-release-candidates.json', dict(old,generated_by=rel(Path(__file__)), candidates=[candidate]))
    rows = list(csv.DictReader((ROOT/'effects/index/processing.csv').open(encoding='utf-8-sig',newline='')))
    save(OUT/'effect-processing-before.json', rows)
    for row in rows:
        if row['asset_key'].split(':')[-1] in accepted:
            row.update(release_state='approved', release_candidate=candidate['candidate_id'])
    with (ROOT/'effects/index/processing.csv').open('w',encoding='utf-8',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]),lineterminator='\n');writer.writeheader();writer.writerows(rows)
    print(json.dumps(dict(resources=len(retained),frames=len(manifest['frames']),runtime_files=len(runtime_files),bytes=sum(f['bytes'] for f in manifest['frames'])),indent=2),flush=True)


if __name__ == '__main__':
    main()
