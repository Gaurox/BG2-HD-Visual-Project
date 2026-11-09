"""Preserve RESTDUNG settings before authorized test-media cleanup; encode game WBM."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
HERE=Path(__file__).resolve().parent
ASSET=ROOT/'video/restdung'
RUNS=ASSET/'runs'
SELECTED=RUNS/'restdung-seedvr-reference-20261109-v1'
MP4=SELECTED/'SeedVR2-RESTDUNG-3B-FP16-LAB-1080p15.mp4'
SOURCE=ASSET/'restdung.wbm'
RUNTIME=RUNS/'restdung-seedvr-ingame-20261109-v1'
FF=Path(shutil.which('ffmpeg'))
PROBE=FF.with_name('ffprobe.exe')

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def main():
    memory=HERE/'settings-memory';memory.mkdir(exist_ok=False)
    # Exact text snapshots; small, sufficient to reproduce discarded experiments.
    for folder in [RUNS,ASSET/'analysis']:
        for f in folder.rglob('*'):
            if f.is_file() and f.suffix.lower() in {'.json','.py','.log','.txt','.md','.csv'}:
                dest=memory/f.relative_to(ASSET);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    old=RUNS/'restdung-comfyui-experiment-20260814/ComfyUI_00001_.mp4'
    result=subprocess.run([str(PROBE),'-v','error','-show_entries','format_tags','-of','json',str(old)],capture_output=True,text=True,check=True)
    tags=json.loads(result.stdout)['format']['tags']
    for key in ['prompt','workflow']:
        (HERE/f'seedvr-original-{key}.json').write_text(json.dumps(json.loads(tags[key]),ensure_ascii=False,indent=2),encoding='utf-8')
    discarded=[]
    for d in sorted(RUNS.iterdir()):
        if d.is_dir() and d!=SELECTED:
            discarded.append({'path':d.relative_to(ROOT).as_posix(),'bytes':sum(f.stat().st_size for f in d.rglob('*')if f.is_file())})
    manifest={'scope':'RESTDUNG only','selected':{'path':MP4.relative_to(ROOT).as_posix(),'sha256':digest(MP4),'historical_parent_sha256':digest(old)},'source':{'path':SOURCE.relative_to(ROOT).as_posix(),'sha256':digest(SOURCE)},'discarded_test_directories':discarded,'text_memory':memory.relative_to(ROOT).as_posix(),'status':'prepared-not-deleted'}
    (HERE/'cleanup.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    # Keep the original preview independent of discarded A/B runs.
    preview=ASSET/'source-preview-720p15.mp4'
    shutil.copy2(RUNS/'restdung-topaz-ab-20261109-v1/Source-originale-720p15.mp4',preview)
    RUNTIME.mkdir(exist_ok=False)
    target=RUNTIME/'restdung.wbm'
    cmd=[str(FF),'-hide_banner','-nostdin','-n','-i',str(MP4),'-i',str(SOURCE),'-map','0:v:0','-map','1:a:0','-c:v','libvpx','-crf','4','-b:v','20M','-qmin','0','-qmax','12','-deadline','good','-cpu-used','0','-pix_fmt','yuv420p','-fps_mode','passthrough','-c:a','copy','-f','webm',str(target)]
    print('ENCODE_RUNTIME',flush=True)
    with (RUNTIME/'encode.log').open('w',encoding='utf-8') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
    p=subprocess.run([str(PROBE),'-v','error','-count_frames','-show_entries','stream=codec_type,codec_name,width,height,r_frame_rate,nb_read_frames:format=duration,format_name','-of','json',str(target)],capture_output=True,text=True,check=True)
    info=json.loads(p.stdout);v=next(s for s in info['streams']if s['codec_type']=='video');a=next(s for s in info['streams']if s['codec_type']=='audio')
    assert(v['codec_name'],v['width'],v['height'],v['r_frame_rate'],v['nb_read_frames'],a['codec_name'])==('vp8',1920,1080,'15/1','91','vorbis'),info
    report={'state':'runtime-encoded','qa_ingame':'not-performed','source':str(MP4.relative_to(ROOT)),'source_sha256':digest(MP4),'output':target.relative_to(ROOT).as_posix(),'output_sha256':digest(target),'probe':info,'command':cmd}
    (RUNTIME/'encoding.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(info),flush=True)
    print('READY_TO_INSTALL',target,flush=True)

if __name__=='__main__':main()
