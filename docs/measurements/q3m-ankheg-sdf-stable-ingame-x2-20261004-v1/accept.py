"""Record explicit user acceptance of the exact installed SDF + wait variant."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
QA = ROOT / 'sprite/index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json'


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)


def save(path, value, mode='w'):
    with path.open(mode, encoding='utf-8', newline='\n') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


assert not QA.exists(), 'Immutable QA decision already exists'
generation = load(HERE / 'current-generation.json')
receipt_path = HERE / 'ingame-installation/active-test.json'
receipt = load(receipt_path)
baseline = load(HERE / 'baseline.json')
game = Path(load(ROOT / 'config/workspace-paths.local.json')['paths']['bg2ee_game_root'])
assert receipt['status'] == 'installed-pending-ingame-qa'
assert generation['family'] == 'monster_ankheg' and generation['animation_ids'] == ['0x3000']
assert sha(game / 'InfinityEngine-Enhancer.dll') == generation['dll']['sha256']
for item in baseline['unchanged_assets']:
    assert sha(game / item['relative_path']) == item['sha256'], item['relative_path']
for sealed in (generation['runtime'], generation['production'], generation['host_verification']):
    assert sha(ROOT / sealed['path']) == sealed['sha256'], sealed['path']
production = load(ROOT / generation['production']['path'])
pack = load(ROOT / generation['generation_dir'] / 'pack.json')
leaves = []
for item in production['details']:
    shard = next(x for x in pack['new_shards'] if x['sha256'] == item['V9_sha256'])
    leaves.append(dict(resref=item['resref'], animation_ids=['0x3000'], registry=shard['registry'],
                       sha256=shard['sha256'].lower(), frames=shard['frame_count'], bytes=shard['registry_bytes']))
leaves.sort(key=lambda x: x['resref'])
assert len(leaves) == 12 and sum(x['frames'] for x in leaves) == 516
scope_digest = hashlib.sha256(json.dumps(leaves, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
ini_sha = next(x['sha256'] for x in baseline['unchanged_assets'] if x['relative_path'] == 'InfinityEngine-Enhancer.ini')
decision = dict(
    schema='bg2-upscale-native-sprite-family-qa-decision-v1', status='accepted', qa_state='passed',
    recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    scope=dict(kind='installed-complete-native-family-contour-trial', engine_family='monster_ankheg',
               animation_ids=['0x3000'], variant_id='q3m-v9-sdf-stable-x2-catmullrom', scale=2,
               resources=12, frames=516, resource_bindings=12, ordered_resource_sha256=scope_digest,
               resources_order='resref ascending'),
    visual_qa=dict(result='pass', authority='user', user_statement='validé, committe',
                   scenario='user acceptance of installed complete Ankheg SDF x2 and metadata-wait stability patch',
                   individual_scenario_details='not specified by user', test_commands_provided=['ANKHEG01']),
    runtime_contract=dict(runtime=generation['runtime'], dll=generation['dll'], ini_sha256=ini_sha,
                          catalogue_sha256=generation['catalog']['sha256'], owner=9, native_palette_kind=0,
                          class_profile_id=8, decode_rule_id=3, registry_version=9, palette='live-native',
                          world_filter='CatmullRom', native_geometry=True, SDF_recipe=generation['mask_recipe'],
                          metadata_wait=generation['metadata_wait'], shaders=load(ROOT / generation['runtime']['path'])['shaders']),
    provenance=dict(selected_generation=identity(HERE / 'current-generation.json'), production=generation['production'],
                    installed_receipt_at_decision=identity(receipt_path),
                    installation_snapshot=identity(HERE / 'installation-verification.json'),
                    native_verification=generation['host_verification']),
    resources=leaves, release_state='not-promoted')
save(QA, decision, mode='x')
reference = QA.relative_to(ROOT).as_posix()
tracking_path = ROOT / 'sprite/index/q3m-work-tracking.json'
tracking = load(tracking_path)
family = next(x for x in tracking['families'] if x['engine_section'] == 'monster_ankheg')
for trial in (family['current_contour_trial'], next(x for x in tracking['current_contour_trials'] if x['family'] == 'monster_ankheg')):
    assert trial['reference'] == identity(HERE / 'current-generation.json')['path']
    trial.update(state='SDF-trial-metadata-wait-installed-ingame-accepted', qa_ingame=True, qa_state='passed',
                 qa_reference=reference, qa_decision=reference, qa_decision_sha256=sha(QA))
accepted = [x for x in tracking['current_recipe_complete_productions'] if x.get('qa_ingame')]
accepted += [x for x in tracking['current_contour_trials'] if x.get('qa_ingame')]
tracking['queue_totals']['current_recipe_ingame_accepted_families'] = len({x['family'] for x in accepted})
tracking['queue_totals']['current_recipe_ingame_accepted_animation_ids'] = len({i for x in accepted for i in x['animation_ids']})
tracking['queue_totals']['ingame_acceptance_counting_rule'] = 'unique families/IDs across accepted full productions and current contour trials; QA belongs to exact variant/runtime'
tracking['colour_variants']['state'] = 'Q3m-x2-flying-accepted-Ankheg-V9-SDF-stable-accepted-Ogre-installed-other-families-pilot'
save(tracking_path, tracking)
csv_path = ROOT / 'sprite/index/q3m-work-items.csv'
lines = csv_path.read_text(encoding='utf-8').splitlines(keepends=True)
for i, line in enumerate(lines):
    if line.startswith('0x3000,'):
        assert 'v7-colours-with-v9-sdf-stable-runtime-installed-QA-pending' in line
        lines[i] = line.replace('current-recipe-complete-contour-trial-installed-QA-pending',
                                'current-recipe-complete-contour-trial-ingame-accepted').replace(
                                'v7-colours-with-v9-sdf-stable-runtime-installed-QA-pending',
                                'v7-colours-with-v9-sdf-stable-runtime-ingame-accepted')
with csv_path.open('w', encoding='utf-8', newline='\n') as stream:
    stream.write(''.join(lines))
print(json.dumps(dict(qa_reference=reference, accepted_resources=12, accepted_frames=516,
                      accepted_variant='q3m-v9-sdf-stable-x2-catmullrom')))
