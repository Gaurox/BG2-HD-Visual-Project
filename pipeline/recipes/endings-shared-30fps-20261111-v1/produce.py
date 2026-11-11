"""Two shared SeedVR/Apollo masters, seven native-audio assemblies and game files."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import csv, hashlib, json, math, os, re, shutil, subprocess, sys, time
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
RECIPE = Path(__file__).resolve().parent
AUDIT = ROOT/'video/research/endings-locales-analysis-20261111-v1'
FINAL = ROOT/'video/final/endings-shared-30fps-20261111-v1'
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
FF = shutil.which('ffmpeg'); FP = shutil.which('ffprobe')
TOPAZ = get_path('topaz_video_ffmpeg', required=True)
MODELS = get_path('topaz_video_models', required=True)

def save(p, d):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def call(args):
    p = subprocess.run([str(x) for x in args], capture_output=True)
    if p.returncode: raise RuntimeError(p.stderr.decode('utf-8', errors='replace')[-10000:])
    return p.stdout

def sha(p):
    with Path(p).open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()

def run_dir(film):
    return ROOT/f'video/{film.lower()}/runs/{film.lower()}-shared-seedvr-apollo30-20261111-v1'

def frames(p):
    return np.array([float(f['best_effort_timestamp_time']) for f in json.loads(call([
        FP,'-v','error','-select_streams','v:0','-show_frames','-show_entries',
        'frame=best_effort_timestamp_time','-of','json',p]))['frames']])

def probe(p):
    return json.loads(call([FP,'-v','error','-count_frames','-show_streams','-show_format','-of','json',p]))

def audio(p):
    h = call([FF,'-v','error','-i',p,'-map','0:a:0','-c:a','pcm_s16le','-f','hash','-hash','sha256','-']).decode().strip()
    encoded = call([FF,'-v','error','-i',p,'-map','0:a:0','-c:a','copy','-f','hash','-hash','sha256','-']).decode().strip()
    packets = json.loads(call([FP,'-v','error','-select_streams','a:0','-show_packets',
        '-show_entries','packet=pts_time','-of','json',p]))['packets']
    return h, encoded, np.array([float(x['pts_time']) for x in packets])

def metadata(film, loc):
    return json.loads((AUDIT/f'{film}-{loc}.metadata.json').read_text(encoding='utf-8'))

def interpolate(film):
    folder = run_dir(film); ready = folder/'apollo-verification.json'
    if ready.exists():
        report = json.loads(ready.read_text()); assert sha(ROOT/report['output']) == report['sha256']
        return report
    seed = json.loads((folder/'run.json').read_text()); assert seed['status']=='inference-completed'
    source = folder/seed['output']; n = seed['frames']; count = n*2
    p = probe(source); v = next(s for s in p['streams'] if s['codec_type']=='video')
    assert (v['width'],v['height'],int(v['nb_read_frames'])) == (1920,1080,n)
    ts = frames(source); assert np.max(np.abs(ts-np.arange(n)/15)) < .002
    output = folder/f'{film}-shared-SeedVR2-Apollo8-1080p30.mp4'
    assert not output.exists(), output
    producer = [str(TOPAZ),'-hide_banner','-nostdin','-n','-threads','8','-i',str(source),
        '-map','0:v:0','-an','-vf',
        'setpts=N/(15*TB),format=rgb24,tvai_fi=model=apo-8:fps=30:slowmo=1:rdt=-0.01:device=0:vram=0.8:instances=0:download=0,setpts=N/(30*TB),format=gbrp16le',
        '-c:v','rawvideo','-pix_fmt','gbrp16le','-fps_mode','passthrough','-f','rawvideo','pipe:1']
    consumer = [FF,'-hide_banner','-nostdin','-n','-f','rawvideo','-pixel_format','gbrp16le',
        '-video_size','1920x1080','-framerate','30','-i','pipe:0','-an','-vf',
        f'tpad=stop_mode=clone:stop_duration=0.033333333,trim=end_frame={count},setpts=N/(30*TB),scale=in_range=pc:out_range=tv:out_color_matrix=bt601,format=yuv420p',
        '-c:v','libx264','-crf','14','-preset','slow','-threads','4','-fps_mode','passthrough',
        '-video_track_timescale','1000000','-color_range','tv','-movflags','+faststart',str(output)]
    save(folder/'apollo-commands.json',[producer,consumer])
    env = os.environ.copy(); env.update(TVAI_MODEL_DIR=str(MODELS),TVAI_MODEL_DATA_DIR=str(MODELS))
    env['PATH']=str(TOPAZ.parent)+os.pathsep+env.get('PATH','')
    print('APOLLO',film,n,'->',count,flush=True)
    with (folder/'apollo.log').open('wb') as a, (folder/'apollo-encode.log').open('wb') as b:
        pr=subprocess.Popen(producer,stdout=subprocess.PIPE,stderr=a,env=env)
        co=subprocess.Popen(consumer,stdin=pr.stdout,stdout=b,stderr=b);pr.stdout.close()
        cr=co.wait()
        if cr and pr.poll() is None:pr.terminate()
        rc=pr.wait()
    assert rc==cr==0,(rc,cr)
    generated=int(re.findall(r'frame=\s*(\d+)',(folder/'apollo.log').read_text(errors='replace'))[-1])
    assert generated==2*n-1,generated
    stamps=frames(output);assert len(stamps)==count
    assert np.max(np.abs(stamps-np.arange(count)/30))<.000002
    report=dict(film=film,output=output.relative_to(ROOT).as_posix(),sha256=sha(output),
        frames=count,apollo_generated_frames=generated,fps='30/1',final_hold_frames=1,
        model='apo-8',spatial_source=source.relative_to(ROOT).as_posix(),user_visual_qa='pending')
    save(ready,report);return report

def polish_mapping(film):
    """Full-frame luma MAE + sparse edit penalty, monotone; fade uses known index order."""
    a=metadata(film,'default');b=metadata(film,'pl_PL')
    n,m=a['frames'],b['frames']
    if film=='MELISSAN':return np.minimum(np.arange(m),n-1)
    x=np.memmap(AUDIT/f'{film}-default.gray',np.uint8,'r',shape=(n,90,160))
    y=np.memmap(AUDIT/f'{film}-pl_PL.gray',np.uint8,'r',shape=(m,90,160))
    cost=np.full((m,n),np.inf,np.float32);prev=np.full((m,n),-1,np.int32)
    for j in range(m):
        for i in range(max(0,j-5),min(n,j+6)):
            err=float(np.abs(y[j].astype(np.int16)-x[i].astype(np.int16)).mean())
            if j==0:
                cost[j,i]=err+i*.5;continue
            choices=[(cost[j-1,k]+(.45 if i-k!=1 else 0),k) for k in (i-2,i-1,i) if 0<=k<n]
            value,k=min(choices);cost[j,i]=err+value;prev[j,i]=k
    i=min(range(max(0,n-5),n),key=lambda k:cost[-1,k]+(n-1-k)*.5)
    mapping=np.empty(m,np.int32)
    for j in range(m-1,-1,-1):mapping[j]=i;i=prev[j,i]
    assert np.all(np.diff(mapping)>=0) and mapping[-1]>=n-3
    return mapping

def polish_video(film,shared,folder):
    m=metadata(film,'pl_PL');source=ROOT/m['source'];n=m['frames']
    pts=np.array([float(x['best_effort_timestamp_time']) for x in json.loads((AUDIT/f'{film}-pl_PL.native-frame-times.json').read_text())['frames']])
    mapped=polish_mapping(film)
    # Duplicate first PTS: keep the last source anchor at that instant.
    keep=np.r_[np.diff(pts)>0,True];anchors=pts[keep];positions=2*mapped[keep]
    count=math.ceil((pts[-1]+1/15)*30-1e-7)
    selected=np.rint(np.interp(np.arange(count)/30,anchors,positions)).astype(int)
    selected=np.clip(selected,0,shared['frames']-1)
    assert np.all(np.diff(selected)>=0)
    save(folder/'native-mapping.json',dict(native_pts_s=pts.tolist(),native_to_default_frame=mapped.tolist(),
        master30_selected_frames=selected.tolist(),frames=count,
        method='monotone luma/edit alignment END; same-index 525 content frames then hold MEL; native PTS anchors sampled at 30fps',
        source_duplicate_pts_kept_in_evidence=True,appearance='shared default master'))
    output=folder/f'{film}-pl_PL-1080p30-video.mp4';assert not output.exists()
    master=ROOT/shared['output'];size=1920*1080*3//2
    decode=[FF,'-v','error','-threads','2','-i',str(master),'-an','-pix_fmt','yuv420p','-threads','1','-fps_mode','passthrough','-f','rawvideo','pipe:1']
    encode=[FF,'-hide_banner','-nostdin','-n','-f','rawvideo','-pixel_format','yuv420p','-video_size','1920x1080',
        '-framerate','30','-i','pipe:0','-an','-c:v','libx264','-crf','12','-preset','medium','-threads','4',
        '-video_track_timescale','1000000','-movflags','+faststart',str(output)]
    save(folder/'retime-commands.json',[decode,encode])
    with (folder/'retime.log').open('wb') as log:
        dec=subprocess.Popen(decode,stdout=subprocess.PIPE,stderr=log)
        enc=subprocess.Popen(encode,stdin=subprocess.PIPE,stdout=log,stderr=log)
        current=-1;frame=None
        try:
            for target in selected:
                while current<target:
                    chunks=[];remaining=size
                    while remaining:
                        data=dec.stdout.read(remaining)
                        if not data:raise RuntimeError('Shared decoder EOF')
                        chunks.append(data);remaining-=len(data)
                    frame=b''.join(chunks);current+=1
                enc.stdin.write(frame)
        finally:
            enc.stdin.close();dec.stdout.close()
            if dec.poll() is None:dec.terminate()
            dec.wait()
        assert enc.wait()==0
    return output,count,0.0

def build(film,loc,shared,runtime_reference=None):
    folder=FINAL/film/loc;folder.mkdir(parents=True,exist_ok=True);vp=folder/'verification.json'
    if vp.exists():
        res=json.loads(vp.read_text())
        for f in res['files'].values():assert sha(ROOT/f['path'])==f['sha256']
        return res
    m=metadata(film,loc);native=ROOT/m['source'];assert sha(native).upper()==m['source_sha256']
    if loc=='pl_PL':selected,count,origin=polish_video(film,shared,folder)
    else:
        selected=ROOT/shared['output'];count=shared['frames']
        origin=float(json.loads((AUDIT/f'{film}-{loc}.native-frame-times.json').read_text())['frames'][0]['best_effort_timestamp_time'])
    master=folder/f'{film}-{loc}-1080p30-native-audio.mkv'
    preview=folder/f'{film}-{loc}-1080p30-audio.mp4';runtime=folder/(film.lower()+'.wbm')
    assert not master.exists()
    call([FF,'-v','error','-nostdin','-n','-copyts','-itsoffset',origin,'-i',selected,'-i',native,
        '-map','0:v:0','-map','1:a:0','-map_metadata','-1','-c','copy','-avoid_negative_ts','disabled',master])
    call([FF,'-v','error','-nostdin','-n','-copyts','-i',master,'-map','0:v:0','-map','0:a:0',
        '-c:v','copy','-c:a','aac','-b:a','192k','-avoid_negative_ts','disabled','-movflags','+faststart',preview])
    command=[FF,'-hide_banner','-nostdin','-n','-threads','2','-copyts','-i',str(master),
        '-map','0:v:0','-map','0:a:0','-map_metadata','-1','-c:v','libvpx','-crf','4','-b:v','30M',
        '-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2','-pix_fmt','yuv420p',
        '-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',str(runtime)]
    if runtime_reference is not None:
        base=runtime_reference.result();base_runtime=ROOT/base['files']['game_ready']['path']
        base_origin=float(json.loads((AUDIT/f'{film}-default.native-frame-times.json').read_text())['frames'][0]['best_effort_timestamp_time'])
        command=[FF,'-v','error','-nostdin','-n','-copyts','-itsoffset',str(round(origin-base_origin,6)),
            '-i',str(base_runtime),'-i',str(native),'-map','0:v:0','-map','1:a:0','-c','copy',
            '-map_metadata','-1','-avoid_negative_ts','disabled','-f','webm',str(runtime)]
    save(folder/'encoding-command.json',command);print('RUNTIME',film,loc,flush=True)
    with (folder/'runtime.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    p=probe(runtime);v=next(s for s in p['streams'] if s['codec_type']=='video');a=next(s for s in p['streams'] if s['codec_type']=='audio')
    assert (v['codec_name'],v['width'],v['height'],int(v['nb_read_frames']),v['r_frame_rate'],a['codec_name'])==('vp8',1920,1080,count,'30/1','vorbis')
    reference=audio(native);audio_drift=0
    for path in (master,runtime):
        actual=audio(path);assert reference[:2]==actual[:2] and len(reference[2])==len(actual[2])
        audio_drift=max(audio_drift,float(np.max(np.abs(reference[2]-actual[2]))));assert audio_drift<=.0011
    stamps=frames(runtime);baseline=frames(master);assert len(stamps)==len(baseline)==count
    video_drift=float(np.max(np.abs(stamps-baseline)));assert video_drift<=.0011
    assert np.all(np.diff(stamps)>0) and np.max(np.abs(stamps-(origin+np.arange(count)/30)))<=.0011
    graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
    check=subprocess.run([FF,'-hide_banner','-nostdin','-threads','2','-i',str(master),'-threads','2','-i',str(runtime),
        '-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
    (folder/'ssim-sampled.log').write_text(check.stderr,encoding='utf-8')
    score=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert score>.99
    for sec in ([1,30,60,110,121] if film=='END15FPS' else [1,19,28,34,36] if loc=='pl_PL' else [1,19,28,34]):
        call([FF,'-v','error','-nostdin','-n','-ss',sec,'-i',runtime,'-frames:v','1',folder/f'check-{sec}s.png'])
    target='movies/'+film.lower()+'.wbm' if loc=='default' else f'lang/{loc}/movies/'+(film+'.wbm' if loc=='pl_PL' else film.lower()+'.wbm')
    result=dict(film=film,locale=loc,frames=count,fps='30/1',dimensions=[1920,1080],
        source=m['source'],shared_master=shared['output'],target='config://bg2ee_game_root/'+target,
        files={role:dict(path=path.relative_to(ROOT).as_posix(),sha256=sha(path),bytes=path.stat().st_size) for role,path in [('preview',preview),('native_audio_master',master),('game_ready',runtime)]},
        native_audio_pcm_identical=True,native_audio_encoded_identical=True,audio_packets=len(reference[2]),
        max_audio_pts_deviation_s=audio_drift,max_video_pts_deviation_s=video_drift,
        ssim_sampled_all=score,full_frame_decode=True,probe=p,user_visual_qa='pending',runtime_ingame_qa='pending',installed_by_this_run=False,release_integration=False)
    save(vp,result);print('READY',film,loc,count,'SSIM',score,flush=True);return result

def main():
    assert not (FINAL/'manifest.json').exists(),'Final manifest immutable'
    futures=[];masters=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for film in ('END15FPS','MELISSAN'):
            folder=run_dir(film)
            if not (folder/'run.json').exists():subprocess.run([sys.executable,'-B',str(RECIPE/'seedvr.py'),'--film',film],check=True)
            deadline=time.monotonic()+7200
            while json.loads((folder/'run.json').read_text())['status']=='running':
                assert time.monotonic()<deadline,'Existing SeedVR job timed out'
                time.sleep(10)
            assert json.loads((folder/'run.json').read_text())['status']=='inference-completed'
            master=interpolate(film);masters.append(master)
            base=pool.submit(build,film,'default',master);futures.append(base)
            for loc in (['de_DE','it_IT','pl_PL'] if film=='END15FPS' else ['de_DE','pl_PL']):
                futures.append(pool.submit(build,film,loc,master,None if loc=='pl_PL' else base))
        variants=[f.result() for f in futures]
    report=dict(schema='endings-shared-finals30-v1',state='runtime-ready',created_utc=datetime.now(timezone.utc).isoformat(),
        masters=masters,variants=variants,shared_spatial_passes=2,shared_apollo_passes=2,installed=False,release_integration=False)
    save(FINAL/'manifest.json',report);save(RECIPE/'metadata/manifest.json',report)
    save(ROOT/'video/index/endings-finals30-20261111-v1.json',report)
    print('ALL_SEVEN_ENDINGS_READY',flush=True)

if __name__=='__main__':main()
