"""Replace only 7314 routes; preserve all 330 other IDs and installed source bytes."""
import copy,json,os,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
PARENT=HERE.parent/'q3m-mfie-palette-stability-x2-20261007-v2'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
def signatures(cat,ids):return sorted((r['animation_id'],r['resref'],r['resource_ordinal'],cat['shards'][r['shard_index']]['sha256'],cat['components'][r['component_index']]['digest']) for r in cat['directory'] if r['animation_id'] in ids)
assert not(HERE/'current-generation.json').exists()
game=get_path('bg2ee_game_root',required=True);old=load(PARENT/'current-generation.json');runtime=load(HERE/'runtime.json');prod=load(HERE/'production.json')
assert file_sha(game/'InfinityEngine-Enhancer.dll')==old['dll']['sha256']
relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog';parent=registry.read_sealed_catalog_index(game/relative,old['catalog']['sha256'])
isolated=ROOT/prod['pack_directory'];new=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
assert len(new['animations'])==1 and new['animations'][0]['animation_id']=='0x7314' and len(new['directory'])==14
kept={a['animation_id'] for a in parent['animations']}-{'0x7314'};assert len(kept)==330
canonical=ROOT/old['generation_dir'];oldlogical=load(canonical/'pack.json')['catalog']['logical_component_digests']
out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
components=[];shards=[];logical=[];seen={};shahits=set();oldmap={};newmap={};oldsmap={};newsmap={}
def add(cat,index,source,digest,cmap,smap):
    c=cat['components'][index];ss=cat['shards'][c['shard_start']:c['shard_start']+c['shard_count']]
    if c['digest'] in seen:
        mapped=seen[c['digest']];existing=components[mapped]
        assert [s['sha256'] for s in ss]==[s['sha256'] for s in shards[existing['shard_start']:existing['shard_start']+existing['shard_count']]]
        cmap[index]=mapped
        for n,s in enumerate(ss):smap[s['index']]=existing['shard_start']+n
        return
    mapped=len(components);start=len(shards);seen[c['digest']]=mapped;cmap[index]=mapped
    for s in ss:
        assert s['sha256'] not in shahits;shahits.add(s['sha256']);p=source/Path(s['registry']).name
        if cat is new:assert file_sha(p).upper()==s['sha256']
        else:assert p.stat().st_size==(game/s['registry']).stat().st_size==s['registry_bytes']
        os.link(p,assets/p.name);smap[s['index']]=len(shards);shards.append(dict(s,index=len(shards)))
    components.append(dict(c,index=mapped,shard_start=start));logical.append(digest)
for i in sorted({i for a in parent['animations'] if a['animation_id'] in kept for i in a['component_indices']}):add(parent,i,canonical/'iee-assets/creature-sprites',oldlogical[i],oldmap,oldsmap)
for c in new['components']:add(new,c['index'],isolated,c['digest'],newmap,newsmap)
animations=[dict(a,component_indices=[oldmap[i] for i in a['component_indices']]) for a in parent['animations'] if a['animation_id'] in kept]
animations.extend(dict(a,component_indices=[newmap[i] for i in a['component_indices']]) for a in new['animations'])
directory=[dict(r,component_index=oldmap[r['component_index']],shard_index=oldsmap[r['shard_index']]) for r in parent['directory'] if r['animation_id'] in kept]
directory.extend(dict(r,component_index=newmap[r['component_index']],shard_index=newsmap[r['shard_index']]) for r in new['directory'])
catalog=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,logical,dict(shard_registry_versions=[6,7,9],delta='MFIE-native-G1-G2-palettes'))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',catalog['sha256'])
assert signatures(checked,kept)==signatures(parent,kept) and signatures(checked,{'0x7314'})==signatures(new,{'0x7314'})
prior={r[1]:r for r in signatures(parent,{'0x7314'})};current={r[1]:r for r in signatures(checked,{'0x7314'})}
changed=[ref for ref in current if current[ref]!=prior[ref]];assert changed==['MFIEG1','MFIEG11','MFIEG12','MFIEG13','MFIEG14','MFIEG15']
leaves=[checked['shards'][i] for i in sorted({r['shard_index'] for r in checked['directory'] if r['animation_id']=='0x7314'})]
proof=dict(passed=True,retained_ids=330,retained_routes=len(signatures(parent,kept)),retained_routes_and_component_digests_exact=True,
    corrected_ids=['0x7314'],corrected_bindings=14,changed_bindings=changed,unchanged_bindings=sorted(set(current)-set(changed)),
    active_ids=len(checked['animations']),active_leaves=checked['total_resources'],active_frames=checked['total_frames'],old_files_not_deleted=True,
    QA_accepted_ids_unchanged=76,ingame_QA=False,release=False)
write_json(HERE/'catalog-proof.json',proof);write_json(out/'pack.json',dict(catalog=catalog,MFIE_shards=leaves,proof=proof))
baseline=load(PARENT/'baseline.json');baseline['preserved']=[r for r in baseline['preserved'] if r['relative_path']!=relative]
baseline.update(parent_generation=identity(PARENT/'current-generation.json'),parent_dll_sha256=old['dll']['sha256'],parent_catalog_sha256=old['catalog']['sha256'],catalog_relative=relative,
    changed_files=['InfinityEngine-Enhancer.dll',relative],candidate_shards=leaves)
write_json(HERE/'baseline.json',baseline)
gen=copy.deepcopy(old);gen.update(schema='bg2-monster-native-MFIE-palette-successor-v3',role='installation-candidate-not-QA-or-release',
    generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),dll=runtime['dll'],runtime=identity(HERE/'runtime.json'),
    parent_generation=identity(PARENT/'current-generation.json'),correction_animation_ids=['0x7314'],correction_production=identity(HERE/'production.json'),
    correction_selection=identity(HERE/'selection.json'),native_palette_analysis=identity(HERE/'analysis.json'),runtime_changed=True,ingame_QA=False,release=False)
gen.pop('runtime_verification',None);write_json(HERE/'current-generation.json',gen)
production=load(HERE.parent/'q3m-monster-full-x2-20261006-v2/current-generation.json')
production.update(generation_dir=out.relative_to(ROOT).as_posix(),catalog=gen['catalog'],parent_production=gen['production_generation'],
    correction_animation_ids=['0x7314'],correction_production=gen['correction_production'],correction_selection=gen['correction_selection'],
    runtime=gen['runtime'],dll=gen['dll'],role='complete-production-with-native-MFIE-palette-delta-not-QA-or-installation',installation=False,ingame_QA=False,release=False)
write_json(HERE/'production-generation.json',production)
print(json.dumps(dict(prepared=True,changed_bindings=changed,retained_ids=330,leaves=14)),flush=True)
