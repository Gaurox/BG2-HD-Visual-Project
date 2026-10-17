"""Bind explicit user QA to the 58 mono-BAM packs and installed repaired runtime."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

BATCH = ROOT / 'effects/batches/lot58-seedvr7b-apollo30-20261016-v1'
CLOUD = ROOT / 'effects/installations/cloud-palettealpha-20261017-v1'
ENGINE = ROOT / 'engine/InfinityEngine-Enhancer/installations/effects-gl-flush-state-20261017-v1'
OUT = ROOT / 'effects/batches/lot58-accepted-20261017-v1'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
evidence = lambda p: workflow.file_evidence(ROOT, p)
decision = 'ok tout est validé. maj le suivi et committe. puis raffiche moi le prochain lot que tu avais préparé'

OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT / 'acceptance.json').exists(), 'Final acceptance is immutable'
assets = load(BATCH / 'batch.json')['assets']
assert len(assets) == load(BATCH / 'production.json')['assets_count'] == 58
assert load(BATCH / 'verification.json')['passed'] == 58
cloud = load(CLOUD / 'installation.json')
engine = load(ENGINE / 'installation.json')
game = get_path('bg2ee_game_root', required=True)
manifest_path = game / 'iee-assets/effects/manifest.json'
assert workflow.sha256_file(manifest_path) == cloud['manifest_sha256']
assert workflow.sha256_file(game / 'InfinityEngine-Enhancer.dll') == engine['dll']['sha256']
preserved = {k: v for k, v in engine['preserved'].items() if not k.startswith('iee-assets/effects/')}
assert all(workflow.sha256_file(game / name) == item['sha256'] for name, item in preserved.items())
installed = load(manifest_path)
assert installed['registry_version'] == 3 and installed['resource_count'] == 225
members = {r['resref']: r for r in installed['resources']}
assert workflow.sha256_file(game / 'iee-assets/effects/EffectAnimations-X4.registry') == installed['registry_sha256']

# Supplemental normal-alpha variants are aliases, not replacements of the PRO mono packs.
normal = []
for ref, alias in cloud['aliases'].items():
    member = members[alias]
    run = ROOT / 'effects/ressources' / ref / 'runs' / member['interpolation_run']
    descriptor = load(run / 'run.json')
    assert descriptor['result']['sealed'] and descriptor['result']['status'] == 'completed'
    assert member['production_bam'] == ref and member['rgb_encoding'] == 'straight'
    for item in descriptor['inputs'] + descriptor['outputs']:
        assert workflow.sha256_file(ROOT / item['path']) == item['sha256']
    normal.append({'resref': ref, 'runtime_alias': alias, 'accepted': True,
                   'run': evidence(run / 'run.json'),
                   'interpolation_manifest': evidence(run / '02-interpolation/manifest.json'),
                   'verification': evidence(run / 'verification.json')})
plan = load(CLOUD / 'plan.json')
controllers = {item['name']: item for item in plan['files'] if item['name'] in plan['routed_controllers']}
assert len(controllers) == 46
assert all(workflow.sha256_file(game / name) == item['sha256'] for name, item in controllers.items())

before_path = OUT / 'processing-before.csv'
if not before_path.exists():
    before_path.write_bytes((ROOT / 'effects/index/processing.csv').read_bytes())
before = {r['asset_key']: r for r in workflow.read_csv(before_path, workflow.PROCESSING_FIELDS)}
names = {a['resref'] for a in assets}
accepted = []
for asset in assets:
    ref = asset['resref']
    check = load(BATCH / 'checks' / f'{ref}.json')
    assert workflow.sha256_file(ROOT / asset['pack'] / 'manifest.json') == check['pack_manifest_sha256']
    assert ref in members
    accepted.append(workflow.accept_asset(ROOT, ref, pack_path=asset['pack'], decision=decision,
                                          decision_date='2026-10-17', write=True))
    print('accepted', ref, flush=True)

proof = []
for row in workflow.read_csv(ROOT / 'effects/index/processing.csv', workflow.PROCESSING_FIELDS):
    old = before[row['asset_key']]
    ref = row['asset_key'].rsplit(':', 1)[-1]
    if ref not in names:
        assert row == old, row['asset_key']
        continue
    assert row['qa_state'] == 'passed' and row['spatial_state'] == row['interpolation_state'] == 'verified'
    assert row['selected_run'] == row['interpolation_run']
    assert all(row[k] == old[k] for k in ('installation_state', 'installation_receipt', 'release_state', 'release_candidate'))
    selection = load(ROOT / f'effects/index/selections/{ref}.json')
    assert selection['selected_run'] == row['selected_run']
    assert selection['qa_evidence']['path'] == row['qa_evidence']
    assert workflow.sha256_file(ROOT / row['qa_evidence']) == selection['qa_evidence']['sha256']
    proof.append({'resref': ref, 'passed': True, 'selection': evidence(ROOT / f'effects/index/selections/{ref}.json'),
                  'qa_evidence': evidence(ROOT / row['qa_evidence'])})
assert len(proof) == 58
report = {'schema': 'bg2-effects-batch-user-acceptance-v1', 'decision_date': '2026-10-17',
          'user_decision': decision, 'status': 'accepted', 'accepted_count': 58, 'accepted': accepted,
          'accepted_normal_variants': normal, 'renderer_fix_accepted': True,
          'production': evidence(BATCH / 'production.json'), 'verification': evidence(BATCH / 'verification.json'),
          'base_installation': evidence(ROOT / 'effects/installations/lot58-7b-x4-nearest30-20261017-v1/installation.json'),
          'alpha_installation': evidence(CLOUD / 'installation.json'),
          'alpha_integration_verification': evidence(CLOUD / 'verification.json'),
          'alpha_routing_plan': evidence(CLOUD / 'plan.json'),
          'renderer_installation': evidence(ENGINE / 'installation.json'),
          'installed_renderer_sha256': engine['dll']['sha256'],
          'installed_manifest_sha256': cloud['manifest_sha256'],
          'installed_registry_sha256': installed['registry_sha256'],
          'preserved_profile': preserved,
          'runtime_contract': {'registry_version': 3, 'production_assets': 219, 'runtime_resources': 225,
                               'normal_alpha_aliases': cloud['aliases'], 'routed_controllers': controllers,
                               'model': 'seedvr2_7b_int8_convrot.safetensors', 'scale': 4,
                               'filter': 'NEAREST', 'target_fps': [30, 1],
                               'duplicate_native_poses_removed_duration_preserved': True,
                               'native_contracts_verified_at_installation': 65392},
          'ingame_qa': 'explicit-user-validation-of-installed-series-and-corrections',
          'measured_presentation_cadence': 'no-new-instrumented-measurement-inferred',
          'historical_installation_receipts_immutable': True,
          'installed_files_changed': False, 'release_mutation': False}
(OUT / 'acceptance.json').write_bytes(workflow.json_bytes(report))
(OUT / 'verification.json').write_bytes(workflow.json_bytes({
    'schema': 'bg2-effects-acceptance-verification-v1', 'passed': True, 'accepted_count': 58,
    'accepted_normal_variants': 4, 'assets': proof, 'other_rows_unchanged': True,
    'installation_and_release_authorities_unchanged': True}))
print('58 accepted; 4 normal variants and renderer fix bound; other rows and installation/release unchanged.', flush=True)
