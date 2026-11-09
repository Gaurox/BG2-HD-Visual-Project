"""Reconcile current owner contracts with immutable shared evidence; no game writes.

Run in a new output directory; publish.py updates only projectile projections.
Technical compatibility is distinct from new visual acceptance or live HD proof.
"""
from pathlib import Path
from collections import Counter, defaultdict
from functools import lru_cache
import argparse
import csv
import hashlib
import json
import re
import struct
import sys
import zlib

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'pipeline/scripts'),
               str(ROOT / 'pipeline/recipes/projectiles-secondary-links-20261028-v1')]
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
from bam_export import decode_bam
from export_bam_frames import cycle_metadata
from projectile_tracking import parse_pro, dependency_activity, ids_entries, projectile_child_id
from native import PE

EXPECTED_EXE = 'B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57'
EXT = {1: 'bmp', 1000: 'bam', 1005: 'itm', 1006: 'spl', 1008: 'ids', 1016: 'eff', 1019: 'vvc', 1020: 'vef', 1021: 'pro'}
ENGINE_SOURCE = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/src/iee'
NATIVE = ROOT / 'projectiles/analysis/native-contracts-20261109-v2'


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            h.update(block)
    return h.hexdigest().upper()


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def rows(p):
    with p.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def save(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write('\n')


def savecsv(p, data):
    if not data:
        return
    with p.open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(data[0]))
        w.writeheader()
        w.writerows({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                    for k, v in r.items()} for r in data)


def parse_registry(raw):
    magic, version, scale, count, reserved = struct.unpack_from('<8sIIII', raw)
    assert (magic, version, scale, reserved) == (b'IEEEFX4\0', 3, 4, 0)
    pos = 24

    def words(n=1):
        nonlocal pos
        v = list(struct.unpack_from('<' + 'I' * n, raw, pos))
        pos += n * 4
        return v

    result = {}
    for _ in range(count):
        name = raw[pos:pos + 8].rstrip(b'\0').decode('ascii')
        pos += 8
        nf, nc = words(2)
        dims = [words(2) for _ in range(nf)]
        cycles = [words(words()[0]) for _ in range(nc)]
        fps = words(5)
        timeline = [words(fps[-1]) for _ in range(nc)]
        once = {}
        for _ in range(words()[0]):
            cycle, size = words(2)
            once[cycle] = words(size)
        assert name not in result
        result[name] = dict(dims=dims, cycles=cycles, fps=fps, timeline=timeline, once=once)
    assert pos == len(raw)
    return result


def cfg(pe, start, stop, entry):
    im = {i.address: i for i in pe.instructions(start, stop)}
    todo, seen, strings = [entry], set(), {}
    while todo:
        at = todo.pop()
        if at in seen or at not in im:
            continue
        seen.add(at)
        i = im[at]
        m = re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]', i.op_str)
        if m:
            target = i.address + i.size + (1 if m[1] == '+' else -1) * int(m[2], 16)
            off = pe.off(target)
            if off is not None:
                value = pe.data[off:off + 40].split(b'\0')[0]
                if value and all(32 <= c < 127 for c in value):
                    strings[value.decode('ascii').upper()] = hex(target)
        if i.mnemonic.startswith('j'):
            if i.op_str.startswith('0x'):
                todo.append(int(i.op_str, 16))
            if i.mnemonic == 'jmp':
                continue
        if i.mnemonic not in ('ret', 'int3'):
            todo.append(i.address + i.size)
    assert entry in seen
    return dict(strings=strings, instructions=len(seen))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', required=True)
    ap.add_argument('--reuse-physical', help='Reuse bounded prior SHA proof with identical manifest; recheck file presence/size and hash additional resources')
    ap.add_argument('--metadata-only', action='store_true', help='Development probe; cannot be published as a physical verification')
    args = ap.parse_args()
    out = ROOT / args.output
    assert not out.exists(), 'Use a new reconciliation directory'
    out.mkdir(parents=True)
    sys.stdout.reconfigure(encoding='utf-8')
    game = get_path('bg2ee_game_root', required=True)
    assets = game / 'iee-assets/effects'
    inputs = {}
    recorded_script = sha(Path(__file__))

    def recorded(p):
        label = ('config://bg2ee_game_root/' + p.relative_to(game).as_posix()
                 if p.is_relative_to(game) else p.relative_to(ROOT).as_posix())
        inputs[label] = sha(p)
        return p

    current = load(recorded(ROOT / 'projectiles/index/work-analysis-current.json'))
    snap = ROOT / current['snapshot']
    analysis = load(recorded(snap / 'analysis.json'))
    contexts = load(recorded(snap / 'contexts.json'))
    tracking = load(ROOT / 'projectiles/index/work-tracking.json')
    # QA state is preserved separately by publish; no reconciliation input cycle.
    baseline_qa = {ns: {n: {k: v for k, v in item.items() if k in ('qa', 'component_visual_qa', 'release')}
                        for n, item in tracking[ns].items()}
                   for ns in ('projectiles', 'engine_projectiles')}
    save(out / 'qa-baseline.json', baseline_qa)
    manifest = load(recorded(assets / 'manifest.json'))
    registry = parse_registry(recorded(assets / manifest['registry']).read_bytes())
    assert inputs['config://bg2ee_game_root/' + (assets / manifest['registry']).relative_to(game).as_posix()] == manifest['registry_sha256'].upper()
    catalog = {r['resref']: r for r in manifest['resources']}
    assert set(registry) == set(catalog)
    frames = defaultdict(list)
    for f in manifest['frames']:
        frames[f['resref']].append(f)
    for fs in frames.values():
        fs.sort(key=lambda f: f['resource_frame'])
    for n in ('BaldurReal.exe', 'InfinityEngine-Enhancer.dll', 'InfinityEngine-Enhancer.ini'):
        recorded(game / n)
    assert sha(game / 'BaldurReal.exe') == EXPECTED_EXE
    # Reject silently changed code: these source hashes must occur in the installation proof.
    installation = load(recorded(ROOT / 'engine/InfinityEngine-Enhancer/installations/projectiles-final-four-links-20261109-v1/installation.json'))
    assert sha(game / 'InfinityEngine-Enhancer.dll') == installation['dll']['sha256']
    before = load(recorded(ROOT / 'engine/InfinityEngine-Enhancer/installations/projectiles-final-four-links-20261109-v1/before.json'))
    for name, expected_hash in before['source_sha256'].items():
        assert sha(recorded(ENGINE_SOURCE.parents[1] / name)) == expected_hash, name
    for p in [ENGINE_SOURCE / 'hooks.cpp', *sorted((ENGINE_SOURCE / 'core').glob('effect_*.h'))]:
        recorded(p)
    scope = set(re.findall(r'^\s*"([A-Z0-9]+)"', (ENGINE_SOURCE / 'core/effect_secondary_scope.h').read_text(encoding='utf-8'), re.M))
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}

    @lru_cache(None)
    def read(n, t):
        p = game / 'override' / f'{n}.{EXT[t]}'
        if p.is_file():
            return recorded(p).read_bytes()
        if (n, t) in key:
            raw = resolve_resource(bifs, key[n, t])[0]
            inputs[f'KEY://{n}.{t}'] = digest(raw)
            return raw
        inputs[f'ABSENT://{n}.{EXT[t]}'] = None
        return None

    @lru_cache(None)
    def native_bam(n):
        raw = read(n, 1000)
        if raw is None:
            return None
        raw = zlib.decompress(raw[12:]) if raw[:4] == b'BAMC' else raw
        decoded, _, _ = decode_bam(raw)
        return raw, decoded, cycle_metadata(raw, len(decoded))

    projectl = ids_entries(read('PROJECTL', 1008))
    inventory = rows(recorded(ROOT / 'projectiles/index/resources.csv'))
    stock = {r['resref']: recorded(ROOT / r['extracted_path']).read_bytes() for r in inventory}
    active = {n: read(n, 1021) for n in stock}
    pros = {n: parse_pro(b) for n, b in active.items()}
    expected = {n: bytearray(b) for n, b in stock.items()}
    palette_routes = load(recorded(ROOT / 'effects/installations/lot31-latest-20261019-v1/palette-routes.json'))
    for r in palette_routes:
        expected[r['owner']][0x104:0x10c] = r['runtime_bam'].encode().ljust(8, b'\0')
    insect_routes = load(recorded(ROOT / 'effects/installations/insectes-continu-reference060-20261027-v1/palette-routes.json'))
    for r in insect_routes:
        off = int(r['offset'], 16)
        expected[r['owner']][off:off + 8] = r['target'].encode().ljust(8, b'\0')
    mutations = [n for n in stock if active[n] != bytes(expected[n])]
    source_uses = defaultdict(list)
    black_names = {n for ctx in contexts.values() if ctx['black_only'] for n in ctx['bam_names']}
    for cid, ctx in contexts.items():
        for u in ctx['uses']:
            source_uses[u['projectile'], u['role']].append((cid, u))
    shared = load(recorded(ROOT / 'projectiles/analysis/validation-v13-20261028-v1/secondary-progress.json'))
    shared_map = {(r['role'], r['asset']): r['current_evidence'] for r in shared['prior_shared_evidence']}
    shared_map.update({(r['role'], r['asset']): r['current_evidence'] for r in shared.get('remaining', [])})
    fire_modes = {r['mode']: r for r in load(recorded(NATIVE / 'fireball-modes.json'))}
    old_engine = {r['projectl_id']: r for r in load(recorded(NATIVE / 'native-ids.json'))}
    sprites = {int(r['animation_id'], 16): r for r in rows(recorded(ROOT / 'sprite/index/sprite_animations.csv'))}
    aliases = {'SPCLOUDK': 'X58CLK', 'SPCLOUDS': 'X58CLS', 'SPDFOGA': 'X58DFOG'}
    normal_aliases = {'BGLRYU': 'X3N001', 'SPCL236U': 'X3N002', 'SPGLYPHI': 'X3N003',
                      'WRITHING': 'X28WRTH', 'BDWOFOGA': 'X58WFOG'}
    components, controllers, links = [], [], []
    resource_proofs = {}
    loader_contracts = set()

    def qualify(n, runtime):
        cache_key = n + '>' + runtime
        if cache_key in resource_proofs:
            return resource_proofs[cache_key]
        native = native_bam(n)
        errors, notes = [], []
        if native is None:
            errors.append('missing-native-BAM')
        if runtime not in catalog:
            errors.append('missing-installed-raster')
        if errors:
            p = dict(native=n, runtime=runtime, errors=errors, notes=notes)
            resource_proofs[cache_key] = p
            return p
        _, decoded, native_cycles = native
        r, reg, fs = catalog[runtime], registry[runtime], frames[runtime]
        if len(fs) != len(reg['dims']):
            errors.append('registry-frame-count')
        if [c['frame_indices'] for c in r['cycles']] != [c['frame_indices'] for c in native_cycles]:
            errors.append('native-cycle-layout')
        if len(reg['cycles']) != len(native_cycles):
            errors.append('registry-cycle-count')
        geometry_issues = []
        for c, nc in enumerate(native_cycles):
            if c >= len(reg['cycles']) or len(reg['cycles'][c]) != len(nc['frame_indices']):
                errors.append('native-cycle-slot-count')
                continue
            count = len(nc['frame_indices'])
            for once in (0, 1):
                timeline = reg['once'].get(c, reg['timeline'][c]) if once else reg['timeline'][c]
                for phase in range(count * 2):
                    slot = phase // 2
                    image, cx, cy, _ = decoded[nc['frame_indices'][slot]]
                    size = [image.shape[1], image.shape[0]]
                    # Current V14 runtime explicitly crops the accepted64x78 pack
                    # back to its64x64 native cell and places it on variable FX canvases.
                    # Keep this source-specific rule, not a general geometry waiver.
                    cropped_magic = n == runtime == 'SPMAGMIS' and size == [64, 64]
                    lookup_size = [64, 78] if cropped_magic else size
                    ni = timeline[slot * 2] if once and c in reg['once'] else reg['cycles'][c][slot]
                    ti = timeline[phase]
                    good = True
                    for ix in (ni, ti):
                        f = fs[ix]
                        centre = f.get('runtime_centre_x1', f.get('source_centre_x1'))
                        if f['logical_size_x1'] != lookup_size or (not cropped_magic and centre is not None and centre != [cx, cy]):
                            geometry_issues.append([c, phase, ix, size, [cx, cy], f['logical_size_x1'], centre])
                            good = False
                    if good:
                        loader_contracts.add(f'{runtime}\t{slot}\t{lookup_size[0]}\t{lookup_size[1]}\t{phase}\t{c}\t{ni}\t{ti}\t{once}')
        if n == 'SPMAGMIS':
            notes.append('V14-specific native64x64 -> lookup64x78 -> cropped-source variable FX placement; immutable acceptance retained')
        if geometry_issues:
            errors.append('native-geometry-centres')
        for f in fs:
            if f['logical_size_x1'] != reg['dims'][f['resource_frame']]:
                errors.append('registry-frame-dimensions')
        selected = []
        production = r.get('production_bam', n)
        selection_path = ROOT / f'effects/index/selections/{production}.json'
        if selection_path.exists():
            sel = load(recorded(selection_path))
            qa = sel['qa_evidence']
            assert sha(recorded(ROOT / qa['path'])) == qa['sha256'].upper()
            pack_ref = sel['runtime_pack']['manifest']
            assert sha(recorded(ROOT / pack_ref['path'])) == pack_ref['sha256'].upper()
            selected_pack = load(ROOT / pack_ref['path'])
            selected = [dict(qa=qa, pack=pack_ref,
                        exact_installed_frame_hashes=[f['sha256'].upper() for f in fs] == [f['sha256'].upper() for f in selected_pack['frames']],
                        scope='Image QA only; palette variants and alpha companions qualified by their specific technical proofs')]
        p = dict(native=n, runtime=runtime, errors=sorted(set(errors)), notes=notes,
                 native_cycles=len(native_cycles), registry_frames=len(fs), fps=reg['fps'],
                 geometry_issue_count=len(geometry_issues), geometry_samples=geometry_issues[:4],
                 native_bam_sha256=digest(read(n, 1000)), source_selection=selected,
                 palette_job=r.get('palette_job', ''), encoding=r.get('rgb_encoding', ''),
                 production_bam=production)
        resource_proofs[cache_key] = p
        return p

    def component(owner, role, n, activity, path, cycle='', inherited=None, native_palette=''):
        inherited = inherited or {}
        cs = [(cid, u) for cid, u in source_uses[owner, role]
              if u['bam'] == n or catalog.get(n, {}).get('production_bam') == u['bam']]
        context_ids = sorted({cid for cid, u in cs})
        black = n in black_names or any(contexts[cid]['black_only'] for cid in context_ids)
        native = native_bam(n)
        if not black and not context_ids and native:
            # Native masks absent from the original source graph, e.g. fragment shadow.
            raw, decoded, _ = native
            paloff = struct.unpack_from('<I', raw, 0x10)[0]
            rgb = [raw[paloff + 4*i:paloff + 4*i + 3] for i in range(256)]
            transparent = raw[0x0b]
            used = set(int(v) for image, *_ in decoded for v in set(image.ravel())) - {transparent}
            black = all(rgb[i] == b'\0\0\0' for i in used)
        errors = []
        if activity in ('disabled', 'metadata'):
            state = 'inactive-or-metadata-preserved'
            runtimes = []
        elif native is None:
            state, runtimes = 'exception', []
            errors.append('missing-native-BAM')
        elif black:
            state, runtimes = 'native-mask-preserved', []
        else:
            runtimes = [aliases.get(n, n)]
            if n in normal_aliases:
                runtimes.append(normal_aliases[n])
            for runtime in runtimes:
                errors.extend(qualify(n, runtime)['errors'])
                # VVC Render establishes its own owner scope before the FX pass.
                if role != 'travel-animation' and not inherited and runtime not in scope:
                    errors.append('missing-secondary-scope')
            if cycle != '' and native and not 0 <= cycle < len(native[2]):
                errors.append('owner-cycle-outside-native-BAM')
            jobs = {c.get('job_id') for cid in context_ids for c in contexts[cid]['candidates'] if c.get('job_id')}
            job = catalog.get(runtimes[0], {}).get('palette_job')
            if role == 'travel-animation' and not inherited and jobs and job not in jobs:
                errors.append('owner-palette-job-mismatch')
            if inherited.get('palette'):
                errors.append('VVC-palette-contract')
            state = 'exception' if errors else 'compatible-shared-technical-evidence'
        refs = []
        for cid in context_ids:
            for candidate in contexts[cid]['candidates']:
                if candidate.get('evidence'):
                    recorded(ROOT / candidate['evidence'])
        evidence = shared_map.get((role, n))
        if evidence:
            recorded(ROOT / evidence)
            refs.append(evidence)
        if n in tracking.get('shared_component_route_QA', {}):
            refs += tracking['shared_component_route_QA'][n]['evidence']
        if n == 'SPMAGMIS':
            refs.append('projectiles/analysis/projectile-magique-v14-valide-20261028-v1/acceptance.json')
        if n == 'ACOWG1':
            refs.append('projectiles/analysis/cow-accepted-20261109-v1/acceptance.json')
        item = dict(owner=owner, role=role, native_resource=n, runtime_resources=runtimes, activity=activity,
                    state=state, errors=sorted(set(errors)), context_ids=context_ids, path=path, cycle=cycle,
                    owner_contract={k: pros.get(owner, {}).get(k) for k in ('bam_flags', 'extended_flags', 'area_extended_flags', 'orientations', 'travel_cycle', 'shadow_cycle', 'trail_flags', 'trailing_periods', 'colors', 'palette', 'smoke_colors', 'explosion_color')},
                    controller=inherited, native_palette=native_palette,
                    shared_runtime_evidence=sorted(set(refs)))
        components.append(item)

    def expand(owner, role, n, types, activity, path, cycle='', seen=()):
        typ = next((t for t in types if read(n, t) is not None), None)
        if typ is None or typ == 1000:
            component(owner, role, n, activity, path, cycle)
            return
        if typ == 1:
            return
        assert (n, typ) not in seen, (owner, path, 'controller cycle')
        raw = read(n, typ)
        controllers.append(dict(owner=owner, role=role, resource=n, type=EXT[typ], sha256=digest(raw)))
        if typ == 1019:
            assert raw[:8] == b'VVC V1.0'
            ref = lambda o: raw[o:o+8].split(b'\0')[0].decode('ascii').upper()
            inherited = dict(resource=n, fps=struct.unpack_from('<I', raw, 0x34)[0],
                             blend=bool(struct.unpack_from('<H', raw, 0x18)[0] & 8), palette=ref(0x44),
                             cycles=[struct.unpack_from('<I', raw, p)[0] for p in (0x68, 0x6c, 0x90)])
            for off in (8, 0x88):
                if ref(off):
                    component(owner, role, ref(off), activity, path + [f'{n}.vvc:{off:#x}', ref(off)], inherited=inherited)
        else:
            assert raw[:4] == b'VEF '
            for oa, ca in ((8, 12), (16, 20)):
                offset, count = struct.unpack_from('<I', raw, oa)[0], struct.unpack_from('<I', raw, ca)[0]
                for i in range(count):
                    pos = offset + i * 0xe0
                    kind = struct.unpack_from('<I', raw, pos + 12)[0]
                    child = raw[pos+16:pos+24].split(b'\0')[0].decode('ascii').upper()
                    if child and kind in (1, 2):
                        expand(owner, role, child, (1019, 1000) if kind == 1 else (1020, 1019, 1000),
                               activity, path + [f'{n}.vef:{i}', child], seen=seen + ((n, typ),))

    def animate(owner, role, aid, activity):
        n = sprites.get(aid, {}).get('resref', '')
        names = [n] if n else {0x300: ['SPSMPUFF'], 0x301: ['SPSMPUFF'], 0x400: ['SKLH', 'SPSHADOW']}.get(aid)
        assert names, (owner, role, aid)
        for n in names:
            component(owner, role, n, activity, [f'ANIMATE:{aid:#x}', n])

    for n, p in sorted(pros.items()):
        for role, off, target, types in p['resources']:
            activity, why = dependency_activity(p, role)
            if role == 'explosion-animation' and not p.get('area_flags', 0) & 1024:
                types = (1000,)
            cycle = p['travel_cycle'] if role == 'travel-animation' else p['shadow_cycle'] if role == 'shadow-animation' else ''
            expand(n, role, target, types, activity, [target], cycle)
        if p.get('bam_flags', 0) & 2:
            animate(n, 'smoke-animation', p['smoke_animation_id'], 'conditional' if p['extended_flags'] & 16384 else 'potential')
        if p.get('area_flags', 0) & 32:
            animate(n, 'fragment-animation', p['fragment_animation_id'], 'disabled' if p['ray_count'] else 'potential')
        if p.get('explosion_effect') not in (None, 254, 255):
            mode = fire_modes[p['explosion_effect']]
            if mode['BAMs']:
                for bam in mode['BAMs']:
                    component(n, 'native-explosion-effect', bam, 'potential', [f'FIREBALL:{mode["mode"]}', bam])
            else:
                components.append(dict(owner=n, role='native-explosion-effect', native_resource=f'FIREBALL:{mode["mode"]}',
                                       runtime_resources=[], activity='potential', state='native-procedural-preserved', errors=[],
                                       context_ids=[], path=[f'FIREBALL:{mode["mode"]}'], cycle='', owner_contract={}, controller={}, native_palette='',
                                       shared_runtime_evidence=[(NATIVE / 'fireball-modes.json').relative_to(ROOT).as_posix()]))
        if p['sparking_flags'] & 1:
            components.append(dict(owner=n, role='sparks', native_resource=f'SPRKCLR:{p["particle_color"]}',
                                   runtime_resources=[], activity='potential', state='native-procedural-preserved', errors=[],
                                   context_ids=[], path=['sparks'], cycle='', owner_contract={}, controller={}, native_palette='', shared_runtime_evidence=[]))
        for relation, raw, enabled in [('secondary-projectile', p.get('secondary_raw', 0), p.get('area_flags', 0) & 16),
                                       ('explosion-projectile', p.get('explosion_projectile_raw', 0), p.get('explosion_projectile_raw', 0))]:
            if enabled:
                ident = projectile_child_id(relation, raw)
                links.append(dict(owner=n, relation=relation, id=ident, target=projectl.get(ident, f'engine-id:{ident}')))
        if p['extended_flags'] & 1024:
            for ident, name in projectl.items():
                if name == n:
                    links.append(dict(owner=n, relation='multiple-previous', id=ident-1, target=projectl.get(ident-1, f'engine-id:{ident-1}')))
    pe = PE()
    assert digest(pe.data) == EXPECTED_EXE
    # Launching opcode references complement abilities and PRO children.
    # Mapping: IESDP BGEE op140/op141. Preserve source offsets and hashes.
    op141 = {4*s+k: 118+3*s+k for s in range(8) for k in range(3)}
    op141.update({32: 142, 33: 143, 34: 144, 35: 145, 36: 146, 37: 147, 38: 109, 39: 207})
    opcode_refs = []
    for name, typ in sorted(key):
        if typ not in (1005, 1006, 1016):
            continue
        raw = read(name, typ)
        if typ == 1016:
            effects = [(0x10, struct.unpack_from('<I', raw, 0x10)[0], *struct.unpack_from('<II', raw, 0x1c))] if raw[:8] == b'EFF V2.0' else []
        else:
            offset = struct.unpack_from('<I', raw, 0x6a)[0]
            effects = [(p, struct.unpack_from('<H', raw, p)[0], *struct.unpack_from('<II', raw, p+4))
                       for p in range(offset, len(raw)-47, 48)] if offset else []
        for offset, opcode, p1, p2 in effects:
            ident = None
            if opcode == 141:
                ident = op141.get(p2)
            elif opcode == 140:
                ident = p1-1 if p2 == 0 and p1 else p2+101 if 9 <= p2 <= 16 else None
            if ident is not None:
                opcode_refs.append(dict(resource=name, format=EXT[typ], offset=hex(offset), opcode=opcode,
                    parameter1=p1, parameter2=p2, projectl_id=ident, source_sha256=digest(raw),
                    target=f'engine-id:{ident}' if opcode == 141 else projectl.get(ident, f'engine-id:{ident}')))
    opcode_counts = Counter(r['target'] for r in opcode_refs)
    for stem, start, stop in [('cone-helper', 0x227800, 0x22792a), ('sparks-helper', 0x227b10, 0x227bee),
                              ('dimension-door-factory', 0x22c9e4, 0x22cb60), ('dimension-door-update', 0x22a060, 0x22a268),
                              ('dimension-door-render', 0x235a10, 0x235d48), ('native-range-recolour', 0x235d80, 0x235ddf)]:
        (out / (stem + '.asm')).write_text(pe.dump(start, stop) + '\n', encoding='utf-8')
    engine = []
    for row in rows(recorded(snap / 'engine-projectiles.csv')):
        ident = int(row['projectl_id'])
        n = f'engine-id:{ident}'
        effective = 3 if ident == 13 else ident
        index = pe.at(0x22eebc + effective, 1)[0]
        case = struct.unpack('<I', pe.at(0x22eddc + index * 4, 4))[0]
        graph = cfg(pe, 0x22bf00, 0x22edda, case)
        bams = sorted(s for s in graph['strings'] if (s, 1000) in key)
        palettes = sorted(s for s in graph['strings'] if (s, 1) in key)
        children = []
        classification = 'named-native-constructor' if bams else 'native-no-named-raster'
        if ident == 13:
            bams, children, classification = [], ['ARROWFLM'], 'native-normalization-to-PRO'
        elif ident in (0, 78):
            bams, classification = [], 'native-instant-or-invisible'
        elif 80 <= ident <= 90:
            bams, children, classification = [], ['SKYBOLT'], 'native-lightning-controller'
        elif ident in (24, 25):
            assert 'SPBRNHND' in pe.dump(0x227800, 0x22792a)
            bams, classification = ['SPBRNHND'], 'named-raster-in-cone-helper'
        elif ident in (142, 143, 144):
            assert 'SPBOOM' in pe.dump(0x227b10, 0x227bee)
            bams, classification = ['SPBOOM'], 'native-range-recolour-in-sparks-helper'
        elif ident == 109:
            assert 'SPDimDr' in pe.dump(0x22c9e4, 0x22cb60)
            assert "b'1'" in pe.dump(0x22a060, 0x22a268)
            bams, classification = ['SPDIMDR1', 'SPDIMDR2'], 'native-dimension-door-prefix-suffix'
        for bam in bams:
            component(n, 'native-factory-raster', bam, 'potential', [f'factory:{case:#x}', bam], native_palette=';'.join(palettes))
            if ident in (142, 143, 144):
                components[-1]['errors'].append('native-range-palette-not-transferred')
                components[-1]['state'] = 'exception'
                components[-1]['native_palette'] = {142: 'MPALETTE67', 143: 'MPALETTE65', 144: 'MPALETTE69'}[ident]
            if bam == 'SHWATER' and palettes:
                components[-1]['errors'].append('native-BMP-palette-not-transferred')
                components[-1]['state'] = 'exception'
        for child in children:
            links.append(dict(owner=n, relation='native-factory-child', id=next(k for k, v in projectl.items() if v == child), target=child))
        engine.append(dict(owner=n, projectl_id=ident, factory_case=hex(case), classification=classification,
                           BAMs=bams, palettes=palettes, children=children, graph=graph,
                           references=int(row['direct_ability_references']) + int(row['PRO_references']),
                           opcode_references=opcode_counts[n],
                           prior_used_id_proof=ident in old_engine))
    engine_by_owner = {e['owner']: e for e in engine}
    print(f'Expanded {len(pros)} PRO + {len(engine)} native IDs; {len(components)} occurrences.', flush=True)
    # Physical checks are bounded to the raster resources actually referenced above.
    relevant = {r for c in components for r in c['runtime_resources'] if r in catalog}
    physical_issues, checked, byte_count = [], 0, 0
    reused, reusable_names, reused_evidence = None, set(), None
    if args.reuse_physical:
        prior = ROOT / args.reuse_physical
        prior_inputs = load(prior / 'inputs.json')
        assert prior_inputs['config://bg2ee_game_root/iee-assets/effects/manifest.json'] == sha(assets / 'manifest.json')
        prior_resources = load(prior / 'resources.json')
        reusable_names = {r['runtime'] for r in prior_resources.values() if r['runtime'] in catalog}
        assert reusable_names <= relevant
        reused = load(prior / 'physical.json')
        assert not reused.get('metadata_only') and not reused.get('reuse_evidence')
        assert reused['backings_checked'] == sum(len(frames[n]) for n in reusable_names)
        physical_issues = list(reused['issues'])
        # Carry the exact bounded physical proof into the final immutable result.
        for name in ('physical.json', 'inputs.json', 'resources.json'):
            target = out / 'physical-baseline' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((prior / name).read_bytes())
        reused_evidence = dict(path=(out / 'physical-baseline/physical.json').relative_to(ROOT).as_posix(),
                               sha256=sha(out / 'physical-baseline/physical.json'), resources=len(reusable_names))
    for n in sorted(relevant):
        for f in frames[n]:
            path = assets / f['asset']
            checked += 1
            byte_count += f['bytes']
            if not path.is_file() or path.stat().st_size != f['bytes'] or (n not in reusable_names and not args.metadata_only and sha(path) != f['sha256'].upper()):
                physical_issues.append(dict(resource=n, asset=f['asset'], error='backing-SHA-or-size'))
        if checked % 2000 < len(frames[n]):
            print(f'Backings: {checked} checked.', flush=True)
    for carrier in manifest.get('runtime_bam_carriers', []):
        if carrier['resref'] in relevant:
            if sha(recorded(game / carrier['asset'])) != carrier['sha256'].upper():
                physical_issues.append(dict(resource=carrier['resref'], asset=carrier['asset'], error='carrier-SHA'))
    for c in components:
        if any(x['resource'] in c['runtime_resources'] for x in physical_issues):
            c['errors'].append('physical-backing-or-carrier')
            c['state'] = 'exception'
    graph = defaultdict(set)
    for edge in links:
        graph[edge['owner']].add(edge['target'])
    byowner = defaultdict(list)
    for c in components:
        byowner[c['owner']].append(c)
    owners = []
    for name in [*sorted(pros), *(e['owner'] for e in engine)]:
        seen, todo = set(), [name]
        while todo:
            node = todo.pop()
            if node in seen:
                continue
            seen.add(node)
            todo.extend(graph[node] - seen)
        bad = [c for node in seen for c in byowner[node] if c['state'] == 'exception']
        owner_errors = sorted({err for c in bad for err in c['errors']})
        if name in mutations:
            owner_errors.append('unexplained-PRO-bytes')
        unknown = sorted(node for node in seen if node not in pros and node not in {e['owner'] for e in engine})
        if unknown:
            owner_errors.append('unmapped-child')
        own = byowner[name]
        referenced = (engine_by_owner[name]['references'] + engine_by_owner[name]['opcode_references']) if name in engine_by_owner else next(int(r['direct_ability_references']) for r in rows(snap / 'work-items.csv') if r['resref'] == name)
        dormant = bool(owner_errors) and not referenced and name in {'LIGHTSTO', *(e['owner'] for e in engine)}
        state = 'documented-native-gap-no-static-driver' if dormant else 'exception-to-treat' if owner_errors else 'reconciled-compatible-contracts'
        image_qa = sorted({entry['qa']['path'] for node in seen for c in byowner[node]
                           for runtime in c['runtime_resources'] for p in [resource_proofs.get(c['native_resource'] + '>' + runtime, {})]
                           for entry in p.get('source_selection', [])})
        owners.append(dict(owner=name, state=state,
                           errors=owner_errors, closure=sorted(seen), unknown_children=unknown,
                           static_reference_occurrences=referenced, image_QA_evidence=image_qa,
                           direct_components=len(own), closure_components=sum(len(byowner[node]) for node in seen),
                           shared_runtime_evidence=sorted({p for node in seen for c in byowner[node] for p in c['shared_runtime_evidence']}),
                           active_PRO_sha256=digest(active[name]) if name in active else None))
    for path in {p for c in components for p in c['shared_runtime_evidence']}:
        recorded(ROOT / path)
    (out / 'runtime-contracts.tsv').write_text('\n'.join(sorted(loader_contracts)) + '\n', encoding='ascii')
    save(out / 'components.json', components)
    save(out / 'resources.json', resource_proofs)
    save(out / 'engine-owners.json', engine)
    savecsv(out / 'opcode-references.csv', opcode_refs)
    save(out / 'owners.json', owners)
    savecsv(out / 'owners.csv', owners)
    savecsv(out / 'controllers.csv', controllers)
    savecsv(out / 'links.csv', links)
    save(out / 'physical.json', dict(backings_checked=checked, bytes_checked=byte_count, relevant_resources=len(relevant), issues=physical_issues,
         reuse_evidence=reused_evidence, freshly_hashed_backings=sum(len(frames[n]) for n in relevant - reusable_names), metadata_only=args.metadata_only,
         meaning='Development metadata only' if args.metadata_only else 'Prior exact SHA evidence + current existence/size' if reused else 'Current exact SHA256 of referenced installed backings'))
    save(out / 'inputs.json', inputs)
    save(out / 'summary.json', dict(schema='bg2-projectile-owner-reconciliation-v1', date='2026-11-10',
         recipe_sha256=recorded_script,
         snapshot=snap.relative_to(ROOT).as_posix(), PROs=len(pros), engine_IDs=len(engine),
         owner_states=dict(Counter(o['state'] for o in owners)), component_states=dict(Counter(c['state'] for c in components)),
         component_error_counts=dict(Counter(err for c in components for err in c['errors'])),
         unexplained_PRO_changes=mutations, runtime_contracts=len(loader_contracts),
         physical_backings_checked=checked, physical_bytes_checked=byte_count, opcode_references=len(opcode_refs),
         engine_IDs_with_static_drivers=sum(bool(e['references'] or e['opcode_references']) for e in engine),
         scope='Current stock owners, active overrides, controller leaves, native factory/child edges and FIREBALL modes. Technical reuse only; immutable visual QA and release unchanged.',
         limits=['Bounded constructor CFG retains both conditional branches; not a new live draw claim.',
                 'Native fallback for unsupported compositing/palette/opacity remains part of runtime contract.',
                 'No per-owner manual QA inferred from image or shared route evidence.',
                 'No game writes, inference, installation, release or new test commands.']))
    print(json.dumps(load(out / 'summary.json'), ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
