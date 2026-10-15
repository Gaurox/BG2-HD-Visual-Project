"""Record explicit user QA for the 64 installed 7B productions and their v3 runtime."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

BATCH = ROOT/'effects/batches/lot64-seedvr7b-apollo30-strict-20261015-v3'
INSTALL = ROOT/'effects/installations/lot64-7b-x4-nearest30-20261015-v1'
OUT = ROOT/'effects/batches/lot64-accepted-20261015-v1'
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
rel = lambda p: p.relative_to(ROOT).as_posix()
OUT.mkdir(parents=True, exist_ok=True)
assert not (OUT/'acceptance.json').exists(), 'Final acceptance is immutable'

batch = load(BATCH/'batch.json'); assets = batch['assets']
production = load(BATCH/'production.json'); installation = load(INSTALL/'installation.json')
assert len(assets) == production['count'] == 64
assert load(BATCH/'verification.json')['passed'] == 64
assert installation['status'] == 'installed-offline-verified' and installation['contracts'] == 33548
game = get_path('bg2ee_game_root', required=True)
assert workflow.sha256_file(game/'InfinityEngine-Enhancer.dll') == installation['dll_sha256']
assert workflow.sha256_file(game/'iee-assets/effects/manifest.json') == installation['manifest_sha256']
assert all(workflow.sha256_file(game/n) == h for n,h in installation['profile_sha256'].items())
installed = load(game/'iee-assets/effects/manifest.json')
assert installed['registry_version'] == 3 and installed['resource_count'] == 161
members = {r['resref']: r for r in installed['resources']}
installed_frames = {f['asset']: f['sha256'] for f in installed['frames']}

before_path = OUT/'processing-before.csv'
if not before_path.exists(): before_path.write_bytes((ROOT/'effects/index/processing.csv').read_bytes())
before = {r['asset_key']: r for r in workflow.read_csv(before_path, workflow.PROCESSING_FIELDS)}
names = {a['resref'] for a in assets}
accepted = []
decision = 'tout est validé. maj le suivi et committe'
for a in assets:
    ref = a['resref']; check = load(BATCH/'checks'/f'{ref}.json')
    manifest_path = ROOT/a['pack']/'manifest.json'; unit = load(manifest_path)
    assert workflow.sha256_file(manifest_path) == check['pack_manifest_sha256']
    resource = {k:unit[k] for k in ('resref','frame_count','cycles','source','timeline')}
    assert resource == members[ref], ref
    assert all(installed_frames[f['asset']] == f['sha256'] for f in unit['frames']), ref
    result = workflow.accept_asset(ROOT, ref, pack_path=a['pack'], decision=decision,
                                   decision_date='2026-10-15', write=True)
    accepted.append(result)
    print('accepted', ref, flush=True)

after = workflow.read_csv(ROOT/'effects/index/processing.csv', workflow.PROCESSING_FIELDS)
proof = []
for row in after:
    old = before[row['asset_key']]; ref = row['asset_key'].rsplit(':',1)[-1]
    if ref not in names:
        assert row == old, row['asset_key']
        continue
    assert row['qa_state'] == 'passed' and row['spatial_state'] == row['interpolation_state'] == 'verified'
    assert row['selected_run'] == row['interpolation_run']
    assert all(row[k] == old[k] for k in ('installation_state','installation_receipt','release_state','release_candidate'))
    selection = load(ROOT/f'effects/index/selections/{ref}.json')
    assert selection['selected_run'] == row['selected_run']
    assert selection['qa_evidence']['path'] == row['qa_evidence']
    assert workflow.sha256_file(ROOT/row['qa_evidence']) == selection['qa_evidence']['sha256']
    proof.append({'resref':ref, 'passed':True, 'selected_run':row['selected_run'], 'qa_evidence':row['qa_evidence']})
assert len(proof) == 64

report = {'schema':'bg2-effects-batch-user-acceptance-v1', 'decision_date':'2026-10-15',
    'user_decision':decision, 'status':'accepted', 'accepted_count':64, 'accepted':accepted,
    'production':workflow.file_evidence(ROOT, BATCH/'production.json'),
    'native_verification':workflow.file_evidence(ROOT, BATCH/'native-verification.json'),
    'installation':workflow.file_evidence(ROOT, INSTALL/'installation.json'),
    'installed_renderer_sha256':installation['dll_sha256'],
    'installed_manifest_sha256':installation['manifest_sha256'],
    'runtime_contract':{'registry_version':3, 'new_resources':64, 'total_resources':161,
        'model':'seedvr2_7b_int8_convrot.safetensors', 'scale':4, 'filter':'NEAREST', 'target_fps':[30,1],
        'native_cycles':226, 'cycle_mode_profiles':228, 'phases':10014,
        'native_world_geometry_and_durations_preserved':True,
        'once_profile_routes':{'SPFLESHS':'cycle000-once','SPMETSWA':'cycle000-once'},
        'character_profile':'NearestRGB-SilhouetteAlphaAA', 'character_files_byte_identical':True,
        'gpu_cache_slots':64, 'cpu_payload_limit_bytes':8589934592},
    'constant_transparent_native_profiles':production['constant_native_profiles'],
    'ingame_qa':'explicit-user-validation-of-installed-series',
    'measured_presentation_cadence':'no-new-instrumented-measurement-inferred',
    'installed_files_changed':False, 'release_mutation':False}
(OUT/'acceptance.json').write_bytes(workflow.json_bytes(report))
(OUT/'verification.json').write_bytes(workflow.json_bytes({'schema':'bg2-effects-acceptance-verification-v1',
    'passed':True, 'accepted_count':64, 'assets':proof, 'other_rows_unchanged':True,
    'installation_and_release_authorities_unchanged':True}))
print('64 accepted; installed bytes, other rows and release unchanged.', flush=True)
