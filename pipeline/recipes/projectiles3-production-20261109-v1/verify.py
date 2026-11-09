"""Verify source/carrier geometry, native-clock anchors and actual pack bytes."""
from fractions import Fraction
import argparse
import struct
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from temporal import ROOT,BATCH,load,save,rel,digest,workflow
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam,cycle_metadata
from compose_effect_runtime_packs import validate_pack


def verify(a):
    name=a['resref'];run=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run'];stage=run/'02-interpolation'
    m=load(stage/'manifest.json');sp=ROOT/m['parent']['spatial_manifest'];s=load(sp)
    raw=read_bam(ROOT/a['source']);old,pal,tr=decode_bam(raw);new,npal,ntr=decode_bam(read_bam(ROOT/m['runtime_carrier']['path']))
    assert np.array_equal(pal,npal) and tr==ntr and len(old)==len(new)
    cycles=cycle_metadata(raw,len(old));assert cycles==cycle_metadata(read_bam(ROOT/m['runtime_carrier']['path']),len(new))
    assert cycles==a['native_cycles']
    assert s['parameters']['model'] in {'seedvr2_7b_int8_convrot.safetensors','XBR/xbr4X','XBR/xbr2blend-nearest2','XBR/xbr2-nearest2','NATIVE/palette-alpha-nearest4','reuse-TRGOOY-spatial'}
    assert s['parameters']['color_correction_method'] in {'lab','native','reuse'} and s['scale']==4
    cw,ch=s['aligned_canvas_size_x1'];anchor=[s['frames'][0]['canvas_offset_x1'][i]+old[0][i+1] for i in range(2)]
    masks={};source_alpha=native_palette_alpha(raw,tr)
    bubble_expected=None
    if name=='BUBLES':
        from run_animation_small_subject_xbr2 import run_xbr2x,nearest_x2
        from workspace_paths import get_path
        fm=load(ROOT/s['source']['frame_manifest']);base=(ROOT/s['source']['frame_manifest']).parent
        sources=[np.array(Image.open(base/'rgba'/f['file']).convert('RGBA')) for f in fm['frames']]
        bubble_expected=[nearest_x2(x) for x in run_xbr2x(sources,get_path('mmpx_scalepix',required=True),'node',True)]
    for i,((idx,cx,cy,_),(idx2,cx2,cy2,_)) in enumerate(zip(old,new)):
        before=np.full((ch,cw),tr,np.uint8);after=before.copy()
        x,y=anchor[0]-cx,anchor[1]-cy;xx,yy=anchor[0]-cx2,anchor[1]-cy2
        before[y:y+idx.shape[0],x:x+idx.shape[1]]=idx
        after[yy:yy+idx2.shape[0],xx:xx+idx2.shape[1]]=idx2
        assert np.array_equal(before,after),(name,i,'native carrier geometry')
        alpha=source_alpha[idx].copy()
        if a.get('green_index') is not None:
            labels,_=ndi.label(idx==a['green_index'])
            edge=np.unique(np.concatenate([labels[0],labels[-1],labels[:,0],labels[:,-1]]));edge=edge[edge>0]
            alpha[np.isin(labels,edge)]=0
        mask=np.zeros((ch,cw),np.uint8);mask[y:y+idx.shape[0],x:x+idx.shape[1]]=alpha
        masks[i]=np.repeat(np.repeat(mask,4,0),4,1)
        actual=np.array(Image.open(sp.parent/s['frames'][i]['aligned_rgba_xn']).getchannel('A'))
        if bubble_expected is not None:
            expected=bubble_expected[i][:,:,3].copy()
            l,t,r,b=s['frames'][i]['runtime_crop_box_xn'];inside=np.zeros(expected.shape,bool);inside[t:b,l:r]=True;expected[~inside]=0
            assert np.array_equal(actual,expected),(name,i,'deterministic xBR2blend source alpha')
            masks[i]=expected
        else:assert np.array_equal(actual,masks[i]),(name,i,'spatial source-derived alpha')
    pm=validate_pack(ROOT/a['pack']);assert pm.manifest['cycles']==cycles
    proof=workflow.verify_run_descriptor(ROOT,run.parent.parent,name,a['interpolation_run'],stage='interpolation',spatial_run=a['spatial_run'])
    assert proof['ok'],proof
    profiles=[];contracts=[];lost=0
    for v in m['timing']['cycles']:
        slots=cycles[v['cycle']]['frame_indices'];seq=v['timeline_frame_indices'];count=len(slots)*2
        assert len(seq)==count==v['phase_count']
        assert sum(Fraction(*d) for d in v['phase_durations_rational'])==Fraction(len(slots),15)
        for phase,index in enumerate(seq):
            f=m['frames'][index];g=slots[phase//2];nxt=slots[(phase//2+1)%len(slots)] if v['loop_closed'] else slots[min(phase//2+1,len(slots)-1)]
            left,right=f['temporal_source_frames'];t=f['temporal_fraction']
            assert left==g and right==nxt
            assert t==0 if phase%2==0 else t in (0,.5)
            assert f['geometry_source_frame']==g and f['centre_x1']==list(new[g][1:3])
            w,h=f['physical_size_x4'];assert [w,h]==[new[g][0].shape[1]*4,new[g][0].shape[0]*4]
            b=(stage/f['raw_rgba_x4']).read_bytes();assert digest(b)==f['raw_rgba_x4_sha256']
            rgba=np.frombuffer(b,np.uint8).reshape(h,w,4)
            assert np.all(rgba[:,:,:3]<=rgba[:,:,3:4])
            bs=(stage/f['straight_raw_rgba_x4']).read_bytes();assert digest(bs)==f['straight_raw_rgba_x4_sha256']
            straight=np.frombuffer(bs,np.uint8).reshape(h,w,4)
            assert np.array_equal(straight[:,:,3],rgba[:,:,3])
            reconstructed=np.rint(straight[:,:,:3].astype(float)*straight[:,:,3:4]/255).astype(np.uint8)
            assert np.abs(reconstructed.astype(np.int16)-rgba[:,:,:3].astype(np.int16)).max()<=1
            xx,yy=(anchor[0]-new[g][1])*4,(anchor[1]-new[g][2])*4
            expected=np.rint(masks[left].astype(float)*(1-t)+masks[right].astype(float)*t).astype(np.uint8)
            canvas=np.zeros((ch*4,cw*4,4),np.uint8);canvas[yy:yy+h,xx:xx+w]=rgba
            assert digest(canvas.tobytes())==f['anchored_rgba_sha256']
            assert np.all(canvas[:,:,3]<=expected)
            if not a['inner_feather_x4']:assert np.array_equal(canvas[:,:,3],expected)
            if phase%2==0:
                labs,n=ndi.label(masks[g]>0,np.ones((3,3)))
                for k in range(1,n+1):
                    assert np.any(canvas[:,:,3][labs==k]),(name,v['id'],phase,'native component erased')
            if 'neutral_raw_rgba_x4' in f:
                bn=(stage/f['neutral_raw_rgba_x4']).read_bytes();assert digest(bn)==f['neutral_raw_rgba_x4_sha256']
                neutral=np.frombuffer(bn,np.uint8).reshape(h,w,4)
                nr=np.rint(neutral[:,:,:3].astype(float)*neutral[:,:,3:4]/255).astype(np.uint8)
                assert np.abs(nr.astype(np.int16)-reconstructed.astype(np.int16)).max()<=1
            contracts.append(dict(profile=v['id'],phase=phase,native_slot=phase//2,source_frame=g,centre=f['centre_x1'],size=[w,h]))
        profiles.append(dict(id=v['id'],native_slots=len(slots),phases=count,duration=[len(slots),15]))
    tl=pm.manifest['timeline'];assert len(tl['cycle_profiles'])==len(cycles)
    for i,c in enumerate(cycles):
        assert len(tl['native_frame_indices_by_cycle'][i])==len(c['frame_indices'])
        assert len(tl['timeline_frame_indices_by_cycle'][i])==len(c['frame_indices'])*2
        if not c['frame_indices']:assert tl['cycle_profiles'][i] is None
    result=dict(resref=name,passed=True,phases=len(m['frames']),profiles=len(profiles),native_anchor_contracts=len(contracts),
                source_pixels_palette_cycles_centres_preserved=True,source_derived_alpha_verified=True,profile_timings=profiles,
                pack_manifest_sha256=pm.manifest_sha256,visual_qa='pending-user-review',installed=False)
    save(BATCH/'verification'/f'{name}.json',result)
    print(name,'verification PASS',len(profiles),'profiles',len(m['frames']),'phases',flush=True)
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--resref',action='append');args=p.parse_args()
    for a in load(BATCH/'batch.json')['assets']:
        if not args.resref or a['resref'] in args.resref:verify(a)
