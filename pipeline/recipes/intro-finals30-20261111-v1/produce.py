"""Build seven 30fps review/native-audio/runtime sets; no installation/release writes."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,shutil,subprocess,sys,time,re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/final/intro-30fps-20261111-v1'
RECIPE=Path(__file__).resolve().parent
INTERPOLATOR=ROOT/'pipeline/recipes/intro15f-default-apollo30-20261111-v1/produce.py'
ENC=shutil.which('ffmpeg');PROBE=shutil.which('ffprobe')

def call(args):
    p=subprocess.run([str(x) for x in args],capture_output=True,check=True)
    return p.stdout

def sha(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def save(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def probe(path):return json.loads(call([PROBE,'-v','error','-count_frames','-show_streams','-show_format','-of','json',path]))

def audio(path):
    pcm=call([ENC,'-v','error','-i',path,'-map','0:a:0','-c:a','pcm_s16le','-f','hash','-hash','sha256','-']).decode().strip()
    packets=json.loads(call([PROBE,'-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time','-of','json',path]))['packets']
    return pcm,[float(x['pts_time']) for x in packets]

def frames(path):
    return [float(f['best_effort_timestamp_time']) for f in json.loads(call([PROBE,'-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',path]))['frames']]

def video(p):return next(s for s in p['streams'] if s['codec_type']=='video')

def specs():
    data=[]
    installed=json.loads((ROOT/'video/intro/runs/intro-locales-ingame-20261111-v1/encoding.json').read_text())['variants']
    for e in installed:
        loc=e['locale']
        preview=(ROOT/'video/assembly/intro-polish-master30-20261111-v1/INTRO-pl_PL-SeedVR2-shared-master-1080p2997-audio.mp4' if loc=='pl_PL' else ROOT/f'video/assembly/intro-locales-seedvr-1080-20261111-v1/{loc}/INTRO-{loc}-SeedVR2-1080-audio.mp4')
        data.append(dict(film='INTRO',locale=loc,master=ROOT/e['source'],preview=preview,runtime=ROOT/e['output'],runtime_sha=e['output_sha256'],target=e['target'],fps='30000/1001',frames=e['frames']))
    for loc in ['default','de_DE','it_IT','pl_PL']:
        production=ROOT/f'video/intro15f/runs/intro15f-{loc}-apollo30-20261111-v1/production.json'
        source=json.loads((ROOT/f'video/research/intro-locales-analysis-20261110-v1/INTRO15F-{loc}.metadata.json').read_text())['source']
        target='movies/intro15f.wbm' if loc=='default' else f'lang/{loc}/movies/'+('INTRO15F.wbm' if loc=='pl_PL' else 'intro15f.wbm')
        data.append(dict(film='INTRO15F',locale=loc,production=production,native=ROOT/source,target='config://bg2ee_game_root/'+target,fps='30/1',frames=5147 if loc=='pl_PL' else 5148))
    return data

def build(spec):
    film=spec['film'];loc=spec['locale'];folder=RUN/film/loc;folder.mkdir(parents=True,exist_ok=True)
    result=folder/'verification.json'
    if result.exists():return json.loads(result.read_text())
    preview=folder/f'{film}-{loc}-1080p30-audio.mp4'
    master=folder/f'{film}-{loc}-1080p30-native-audio.mkv'
    runtime=folder/(film.lower()+'.wbm')
    if film=='INTRO':
        assert sha(spec['runtime'])==spec['runtime_sha']
        for src,dst in [(spec['preview'],preview),(spec['master'],master),(spec['runtime'],runtime)]:
            assert not dst.exists();shutil.copy2(src,dst)
        native=spec['master'];baseline=master
        encoding='Existing verified VP8/Vorbis bytes reused unchanged'
    else:
        prod=json.loads(spec['production'].read_text());assert prod['state']=='review-ready'
        selected=ROOT/prod['output'];assert sha(selected)==prod['output_sha256']
        assert not preview.exists();shutil.copy2(selected,preview)
        native=spec['native']
        call([ENC,'-v','error','-nostdin','-n','-copyts','-i',preview,'-i',native,
            '-map','0:v:0','-map','1:a:0','-c','copy','-map_metadata','-1','-avoid_negative_ts','disabled',master])
        command=[ENC,'-hide_banner','-nostdin','-n','-threads','2','-copyts','-i',str(master),
            '-map','0:v:0','-map','0:a:0','-map_metadata','-1','-c:v','libvpx','-crf','4','-b:v','30M',
            '-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2','-pix_fmt','yuv420p',
            '-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',str(runtime)]
        save(folder/'encoding-command.json',command)
        print('RUNTIME ENCODE',film,loc,flush=True)
        with (folder/'encode.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
        baseline=master;encoding='VP8 CRF4/30M/qmax12/cpu-used2; Vorbis stream copy'
    print('VERIFY',film,loc,flush=True)
    p=probe(runtime);v=video(p);a=next(s for s in p['streams'] if s['codec_type']=='audio')
    assert (v['codec_name'],v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']),a['codec_name'])==('vp8',1920,1080,spec['fps'],spec['frames'],'vorbis'),p
    assert v['pix_fmt']=='yuv420p' and p['format']['format_name']=='matroska,webm'
    ah=audio(native)
    for path in [master,runtime]:
        other=audio(path);assert ah[0]==other[0] and len(ah[1])==len(other[1])
        drift=max(abs(x-y) for x,y in zip(ah[1],other[1]));assert drift<=.0011
    ts0,ts1=frames(baseline),frames(runtime)
    assert len(ts0)==len(ts1)==spec['frames']
    video_drift=max(abs(x-y) for x,y in zip(ts0,ts1));assert video_drift<=.0011
    # One frame per second across the complete movie: verify VP8 delivery fidelity.
    graph="[0:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[a];[1:v]select='not(mod(n,30))',settb=AVTB,setpts=N/TB[b];[a][b]ssim=shortest=1[v]"
    check=subprocess.run([ENC,'-hide_banner','-nostdin','-threads','2','-i',str(baseline),'-threads','2','-i',str(runtime),
        '-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,check=True)
    (folder/'ssim-sampled.log').write_text(check.stderr)
    score=float(re.search(r'All:([0-9.]+)',check.stderr)[1]);assert score>.99,score
    for sec in [8,18.5,65] if film=='INTRO15F' else [3,7.5,65]:
        call([ENC,'-v','error','-nostdin','-n','-ss',sec,'-i',runtime,'-frames:v','1',folder/f'check-{sec:g}s.png'])
    res=dict(film=film,locale=loc,fps=spec['fps'],frames=spec['frames'],dimensions=[1920,1080],
        files={role:dict(path=path.relative_to(ROOT).as_posix(),bytes=path.stat().st_size,sha256=sha(path)) for role,path in [('preview',preview),('native_audio_master',master),('game_ready',runtime)]},
        target=spec['target'],encoding=encoding,probe=p,native_audio_pcm_identical=True,
        audio_packets=len(ah[1]),max_audio_pts_deviation_s=drift,max_video_pts_deviation_s=video_drift,
        ssim_sampled_all=score,full_frame_decode=True,user_visual_qa='accepted' if film=='INTRO15F' and loc=='default' else 'existing-INTRO-QA' if film=='INTRO' else 'pending',
        runtime_ingame_qa='pending',installed_by_this_run=False,release_integration=False)
    save(result,res);print('READY',film,loc,'SSIM',score,flush=True)
    return res

def main():
    assert not (RUN/'manifest.json').exists(),'Final production manifest is immutable; use a new run version'
    RUN.mkdir(parents=True,exist_ok=True)
    specifications=specs();futures=[]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for s in specifications[:4]:futures.append(pool.submit(build,s))
        for s in specifications[4:]:
            loc=s['locale'];print('INTERPOLATE',loc,flush=True)
            if loc=='de_DE' and s['production'].parent.exists():
                # First job was started by the foreground agent before this packager.
                deadline=time.monotonic()+1800
                while not s['production'].exists() or json.loads(s['production'].read_text())['state']!='review-ready':
                    assert time.monotonic()<deadline,'German foreground interpolation did not finish'
                    time.sleep(10)
            elif not s['production'].exists():
                subprocess.run([sys.executable,'-B',str(INTERPOLATOR),'--locale',loc],check=True)
            else:assert json.loads(s['production'].read_text())['state']=='review-ready'
            futures.append(pool.submit(build,s))
        results=[f.result() for f in futures]
    data=dict(schema='intro-finals30-v1',state='runtime-ready',created_utc=datetime.now(timezone.utc).isoformat(),
        scope='7 final filesets, no game/release writes',variants=results,installed=False,release_integration=False)
    save(RUN/'manifest.json',data)
    meta=RECIPE/'metadata';meta.mkdir(exist_ok=True)
    save(meta/'manifest.json',data)
    save(ROOT/'video/index/intro-finals30-20261111-v1.json',data)
    for s in specifications[3:]:
        save(meta/(s['locale']+'-apollo.json'),json.loads(s['production'].read_text()))
    print('ALL_SEVEN_FINALS_RUNTIME_READY',flush=True)

if __name__=='__main__':main()
