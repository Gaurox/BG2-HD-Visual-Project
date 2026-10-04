"""Append only Large16 V7 leaves; preserve the installed stable Ankheg runtime."""
import configparser,json,os,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
def keyed(rows,fields):
    result={tuple(r[f] for f in fields):r for r in rows};assert len(result)==len(rows);return result

game=get_path('bg2ee_game_root',required=True)
previous_dir=ROOT/'docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1'
previous=load(previous_dir/'current-generation.json');canonical=ROOT/previous['generation_dir']
production=load(HERE/'production.json');isolated=ROOT/production['pack_directory']
work=isolated.parent;out=work/'combined';assets=out/'iee-assets/creature-sprites'
assert not out.exists() and not (HERE/'baseline.json').exists(),'new run required'
native=next(json.loads(x) for x in reversed((HERE/'native-isolated.log').read_text().splitlines()) if x.startswith('{'))
assert native['passed'] and native['resources']==20 and native['frames']==1692
catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert file_sha(game/catalog_relative)==previous['catalog']['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
parent=registry.read_sealed_catalog_index(game/catalog_relative,previous['catalog']['sha256'])
assert len(parent['animations'])==88 and parent['total_resources']==4572 and len(parent['directory'])==50253
assert not any(a['animation_id'] in ('0xA000','0xA100','0xA200') for a in parent['animations'])
selection=load(HERE/'selection.json');refs={r for w in selection['witnesses'] for r in w['refs']}
for name in {*(aid[2:]+'.INI' for aid in ('0xA000','0xA100','0xA200')),*(''+r+'.BAM' for r in refs),'MWYV_WS.BMP','QMWYVW01.CRE'}:
    assert not any(p.name.upper()==name for p in (game/'override').iterdir()),'source/test override collision: '+name
ini=configparser.ConfigParser(interpolation=None,strict=False);ini.read(game/'InfinityEngine-Enhancer.ini')
expected=dict(EnableCreatureSpriteUpscaleTest='true',EnableCreatureSpriteX2Test='false',EnableCreatureSpriteLinearFiltering='false',CreatureSpriteFilter='CatmullRom',CreatureSpriteFilterAnimation='0x0')
assert all(ini.get('Shaders',k)==v for k,v in expected.items())
restored=load(ROOT/'docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/restoration-verification.json')
preserved=[r for r in restored['restored_files']+restored['preserved_files'] if r['relative_path']!=catalog_relative]
for r in preserved:assert file_sha(game/r['relative_path']).lower()==r['sha256'].lower(),r['relative_path']
qa_refs=[ROOT/'sprite/index/qa-decisions/flying/2026-10-03-accepted-full-flying-q3m-v7-k6-x2-box-v1.json',
         ROOT/'sprite/index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json']
assert load(ROOT/'docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/ingame-installation/active-test.json')['status']=='restored-parent'
assets.mkdir(parents=True)
for s in parent['shards']:
    source=canonical/s['registry'];assert source.is_file() and source.stat().st_size==s['registry_bytes']
    os.link(source,assets/source.name)
new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
ci,si=len(parent['components']),len(parent['shards'])
components=[dict(c) for c in parent['components']];shards=[dict(s) for s in parent['shards']]
animations=[dict(a) for a in parent['animations']];directory=[dict(r) for r in parent['directory']]
for s in new['shards']:
    source=isolated/Path(s['registry']).name;assert file_sha(source).upper()==s['sha256']
    with source.open('rb') as stream:assert struct.unpack_from('<I',stream.read(12),8)[0]==7
    os.link(source,assets/source.name);shards.append(dict(s,index=si+s['index']))
components.extend(dict(c,index=ci+c['index'],shard_start=si+c['shard_start']) for c in new['components'])
animations.extend(dict(a,component_indices=[ci+i for i in a['component_indices']]) for a in new['animations'])
directory.extend(dict(r,component_index=ci+r['component_index'],shard_index=si+r['shard_index']) for r in new['directory'])
logical=load(canonical/'pack.json')['catalog']['logical_component_digests']+[c['digest'] for c in new['components']]
combined=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,
    dict(shard_registry_versions=[6,7,9],logical_digest_schemes=dict(parent='inherited-V6-V7-V9',delta='V7-complete-native-Large16-colour-contracts')))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',combined['sha256'])
old_a=keyed(parent['animations'],('animation_id',));new_a=keyed(checked['animations'],('animation_id',))
old_r=keyed(parent['directory'],('animation_id','resref'));new_r=keyed(checked['directory'],('animation_id','resref'))
assert checked['components'][:ci]==parent['components'] and checked['shards'][:si]==parent['shards']
assert all(new_a[k]==v for k,v in old_a.items()) and all(new_r[k]==v for k,v in old_r.items())
assert checked['total_resources']==4592 and checked['total_frames']==1587864 and len(checked['animations'])==91 and len(checked['directory'])==50273
proof=dict(schema='bg2-Large16-catalog-preservation-v1',parent_catalog_sha256=previous['catalog']['sha256'],
    inherited_animations_unchanged=88,inherited_routes_unchanged=50253,inherited_components_unchanged=ci,
    new_animation_ids=['0xA000','0xA100','0xA200'],new_owner=11,new_resources=20,new_frames=1692,
    original_world_BAMs=12,auxiliary_inventory_BAMs=1,native_white_palette='MWYV_WS',
    active_animations=91,active_resources=4592,active_frames=1587864,active_routes=50273,
    inherited_Ankheg_SDF_and_wait_unchanged=True,Character_SDF_not_enabled=True,
    native_geometry_cycles_preserved=True,Large16_SDF=False,old_leaf_pixels_recomputed=False)
baseline=dict(schema='bg2-Large16-install-baseline-v1',game_root='config://bg2ee_game_root',catalog_relative=catalog_relative,
    parent_catalog_sha256=previous['catalog']['sha256'],dll_sha256=previous['dll']['sha256'],
    ini_sha256=file_sha(game/'InfinityEngine-Enhancer.ini'),preserved=preserved,world_configuration=expected,
    inherited_QA=[identity(p) for p in qa_refs],native_palette=selection['witnesses'][-1]['palette_override'],
    test_CRE_parent='absent',source_BAMs=sorted(refs))
write_json(HERE/'baseline.json',baseline);write_json(HERE/'catalog-proof.json',proof)
write_json(out/'pack.json',dict(schema='bg2-Large16-mixed-V6-V7-V9-pack-v1',catalog=combined,new_shards=shards[si:],proof=proof))
write_json(HERE/'current-generation.json',dict(schema='bg2-Large16-Q3m-V7-current-v1',role='production-not-QA-installation-or-release',
    family='monster_large16',animation_ids=['0xA000','0xA100','0xA200'],source_absent_animation_ids=['0xA201','0xA202'],
    resources=20,frames=1692,original_resources=13,original_frames=1114,scale=2,colour='K6-four-partners-eight-levels',registry_version=7,SDF=False,
    generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),
    production=identity(HERE/'production.json'),runtime=previous['runtime'],dll=previous['dll'],state='produced-host-verified-ready-to-install',ingame_QA=False,release=False))
print(json.dumps(proof))
