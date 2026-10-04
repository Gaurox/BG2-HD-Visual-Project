"""Scoped 0x6110 CHFB1 SDF trial, derived from installed Q3m; no inference."""
import copy, hashlib, importlib.util, json, shutil, struct, sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_registry as v6
import character_sdf_registry as v10
import run_creature_sprite_x2 as registry
from sprite_sdf_registry import planes
from palette_p2 import golden
from workspace_paths import get_path

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,value):
    assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
reference_path=ROOT/'docs/measurements/q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py'
spec=importlib.util.spec_from_file_location('sdf_reference',reference_path);reference=importlib.util.module_from_spec(spec);spec.loader.exec_module(reference)
previous=ROOT/'docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1'
generation=load(previous/'current-generation.json');baseline=load(previous/'baseline.json')
game=get_path('bg2ee_game_root',required=True);catalog_path=game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog'
assert sha(catalog_path)==generation['catalog']['sha256'] and sha(game/'InfinityEngine-Enhancer.dll')==generation['dll']['sha256']
parent=registry.read_sealed_catalog_index(catalog_path,generation['catalog']['sha256'])
targets=sorted((x for x in parent['directory'] if x['animation_id']=='0x6110' and x['resref'].startswith('CHFB1')),key=lambda x:x['resref'])
assert len(targets)==23
work=ROOT/'sprite/.work/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1';assert not work.exists()
isolated=work/'isolated';original=work/'original';combined=work/'combined'
for path in (isolated,original,combined):path.mkdir(parents=True)
cache_dir=work/'mask-cache';cache_dir.mkdir()
palettes=golden()[0][:6].copy();palettes[:,0]=0
assert np.all(palettes[:,1]==[0,0,0,128]) and np.all(palettes[:,2:,3]==255)
oracle=(isolated/'character-sdf.oracle').open('xb');oracle.write(struct.pack('<8sII',b'IEECSD10',len(targets),len(palettes)));oracle.write(palettes.tobytes())
mask_cache={};infos=[];old_infos=[];details=[];witnesses=[]
stats=dict(physical_frames=0,unique_masks=0,mask_cache_hits=0,new_neural_targets=0,new_Q3m_encodings=0)
recipe_bytes=json.dumps(reference.RECIPE,sort_keys=True).encode()+bytes.fromhex(sha(reference_path))
for route in targets:
    old=parent['shards'][route['shard_index']];source=game/old['registry'];assert sha(source).upper()==old['sha256']
    parsed=v6.inspect(source,include_frames=True);assert parsed['resource_count']==1
    resource=parsed['frame_data'][0];assert resource['resref']==route['resref']
    for frame in resource['frames']:
        w,h,*_=frame['geometry']
        frame['I']=np.frombuffer(frame['I'],np.uint8).reshape(h*2,w*2)
        frame['F']=np.frombuffer(frame['F'],np.uint8).reshape(h*2,w*2) if frame['F'] else np.zeros_like(frame['I'])
    shutil.copyfile(source,original/source.name);old_infos.append(parsed)
    oracle.write(struct.pack('<8sII',resource['resref'].encode().ljust(8,b'\0'),len(resource['frames']),len(resource['cycles'])))
    for cycle in resource['cycles']:oracle.write(struct.pack('<I',len(cycle))+struct.pack(f'<{len(cycle)}I',*cycle))
    fields=[];reports=[]
    for ordinal,frame in enumerate(resource['frames']):
        i,f=frame['I'],frame['F'];binary=np.minimum(i,3)
        key=hashlib.sha256(recipe_bytes+struct.pack('<II',*i.shape)+binary.tobytes()).hexdigest()
        if key not in mask_cache:
            if np.any(i>=2):field,report=reference.reconstruct(i)
            else:field=np.full((i.shape[0]+12,i.shape[1]+12),-4,np.float32);report=dict(empty_foreground=True)
            s,m=planes(i,field);mask_cache[key]=(s,m);stats['unique_masks']+=1
            np.savez_compressed(cache_dir/(key+'.npz'),S=s,M=m)
        else:stats['mask_cache_hits']+=1
        s,m=mask_cache[key];fields.append((s,m));stats['physical_frames']+=1
        reports.append(dict(frame=ordinal,mask_key=key))
        w,h,cx,cy,_=frame['geometry'];oracle.write(struct.pack('<IIii',w,h,cx,cy))
        # Independent scalar-derived LUT; colours/shadow alpha unchanged.
        indices=np.arange(256);terminal=(indices<=3)|((indices<88)&((indices-4)%12==11))|((indices>=88)&((indices-88)%8==7))
        successor=np.where(terminal,indices,indices+1)
        for palette in palettes:
            a=palette[i,:3].astype(np.uint16);b=palette[successor[i],:3].astype(np.uint16)
            rgba=np.dstack((((a*(8-f[...,None])+b*f[...,None]+4)//8).astype(np.uint8),palette[i,3]))
            encoded=np.zeros((*s.shape,4),np.uint8);valid=m!=0xffffffff
            encoded[valid,:3]=rgba.reshape(-1,4)[m[valid],:3];encoded[...,3]=s
            encoded[6:-6,6:-6,3]|=(i==1).astype(np.uint8)*128
            oracle.write(hashlib.sha256(rgba.tobytes()).digest());oracle.write(hashlib.sha256(encoded.tobytes()).digest())
            oracle.write(hashlib.sha256(encoded[4:-4,4:-4].tobytes()).digest())
        if resource['resref'] in ('CHFB1G11','CHFB1G12','CHFB1A5') and ordinal in (0,10):
            p=work/f"{resource['resref']}-{ordinal}.npz";np.savez_compressed(p,I=i,F=f,S=s,M=m,raw=rgba)
            witnesses.append(identity(p))
    temporary=isolated/(route['resref']+'.registry');info=v10.derive(source,temporary,fields)
    temporary.rename(isolated/registry.catalog_shard_filename(info['sha256']));infos.append(info)
    details.append(dict(resref=route['resref'],frames=len(fields),source_leaf_sha256=old['sha256'],leaf=info,masks=reports))
    print(json.dumps(dict(resref=route['resref'],frames=len(fields),unique_masks=stats['unique_masks'],mask_cache_hits=stats['mask_cache_hits'])),flush=True)
oracle.close()
assert stats['physical_frames']==10323

def component(info,ci,si):
    entry=registry.catalog_shard_entry_bytes(info,isolated);digest=registry.catalog_component_digest(2,[entry])
    return dict(index=ci,digest=digest,shard_start=si,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=info['registry_bytes'])
for folder,leaves in ((isolated,infos),(original,old_infos)):
    comps=[component(info,n,n) for n,info in enumerate(leaves)]
    shards=[dict(info,index=n,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(info['sha256'])) for n,info in enumerate(leaves)]
    directory=[dict(animation_id='0x6110',resref=route['resref'],component_index=n,shard_index=n,resource_ordinal=0) for n,route in enumerate(targets)]
    registry.write_registry_catalog_index(folder/'CreatureSprites-XN.catalog',2,[dict(animation_id='0x6110',owner=1,component_indices=list(range(23)))],comps,shards,directory,[c['digest'] for c in comps],dict(shard_registry_versions=[10 if folder==isolated else 6]))
# Shared source components remain in place for their other five consumers.
mixed=copy.deepcopy(parent);logical=load(ROOT/generation['generation_dir']/'pack.json')['catalog']['logical_component_digests'][:]
replacements={};new_shards=[]
for route,info in zip(targets,infos):
    ci=len(mixed['components']);si=len(mixed['shards']);comp=component(info,ci,si)
    shard=dict(info,index=si,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(info['sha256']))
    mixed['components'].append(comp);mixed['shards'].append(shard);logical.append(comp['digest']);new_shards.append(shard)
    replacements[route['component_index']]=ci
    target=next(x for x in mixed['directory'] if x['animation_id']=='0x6110' and x['resref']==route['resref'])
    target.update(component_index=ci,shard_index=si)
actor=next(x for x in mixed['animations'] if x['animation_id']=='0x6110')
actor['component_indices']=[replacements.get(x,x) for x in actor['component_indices']]
new_catalog=combined/'CreatureSprites-XN.catalog'
catalog=registry.write_registry_catalog_index(new_catalog,2,mixed['animations'],mixed['components'],mixed['shards'],mixed['directory'],logical,dict(shard_registry_versions=[6,7,9,10]))
checked=registry.read_sealed_catalog_index(new_catalog,catalog['sha256'])
assert all(x in checked['directory'] for x in parent['directory'] if not (x['animation_id']=='0x6110' and x['resref'].startswith('CHFB1')))
assert checked['components'][:len(parent['components'])]==parent['components'] and checked['shards'][:len(parent['shards'])]==parent['shards']
assert all(x in checked['animations'] for x in parent['animations'] if x['animation_id']!='0x6110')
write(combined/'pack.json',dict(catalog=catalog,new_shards=new_shards))
write(HERE/'production.json',dict(scope='0x6110 CHFB1 world body only; armour/equipment/UI/other consumers unchanged',animation_ids=['0x6110'],resources=23,frames=10323,registry_version=10,scale=2,colour_profile=1,decode_rule=1,stats=stats,recipe=reference.RECIPE,details=details,new_shards=new_shards,witnesses=witnesses,work_dir=work.relative_to(ROOT).as_posix(),catalog=identity(new_catalog),oracle=identity(isolated/'character-sdf.oracle'),original_compressed_colour_leaves_byte_identical=True,inherited_directory_entries_unchanged=len(parent['directory'])-23,ingame_QA=False,release=False))
write(HERE/'baseline.json',dict(game_root='config://bg2ee_game_root',dll_sha256=generation['dll']['sha256'],catalog_sha256=generation['catalog']['sha256'],parent_runtime=generation['runtime'],unchanged_assets=baseline['unchanged_assets'],replaced_shaders=load(ROOT/generation['runtime']['path'])['shaders']))
print(json.dumps(stats))
