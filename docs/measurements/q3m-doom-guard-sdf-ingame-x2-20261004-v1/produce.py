"""V9 masks only; reuse sealed Q3m I/F, clone shared layers only for 6405/6406."""
import copy,hashlib,importlib.util,json,os,struct,sys
from pathlib import Path
from collections import OrderedDict
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves,run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from sprite_sdf_registry import planes
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
spec=importlib.util.spec_from_file_location('sdf_reference',ROOT/'docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py');reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
prior=ROOT/'docs/measurements/q3m-character-old-runtime-fix-x2-20261004-v1';previous=load(prior/'current-generation.json')
parent_root=ROOT/previous['generation_dir'];game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==previous['catalog']['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
WORK=ROOT/'sprite/.work'/HERE.name;isolated=WORK/'isolated';isolated.mkdir(parents=True)
assert not (HERE/'production.json').exists()
mask_dir=WORK/'mask-cache';mask_dir.mkdir();verify_dir=HERE/'work';verify_dir.mkdir()
parent=registry.read_sealed_catalog_index(parent_root/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',previous['catalog']['sha256'])
targets={r['resref']:r for r in parent['directory'] if r['animation_id']=='0x6405'}
shadows={r['resref']:r for r in parent['directory'] if r['animation_id']=='0x6400' and r['resref'].startswith('CSHD')}
assert len(targets)==941 and len(shadows)==33;targets.update(shadows)
assert len(targets)==974 and sum(r.startswith('MDGU') for r in targets)==22
records={};palettes={}
for run in [ROOT/'docs/measurements/q3m-character-old-full-x2-20261004-v1',prior]:
    raw=(ROOT/load(run/'production.json')['pack_directory']/'witnesses.oracle').read_bytes();pos=12
    for _ in range(struct.unpack_from('<I',raw,8)[0]):
        start=pos;aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',raw,pos);pos+=24
        ref=ref.rstrip(b'\0').decode();palette=np.frombuffer(raw,np.uint8,6144,pos).reshape(6,256,4).copy();pos+=6144+2052
        for __ in range(nc):n=struct.unpack_from('<I',raw,pos)[0];pos+=4+n*4
        pos+=nf*(16+6*32)
        if ref in targets:records[ref]=struct.pack('<I',0x6405)+raw[start+4:pos];palettes[ref]=palette
    assert pos==len(raw)
assert set(records)==set(targets)
mask_cache=OrderedDict();mask_keys=set();stats=dict(resources=0,frames=0,unique_masks=0,mask_cache_hits=0,empty_body_frames=0,new_neural_targets=0,new_Q3m_encodings=0)
details=[];infos={};sdf_records={};recipe_bytes=json.dumps(reference.RECIPE,sort_keys=True).encode()
for ordinal,(ref,route) in enumerate(sorted(targets.items())):
    shard=parent['shards'][route['shard_index']];source=parent_root/shard['registry'];assert file_sha(source).upper()==shard['sha256']
    parsed=leaves.inspect(source,include_frames=True);assert parsed['version']==7
    resource=parsed['resources'][0];assert resource['resref']==ref;profile=resource['profile'];golden=bytearray()
    for frame in resource['frames']:
        i=frame['I'];binary=np.minimum(i,3);key=hashlib.sha256(recipe_bytes+struct.pack('<II',*i.shape)+binary.tobytes()).hexdigest()
        if key in mask_cache:distance=mask_cache.pop(key);stats['mask_cache_hits']+=1
        elif key in mask_keys:
            with np.load(mask_dir/(key+'.npz')) as cached:distance=cached['SDF']
            stats['mask_cache_hits']+=1
        else:
            if np.any(i>=2):distance,_=reference.reconstruct(i)
            else:distance=np.full((i.shape[0]+12,i.shape[1]+12),-4,np.float32)
            np.savez_compressed(mask_dir/(key+'.npz'),SDF=distance);mask_keys.add(key)
        mask_cache[key]=distance
        if len(mask_cache)>64:mask_cache.popitem(last=False)
        frame['S'],frame['M']=planes(i,distance);frame['guide']=i.copy();frame['dep']=np.frombuffer(frame['dep'],np.uint8).copy()
        for k,palette in enumerate(palettes[ref]):
            rgba=profile.decode(i,frame['F'],palette);m=frame['M'];valid=m!=0xffffffff
            encoded=np.zeros((*m.shape,4),np.uint8);encoded[valid,:3]=rgba.reshape(-1,4)[m[valid],:3];encoded[...,3]=frame['S']
            encoded[6:-6,6:-6,3]|=(i==1).astype(np.uint8)*128
            assert np.all(rgba[i>=2,3]==255) and np.all(rgba[i==1,:3]==0) and np.all(rgba[i==1,3]==127)
            golden.extend(hashlib.sha256(encoded.tobytes()).digest())
            if k==0:composite_sha=hashlib.sha256(encoded[4:-4,4:-4].tobytes()).digest()
        golden.extend(composite_sha);stats['frames']+=1
        if ref.startswith('MDGU'):assert not np.any(i);stats['empty_body_frames']+=1
    path=isolated/(ref+'.registry');info=leaves.write(path,[resource],profile,version=9);sealed=isolated/registry.catalog_shard_filename(info['sha256']);path.replace(sealed)
    checked=leaves.inspect(sealed,include_frames=True)['resources'][0]
    assert checked['profile'].metadata()==profile.metadata() and checked['cycles']==resource['cycles'] and checked['source_sha256']==resource['source_sha256']
    for a,b in zip(resource['frames'],checked['frames']):
        assert a['geometry']==b['geometry'] and a['dep'].tobytes()==b['dep']
        assert all(np.array_equal(a[p],b[p]) for p in ('I','F','representatives','S','M'))
    infos[ref]=info;sdf_records[ref]=bytes(golden);details.append(dict(resref=ref,frames=info['frame_count'],profile=profile.id,V7_sha256=shard['sha256'],V9_sha256=info['sha256']))
    stats['resources']+=1
    if ordinal%25==0:print(json.dumps(dict(done=ordinal+1,total=len(targets),frames=stats['frames'],masks=len(mask_keys))),flush=True)
stats['unique_masks']=len(mask_keys);assert stats['empty_body_frames']==936
for start in range(0,len(targets),128):
    refs=sorted(targets)[start:start+128];n=start//128
    (verify_dir/f'physical-{n}.oracle').write_bytes(struct.pack('<8sI',b'IEEQP7\0\0',len(refs))+b''.join(records[r] for r in refs))
    (verify_dir/f'sdf-{n}.oracle').write_bytes(b'IEESDF1\0'+b''.join(sdf_records[r] for r in refs))

mixed=copy.deepcopy(parent);logical=load(parent_root/'pack.json')['catalog']['logical_component_digests'][:];replacement={};new_bindings={};new_shards=[]
for ref,route in sorted(targets.items()):
    info=infos[ref];entry=registry.catalog_shard_entry_bytes(info,isolated);digest=registry.catalog_component_digest(2,[entry])
    if ref.startswith('MDGU'):
        ci,si=route['component_index'],route['shard_index']
        assert {r['animation_id'] for r in parent['directory'] if r['component_index']==ci}=={'0x6405','0x6406'}
        logical[ci]=digest
    else:
        ci,si=len(mixed['components']),len(mixed['shards']);mixed['components'].append({});mixed['shards'].append({});logical.append(digest)
    mixed['components'][ci]=dict(index=ci,digest=digest,shard_start=si,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=info['registry_bytes'])
    mixed['shards'][si]=dict(index=si,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(info['sha256']),**info)
    new_bindings[ref]=dict(resref=ref,component_index=ci,shard_index=si,resource_ordinal=0);replacement[si]=isolated/registry.catalog_shard_filename(info['sha256']);new_shards.append(mixed['shards'][si])
for aid in ('0x6405','0x6406'):
    mixed['directory']=[r for r in mixed['directory'] if r['animation_id']!=aid]+[dict(animation_id=aid,**r) for r in new_bindings.values()]
    next(a for a in mixed['animations'] if a['animation_id']==aid)['component_indices']=sorted({r['component_index'] for r in new_bindings.values()})
out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
for si,shard in enumerate(mixed['shards']):
    source=replacement.get(si,parent_root/shard['registry']);os.link(source,assets/source.name)
catalog=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,mixed['animations'],mixed['components'],mixed['shards'],mixed['directory'],logical,dict(shard_registry_versions=[6,7,9],scope='SDF only 0x6405/0x6406'))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',catalog['sha256']);routes={(r['animation_id'],r['resref']):r for r in checked['directory']}
assert all(routes[(r['animation_id'],r['resref'])]==r for r in parent['directory'] if r['animation_id'] not in ('0x6405','0x6406'))
assert all(a in checked['animations'] for a in parent['animations'] if a['animation_id'] not in ('0x6405','0x6406'))
assert len(checked['animations'])==147 and checked['total_resources']==6688 and len(checked['directory'])==55318
proof=dict(unaffected_animations=145,unaffected_routes=sum(r['animation_id'] not in ('0x6405','0x6406') for r in parent['directory']),body_replaced_resources=22,cloned_shared_resources=952,added_shadow_routes=66,active_resources=checked['total_resources'],active_frames=checked['total_frames'],active_routes=len(checked['directory']))
write_json(out/'pack.json',dict(catalog=catalog,new_shards=new_shards,proof=proof))
preserved={r['relative_path']:r for r in load(prior/'baseline.json')['preserved'] if r['relative_path']!='InfinityEngine-Enhancer.dll'}
for s in load(prior/'ingame-installation/active-test.json')['new_shards']:preserved[s['registry']]=dict(relative_path=s['registry'],sha256=s['sha256'])
for p in ('InfinityEngine-Enhancer.ini','BaldurReal.exe','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl'):preserved[p]=dict(relative_path=p,sha256=file_sha(game/p))
for r in preserved.values():assert file_sha(game/r['relative_path']).upper()==r['sha256'].upper()
write_json(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',catalog_relative='iee-assets/creature-sprites/CreatureSprites-XN.catalog',parent_catalog_sha256=previous['catalog']['sha256'],dll_sha256=previous['dll']['sha256'],preserved=list(preserved.values()),source_names=load(prior/'baseline.json')['source_names']))
write_json(HERE/'production.json',dict(stats=stats,recipe=reference.RECIPE,details=details,proof=proof,Q3m_colour_planes_byte_identical=True,native_geometry_cycles_metadata_identical=True,transparent_native_body=True,ingame_QA=False,release=False))
write_json(HERE/'current-generation.json',dict(schema='bg2-doom-guard-Q3m-V9-SDF-current-v1',role='production-not-QA-installation-or-release',family='character_old',animation_ids=['0x6405','0x6406'],scale=2,SDF=True,registry_version=9,colour='acquired-K6-four-partners-eight-levels',resources=974,frames=stats['frames'],generation_dir=out.relative_to(ROOT).as_posix(),catalog=identity(assets/'CreatureSprites-XN.catalog'),parent_generation=identity(prior/'current-generation.json'),production=identity(HERE/'production.json'),ingame_QA=False,release=False))
print(json.dumps(dict(stats=stats,proof=proof,catalog=catalog['sha256'])),flush=True)
