"""Spatial-only 75-frame ENDCRDIT experiments; no installation/full-film processing."""
from pathlib import Path
import os,sys,json,subprocess,time,hashlib
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
FF=Path('C:/ffmpeg/bin/ffmpeg.exe');PROBE=FF.with_name('ffprobe.exe')
TOPAZ=get_path('topaz_video_ffmpeg',required=True);MODELS=get_path('topaz_video_models',required=True)
RUN=ROOT/'video/endcrdit/runs/endcrdit-topaz-tests-5s-20261112-v1'
RECIPE=Path(__file__).resolve().parent
SOURCE=ROOT/'video/endcrdit/endcrdit.wbm'
env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));env['PATH']=str(TOPAZ.parent)+os.pathsep+env['PATH']
common=':grain=0:estimate=0:device=0:vram=0.8:instances=0:download=0'
def ai(model,params='',native=False):
    return f'tvai_up=model={model}:scale={1 if native else 2}:w={1280 if native else 2560}:h={720 if native else 1440}'+params+common+',scale=1920:1080:flags=lanczos'
tests=[
 ('R0','Lanczos sans IA','scale=1920:1080:flags=lanczos',False),
 ('R1','Spline et nettete legere','scale=1920:1080:flags=spline,unsharp=5:5:0.3:5:5:0',False),
 ('T1','Proteus neutre x2',ai('prob-4'),True),
 ('T2','Proteus doux blend 50%',ai('prob-4',':preblur=-0.05:noise=0:details=0:halo=0.05:blur=0:compression=0.1:blend=0.5'),True),
 ('T3','Proteus detail et nettete',ai('prob-4',':preblur=0:noise=0:details=0.3:halo=0.05:blur=0.2:compression=0.1:blend=0'),True),
 ('T4','Gaia CGI',ai('gcg-5'),True),
 ('T5','Gaia HQ',ai('ghq-5'),True),
 ('T6','Artemis HQ',ai('ahq-12'),True),
 ('T7','Artemis MQ',ai('amq-13'),True),
 ('T8','Nyx doux 1x puis Lanczos',ai('nyx-2',':noise=0.05:details=0:blur=0:blend=0.5',True),True),
 ('T9','Proteus doux 1x puis Lanczos',ai('prob-4',':noise=0:details=0.05:blur=0:compression=0.1:blend=0.5',True),True),
 ('T10','Iris v2',ai('iris-2',':details=0:blur=0:noise=0:blend=0.25'),True),
 ('T8b','Nyx v3 doux 1x puis Lanczos',ai('nyx-3',':noise=0.05:details=0:blur=0:blend=0.5',True),True),
 ('T11','Iris v3',ai('iris-3',':details=0:blur=0:noise=0:blend=0.25'),True),
]
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def run(cmd,log):
    cmd=list(map(str,cmd));start=time.monotonic()
    with log.open('w',encoding='utf-8') as f:p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
    if p.returncode:raise RuntimeError(log.read_text(encoding='utf-8',errors='replace')[-2500:])
    return round(time.monotonic()-start,2)
def probe(p):return json.loads(subprocess.check_output([str(PROBE),'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(p)]))
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    RUN.mkdir(parents=True,exist_ok=True)
    state= json.loads((RUN/'production.json').read_text(encoding='utf-8')) if (RUN/'production.json').exists() else dict(state='working',source=str(SOURCE.relative_to(ROOT)),source_sha256=sha(SOURCE),frames=75,fps='15/1',interpolation=False,tests={})
    native=RUN/'source-75frames-rgb.mkv'
    if not native.exists():run([FF,'-v','error','-nostdin','-n','-i',SOURCE,'-map','0:v','-an','-frames:v','75','-vf','scale=in_range=tv:in_color_matrix=bt601:out_range=pc,format=gbrp16le,settb=1/15000,setpts=N*1000','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',native],RUN/'source.log')
    audio=RUN/'audio-5s.m4a'
    if not audio.exists():run([FF,'-v','error','-nostdin','-n','-i',SOURCE,'-map','0:a','-t','5','-c:a','aac','-b:a','192k',audio],RUN/'audio.log')
    for tid,label,filt,gpu in tests:
        if state['tests'].get(tid,{}).get('state') in ('ready','failed'):continue
        dest=RUN/f'{tid}-ENDCRDIT-1080p15-5s.mp4';inter=RUN/f'{tid}-rgb.mkv'
        info=dict(label=label,filter=filt,gpu=gpu,state='running');state['tests'][tid]=info;save(RUN/'production.json',state);print('START',tid,label,flush=True)
        try:
            cmd=[TOPAZ if gpu else FF,'-hide_banner','-nostdin','-n','-threads','4','-i',native,'-map','0:v','-an','-vf',filt+',format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',inter]
            info['command']=list(map(str,cmd));info['seconds']=run(cmd,RUN/f'{tid}-topaz.log')
            run([FF,'-v','error','-nostdin','-n','-threads','4','-i',inter,'-i',audio,'-map','0:v','-map','1:a','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-c:a','copy','-fps_mode','passthrough','-color_range','tv','-colorspace','bt709','-movflags','+faststart',dest],RUN/f'{tid}-encode.log')
            p=probe(dest);v=next(s for s in p['streams'] if s['codec_type']=='video');assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,75,'15/1')
            info.update(state='ready',path=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),probe=p)
            run([FF,'-v','error','-nostdin','-n','-ss','4','-i',dest,'-frames:v','1',RUN/f'{tid}-4s.png'],RUN/f'{tid}-frame.log')
            print('READY',tid,info['seconds'],flush=True)
        except Exception as e:info.update(state='failed',error=str(e));print('FAILED',tid,str(e)[-700:],flush=True)
        save(RUN/'production.json',state)
    state['state']='completed';state['user_qa']='pending';save(RUN/'production.json',state);save(RECIPE/'metadata/production.json',state)
    print('ALL_TESTS_FINISHED',flush=True)
if __name__=='__main__':main()
