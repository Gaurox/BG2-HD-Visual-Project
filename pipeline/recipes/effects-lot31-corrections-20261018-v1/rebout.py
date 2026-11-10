"""ReboutCX on exact native palette inputs; single persistent model, no registries."""
from prepare import ROOT,BASE,OUT,load,save
import sys,hashlib
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
from workspace_paths import get_path
from reboutcx_batch import load_model,infer_x4_box_x2
import effect_workflow as workflow

def main():
    model=get_path('reboutcx_model',required=True);descriptor,versions=load_model(model,device='cuda:0',fp16=True)
    sha=workflow.sha256_file(model);cache={};progress={}
    jobs=[a for a in load(OUT/'plan.json')['jobs'] if a['rebout']]
    for i,a in enumerate(jobs,1):
        key=a['job_id'];folder=OUT/'reboutcx'/key;manifest=folder/'manifest.json'
        print('ReboutCX',i,'/',len(jobs),key,flush=True)
        if manifest.exists():progress[key]='completed';continue
        parent=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']
        src=parent/'00-frames-x1';fm=load(src/'manifest.json');folder.mkdir(parents=True,exist_ok=True)
        records=[]
        for f in fm['frames']:
            k=f['frame'];target=folder/f'frame_{k:03d}.png'
            if not target.exists():
                rgba=np.array(Image.open(src/'rgba'/f['file']).convert('RGBA'));mask=rgba[:,:,3]>0
                if mask.any():
                    near=distance_transform_edt(~mask,return_distances=False,return_indices=True)
                    rgb=rgba[:,:,:3][tuple(near)].copy()
                    sig=hashlib.sha256(rgb.tobytes()+str(rgb.shape).encode()).hexdigest()
                    if sig not in cache:cache[sig]=infer_x4_box_x2(descriptor,rgb,fp16=True)[0]
                    up=cache[sig]
                else:up=np.zeros((rgba.shape[0]*4,rgba.shape[1]*4,3),np.uint8)
                alpha=rgba[:,:,3].repeat(4,0).repeat(4,1)
                result=np.dstack((up,alpha));result[alpha==0]=0
                Image.fromarray(result).save(target,compress_level=3)
            records.append({'frame':k,'path':target.relative_to(ROOT).as_posix(),'sha256':workflow.sha256_file(target)})
        save(manifest,{'job_id':key,'model':str(model),'model_sha256':sha,'scale':4,'fp16':True,'versions':versions,
            'native_palette_input':a['palette_file'],'source_export':str((src/'manifest.json').relative_to(ROOT)),
            'source_export_sha256':workflow.sha256_file(src/'manifest.json'),'aligned_canvas_size_x1':fm['aligned_canvas_size'],
            'frames':records,'alpha':'original source nearest4; smoothing applied separately'})
        progress[key]='completed';save(OUT/'rebout-progress.json',progress)
    print('ReboutCX complete:',len(jobs),'contexts',flush=True)

if __name__=='__main__':main()
