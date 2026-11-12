"""Compare second spatial passes on the exact accepted T1 preview, 75 frames."""
from pathlib import Path
import sys,os,subprocess,json,time,hashlib
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
FF=Path('C:/ffmpeg/bin/ffmpeg.exe');PROBE=FF.with_name('ffprobe.exe')
TOPAZ=get_path('topaz_video_ffmpeg',required=True);MODELS=get_path('topaz_video_models',required=True)
RECIPE=Path(__file__).resolve().parent;RUN=ROOT/'video/endcrdit/runs/endcrdit-topaz-second-pass-5s-20261112-v1'
PREVIOUS=ROOT/'video/endcrdit/runs/endcrdit-topaz-tests-5s-20261112-v1'
BASE=PREVIOUS/'T1-ENDCRDIT-1080p15-5s.mp4'
env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));env['PATH']=str(TOPAZ.parent)+os.pathsep+env['PATH']
COMMON=':grain=0:estimate=0:device=0:vram=0.8:instances=0:download=0'
def ai(model,params='',scale=1):
 return f'tvai_up=model={model}:scale={scale}:w={1920*scale}:h={1080*scale}'+params+COMMON+(',scale=1920:1080:flags=lanczos' if scale==2 else '')
TESTS=[
 ('P1','Proteus 1x neutre',ai('prob-4')),
 ('P2','Proteus 1x tres doux 50%',ai('prob-4',':noise=0:details=0:blur=0:compression=0.05:halo=0.03:blend=0.5')),
 ('P3','Proteus antialias leger',ai('prob-4',':preblur=-0.15:noise=0:details=0:blur=0:compression=0:blend=0.35')),
 ('P4','Proteus details et nettete legers',ai('prob-4',':noise=0:details=0.15:blur=0.08:halo=0.05:compression=0:blend=0.25')),
 ('P5','Nyx3 nettoyage doux 1x',ai('nyx-3',':noise=0.03:details=0:blur=0:blend=0.6')),
 ('P6','Gaia CGI x2 puis reduction',ai('gcg-5',scale=2)),
 ('P7','Artemis MQ x2 puis reduction',ai('amq-13',scale=2)),
 ('P8','Proteus x2 doux puis reduction',ai('prob-4',':noise=0:details=0.05:blur=0:compression=0:blend=0.5',2)),
 ('P9','Nettete classique legere sans IA','unsharp=5:5:0.25:5:5:0'),
]
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def probe(p):return json.loads(subprocess.check_output([str(PROBE),'-v','error','-count_frames','-show_streams','-show_format','-of','json',str(p)]))
def run(cmd,log,cwd=None):
 start=time.monotonic()
 with log.open('w',encoding='utf-8') as f:p=subprocess.run(list(map(str,cmd)),env=env,stdout=f,stderr=subprocess.STDOUT,cwd=cwd)
 if p.returncode:raise RuntimeError(log.read_text(encoding='utf-8',errors='replace')[-1600:])
 return round(time.monotonic()-start,2)
def verify(path):
 p=probe(path);v=next(s for s in p['streams'] if s['codec_type']=='video');assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']))==(1920,1080,'15/1',75)
 return p
def frame(tid,path):
 out=RUN/f'{tid}-4s.png'
 if not out.exists():run([FF,'-v','error','-nostdin','-n','-ss','4','-i',path,'-frames:v','1',out],RUN/f'{tid}-frame.log')
def main():
 RUN.mkdir(parents=True,exist_ok=True)
 previous=json.loads((PREVIOUS/'production.json').read_text(encoding='utf-8'))['tests']['T1'];assert sha(BASE)==previous['sha256']
 report=RUN/'production.json'
 state=json.loads(report.read_text(encoding='utf-8')) if report.exists() else dict(state='working',base=dict(path=BASE.relative_to(ROOT).as_posix(),sha256=sha(BASE),accepted_user=True,scope='first-5-seconds-only'),frames=75,fps='15/1',interpolation=False,tests={})
 qa=ROOT/'video/index/qa-decisions/ENDCRDIT/20261112-topaz-T1-first5s-visual-accepted-v1.json'
 if not qa.exists():save(qa,dict(asset_key='movie:default:ENDCRDIT',decision='accepted',scope='Topaz-T1-first5s-visual-only',decision_date='2026-11-12',user_decision='je valide T1. tu peux faire un second travail basé sur T1 STP? voir si 2 passes différentes peuvent le rendre encore meilleur?',preview=state['base'],full_film_qa='not-performed',ingame_qa='not-performed',installed=False))
 base=RUN/'T1-accepted-rgb.mkv'
 if not base.exists():run([FF,'-v','error','-nostdin','-n','-i',BASE,'-map','0:v','-an','-vf','scale=in_range=tv:in_color_matrix=bt709:out_range=pc,format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',base],RUN/'base.log')
 for tid,label,filt in TESTS:
  if state['tests'].get(tid,{}).get('state') in ('ready','failed'):continue
  info=dict(state='running',label=label,filter=filt,gpu=tid!='P9');state['tests'][tid]=info;save(report,state);print('START',tid,label,flush=True)
  stage=RUN/f'{tid}-rgb.mkv';dest=RUN/f'{tid}-ENDCRDIT-T1-second-pass-1080p15-5s.mp4'
  try:
   cmd=[TOPAZ if tid!='P9' else FF,'-hide_banner','-nostdin','-n','-threads','4','-i',base,'-map','0:v','-an','-vf',filt+',format=gbrp16le','-c:v','ffv1','-level','3','-fps_mode','passthrough','-color_range','pc','-colorspace','rgb',stage]
   info['command']=list(map(str,cmd));info['seconds']=run(cmd,RUN/f'{tid}-topaz.log')
   cmd=[FF,'-v','error','-nostdin','-n','-threads','4','-i',stage,'-i',BASE,'-map','0:v','-map','1:a','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-c:a','copy','-fps_mode','passthrough','-color_range','tv','-colorspace','bt709','-movflags','+faststart',dest]
   info['encode_command']=list(map(str,cmd));run(cmd,RUN/f'{tid}-encode.log')
   info.update(state='ready',path=dest.relative_to(ROOT).as_posix(),sha256=sha(dest),probe=verify(dest));frame(tid,dest)
   info['rgb_intermediate_removed_bytes']=stage.stat().st_size;assert stage.resolve().is_relative_to(RUN.resolve());stage.unlink()
   print('READY',tid,info['seconds'],flush=True)
  except Exception as e:info.update(state='failed',error=str(e));print('FAILED',tid,str(e)[-500:],flush=True)
  save(report,state)
 state.update(state='completed',user_qa='pending-second-pass');save(report,state);save(RECIPE/'metadata/production.json',state);print('SECOND_PASSES_FINISHED',flush=True)
if __name__=='__main__':main()
