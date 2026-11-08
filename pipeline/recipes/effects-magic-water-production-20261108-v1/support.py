"""Native-clock interpolation and bounded contour fade for lot50."""
import json
import os
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image
from scipy import ndimage as ndi


def sources(slots,identities,closed):
    keys=[];ranks=[]
    for k in slots:
        if not keys or identities[k]!=identities[keys[-1]]:keys.append(k)
        ranks.append(len(keys)-1)
    phases=[];samples=[]
    for phase in range(len(slots)*2):
        slot=phase//2;nxt=(slot+1)%len(slots) if closed else min(slot+1,len(slots)-1)
        left,right=slots[slot],slots[nxt]
        t=.5 if phase%2 and identities[left]!=identities[right] else 0.
        phases.append((left,right,t));samples.append(2*ranks[slot]+1 if t else None)
    return keys,phases,samples


def apollo(plan,v,images,interpolation,save):
    batchroot=Path(__file__).resolve().parents[3]/'effects/batches/lot50-magic-water-production-20261108-v1'
    if (batchroot/'gpu-paused.json').exists():
        permit=batchroot/'gpu-one-test.json';allowed=json.loads(permit.read_text()) if permit.exists() else {}
        if allowed.get('state')!='running' or allowed.get('resref')!=plan.resref:
            raise RuntimeError('GPU paused by user; no Apollo except authorized one-asset test.')
    folder=plan.interpolation_root/v['id'];inputs=folder/'input-rgb';outputs=folder/'apollo-raw'
    for p in (inputs,outputs):p.mkdir(parents=True,exist_ok=True)
    keys=v['keyframes']
    if len(keys)<2:return None
    size=images[keys[0]].shape[:2];h,w=size
    pw=max(128,(w+31)//32*32);ph=max(128,(h+31)//32*32)
    extended=keys+(keys[:2] if v['loop_closed'] else [keys[-1]])
    for i,k in enumerate(extended):
        p=inputs/f'in_{i:03d}.png'
        if not p.exists():
            im=Image.new('RGB',(pw,ph));im.paste(Image.fromarray(images[k][:,:,:3]),(0,0));im.save(p)
    command=[str(plan.tvai_ffmpeg),'-hide_banner','-loglevel','error','-y','-framerate','15','-i',str(inputs/'in_%03d.png'),
             '-vf','tvai_fi=model=apo-8:fps=30:rdt=-0.01:device=-2','-pix_fmt','rgb24',str(outputs/'out_%04d.png')]
    if not (folder/'completed.json').exists():
        save(folder/'apollo-command.json',{'command':command,'input_fps':[15,1],'source_size':[w,h],
                                          'padded_size':[pw,ph],'keys_occurrences':keys,'samples_by_phase':v['apollo_samples']})
        env=dict(os.environ,TVAI_MODEL_DIR=str(plan.tvai_model_dir),TVAI_MODEL_DATA_DIR=str(plan.tvai_model_dir))
        with (folder/'apollo.log').open('w',encoding='utf-8') as log:subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        save(folder/'completed.json',{'passed':True})
    files=interpolation.parse_numbered_pngs(outputs)
    samples=[s for s in v['apollo_samples'] if s is not None]
    assert not samples or max(samples)<len(files),(v['id'],len(files),samples)
    return files


def feather_factor(alpha,radius):
    if not radius:return np.ones(alpha.shape,np.float32)
    from derive_animation_visual_treatment import smoothstep
    inside=alpha>0;dist=ndi.distance_transform_edt(np.pad(inside,1))[1:-1,1:-1]
    labels,n=ndi.label(inside,np.ones((3,3)))
    maxima=ndi.maximum(dist,labels,index=np.arange(n+1))
    local=np.minimum(radius,np.maximum((maxima[labels]-1)*.5,1))
    factor=smoothstep((dist-1)/local)
    factor[maxima[labels]<=4]=1
    factor[~inside]=0
    return factor


def neutral(straight):
    a=straight[:,:,3].astype(float);rgb=straight[:,:,:3].astype(float)
    energy=np.rint(rgb*a[:,:,None]/255).astype(np.uint8)
    alpha=np.rint(a*rgb.max(2)/255).astype(np.uint8)
    out=np.zeros_like(straight);out[:,:,3]=alpha;mask=alpha>0
    out[:,:,:3][mask]=np.clip(np.rint(energy[mask].astype(float)*255/alpha[mask,None]),0,255).astype(np.uint8)
    reconstructed=np.rint(out[:,:,:3].astype(float)*alpha[:,:,None]/255).astype(np.uint8)
    assert np.max(np.abs(reconstructed.astype(np.int16)-energy.astype(np.int16)))<=1
    return out
