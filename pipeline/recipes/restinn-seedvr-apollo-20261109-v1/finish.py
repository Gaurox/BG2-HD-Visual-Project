"""Finalize local RESTINN SeedVR+Apollo previews; no game or release writes."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
RUN=ROOT/'video/restinn/runs/restinn-seedvr-apollo-20261109-v1'
NATIVE=ROOT/'video/restinn/restinn.wbm'
ENC=Path(shutil.which('ffmpeg'));PROBE=ENC.with_name('ffprobe.exe');TOPAZ=get_path('topaz_video_ffmpeg',required=True)
MODELS=get_path('topaz_video_models',required=True)
SEED=RUN/'RESTINN-SeedVR2-3B-FP16-LAB-1080p15.mp4'
FINAL=RUN/'RESTINN-SeedVR2-3B-FP16-LAB-Apollo8-1080p30.mp4'
MASTER=RUN/'apollo-working.mkv'
env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));env['PATH']=str(TOPAZ.parent)+os.pathsep+env.get('PATH','')
report={'asset_key':'movie:default:RESTINN','state':'working','qa':'pending-user','installed':False,'seedvr_prompt_id':'11649285-9251-4cef-ad69-168920135b1e','workflow':'seedvr-workflow.api.json','commands':[]}
def save():(RUN/'production.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
def command(cmd,name):
    cmd=[str(x)for x in cmd];report['commands'].append(cmd);save();print('START',name,flush=True)
    with (RUN/(name+'.log')).open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
    print('DONE',name,flush=True)
def probe(f):
    r=subprocess.run([str(PROBE),'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames:format=duration','-of','json',str(f)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)
raw=list((RUN/'comfy-output').rglob('*.mp4'));assert len(raw)==1,raw
report['comfy_output']=str(raw[0].relative_to(ROOT));report['comfy_output_sha256']=hashlib.sha256(raw[0].read_bytes()).hexdigest()
command([ENC,'-hide_banner','-nostdin','-n','-i',raw[0],'-i',NATIVE,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-movflags','+faststart',SEED],'seed15-audio')
p=probe(SEED);v=p['streams'][0];assert(v['width'],v['height'],v['r_frame_rate'],v['nb_read_frames'])==(1920,1080,'15/1','90'),p
command([TOPAZ,'-hide_banner','-nostdin','-n','-threads','8','-i',SEED,'-map','0:v:0','-an','-vf','format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',MASTER],'apollo30')
command([ENC,'-hide_banner','-nostdin','-n','-threads','8','-i',MASTER,'-i',SEED,'-map','0:v:0','-map','1:a:0','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt601,format=yuv420p','-c:v','libx264','-crf','16','-preset','slow','-fps_mode','passthrough','-color_range','tv','-colorspace','unknown','-color_trc','unknown','-color_primaries','unknown','-c:a','copy','-movflags','+faststart',FINAL],'preview30')
p30=probe(FINAL);v=p30['streams'][0];assert(v['width'],v['height'],v['r_frame_rate'],v['nb_read_frames'])==(1920,1080,'30/1','179'),p30
source_preview=ROOT/'video/restinn/source-preview-720p15.mp4'
command([ENC,'-hide_banner','-nostdin','-n','-i',NATIVE,'-c:v','libx264','-crf','16','-preset','slow','-pix_fmt','yuv420p','-fps_mode','passthrough','-c:a','aac','-b:a','192k','-movflags','+faststart',source_preview],'source-preview')
def samples(f,a,b):
    r=subprocess.run([str(ENC),'-v','error','-i',str(f),'-vf',f"select='between(n,{a},{b})',scale=640:360:flags=area,format=gray",'-frames:v',str(b-a+1),'-fps_mode','passthrough','-f','rawvideo','-'],capture_output=True,check=True)
    return np.frombuffer(r.stdout,dtype=np.uint8).reshape(-1,360,640).astype(float)[:,60:316,:]
a=samples(SEED,33,63);b=samples(FINAL,66,126);dprev=np.abs(b[1::2]-b[:-1:2]).mean(axis=(1,2));dnext=np.abs(b[1::2]-b[2::2]).mean(axis=(1,2))
novel=int(((dprev>.005)&(dnext>.005)).sum())
audio=[]
for f in [SEED,FINAL]:
    r=subprocess.run([str(ENC),'-v','error','-i',str(f),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-'],capture_output=True,text=True,check=True);audio.append(r.stdout.strip())
assert audio[0]==audio[1]
report.update(state='verified-comparison-ready',outputs={'seed15':SEED.relative_to(ROOT).as_posix(),'apollo30':FINAL.relative_to(ROOT).as_posix(),'source_preview':source_preview.relative_to(ROOT).as_posix()},probe15=p,probe30=p30,interpolation_check={'central_odd_frames':30,'novel_odd_frames':novel,'even_anchor_mae':float(np.abs(a-b[::2]).mean()),'audio_stream_identical':True,'audio_hash':audio[0]})
assert novel>0,'No generated changing frames detected; inspect before adding comparator'
save();master=MASTER.resolve();assert master.parent==RUN.resolve() and master.name=='apollo-working.mkv';master.unlink();print(json.dumps(report['interpolation_check']),flush=True)
