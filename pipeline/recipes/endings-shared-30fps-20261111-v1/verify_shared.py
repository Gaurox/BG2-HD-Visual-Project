"""Check real Apollo in-between frames, shared VP8 bytes, and SeedVR portion joins."""
import json
import numpy as np
from produce import ROOT, RECIPE, AUDIT, FINAL, FF, call, save, run_dir

def small(path,first=0,last=None):
    filters=[]
    if last is not None:filters.append(f'select=between(n\\,{first}\\,{last})')
    filters.append('scale=160:90:flags=area,format=gray')
    return np.frombuffer(call([FF,'-v','error','-threads','2','-i',path,'-an','-vf',','.join(filters),
        '-threads','1','-fps_mode','passthrough','-f','rawvideo','-']),np.uint8).reshape(-1,90,160).astype(np.float32)

def main():
    manifest=json.loads((FINAL/'manifest.json').read_text());results=[]
    for master in manifest['masters']:
        film=master['film'];folder=run_dir(film);seed=json.loads((folder/'run.json').read_text())
        native=np.fromfile(AUDIT/f'{film}-default.gray',np.uint8).reshape(-1,90,160).astype(np.float32)
        upscaled=small(folder/seed['output']);assert len(native)==len(upscaled)
        before=np.abs(np.diff(native,axis=0)).mean(axis=(1,2));after=np.abs(np.diff(upscaled,axis=0)).mean(axis=(1,2))
        joins=[dict(frame=n,native_adjacent_mae=float(before[n-1]),seedvr_adjacent_mae=float(after[n-1]),
            seedvr_local_median=float(np.median(after[n-6:n+5]))) for n in range(330,len(native),330)]
        second=40 if film=='END15FPS' else 8
        s=small(folder/seed['output'],second*15,second*15+30)
        o=small(ROOT/master['output'],second*30,second*30+60)
        assert len(s)==31 and len(o)==61
        left=np.abs(o[1::2]-o[:-1:2]).mean(axis=(1,2));right=np.abs(o[1::2]-o[2::2]).mean(axis=(1,2))
        novel=int(((left>.01)&(right>.01)).sum());assert novel>0
        group=[v for v in manifest['variants'] if v['film']==film and v['locale']!='pl_PL']
        hashes={v['locale']:call([FF,'-v','error','-i',ROOT/v['files']['game_ready']['path'],
            '-map','0:v:0','-an','-c:v','copy','-f','hash','-hash','sha256','-']).decode().strip() for v in group}
        assert len(set(hashes.values()))==1
        results.append(dict(film=film,apollo_check_second=second,tested_odd_frames=30,novel_odd_frames=novel,
            even_anchor_luma_mae=float(np.abs(s-o[::2]).mean()),seedvr_joins=joins,shared_vp8_hashes=hashes))
    report=dict(state='verified',results=results,user_visual_qa='pending',ingame_qa='pending')
    save(RECIPE/'metadata/shared-verification.json',report);save(FINAL/'shared-verification.json',report)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
