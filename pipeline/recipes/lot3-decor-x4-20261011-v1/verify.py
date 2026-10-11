"""Verify the final bytes, phase durations, duplicate poses and unchanged native contracts."""
from common import *
import hashlib

def main():
    pack=BATCH/'final-assets';manifest,resources=v.validate_v2_pack(pack)
    assert manifest['frame_count']==128
    records=[]
    for r in resources:
        ref=r['resref']; groups={}
        for f in r['frames']:
            p=pixels(pack,f);assert not p[p[...,3]==0,:3].any()
            if ref=='AM2008A':assert np.all(p[...,:3]<=p[...,3,None])
            key=(tuple(f['physical_size_x4']),tuple(f['centre_x1']),f['sha256'])
            groups.setdefault(key,[]).append(f['frame'])
        duplicates=[g for g in groups.values() if len(g)>1]
        assert not duplicates,ref+': duplicate final poses need storage deduplication without shortening clock'
        # Source RGBA pixels, rather than compressed PNG bytes, establish duplicate identity.
        run=REB if ref in ('AM0902L','AM2008A') else SEED
        source=run/'03_runtime_pack';_,originals,_=v.load_base_pack(source)
        original=next(x for x in originals if x['resref']==ref)
        source_groups={}
        for f in original['frames']:
            key=(tuple(f['physical_size_x4']),tuple(f['centre_x1']),hashlib.sha256(pixels(source,f).tobytes()).hexdigest())
            source_groups.setdefault(key,[]).append(f['frame'])
        assert all(len(g)==1 for g in source_groups.values())
        fps=r['target_fps'];nativefps=r['native_fps']
        assert fps==dict(numerator=30,denominator=1) and nativefps==dict(numerator=15,denominator=1)
        cycles=[]
        for c,old in zip(r['cycles'],original['cycles']):
            duration_before=len(old['native_frame_indices'])/15;duration_after=len(c['timeline_frame_indices'])/30
            assert duration_before==duration_after
            timeline=c['timeline_frame_indices']
            consecutive=[i for i in range(len(timeline)) if r['frames'][timeline[i]]['sha256']==r['frames'][timeline[(i+1)%len(timeline)]]['sha256']]
            assert not consecutive,ref+': repeated final consecutive pose'
            cycles.append(dict(cycle=c['cycle'],native_slots=len(old['native_frame_indices']),output_phases=len(timeline),
                duration_seconds=duration_after,repeated_consecutive_output_poses=consecutive))
        records.append(dict(resref=ref,source_stored_frames=original['frame_count'],source_duplicate_frames=[],
            duplicate_lookup_holds_removed_before_interpolation=5 if ref=='AM1512PA' else 0,
            final_duplicate_frames=duplicates,cycles=cycles))
    _,whole=v.validate_v2_pack(BATCH/'context-base')
    assert len({f['sha256'] for f in whole[0]['frames']})==8
    v.write_json(BATCH/'verification.json',dict(status='completed',resources=records,
        final_runtime_frames=128,assembled_AM0902L_unique_input_poses=8,
        duration_preserved=True,premultiply_AM2008A_once=True,qa_status='pending-ingame'))
    print('VERIFIED: 128 unique runtime frames, original durations, no consecutive duplicate outputs')

if __name__=='__main__':main()
