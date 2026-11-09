"""SeedVR accepted 15fps -> Apollo8 30fps comparison; never touches the game."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
FF=get_path('topaz_video_ffmpeg',required=True)
ENC=Path(shutil.which('ffmpeg'))
PROBE=ENC.with_name('ffprobe.exe')
MODELS=get_path('topaz_video_models',required=True)
SOURCE=ROOT/'video/restdung/runs/restdung-seedvr-reference-20261109-v1/SeedVR2-RESTDUNG-3B-FP16-LAB-1080p15.mp4'
RUN=ROOT/'video/restdung/runs/restdung-seedvr-apollo30-20261109-v1'
RUN.mkdir(exist_ok=False)
MASTER=RUN/'apollo30-working.mkv'
FINAL=RUN/'SeedVR2-RESTDUNG-3B-FP16-LAB-Apollo8-1080p30.mp4'
env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));env['PATH']=str(FF.parent)+os.pathsep+env.get('PATH','')
before=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
report={'state':'working','parent':SOURCE.relative_to(ROOT).as_posix(),'parent_sha256':before,'qa':'pending-user','installed':False,'interpolation':{'model':'apo-8','fps':30,'slowmo':1,'rdt':-0.01},'commands':[]}

def run(cmd,name):
    cmd=[str(x)for x in cmd];report['commands'].append(cmd)
    (RUN/'run.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print('START',name,flush=True)
    with (RUN/(name+'.log')).open('w')as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,env=env,check=True)
    print('DONE',name,flush=True)

# Match the source's untagged YUV interpretation; use its RGB8 decoded pixels
# for interpolation, then an explicit inverse BT.601 conversion for the preview.
# This avoids applying a new exposure or color correction while comparing FPS.
run([FF,'-hide_banner','-nostdin','-n','-threads','8','-i',SOURCE,'-map','0:v:0','-an','-vf','format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',MASTER],'apollo')
run([ENC,'-hide_banner','-nostdin','-n','-threads','8','-i',MASTER,'-i',SOURCE,'-map','0:v:0','-map','1:a:0','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt601,format=yuv420p','-c:v','libx264','-crf','16','-preset','slow','-fps_mode','passthrough','-color_range','tv','-colorspace','unknown','-color_trc','unknown','-color_primaries','unknown','-c:a','copy','-movflags','+faststart',FINAL],'preview')
p=subprocess.run([str(PROBE),'-v','error','-count_frames','-show_entries','stream=codec_type,codec_name,width,height,nb_read_frames,r_frame_rate:format=duration','-of','json',str(FINAL)],capture_output=True,text=True,check=True)
info=json.loads(p.stdout);v=next(x for x in info['streams']if x['codec_type']=='video')
assert(v['width'],v['height'],v['r_frame_rate'],v['nb_read_frames'])==(1920,1080,'30/1','181'),info
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==before
report.update(state='encoded-awaiting-intermediate-check',output=FINAL.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(FINAL.read_bytes()).hexdigest(),probe=info)
(RUN/'run.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(info),flush=True)
