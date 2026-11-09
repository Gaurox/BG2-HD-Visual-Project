"""Produce RESTDUNG T1..T6; shared lossless RGB stages, no release writes."""
from pathlib import Path
import json
import os
import subprocess
import shutil
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

FF = get_path('topaz_video_ffmpeg', required=True)
PROBE = FF.with_name('ffprobe.exe')
ENCODER = Path(shutil.which('ffmpeg') or '')
assert ENCODER.is_file() and ENCODER != FF, 'Standard FFmpeg with libx264 required on PATH'
MODELS = get_path('topaz_video_models', required=True)
ASSET = ROOT / 'video/restdung'
SOURCE = ASSET / 'restdung.wbm'
WORK = ASSET / 'runs/restdung-topaz-six-shared-20261109-v1'
WORK.mkdir(exist_ok=True)
REPORT = WORK / 'production.json'
state = json.loads(REPORT.read_text()) if REPORT.exists() else {'state': 'working', 'qa': 'pending', 'stages': {}, 'finals': {}}
env = os.environ.copy()
env.update(TVAI_MODEL_DIR=str(MODELS), TVAI_MODEL_DATA_DIR=str(MODELS))
env['PATH'] = str(FF.parent) + os.pathsep + env.get('PATH', '')
RGB_TAGS = ['-color_range','pc','-colorspace','rgb','-color_primaries','bt709','-color_trc','iec61966-2-1']
YUV_TAGS = ['-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','iec61966-2-1']
COMMON = ':grain=0:estimate=0:device=0:vram=0.8:instances=0:download=0'
C = 'tvai_up=model=prob-4:scale=1:w=1280:h=720:preblur=-0.03:noise=0.02:details=0:halo=0.03:blur=0:compression=0.20:blend=0.25'+COMMON
CS = 'tvai_up=model=prob-4:scale=1:w=1280:h=720:preblur=-0.03:noise=0.01:details=0:halo=0.03:blur=0:compression=0.12:blend=0.45'+COMMON
U = 'tvai_up=model=prob-4:scale=2:w=2560:h=1440:preblur=-0.03:noise=0:details=0.12:halo=0.05:blur=0.06:compression=0.15:blend=0.20'+COMMON+',scale=1920:1080:flags=lanczos'
G = 'tvai_up=model=gcg-5:scale=2:w=2560:h=1440'+COMMON+',scale=1920:1080:flags=lanczos'

def save():
    REPORT.write_text(json.dumps(state, indent=2), encoding='utf-8')

def probe(path):
    r = subprocess.run([str(PROBE),'-v','error','-threads','8','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,r_frame_rate,color_range,color_space,pix_fmt:format=duration','-of','json',str(path)],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)

def execute(cmd, log):
    cmd = [str(x) for x in cmd]
    start = time.monotonic()
    with log.open('w',encoding='utf-8') as f:
        p = subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
    if p.returncode:
        print(log.read_text(encoding='utf-8', errors='replace')[-4000:], flush=True)
        raise RuntimeError(f'FFmpeg failed ({p.returncode}): {log}')
    return round(time.monotonic()-start,2)

def stage(name, parent, filt, width=1920, height=1080, frames=91, fps=15):
    dest = WORK / (name+'.mkv')
    if name in state['stages'] and state['stages'][name].get('state') == 'verified' and dest.exists():
        print('REUSE',name,flush=True)
        return dest
    if dest.exists():
        raise RuntimeError(f'Unverified output exists; use a new stage name: {dest}')
    # RGB FFV1 avoids lossy or range-changing YUV round trips between AI passes.
    cmd = [FF,'-hide_banner','-nostdin','-n','-threads','8','-i',parent,'-map','0:v:0','-an','-vf',filt+',format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough',*RGB_TAGS,dest]
    state['stages'][name]={'state':'running','parent':str(parent.relative_to(ROOT)), 'command':[str(x)for x in cmd]}
    save();print('START',name,flush=True)
    elapsed=execute(cmd,WORK/(name+'.log'))
    info=probe(dest);s=info['streams'][0]
    assert (s['width'],s['height'],int(s['nb_read_frames']),s['r_frame_rate']) == (width,height,frames,f'{fps}/1'), info
    state['stages'][name].update(state='verified',probe=info,seconds=elapsed)
    save();print('VERIFIED',name,elapsed,'seconds',flush=True)
    return dest

def interpolate(name,parent,model='apo-8',width=1920,height=1080):
    return stage(name,parent,f'tvai_fi=model={model}:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB)',width,height,181,30)

def final(tid,label,parent):
    run=ASSET/'runs'/f'restdung-{tid}-20261109-v1';run.mkdir(exist_ok=True)
    filename=f'{tid}-RESTDUNG-{label}-1080p30.mp4';dest=run/filename
    if tid in state['finals'] and state['finals'][tid].get('state')=='verified' and dest.exists():
        return
    cmd=[ENCODER,'-hide_banner','-nostdin','-n','-threads','8','-i',parent,'-i',SOURCE,'-map','0:v:0','-map','1:a:0?','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','16','-preset','slow','-fps_mode','passthrough','-c:a','aac','-b:a','192k',*YUV_TAGS,'-movflags','+faststart',dest]
    print('ENCODE',tid,flush=True);execute(cmd,run/'encode.log')
    info=probe(dest);s=info['streams'][0]
    assert (s['width'],s['height'],s['r_frame_rate'],int(s['nb_read_frames']))==(1920,1080,'30/1',181), info
    state['finals'][tid]={'state':'verified','qa':'pending','path':str(dest.relative_to(ROOT)),'parent':str(parent.relative_to(ROOT)),'probe':info,'command':[str(x)for x in cmd]}
    (run/'run.json').write_text(json.dumps(state['finals'][tid],indent=2),encoding='utf-8');save()
    print('FINAL_READY',tid,dest,flush=True)

src=stage('source-rgb709-15',SOURCE,'scale=in_range=tv:in_color_matrix=bt601:out_range=pc,format=gbrp16le,setpts=N/(15*TB)',1280,720)
c=stage('C-proteus720',src,C,1280,720)
cs=stage('Csoft-proteus720',src,CS,1280,720)
u=stage('C-U1080-15',c,U)
g=stage('C-G1080-15',c,G)
gs=stage('Csoft-G1080-15',cs,G)
l=stage('C-Lanczos1080-15',c,'scale=1920:1080:flags=lanczos')
final('T1','Proteus-Proteus-Apollo',interpolate('T1-Apollo1080',u))
final('T2','Proteus-Gaia-Apollo',interpolate('T2-Apollo1080',g))
final('T3','Proteus-doux-Gaia-Apollo',interpolate('T3-Apollo1080',gs))
final('T4','Proteus-Lanczos-Apollo',interpolate('T4-Apollo1080',l))
ci=interpolate('C-Apollo720-30',c,width=1280,height=720)
final('T5','Proteus-Apollo-Gaia',stage('T5-Gaia1080-30',ci,G,frames=181,fps=30))
final('T6','Proteus-Gaia-Aion',interpolate('T6-Aion1080',g,model='aion-1'))
state['state']='completed';save();print('ALL_SIX_COMPLETED',flush=True)
