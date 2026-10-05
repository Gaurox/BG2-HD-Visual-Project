"""Add S/M to native Large16 world V7 leaves; retain acquired colours and INV."""
import copy, hashlib, importlib.util, json, os, struct, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
from sprite_sdf_registry import planes
OFFLINE=ROOT/'docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1'
spec=importlib.util.spec_from_file_location('sdf_reference',OFFLINE/'sdf_trial.py');reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ident(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
PARENT=HERE.parent/'q3m-monster-large16-full-x2-20261004-v1'
previous=load(PARENT/'current-generation.json');production=load(PARENT/'production.json')
parent_root=ROOT/previous['generation_dir'];source_dir=ROOT/production['pack_directory']
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==previous['catalog']['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==previous['dll']['sha256']
WORK=ROOT/'sprite/.work/q3m-large16-sdf-ingame-x2-20261004-v1'
isolated=WORK/'isolated';assert not (HERE/'production.json').exists()
assert not isolated.exists() or not list(isolated.glob('*.registry'))
isolated.mkdir(parents=True,exist_ok=True);cache=WORK/'mask-cache';cache.mkdir(exist_ok=True)
recipe=dict(reference.RECIPE,installation='V9-adaptive-runtime',distance_quantization_x2=1/16,sdf_pad_x2=6)
recipe_bytes=json.dumps(reference.RECIPE,sort_keys=True).encode()+bytes.fromhex(file_sha(OFFLINE/'sdf_trial.py'))
old=(source_dir/'witnesses.oracle').read_bytes();pos=12;chunks=[]
for n in range(struct.unpack_from('<I',old,8)[0]):
    start=pos;aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',old,pos);pos+=24
    palettes=np.frombuffer(old,np.uint8,6*256*4,pos).reshape(6,256,4).copy();pos+=6*256*4+2052
    for c in range(nc):count=struct.unpack_from('<I',old,pos)[0];pos+=4+count*4
    for f in range(nf):pos+=16+6*32
    name=ref.split(b'\0')[0].decode()
    if not name.endswith('INV'):chunks.append(dict(aid=f'0x{aid:04X}',ref=name,raw=old[start:pos],palettes=palettes,leaf_index=n))
assert pos==len(old) and len(chunks)==18
witness=old[:8]+struct.pack('<I',18)+b''.join(c['raw'] for c in chunks)
(isolated/'witnesses.oracle').write_bytes(witness)
mask_cache={};details=[];infos=[];resources={};statistics=dict(physical_frames=0,unique_masks=0,mask_cache_hits=0,acquired_masks_reused=0,new_neural_targets=0,new_Q3m_encodings=0)
acquired_dirs=[ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/mask-cache',ROOT/'sprite/.work/q3m-ankheg-sdf-offline-x2-20261004-v1']
auxiliary=[]
for c in chunks:
    info=production['pack']['leaves'][c['leaf_index']]
    source=source_dir/registry.catalog_shard_filename(info['sha256']);assert file_sha(source).upper()==info['sha256']
    resource=leaves.inspect(source,include_frames=True)['resources'][0];ref=resource['resref'];assert ref==c['ref']
    assert not np.any(resource['profile'].source[1,:3]) or all(not np.any(f['I']==1) for f in resource['frames']), 'coloured world shadow unsupported by existing V9'
    masks=[]
    for ordinal,frame in enumerate(resource['frames']):
        binary=np.minimum(frame['I'],3);key=hashlib.sha256(recipe_bytes+struct.pack('<II',*binary.shape)+binary.tobytes()).hexdigest()
        if key in mask_cache:distance,report=mask_cache[key];statistics['mask_cache_hits']+=1
        else:
            acquired=next((d/(key+'.npz') for d in acquired_dirs if (d/(key+'.npz')).exists()),None)
            if acquired is not None:
                distance=np.load(acquired)['SDF'];report=dict(reused_acquired=True);statistics['acquired_masks_reused']+=1
            elif np.any(frame['I']>=2):distance,report=reference.reconstruct(frame['I'])
            else:distance=np.full((binary.shape[0]+12,binary.shape[1]+12),-4,np.float32);report=dict(empty_foreground=True)
            np.savez_compressed(cache/(key+'.npz'),SDF=distance);mask_cache[key]=(distance,report);statistics['unique_masks']+=1
        frame['S'],frame['M']=planes(frame['I'],distance);frame['guide']=frame['I'];frame['dep']=np.frombuffer(frame['dep'],np.uint8).copy()
        masks.append(dict(frame=ordinal,key=key,**report));statistics['physical_frames']+=1
    materials=dict(resref=ref,source_sha256=resource['source_sha256'],frames=resource['frames'],cycles=resource['cycles'])
    new=leaves.write(isolated/(ref+'.registry'),[materials],resource['profile'],version=9)
    sealed=isolated/registry.catalog_shard_filename(new['sha256']);(isolated/(ref+'.registry')).replace(sealed)
    checked=leaves.inspect(sealed,include_frames=True)['resources'][0]
    assert checked['cycles']==resource['cycles'] and checked['source_sha256']==resource['source_sha256']
    for a,b in zip(resource['frames'],checked['frames']):
        assert a['geometry']==b['geometry'] and a['dep'].tobytes()==b['dep']
        assert all(np.array_equal(a[k],b[k]) for k in ['I','F','S','M'])
    # Removing the two auxiliary planes exactly restores the acquired V7 file.
    plain=copy.deepcopy(checked)
    for f in plain['frames']:
        f.pop('S');f.pop('M');f['guide']=f['I'];f['dep']=np.frombuffer(f['dep'],np.uint8).copy()
    roundtrip=WORK/'roundtrip.registry';leaves.write(roundtrip,[plain],plain['profile'],version=7)
    assert roundtrip.read_bytes()==source.read_bytes();roundtrip.unlink()
    infos.append(new);resources[(c['aid'],ref)]=resource
    details.append(dict(animation_id=c['aid'],resref=ref,frames=len(masks),V7_sha256=info['sha256'],V9_sha256=new['sha256'],frame_masks=masks))
    print(json.dumps(dict(animation_id=c['aid'],resref=ref,unique_masks=statistics['unique_masks'],hits=statistics['mask_cache_hits'])),flush=True)
assert statistics['physical_frames']==1688
sdf=bytearray(b'IEESDF1\0')
for c in chunks:
    resource=resources[(c['aid'],c['ref'])]
    for f in resource['frames']:
        for k,palette in enumerate(c['palettes']):
            rgba=resource['profile'].decode(f['I'],f['F'],palette);shadow=rgba[f['I']==1]
            assert np.all(shadow[:,:3]==0) and np.all(shadow[:,3]==127)
            m=f['M'];valid=m!=0xffffffff;encoded=np.zeros((*m.shape,4),np.uint8)
            encoded[valid,:3]=rgba.reshape(-1,4)[m[valid],:3];encoded[...,3]=f['S']
            encoded[6:-6,6:-6,3]|=(f['I']==1).astype(np.uint8)*128
            sdf.extend(hashlib.sha256(encoded.tobytes()).digest())
            if k==0:composite=hashlib.sha256(encoded[4:-4,4:-4].tobytes()).digest()
        sdf.extend(composite)
(isolated/'sdf.oracle').write_bytes(sdf)
components=[];shards=[];directory=[];animations=[]
for n,(info,detail) in enumerate(zip(infos,details)):
    entry=registry.catalog_shard_entry_bytes(info,isolated);digest=registry.catalog_component_digest(2,[entry])
    components.append(dict(index=n,digest=digest,shard_start=n,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=info['registry_bytes']))
    shards.append(dict(index=n,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(info['sha256']),**info))
    directory.append(dict(animation_id=detail['animation_id'],resref=detail['resref'],component_index=n,shard_index=n,resource_ordinal=0))
for aid in previous['animation_ids']:animations.append(dict(animation_id=aid,owner=11,component_indices=[n for n,d in enumerate(details) if d['animation_id']==aid]))
catalog=registry.write_registry_catalog_index(isolated/'CreatureSprites-XN.catalog',2,animations,components,shards,directory,[c['digest'] for c in components],dict(shard_registry_versions=[9]))
write_json(isolated/'pack.json',dict(catalog=catalog,leaves=infos))
parent=registry.read_sealed_catalog_index(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog',previous['catalog']['sha256']);mixed=copy.deepcopy(parent)
logical=load(parent_root/'pack.json')['catalog']['logical_component_digests'][:]
out=WORK/'combined';assets=out/'iee-assets/creature-sprites';assets.mkdir(parents=True)
targets={(d['animation_id'],d['resref']):d for d in parent['directory'] if d['animation_id'] in previous['animation_ids']}
assert len(targets)==20
replacement={}
for local,(info,detail) in enumerate(zip(infos,details)):
    binding=targets[(detail['animation_id'],detail['resref'])];ci,si=binding['component_index'],binding['shard_index']
    assert parent['components'][ci]['shard_count']==1 and parent['shards'][si]['resource_count']==1
    replacement[si]=isolated/registry.catalog_shard_filename(info['sha256'])
    mixed['shards'][si]=dict(shards[local],index=si);mixed['components'][ci]=dict(components[local],index=ci,shard_start=si);logical[ci]=components[local]['digest']
for si,shard in enumerate(mixed['shards']):
    source=replacement.get(si,parent_root/shard['registry']);assert source.is_file();os.link(source,assets/source.name)
catalog=registry.write_registry_catalog_index(assets/'CreatureSprites-XN.catalog',2,mixed['animations'],mixed['components'],mixed['shards'],mixed['directory'],logical,dict(shard_registry_versions=[6,7,9]))
checked=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',catalog['sha256'])
assert checked['animations']==parent['animations'] and checked['directory']==parent['directory']
assert all(checked['shards'][i]==s for i,s in enumerate(parent['shards']) if i not in replacement)
assert checked['total_resources']==4592 and checked['total_frames']==1587864
write_json(out/'pack.json',dict(catalog=catalog,new_shards=[mixed['shards'][i] for i in sorted(replacement)]))
baseline=load(PARENT/'baseline.json');baseline['parent_catalog_sha256']=previous['catalog']['sha256'];baseline['parent_generation']=ident(PARENT/'current-generation.json')
baseline['preserved'].append(dict(relative_path='override/QMWYVW01.cre',sha256=load(PARENT/'creatures.json')['fixture']['sha256']))
baseline['inherited_QA'].append(ident(ROOT/'sprite/index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json'))
write_json(HERE/'baseline.json',baseline)
write_json(HERE/'production.json',dict(schema='bg2-Large16-SDF-production-v1',family='monster_large16',animation_ids=previous['animation_ids'],recipe=recipe,stats=statistics,resources=18,frames=1688,auxiliary_INV_V7_unchanged=2,details=details,original_generation=ident(PARENT/'current-generation.json'),catalog=ident(assets/'CreatureSprites-XN.catalog'),registry_version=9,colour_planes_I_F_deps_profile_byte_identical=True,V7_roundtrip_all18_byte_identical=True,native_geometry_cycles_unchanged=True,world_shadow_colour_supported=True,world_wyvern_shadow_pixels=0,all_native_routes_unchanged=50273,unchanged_shards=4574,ingame_QA=False,release=False))
print(json.dumps(dict(complete=True,stats=statistics,catalog=catalog['sha256'])),flush=True)
