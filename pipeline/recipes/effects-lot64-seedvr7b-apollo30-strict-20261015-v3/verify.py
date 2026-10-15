"""Independent decode of each output, source carrier, timing and native contract."""
import argparse
import collections
from fractions import Fraction
import subprocess
import time

from temporal import ROOT,BATCH,load,save,digest,rel
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata
from compose_effect_runtime_packs import validate_pack
import numpy as np
from PIL import Image


def verify(a):
    name=a['resref'];report=load(BATCH/'checks'/(name+'.json'))
    run=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run'];stage=run/'02-interpolation'
    m=load(stage/'manifest.json');sp=ROOT/m['parent']['spatial_manifest'];s=load(sp)
    assert s['parameters']['model']=='seedvr2_7b_int8_convrot.safetensors'
    assert s['parameters']['scale']==s['scale']==m['scale']==4
    assert s['parameters']['color_correction_method']=='lab'
    original=read_bam(ROOT/a['source']);old,pal,tr=decode_bam(original)
    carrier=read_bam(ROOT/m['runtime_carrier']['path']);new,npal,ntr=decode_bam(carrier)
    assert len(old)==len(new) and np.array_equal(pal,npal) and tr==ntr
    cycles=cycle_metadata(original,len(old));assert cycles==cycle_metadata(carrier,len(new))==a['native_cycles']
    cw,ch=s['aligned_canvas_size_x1']
    anchor=[s['frames'][0]['canvas_offset_x1'][0]+old[0][1],s['frames'][0]['canvas_offset_x1'][1]+old[0][2]]
    native_pose_hashes=[]
    for (oi,cx,cy,_),(ni,nx,ny,_) in zip(old,new):
        before=np.full((ch,cw),tr,np.uint8);after=np.full_like(before,tr)
        x,y=anchor[0]-cx,anchor[1]-cy;xx,yy=anchor[0]-nx,anchor[1]-ny
        assert xx<=x and yy<=y and xx+ni.shape[1]>=x+oi.shape[1] and yy+ni.shape[0]>=y+oi.shape[0]
        before[y:y+oi.shape[0],x:x+oi.shape[1]]=oi;after[yy:yy+ni.shape[0],xx:xx+ni.shape[1]]=ni
        assert np.array_equal(before,after),(name,'native carrier changed pixels')
        native_rgba=np.dstack((pal[before],(before!=tr).astype(np.uint8)*255))
        native_rgba[native_rgba[:,:,3]==0]=0
        native_pose_hashes.append(digest(native_rgba.tobytes()))
    pm=validate_pack(ROOT/a['pack']);assert pm.manifest_sha256==report['pack_manifest_sha256']
    assert pm.manifest['cycles']==cycles
    by_hash={(f['sha256'],tuple(f['physical_size_x4'])):i for i,f in enumerate(pm.frames)}
    alpha={};rows=[];contracts=[];frame_backings={}
    for v in m['timing']['cycles']:
        slots=cycles[v['cycle']]['frame_indices'];phases=v['timeline_frame_indices']
        assert len({native_pose_hashes[k] for k in v['keyframes']})==len(v['keyframes']),(name,v['id'],'repeated native input key')
        assert len(phases)==2*len(slots)==v['phase_count']
        assert Fraction(len(phases),30)==Fraction(len(slots),15)
        rgba_hash=[];rgb_hash=[];empty=[]
        for phase,idx in enumerate(phases):
            f=m['frames'][idx];g=slots[phase//2];ni,cx,cy,_=new[g]
            assert f['geometry_source_frame']==g and f['centre_x1']==[cx,cy]
            assert f['logical_size_x1']==[ni.shape[1],ni.shape[0]]
            assert f['physical_size_x4']==[ni.shape[1]*4,ni.shape[0]*4]
            raw=(stage/f['raw_rgba_x4']).read_bytes();assert digest(raw)==f['raw_rgba_x4_sha256']
            h,w=ni.shape;crop=np.frombuffer(raw,np.uint8).reshape(h*4,w*4,4)
            assert np.all(crop[:,:,:3]<=crop[:,:,3:4])
            canvas=np.zeros((ch*4,cw*4,4),np.uint8);x,y=(anchor[0]-cx)*4,(anchor[1]-cy)*4
            canvas[y:y+h*4,x:x+w*4]=crop
            left,right=f['temporal_source_frames'];t=f['temporal_fraction']
            for k in (left,right):
                if k not in alpha:
                    with Image.open(sp.parent/s['frames'][k]['aligned_rgba_xn']) as im:alpha[k]=np.asarray(im.getchannel('A')).astype(np.float32)
            limit=np.rint(alpha[left]*(1-t)+alpha[right]*t)
            assert np.all(canvas[:,:,3]<=limit)
            rh=digest(canvas.tobytes());bh=digest(canvas[:,:,:3].tobytes())
            assert rh==f['anchored_rgba_sha256'] and bh==f['anchored_rgb_sha256']
            rgba_hash.append(rh);rgb_hash.append(bh)
            if not canvas[:,:,:3].any():empty.append(phase)
            frame_backings[idx]=by_hash[(f['raw_rgba_x4_sha256'],tuple(f['physical_size_x4']))]
        duplicates=[p for p in range(1,len(rgb_hash)) if rgb_hash[p]==rgb_hash[p-1]]
        seam=bool(v['loop_closed'] and rgb_hash[-1]==rgb_hash[0])
        if not v['constant_native_cycle']:
            assert not duplicates and not seam,(name,v['id'],duplicates,seam)
            assert len(empty)<=1
            assert len(set(rgb_hash))==len(rgb_hash),(name,v['id'],'nonconsecutive RGB duplicate')
            assert len(set(rgba_hash))==len(rgba_hash),(name,v['id'],'nonconsecutive RGBA duplicate')
        rows.append({'profile':v['id'],'cycle':v['cycle'],'closed':v['loop_closed'],'source_slots':len(slots),
                     'output_phases':len(phases),'duration':[len(slots),15],'unique_rgb':len(set(rgb_hash)),
                     'nonconsecutive_pose_revisits':len(rgb_hash)-len(set(rgb_hash))-len(duplicates),
                     'visible_adjacent_duplicates':0 if v['constant_native_cycle'] else len(duplicates),
                     'constant_native_cycle':v['constant_native_cycle'],'transparent_native_cycle':v['transparent_native_cycle'],
                     'empty_phases':empty,'loop_seam_duplicate':seam and not v['constant_native_cycle']})
    tl=pm.manifest['timeline']
    for sequence,profile in enumerate(tl['cycle_profiles']):
        v=next(v for v in m['timing']['cycles'] if v['id']==profile)
        native=tl['native_frame_indices_by_cycle'][sequence];timeline=tl['timeline_frame_indices_by_cycle'][sequence]
        assert len(native)==len(v['native_slots']) and len(timeline)==2*len(native)
        assert timeline==[frame_backings[i] for i in v['timeline_frame_indices']]
        for phase,idx in enumerate(v['timeline_frame_indices']):
            f=m['frames'][idx];w,h=f['logical_size_x1']
            for ref in (name,name.lower()):
                contracts.append(f'{ref}\t{phase//2}\t{w}\t{h}\t{phase}\t{sequence}\t{native[phase//2]}\t{timeline[phase]}')
    result={'resref':name,'passed':True,'native_cycles':len(cycles),'cycle_mode_variants':len(rows),
            'phases':len(m['frames']),'cycles':rows,'native_pixels_palette_world_geometry_preserved':True,
            'source_model':'seedvr2_7b_int8_convrot.safetensors','scale':4,'target_fps':[30,1],
            'filter':'NEAREST','pack_manifest_sha256':pm.manifest_sha256,'runtime_contract_rows':len(contracts),
            'native_input_keys_unique_before_apollo':True,
            'raw_bytes':sum(f['bytes'] for f in pm.frames),'visual_qa':'pending-user-review','installed':False}
    output=BATCH/'verification'/f'{name}.json';save(output,result)
    contract_path=BATCH/'contracts'/f'{name}.tsv';contract_path.parent.mkdir(exist_ok=True)
    contract_path.write_text('\n'.join(contracts)+'\n',encoding='ascii')
    print(name,'independent verification PASS',len(rows),'profiles',len(m['frames']),'phases',flush=True)
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--resref',action='append');p.add_argument('--wait',action='store_true');args=p.parse_args()
    assets=[a for a in load(BATCH/'batch.json')['assets'] if not args.resref or a['resref'] in args.resref]
    failures=[];results=[]
    for a in assets:
        proof=BATCH/'verification'/f'{a["resref"]}.json'
        if proof.exists():results.append(load(proof));continue
        if args.wait:
            while not (BATCH/'checks'/f'{a["resref"]}.json').exists():
                progress=load(BATCH/'temporal-progress.json') if (BATCH/'temporal-progress.json').exists() else {}
                if progress.get(a['resref'],{}).get('state')=='failed':break
                time.sleep(3)
        try:results.append(verify(a))
        except Exception as exc:
            failures.append({'resref':a['resref'],'error':repr(exc)});print('VERIFY FAILED',a['resref'],repr(exc),flush=True)
    save(BATCH/'verification.json',{'schema':'bg2-effects-multicycle-verification-v1','passed':len(results),'failures':failures,
         'phases':sum(r['phases'] for r in results),'cycle_mode_variants':sum(r['cycle_mode_variants'] for r in results),
         'assets':results,'visual_qa':'pending-user-review','installed':False})
    return int(bool(failures))


if __name__=='__main__':raise SystemExit(main())
