"""Release the GPU after the first closed portion; preserve an explicit resume boundary."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,signal,subprocess,time

ROOT=Path(__file__).resolve().parents[3]
RUN=ROOT/'video/endcrdit/runs/endcrdit-seedvr-apollo30-20261111-v1'
PART=RUN/'portions/ENDCRDIT-common-part-01.mp4'

def main():
    deadline=time.monotonic()+1800
    while True:
        assert time.monotonic()<deadline,'First portion timeout'
        log=RUN/'seedvr-stream.log'
        if log.exists() and 'BG2_PORTION_SAVED 1 ' in log.read_text(encoding='utf-8',errors='replace'):break
        time.sleep(.1)
    run=json.loads((RUN/'run.json').read_text());assert run['status']=='running'
    assert run['film']=='ENDCRDIT' and run['source']=='video/endcrdit/endcrdit.wbm'
    p=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_streams','-of','json',str(PART)]))
    v=p['streams'][0];assert (v['width'],v['height'],int(v['nb_read_frames']))==(1920,1080,330)
    with PART.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
    pid=run['pid']
    checkpoint=dict(state='pause-requested',requested_by_user='une fois que tu m’as montré la premiere portion, peux tu mettre le travail en pause sans le perdre? j’ai besoin du GPU pour autre chose',
        requested_utc=datetime.now(timezone.utc).isoformat(),gpu_worker_pid=pid,
        kept_video=PART.relative_to(ROOT).as_posix(),kept_sha256=digest,kept_frames=330,
        kept_source_frames_inclusive=[0,329],next_source_frame=330,total_source_frames=run['frames'],
        remaining_source_frames=run['frames']-330,
        preserved_native_input=(RUN/'ENDCRDIT-common-native-input.mkv').relative_to(ROOT).as_posix(),
        preserved_mapping=(RUN/'frames.csv').relative_to(ROOT).as_posix(),
        resume_plan=dict(source_start_frame_with_context=297,context_frames=33,
            discard_resumed_context_frames=33,append_from_source_frame=330,
            retained_prefix_must_not_be_regenerated=True,join_text_review_required=True),
        full_seedvr_completed=False,apollo_started=False,installed=False,release_integration=False)
    cp=RUN/'pause-checkpoint.json'
    cp.write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.kill(pid,signal.SIGTERM)
    # The launcher records the intentional interruption, then its waiting finisher exits.
    deadline=time.monotonic()+60
    while time.monotonic()<deadline:
        try:latest=json.loads((RUN/'run.json').read_text())
        except json.JSONDecodeError:time.sleep(.2);continue
        if latest['status']!='running':break
        time.sleep(.2)
    assert latest['status']!='running','SeedVR launcher did not observe worker exit'
    checkpoint.update(state='paused',paused_utc=datetime.now(timezone.utc).isoformat(),launcher_exit_code=latest.get('exit_code'),
        worker_stop='Intentional termination after a complete, verified MP4 portion; GPU process exited')
    cp.write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'video/index/endcrdit-paused-20261111-v1.json').write_text(json.dumps(checkpoint,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('ENDCRDIT_PAUSED_FIRST_330_FRAMES_PRESERVED_GPU_WORKER_STOPPED',flush=True)

if __name__=='__main__':main()
