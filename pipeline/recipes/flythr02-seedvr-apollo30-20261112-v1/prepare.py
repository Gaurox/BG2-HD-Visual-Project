"""Keep every native frame; use a temporary 15fps clock for SeedVR only."""
from pathlib import Path
import importlib.util,json,csv
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
RECIPE=Path(__file__).resolve().parent
RUN=ROOT/'video/flythr02/runs/flythr02-seedvr-apollo30-20261112-v1'
SOURCE=ROOT/'video/flythr02/flythr02.wbm'
spec=importlib.util.spec_from_file_location('ending_tools',ROOT/'pipeline/recipes/endings-shared-30fps-20261111-v1/produce.py')
tools=importlib.util.module_from_spec(spec);spec.loader.exec_module(tools)

def main():
    assert not (RUN/'production.json').exists()
    RUN.mkdir(parents=True,exist_ok=True)
    pts=tools.frames(SOURCE);assert len(pts)==187 and np.all(np.diff(pts)>0)
    row=next(r for r in csv.DictReader((ROOT/'video/index/resources.csv').open(encoding='utf-8-sig')) if r['asset_key']=='movie:default:FLYTHR02')
    assert tools.sha(SOURCE).upper()==row['source_sha256'].upper()
    tools.save(RUN/'native-frame-times.json',pts.tolist())
    hashes=tools.call([tools.FF,'-v','error','-i',SOURCE,'-map','0:v:0','-an','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framemd5','-']).decode()
    native=[line.split(',')[-1].strip() for line in hashes.splitlines() if not line.startswith('#')]
    parts=[]
    for number,first,end,discard in [(1,0,187,0)]:
        name=f'BG2-FLYTHR02-20261112-v1-p{number:02d}.mkv'
        inp=RUN/'inputs'/name;inp.parent.mkdir(exist_ok=True)
        command=[tools.FF,'-v','error','-nostdin','-n','-threads','2','-i',SOURCE,'-map','0:v:0','-an','-vf',f'trim=start_frame={first}:end_frame={end},setpts=N/(15*TB)',
            '-c:v','ffv1','-level','3','-pix_fmt','yuv420p','-threads','2','-fps_mode','passthrough','-enc_time_base','1:1000000',inp]
        tools.call(command)
        actual=tools.call([tools.FF,'-v','error','-i',inp,'-map','0:v:0','-an','-pix_fmt','yuv420p','-fps_mode','passthrough','-f','framemd5','-']).decode()
        actual=[line.split(',')[-1].strip() for line in actual.splitlines() if not line.startswith('#')]
        assert actual==native[first:end]
        workflow=json.loads((ROOT/'pipeline/recipes/outro-seedvr-apollo30-20261112-v1/workflow-first-portion.api.json').read_text())
        workflow['21']['inputs']['file']=name
        workflow['23']['inputs']['filename_prefix']=f'BG2_video_upscale/flythr02-seedvr-apollo30-20261112-v1/FLYTHR02-p{number:02d}-SeedVR2-LAB'
        workflow['24']['inputs']['fps']=15
        wp=RUN/'workflows'/f'part-{number:02d}.api.json';tools.save(wp,workflow)
        parts.append(dict(number=number,first=first,end=end,discard=discard,kept=end-first-discard,input_frames=end-first,input=inp.relative_to(ROOT).as_posix(),workflow=wp.relative_to(ROOT).as_posix()))
    tools.save(RUN/'production.json',dict(source=SOURCE.relative_to(ROOT).as_posix(),source_sha256=tools.sha(SOURCE),native_frames=187,native_pts_s=pts.tolist(),parts=parts,profile='SeedVR2-3B-FP16-LAB1080-batch33-overlap3-seed42',state='prepared'))
    print('PREPARED 187 native frames; one portion; frame hashes identical')

if __name__=='__main__':main()
