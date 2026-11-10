"""Decode candidate bytes and compare targeted invariants against immutable parents."""
from prepare import ROOT,BASE,OUT,load,save
from masks import PAD
from correct import parent,before_frame,sha
from fractions import Fraction
from PIL import Image
import numpy as np
import hashlib,collections,argparse,time
import effect_workflow as workflow

checked_png=set()

def png(path,array):
    path=OUT/'review'/path
    expected=sha(array.tobytes()+str(array.shape).encode())
    assert path.stem==expected
    if path in checked_png:return False
    valid=False
    if path.exists():
        try:
            with Image.open(path) as im:valid=np.array_equal(np.asarray(im.convert('RGBA')),array)
        except (OSError,ValueError):pass
    if not valid:
        # Interrupted working previews may leave a partial PNG; immutable parents are never touched.
        Image.fromarray(array).save(path,compress_level=2)
    checked_png.add(path)
    return not valid

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--job',action='append');args=parser.parse_args()
    jobs=[a for a in load(OUT/'plan.json')['jobs'] if not args.job or a['job_id'] in args.job];reports=[];repaired=0
    verifier_sha=workflow.sha256_file(__import__('pathlib').Path(__file__))
    for a in jobs:
        result_file=OUT/'results'/f'{a["job_id"]}.json';cache=OUT/'verification'/f'{a["job_id"]}.json'
        while not result_file.exists():
            state=load(OUT/'progress.json')
            if state.get(a['job_id'],{}).get('state')=='failed':raise RuntimeError(state[a['job_id']])
            time.sleep(2)
        result_sha=workflow.sha256_file(result_file)
        if cache.exists():
            previous=load(cache)
            if previous.get('result_sha256')==result_sha and previous.get('verifier_sha256')==verifier_sha:
                reports.append(previous);continue
        r=load(result_file);stage,m,sp,anchor=parent(a)
        assert r['parent_interpolation']['sha256']==__import__('effect_workflow').sha256_file(stage/'manifest.json')
        w,h=r['size_x4'];frames=r['frames'];changes=0;hold=0;blank=0;max_error=0
        masks=None
        if a['smooth']:
            z=np.load(OUT/'masks'/a['resref']/'masks.npz');masks={int(k):z[k] for k in z.files}
        native_cache={}
        for profile,old_profile in zip(r['profiles'],m['timing']['cycles'],strict=True):
            assert profile['id']==old_profile['id']
            assert profile['duration_rational']==old_profile['duration_rational']
            assert sum(Fraction(*d) for d in profile['phase_durations_rational'])==Fraction(*profile['duration_rational'])
            selected=[f for f in frames if f['profile']==profile['id']]
            assert len(selected)==len(old_profile['timeline_frame_indices'])==profile['phases']
            source=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'00-frames-x1/rgba'
            for path,k in zip(profile['native'],old_profile['native_slots'],strict=True):
                if k not in native_cache:
                    small=np.array(Image.open(source/f'frame_{k:03d}.png').convert('RGBA'))
                    n=np.pad(small.repeat(4,0).repeat(4,1),((PAD,PAD),(PAD,PAD),(0,0)));n[n[:,:,3]==0]=0
                    native_cache[k]=n
                    repaired+=png(path,n)
            previous=None
            for f,old_index in zip(selected,old_profile['timeline_frame_indices'],strict=True):
                oldf=m['frames'][old_index];before=before_frame(stage,oldf,sp,anchor)
                repaired+=png(f['before'],before)
                p=ROOT/f['straight']['path'];data=p.read_bytes()
                if sha(data)!=f['straight']['sha256'] or len(data)!=w*h*4:
                    with Image.open(OUT/'review'/f['after']) as im:normal=np.array(im.convert('RGBA'))
                    assert normal.shape==(h,w,4) and sha(normal.tobytes())==f['straight']['sha256']
                    p.write_bytes(normal.tobytes());data=normal.tobytes();repaired+=1
                normal=np.frombuffer(data,np.uint8).reshape(h,w,4)
                repaired+=png(f['after'],normal)
                primary=normal.copy();primary[:,:,:3]=np.rint(normal[:,:,:3].astype(float)*normal[:,:,3:4]/255).astype(np.uint8)
                raw=ROOT/f['premultiplied']['path'];payload=raw.read_bytes()
                if sha(payload)!=f['premultiplied']['sha256'] or len(payload)!=w*h*4:
                    assert sha(primary.tobytes())==f['premultiplied']['sha256']
                    raw.write_bytes(primary.tobytes());payload=primary.tobytes();repaired+=1
                prem=np.frombuffer(payload,np.uint8).reshape(h,w,4)
                assert np.array_equal(prem[:,:,3],normal[:,:,3]) and np.all(prem[:,:,:3]<=prem[:,:,3:4])
                assert not normal[normal[:,:,3]==0].any() and not prem[prem[:,:,3]==0].any()
                error=int(np.abs(primary.astype(np.int16)-prem.astype(np.int16)).max());assert error<=1;max_error=max(max_error,error)
                assert not normal[[0,-1],:].any() and not normal[:,[0,-1]].any()
                if a['smooth']:
                    left,right=f['temporal_source_frames'];t=f['temporal_fraction']
                    expected=np.rint(masks[left].astype(float)*(1-t)+masks[right].astype(float)*t).astype(np.uint8)
                    assert np.array_equal(normal[:,:,3],expected),(a['job_id'],profile['id'],f['phase'],'smoothed alpha')
                if a['smooth'] and not a['rebout'] and not a['retime']:
                    shared=(normal[:,:,3]>0)&(before[:,:,3]>0)
                    assert np.array_equal(normal[:,:,:3][shared],before[:,:,:3][shared])
                if not a['changed']:assert np.array_equal(normal,before)
                if a['black_neutral']:
                    assert r['black_premultiplied_flux_max_error']<=1
                    if not a['retime']:
                        black=before[:,:,:3].max(2)==0;assert not normal[black].any()
                        old_prem=np.rint(before[:,:,:3].astype(float)*before[:,:,3:4]/255).astype(np.uint8)
                        assert np.abs(prem[:,:,:3].astype(int)-old_prem.astype(int)).max()<=1
                if a['retime']:
                    slots=old_profile['native_slots'];slot=f['phase']//2
                    assert f['temporal_source_frames'][0]==slots[slot]
                    if f['phase']%2==0:assert f['temporal_fraction']==0
                    else:assert f['temporal_fraction'] in (0,.5)
                current=f['straight']['sha256']
                if current==previous:
                    # A genuine native hold or invisible reserve is kept in time, with one stored image.
                    left,right=f['temporal_source_frames']
                    assert not normal.any() or (left==right and f['temporal_fraction']==0), (a['job_id'],profile['id'],f['phase'],'unexpected duplicate')
                    hold+=1
                previous=current
                if not normal.any():blank+=1
        if a['retime']:
            for p in r['profiles']:
                if not p['loop'] and a['ordinal'] in (12,20):
                    terminal=16 if a['ordinal']==12 else 40
                    seq=[f for f in frames if f['profile']==p['id']]
                    assert all(not np.fromfile(ROOT/f['straight']['path'],np.uint8).any() for f in seq[terminal:])
        report={'job_id':a['job_id'],'resref':a['resref'],'passed':True,'phases':len(frames),
            'result_sha256':result_sha,'verifier_sha256':verifier_sha,
            'durations_exact':True,'existing_rgb_exact_for_mask_only':a['smooth'] and not a['rebout'] and not a['retime'],
            'black_neutral':a['black_neutral'],'black_flux_error':r['black_premultiplied_flux_max_error'],
            'native_hold_or_blank_duplicate_slots':hold,'invisible_phases':blank,'premultiplied_roundtrip_max_error':max_error}
        reports.append(report);save(cache,report)
        print('VERIFY PASS',a['job_id'],flush=True)
    save(OUT/('verification-subset.json' if args.job else 'verification.json'),{'status':'passed','assets':len({a['resref'] for a in jobs}),'contexts':len(jobs),'corrected_assets':len({a['resref'] for a in jobs if a['changed']}),'corrected_contexts':sum(a['changed'] for a in jobs),
        'phases':sum(r['phases'] for r in reports),'partial_work_files_repaired':repaired,
        'all_native_durations_preserved':True,'unexpected_duplicates':0,'qa':'pending-user-preview','installed':False,'results':reports})
    print(len(jobs),'contexts independently verified;',repaired,'interrupted work files repaired',flush=True)

if __name__=='__main__':main()
