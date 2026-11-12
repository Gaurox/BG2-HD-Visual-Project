"""LOGO spatial upscale only: 302 original frames, 30000/1001fps, no Apollo."""
from prepare import ROOT,RECIPE,RUN,SOURCE,tools
import json,subprocess,re
import numpy as np
FINAL=ROOT/'video/final/logo-seedvr-nativefps-20261112-v1/LOGO/default'

def main():
    assert not (FINAL/'verification.json').exists()
    raw=list((RUN/'downloads/part-01').rglob('*.mov'));assert len(raw)==1
    p=tools.probe(raw[0]);v=next(s for s in p['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,302)
    native=tools.frames(SOURCE);assert len(native)==302
    origin=float(native[0]);rate=30000/1001
    assert np.max(np.abs(native-(origin+np.arange(302)/rate)))<.0011
    FINAL.mkdir(parents=True,exist_ok=True)
    video=RUN/'LOGO-SeedVR2-1080p-native2997-video.mp4'
    command=[tools.FF,'-v','error','-nostdin','-n','-hwaccel','none','-threads','2','-r','30000/1001','-i',raw[0],'-map','0:v:0','-an',
        '-vf','settb=1/30000,setpts=N*1001','-c:v','libx264','-crf','12','-preset','medium','-threads','4',
        '-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:30000','-video_track_timescale','30000',video]
    tools.save(RECIPE/'metadata/video-command.json',[str(x) for x in command])
    if not video.exists():tools.call(command)
    master=FINAL/'LOGO-default-1080p2997-native-audio.mkv';preview=FINAL/'LOGO-default-1080p2997-audio.mp4';runtime=FINAL/'logo.wbm'
    if not master.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-copyts','-itsoffset',origin,'-i',video,'-i',SOURCE,
        '-map','0:v:0','-map','1:a:0','-c','copy','-avoid_negative_ts','disabled',master])
    if not preview.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-copyts','-i',master,'-map','0:v:0','-map','0:a:0',
        '-c:v','copy','-c:a','aac','-b:a','192k','-avoid_negative_ts','disabled','-video_track_timescale','30000','-movflags','+faststart',preview])
    command=[tools.FF,'-v','error','-nostdin','-n','-hwaccel','none','-threads','2','-copyts','-i',master,'-map','0:v:0','-map','0:a:0',
        '-c:v','libvpx','-crf','4','-b:v','30M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2',
        '-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:1000000',
        '-c:a','copy','-avoid_negative_ts','disabled','-f','webm',runtime]
    tools.save(RECIPE/'metadata/runtime-command.json',[str(x) for x in command])
    print('ENCODE LOGO native 29.97fps, 302 frames, no interpolation',flush=True)
    if not runtime.exists():tools.call(command)
    probes={};drifts={}
    for role,path in [('preview',preview),('master',master),('game_ready',runtime)]:
        p=tools.probe(path);v=next(s for s in p['streams'] if s['codec_type']=='video')
        assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,302,'30000/1001'),(role,v)
        actual=tools.frames(path);drifts[role]=float(np.max(np.abs(actual-native)));assert drifts[role]<.0011,(role,drifts[role])
        probes[role]=p
    audio=tools.audio(SOURCE)
    for path in (master,runtime):
        actual=tools.audio(path);assert audio[:2]==actual[:2] and len(audio[2])==len(actual[2])
        assert np.max(np.abs(audio[2]-actual[2]))<=.0011
    graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
    check=subprocess.run([tools.FF,'-hide_banner','-nostdin','-hwaccel','none','-threads','2','-i',str(master),'-hwaccel','none','-threads','2','-i',str(runtime),
        '-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
    (FINAL/'ssim.log').write_text(check.stderr,encoding='utf-8');ssim=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert ssim>.99
    for sec in (1,3,5,6,7.5,9,9.9):tools.call([tools.FF,'-v','error','-nostdin','-n','-ss',sec,'-i',preview,'-frames:v','1',FINAL/f'check-{sec:g}s.png'])
    result=dict(asset_key='movie:default:LOGO',state='runtime-ready',source='video/logo/logo.wbm',source_sha256=tools.sha(SOURCE),
        dimensions=[1920,1080],fps='30000/1001',frames=302,video_origin_s=origin,video_duration_s=302/rate,
        interpolation=False,apollo_launched=False,source_frame_count_preserved=True,ssim_sampled_all=ssim,
        native_audio_pcm_identical=True,native_audio_encoded_identical=True,full_frame_decode=True,native_video_pts_max_deviation_s=drifts,
        files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=tools.sha(path),bytes=path.stat().st_size) for role,path in [('preview',preview),('master',master),('game_ready',runtime)]},
        probes=probes,user_visual_qa='pending',ingame_qa='not-performed',installed=False,release_integration=False)
    tools.save(FINAL/'verification.json',result);tools.save(RECIPE/'metadata/manifest.json',result);tools.save(ROOT/'video/index/logo-finals-nativefps-20261112-v1.json',result)
    print('LOGO_READY 302 original frames at 30000/1001fps; no Apollo; SSIM',ssim,flush=True)

if __name__=='__main__':main()
