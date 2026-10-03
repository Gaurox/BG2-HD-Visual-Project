"""Phase-5 standalone 39-BAM Monster pack. Reuse leaves and phase-4 verification; no active catalog update."""
from __future__ import annotations
import argparse
from collections import defaultdict
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
PILOT=ROOT/'docs/measurements/q3m-monster-pilot-x2-20261003-v1/assemble.py'
spec=importlib.util.spec_from_file_location('q3m_pilot_assembly',PILOT)
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)


def preview(output,samples):
    """Centre-align every sample with enough room for the full Monster frame."""
    np=pilot.np;Image=pilot.Image;ImageDraw=pilot.ImageDraw;ImageFont=pilot.ImageFont
    left=min(-2*s[3]['source']['center_x'] for s in samples)
    top=min(-2*s[3]['source']['center_y'] for s in samples)
    right=max(2*(s[3]['source']['width']-s[3]['source']['center_x']) for s in samples)
    bottom=max(2*(s[3]['source']['height']-s[3]['source']['center_y']) for s in samples)
    tw,th=max(208,right-left+32),max(226,bottom-top+64);ax,ay=16-left,30-top
    labels=['Source NN x2','Guide xBR / neutre','Q3m / neutre','Q3m / chaud','Q3m / froid']
    canvas=Image.new('RGB',(tw*5,th*len(samples)+46),(25,27,31));draw=ImageDraw.Draw(canvas)
    try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
    except OSError:font=ImageFont.load_default()
    for col,label in enumerate(labels):draw.text((col*tw+10,12),label,font=font,fill=(235,235,235))
    records=[]
    for row,(ref,cycle,index,frame,lut) in enumerate(samples):
        source=frame['source'];native=source['indices'];g=frame['guide'];i,f=frame['I'],frame['F']
        images=[lut[0,np.repeat(np.repeat(native,2,0),2,1),0],lut[0,g,0],lut[0,i,f],lut[1,i,f],lut[2,i,f]]
        for col,rgba in enumerate(images):
            tile=Image.new('RGBA',(tw,th),(42,45,50,255));td=ImageDraw.Draw(tile)
            for y in range(22,th-20,12):
                for x in range(0,tw,12):
                    if (x//12+y//12)%2:td.rectangle((x,y,x+11,y+11),fill=(55,58,63,255))
            tile.alpha_composite(Image.fromarray(rgba,'RGBA'),(ax-2*source['center_x'],ay-2*source['center_y']))
            td.text((8,th-20),f'{ref}  cycle {cycle} / frame {index}',font=font,fill=(225,225,225,255))
            canvas.paste(tile.convert('RGB'),(col*tw,46+row*th))
        records.append(dict(resref=ref,cycle=cycle,frame=index,centre=[source['center_x'],source['center_y']],
                            fractional_pixels=int(np.count_nonzero(f))))
    canvas.save(output/'preview.png');pilot.write_json(output/'preview.json',dict(role='comparison-only-not-ingame-QA',
                                     tile=[tw,th],common_anchor=[ax,ay],samples=records))


def assemble(leaves,cache_root,output):
    pilot.require(not output.exists(),'new complete pack destination required')
    output.mkdir(parents=True);assets=output/'iee-assets/creature-sprites';assets.mkdir(parents=True)
    (output/'oracles').mkdir();(output/'previews').mkdir()
    plan=pilot.WorkPlan();started=time.monotonic()
    try:
        resources=plan.resources();plan.validate_sources(resources)
        cache=pilot.Cache(plan,cache_root,pilot.backend_for_run(cache_root))
        descriptor=json.loads((leaves/'leaves.json').read_text())
        pilot.require(descriptor['cache_namespace']==cache.namespace and
                      {r['resref'] for r in descriptor['resources']}=={r['resref'] for r in resources},'complete leaf coverage/recipe differs')
        infos,components,directory,digests,reports=[],[],[],[],[]
        memberships=defaultdict(list);samples=defaultdict(list);source_groups=defaultdict(list)
        for number,resource in enumerate(resources):
            ref=resource['resref'];leaf=leaves/(ref+'.registry')
            info=pilot.v6.inspect(leaf,include_resource_records=True,include_frames=True)
            registered=next(r for r in descriptor['resources'] if r['resref']==ref)
            pilot.require(info['sha256']==registered['sha256'],'leaf manifest SHA differs')
            target=assets/pilot.registry.catalog_shard_filename(info['sha256']);shutil.copyfile(leaf,target)
            pilot.require(pilot.file_sha(target).upper()==info['sha256'],'copied registry differs')
            report,frames,lut,native=pilot.verify_and_oracle(resource,info,plan,cache,output/'oracles'/(ref+'.bin'))
            report['animation_id']=resource['animation_id'];report['leaf_sha256']=info['sha256'];report['registry_bytes']=info['registry_bytes']
            report['native_unreferenced_frames']=plan.db.execute('SELECT count(*) FROM frames WHERE resource_id=? AND cycle_referenced=0',
                                                               (resource['resource_id'],)).fetchone()[0]
            reports.append(report);source_groups[resource['canonical_sha256']].append(ref)
            infos.append({k:v for k,v in info.items() if k not in ('frame_data','resource_records')})
            components.append(dict(index=number,digest=pilot.registry.catalog_component_digest(2,[pilot.registry.catalog_shard_entry_bytes(info,target)]),
                                   shard_start=number,shard_count=1,**{k:info[k] for k in ('resource_count','frame_count','index_bytes','registry_bytes')}))
            memberships[resource['animation_id']].append(number)
            directory.append(dict(animation_id=resource['animation_id'],resref=ref,component_index=number,shard_index=number,resource_ordinal=0))
            digests.append(pilot.registry.catalog_source_component_sha256(2,info['resource_records']))
            # The two base groups are visual samples; all 39 resources are verified above and by the native oracle.
            if ref in ('NBOHG1','NBOHG2','MGLCG1','MGLCG2','MBEHG1','MBEHG2'):
                for cycle,n in pilot.representative_cycles(native,frames):
                    samples[resource['animation_id']].append((ref,cycle,n,frames[n],lut))
            print(json.dumps(dict(assembled=number+1,resources=len(resources),resref=ref,frames=report['native_frames'],
                                  unreferenced_frames=report['native_unreferenced_frames'])),flush=True)
        storage=dict(shard_registry_version=6)
        for k in ('stored_index_bytes','stored_fraction_bytes','fraction_bytes','compressed_frame_count','raw_frame_count',
                  'compressed_fraction_count','fractional_frame_count'):storage[k]=sum(i[k] for i in infos)
        catalog_path=assets/pilot.registry.XN_REGISTRY_CATALOG_FILENAME
        catalog=pilot.registry.write_registry_catalog_index(catalog_path,2,
                   [dict(animation_id=a,owner=3,component_indices=m) for a,m in sorted(memberships.items())],
                   components,infos,directory,digests,storage)
        checked=pilot.registry.inspect_registry_catalog(catalog_path)
        pilot.require(checked['logical_content_sha256']==catalog['logical_content_sha256'] and checked['total_frames']==20925 and
                      checked['animation_count']==3 and checked['total_resources']==39,'complete catalog logical coverage differs')
        for animation,selected in samples.items():
            folder=output/'previews'/animation;folder.mkdir();preview(folder,selected)
        pilot_record=json.loads((ROOT/'docs/measurements/q3m-monster-pilot-x2-20261003-v1/verification.json').read_text())
        reused=[]
        for report in reports:
            if report['resref'] not in ('NBOHG1','NBOHG2'):continue
            original=ROOT/'sprite/.work/q3m-monster-pilot-x2-leaves-20261003-v1'/(report['resref']+'.registry')
            pilot.require(pilot.file_sha(original).upper()==report['leaf_sha256'],'pilot leaf bytes changed')
            old_oracle=next(r for r in pilot_record['pack']['resources'] if r['resref']==report['resref'])['oracle']['sha256']
            pilot.require(report['oracle']['sha256']==old_oracle,'pilot oracle changed')
            reused.append(report['resref'])
        report=dict(schema='bg2-monster-q3m-complete-isolated-pack-v1',status='source-cache-leaf-verified-awaiting-native-host',
                    scope='three Monster families only; no Character integration or active catalog update',
                    animation_ids=sorted(memberships),owner=3,scale=2,k=6,dithering=False,boundary_mixing=False,
                    cache_namespace=cache.namespace,inference=cache.recipe['inference'],
                    catalog=dict(path=pilot.relative(catalog_path),sha256=catalog['sha256'],logical_content_sha256=catalog['logical_content_sha256'],
                                 components=39,shards=39),resources=reports,pilot_leaf_oracle_byte_reuse=reused,
                    source_alias_groups=[refs for refs in source_groups.values() if len(refs)>1],source_unique_payloads=len(source_groups),
                    frames=sum(r['native_frames'] for r in reports),cycles=sum(r['cycles'] for r in reports),
                    cycle_slots=sum(r['cycle_slots'] for r in reports),unreferenced_frames=sum(r['native_unreferenced_frames'] for r in reports),
                    elapsed_seconds=time.monotonic()-started,ingame_validated=False,visual_QA_accepted=False,installation_changed=False)
        pilot.write_json(output/'pack.json',report)
        print(json.dumps(dict(pack=pilot.relative(output),resources=39,frames=report['frames'],cycles=report['cycles'],
                             slots=report['cycle_slots'],source_payloads=report['source_unique_payloads'])),flush=True)
    finally:plan.close()


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--leaves',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args();assemble(a.leaves.resolve(),a.cache.resolve(),a.output.resolve())
