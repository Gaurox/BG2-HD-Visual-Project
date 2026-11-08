"""Seven scoped alpha derivations; exact premultiplied RGB, no inference/install."""
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
from build_effect_runtime_pack import write_pack
from compose_effect_runtime_packs import validate_pack

BASE=ROOT/'effects/batches/lot50-seedvr7b-apollo30-20261108-v1'
OUT=ROOT/'effects/batches/lot50-black-transparent-20261108-v1'
NAMES={'SPFINODI','SPFIRET','SPPFIRAI','SPPFIRXI','SPOUTA','STEAM1','STEAM4'}
PROBE=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def rel(p):return p.relative_to(ROOT).as_posix()
def sha(raw):return __import__('hashlib').sha256(raw).hexdigest().upper()
def evidence(role,p):return dict(role=role,path=rel(p),sha256=workflow.sha256_file(p),bytes=p.stat().st_size)

def produce(a):
    n=a['resref'];receipt=OUT/'verification'/f'{n}.json'
    if receipt.exists():return load(receipt)
    parent=ROOT/'effects/ressources'/n/'runs'/a['interpolation_run'];pm=parent/'02-interpolation/manifest.json';old=load(pm)
    run_id=f'{n.lower()}-black-transparent-apollo30-20261108-v1'
    run=parent.parent/run_id;stage=run/'02-interpolation';frames=stage/'frames-rgba'
    assert not (run/'run.json').exists(),'Use a new version for an existing correction'
    workflow.new_run(ROOT,n,'interpolation','black-transparent-premultiplied-flux',run_id,write=True)
    frames.mkdir(parents=True,exist_ok=True)
    snapshot=run/'producer-source.py';shutil.copyfile(Path(__file__),snapshot)
    spatial=load(ROOT/old['parent']['spatial_manifest']);cw,ch=spatial['aligned_canvas_size_x1']
    anchor=[spatial['frames'][0]['canvas_offset_x1'][i]+spatial['frames'][0]['centre_x1'][i] for i in range(2)]
    m=copy.deepcopy(old);old_to_new={};black_before=black_after=changed=0;phase_hashes=[]
    for f in m['frames']:
        w,h=f['physical_size_x4'];raw=(parent/'02-interpolation'/f['raw_rgba_x4']).read_bytes()
        before=np.frombuffer(raw,np.uint8).reshape(h,w,4);after=before.copy()
        after[:,:,3]=before[:,:,:3].max(2)
        straight=after.copy();mask=after[:,:,3]>0
        straight[:,:,:3][mask]=np.clip(np.rint(after[:,:,:3][mask].astype(float)*255/after[:,:,3][mask,None]),0,255).astype(np.uint8)
        straight[~mask]=0
        assert np.array_equal(after[:,:,:3],before[:,:,:3])
        assert np.all(after[:,:,3]<=before[:,:,3])
        assert not after[before[:,:,:3].max(2)==0].any()
        reconstructed=np.rint(straight[:,:,:3].astype(float)*straight[:,:,3:4]/255).astype(np.uint8)
        assert np.abs(reconstructed.astype(np.int16)-before[:,:,:3].astype(np.int16)).max()<=1
        black_before+=int(((before[:,:,:3].max(2)==0)&(before[:,:,3]>0)).sum())
        black_after+=int(((straight[:,:,:3].max(2)==0)&(straight[:,:,3]>0)).sum())
        changed+=int((before[:,:,3]!=after[:,:,3]).sum())
        png=frames/f'frame_{f["frame"]:04d}.png';raw_path=png.with_suffix('.rgba');straight_path=frames/f'frame_{f["frame"]:04d}-straight.rgba'
        Image.fromarray(after).save(png,compress_level=3);raw_path.write_bytes(after.tobytes());straight_path.write_bytes(straight.tobytes())
        old_to_new[(f['raw_rgba_x4_sha256'],tuple(f['physical_size_x4']))]=raw_path
        canvas=np.zeros((ch*4,cw*4,4),np.uint8);x,y=[(anchor[i]-f['centre_x1'][i])*4 for i in range(2)];canvas[y:y+h,x:x+w]=after
        f.update(rgba_x4='frames-rgba/'+png.name,rgba_x4_sha256=workflow.sha256_file(png),
                 raw_rgba_x4='frames-rgba/'+raw_path.name,raw_rgba_x4_sha256=workflow.sha256_file(raw_path),
                 straight_raw_rgba_x4='frames-rgba/'+straight_path.name,straight_raw_rgba_x4_sha256=workflow.sha256_file(straight_path),
                 anchored_rgba_sha256=sha(canvas.tobytes()),normal_alpha_policy='premultiplied flux encoded as alpha=max(Rp,Gp,Bp); exact black transparent')
        # Corrected transparency is now the default in both encodings.
        f.pop('neutral_raw_rgba_x4',None);f.pop('neutral_raw_rgba_x4_sha256',None)
        assert f['anchored_rgb_sha256']==sha(canvas[:,:,:3].tobytes())
        phase_hashes.append((f['anchored_rgba_sha256'],bool(after[:,:,3].any())))
    for v in m['timing']['cycles']:
        seq=v['timeline_frame_indices'];v['unique_rgba']=len({phase_hashes[i][0] for i in seq})
        v['empty_phases']=[phase for phase,i in enumerate(seq) if not phase_hashes[i][1]]
    carrier=run/'runtime-carrier'/f'{n}.bam';carrier.parent.mkdir();shutil.copyfile(ROOT/old['runtime_carrier']['path'],carrier)
    assert workflow.sha256_file(carrier)==old['runtime_carrier']['sha256']
    m['runtime_carrier'].update(path=rel(carrier))
    recipe=dict(schema='bg2-upscale-effect-interpolation-recipe-v1',recipe_id='black-transparent-premultiplied-flux',
                pipeline_id='effects.interpolation-30fps.v1',scale=4,target_fps=[30,1],
                source_run=a['interpolation_run'],parent_manifest=evidence('previous-interpolation-manifest',pm),
                policy='Keep exact premultiplied RGB; A=max(Rp,Gp,Bp); straight RGB reconstructed. No luminance cutoff, no inference, no timing/geometry change.',
                tools=[evidence('producer',snapshot)])
    save(run/'recipe.json',recipe);m['visual_treatment']=recipe
    m['alpha_derivation']=dict(parent_run=a['interpolation_run'],premultiplied_rgb_exact=True,normal_roundtrip_error_max=1)
    save(stage/'manifest.json',m)
    d=load(parent/'run.json');d['run_id']=run_id
    d['pipeline'].update(version='black-transparent-exact-flux.v1',recipe_path=rel(run/'recipe.json'),recipe_sha256=workflow.sha256_file(run/'recipe.json'))
    d['inputs'].append(evidence('previous-interpolation-manifest',pm))
    d['outputs']=[evidence('interpolation-manifest',stage/'manifest.json'),evidence('runtime-bam-carrier',carrier)]
    d['provenance'].update(created_at_utc=workflow.utc_now(),generator=rel(Path(__file__)),command=['correct.py',n])
    d['result'].update(completed_at_utc=workflow.utc_now(),status='completed',sealed=True)
    save(run/'run.json',d)
    checked=workflow.verify_run_descriptor(ROOT,run.parent.parent,n,run_id,stage='interpolation',spatial_run=a['spatial_run']);assert checked['ok'],checked
    oldpack=validate_pack(ROOT/a['pack']);assets=[]
    for f in oldpack.frames:
        source=old_to_new[(f['sha256'],tuple(f['physical_size_x4']))]
        row={k:v for k,v in f.items() if k not in {'resref','resource_frame'}}
        row.update(source=rel(source),source_sha256=workflow.sha256_file(source),sha256=workflow.sha256_file(source));assets.append(row)
    output=ROOT/'effects/ressources'/n/'packs'/f'{n.lower()}-black-transparent-profiles-20261108-v1'
    write_pack(output,(oldpack.root/'EffectAnimations-X4.registry').read_bytes(),assets,
               load(ROOT/'effects/ressources'/n/'runs'/a['spatial_run']/'run.json'),
               load(ROOT/spatial['source']['frame_manifest']),spatial,registry_version=3,
               timeline=oldpack.manifest['timeline'],interpolation_descriptor=d)
    newpack=validate_pack(output)
    assert (newpack.root/'EffectAnimations-X4.registry').read_bytes()==(oldpack.root/'EffectAnimations-X4.registry').read_bytes()
    original_contract=ROOT/a['runtime_verification'];original_contract=original_contract.parent.parent/'contracts'/f'{n}.tsv'
    log=OUT/'runtime-verification'/f'{n}.log';log.parent.mkdir(parents=True,exist_ok=True)
    with log.open('w',encoding='utf-8') as f:subprocess.run([str(PROBE),'--catalogue-only',str(output),str(original_contract)],stdout=f,stderr=subprocess.STDOUT,check=True)
    workflow.register_run(ROOT,n,'interpolation',run_id,write=True)
    result={**a,'parent_interpolation_run':a['interpolation_run'],'parent_pack':a['pack'],
            'interpolation_run':run_id,'pack':rel(output),'pack_manifest_sha256':newpack.manifest_sha256,
            'black_covered_pixels_before':black_before,'black_covered_pixels_after':black_after,'changed_alpha_pixels':changed,
            'premultiplied_rgb_exact':True,'native_registry_exact':True,'carrier_exact':True,
            'normal_roundtrip_max_error':1,'catalogue_probe':rel(log),'qa':'pending-user-review','installed':False,'passed':True}
    assert black_after==0
    save(receipt,result);print(n,'PASS',len(m['frames']),'phases; black pixels',black_before,'->0',flush=True)
    return result

def main():
    base=load(BASE/'production.json');results=[]
    for a in base['assets']:
        if a['resref'] in NAMES:results.append(produce(a))
    assert len(results)==7
    for r in results:
        receipt=OUT/'verification'/f'{r["resref"]}.json'
        r.update(verification=rel(receipt),runtime_verification=rel(receipt),source_interpolation_run=r['interpolation_run'])
        save(receipt,r)
    final=copy.deepcopy(base);by_name={r['resref']:r for r in results}
    final['assets']=[by_name.get(a['resref'],a) for a in base['assets']]
    final.update(completed_utc=workflow.utc_now(),alpha_revision='Seven black-matte alpha derivations; exact premultiplied RGB; previous production immutable.',
                 parent_production=evidence('previous-production',BASE/'production.json'))
    save(OUT/'production.json',final)
    save(OUT/'verification.json',dict(passed=7,assets=results,phases=sum(r['phases'] for r in results),
                                    native_contracts=sum(r['native_contracts'] for r in results),installed=False,qa='pending-user-review'))

if __name__=='__main__':main()
