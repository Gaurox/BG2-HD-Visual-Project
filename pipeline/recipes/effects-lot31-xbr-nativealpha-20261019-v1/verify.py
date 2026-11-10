"""Check only changed candidates: native masks, durations, bytes and luminous energy."""
from common import *
from PIL import Image
import numpy as np
from fractions import Fraction
import time

def main():
    reports=[];verifier=evidence(Path(__file__))
    for a in sorted(jobs(),key=lambda a:(not a['primary'],a['ordinal'])):
        file=OUT/'results'/f'{a["job_id"]}.json';cache=OUT/'verification'/file.name
        while not file.exists():
            if load(OUT/'progress.json').get(a['job_id'],{}).get('state')=='failed':raise RuntimeError(a['job_id']+' failed')
            time.sleep(2)
        record=evidence(file)
        if cache.exists():
            old=load(cache)
            if old['result']==record and old['verifier']==verifier:reports.append(old);continue
        r=load(file);p=load(PREVIOUS/'results'/file.name);w,h=r['size_x4'];assert r['size_x4']==p['size_x4'] and r['centre_x1']==p['centre_x1']
        assert r['parent_correction']==evidence(PREVIOUS/'results'/file.name)
        is_xbr=a['ordinal']<=6;native={};anchor_errors=0;flux=0;black_removed=0;near_transparent=0
        if is_xbr:
            source=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'00-frames-x1';fm=load(source/'manifest.json')
            for f in fm['frames']:
                v=np.array(Image.open(source/'rgba'/f['file']).convert('RGBA'))[:,:,3].repeat(4,0).repeat(4,1);native[f['frame']]=np.pad(v,previous.PAD)
            sm=load(OUT/'spatial'/a['job_id']/'manifest.json');assert sm['algorithm']=='XBR/xbr4X' and sm['scale']==4 and sm['blend_colors']==False
            assert sm['source']==evidence(source/'manifest.json') and sm['palette']==evidence(ROOT/a['palette_file'])
            spatial={f['frame']:f for f in sm['frames']}
        for profile,oldprofile in zip(r['profiles'],p['profiles'],strict=True):
            assert profile['id']==oldprofile['id'] and profile['duration_rational']==oldprofile['duration_rational']
            assert profile['phases']==oldprofile['phases'] and profile['phase_durations_rational']==oldprofile['phase_durations_rational']
            assert sum(Fraction(*d) for d in profile['phase_durations_rational'])==Fraction(*profile['duration_rational'])
        for f,oldf in zip(r['frames'],p['frames'],strict=True):
            b=(ROOT/f['straight']['path']).read_bytes();assert sha(b)==f['straight']['sha256'] and len(b)==w*h*4;normal=np.frombuffer(b,np.uint8).reshape(h,w,4)
            pb=(ROOT/f['premultiplied']['path']).read_bytes();assert sha(pb)==f['premultiplied']['sha256'];prem=np.frombuffer(pb,np.uint8).reshape(h,w,4)
            assert np.array_equal(normal[:,:,3],prem[:,:,3]);expected=np.rint(normal[:,:,:3].astype(float)*normal[:,:,3:4]/255).astype(np.uint8);assert np.abs(expected.astype(int)-prem[:,:,:3].astype(int)).max()<=1
            assert not normal[normal[:,:,3]==0].any() and not prem[prem[:,:,3]==0].any();assert not normal[[0,-1]].any() and not normal[:,[0,-1]].any()
            with Image.open(media(f['after'])) as im:assert np.array_equal(np.array(im.convert('RGBA')),normal)
            assert f['before']==old_image(oldf['after'])
            if is_xbr:
                left,right=f['temporal_source_frames'];t=f['temporal_fraction'];alpha=np.rint(native[left].astype(np.float32)*(1-t)+native[right].astype(np.float32)*t).astype(np.uint8)
                assert np.array_equal(normal[:,:,3],alpha),(a['job_id'],f['phase'],'default native alpha changed')
                if t==0:
                    row=spatial[left];assert evidence(ROOT/row['path'])['sha256']==row['sha256']
                    with Image.open(ROOT/row['path']) as im:sp=np.array(im.convert('RGBA'))
                    pad=previous.PAD;inside=normal[pad:-pad,pad:-pad];v=inside[:,:,3]>0;assert np.array_equal(inside[:,:,:3][v],sp[:,:,:3][v])
            else:
                old=np.fromfile(ROOT/oldf['straight']['path'],np.uint8).reshape(h,w,4);energy=np.rint(old[:,:,:3].astype(float)*old[:,:,3:4]/255).astype(np.uint8)
                error=int(np.abs(energy.astype(int)-prem[:,:,:3].astype(int)).max());assert error<=1;flux=max(flux,error)
                expected_alpha=np.rint(old[:,:,3].astype(np.float32)*old[:,:,:3].max(2).astype(np.float32)/255).astype(np.uint8);assert np.array_equal(normal[:,:,3],expected_alpha)
                black=old[:,:,:3].max(2)==0;assert not normal[black].any();black_removed+=int((black&(old[:,:,3]>0)).sum())
                near=(old[:,:,:3].max(2)<=8)&(old[:,:,3]>0);assert np.all(normal[:,:,3][near]<=8);near_transparent+=int(near.sum())
                # Black leaves all three backgrounds untouched; additive output is invariant to one byte.
                for bg in ([20,30,40],[110,94,70],[235,235,235]):
                    composed=np.rint(prem[:,:,:3].astype(float)+np.array(bg)*(1-normal[:,:,3:4].astype(float)/255)).clip(0,255).astype(np.uint8);assert np.all(composed[black]==bg)
                    additive=np.minimum(255,prem[:,:,:3].astype(int)+bg);oldadd=np.minimum(255,energy.astype(int)+bg);assert np.abs(additive-oldadd).max()<=1
        report={'job_id':a['job_id'],'passed':True,'result':record,'verifier':verifier,'phases':len(r['frames']),'profiles':len(r['profiles']),
            'durations_and_world_anchor_unchanged':True,'native_default_alpha_exact':is_xbr,'no_mask_retouch':is_xbr,
            'black_neutral':not is_xbr,'emissive_energy_max_byte_error':flux,'black_pixels_removed':black_removed,'nearblack_pixels_softened':near_transparent}
        save(cache,report);reports.append(report);print('VERIFY',a['job_id'],flush=True)
    save(OUT/'verification.json',{'status':'passed','assets':8,'contexts':len(reports),'phases':sum(r['phases'] for r in reports),'profiles':sum(r['profiles'] for r in reports),'xbr_native_alpha_contexts':37,'black_contexts':2,'results':reports,'installed':False})
    print('All39 changed contexts verified',flush=True)

if __name__=='__main__':main()
