"""Read-only native projectile analysis + source-verified CLUA test plan.

No inference, game mutation, integration/QA promotion, or historical rewrite.
Addresses below are observations pinned to one executable, never hook contracts.
"""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / 'pipeline/scripts'),
                str(ROOT / 'pipeline/recipes/projectiles-secondary-links-20261028-v1')]
from native import PE
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path
from projectile_tracking import ids_entries, parse_pro

OUT = ROOT / 'projectiles/analysis/native-contracts-20261109-v2'
SNAP = ROOT / 'projectiles/analysis/20261109-native-child-indices-v7'
EXPECTED_EXE = 'B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57'
EXT = {1: 'bmp', 4: 'wav', 5: 'wfx', 1000: 'bam', 1006: 'spl',
       1008: 'ids', 1019: 'vvc', 1020: 'vef', 1021: 'pro', 1005: 'itm'}


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def rows(path):
    return list(csv.DictReader(path.open(encoding='utf-8-sig', newline='')))


def save(name, value):
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')


def savecsv(name, values):
    with (OUT / name).open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(values[0]))
        w.writeheader()
        w.writerows(values)


def main():
    assert not (OUT / 'summary.json').exists(), 'Completed analysis: use a new version'
    OUT.mkdir(parents=True, exist_ok=True)
    game = get_path('bg2ee_game_root', required=True)
    p = PE()
    assert sha(p.data) == EXPECTED_EXE
    pe = struct.unpack_from('<I', p.data, 60)[0]
    base = struct.unpack_from('<Q', p.data, pe + 48)[0]
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    inputs = {}

    def read(name, typ):
        override = game / 'override' / (name + '.' + EXT[typ])
        if override.exists():
            raw = override.read_bytes()
            origin = 'config://bg2ee_game_root/override/' + override.name
        elif (name, typ) in key:
            raw, bif = resolve_resource(bifs, key[name, typ])
            origin = 'KEY://' + name + '.' + str(typ) + '@' + bif
        else:
            return None
        inputs[f'{name}.{EXT[typ]}'] = dict(sha256=sha(raw), origin=origin)
        return raw

    def write_asm(name, start, end):
        (OUT / 'native').mkdir(exist_ok=True)
        (OUT / 'native' / (name + '.asm')).write_text(p.dump(start, end) + '\n', encoding='utf-8')

    # Disassemble contiguous function code: .pdata has split unwind regions.
    # A first unwind region alone is not a complete function body.
    ranges = {
        'bam-constructor': (0x2270e0, 0x2275fa),
        'bam-update': (0x228650, 0x228e5d),
        'factory': (0x22bf00, 0x22edda),
        'invisible-constructor': (0x227a40, 0x227b0a),
        'bam-render-gate': (0x233f20, 0x233f92),
        'call-lightning-update': (0x228e60, 0x229090),
        'fireball-constructor': (0x1e8a20, 0x1e964c),
        'fireball-render': (0x1eaf90, 0x1eb2de),
        'area-fireball-create': (0x22f8e4, 0x22f9b8),
        'resource-tables-load': (0x237916, 0x23795c),
        'vefproj-name': (0x19ca0, 0x19cc7),
        'projectl-name': (0x18440, 0x18467),
        'ids-lookup': (0x11b480, 0x11b4b7),
        'area-child-constructor': (0x226d98, 0x226dbc),
        'area-explosion-child': (0x22bde2, 0x22bdf3),
        'area-secondary-child': (0x22f7b2, 0x22f7d0),
        'effect-create-bam': (0x2590ff, 0x259154),
    }
    for name, (s, e) in ranges.items():
        write_asm(name, s, e)

    child_ranges = ['area-child-constructor', 'area-explosion-child', 'area-secondary-child']
    proof = '\n\n'.join((OUT / 'native' / (name + '.asm')).read_text(encoding='utf-8') for name in child_ranges)
    assert 'dec ax' in proof and 'inc cx' in proof
    (OUT / 'native/child-index-conventions.asm').write_text(proof, encoding='utf-8')

    def cfg(start, stop, entry):
        im = {i.address: i for i in p.instructions(start, stop)}
        todo, seen, strings, calls = [entry], set(), {}, set()
        while todo:
            at = todo.pop()
            if at in seen or at not in im:
                continue
            seen.add(at)
            i = im[at]
            m = re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]', i.op_str)
            if m:
                target = i.address + i.size + (1 if m[1] == '+' else -1) * int(m[2], 16)
                offset = p.off(target)
                if offset is not None:
                    value = p.data[offset:offset + 40].split(b'\0')[0]
                    if value and all(32 <= c < 127 for c in value):
                        strings[value.decode('ascii').upper()] = hex(target)
            if i.mnemonic == 'call' and i.op_str.startswith('0x'):
                calls.add(i.op_str)
            if i.mnemonic.startswith('j'):
                if i.op_str.startswith('0x'):
                    todo.append(int(i.op_str, 16))
                if i.mnemonic == 'jmp':
                    continue
            if i.mnemonic not in ('ret', 'int3'):
                todo.append(i.address + i.size)
        assert entry in seen
        return dict(strings=strings, calls=sorted(calls), instructions=len(seen))

    projectl = ids_entries(read('PROJECTL', 1008))
    vefproj = ids_entries(read('VEFPROJ', 1008))
    missile = ids_entries(read('MISSILE', 1008))
    fireids = ids_entries(read('FIREBALL', 1008))
    catalog_raw = (game / 'iee-assets/effects/manifest.json').read_bytes()
    catalog = json.loads(catalog_raw)
    catalog_names = {r['resref'] for r in catalog['resources']}
    usage = rows(SNAP / 'usage.csv')
    links = rows(SNAP / 'projectile-links.csv')
    engine = rows(SNAP / 'engine-projectiles.csv')
    routes = rows(ROOT / 'projectiles/index/engine-routes.csv')
    known = load(SNAP / 'analysis.json')['hardcoded_ids_referenced']
    before_tracking = (ROOT / 'projectiles/index/work-tracking.json').read_bytes()

    # Confirm native source data and the exact executable operations supporting the interpretation.
    lightcha = parse_pro(read('LIGHTCHA', 1021))
    assert lightcha['trailing_periods'] == [5, 7, 9]
    constructor = p.dump(0x22751d, 0x22759f)
    update = p.dump(0x228d73, 0x228e1f)
    for field in ('0x36c', '0x36e', '0x370'):
        assert field in constructor and field in update
    assert update.count('idiv ecx') == 3 and 'call 0x258da0' in update
    schedule = []
    for tick in range(1, 316):
        slot = next((i for i, period in enumerate([5, 7, 9]) if tick % period == 0), None)
        if slot is not None:
            schedule.append(dict(tick=tick, trail=slot + 1, resref=f'SPCHLGT{slot + 1}'))
    save('lightcha.json', dict(
        conclusion='resolved-emission-periods-not-cycle-ids', periods=[5, 7, 9],
        file_offsets=['0x14e', '0x150', '0x152'], resource_header_bytes=8,
        constructor='0x227569..0x22758c: file+8 base -> object+36c/36e/370',
        update='0x228d73..0x228e1a: increment counter, idiv(period), remainder==0, first eligible trail, CreateVisualEffect',
        schedule_first_315_updates=schedule,
        result='No required SPCHLGT3 cycle9; no new image or runtime change; existing observed cycle QA retained.',
        historical_correction='Earlier audits treating these words as sequence IDs were incorrect; immutable evidence retained.',
        limits='Static scheduling proof; frame rate in seconds and all native draws not remeasured.'))

    lightsto = parse_pro(read('LIGHTSTO', 1021))
    owners = [r for r in links if r['target'] == 'LIGHTSTO']
    direct = [r for r in usage if r['projectile'] == 'LIGHTSTO']
    assert not owners and not direct and read('MAGMIS', 1000) is None
    assert lightsto['explosion_projectile_raw'] == 23 and projectl[22] == 'SKYBOLT'
    save('lightsto.json', dict(
        conclusion='unreferenced-stock-PRO-with-genuine-missing-native-BAM', projectl_id=92, missile_id=93,
        parsed_source=lightsto, direct_ability_references=direct, incoming_PRO_edges=owners,
        MAGMIS_KEY_BAM_present=False, MAGMIS_override_BAM_present=False,
        outgoing_child='SKYBOLT PROJECTL22; file0x21a=23 is a one-based factory argument',
        decision='Keep native bytes; do not substitute SPMAGMIS. No normal driver found in scanned SPL/ITM/PRO graph.',
        limits='Scripts/opcodes/mods may construct an ID dynamically. No claim of universal unused status; synthetic test not needed for current QA lot.'))

    factory_rows = []
    for ident in known:
        # Native input is missile ID=PROJECTL+1; raw14 is explicitly normalized to raw4.
        effective = 3 if ident == 13 else ident
        index = p.at(0x22eebc + effective, 1)[0]
        case = struct.unpack('<I', p.at(0x22eddc + index * 4, 4))[0]
        graph = cfg(0x22bf00, 0x22edda, case)
        raster = sorted(n for n in graph['strings'] if (n, 1000) in key)
        palettes = sorted(n for n in graph['strings'] if (n, 1) in key)
        children = []
        classification = 'named-native-constructor'
        limits = 'Static constructor names and native table resolution; per-owner visual QA remains separate.'
        if ident == 13:
            classification = 'native-id-normalization-to-PRO'
            assert projectl[effective] == 'ARROWFLM'
            children = ['PROJECTL3:ARROWFLM']
        elif ident == 38:
            classification = 'generic-native-no-raster-fallback'
            assert ident not in vefproj and ident not in projectl and case == 0x22e8f5
            limits = 'Active VEFPROJ/PROJECTL have no38; native factory falls back to base CProjectile. ICE_FRAGMENTS label is not a missing BAM.'
        elif ident == 78:
            classification = 'native-invisible-travelling'
            # Constructor SPFIREBL is a disabled placeholder, not an image gap.
            raster = []
            limits = '227a40 allocates SPFIREBL then sets object+21c=0 at227ac0; Render233f85 skips raster. Native delay/gameplay retained.'
        elif 80 <= ident <= 90:
            classification = 'native-lightning-controller-with-SKYBOLT-child'
            raster = []
            children = ['PROJECTL22:SKYBOLT']
            limits = 'SPMAGMIS constructor placeholder is not final visible asset: vtable59c5e0 Render slot98=1e1e0 (ret); child3c0=22, factory input23 at22c761 and229064.'
            assert struct.unpack('<Q', p.at(0x59c5e0 + 0x98, 8))[0] - base == 0x1e1e0
        elif ident == 0:
            classification = 'native-instant-no-raster'
        elif ident == 188:
            classification = 'existing-accepted-COW-bridge'
        for name in raster:
            assert name in catalog_names, name
        factory_rows.append(dict(projectl_id=ident, missile_id=ident + 1,
            symbol=missile.get(ident + 1, ''), effective_projectl_id=effective,
            factory_case=hex(case), classification=classification,
            BAMs=';'.join(raster), palettes=';'.join(palettes), children=';'.join(children),
            BAMs_in_catalogue=all(n in catalog_names for n in raster),
            direct_ability_references=next(int(r['direct_ability_references']) for r in engine if int(r['projectl_id']) == ident),
            PRO_references=next(int(r['PRO_references']) for r in engine if int(r['projectl_id']) == ident),
            literal_graph=graph, limits=limits))
    save('native-ids.json', factory_rows)
    savecsv('native-ids.csv', [{k: v for k, v in r.items() if k != 'literal_graph'} for r in factory_rows])

    fire_rows = []
    for mode, symbol in sorted(fireids.items()):
        if mode == 255:
            continue
        index = p.at(0x1e969c + mode, 1)[0]
        case = struct.unpack('<I', p.at(0x1e964c + index * 4, 4))[0]
        graph = cfg(0x1e8a20, 0x1e964c, case)
        raster = sorted(n for n in graph['strings'] if (n, 1000) in key)
        sound = sorted(n for n in graph['strings'] if (n, 4) in key)
        named_pros = sorted(r['projectile'] for r in routes if r['role'] == 'native-explosion-effect' and int(r['value']) == mode)
        # Unknown literal names in unused legacy dragon modes are reported, not produced speculatively.
        absent_literals = sorted(n for n in graph['strings'] if n.startswith('SPRDR') and not any(name == n for name, typ in key))
        assert all(n in catalog_names for n in raster), raster
        fire_rows.append(dict(mode=mode, symbol=symbol, factory_case=hex(case),
            PRO_owners=named_pros, BAMs=raster, sounds=sound,
            absent_legacy_literals=absent_literals,
            classification='native-mode-with-named-raster' if raster else 'native-mode-no-named-raster-in-constructor',
            literal_graph=graph,
            limits='Constructor CFG only, both conditional paths retained; explicit ring/spread/children and procedural particles remain native. Raster draw not inferred from catalog presence.'))
    save('fireball-modes.json', fire_rows)
    savecsv('fireball-modes.csv', [{k: ';'.join(map(str, v)) if isinstance(v, list) else v
        for k, v in r.items() if k != 'literal_graph'} for r in fire_rows])

    # Source-verified native drivers: no synthetic SPL/VVC/PRO or installation needed.
    tests = []
    def test(code, name, typ, target, watch, wave=1):
        raw = read(name, typ)
        assert raw is not None
        refs = [r for r in usage if r['resource'] == name and r['format'] == EXT[typ].upper()]
        assert refs and any(r['projectile'] == target for r in refs), (name, target)
        for r in refs:
            # Runtime SPL/ITM source still agrees with inventoried ability offset.
            assert sha(raw) == r['source_sha256']
            assert struct.unpack_from('<H', raw, int(r['offset'], 16))[0] == int(r['raw_missile_id'])
        command = f'C:Eval(\'ForceSpellRES("{name}",Player2)\',0)' if typ == 1006 else f'C:CreateItem("{name}",5)'
        tests.append(dict(id=code, wave=wave, resource=name + '.' + EXT[typ],
            source_sha256=sha(raw), entry_projectile=target, command=command,
            watch=watch, ability_references=refs, state='prepared-not-run',
            scope='Visual result of tested runtime route only; no global PRO/ID/phase acceptance.'))

    test('QA01', 'SPWI304', 1006, 'PFIRE2', 'Boule de feu : vol, impact, transparence ; accord historique avant correctifs.')
    test('QA02', 'SPWI313', 1006, 'TRAPSKUL', 'Piège à crâne : vol, crâne posé, fragments à déclenchement ; accord historique avant correctifs.')
    test('QA03', 'SPWI118', 1006, 'CHROMORB', 'Orbe chromatique : vol/couches, alpha et disparition ; accord historique avant correctifs.')
    test('QA04', 'SPWM157', 1006, 'SPKLARST', 'Anneau202 SHAREA2 via SPKLARST ; cible ennemie, petrification possible.')
    test('QA05', 'BOLT07', 1005, 'TSKULLNP', 'Tir réel BOLT07 : vol SKLT, impact/fragments SKLH ; équiper une arbalète compatible, tirer sur ennemi vivant.')
    test('QA06', 'SPPR302', 1006, 'engine-id:80', 'Extérieur : Appel de la foudre ; contrôleur80..83 selon niveau -> enfant SKYBOLT. Visuel distinct de LIGHTCHA.', 2)
    test('QA07', 'SPWI399', 1006, 'FIRESTOR', 'FIRESTOR -> enfant37 FIREBALL ; pas ICE_FRAGMENTS. Sort interne, pas Tempete de feu standard.', 2)
    test('QA08', 'XBOW15', 1005, 'engine-id:13', 'Tir réel XBOW15 avec sa capacité utilisant missile14 : normalisation native vers ARROWFLM ; ne pas assimiler création objet et tir.', 2)
    save('tests.json', tests)
    savecsv('tests.csv', [{k: v for k, v in r.items() if k != 'ability_references'} for r in tests])
    save('inputs.json', inputs)

    save('summary.json', dict(
        schema='bg2-projectile-native-contract-review-v1', status='technical-analysis-complete-QA-prepared',
        executable_sha256=EXPECTED_EXE, installed_DLL_sha256=sha((game / 'InfinityEngine-Enhancer.dll').read_bytes()),
        installed_manifest_sha256=sha(catalog_raw), installed_resources=catalog['resource_count'],
        snapshot=SNAP.relative_to(ROOT).as_posix(), LIGHTCHA='resolved-periods-5-7-9',
        LIGHTSTO='missing-MAGMIS-with-no-SPL-ITM-PRO-incoming-reference; preserve-native',
        native_used_ids=len(factory_rows), native_classes=dict(__import__('collections').Counter(r['classification'] for r in factory_rows)),
        FIREBALL_stock_PRO_occurrences=sum(len(r['PRO_owners']) for r in fire_rows),
        FIREBALL_stock_modes=sum(bool(r['PRO_owners']) for r in fire_rows),
        FIREBALL_modes_analysed=len(fire_rows),
        constructor_named_BAMs=sorted({n for r in fire_rows if r['PRO_owners'] for n in r['BAMs']}),
        confirmed_new_image_jobs=[], tests_prepared=len(tests),
        completed_ingame_tests=0, game_writes=0, inference_jobs=0, runtime_changes=0,
        tracking_sha256_before=sha(before_tracking),
        limits=['Static CFG is bounded to identified constructors; computed resources/runtime branches may require targeted observation.',
                'Missing legacy literals in unused modes are not missing jobs for the current stock PRO graph.',
                'No visual QA/installation/release states promoted; prior QA retained.']))
    assert (ROOT / 'projectiles/index/work-tracking.json').read_bytes() == before_tracking
    print(json.dumps(load(OUT / 'summary.json'), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
