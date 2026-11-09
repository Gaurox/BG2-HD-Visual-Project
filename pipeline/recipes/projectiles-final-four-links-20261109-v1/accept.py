"""Accept the three colour variants; document SPWI985's native removal effect."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timedelta, timezone
import copy
import gzip
import hashlib
import json
import re
import struct
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
from projectile_tracking import validate_tracking, read_csv

OUT = ROOT / 'projectiles/analysis/final-four-colours-accepted-20261109-v1'
PLAN = ROOT / 'projectiles/analysis/final-four-links-20261109-v1'
INSTALL = ROOT / 'engine/InfinityEngine-Enhancer/installations/projectiles-final-four-links-20261109-v1'
EV = 'projectiles/analysis/final-four-colours-accepted-20261109-v1/acceptance.json'
DECISION = "les 3 tests sont validé visuellement. le premier fait disparaitre le player 2 c'est normal ?"


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def digest(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def save(name, data):
    with (OUT / name).open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    assert not OUT.exists()
    game = get_path('bg2ee_game_root', required=True)
    installed = load(INSTALL / 'installation.json')
    assert digest((game / 'InfinityEngine-Enhancer.dll').read_bytes()) == installed['dll']['sha256']
    cut = datetime.fromisoformat(installed['installed_utc'].replace('Z', '+00:00')).astimezone(
        timezone(timedelta(hours=1))).strftime('[%Y-%m-%d %H:%M:%S')
    names = ['HLYMITE', 'SHAIR', 'SHEARTH']
    rows, selected, palette_rows = [], [], []
    for p in game.glob('InfinityEngine-Enhancer*.log'):
        for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
            if line[:20] < cut:
                continue
            if 'EFX_PALETTE_BOUND' in line and any('resref=' + n + ' ' in line for n in names):
                palette_rows.append(line)
            if 'EFX_STREAM_ROW' not in line:
                continue
            values = dict(re.findall(r'(\w+)=([^ ]+)', line))
            if values.get('resref') in names and values.get('swap') == 'false':
                selected.append(line)
                rows.append(values)
    summary = {}
    for name in names:
        draws = [r for r in rows if r['resref'] == name and r.get('paused') == 'false']
        hd = [r for r in draws if r.get('hd') == 'true' and r.get('outcome') == '0']
        bindings = [line for line in palette_rows if 'resref=' + name + ' ' in line]
        assert hd and bindings and any(int(r['phase']) % 2 for r in hd)
        summary[name] = dict(HD_draws=len(hd), masked_HD_draws=sum(r.get('masked') == 'true' for r in hd),
            odd_HD_draws=sum(int(r['phase']) % 2 for r in hd), palette_bindings=bindings,
            outcomes=dict(Counter(r['outcome'] for r in draws)),
            scope='Observed new coloured route only; mask not claimed when absent from trace.')
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    override = game / 'override/SPWI985.spl'
    spell = override.read_bytes() if override.exists() else resolve_resource(bifs, key['SPWI985', 1006])[0]
    ability, count, effects = struct.unpack_from('<IHI', spell, 0x64)
    fx_count, first = struct.unpack_from('<HH', spell, ability + 0x1e)
    fx = effects + first * 48
    assert count == 1 and fx_count == 1 and struct.unpack_from('<H', spell, fx)[0] == 168
    source_effect = dict(spell='SPWI985', sha256=digest(spell), effect_offset=hex(fx),
        opcode=168, target=spell[fx + 2], timing=spell[fx + 12],
        duration_seconds=struct.unpack_from('<I', spell, fx + 14)[0],
        parameter1=struct.unpack_from('<I', spell, fx + 4)[0],
        parameter2=struct.unpack_from('<I', spell, fx + 8)[0],
        meaning='Native Remove Creature, not a graphical disappearance defect.',
        source='https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op168',
        instruction_correction='Never target a party member with this internal test spell; reload the pre-test save. No visual retest needed.')
    before_path = ROOT / 'projectiles/index/work-tracking.json'
    before_raw = before_path.read_bytes()
    before = json.loads(before_raw)
    after = copy.deepcopy(before)
    OUT.mkdir(parents=True)
    (OUT / 'CLUA-tested.md').write_bytes((PLAN / 'CLUA.md').read_bytes())
    (OUT / 'tracking-before.json').write_bytes(before_raw)
    (OUT / 'trace-selected.txt.gz').write_bytes(gzip.compress(('\n'.join(selected + palette_rows) + '\n').encode('utf-8'), mtime=0))
    save('trace-summary.json', dict(resources=summary, local_cutoff=cut,
        limits=['Sampled HD/odd phase/palette bindings, not every cycle/owner/frame.',
                'SHEARTH had zero masked trace rows: no new occlusion-mask proof claimed.',
                'SPSCORIC not requested or observed again; its prior visual QA and nine-cycle static qualification remain separate.']))
    save('SPWI985-native-effect.json', source_effect)
    save('acceptance.json', dict(schema='bg2-projectile-scoped-acceptance-v1',
        status='accepted-three-observed-colour-variants', user_decision=DECISION,
        decision_date='2026-11-09', installed_dll_sha256=installed['dll']['sha256'],
        installation=INSTALL.relative_to(ROOT).as_posix() + '/installation.json',
        tested_commands=dict(path='projectiles/analysis/final-four-colours-accepted-20261109-v1/CLUA-tested.md',
                             sha256=digest((OUT / 'CLUA-tested.md').read_bytes())),
        observed_variants=['HLYMITE red194', 'SHAIR4/130', 'SHEARTH6/137'],
        source_effect_analysis='projectiles/analysis/final-four-colours-accepted-20261109-v1/SPWI985-native-effect.json',
        actual_palette_HD_binding_observed=True, SPSCORIC_new_live_draw_claimed=False,
        repeat_visual_tests_requested=0, new_inference=0, release_changed=False))
    for ident, name in [('194', 'HLYMITE'), ('130', 'SHAIR'), ('137', 'SHEARTH')]:
        node = after['engine_projectiles'][ident]
        node['integration'].update(state='accepted-observed-colour-route', HD_review_state='accepted-three-colour-variants',
            evidence=list(dict.fromkeys(node['integration']['evidence'] + [EV])))
        previous = node.get('qa', {})
        evidence = previous.get('evidence', [])
        if isinstance(evidence, str):
            evidence = [evidence]
        node['qa'] = dict(state='accepted-observed-components', evidence=list(dict.fromkeys(evidence + [EV])),
            scope=[name + ' coloured native route' + ident + ': explicit visual approval and realized palette bound to HD upload.'],
            reviewed_on='2026-11-09', limits='Observed colour only; no QA of all owners/palettes/cycles or unobserved masks/cadence.',
            latest_manual_feedback=dict(text=DECISION, evidence=EV))
    for ident in ['65', '118', '119']:
        after['engine_projectiles'][ident]['integration'].update(
            state='verified-static-installed-component-route',
            HD_review_state='neutral-identity-verified-no-manual-retest-requested')
    batch = after['runtime_route_installations']['final-four-links-20261109-v1']
    batch.update(state='four-routes-qualified-three-colours-accepted', acceptance=EV,
        remaining_manual_variants=[], beam_visual_approval_reused=True)
    after.setdefault('shared_component_route_QA', {}).update({name: dict(
        state='accepted-observed-coloured-component-route', evidence=[EV], native_id=ident,
        limits='Reuse only with matching palette/blend/geometry/cycles/timing; neutral variants qualified separately.')
        for ident, name in [('194', 'HLYMITE'), ('130', 'SHAIR'), ('137', 'SHEARTH')]})
    after['manual_QA_policy']['test_driver_constraints'] = 'Inspect gameplay opcodes before choosing a native visual driver; internal destructive spells target disposable creatures, never party members.'
    validate_tracking(after, {r['resref'] for r in read_csv(ROOT / 'projectiles/index/resources.csv')})
    for ns in ['projectiles', 'engine_projectiles']:
        for name, node in before.get(ns, {}).items():
            if ns != 'engine_projectiles' or name not in ('194', '130', '137'):
                assert node.get('qa') == after[ns][name].get('qa')
            for field in ['installation', 'release']:
                assert node.get(field) == after[ns][name].get(field)
    before_path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Accepted three colours + actual palette/HD bindings. SPWI985 opcode168 confirmed; party target instruction corrected; no retests.')


if __name__ == '__main__':
    main()
