"""Full-film exact T1 spatial recipe, lossless RGB pipes, no large stage caches."""
from pathlib import Path
import sys,os,subprocess,json,time,hashlib,importlib.util
ROOT=Path(__file__).resolve().parents[3];RECIPE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
FF=Path('C:/ffmpeg/bin/ffmpeg.exe');FP=FF.with_name('ffprobe.exe');TOPAZ=get_path('topaz_video_ffmpeg',required=True);MODELS=get_path('topaz_video_models',required=True)
SOURCE=ROOT/'video/endcrdit/endcrdit.wbm'
RUN=ROOT/'video/endcrdit/runs/endcrdit-proteus-T1-apollo30-20261112-v1'
FINAL=ROOT/'video/final/endcrdit-proteus-T1-apollo30-20261112-v1/ENDCRDIT/default'
spatial=RUN/'ENDCRDIT-Proteus-T1-1080p15-video.mp4'
env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS));env['PATH']=str(TOPAZ.parent)+os.pathsep+env['PATH']
spec=importlib.util.spec_from_file_location('ending_tools',ROOT/'pipeline/recipes/endings-shared-30fps-20261111-v1/produce.py');tools=importlib.util.module_from_spec(spec);spec.loader.exec_module(tools)
save=tools.save;sha=tools.sha;probe=tools.probe
def pipe(commands,name):
 save(RUN/f'{name}-commands.json',[[str(x) for x in c] for c in commands]);ps=[];logs=[];start=time.monotonic()
 try:
  for i,c in enumerate(commands):
   log=(RUN/f'{name}-{i}.log').open('wb');logs.append(log)
   p=subprocess.Popen(list(map(str,c)),stdin=ps[-1].stdout if ps else None,stdout=subprocess.PIPE if i<len(commands)-1 else log,stderr=log,env=env)
   if ps:ps[-1].stdout.close()
   ps.append(p)
  rc=ps[-1].wait()
  if rc:
   for p in ps[:-1]:
    if p.poll() is None:p.terminate()
  codes=[p.wait() for p in ps];assert not any(codes),(name,codes)
 finally:
  for p in ps:
   if p.poll() is None:p.terminate()
  for log in logs:log.close()
 return round(time.monotonic()-start,2)
def main():
 RUN.mkdir(parents=True,exist_ok=True)
 if (RUN/'spatial-verification.json').exists():assert sha(spatial)==json.loads((RUN/'spatial-verification.json').read_text())['sha256'];return
 assert not spatial.exists()
 native=tools.frames(SOURCE);assert len(native)==2001
 row=next(x for x in __import__('csv').DictReader((ROOT/'video/index/resources.csv').open(encoding='utf-8-sig')) if x['asset_key']=='movie:default:ENDCRDIT');assert sha(SOURCE).upper()==row['source_sha256'].upper()
 filt='tvai_up=model=prob-4:scale=2:w=2560:h=1440:grain=0:estimate=0:device=0:vram=0.8:instances=0:download=0,scale=1920:1080:flags=lanczos,format=gbrp16le'
 commands=[
 [FF,'-hide_banner','-nostdin','-threads','4','-i',SOURCE,'-map','0:v','-an','-vf','scale=in_range=tv:in_color_matrix=bt601:out_range=pc,format=gbrp16le,settb=1/15000,setpts=N*1000','-pix_fmt','gbrp16le','-fps_mode','passthrough','-f','rawvideo','pipe:1'],
 [TOPAZ,'-hide_banner','-nostdin','-threads','4','-f','rawvideo','-pixel_format','gbrp16le','-video_size','1280x720','-framerate','15','-color_range','pc','-colorspace','rgb','-i','pipe:0','-an','-vf',filt,'-c:v','rawvideo','-pix_fmt','gbrp16le','-fps_mode','passthrough','-f','rawvideo','pipe:1'],
 [FF,'-hide_banner','-nostdin','-n','-f','rawvideo','-pixel_format','gbrp16le','-video_size','1920x1080','-framerate','15','-i','pipe:0','-an','-vf','scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-fps_mode','passthrough','-color_range','tv','-colorspace','bt709','-video_track_timescale','15000','-movflags','+faststart',spatial]]
 save(RUN/'production.json',dict(state='spatial-running',source=SOURCE.relative_to(ROOT).as_posix(),source_sha256=sha(SOURCE),recipe='T1 Proteus neutral x2 then Lanczos1080',selected_by_user=True,second_pass=False,seedvr=False,native_frames=2001,native_pts_origin_s=float(native[0]),source_duration_s=float(probe(SOURCE)['format']['duration'])))
 print('PROTEUS_T1_FULL_START 2001frames',flush=True);elapsed=pipe(commands,'proteus-T1')
 p=probe(spatial);v=p['streams'][0];assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,2001,'15/1')
 save(RUN/'spatial-verification.json',dict(state='spatial-ready',path=spatial.relative_to(ROOT).as_posix(),sha256=sha(spatial),frames=2001,fps='15/1',seconds=elapsed,filter=filt,probe=p))
 print('PROTEUS_T1_FULL_READY',elapsed,flush=True)
if __name__=='__main__':main()
