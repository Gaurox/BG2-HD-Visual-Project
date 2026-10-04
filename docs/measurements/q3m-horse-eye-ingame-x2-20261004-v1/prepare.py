"""Install the reviewed v3 horse candidate without regenerating any sprite."""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import run_creature_sprite_x2 as reg
from palette_work_plan import file_sha, write_json
from workspace_paths import get_path

def load(p):
    return json.loads(p.read_text(encoding='utf-8-sig'))

def identity(p):
    return dict(path=p.relative_to(ROOT).as_posix(), sha256=file_sha(p), bytes=p.stat().st_size)

assert not (HERE / 'current-generation.json').exists()
base = ROOT / 'docs/measurements/q3m-horse-eye-x2-20261004-v1'
analysis = ROOT / 'docs/measurements/q3m-horse-eye-directions-20261004-v3'
old = load(base / 'current-generation.json')
production = load(analysis / 'candidate.json')
verified = load(analysis / 'verification.json')
assert verified['passed'] and verified['changed_x2_pixels'] == 134
assert verified['contrast_below_original'] == 0 and not production['SDF']
game = get_path('bg2ee_game_root', required=True)
catalog_relative = 'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game / catalog_relative).lower() == old['catalog']['sha256'].lower()
parent = reg.read_sealed_catalog_index(game / catalog_relative, old['catalog']['sha256'])
isolated = ROOT / production['pack_directory']
new = reg.read_sealed_catalog_index(isolated / 'CreatureSprites-XN.catalog', production['pack']['catalog_sha256'])
assert len(new['directory']) == 2 and {r['resref'] for r in new['directory']} == {'AHRSG1', 'AHRSG1E'}
out = ROOT / 'sprite/.work/q3m-horse-eye-ingame-x2-20261004-v1/combined'
assert not (out / 'pack.json').exists() and not any(out.rglob('*.registry'))
assets = out / 'iee-assets/creature-sprites'
assets.mkdir(parents=True, exist_ok=True)
components = [dict(c) for c in parent['components']]
shards = [dict(s) for s in parent['shards']]
animations = [dict(a) for a in parent['animations']]
directory = [dict(r) for r in parent['directory']]
new_shards, replaced, unchanged_horse = [], [], []
for route in new['directory']:
    target = next(r for r in directory if r['animation_id'] == '0xB100' and r['resref'] == route['resref'])
    ci, si = target['component_index'], target['shard_index']
    assert target['resource_ordinal'] == 0
    s = dict(new['shards'][route['shard_index']], index=si)
    c = dict(new['components'][route['component_index']], index=ci, shard_start=si)
    assert s['frame_count'] == parent['shards'][si]['frame_count']
    if s['sha256'] == parent['shards'][si]['sha256']:
        assert s == parent['shards'][si] and c == parent['components'][ci]
        unchanged_horse.append(route['resref'])
        continue
    shards[si], components[ci] = s, c
    new_shards.append(s)
    replaced.append(dict(resref=route['resref'], component_index=ci, shard_index=si,
                         old_sha256=parent['shards'][si]['sha256'], new_sha256=s['sha256']))
assert len(replaced) == 1 and replaced[0]['resref'] == 'AHRSG1' and unchanged_horse == ['AHRSG1E']
for s in shards:
    source = isolated / Path(s['registry']).name if s in new_shards else ROOT / old['generation_dir'] / s['registry']
    assert source.is_file() and source.stat().st_size == s['registry_bytes']
    os.link(source, assets / source.name)
combined = reg.write_registry_catalog_index(assets / 'CreatureSprites-XN.catalog', 2, animations,
    components, shards, directory, [c['digest'] for c in components],
    dict(shard_registry_versions=[6, 7, 9], logical_digest_schemes=dict(parent='inherited-V6-V7-V9', horse=production['recipe'])))
checked = reg.read_sealed_catalog_index(assets / 'CreatureSprites-XN.catalog', combined['sha256'])
assert checked['directory'] == parent['directory'] and checked['animations'] == parent['animations']
changed_si = {r['shard_index'] for r in replaced}
changed_ci = {r['component_index'] for r in replaced}
assert all(checked['shards'][i] == s for i, s in enumerate(parent['shards']) if i not in changed_si)
assert all(checked['components'][i] == c for i, c in enumerate(parent['components']) if i not in changed_ci)
oldbase = load(base / 'baseline.json')
receipt = load(base / 'ingame-installation/active-test.json')
assert receipt['status'] == 'installed-pending-ingame-qa'
preserved = {r['relative_path']: r for r in oldbase['preserved']}
for s in receipt['new_shards']:
    if s['sha256'] not in {r['old_sha256'] for r in replaced}:
        preserved[s['registry']] = dict(relative_path=s['registry'], sha256=s['sha256'])
for item in preserved.values():
    assert file_sha(game / item['relative_path']).lower() == item['sha256'].lower()
qa = ROOT / oldbase['accepted_QA']['path']
assert file_sha(qa) == oldbase['accepted_QA']['sha256']
proof = dict(inherited_animations_unchanged=len(animations), inherited_routes_unchanged=len(directory),
    replaced_resources=replaced, unchanged_horse_resources=unchanged_horse,
    new_resources=1, new_frames=22, verified_horse_resources=2, verified_horse_frames=44,
    active_animations=len(animations), active_resources=checked['total_resources'],
    active_frames=checked['total_frames'], active_routes=len(directory),
    unchanged_other_shards=len(shards)-1, unchanged_other_components=len(components)-1,
    accepted_ambient_static_resources_preserved=24, accepted_ambient_static_QA=identity(qa),
    changed_frames=5, changed_x2_pixels=134, SDF=False, ingame_QA=False, release=False)
assert proof['active_animations'] == 104 and proof['active_resources'] == 4618 and proof['active_routes'] == 50299
write_json(HERE / 'baseline.json', dict(game_root='config://bg2ee_game_root', catalog_relative=catalog_relative,
    parent_catalog_sha256=old['catalog']['sha256'], dll_sha256=oldbase['dll_sha256'], ini_sha256=oldbase['ini_sha256'],
    preserved=list(preserved.values()), source_names=oldbase['source_names'], accepted_QA=identity(qa)))
write_json(HERE / 'catalog-proof.json', proof)
write_json(out / 'pack.json', dict(catalog=combined, new_shards=new_shards, proof=proof))
write_json(HERE / 'current-generation.json', dict(schema='bg2-horse-eye-reviewed-candidate-Q3m-V7-v1',
    role='production-not-QA-installation-or-release', family='ambient_static', animation_ids=['0xB100'],
    resources=2, frames=44, scale=2, colour=old['colour'], registry_version=7, SDF=False,
    recipe=production['recipe'], generation_dir=out.relative_to(ROOT).as_posix(),
    catalog=identity(assets / 'CreatureSprites-XN.catalog'), production=identity(analysis / 'candidate.json'),
    analysis_verification=identity(analysis / 'verification.json'), runtime=old['runtime'], dll=old['dll'],
    ingame_QA=False, release=False))
write_json(HERE / 'creatures.json', dict(fixtures=[], representatives=[dict(resref='HORSE', animation_id='0xB100', clua='C:CreateCreature("HORSE")')]))
print(json.dumps(dict(catalog=combined['sha256'], replaced_resources=replaced,
                      preserved_files=len(preserved), inherited_routes=len(directory))))
