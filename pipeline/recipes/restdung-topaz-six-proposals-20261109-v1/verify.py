"""Verify actual generated intermediates, independent of the output FPS tag."""
from pathlib import Path
import json
import subprocess
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
WORK=ROOT/'video/restdung/runs/restdung-topaz-six-shared-20261109-v1'
import sys
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
FF=get_path('topaz_video_ffmpeg',required=True)

def sample(name,start,end):
    p=subprocess.run([str(FF),'-v','error','-threads','4','-i',str(WORK/(name+'.mkv')),'-vf',f"select='between(n,{start},{end})',scale=640:360:flags=area,format=gray",'-fps_mode','passthrough','-frames:v',str(end-start+1),'-f','rawvideo','-'],capture_output=True,check=True)
    return np.frombuffer(p.stdout,dtype=np.uint8).reshape((-1,360,640)).astype(np.float32)

report={'method':'Frames33..63 input vs66..126 output; gray640x360, central content only. Original/even anchor error and odd-frame novelty; novelty is not proof of motion quality.','interpolation':{}}
for child,parent in [('T1-Apollo1080','C-U1080-15'),('T2-Apollo1080','C-G1080-15'),('T3-Apollo1080','Csoft-G1080-15'),('T4-Apollo1080','C-Lanczos1080-15'),('C-Apollo720-30','C-proteus720'),('T6-Aion1080','C-G1080-15')]:
    a=sample(parent,33,63)[:,60:316,:]
    b=sample(child,66,126)[:,60:316,:]
    assert len(a)==31 and len(b)==61,(child,a.shape,b.shape)
    odd=b[1::2];prev=b[:-1:2];nxt=b[2::2]
    dp=np.abs(odd-prev).mean(axis=(1,2));dn=np.abs(odd-nxt).mean(axis=(1,2))
    novel=int(((dp>0.005)&(dn>0.005)).sum())
    item={'input_frames':31,'output_frames':61,'novel_odd_frames_of_30':novel,'odd_to_previous_mae':float(dp.mean()),'odd_to_next_mae':float(dn.mean()),'even_anchor_mae':float(np.abs(a-b[::2]).mean()),'odd_to_linear_blend_mae':float(np.abs(odd-(prev+nxt)/2).mean())}
    assert novel>=24,(child,item)
    report['interpolation'][child]=item
    print(child,item,flush=True)
(WORK/'interpolation-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
