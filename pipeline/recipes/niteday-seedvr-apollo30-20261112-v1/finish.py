"""SeedVR150 native frames -> Apollo300 frames -> native audio duration329 frames."""
from prepare import ROOT,RECIPE,RUN,SOURCE,tools
import json,math,re,subprocess
import numpy as np
FINAL=ROOT/'video/final/niteday-seedvr-apollo30-20261112-v1/NITEDAY/default'

def main():
    assert not (FINAL/'verification.json').exists()
    production=json.loads((RUN/'production.json').read_text())
    raw=list((RUN/'downloads').rglob('*.mov'));assert len(raw)==1
    p=tools.probe(raw[0]);v=next(s for s in p['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,150)
    seed=RUN/'NITEDAY-SeedVR2-LAB-1080p15.mp4'
    if not seed.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-threads','2','-i',raw[0],'-map','0:v:0','-an','-vf','setpts=N/(15*TB)',
        '-c:v','libx264','-crf','12','-preset','medium','-threads','4','-pix_fmt','yuv420p','-fps_mode','passthrough','-video_track_timescale','1000000',seed])
    assert len(tools.frames(seed))==150
    tools.save(RUN/'run.json',dict(status='inference-completed',output=seed.name,frames=150,source=production['source'],source_sha256=production['source_sha256']))
    tools.run_dir=lambda film:RUN
    apollo=tools.interpolate('NITEDAY');video=ROOT/apollo['output']
    native_probe=tools.probe(SOURCE);duration=float(native_probe['format']['duration']);count=math.ceil(duration*30-1e-6)
    assert count==329
    extended=RUN/'NITEDAY-1080p30-full-duration.mp4'
    if not extended.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-threads','2','-i',video,'-map','0:v:0','-an',
        '-vf',f'tpad=stop_mode=clone:stop_duration=3,trim=end_frame={count},setpts=N/(30*TB)',
        '-c:v','libx264','-crf','12','-preset','medium','-threads','4','-pix_fmt','yuv420p','-fps_mode','passthrough','-video_track_timescale','1000000',extended])
    FINAL.mkdir(parents=True,exist_ok=True)
    master=FINAL/'NITEDAY-default-1080p30-native-audio.mkv';preview=FINAL/'NITEDAY-default-1080p30-audio.mp4';runtime=FINAL/'niteday.wbm'
    if not master.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-copyts','-i',extended,'-i',SOURCE,'-map','0:v:0','-map','1:a:0','-c','copy','-avoid_negative_ts','disabled',master])
    if not preview.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-copyts','-i',master,'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-avoid_negative_ts','disabled','-movflags','+faststart',preview])
    print('ENCODE runtime VP8',flush=True)
    command=[tools.FF,'-v','error','-nostdin','-n','-threads','2','-copyts','-i',master,'-map','0:v:0','-map','0:a:0',
        '-c:v','libvpx','-crf','4','-b:v','30M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2',
        '-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',runtime]
    tools.save(RUN/'runtime-command.json',[str(x) for x in command])
    if not runtime.exists():tools.call(command)
    probes={}
    for role,path in [('preview',preview),('master',master),('game_ready',runtime)]:
        p=tools.probe(path);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
        assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,count,'30/1')
        if role=='game_ready':assert v['codec_name']=='vp8' and a['codec_name']=='vorbis'
        assert np.max(np.abs(tools.frames(path)-np.arange(count)/30))<.0011
        probes[role]=p
    native_audio=tools.audio(SOURCE)
    for path in (master,runtime):
        actual=tools.audio(path);assert native_audio[:2]==actual[:2] and len(native_audio[2])==len(actual[2])
        assert np.max(np.abs(native_audio[2]-actual[2]))<=.0011
    graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
    check=subprocess.run([tools.FF,'-hide_banner','-nostdin','-threads','2','-i',str(master),'-threads','2','-i',str(runtime),'-filter_complex_threads','1',
        '-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
    (FINAL/'ssim.log').write_text(check.stderr,encoding='utf-8');ssim=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert ssim>.99
    gray=np.frombuffer(tools.call([tools.FF,'-v','error','-threads','2','-i',video,'-an','-vf','scale=160:90:flags=area,format=gray','-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(300,90,160).astype(np.float32)
    odd=gray[1:299:2];novel=int(((np.abs(odd-gray[:298:2]).mean((1,2))>.01)&(np.abs(odd-gray[2:300:2]).mean((1,2))>.01)).sum());assert novel>0
    for sec in (1,3,5,7,9.8,10.7):tools.call([tools.FF,'-v','error','-nostdin','-n','-ss',sec,'-i',preview,'-frames:v','1',FINAL/f'check-{sec:g}s.png'])
    result=dict(asset_key='movie:default:NITEDAY',state='runtime-ready',source=production['source'],source_sha256=production['source_sha256'],
        dimensions=[1920,1080],fps='30/1',frames=count,duration_s=count/30,native_video_frames=150,native_video_duration_s=150/15,native_container_duration_s=duration,
        apollo=apollo,additional_final_hold_frames=29,ssim_sampled_all=ssim,native_audio_pcm_identical=True,native_audio_encoded_identical=True,
        full_frame_decode=True,novel_intermediate_frames=novel,tested_intermediate_frames=149,probes=probes,
        files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=tools.sha(path),bytes=path.stat().st_size) for role,path in [('preview',preview),('master',master),('game_ready',runtime)]},
        user_visual_qa='pending',ingame_qa='not-performed',installed=False,release_integration=False)
    tools.save(FINAL/'verification.json',result);tools.save(RECIPE/'metadata/manifest.json',result);tools.save(ROOT/'video/index/niteday-finals30-20261112-v1.json',result)
    print('NITEDAY_READY',count,'frames SSIM',ssim,flush=True)

if __name__=='__main__':main()
