"""Phase-4 Bodhi pilot: reuse V6 leaves, compare source/cache, isolated catalog + native oracle + previews."""
from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import subprocess

import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_monster_contract import get_profile
from palette_monster import backend_for_run
from palette_monster_work_plan import Cache,WorkPlan,require
from palette_oracle import read_bam_p8
from palette_work_plan import file_sha,write_json
import palette_registry as v6
import run_creature_sprite_x2 as registry


def relative(path): return Path(path).resolve().relative_to(ROOT).as_posix()


def adopt_inspector_only_cache(plan,resources,cache_root,leaves):
    """Exact recipe + AST proof; changed catalog inspector is never invoked by pixel production."""
    cache=Cache(plan,cache_root,backend_for_run(cache_root))
    original_namespace=json.loads((leaves/'leaves.json').read_text())['cache_namespace']
    if original_namespace==cache.namespace: return cache,dict(adopted=0,namespace_unchanged=True)
    source_root=cache_root/'x2'/original_namespace
    source_recipe=json.loads((source_root/'recipe.json').read_text())
    old=json.loads(json.dumps(source_recipe));new=json.loads(json.dumps(cache.recipe))
    for recipe in (old,new): recipe.pop('namespace')
    old_sha=old['code_sha256'].pop('run_creature_sprite_x2.py')
    new_sha=new['code_sha256'].pop('run_creature_sprite_x2.py')
    require(old==new,'cache migration changes pixel/profile/inference recipe')
    previous=subprocess.run(['git','show','1e0eda3d:pipeline/scripts/run_creature_sprite_x2.py'],cwd=ROOT,
                            check=True,capture_output=True).stdout
    current=(ROOT/'pipeline/scripts/run_creature_sprite_x2.py').read_bytes()
    require(hashlib.sha256(previous).hexdigest()==old_sha and hashlib.sha256(current).hexdigest()==new_sha,
            'cache migration source identity differs')
    def pixel_ast(raw):
        tree=ast.parse(raw.decode('utf-8'))
        tree.body=[n for n in tree.body if not (isinstance(n,ast.FunctionDef) and n.name=='inspect_registry_catalog')]
        return ast.dump(tree,include_attributes=False)
    require(pixel_ast(previous)==pixel_ast(current),'code outside catalog inspector changed; cache reuse refused')
    source=Cache(plan,cache_root,cache.recipe['inference'])
    source.namespace=original_namespace;source.root=source_root;source.directory=source_root/'work/encoded';source.recipe=source_recipe
    records=[]
    with cache.exclusive():
        for row in plan.work_rows(resources):
            work=plan.work(row);arrays=source.load(work);cache.validate(work,arrays)
            destination=cache.path(work)
            if not destination.exists():
                temporary=destination.with_suffix('.part');shutil.copyfile(source.path(work),temporary);temporary.replace(destination)
            cache.load(work)
            original_sha=file_sha(source.path(work));require(file_sha(destination)==original_sha,'adopted result bytes changed')
            records.append(dict(key=plan.key(work),sha256=original_sha))
    return cache,dict(adopted=len(records),old_namespace=original_namespace,new_namespace=cache.namespace,
                      compatibility='only inspect_registry_catalog AST changed; all other AST and recipe fields identical',
                      previous_commit='1e0eda3d',old_code_sha256=old_sha,new_code_sha256=new_sha,
                      encoded_payloads_sha256=hashlib.sha256(json.dumps(records,sort_keys=True).encode()).hexdigest(),
                      original_cache_unchanged=True,gpu_recomputed=False)


def native_palettes(profile):
    palettes=list(profile.fitting.copy())
    partial=profile.fitting[0].copy();partial[:,3]=128;partial[0]=0;partial[1,3]=64;palettes.append(partial)
    opaque=profile.fitting[0].copy();opaque[:,3]=255;opaque[0]=0;palettes.append(opaque)
    arbitrary=np.random.default_rng(profile.profile_id).integers(0,256,(256,4),dtype=np.uint8)
    arbitrary[:,3]=200;arbitrary[0]=0;arbitrary[1,3]=100;palettes.append(arbitrary)
    for palette in palettes: palette[0]=0
    return np.stack(palettes)


def scalar_lut(profile,palettes):
    """Independent integer RGB/primary-alpha oracle; never calls Profile.decode."""
    table=np.empty((len(palettes),256,8,4),np.uint8)
    for k,palette in enumerate(palettes):
        for i in range(256):
            s=int(profile.succ[i])
            for f in range(8):
                for c in range(3): table[k,i,f,c]=((8-f)*int(palette[i,c])+f*int(palette[s,c])+4)//8
                table[k,i,f,3]=int(palette[i,3]) if i else 0
    return table


def verify_and_oracle(resource,info,plan,cache,path):
    native=read_bam_p8((ROOT/resource['canonical_path']).read_bytes())
    decoded=info['frame_data'][0];profile=get_profile(resource['profile_id'])
    require(info['version']==6 and info['scale']==2 and info['class_profile_id']==resource['profile_id'] and
            info['decode_rule_id']==2 and decoded['source_sha256']==resource['canonical_sha256'], 'leaf source/profile differs')
    require(len(decoded['frames'])==len(native['frames'])==resource['frame_count'],'native frame count changed')
    require(decoded['cycles']==[c['frame_indices'] for c in native['cycles']],'native cycles/slots changed')
    require(native['palette_bgra'].tobytes().hex()==profile.document['base_bgra_hex'],'native fixed palette changed')
    palettes=native_palettes(profile);lut=scalar_lut(profile,palettes)
    stats=Counter();frames=[]
    with path.open('xb') as stream:
        stream.write(struct.pack('<8s5I',b'IEEQM4\0\0',len(palettes),len(native['frames']),resource['profile_id'],
                                 int(resource['animation_id'],16),len(native['cycles'])))
        stream.write(resource['resref'].encode().ljust(8,b'\0')+bytes.fromhex(resource['canonical_sha256']))
        stream.write(palettes.tobytes())
        for cycle in decoded['cycles']:
            stream.write(struct.pack('<I',len(cycle))+np.asarray(cycle,dtype='<u4').tobytes())
        for n,(source,encoded) in enumerate(zip(native['frames'],decoded['frames'],strict=True)):
            geometry=(source['width'],source['height'],source['center_x'],source['center_y'],native['transparent'])
            require(encoded['geometry']==geometry,'native frame dimensions/centres/transparency changed')
            row=dict(plan.db.execute('''SELECT f.*,q.* FROM frames f JOIN processing_queue q USING(work_id)
                         WHERE f.resource_id=? AND f.frame_index=?''',(resource['resource_id'],n)).fetchone())
            work=plan.work(row,resource=resource,position=row);expected=cache.load(work)
            h,w=source['indices'].shape
            i=np.frombuffer(encoded['I'],np.uint8).reshape(h*2,w*2)
            f=np.frombuffer(encoded['F'],np.uint8).reshape(i.shape) if encoded['F'] else np.zeros_like(i)
            require(np.array_equal(i,expected['I']) and np.array_equal(f,expected['F']) and
                    encoded['dep']==expected['dep'].tobytes(),'leaf differs from validated persistent result')
            reps=np.full(256,65535,np.uint16);values,offsets=np.unique(source['indices'],return_index=True);reps[values]=offsets
            require(np.array_equal(encoded['representatives'],reps),'source representative offsets changed')
            stream.write(struct.pack('<IIii',w,h,source['center_x'],source['center_y']))
            for k in range(len(palettes)):
                pixels=lut[k,i,f]
                stream.write(hashlib.sha256(pixels.tobytes()).digest())
            stats['native_frames']+=1;stats['decoded_pixels']+=i.size
            stats['fractional_pixels']+=int(np.count_nonzero(f));stats['fractional_frames']+=int(bool(np.any(f)))
            stats['null_frames']+=int(source['indices'].shape==(1,1) and source['indices'][0,0]==2)
            frames.append(dict(source=source,guide=expected['guide'],I=i,F=f))
    stats['cycles']=len(decoded['cycles']);stats['cycle_slots']=sum(map(len,decoded['cycles']))
    return dict(resref=resource['resref'],profile_id=resource['profile_id'],source_sha256=resource['canonical_sha256'],
                source_cache_leaf_identical=True,representatives_identical=True,native_geometry_cycles_identical=True,
                oracle=dict(path=relative(path),sha256=file_sha(path),palettes=len(palettes)),**stats),frames,lut,native


def preview(output,samples):
    labels=['Source NN x2','Guide xBR / neutre','Q3m / neutre','Q3m / chaud','Q3m / froid']
    tw,th=208,226;canvas=Image.new('RGB',(tw*len(labels),th*len(samples)+46),(25,27,31));draw=ImageDraw.Draw(canvas)
    try: font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    except OSError: font=ImageFont.load_default()
    for x,label in enumerate(labels): draw.text((x*tw+10,12),label,font=font,fill=(235,235,235))
    refs=[]
    for row,(ref,cycle,index,frame,lut) in enumerate(samples):
        source=frame['source'];native=source['indices'];guide=frame['guide'];i,f=frame['I'],frame['F']
        images=[lut[0,np.repeat(np.repeat(native,2,0),2,1),0],lut[0,guide,0],lut[0,i,f],lut[1,i,f],lut[2,i,f]]
        for col,rgba in enumerate(images):
            tile=Image.new('RGBA',(tw,th),(42,45,50,255));td=ImageDraw.Draw(tile)
            for y in range(22,th-20,12):
                for x in range(0,tw,12):
                    if (x//12+y//12)%2: td.rectangle((x,y,x+11,y+11),fill=(55,58,63,255))
            img=Image.fromarray(rgba,'RGBA')
            tile.alpha_composite(img,(tw//2-2*source['center_x'],th-44-2*source['center_y']))
            td.text((8,th-20),f'{ref}  cycle {cycle} / frame {index}',font=font,fill=(225,225,225,255))
            canvas.paste(tile.convert('RGB'),(col*tw,46+row*th))
        refs.append(dict(resref=ref,cycle=cycle,frame=index,centre=[source['center_x'],source['center_y']],
                         fractional_pixels=int(np.count_nonzero(f))))
    canvas.save(output/'preview.png');write_json(output/'preview.json',dict(role='comparison-only-not-ingame-QA',samples=refs))


def representative_cycles(native,frames):
    available=[c for c,cycle in enumerate(native['cycles']) if any(frames[n]['source']['indices'].size>1 for n in cycle['frame_indices'])]
    if not available: return []
    chosen=set();result=[]
    for c in dict.fromkeys(available[x] for x in (0,len(available)//2,len(available)-1)):
        possible=[n for n in native['cycles'][c]['frame_indices'] if frames[n]['source']['indices'].size>1 and n not in chosen]
        if not possible: continue
        n=max(possible,key=lambda n:np.count_nonzero(frames[n]['F']))
        chosen.add(n);result.append((c,n))
    return result


def assemble(leaves,cache_root,output):
    require(not output.exists(),'new pilot destination required');output.mkdir(parents=True)
    assets=output/'iee-assets/creature-sprites';assets.mkdir(parents=True)
    plan=WorkPlan()
    try:
        resources=plan.resources(refs=['NBOHG1','NBOHG2']);plan.validate_sources(resources)
        cache,adoption=adopt_inspector_only_cache(plan,resources,cache_root,leaves)
        infos,components,directory,digests,reports,samples=[],[],[],[],[],[]
        for number,resource in enumerate(resources):
            leaf=leaves/(resource['resref']+'.registry');info=v6.inspect(leaf,include_resource_records=True,include_frames=True)
            target=assets/registry.catalog_shard_filename(info['sha256']);shutil.copyfile(leaf,target)
            require(file_sha(target).upper()==info['sha256'],'copied leaf differs')
            report,frames,lut,native=verify_and_oracle(resource,info,plan,cache,output/(resource['resref']+'-oracle.bin'))
            reports.append(report);infos.append(info)
            components.append(dict(index=number,digest=registry.catalog_component_digest(2,[registry.catalog_shard_entry_bytes(info,target)]),
                                   shard_start=number,shard_count=1,**{k:info[k] for k in ('resource_count','frame_count','index_bytes','registry_bytes')}))
            directory.append(dict(animation_id='0x7F30',resref=resource['resref'],component_index=number,shard_index=number,resource_ordinal=0))
            digests.append(registry.catalog_source_component_sha256(2,info['resource_records']))
            for c,n in representative_cycles(native,frames):
                samples.append((resource['resref'],c,n,frames[n],lut))
        storage=dict(shard_registry_version=6)
        for k in ('stored_index_bytes','stored_fraction_bytes','fraction_bytes','compressed_frame_count','raw_frame_count',
                  'compressed_fraction_count','fractional_frame_count'): storage[k]=sum(i[k] for i in infos)
        catalog=registry.write_registry_catalog_index(assets/registry.XN_REGISTRY_CATALOG_FILENAME,2,
                    [dict(animation_id='0x7F30',owner=3,component_indices=[0,1])],components,infos,directory,digests,storage)
        checked=registry.inspect_registry_catalog(assets/registry.XN_REGISTRY_CATALOG_FILENAME)
        require(checked['logical_content_sha256']==catalog['logical_content_sha256'],'pilot catalog logical identity differs')
        preview(output,samples)
        report=dict(schema='bg2-monster-q3m-isolated-pilot-pack-v1',status='source-cache-leaf-verified-awaiting-native-host',
                    scope='NBOHG1+NBOHG2 only; no active catalog update',animation_id='0x7F30',owner=3,scale=2,k=6,
                    dithering=False,boundary_mixing=False,cache_namespace=cache.namespace,cache_adoption=adoption,inference=cache.recipe['inference'],
                    catalog=dict(path=relative(assets/registry.XN_REGISTRY_CATALOG_FILENAME),sha256=catalog['sha256'],
                                 logical_content_sha256=catalog['logical_content_sha256'],components=2,shards=2),resources=reports,
                    ingame_validated=False,visual_QA_accepted=False,installation_changed=False)
        write_json(output/'pack.json',report)
        print(json.dumps(dict(output=relative(output),cache_namespace=cache.namespace,resources=reports),ensure_ascii=False),flush=True)
    finally: plan.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--leaves',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();assemble(args.leaves.resolve(),args.cache.resolve(),args.output.resolve())
