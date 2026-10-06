"""Pin partial user QA to the previous runtime; prepare a DLL-only successor."""
import csv,datetime,json,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
INSTALL=HERE.parent/'q3m-monster-ingame-x2-20261007-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
assert not(HERE/'current-generation.json').exists()
qa_path=ROOT/'sprite/index/qa-decisions/monsters/2026-10-07-accepted-partial-monster-73-q3m-v7-x2-nearest-v1.json'
assert not qa_path.exists()
gen=load(INSTALL/'current-generation.json');runtime=load(HERE/'runtime.json');verification=load(HERE/'runtime-verification.json')
assert verification['passed'] and verification['monster']['resources']==1040
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
cat=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',gen['catalog']['sha256'])
excluded=['0x7314','0x7F0B','0x7F2C','0x7F36'];accepted=[a for a in gen['animation_ids'] if a not in excluded];assert len(accepted)==73
allroutes=[r for r in cat['directory'] if r['animation_id'] in gen['animation_ids']]
allshards=[cat['shards'][i] for i in sorted({r['shard_index'] for r in allroutes})];assert len(allshards)==1037
for s in allshards:assert file_sha(game/s['registry']).upper()==s['sha256']
fixtures=load(INSTALL/'creatures.json')['fixtures']
for f in fixtures:assert file_sha(game/f['target'])==f['sha256']
preserved=load(INSTALL/'baseline.json')['preserved']
for r in preserved:assert file_sha(game/r['relative_path'])==r['sha256']
# No used base/partner index may reference native Realize's unwritten tail.
frames=0;short_resources=0
for r in allroutes:
    if r['animation_id']!='0x7314' or r['resref'].endswith('INV'):continue
    s=cat['shards'][r['shard_index']];info=leaves.inspect(game/s['registry'],include_frames=True)
    res=info['resources'][r['resource_ordinal']];assert res['resref']==r['resref']
    for f in res['frames']:
        used=np.unpackbits(np.frombuffer(f['dep'],np.uint8),bitorder='little')
        assert not np.any(used[252:]),(r['resref'],frames)
        frames+=1
    short_resources+=1
assert short_resources==13
write_json(HERE/'short-palette-dependencies.json',dict(passed=True,world_resources=short_resources,world_frames=frames,
    no_used_base_or_partner_index_at_or_above_252=True,native_realize_tail_not_consumed=True,assets_modified=False))
routes=sorted((r for r in allroutes if r['animation_id'] in accepted),key=lambda r:(r['animation_id'],r['resref']))
shards=[cat['shards'][i] for i in sorted({r['shard_index'] for r in routes})]
inventory=HERE/'accepted-asset-scope.csv'
with inventory.open('x',encoding='utf-8',newline='') as out:
    writer=csv.writer(out,lineterminator='\n');writer.writerow(['animation_id','resref','registry','sha256','frame_count','resource_ordinal'])
    for r in routes:
        s=cat['shards'][r['shard_index']];writer.writerow([r['animation_id'],r['resref'],s['registry'],s['sha256'],s['frame_count'],r['resource_ordinal']])
rows=list(csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig',newline='')))
models=len({r['body_resref'] for r in rows if r['animation_id'] in accepted});assert models==60
qa=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='accepted',qa_state='passed',
    recorded_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),recorded_on='2026-10-07',timezone='Europe/Paris',
    scope=dict(kind='installed-native-family-partial',engine_family='monster',animation_ids=accepted,models=models,colour_variants=73,
        excluded_animation_ids=excluded,scale=2,SDF=False,resources=len(shards),resource_bindings=len(routes),frames=sum(s['frame_count'] for s in shards)),
    visual_qa=dict(result='pass',authority='user',user_statement='tout le reste est validé',
        context='7314 vanilla; 7F0B/7F2C/7F36 possible vanilla click frames excluded',accepted_as_installed=True,full_lot_explicitly_confirmed=False),
    runtime_contract=dict(runtime=gen['runtime'],dll=gen['dll'],catalogue_sha256=gen['catalog']['sha256'],owner=3,
        world_filter='Nearest',colour='Q3m K6 four partners/eight levels x2',SDF=False,
        successor_runtime_QA_inferred=False,installed_runtime_files=preserved),
    asset_scope=dict(inventory=identity(inventory),physical_leaf_count=len(shards),binding_count=len(routes),catalogue=gen['catalog'],physical_leaf_hashes_verified=len(shards)),
    provenance=dict(installed_generation=identity(INSTALL/'current-generation.json'),installation_snapshot=identity(INSTALL/'installation-verification.json'),
        installation_receipt=identity(INSTALL/'ingame-installation/active-test.json'),analysis=identity(HERE/'analysis.json')),release=False)
qa_path.parent.mkdir(parents=True,exist_ok=True);write_json(qa_path,qa)
write_json(HERE/'partial-QA.json',dict(qa_reference=qa_path.relative_to(ROOT).as_posix(),accepted_ids=accepted,accepted_models=models,
    excluded_ids=excluded,accepted_dll_sha256=gen['dll']['sha256'],corrected_runtime_not_ingame_tested=True))
preserved=[r for r in preserved if r['relative_path']!='InfinityEngine-Enhancer.dll']
preserved.append(dict(relative_path='iee-assets/creature-sprites/CreatureSprites-XN.catalog',sha256=gen['catalog']['sha256']))
preserved.extend(dict(relative_path=s['registry'],sha256=s['sha256']) for s in allshards)
preserved.extend(dict(relative_path=f['target'],sha256=f['sha256']) for f in fixtures)
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',parent_generation=identity(INSTALL/'current-generation.json'),
    parent_dll_sha256=gen['dll']['sha256'],preserved=preserved,changed_files=['InfinityEngine-Enhancer.dll']))
gen.update(schema='bg2-monster-runtime-successor-candidate-v1',role='installation-candidate-not-QA-or-release',dll=runtime['dll'],
    runtime=identity(HERE/'runtime.json'),parent_generation=identity(INSTALL/'current-generation.json'),
    runtime_verification=identity(HERE/'runtime-verification.json'),partial_visual_QA=identity(qa_path),runtime_changed=True,ingame_QA=False,release=False)
write_json(HERE/'current-generation.json',gen)
print(json.dumps(dict(prepared=True,accepted_ids=73,accepted_models=models,changed_files=1,short_palette_dependencies_passed=True)),flush=True)
