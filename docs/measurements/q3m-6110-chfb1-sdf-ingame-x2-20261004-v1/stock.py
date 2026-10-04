"""Seal the user's stock decision after restore.ps1; read game files only."""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path


def load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def identity(path):
    return dict(path=path.relative_to(ROOT).as_posix(),
                sha256=sha(path), bytes=path.stat().st_size)


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                    encoding='utf-8', newline='\n')


def check(path, expected):
    assert sha(path) == expected.lower(), path


restoration_path = HERE / 'restoration-verification.json'
decision_path = HERE / 'stock-decision.json'
assert not restoration_path.exists() and not decision_path.exists(), 'Sealed decision exists.'
receipt_path = HERE / 'ingame-installation/active-test.json'
receipt = load(receipt_path)
assert receipt['status'] == 'restored-parent'
game = get_path('bg2ee_game_root', required=True)
for item in receipt['parent_files'] + receipt['preserved_files']:
    check(game / item['relative_path'], item['sha256'])
assert len(receipt['parent_files']) == 5 and len(receipt['preserved_files']) == 95

generation = load(HERE / 'current-generation.json')
runtime = load(HERE / 'runtime.json')
production = load(HERE / 'production.json')
stock_files = [generation[key] for key in ('production', 'runtime', 'dll', 'catalog', 'verification')]
stock_files += runtime['shaders']
for item in stock_files:
    check(ROOT / item['path'], item['sha256'])
work = ROOT / production['work_dir']
assert len(production['new_shards']) == 23
stock_leaves = []
for leaf in production['new_shards']:
    path = work / 'isolated' / Path(leaf['registry']).name
    check(path, leaf['sha256'])
    stock_leaves.append(identity(path))

tracking_path = ROOT / 'sprite/index/q3m-work-tracking.json'
tracking = load(tracking_path)
trial = next(x for x in tracking['current_contour_trials']
             if x.get('body') == 'CHFB1' and x.get('animation_ids') == ['0x6110'])
assert not trial['qa_ingame']
parent = 'docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1'
parent_generation = load(ROOT / parent / 'current-generation.json')
check(game / 'InfinityEngine-Enhancer.dll', parent_generation['dll']['sha256'])
check(game / 'iee-assets/creature-sprites/CreatureSprites-XN.catalog',
      parent_generation['catalog']['sha256'])
recorded_at = datetime.now(timezone.utc).isoformat()
restoration = dict(
    schema='bg2-character-SDF-restoration-verification-v1',
    role='restoration-not-new-ingame-QA-or-release',
    verified_at_utc=recorded_at, status='restored-parent',
    game_root='config://bg2ee_game_root',
    removed_active_scope='0x6110 CHFB1 V10 contour trial',
    restored_generation=identity(ROOT / parent / 'current-generation.json'),
    restored_files=receipt['parent_files'],
    preserved_files_sha256_verified=len(receipt['preserved_files']),
    preserved_files=receipt['preserved_files'],
    restored_active_receipt=identity(receipt_path),
    Character_contour_active=False, Ankheg_SDF_restored=True,
    catalog_byte_identical_to_parent=True, INI_byte_identical=True,
    unused_V10_game_leaves='retained-unreferenced; active catalog restored',
    new_ingame_QA=False, release=False)
write(restoration_path, restoration)
decision = dict(
    schema='bg2-character-SDF-stock-decision-v1', recorded_at_utc=recorded_at,
    authority='explicit-user-request',
    user_request="on garde cette solution en stock mais on ne l'installe pas",
    state='stocked-not-installed', animation_ids=['0x6110'], body='CHFB1',
    resources=23, frames=10323, registry_version=10,
    QA='pending-no-visual-acceptance-or-rejection', currently_installed=False,
    release=False, generation=identity(HERE / 'current-generation.json'),
    previous_installation=identity(HERE / 'installation-verification.json'),
    restoration=identity(restoration_path), reserved_files=stock_files,
    reserved_leaves=stock_leaves,
    source_and_recipe='committed; generated DLL/leaves retained locally outside Git',
    reuse='explicit future request; verify identities; new installation run/receipt')
write(decision_path, decision)

stock = copy.deepcopy(trial)
stock.update(state='Character-CHFB1-SDF-stocked-not-installed-ingame-QA-pending',
             currently_installed=False,
             decision_reference=decision_path.relative_to(ROOT).as_posix(),
             restoration_reference=restoration_path.relative_to(ROOT).as_posix())
stock['previous_installation_snapshot'] = stock.pop('installation_snapshot')
stock['installation_snapshot'] = restoration_path.relative_to(ROOT).as_posix()
tracking['current_contour_trials'].remove(trial)
tracking.setdefault('stocked_contour_solutions', []).append(stock)
family = next(x for x in tracking['families'] if x['engine_section'] == 'character')
family['current_contour_trials'] = [x for x in family.get('current_contour_trials', [])
                                   if x.get('body') != 'CHFB1']
family.setdefault('stocked_contour_solutions', []).append(copy.deepcopy(stock))
tracking['engine_integration']['installed_candidate_reference'] = parent + '/installation-verification.json'
tracking['engine_integration']['latest_installation_verification_reference'] = restoration_path.relative_to(ROOT).as_posix()
tracking['method'].update(world_filter='CatmullRom', initial_world_filter='Box',
                          world_filter_reference=restoration_path.relative_to(ROOT).as_posix())
write(tracking_path, tracking)

csv_path = ROOT / 'sprite/index/q3m-work-items.csv'
lines = csv_path.read_text(encoding='utf-8').splitlines(keepends=True)
header = lines[0].strip().split(',')
colour_column = header.index('colour_variant_state')
for ordinal, line in enumerate(lines):
    if line.startswith('0x6110,'):
        cells = line.rstrip('\n').split(',')
        assert len(cells) == len(header)
        cells[colour_column] = 'v6-colours-active-v10-SDF-CHFB1-stocked-not-installed-QA-pending'
        lines[ordinal] = ','.join(cells) + '\n'
csv_path.write_text(''.join(lines), encoding='utf-8', newline='\n')
print(json.dumps(dict(restored_files=5, preserved_files=95, reserved_V10_leaves=23,
                      Character_SDF='stocked-not-installed', Ankheg_SDF='restored-stable')))
