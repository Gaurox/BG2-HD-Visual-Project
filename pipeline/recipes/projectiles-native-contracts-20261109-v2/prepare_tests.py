"""Finish the render-scope review and prepare native-driver tests, without game writes."""
from pathlib import Path
import copy
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
from projectile_tracking import parse_pro

OUT = ROOT / 'projectiles/analysis/native-contracts-20261109-v2'


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def js(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save(name, data):
    with (OUT / name).open('x', encoding='utf-8', newline='\n') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    assert not (OUT / 'render-summary.json').exists(), 'Use a new version for a completed review'
    baseline = js(OUT / 'summary.json')
    p = PE()
    assert sha(p.data) == baseline['executable_sha256']
    game = get_path('bg2ee_game_root', required=True)
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    extra_inputs = {}

    def read(name, typ, ext):
        path = game / 'override' / (name + '.' + ext)
        raw = path.read_bytes() if path.exists() else resolve_resource(bifs, key[name, typ])[0]
        extra_inputs[name + '.' + ext] = dict(sha256=sha(raw), override=path.exists())
        return raw

    source = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/src/iee'
    scope = source / 'core/effect_secondary_scope.h'
    indexed = source / 'core/effect_indexed_palette.h'
    hooks = source / 'hooks.cpp'
    manifest = js(game / 'iee-assets/effects/manifest.json')
    names = {r['resref'] for r in manifest['resources']}
    allowed = set(re.findall(r'"([A-Z0-9_]+)"', scope.read_text()))
    native = js(OUT / 'native-ids.json')
    fire = js(OUT / 'fireball-modes.json')
    candidates = ({n for r in native for n in r['BAMs'].split(';') if n}
        | {n for r in fire if r['PRO_owners'] for n in r['BAMs']} | {'SKYBOLT'})
    absent = sorted(candidates - allowed)
    assert absent == ['HLYMITE', 'SHAIR', 'SHEARTH', 'SKYBOLT', 'SPBOOM',
                      'SPFDEATH', 'SPGENHLA', 'SPGFLSH1', 'SPSCORIC', 'SPWRDFLD']

    # Native specialized classes do not call the scoped primary Render233f20.
    render_ranges = {
        'sky-strike-render': (0x2352f0, 0x2356b0),
        'spell-hit-render': (0x2356b0, 0x235a40),
        'scorcher-render': (0x234520, 0x234d00),
        'sky-strike-constructor': (0x227cd0, 0x227df0),
        'native-noop-render': (0x1e1e0, 0x1e1f0),
    }
    calls = {}
    for name, (start, end) in render_ranges.items():
        instructions = list(p.instructions(start, end))
        calls[name] = [i.op_str for i in instructions if i.mnemonic == 'call']
        (OUT / 'native' / (name + '.asm')).write_text(p.dump(start, end) + '\n', encoding='utf-8')
    for name in ('sky-strike-render', 'spell-hit-render', 'scorcher-render'):
        assert '0x233f20' not in calls[name]
        assert '0x29e260' in calls[name]
    assert '0x29e260' in (OUT / 'native/fireball-render.asm').read_text()
    assert 'effect_secondary_scope::enabled(ref)' in hooks.read_text()
    assert "'S','H','A','R','E','A'" in indexed.read_text()

    review = []
    for name in absent:
        assert name in names
        ids = [r['projectl_id'] for r in native if name in r['BAMs'].split(';')]
        modes = [r['mode'] for r in fire if r['PRO_owners'] and name in r['BAMs']]
        render = ('0x2356b0' if name in ('SHAIR', 'SHEARTH', 'SPFDEATH') else
                  '0x234520' if name == 'SPSCORIC' else
                  '0x1eaf90' if modes else '0x2352f0')
        palettes = sorted({s for r in native if name in r['BAMs'].split(';')
                           for s in r['palettes'].split(';') if s})
        review.append(dict(resref=name, catalogued=True, secondary_scope_enabled=False,
            native_ids=ids, FIREBALL_modes=modes, native_render=render,
            palette_BMPs=palettes, state='secondary-registration-missing-static',
            next_action='Preserve accepted pack; qualify palette/alpha/composition and register the actual FX cell; targeted HD draw QA afterwards.',
            limits='Known source-code gate omission for the native route; no live draw capture performed. Existing standalone image QA remains acquired.'))
    save('render-gaps.json', review)
    with (OUT / 'render-gaps.csv').open('x', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(review[0]))
        w.writeheader()
        for r in review:
            w.writerow({k: ';'.join(map(str, v)) if isinstance(v, list) else v for k, v in r.items()})

    # Pin the already-installed primary routes reached by ID aliases/children.
    effective = []
    for name in ('ARROWFLM', 'SKYBOLT', 'SPKLARST'):
        raw = read(name, 1021, 'pro')
        effective.append(dict(resref=name, source_sha256=sha(raw), parsed=parse_pro(raw)))
    assert effective[1]['parsed']['extended_flags'] & 128
    assert effective[2]['parsed']['secondary_raw'] == 202
    save('effective-PROs.json', effective)

    tests = copy.deepcopy(js(OUT / 'tests.json'))
    usage = list(csv.DictReader((ROOT / baseline['snapshot'] / 'usage.csv').open(encoding='utf-8-sig')))
    # Corrected field convention: SPWM157 -> SPKLARST secondary202 -> SHAREA2.
    # Use an enemy because this internal spell can petrify its target.
    test4 = next(t for t in tests if t['id'] == 'QA04')
    test4['command'] = 'C:Eval(\'ForceSpellRES("SPWM157",NearestEnemyOf(Myself))\',0)'
    test4['driver_note'] = 'Create an OGRE01 away from the party first; SPWM157 may petrify it. SPWM162 -> child201/SHAREA6, not202.'
    for t in tests:
        t['readiness'] = 'ready-current-runtime'
        if t['id'] == 'QA06':
            t['readiness'] = 'hold-HD-QA-until-SKYBOLT-registration'
        elif t['id'] == 'QA07':
            t['readiness'] = 'optional-FIRESTOR-owner-test-existing-FIREBALL-child'
    save('tests-ready.json', tests)

    # Reserve real native drivers for the missing registrations; no fictitious helper names.
    future_specs = [
        ('HLYMITE', 'SPPR214', 'engine-id:65'),
        ('SHAIR', 'SPIN835', 'engine-id:130'),
        ('SHEARTH', 'SPIN782', 'engine-id:137'),
        ('SKYBOLT', 'SPPR302', 'engine-id:80'),
        ('SPBOOM', 'SPWI404', 'ICESTORM'),
        ('SPFDEATH', 'SENDAIF1', 'engine-id:207'),
        ('SPGENHLA', 'SPPR412', 'engine-id:254'),
        ('SPGFLSH1', 'SPPR105', 'ENTANG2'),
        ('SPSCORIC', 'SPWI015', 'engine-id:190'),
        ('SPWRDFLD', 'SPWI421', 'PFIELD'),
    ]
    future = []
    for resref, spell, pro in future_specs:
        raw = read(spell, 1006, 'spl')
        refs = [r for r in usage if r['resource'] == spell and r['format'] == 'SPL']
        assert refs and any(r['projectile'] == pro for r in refs), (spell, pro)
        for r in refs:
            assert r['source_sha256'] == sha(raw)
            assert struct.unpack_from('<H', raw, int(r['offset'], 16))[0] == int(r['raw_missile_id'])
        future.append(dict(asset=resref, spell=spell, entry=pro, source_sha256=sha(raw),
            command=f'C:Eval(\'ForceSpellRES("{spell}",Player2)\',0)',
            readiness='hold-HD-QA-until-registration-and-palette-contract',
            limits='Driver verified statically; internal spell restrictions, alignment/target/area and successful native draw require runtime observation.'))
    save('tests-after-links.json', future)
    ini = (game / 'InfinityEngine-Enhancer.ini').read_bytes()
    trace = [line for line in ini.decode('utf-8-sig').splitlines() if 'EnableEffectStreamingTrace' in line]
    save('runtime-readonly-baseline.json', dict(DLL_sha256=baseline['installed_DLL_sha256'],
        manifest_sha256=baseline['installed_manifest_sha256'], INI_sha256=sha(ini),
        trace_setting=trace, trace_changed=False, game_launched=False,
        note='Visual tests are ready; detailed HD/mask/phase capture is not enabled by this analysis.'))
    save('additional-inputs.json', extra_inputs)
    result = dict(schema='bg2-projectile-native-render-review-v1',
        status='analysis-complete-ready-tests-and-registration-backlog-separated',
        executable_sha256=baseline['executable_sha256'], DLL_sha256=baseline['installed_DLL_sha256'],
        LIGHTCHA='resolved-emission-periods-not-cycles', LIGHTSTO='native-missing-BAM-no-normal-driver-in-inventoried-graph',
        source_hashes={str(q.relative_to(ROOT)).replace('\\', '/'): sha(q.read_bytes()) for q in (scope, indexed, hooks)},
        missing_secondary_registrations=absent, new_neural_jobs=0,
        ready_first_wave=[t['id'] for t in tests if t['wave'] == 1],
        extra_ready_weapon_test='QA08', optional_native_observation='QA07', held_lightning_test='QA06',
        post_registration_drivers=len(future), tests_executed_ingame=0,
        installation_changes=0, runtime_code_changes=0,
        limits=['Registration gate review is static. Palette/alpha/composition qualification precedes broad enabling.',
                'Indexed native palette adaptation currently covers SHAREA; SHAIR4/SHEARTH6 need their own contract.',
                'No prior image QA revoked, no projectile acceptance inferred, no release change.'])
    save('render-summary.json', result)
    pointer = ROOT / 'projectiles/index/native-contract-review-current.json'
    assert js(pointer)['report'].endswith('native-contracts-20261109-v1/render-summary.json')
    pointer.write_text(json.dumps(dict(schema=result['schema'],
        report='projectiles/analysis/native-contracts-20261109-v2/render-summary.json',
        report_sha256=sha((OUT / 'render-summary.json').read_bytes()),
        CLUA='projectiles/analysis/native-contracts-20261109-v2/CLUA.md'), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
