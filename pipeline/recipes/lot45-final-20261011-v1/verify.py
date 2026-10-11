from common import *
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata
from collections import defaultdict
import hashlib

def main():
    complete=PACKS/(TAG+'-complete');sources=v.load_json(BATCH/'area-sources.json');records=[]
    for area,info in sources.items():
        pack=complete/area;manifest,rs=v.validate_v2_pack(pack)
        r=next(r for r in rs if r['resref']==info['resref']);ref=r['resref']
        data=read_bam(ROOT/f'animations/ressources/{ref}/source.bam');native,palette,tr=decode_bam(data)
        if info['palette']!='embedded':
            from PIL import Image
            pal=BATCH/'palettes'/(info['palette']+'.bmp');im=Image.open(pal)
            palette=np.array(im.getpalette(),np.uint8).reshape(256,3)
            assert v.sha256_file(pal)==v.sha256_file(ROOT/f'animations/tmp/lot45-analysis-20261011-v1/{info["palette"]}.bmp')
        hashes=[]
        for i,(idx,cx,cy,tr) in enumerate(native):
            rgba=np.dstack([palette[idx],(idx!=tr).astype(np.uint8)*255]);rgba[rgba[...,3]==0,:3]=0
            hashes.append(hashlib.sha256(rgba.tobytes()+np.array([cx,cy,*idx.shape],np.int32).tobytes()).hexdigest())
            f=r['frames'][i];assert f['centre_x1']==[cx,cy] and f['logical_size_x1']==[idx.shape[1],idx.shape[0]]
        assert len(set(hashes))==len(hashes),ref+': duplicated realized source pose'
        assert r['native_fps']==dict(numerator=15,denominator=1) and r['target_fps']==dict(numerator=30,denominator=1)
        assert len(r['cycles'])==len(cycle_metadata(data,len(native)))
        loops=[]
        for c,old in zip(r['cycles'],cycle_metadata(data,len(native))):
            assert c['native_frame_indices']==old['frame_indices']
            timeline=c['timeline_frame_indices'];assert len(timeline)==2*len(old['frame_indices'])
            duplicate_pairs=[]
            for phase,i in enumerate(timeline):
                j=timeline[(phase+1)%len(timeline)]
                a,b=r['frames'][i],r['frames'][j]
                if a['sha256']==b['sha256'] and a['centre_x1']==b['centre_x1']:duplicate_pairs.append(phase)
            assert not duplicate_pairs,(area,ref,duplicate_pairs)
            loops.append(dict(cycle=c['cycle'],native_slots=len(old['frame_indices']),target_phases=len(timeline),duration_seconds=len(timeline)/30,
                              consecutive_duplicate_phases=duplicate_pairs))
        stored=defaultdict(list)
        for f in r['frames']:
            stored[(tuple(f['centre_x1']),tuple(f['physical_size_x4']),f['sha256'])].append(f['frame'])
            if ref!='AMWRPGT1':
                p=pixels(pack,f);assert not p[p[...,3]==0,:3].any()
                if ref in ['AM3000E','FLM2PUR']:assert np.all(p[...,:3]<=p[...,3,None])
        assert all(len(x)==1 for x in stored.values()),area+': stored duplicate frame'
        if ref=='AMWRPGT1':
            chosen=v.validate_v2_pack(AMWRP)[1][0]
            assert v.resource_binary_v2(r,3)==v.resource_binary_v2(chosen,3)
            assert [f['sha256'] for f in r['frames']]==[f['sha256'] for f in chosen['frames']]
        records.append(dict(area=area,resref=ref,palette=info['palette'],source_unique_frames=len(native),output_stored_frames=r['frame_count'],
                            cycles=loops,preserved_previously_installed_bytes=info['existing_bytes_preserved']))
    assert len(records)==21 and len(OCCURRENCES)==69
    # This installation does not reinterpret the cyan rim already baked into AR3003's map.
    assert all(sources[a]['existing_bytes_preserved'] for a in ['AR3003','AR3011','AR3016','AR3017'])
    v.write_json(BATCH/'verification.json',dict(status='completed',area_count=21,occurrence_count=69,records=records,
        palettes_realized_before_inference=True,native_geometry_and_lookups_preserved=True,durations_preserved=True,
        qa_status='pending-ingame',release_status='not-selected'))
    print('VERIFIED: 21 maps / 69 occurrences; native contracts and durations preserved; no duplicate poses')

if __name__=='__main__':main()
