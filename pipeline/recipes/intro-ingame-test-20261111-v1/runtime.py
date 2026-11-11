"""Prepare and atomically install only INTRO EN/default, DE and PL plus CLUA test aliases."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json,os,re,shutil,subprocess,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
RUN=ROOT/'video/intro/runs/intro-locales-ingame-20261111-v1'
RECEIPT=ROOT/'video/installations/intro-locales-seedvr-20261111-v1'
SPECS=[
    ('default','video/assembly/intro-locales-seedvr-1080-20261111-v1/default/INTRO-default-SeedVR2-1080-native-audio.mkv',3347,'movies/intro.wbm','HDINEN'),
    ('de_DE','video/assembly/intro-locales-seedvr-1080-20261111-v1/de_DE/INTRO-de_DE-SeedVR2-1080-native-audio.mkv',3345,'lang/de_DE/movies/intro.wbm','HDINDE'),
    ('pl_PL','video/assembly/intro-polish-master30-20261111-v1/INTRO-pl_PL-SeedVR2-shared-master-1080p2997-native-audio.mkv',3440,'lang/pl_PL/movies/INTRO.wbm','HDINPL')]


def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def call(args):
    p=subprocess.run([str(a) for a in args],capture_output=True)
    if p.returncode:raise RuntimeError(p.stderr.decode('utf-8',errors='replace'))
    return p.stdout.decode('utf-8',errors='replace')
def pcm(p):return call(['ffmpeg','-v','error','-i',p,'-map','0:a:0','-vn','-c:a','pcm_s16le','-f','hash','-hash','sha256','-']).strip()
def stopped():
    text=call(['powershell','-NoProfile','-Command',"$p=Get-Process | Where-Object {$_.ProcessName -match '^(Baldur.*|BGMain|BG2.*|InfinityLoader.*)$'}; if($p){$p | Select-Object Id,ProcessName | ConvertTo-Json -Compress}"])
    if text.strip():raise RuntimeError('Close game and InfinityLoader before installation: '+text)


def encode(spec):
    locale,relative,count,target,alias=spec;folder=RUN/locale;folder.mkdir()
    source=ROOT/relative;output=folder/'intro.wbm'
    command=['ffmpeg','-hide_banner','-nostdin','-n','-threads','2','-copyts','-i',str(source),
        '-map','0:v:0','-map','0:a:0','-map_metadata','-1','-c:v','libvpx','-crf','4','-b:v','30M',
        '-qmin','0','-qmax','12','-deadline','good','-cpu-used','2','-threads','2','-pix_fmt','yuv420p',
        '-fps_mode','passthrough','-enc_time_base','1:1000000','-c:a','copy','-avoid_negative_ts','disabled','-f','webm',str(output)]
    print('ENCODE',locale,flush=True)
    with (folder/'encode.log').open('wb') as log:subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,check=True)
    info=json.loads(call(['ffprobe','-v','error','-count_frames','-show_entries',
        'stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames:format=duration,format_name,size','-of','json',output]))
    v=next(x for x in info['streams'] if x['codec_type']=='video');a=next(x for x in info['streams'] if x['codec_type']=='audio')
    assert (v['codec_name'],v['width'],v['height'],v['r_frame_rate'],int(v['nb_read_frames']),a['codec_name'])==('vp8',1920,1080,'30000/1001',count,'vorbis'),info
    source_pcm=pcm(source);assert pcm(output)==source_pcm,'PCM changed'
    graph='[0:v]settb=AVTB,setpts=N*1001/(30000*TB)[a];[1:v]settb=AVTB,setpts=N*1001/(30000*TB)[b];[a][b]ssim=shortest=1[v]'
    check=subprocess.run(['ffmpeg','-hide_banner','-nostdin','-threads','2','-i',str(source),'-threads','2','-i',str(output),
        '-filter_complex_threads','1','-filter_complex',graph,'-map','[v]','-an','-f','null','NUL'],capture_output=True,text=True,encoding='utf-8',errors='replace',check=True)
    (folder/'ssim.log').write_text(check.stderr,encoding='utf-8');m=re.search(r'All:([0-9.]+)',check.stderr);assert m
    score=float(m[1]);assert score>.99,(locale,score)
    # Keep native audio packet timing, including language-specific tails.
    audio_pts=[]
    for path in [source,output]:
        packets=json.loads(call(['ffprobe','-v','error','-select_streams','a:0','-show_packets','-show_entries','packet=pts_time','-of','json',path]))['packets']
        audio_pts.append([float(p['pts_time']) for p in packets])
    assert len(audio_pts[0])==len(audio_pts[1]);drift=max(abs(a-b) for a,b in zip(*audio_pts));assert drift<=.0011,drift
    result=dict(locale=locale,source=relative,source_sha256=sha(source),output=output.relative_to(ROOT).as_posix(),output_sha256=sha(output),
        target='config://bg2ee_game_root/'+target,alias=alias,frames=count,probe=info,ssim_all=score,
        native_audio_pcm_identical=True,pcm_hash=source_pcm,max_audio_packet_pts_deviation_s=drift,
        command=command,quality='VP8 CRF4/qmax12/cpu-used2; no new inference or interpolation',qa_ingame='pending-user',release_integration=False)
    save(folder/'encoding.json',result);print('VERIFIED',locale,'SSIM',score,flush=True)
    return result


def prepare():
    RUN.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(encode,SPECS))
    save(RUN/'encoding.json',dict(state='runtime-verified',variants=results,qa_ingame='pending-user',release_integration=False))
    print('THREE_INTRO_RUNTIMES_READY',flush=True)


def install():
    data=json.loads((RUN/'encoding.json').read_text());assert data['state']=='runtime-verified'
    game=get_path('bg2ee_game_root',required=True).resolve();stopped()
    RECEIPT.mkdir(parents=True,exist_ok=False)
    entries=[]
    for spec,e in zip(SPECS,data['variants']):
        locale,relative,count,relative_target,alias=spec;source=ROOT/e['output'];assert sha(source)==e['output_sha256']
        assert e['ssim_all']>.99 and e['native_audio_pcm_identical']
        for role,rel in [('localized-movie',relative_target),('console-test-alias',f'movies/{alias}.wbm')]:
            target=(game/rel).resolve();assert target.is_relative_to(game) and target.suffix.lower()=='.wbm'
            existed=target.is_file()
            assert existed if role=='localized-movie' else not existed,(role,target)
            before=None;backup=None
            if existed:
                backup=RECEIPT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True)
                before=sha(target);shutil.copy2(target,backup);assert sha(backup)==before
            entries.append(dict(locale=locale,role=role,target='config://bg2ee_game_root/'+rel,resolved_target=str(target),
                existed_before=existed,backup=backup.relative_to(ROOT).as_posix() if backup else None,
                before_sha256=before,source=e['output'],after_sha256=e['output_sha256'],state='backed-up' if existed else 'new-alias'))
    receipt=dict(schema='bg2-intro-local-install-v1',state='backed-up',entries=entries,qa_ingame='pending-user',release_integration=False)
    rp=RECEIPT/'installation.json';save(rp,receipt)
    for e in entries:
        stopped();target=Path(e['resolved_target']);source=ROOT/e['source']
        assert (sha(target)==e['before_sha256']) if e['existed_before'] else not target.exists(),'Concurrent target change'
        temp=target.with_name(target.name+'.bg2hd-intro-20261111-v1.tmp');assert not temp.exists()
        shutil.copy2(source,temp);assert sha(temp)==e['after_sha256'];stopped();os.replace(temp,target)
        assert sha(target)==e['after_sha256'];e['state']='installed';save(rp,receipt)
    receipt.update(state='installed',installed_utc=datetime.now(timezone.utc).isoformat());save(rp,receipt)
    print('INSTALLED_INTRO_AND_TEST_ALIASES',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','install']);a=p.parse_args()
    {'prepare':prepare,'install':install}[a.action]()
