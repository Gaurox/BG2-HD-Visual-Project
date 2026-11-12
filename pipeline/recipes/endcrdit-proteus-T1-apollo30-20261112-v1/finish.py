"""Apollo30, native-audio masters and WBM; user full-film QA stays pending."""
from spatial import *
import numpy as np,math,re
def main():
 assert not (FINAL/'verification.json').exists(),'Final proof immutable'
 ready=json.loads((RUN/'spatial-verification.json').read_text());assert sha(spatial)==ready['sha256']
 apollo=RUN/'ENDCRDIT-Proteus-T1-Apollo8-1080p30-video.mp4';count0=4002
 if not (RUN/'apollo-verification.json').exists():
  assert not apollo.exists()
  producer=[TOPAZ,'-hide_banner','-nostdin','-threads','4','-i',spatial,'-map','0:v','-an','-vf','setpts=N/(15*TB),format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le','-c:v','rawvideo','-pix_fmt','gbrp16le','-fps_mode','passthrough','-f','rawvideo','pipe:1']
  consumer=[FF,'-hide_banner','-nostdin','-n','-f','rawvideo','-pixel_format','gbrp16le','-video_size','1920x1080','-framerate','30','-i','pipe:0','-an','-vf',f'tpad=stop_mode=clone:stop_duration=0.033333333,trim=end_frame={count0},settb=1/30000,setpts=N*1000,scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-fps_mode','passthrough','-video_track_timescale','30000','-color_range','tv','-colorspace','bt709','-movflags','+faststart',apollo]
  print('APOLLO_START 2001 -> 4001 generated +1 held',flush=True);elapsed=pipe([producer,consumer],'apollo')
  generated=int(re.findall(r'frame=\s*(\d+)',(RUN/'apollo-0.log').read_text(errors='replace'))[-1]);assert generated==4001,generated
  p=probe(apollo);v=p['streams'][0];assert int(v['nb_read_frames'])==count0 and v['r_frame_rate']=='30/1'
  save(RUN/'apollo-verification.json',dict(model='apo-8',generated_frames=generated,final_hold_frames=1,frames=count0,path=apollo.relative_to(ROOT).as_posix(),sha256=sha(apollo),seconds=elapsed))
  print('APOLLO_READY',elapsed,flush=True)
 native=probe(SOURCE);duration=float(native['format']['duration']);origin=float(tools.frames(SOURCE)[0]);count=math.ceil((duration-origin)*30-1e-6);assert count==4004
 extended=RUN/'ENDCRDIT-Proteus-T1-1080p30-full-duration.mp4'
 if not extended.exists():tools.call([FF,'-v','error','-nostdin','-n','-i',apollo,'-map','0:v','-an','-vf',f'tpad=stop_mode=clone:stop_duration=1,trim=end_frame={count},settb=1/30000,setpts=N*1000','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-pix_fmt','yuv420p','-fps_mode','passthrough','-video_track_timescale','30000','-color_range','tv','-colorspace','bt709',extended])
 FINAL.mkdir(parents=True,exist_ok=True)
 master=FINAL/'ENDCRDIT-default-1080p30-native-audio.mkv';preview=FINAL/'ENDCRDIT-default-1080p30-audio.mp4';runtime=FINAL/'endcrdit.wbm'
 if not master.exists():tools.call([FF,'-v','error','-nostdin','-n','-copyts','-itsoffset',origin,'-i',extended,'-i',SOURCE,'-map','0:v','-map','1:a','-c','copy','-avoid_negative_ts','disabled',master])
 if not preview.exists():tools.call([FF,'-v','error','-nostdin','-n','-copyts','-i',master,'-map','0:v','-map','0:a','-c:v','copy','-c:a','aac','-b:a','192k','-avoid_negative_ts','disabled','-video_track_timescale','30000','-movflags','+faststart',preview])
 cmd=[FF,'-hide_banner','-nostdin','-n','-threads','4','-copyts','-i',master,'-map','0:v','-map','0:a','-c:v','libvpx','-crf','4','-b:v','30M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','8','-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',runtime]
 save(RECIPE/'metadata/runtime-command.json',list(map(str,cmd)))
 if not runtime.exists():
  print('WBM_ENCODE_START',flush=True)
  with (RUN/'runtime.log').open('wb') as log:subprocess.run(list(map(str,cmd)),stdout=log,stderr=log,check=True)
 probes={};drifts={}
 print('VERIFY_FULL_DECODE_AUDIO_TIMING',flush=True)
 for role,path in [('preview',preview),('master',master),('game_ready',runtime)]:
  p=probe(path);v=next(s for s in p['streams'] if s['codec_type']=='video');assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,count,'30/1')
  ts=tools.frames(path);drifts[role]=float(np.max(np.abs(ts-(origin+np.arange(count)/30))));assert drifts[role]<.0011,(role,drifts[role]);probes[role]=p
 a=tools.audio(SOURCE)
 for path in (master,runtime):
  b=tools.audio(path);assert a[:2]==b[:2] and len(a[2])==len(b[2]) and np.max(np.abs(a[2]-b[2]))<.0011
 graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
 check=subprocess.run([str(x) for x in [FF,'-hide_banner','-nostdin','-threads','2','-i',master,'-threads','2','-i',runtime,'-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL']],capture_output=True,text=True,check=True)
 (FINAL/'ssim.log').write_text(check.stderr,encoding='utf-8');ssim=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert ssim>.99
 # Moving-credit intervals: at least one interpolated frame differs from both anchors.
 gray=np.frombuffer(tools.call([FF,'-v','error','-threads','2','-i',apollo,'-an','-vf','scale=160:90:flags=area,format=gray','-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(count0,90,160).astype(np.float32)
 odd=gray[1:4001:2];novel=int(((np.abs(odd-gray[:4000:2]).mean((1,2))>.01)&(np.abs(odd-gray[2:4002:2]).mean((1,2))>.01)).sum());assert novel>0
 for sec in (1,4,12,30,60,90,120,132):
  p=FINAL/f'check-{sec}s.png'
  if not p.exists():tools.call([FF,'-v','error','-nostdin','-n','-ss',sec,'-i',preview,'-frames:v','1',p])
 result=dict(asset_key='movie:default:ENDCRDIT',state='runtime-ready',source=SOURCE.relative_to(ROOT).as_posix(),source_sha256=sha(SOURCE),spatial_recipe='T1 Proteus prob-4 neutral x2 then Lanczos1080; one pass',spatial_verification=ready,apollo=json.loads((RUN/'apollo-verification.json').read_text()),dimensions=[1920,1080],fps='30/1',frames=count,duration_s=count/30,native_container_duration_s=duration,native_video_frames=2001,video_origin_s=origin,additional_final_hold_frames=count-count0,ssim_sampled_all=ssim,native_audio_pcm_identical=True,native_audio_encoded_identical=True,full_frame_decode=True,native_video_pts_max_deviation_s=drifts,novel_intermediate_frames=novel,tested_intermediate_frames=2000,probes=probes,files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size) for role,path in [('preview',preview),('master',master),('game_ready',runtime)]},first5s_spatial_user_qa='accepted-T1',user_visual_qa='pending-full-film30fps',ingame_qa='not-performed',installed=False,release_integration=False)
 import shutil
 for name in ('production.json','spatial-verification.json','proteus-T1-commands.json','apollo-verification.json','apollo-commands.json'):
  shutil.copy2(RUN/name,RECIPE/'metadata'/name)
 save(RUN/'completion.json',dict(state='runtime-ready',manifest='video/index/endcrdit-proteus-T1-finals30-20261112-v1.json',installed=False))
 save(FINAL/'verification.json',result);save(RECIPE/'metadata/manifest.json',result);save(ROOT/'video/index/endcrdit-proteus-T1-finals30-20261112-v1.json',result);print('ENDCRDIT_T1_FULLHD30_READY',count,ssim,flush=True)
if __name__=='__main__':main()
