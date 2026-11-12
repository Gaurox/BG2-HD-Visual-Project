"""SeedVR portions -> Apollo temporal samples -> native-time 30fps + native audio."""
from prepare import ROOT,RECIPE,RUN,SOURCE,tools
from pathlib import Path
import argparse,json,os,subprocess,re,math
import numpy as np
FINAL=ROOT/'video/final/rasaadmi-seedvr-apollo30-20261112-v1/RASAADMI/default'

def part(number):
    e=json.loads((RUN/'production.json').read_text())['parts'][number-1]
    raw=list((RUN/'downloads'/f'part-{number:02d}').rglob('*.mov'));assert len(raw)==1
    p=tools.probe(raw[0]);v=next(s for s in p['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,e['input_frames'])
    output=RUN/f'RASAADMI-part-{number:02d}-index30.mp4'
    tools.call([tools.FF,'-v','error','-nostdin','-n','-threads','2','-i',raw[0],'-map','0:v:0','-an','-vf',
        f"trim=start_frame={e['discard']},setpts=N/(30*TB)",'-c:v','libx264','-crf','12','-preset','medium','-threads','4',
        '-pix_fmt','yuv420p','-fps_mode','passthrough','-video_track_timescale','1000000','-movflags','+faststart',output])
    assert len(tools.frames(output))==e['kept']
    tools.save(RUN/f'part-{number:02d}-verified.json',dict(**e,raw=raw[0].relative_to(ROOT).as_posix(),raw_sha256=tools.sha(raw[0]),output=output.relative_to(ROOT).as_posix(),sha256=tools.sha(output)))
    print('PART_READY',number,flush=True)

def final():
    assert not (FINAL/'verification.json').exists()
    FINAL.mkdir(parents=True,exist_ok=True)
    listing=RUN/'concat.txt';listing.write_text(''.join(f"file '{(RUN/f'RASAADMI-part-{n:02d}-index30.mp4').as_posix()}'\n" for n in (1,2)))
    seed=RUN/'RASAADMI-SeedVR-LAB-index30.mp4'
    if not seed.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-f','concat','-safe','0','-i',listing,'-map','0:v:0','-an','-c','copy',seed])
    assert len(tools.frames(seed))==403
    apollo=RUN/'RASAADMI-Apollo8-index60.mp4'
    producer=[str(tools.TOPAZ),'-hide_banner','-nostdin','-n','-threads','8','-i',str(seed),'-map','0:v:0','-an','-vf',
        'setpts=N/(30*TB),format=rgb24,tvai_fi=model=apo-8:fps=60:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(60*TB),format=gbrp16le',
        '-c:v','rawvideo','-pix_fmt','gbrp16le','-fps_mode','passthrough','-f','rawvideo','pipe:1']
    consumer=[tools.FF,'-hide_banner','-nostdin','-n','-f','rawvideo','-pixel_format','gbrp16le','-video_size','1920x1080','-framerate','60','-i','pipe:0','-an','-vf',
        'tpad=stop_mode=clone:stop_duration=0.016666667,trim=end_frame=806,setpts=N/(60*TB),scale=in_range=pc:out_range=tv:out_color_matrix=bt601,format=yuv420p',
        '-c:v','libx264','-crf','14','-preset','slow','-threads','4','-fps_mode','passthrough','-video_track_timescale','1000000','-color_range','tv',str(apollo)]
    tools.save(RUN/'apollo-commands.json',[producer,consumer])
    if not apollo.exists():
        env=os.environ.copy();env.update(TVAI_MODEL_DIR=str(tools.MODELS),TVAI_MODEL_DATA_DIR=str(tools.MODELS));env['PATH']=str(tools.TOPAZ.parent)+os.pathsep+env.get('PATH','')
        print('APOLLO index30->index60; restore native timestamps afterwards',flush=True)
        with (RUN/'apollo.log').open('wb') as a,(RUN/'apollo-encode.log').open('wb') as b:
            pr=subprocess.Popen(producer,stdout=subprocess.PIPE,stderr=a,env=env)
            co=subprocess.Popen(consumer,stdin=pr.stdout,stdout=b,stderr=b);pr.stdout.close()
            cr=co.wait()
            if cr and pr.poll() is None:pr.terminate()
            rc=pr.wait()
        assert rc==cr==0,(rc,cr)
    assert int(re.findall(r'frame=\s*(\d+)',(RUN/'apollo.log').read_text(errors='replace'))[-1])==805
    assert len(tools.frames(apollo))==806
    gray=np.frombuffer(tools.call([tools.FF,'-v','error','-threads','2','-i',apollo,'-an','-vf',
        'scale=160:90:flags=area,format=gray','-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(806,90,160).astype(np.float32)
    odd=gray[1:805:2]
    novel=int(((np.abs(odd-gray[:804:2]).mean((1,2))>.01)&(np.abs(odd-gray[2:806:2]).mean((1,2))>.01)).sum())
    assert novel>0,'Apollo must generate intermediate motion'
    pts=np.array(json.loads((RUN/'native-frame-times.json').read_text()));origin=pts[0]
    count=math.ceil((pts[-1]-origin+100/2997)*30-1e-7)
    selected=np.rint(np.interp(origin+np.arange(count)/30,pts,2*np.arange(len(pts)))).astype(int)
    tools.save(RUN/'native-mapping.json',dict(native_pts_s=pts.tolist(),selected_apollo_frames=selected.tolist(),output_origin_s=origin,frames=count,
        method='all native spatial frames retained; Apollo midpoint per adjacent pair; nearest half-frame sampled on native-time 30fps grid'))
    video=RUN/'RASAADMI-1080p30-native-time.mp4'
    if not video.exists():
        dec=[tools.FF,'-v','error','-threads','2','-i',str(apollo),'-an','-pix_fmt','yuv420p','-threads','1','-fps_mode','passthrough','-f','rawvideo','pipe:1']
        enc=[tools.FF,'-v','error','-nostdin','-n','-f','rawvideo','-pixel_format','yuv420p','-video_size','1920x1080','-framerate','30','-i','pipe:0',
            '-an','-c:v','libx264','-crf','12','-preset','medium','-threads','4','-video_track_timescale','1000000','-movflags','+faststart',str(video)]
        with (RUN/'retime.log').open('wb') as log:
            de=subprocess.Popen(dec,stdout=subprocess.PIPE,stderr=log);en=subprocess.Popen(enc,stdin=subprocess.PIPE,stderr=log)
            current=-1;frame=None;size=1920*1080*3//2
            try:
                for target in selected:
                    while current<target:
                        chunks=[];remaining=size
                        while remaining:
                            data=de.stdout.read(remaining)
                            if not data:raise RuntimeError('Apollo decoder EOF')
                            chunks.append(data);remaining-=len(data)
                        frame=b''.join(chunks);current+=1
                    en.stdin.write(frame)
            finally:
                en.stdin.close();de.stdout.close()
                if de.poll() is None:de.terminate()
                de.wait()
            assert en.wait()==0
    master=FINAL/'RASAADMI-default-1080p30-native-audio.mkv';preview=FINAL/'RASAADMI-default-1080p30-audio.mp4';runtime=FINAL/'rasaadmi.wbm'
    if not master.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-copyts','-itsoffset',origin,'-i',video,'-i',SOURCE,'-map','0:v:0','-map','1:a:0','-c','copy','-avoid_negative_ts','disabled',master])
    if not preview.exists():tools.call([tools.FF,'-v','error','-nostdin','-n','-copyts','-i',master,'-map','0:v:0','-map','0:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-avoid_negative_ts','disabled','-movflags','+faststart',preview])
    if not runtime.exists():
        print('ENCODE runtime VP8',flush=True)
        tools.call([tools.FF,'-v','error','-nostdin','-n','-threads','2','-copyts','-i',master,'-map','0:v:0','-map','0:a:0',
            '-c:v','libvpx','-crf','4','-b:v','30M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2',
            '-pix_fmt','yuv420p','-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',runtime])
    probes={}
    for role,path in [('preview',preview),('master',master),('game_ready',runtime)]:
        p=tools.probe(path);v=next(s for s in p['streams'] if s['codec_type']=='video')
        assert (v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'])==(1920,1080,count,'30/1')
        stamps=tools.frames(path);assert np.max(np.abs(stamps-(origin+np.arange(count)/30)))<.0011
        probes[role]=p
    audio=tools.audio(SOURCE)
    for path in (master,runtime):
        actual=tools.audio(path);assert audio[:2]==actual[:2] and len(audio[2])==len(actual[2])
        assert np.max(np.abs(audio[2]-actual[2]))<=.0011
    graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
    check=subprocess.run([tools.FF,'-hide_banner','-nostdin','-threads','2','-i',str(master),'-threads','2','-i',str(runtime),
        '-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
    (FINAL/'ssim.log').write_text(check.stderr,encoding='utf-8');ssim=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert ssim>.99
    for sec in (2,6,10,13.15,13.25,15,15.8):
        tools.call([tools.FF,'-v','error','-nostdin','-n','-ss',sec,'-i',preview,'-frames:v','1',FINAL/f'check-{sec:g}s.png'])
    result=dict(asset_key='movie:default:RASAADMI',state='runtime-ready',source='video/rasaadmi/rasaadmi.wbm',source_sha256=tools.sha(SOURCE),
        dimensions=[1920,1080],fps='30/1',frames=count,duration_s=count/30,video_origin_s=origin,native_frames=403,ssim_sampled_all=ssim,
        native_audio_pcm_identical=True,native_audio_encoded_identical=True,full_frame_decode=True,probes=probes,
        tested_intermediate_frames=402,novel_intermediate_frames=novel,
        files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=tools.sha(path),bytes=path.stat().st_size) for role,path in [('preview',preview),('master',master),('game_ready',runtime)]},
        user_visual_qa='pending',ingame_qa='not-performed',installed=False,release_integration=False)
    tools.save(FINAL/'verification.json',result);tools.save(RECIPE/'metadata/manifest.json',result);tools.save(ROOT/'video/index/rasaadmi-finals30-20261112-v1.json',result)
    print('RASAADMI_READY',count,'frames SSIM',ssim,flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['part','final']);p.add_argument('--number',type=int);a=p.parse_args()
    if a.action=='part':part(a.number)
    else:final()
