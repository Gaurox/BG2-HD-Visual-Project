"""Accept the six observed HD routes and retain shared evidence for future reuse."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
from collections import Counter
import copy
import gzip
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path
from projectile_tracking import validate_tracking, read_csv

OUT = ROOT / 'projectiles/analysis/native-six-links-accepted-20261109-v1'
INSTALL = ROOT / 'engine/InfinityEngine-Enhancer/installations/projectiles-native-six-links-20261109-v1'
NAMES = ['SKYBOLT', 'SPBOOM', 'SPFDEATH', 'SPGENHLA', 'SPGFLSH1', 'SPWRDFLD']
EV = 'projectiles/analysis/native-six-links-accepted-20261109-v1/acceptance.json'
DECISION = "ok les 6 tests sont bons, mais c'etait le meme qu'on a validé avant. a cette vitesse j'en ai poour 2 ans a valider les 400 projectiles non ?"


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
    # The executable's logger uses local time; this Nov9 run is CET/UTC+1.
    cut = datetime.fromisoformat(installed['installed_utc'].replace('Z', '+00:00')).astimezone(
        timezone(timedelta(hours=1))).strftime('[%Y-%m-%d %H:%M:%S')
    selected, parsed, counters = [], [], []
    for path in game.glob('InfinityEngine-Enhancer*.log'):
        raw = path.read_bytes()
        for line in raw.decode('utf-8', errors='replace').splitlines():
            if line[:20] < cut:
                continue
            if 'traceDropped=' in line:
                counters.append(line)
            if 'EFX_STREAM_ROW' not in line:
                continue
            values = dict(re.findall(r'(\w+)=([^ ]+)', line))
            if values.get('resref') in NAMES and values.get('swap') == 'false':
                selected.append(line)
                parsed.append(values)
    result = {}
    for name in NAMES:
        rows = [r for r in parsed if r['resref'] == name and r.get('paused') == 'false']
        hd = [r for r in rows if r.get('hd') == 'true' and r.get('outcome') == '0']
        assert hd and any(r.get('masked') == 'true' for r in hd)
        assert any(int(r['phase']) % 2 for r in hd)
        result[name] = dict(draw_rows=len(rows), HD_draws=len(hd),
            HD_masked=sum(r.get('masked') == 'true' for r in hd),
            HD_odd_phase_draws=sum(int(r['phase']) % 2 for r in hd),
            sequences=sorted({int(r['sequence']) for r in hd}),
            phases=sorted({int(r['phase']) for r in hd}),
            outcomes=dict(Counter(r['outcome'] for r in rows)),
            sample=next(line for line in selected if 'resref=' + name + ' ' in line and 'hd=true' in line and 'masked=true' in line))
    before_path = ROOT / 'projectiles/index/work-tracking.json'
    raw_before = before_path.read_bytes()
    tracking = json.loads(raw_before)
    before = copy.deepcopy(tracking)
    OUT.mkdir(parents=True)
    extracted = ('\n'.join(selected + counters) + '\n').encode('utf-8')
    (OUT / 'trace-selected.txt.gz').write_bytes(gzip.compress(extracted, mtime=0))
    (OUT / 'tracking-before.json').write_bytes(raw_before)
    save('trace-summary.json', dict(resources=result, log_local_cutoff=cut,
        draw_outcome_0='Hd', draw_outcome_1='CpuNotReady',
        draw_row_ok_false='ok belongs to swap events; false on draw rows is not a draw failure',
        maximum_traceDropped=max((int(x) for line in counters for x in re.findall(r'traceDropped=(\d+)', line)), default=0),
        compressed_trace_sha256=digest((OUT / 'trace-selected.txt.gz').read_bytes()),
        limits=['Sampled draws, not all phases/cycles/owners or a measured global presentation cadence.',
                'Transient cold CPU misses retained in counts; no rejection/crash inferred from a swap-only ok field.',
                'Trace buffer drops prevent claiming exhaustive draw capture.']))
    save('acceptance.json', dict(schema='bg2-projectile-scoped-acceptance-v1',
        status='accepted-observed-HD-component-routes', decision_date='2026-11-09', user_decision=DECISION,
        resources=NAMES, installed_DLL_sha256=installed['dll']['sha256'],
        installation=INSTALL.relative_to(ROOT).as_posix() + '/installation.json',
        trace_summary='projectiles/analysis/native-six-links-accepted-20261109-v1/trace-summary.json',
        qualification='projectiles/analysis/native-six-links-20261109-v1/qualification.json',
        user_visual_approval=True, HD_mask_and_odd_phase_draws_observed_for_all_six=True,
        shared_route_evidence=True, new_inference=0, release_changed=False,
        limits=['Observed routes only; source/QA hashes and palette/blend/geometry/timing compatibility govern reuse.',
                'No requirement for manual testing every PRO alias; no global243 visual acceptance invented.']))
    nodes = [('projectiles', 'SKYBOLT', 'SKYBOLT'), ('projectiles', 'ICESTORM', 'SPBOOM'),
             ('engine_projectiles', '207', 'SPFDEATH'), ('engine_projectiles', '254', 'SPGENHLA'),
             ('projectiles', 'ENTANG2', 'SPGFLSH1'), ('projectiles', 'PFIELD', 'SPWRDFLD')]
    for ns, name, resource in nodes:
        node = tracking[ns][name]
        node['integration'].update(state='accepted-observed-component-route', HD_review_state='accepted-observed',
            evidence=list(dict.fromkeys(node['integration']['evidence'] + [EV])))
        qa = node['qa']
        qa['evidence'] = list(dict.fromkeys(qa['evidence'] + [EV]))
        qa['scope'].append(resource + ' : nouveau pont secondaire accepté visuellement ;dessinsHD/masqués/phasesimpaires observés.')
        qa['reviewed_on'] = '2026-11-09'
        qa['limits'] = ('Composant observé sur le nouveau pontHD seulement ;pas de QA de tous propriétaires/palettes/cycles '
                        'ni de cadence globale. Preuves antérieures conservées dans leurs décisions. '
                        'HLYMITE/SHAIR/SHEARTH/SPSCORIC restent distincts.')
        # Prior scope/limits remain linked to their original contract; this record adds the changed HD route.
        qa['latest_manual_feedback'] = dict(text=DECISION, evidence=EV,
            rendering='Six changed HD component routes accepted; shared technical evidence captured.')
    batch = tracking['runtime_route_installations']['native-six-links-20261109-v1']
    batch.update(state='accepted-observed-HD-component-routes', acceptance=EV,
                 reusable_shared_evidence=True)
    tracking['shared_component_route_QA'] = {
        **tracking.get('shared_component_route_QA', {}),
        **{name: dict(state='accepted-observed-HD-component-route', evidence=[EV],
              runtime_class='SpellHit' if name == 'SPFDEATH' else
                  'Fireball' if name in ('SPBOOM', 'SPGFLSH1', 'SPWRDFLD') else 'SkyStrike',
              reuse_policy='Reuse exact pack plus compatible palette/blend/geometry/cycles/timing; audit aliases automatically, manual review only for real differences.')
           for name in NAMES}}
    tracking['manual_QA_policy'] = dict(recorded_on='2026-11-09', evidence=EV,
        strategy='Group by actual render contract and visual variant; reuse previous immutable QA and shared runtime evidence.',
        automated='Source/pack identity, owner edges, palettes, geometry, cycles, blend and loader contracts.',
        manual='New visual variants or reproducible anomalies; a representative route only when a changed contract needs observation.',
        avoid='No exhaustive one-by-one manual pass over every PRO/engine alias; no repeat of unchanged accepted components.')
    validate_tracking(tracking, {r['resref'] for r in read_csv(ROOT / 'projectiles/index/resources.csv')})
    touched = {(ns, name) for ns, name, resource in nodes}
    for ns in ('projectiles', 'engine_projectiles'):
        for name, node in before[ns].items():
            if (ns, name) not in touched:
                assert node.get('qa') == tracking[ns][name].get('qa')
            for field in ('installation', 'release'):
                assert node.get(field) == tracking[ns][name].get(field)
    before_path.write_text(json.dumps(tracking, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(accepted_resources=NAMES, trace=result,
        remaining=['HLYMITE', 'SHAIR', 'SHEARTH', 'SPSCORIC'], manual_pass_over_all_PRO=False),
        ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
