"""Exact 78-Character coverage against the existing source plan; no source rescan."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
REPORT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from palette_work_plan import WorkPlan, write_json
import run_creature_sprite_x2 as registry
from workspace_paths import get_path

PACK = ROOT / 'sprite/.work/q3m-playable-all-x2-pack-20261002-v1'
RUNTIME = ROOT / 'pipeline/runtime/manifests/iee-sprite-p7-full-ui-q3m-20261002-v1.json'


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest().upper()


def snapshot():
    target = REPORT / 'baseline.json'
    assert not target.exists()
    game = get_path('bg2ee_game_root', required=True)
    runtime = json.loads(RUNTIME.read_text())
    paths = ['InfinityEngine-Enhancer.dll', 'BaldurReal.exe']
    paths += [s['target'] for s in runtime['shaders']]
    paths += sorted(p.relative_to(game).as_posix() for p in (game / 'iee-assets/paperdolls').glob('*.registry'))
    preserved = [dict(relative_path=p, sha256=sha(game / p)) for p in paths]
    assert len(paths) == 86
    assert sha(game / paths[0]) == runtime['dll']['sha256'].upper()
    assert sha(game / paths[1]) == runtime['game_profile']['baldur_real_sha256'].upper()
    for item in runtime['shaders']:
        assert sha(game / item['target']) == item['sha256'].upper()
    catalog = game / 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
    before = registry.read_sealed_catalog_index(catalog, sha(catalog))
    assert before['scale'] == 2
    # A standalone replacement is valid here: the live catalog contains only
    # two Character ids, both included in the requested complete Character set.
    assert {a['animation_id'] for a in before['animations']} == {'0x6100', '0x6110'}
    assert sha(catalog) == runtime['baseline']['catalog']
    ini = game / 'InfinityEngine-Enhancer.ini'
    assert sha(ini) == runtime['ini']['sha256']
    write_json(target, dict(schema='bg2-playable-q3m-install-baseline-v1', game_root=str(game),
        runtime_manifest=RUNTIME.relative_to(ROOT).as_posix(), catalog_sha256=sha(catalog),
        ini_sha256=sha(ini), catalog_animation_ids=['0x6100', '0x6110'],
        preserved=preserved, paperdoll_resources=81))
    print('baseline: runtime + 81 paperdolls + 3 shaders preserved; old catalog has 2 Character ids')


def verify(installed):
    pack = json.loads((PACK / 'pack.json').read_text())
    plan = WorkPlan()
    assert pack['source_plan_sha256'] == plan.descriptor['sha256']
    assert pack['scale'] == 2 and pack['resources'] == 4510
    game = get_path('bg2ee_game_root', required=True)
    catalog_path = (game / 'iee-assets/creature-sprites' if installed else PACK) / 'CreatureSprites-XN.catalog'
    sealed = registry.read_sealed_catalog_index(catalog_path, pack['catalog']['sha256'])
    actual_ids = {a['animation_id'] for a in sealed['animations']}
    expected_ids = set(plan.models)
    assert actual_ids == expected_ids and len(actual_ids) == 78
    rows = {}
    for row in sealed['directory']:
        key = row['animation_id'], row['resref']
        assert key not in rows
        rows[key] = row
    expected_keys, coverage = set(), []
    for animation in sorted(expected_ids):
        expected = {r['resref'] for r in plan.resources([animation])}
        actual = {ref for aid, ref in rows if aid == animation}
        assert actual == expected, animation
        memberships = {row['component_index'] for row in rows.values() if row['animation_id'] == animation}
        a = next(a for a in sealed['animations'] if a['animation_id'] == animation)
        assert a['owner'] == 1 and set(a['component_indices']) == memberships
        expected_keys.update((animation, ref) for ref in expected)
        coverage.append(dict(animation_id=animation, resources=len(expected), missing=[]))
    assert set(rows) == expected_keys
    resources = plan.resources()
    assert sealed['total_frames'] == sum(r['frame_count'] for r in resources) == 1564054
    assert sealed['total_resources'] == len(resources) == len(sealed['shards']) == 4510
    resource_map = {r['resref']: r for r in resources}
    for (animation, ref), row in rows.items():
        s = sealed['shards'][row['shard_index']]
        c = sealed['components'][row['component_index']]
        assert s['resource_count'] == c['resource_count'] == 1
        assert s['frame_count'] == c['frame_count'] == resource_map[ref]['frame_count']
        assert c['shard_start'] == row['shard_index'] and c['shard_count'] == 1
        assert row['resource_ordinal'] == 0
        path = game / s['registry'] if installed else PACK / Path(s['registry']).name
        assert path.is_file() and path.stat().st_size == s['registry_bytes'], path
    result = dict(schema='bg2-playable-q3m-x2-coverage-verification-v1',
        status='installed-verified-not-visual-qa' if installed else 'native-pack-verified',
        catalog_sha256=pack['catalog']['sha256'], scale=2, animations=78, resources=4510,
        native_frames=1564054, missing_animation_ids=[], missing_resources=[],
        native_source_geometry_cycles_verified=pack['verification']['frame_geometry_source_cycles_identical'],
        per_animation=coverage, ingame_visual_qa=False)
    if installed:
        receipt = json.loads((REPORT / 'ingame-installation/active-test.json').read_text())
        assert receipt['status'] == 'installed-pending-qa'
        assert receipt['catalog_sha256'] == pack['catalog']['sha256']
        assert receipt['installed_shards_verified'] == 4510
        for item in json.loads((REPORT / 'baseline.json').read_text())['preserved']:
            assert sha(game / item['relative_path']) == item['sha256'], item['relative_path']
        result.update(installed_shards_sha256_verified=4510, preserved_paperdolls=81,
                      filter='Box', filter_animation='0x0')
    destination = REPORT / ('verification.json' if installed else 'native-coverage.json')
    if destination.exists():
        assert json.loads(destination.read_text()) == result, 'Existing final evidence differs; use a new run'
    else:
        write_json(destination, result)
    plan.close()
    print(json.dumps({k: v for k, v in result.items() if k != 'per_animation'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', action='store_true')
    parser.add_argument('--installed', action='store_true')
    args = parser.parse_args()
    snapshot() if args.snapshot else verify(args.installed)
