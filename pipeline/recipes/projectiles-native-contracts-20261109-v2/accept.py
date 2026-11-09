"""Record approval of every CLUA example, without inferring missing HD routes."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bg2lib import load_key, resolve_resource
from workspace_paths import get_path
from projectile_tracking import validate_tracking, read_csv

SOURCE = ROOT / 'projectiles/analysis/native-contracts-20261109-v2'
OUT = ROOT / 'projectiles/analysis/native-clua-accepted-20261109-v1'
EVIDENCE = 'projectiles/analysis/native-clua-accepted-20261109-v1/acceptance.json'
DECISION = "ok tous les test présents dans le fichier commandes clua sont validés. MAJ le suivi et propose la suite"
LIMITS = ('Accord visuel sur le rendu courant des commandes testées. Pas de nouvelle preuve '
          'de substitution HD/masque/phases, de tous niveaux/cycles/palettes, ni de release. '
          'Les10enregistrements secondaires manquants restent ouverts.')


def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest().upper()


def evidence(p):
    return dict(path=p.relative_to(ROOT).as_posix(), sha256=sha(p))


def save(p, data):
    assert not p.exists(), 'Acceptance evidence is immutable'
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    assert not OUT.exists(), 'Use a new acceptance version'
    game = get_path('bg2ee_game_root', required=True)
    baseline = load(SOURCE / 'summary.json')
    assert sha(game / 'InfinityEngine-Enhancer.dll') == baseline['installed_DLL_sha256']
    assert sha(game / 'iee-assets/effects/manifest.json') == baseline['installed_manifest_sha256']
    manifest = load(game / 'iee-assets/effects/manifest.json')
    assert sha(game / 'iee-assets/effects/EffectAnimations-X4.registry') == manifest['registry_sha256']
    bifs, entries = load_key()
    key = {(n.upper(), t): loc for n, t, loc in entries}
    ready = load(SOURCE / 'tests-ready.json')
    extra = load(SOURCE / 'tests-after-links.json')
    sources = {}
    for test in ready + extra:
        name, ext = test['resource'].split('.') if 'resource' in test else (test['spell'], 'spl')
        typ = 1006 if ext == 'spl' else 1005
        path = game / 'override' / (name + '.' + ext)
        raw = path.read_bytes() if path.exists() else resolve_resource(bifs, key[name, typ])[0]
        value = hashlib.sha256(raw).hexdigest().upper()
        assert value == test['source_sha256'], name
        sources[name + '.' + ext] = value
    tracking_path = ROOT / 'projectiles/index/work-tracking.json'
    before_bytes = tracking_path.read_bytes()
    before = load(tracking_path)
    after = copy.deepcopy(before)
    changed = {'projectiles': set(), 'engine_projectiles': set()}
    today = '2026-11-09'

    def qa(namespace, name, scopes):
        node = after.setdefault(namespace, {}).setdefault(name, {})
        old = node.get('qa', {})
        previous_evidence = old.get('evidence', [])
        if isinstance(previous_evidence, str):
            previous_evidence = [previous_evidence]
        previous_scope = old.get('scope', [])
        if isinstance(previous_scope, str):
            previous_scope = [previous_scope]
        node['qa'] = dict(state='accepted-observed-components',
            evidence=list(dict.fromkeys(previous_evidence + [EVIDENCE])),
            scope=list(dict.fromkeys(previous_scope + scopes)), reviewed_on=today,
            limits=LIMITS + (' Limite antérieure conservée : ' + old['limits'] if old.get('limits') else ''),
            latest_manual_feedback=dict(text=DECISION, evidence=EVIDENCE,
                rendering='Current installed runtime; visual acceptance, no new HD draw measurement'))
        changed[namespace].add(name)

    pro_scopes = {
        'PFIRE2': ['QA01/SPWI304 : vol FIREBAT et explosion observés après les correctifs de rendu.'],
        'TRAPSKUL': ['QA02/SPWI313 : vol SKLT, crâne posé et fragments SKLH observés.'],
        'CHROMORB': ['QA03/SPWI118 : SPCHRORB, couches/transparence observées après correctifs.'],
        'SPKLARST': ['QA04/SPWM157 : rendu courant et enfant202 SHAREA+SHAREA2 observés.'],
        'TSKULLNP': ['QA05/BOLT07 tiré avec XBOW12 par Jan : vol SKLT/impact-fragments SKLH observés.'],
        'SKYBOLT': ['QA06/SPPR302 : aspect courant du résultat observé ;enregistrement secondaire HD encore absent.'],
        'FIRESTOR': ['QA07/SPWI399 : aspect courant de la route FIRESTOR→FIREBALL observé.'],
        'ARROWFLM': ['QA08/XBOW15 : tir courant via normalisation native13→3, Y31P056/fuméeSPSMPUFF observés.'],
    }
    for name, scopes in pro_scopes.items():
        qa('projectiles', name, scopes)
    qa('engine_projectiles', '202', ['QA04/SPWM157→SPKLARST→202 : SHAREA avec paletteSHAREA2 observé.'])
    qa('engine_projectiles', '13', ['QA08/XBOW15 : alias natif projectile13/missile14→ARROWFLM3 observé.'])
    for test in extra:
        if test['asset'] == 'SKYBOLT':
            continue  # SPPR302 level/capability was not specified; do not grant all80..83.
        entry = test['entry']
        namespace, name = ('engine_projectiles', entry.split(':')[1]) if entry.startswith('engine-id:') else ('projectiles', entry)
        qa(namespace, name, [f"CLUA {test['spell']} : aspect courant {test['asset']} observé ;raccord HD secondaire non accordé."])

    case_records = []
    for test in ready:
        case_records.append(dict(id=test['id'], command=test['command'],
            entry=test['entry_projectile'], state='accepted-observed-current-rendering',
            source_resource=test['resource'], source_sha256=test['source_sha256'],
            formerly_prepared_as=test['readiness']))
    for test in extra:
        case_records.append(dict(id='native-' + test['asset'], command=test['command'],
            entry=test['entry'], state='accepted-observed-current-rendering',
            source_resource=test['spell'] + '.spl', source_sha256=test['source_sha256'],
            HD_route_state='secondary-registration-still-open'))
    assert len(case_records) == 18 and len(sources) == 17
    after.setdefault('visual_test_batches', {})['native-clua-20261109-v1'] = dict(
        state='accepted-observed-current-rendering', evidence=[EVIDENCE], reviewed_on=today,
        tests=18, unique_native_drivers=17,
        lightning_family='SPPR302 current observed result accepted; actual level-dependent ID80..83 unspecified',
        limits=LIMITS)
    validate_tracking(after, {r['resref'] for r in read_csv(ROOT / 'projectiles/index/resources.csv')})
    # Preserve all integration/install/release decisions and every QA outside this lot.
    for namespace in ('projectiles', 'engine_projectiles'):
        for name, node in before.get(namespace, {}).items():
            for state in ('integration', 'installation', 'release'):
                assert after[namespace][name].get(state) == node.get(state)
            if name not in changed[namespace]:
                assert after[namespace][name].get('qa') == node.get('qa')
    OUT.mkdir(parents=True)
    (OUT / 'tracking-before.json').write_bytes(before_bytes)
    save(OUT / 'acceptance.json', dict(schema='bg2-projectile-scoped-acceptance-v1',
        status='accepted-observed-current-rendering', recorded_utc=datetime.now(timezone.utc).isoformat(),
        decision_date=today, user_decision=DECISION,
        command_file=evidence(SOURCE / 'CLUA.md'), prepared_tests=evidence(SOURCE / 'tests-ready.json'),
        additional_tests=evidence(SOURCE / 'tests-after-links.json'),
        native_review=evidence(SOURCE / 'render-summary.json'),
        case_records=case_records, declared_cases=18, unique_native_drivers=17,
        active_driver_sha256=sources, installed_DLL_sha256=baseline['installed_DLL_sha256'],
        installed_manifest_sha256=baseline['installed_manifest_sha256'],
        installed_registry_sha256=manifest['registry_sha256'],
        trace_setting='EnableEffectStreamingTrace=false at preparation; no new trace capture analysed',
        QA_updated={k: sorted(v) for k, v in changed.items()},
        secondary_registration_backlog=load(SOURCE / 'render-summary.json')['missing_secondary_registrations'],
        new_HD_draw_proof=False, new_inference=0, installation_changes=0, release_changes=0,
        limits=[LIMITS, 'Agreement covers all examples in the command file, including the previously reserved native drivers.',
                'SPPR302 level/capability unspecified: no QA of every controller80..83 inferred.',
                'Newly routed HD cells will have a changed runtime contract and need a targeted check after that change.']))
    tracking_path.write_text(json.dumps(after, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    counts = {state: sum(n.get('qa', {}).get('state') == state for n in after['projectiles'].values())
              for state in ('accepted-observed-components', 'historical-visual-acceptance-runtime-changed')}
    save(OUT / 'tracking-update.json', dict(QA_counts=counts,
        tracking_sha256=sha(tracking_path), outside_lot_QA_preserved=True,
        integration_installation_release_preserved=True))
    print(json.dumps(dict(recorded_cases=18, unique_drivers=17,
        updated={k: sorted(v) for k, v in changed.items()}, QA_counts=counts,
        HD_registrations_still_open=10), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
