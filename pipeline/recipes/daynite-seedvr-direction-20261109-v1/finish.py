"""Finish controlled forward/reverse SeedVR trials in normal playback order."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import hashlib
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
DIRECTION=sys.argv[1];assert DIRECTION in ('forward','reverse')
RUN=ROOT/'video/daynite/runs/daynite-seedvr-direction-20261109-v1'
SOURCE=ROOT/'video/daynite/daynite.wbm'
ENC=Path(shutil.which('ffmpeg'));PROBE=ENC.with_name('ffprobe.exe')
TOPAZ=get_path('topaz_video_ffmpeg',required=True);MODELS=get_path('topaz_video_models',required=True)
env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));env['PATH']=str(TOPAZ.parent)+os.pathsep+env.get('PATH','')
stem='DAYNITE-SeedVR2-'+('DIRECT-temoin'if DIRECTION=='forward'else'INVERSE-remis-endroit')
SEED=RUN/(stem+'-1080p15.mp4');FINAL=RUN/(stem+'-Apollo8-1080p30.mp4');MASTER=RUN/(DIRECTION+'-apollo-working.mkv')
REPORT=RUN/(DIRECTION+'-production.json')
raw=list((RUN/(DIRECTION+'-output')).rglob('*.mov'));assert len(raw)==1,raw
tags=['-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1']
report={'direction':DIRECTION,'playback':'forward-normal','state':'working','qa':'pending-user','installed':False,'workflow':f'{DIRECTION}-workflow.api.json','comfy_output':raw[0].relative_to(ROOT).as_posix(),'raw_sha256':hashlib.sha256(raw[0].read_bytes()).hexdigest(),'commands':[]}
def save():REPORT.write_text(json.dumps(report,indent=2),encoding='utf-8')
def command(cmd,label):
    cmd=[str(x)for x in cmd];report['commands'].append(cmd);save();print('START',DIRECTION,label,flush=True)
    with (RUN/(DIRECTION+'-'+label+'.log')).open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
    print('DONE',DIRECTION,label,flush=True)
def probe(f):
    r=subprocess.run([str(PROBE),'-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,r_frame_rate,nb_read_frames,color_space:format=duration','-of','json',str(f)],capture_output=True,text=True,check=True);return json.loads(r.stdout)
vf=('reverse,'if DIRECTION=='reverse'else'')+'setpts=N/(15*TB),scale=out_color_matrix=bt709:out_range=tv,format=yuv420p'
command([ENC,'-hide_banner','-nostdin','-n','-threads','8','-i',raw[0],'-i',SOURCE,'-map','0:v:0','-map','1:a:0','-vf',vf,'-c:v','libx264','-crf','16','-preset','slow','-fps_mode','passthrough','-c:a','aac','-b:a','192k',*tags,'-movflags','+faststart',SEED],'restore15')
p15=probe(SEED);v=p15['streams'][0];assert(v['width'],v['height'],v['r_frame_rate'],v['nb_read_frames'])==(1920,1080,'15/1','150'),p15
command([TOPAZ,'-hide_banner','-nostdin','-n','-threads','8','-i',SEED,'-map','0:v:0','-an','-vf','format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',MASTER],'apollo30')
command([ENC,'-hide_banner','-nostdin','-n','-threads','8','-i',MASTER,'-i',SEED,'-map','0:v:0','-map','1:a:0','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','16','-preset','slow','-fps_mode','passthrough','-c:a','copy',*tags,'-movflags','+faststart',FINAL],'preview30')
p30=probe(FINAL);v=p30['streams'][0];assert(v['width'],v['height'],v['r_frame_rate'],v['nb_read_frames'])==(1920,1080,'30/1','299'),p30
def frames(f,start,end):
    r=subprocess.run([str(ENC),'-v','error','-i',str(f),'-vf',f"select='between(n,{start},{end})',scale=320:180:flags=area,format=gray",'-frames:v',str(end-start+1),'-fps_mode','passthrough','-f','rawvideo','-'],capture_output=True,check=True)
    return np.frombuffer(r.stdout,dtype=np.uint8).reshape(-1,180,320).astype(float)[:,30:158,:]
a=frames(SEED,0,149);native=frames(SOURCE,0,149);b=frames(FINAL,66,126)
correlation=float(np.corrcoef(a.mean(axis=(1,2)),native.mean(axis=(1,2)))[0,1]);report['brightness_direction_warning']=not bool(np.isfinite(correlation)and correlation>.9)
odd=b[1::2];dp=np.abs(odd-b[:-1:2]).mean(axis=(1,2));dn=np.abs(odd-b[2::2]).mean(axis=(1,2));novel=int(((dp>.005)&(dn>.005)).sum());assert novel==30,novel
ah=[]
for f in [SEED,FINAL]:
    r=subprocess.run([str(ENC),'-v','error','-i',str(f),'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-'],capture_output=True,text=True,check=True);ah.append(r.stdout.strip())
assert ah[0]==ah[1]
report.update(state='verified-comparison-ready',outputs={'seed15':SEED.relative_to(ROOT).as_posix(),'apollo30':FINAL.relative_to(ROOT).as_posix()},sha256={'seed15':hashlib.sha256(SEED.read_bytes()).hexdigest(),'apollo30':hashlib.sha256(FINAL.read_bytes()).hexdigest()},probe15=p15,probe30=p30,checks={'forward_playback_brightness_correlation':correlation,'novel_central_frames':novel,'audio15_30_payload_identical':True,'audio_hash':ah[0]});save()
master=MASTER.resolve();assert master.parent==RUN.resolve() and master.name==DIRECTION+'-apollo-working.mkv';master.unlink();print('VERIFIED',DIRECTION,report['checks'],flush=True)
