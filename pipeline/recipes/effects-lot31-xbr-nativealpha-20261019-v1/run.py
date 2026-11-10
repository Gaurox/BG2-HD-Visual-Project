from common import *
from PIL import Image
from scipy import ndimage as ndi
from types import SimpleNamespace
from fractions import Fraction
from concurrent.futures import ThreadPoolExecutor,as_completed
import numpy as np
import shutil,traceback
from workspace_paths import get_path
from run_creature_sprite_x2 import run_xbr,direct_upscale_contract,XBR_ADAPTER

def spatial(a):
    folder=OUT/'spatial'/a['job_id'];manifest=folder/'manifest.json'
    if manifest.exists():
        m=load(manifest);return {f['frame']:np.array(Image.open(ROOT/f['path']).convert('RGBA')) for f in m['frames']}
    source=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'00-frames-x1';fm=load(source/'manifest.json')
    inputs=[];natives={};order=[];identities={};keys={}
    for f in fm['frames']:
        rgba=np.array(Image.open(source/'rgba'/f['file']).convert('RGBA'));k=f['frame'];natives[k]=rgba;fg=rgba[:,:,3]>0
        rgb=rgba[:,:,:3].copy()
        if fg.any():rgb=rgb[tuple(ndi.distance_transform_edt(~fg,return_distances=False,return_indices=True))]
        else:rgb[:]=0
        filled=np.dstack((rgb,np.full(fg.shape,255,np.uint8)));key=sha(filled.tobytes()+str(filled.shape).encode());keys[k]=key
        if key not in identities:
            identities[key]=len(inputs);order.append(key);inputs.append(SimpleNamespace(width=rgba.shape[1],height=rgba.shape[0],rgba=filled.tobytes()))
    tool=get_path('mmpx_scalepix',required=True);outputs=run_xbr(inputs,tool,shutil.which('node'),direct_upscale_contract(4));frames=[];images={};folder.mkdir(parents=True,exist_ok=True)
    for k,rgba in natives.items():
        w,h,b=outputs[identities[keys[k]]];up=np.frombuffer(b,np.uint8).reshape(h,w,4).copy();alpha=rgba[:,:,3].repeat(4,0).repeat(4,1);assert up.shape[:2]==alpha.shape
        up[:,:,3]=alpha;images[k]=up;p=folder/f'frame_{k:03d}.png';Image.fromarray(up).save(p,compress_level=2)
        frames.append({'frame':k,'path':p.relative_to(ROOT).as_posix(),'sha256':workflow.sha256_file(p)})
    save(manifest,{'algorithm':'XBR/xbr4X','scale':4,'blend_colors':False,'mask':'native nearest4, no mask retouch',
        'source':evidence(source/'manifest.json'),'palette':evidence(ROOT/a['palette_file']),
        'tool':{'path':'config://mmpx_scalepix','sha256':workflow.sha256_file(tool),'bytes':tool.stat().st_size},'adapter':evidence(XBR_ADAPTER),'input_frames':len(natives),'distinct_rgb_inputs':len(inputs),'frames':frames})
    return images

def produce(a):
    file=OUT/'results'/f'{a["job_id"]}.json'
    if file.exists():return
    parent_file=PREVIOUS/'results'/file.name;p=load(parent_file);r={k:v for k,v in p.items() if k not in ('frames','profiles','actions')};records=[];profiles=[];maximum=0
    stage,m,sp,anchor=previous.parent(a);is_xbr=a['ordinal']<=6
    if is_xbr:sources=spatial(a)
    cw,ch=sp['aligned_canvas_size_x1'];pad=previous.PAD
    plan=SimpleNamespace(interpolation_root=OUT/'apollo'/a['job_id'],tvai_ffmpeg=previous.interpolation.DEFAULT_TVAI_FFMPEG,tvai_model_dir=previous.interpolation.DEFAULT_TVAI_MODEL_DIR)
    for oldprofile,timing in zip(p['profiles'],m['timing']['cycles'],strict=True):
        assert oldprofile['id']==timing['id'];oldframes=[f for f in p['frames'] if f['profile']==oldprofile['id']]
        files=previous.base.apollo(plan,timing,sources) if is_xbr else None
        after=[]
        for phase,(oldf,original_index) in enumerate(zip(oldframes,timing['timeline_frame_indices'],strict=True)):
            original=m['frames'][original_index];left,right=original['temporal_source_frames'];fraction=original['temporal_fraction']
            if is_xbr:
                if fraction==0:rgb=sources[left][:,:,:3].copy()
                else:
                    with Image.open(files[phase]) as im:rgb=np.array(im.convert('RGB'))
                alpha=np.rint(sources[left][:,:,3].astype(np.float32)*(1-fraction)+sources[right][:,:,3].astype(np.float32)*fraction).astype(np.uint8)
                normal=np.pad(np.dstack((rgb,alpha)),((pad,pad),(pad,pad),(0,0)));normal[normal[:,:,3]==0]=0
                prem=normal.copy();prem[:,:,:3]=np.rint(normal[:,:,:3].astype(float)*normal[:,:,3:4]/255).astype(np.uint8)
            else:
                w,h=p['size_x4'];old=np.fromfile(ROOT/oldf['straight']['path'],np.uint8).reshape(h,w,4)
                normal,prem,error=previous.black_neutral(old);maximum=max(maximum,error)
            assert not normal[normal[:,:,3]==0].any();assert not normal[[0,-1]].any() and not normal[:,[0,-1]].any()
            after.append(image(normal));records.append({'frame':len(records),'profile':timing['id'],'phase':phase,
                'temporal_source_frames':[left,right],'temporal_fraction':fraction,'before':old_image(oldf['after']),
                'after':after[-1],'straight':raw(normal),'premultiplied':raw(prem)})
        profile={**oldprofile,'native':[old_image(s) for s in oldprofile['native']],
            'before':[old_image(s) for s in oldprofile['after']],'after':after}
        assert sum(Fraction(*d) for d in profile['phase_durations_rational'])==Fraction(*profile['duration_rational']);profiles.append(profile)
    r.update(actions={'xbr_x4':is_xbr,'native_default_mask':is_xbr,'smooth':not is_xbr,'black_neutral':not is_xbr},
        parent_correction=evidence(parent_file),profiles=profiles,frames=records,black_premultiplied_flux_max_error=maximum,
        qa='pending-user-preview',installed=False)
    save(file,r);print('DONE',a['job_id'],len(records),'phases',flush=True)

def main():
    work=sorted(jobs(),key=lambda a:(not a['primary'],a['ordinal']));state={};lock=threading.Lock()
    save(OUT/'plan.json',{'parent':evidence(PREVIOUS/'result.json'),'xbr_ordinals':[1,2,3,4,5,6],'black_ordinals':[22,27],
        'assets':8,'contexts':len(work),'xbr_contexts':sum(a['ordinal']<=6 for a in work),'parent_jobs':work,
        'timing':'Inherited30FPS profiles/durations and duplicate condensation; alpha native nearest4 linearly mixed, no curve/blur/inset for01..06.'})
    def worker(a):
        with lock:state[a['job_id']]={'state':'running'};save(OUT/'progress.json',state)
        try:produce(a);value={'state':'completed'}
        except Exception as error:traceback.print_exc();value={'state':'failed','error':repr(error)}
        with lock:state[a['job_id']]=value;save(OUT/'progress.json',state)
        return value
    with ThreadPoolExecutor(max_workers=2) as pool:results=[f.result() for f in as_completed([pool.submit(worker,a) for a in work])]
    assert all(v['state']=='completed' for v in results),results
    print('Completed8 effects /39 palette contexts',flush=True)

if __name__=='__main__':main()
