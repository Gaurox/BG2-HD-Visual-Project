"""Independent decoded native/carrier geometry and visible temporal audit."""
from produce import ROOT,BATCH,ORIGINAL,load,save,rel
from pathlib import Path
import hashlib
import json
import sys
import numpy as np
from PIL import Image
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam
from compose_effect_runtime_packs import validate_pack


def sha(data):return hashlib.sha256(data).hexdigest().upper()


def verify(a):
    name=a['resref']; report=load(BATCH/'checks'/(name+'.json'))
    run=ROOT/'effects/ressources'/name/'runs'/report['interpolation_run']
    final=load(run/'02-interpolation/manifest.json'); stage=run/'02-interpolation'
    spatial_path=ROOT/final['parent']['spatial_manifest'];spatial=load(spatial_path)
    assert spatial['parameters']['model']=='seedvr2_7b_int8_convrot.safetensors'
    assert spatial['parameters']['scale']==spatial['scale']==4
    raw=read_bam(ROOT/a['source']);native,pal,tr=decode_bam(raw)
    carrier=read_bam(ROOT/report['runtime_bam']);padded,ppal,ptr=decode_bam(carrier)
    assert len(native)==len(padded) and np.array_equal(pal,ppal) and tr==ptr
    cycles=cycle_metadata(raw,len(native));assert cycle_metadata(carrier,len(padded))==cycles
    cycle=cycles[0]['frame_indices'];cw,ch=spatial['aligned_canvas_size_x1']
    anchor=[spatial['frames'][0]['canvas_offset_x1'][0]+native[0][1],
            spatial['frames'][0]['canvas_offset_x1'][1]+native[0][2]]
    for idx,((old,cx,cy,_),(new,ncx,ncy,_)) in enumerate(zip(native,padded)):
        old_canvas=np.full((ch,cw),tr,np.uint8);new_canvas=np.full_like(old_canvas,tr)
        x,y=anchor[0]-cx,anchor[1]-cy
        nx,ny=anchor[0]-ncx,anchor[1]-ncy
        assert nx<=x and ny<=y and nx+new.shape[1]>=x+old.shape[1] and ny+new.shape[0]>=y+old.shape[0]
        old_canvas[y:y+old.shape[0],x:x+old.shape[1]]=old
        new_canvas[ny:ny+new.shape[0],nx:nx+new.shape[1]]=new
        assert np.array_equal(old_canvas,new_canvas),(name,idx,'native world pixels changed')
    pack=validate_pack(ROOT/report['pack']);pm=pack.manifest
    assert pm['cycles']==cycles
    tl=pm['timeline'];n=len(cycle)*2
    assert tl['target_fps']==[30,1] and tl['native_fps']==[15,1] and len(tl['timeline_frame_indices'])==n
    assert n*15==len(cycle)*30 and len(final['frames'])==n
    rgba_hashes=set();rgb_hashes=set();duplicates=[];black=[];previous=None;steps=[];contracts=[]
    refs={name,name.lower()}
    for c in a['consumers']:
        if ':vvc:' in c['consumer_key']:
            v=c['consumer_key'].split(':')[-1]
            refs.add((ROOT/'effects/source/vvc'/f'{v}.vvc').read_bytes()[8:16].split(b'\0')[0].decode('ascii'))
    alpha_cache={}
    for phase,backing in enumerate(tl['timeline_frame_indices']):
        f=pm['frames'][backing];ff=final['frames'][phase];g=cycle[phase//2]
        native_indices,cx,cy,_=padded[g];w,h=f['logical_size_x1']
        assert [w,h]==[native_indices.shape[1],native_indices.shape[0]] and f['source_centre_x1']==[cx,cy]
        assert f['physical_size_x4']==[w*4,h*4] and f['sha256']==ff['raw_rgba_x4_sha256']
        data=(pack.root/f['asset']).read_bytes();assert sha(data)==f['sha256']
        image=np.frombuffer(data,np.uint8).reshape(h*4,w*4,4)
        assert np.all(image[:,:,:3]<=image[:,:,3:4])
        x,y=(anchor[0]-cx)*4,(anchor[1]-cy)*4
        canvas=np.zeros((ch*4,cw*4,4),np.uint8);canvas[y:y+h*4,x:x+w*4]=image
        left,right=ff['temporal_source_frames'];t=ff['temporal_fraction']
        for k in {left,right}:
            if k not in alpha_cache:
                with Image.open(spatial_path.parent/spatial['frames'][k]['aligned_rgba_xn']) as im:
                    alpha_cache[k]=np.asarray(im.getchannel('A')).astype(float)
        limit=np.rint(alpha_cache[left]*(1-t)+alpha_cache[right]*t)
        assert np.all(canvas[:,:,3]<=limit),(name,phase,'alpha expands beyond temporal source coverage')
        rgb=canvas[:,:,:3].copy(); rh=sha(canvas.tobytes());bh=sha(rgb.tobytes())
        if rh in rgba_hashes or bh in rgb_hashes: duplicates.append(phase)
        rgba_hashes.add(rh);rgb_hashes.add(bh)
        if not rgb.any():black.append(phase)
        if previous is not None:
            active=np.any(previous>0,axis=2)|np.any(rgb>0,axis=2)
            diff=np.abs(rgb.astype(float)-previous.astype(float))
            steps.append(float(diff[active].mean()) if active.any() else 0)
        previous=rgb
        for ref in sorted(refs):contracts.append(f'{ref}\t{phase//2}\t{w}\t{h}\t{phase}')
    assert not duplicates,(name,'RGBA or visible RGB duplicate',duplicates)
    assert len(rgba_hashes)==len(rgb_hashes)==n
    assert min(steps)>0
    row={'resref':name,'passed':True,'native_slots':len(cycle),'target_phases':n,'unique_rgba':n,'unique_visible_rgb':n,
        'duplicates':[],'black_phases':black,'minimum_adjacent_visible_rgb_difference':min(steps),
        'duration_seconds':len(cycle)/15,'native_palette_pixels_world_position_cycles_preserved':True,
        'runtime_carrier_sha256':sha(carrier),'pack_manifest_sha256':pack.manifest_sha256,
        'raw_bytes':sum(f['bytes'] for f in pack.frames),'case_variants_checked':sorted(refs)}
    return row,contracts


def main():
    rows=[];contracts=[]
    for a in load(ORIGINAL)['assets']:
        row,cs=verify(a);rows.append(row);contracts.extend(cs)
        print(a['resref'],'PASS',row['unique_visible_rgb'],'unique visible images',flush=True)
    assert len(rows)==33
    (BATCH/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
    save(BATCH/'verification.json',{'schema':'bg2-effects-strict-retimed-verification-v1','passed':33,
        'phases':sum(r['target_phases'] for r in rows),'duplicates':0,'assets':rows,
        'runtime_contract_rows':len(contracts),'visual_qa':'pending-user-controlled-game'})


if __name__=='__main__':main()
