"""AM3000E: compare two non-eroding edge fades on the existing premultiplied animation."""
from pathlib import Path
import sys,copy,hashlib
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import distance_transform_edt,gaussian_filter

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/recipes/lot45-final-20261011-v1'))
from common import v,pixels,write_pack,rel

REF='AM3000E'
TAG='am3000e-contour-soft-20261011-v1'
SOURCE=ROOT/'animations/batches/lot45-final-20261011-v1/final-AM3000E-PLT_MAGE'
OUT=ROOT/'animations/batches'/TAG
PAD_X1=3

def soften(p,sigma):
    pad=4*PAD_X1
    original=np.pad(p,((pad,pad),(pad,pad),(0,0)),mode='constant')
    inside=original[...,3]>0
    distance=distance_transform_edt(inside)
    # Gaussian transition crosses the old outline; keep deep interiors byte-identical.
    full=2*sigma;core=4*sigma
    t=np.clip((distance-full)/(core-full),0,1)
    weight=1-t*t*(3-2*t)
    blurred=gaussian_filter(original.astype(np.float32),sigma=(sigma,sigma,0),mode='constant',cval=0,truncate=4)
    result=np.rint(original*(1-weight[...,None])+blurred*weight[...,None]).clip(0,255).astype(np.uint8)
    result[result[...,3]==0,:3]=0
    assert np.array_equal(result[distance>=core],original[distance>=core])
    assert not result[0].any() and not result[-1].any() and not result[:,0].any() and not result[:,-1].any(), 'fade clipped by canvas'
    return result,original,distance>=core

def main():
    assert not OUT.exists(),'versioned output exists; use a new ID'
    OUT.mkdir(parents=True)
    _,rs=v.validate_v2_pack(SOURCE);native=rs[0]
    trials={};report={};arrays={}
    for label,sigma in [('soft2',2.0),('soft3',3.0)]:
        r=copy.deepcopy(native);images={};metrics=[]
        for f in r['frames']:
            p=pixels(SOURCE,native['frames'][f['frame']]);q,padded,core=soften(p,sigma)
            w,h=f['logical_size_x1'];cx,cy=f['centre_x1']
            f.update(logical_size_x1=[w+2*PAD_X1,h+2*PAD_X1],physical_size_x4=[(w+2*PAD_X1)*4,(h+2*PAD_X1)*4],centre_x1=[cx+PAD_X1,cy+PAD_X1])
            assert f['centre_x1'][0]-PAD_X1==cx and f['centre_x1'][1]-PAD_X1==cy
            lum=np.array([.2126,.7152,.0722]);before=(p[...,:3]@lum).sum();after=(q[...,:3]@lum).sum()
            metrics.append(dict(frame=f['frame'],additive_energy_change_pct=100*(after/max(before,1)-1),
                core_pixels_preserved=int(core.sum()),alpha_flux_change_pct=100*(q[...,3].sum()/max(int(p[...,3].sum()),1)-1)))
            images[(REF,f['frame'])]=q
        assert r['cycles']==native['cycles'] and r['native_fps']==native['native_fps'] and r['target_fps']==native['target_fps']
        assert len({hashlib.sha256(p.tobytes()).hexdigest() for p in images.values()})==r['frame_count']
        pack=write_pack(OUT/label,[r],images);trials[label]=pack;arrays[label]=images
        report[label]=dict(sigma_x4=sigma,edge_only=True,full_filter_within_x4=2*sigma,core_unchanged_beyond_x4=4*sigma,
            max_absolute_additive_energy_change_pct=max(abs(m['additive_energy_change_pct']) for m in metrics),
            mean_additive_energy_change_pct=float(np.mean([m['additive_energy_change_pct'] for m in metrics])),frames=metrics,
            pack=rel(pack),pack_manifest_sha256=v.sha256_file(pack/'manifest.json'))
    preview(native,arrays)
    v.write_json(OUT/'manifest.json',dict(schema='bg2-upscale-animation-trial-v1',status='completed',created_utc=v.utc_now(),resref=REF,
        source_pack=rel(SOURCE),source_pack_manifest_sha256=v.sha256_file(SOURCE/'manifest.json'),
        method='Gaussian edge-only RGBA filtering in premultiplied space; no inner erosion; preserve every component and deep interior',
        palette='PLT_MAGE already realized before ReboutCX',pad_x1=PAD_X1,world_placement_preserved=True,
        premultiplication='already premultiplied input; linear filtering only, no second multiplication',
        frame_count=61,cycle_phase_counts=[len(c['timeline_frame_indices']) for c in native['cycles']],
        cycle_durations_seconds=[len(c['timeline_frame_indices'])/30 for c in native['cycles']],
        target_fps=30,existing_duplicate_aliases_and_all_timeline_slots_preserved=True,variants=report,
        comparison=rel(OUT/'comparison.png'),qa_status='pending-user-review',installation_status='not-installed',release_status='not-selected'))
    v.write_json(Path(__file__).resolve().parent/'result.json',dict(source_pack=rel(SOURCE),trial=rel(OUT),
        variants={k:{kk:vv for kk,vv in val.items() if kk!='frames'} for k,val in report.items()},
        phase_counts=[48,36,20],durations_seconds=[1.6,1.2,20/30],installation_status='not-installed'))
    print({k:round(val['max_absolute_additive_energy_change_pct'],3) for k,val in report.items()},flush=True)

def preview(r,arrays):
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
    timeline=r['cycles'][1]['timeline_frame_indices']
    tiny=min(r['frames'],key=lambda f:pixels(SOURCE,f)[...,3].sum())['frame']
    indexes=[timeline[i] for i in (0,12,24)]+[tiny]
    sheet=Image.new('RGB',(1080,1330),(32,32,32));d=ImageDraw.Draw(sheet)
    for col,title in enumerate(('Actuel','Fondu doux - sigma2','Fondu plus large - sigma3')):
        d.text((col*360+15,10),title,font=font,fill='white')
    def row(index,label,y):
        for col,name in enumerate(('current','soft2','soft3')):
            p=pixels(SOURCE,r['frames'][index]) if name=='current' else arrays[name][(REF,index)]
            if name=='current':p=np.pad(p,((12,12),(12,12),(0,0)))
            im=Image.fromarray(np.minimum(p[...,:3].astype(np.uint16)+32,255).astype(np.uint8))
            im.thumbnail((340,265),Image.Resampling.LANCZOS)
            sheet.paste(im,(col*360+(360-im.width)//2,y+36+(265-im.height)//2))
            d.text((col*360+15,y+5),label,font=small,fill=(185,185,185))
    for n,index in enumerate(indexes):row(index,f'Cycle1 phase{n*12}' if n<3 else f'Petite pose - frame{index}',45+n*320)
    sheet.save(OUT/'comparison.png')
    frames=[]
    for phase,index in enumerate(timeline):
        canvas=Image.new('RGB',(1080,365),(32,32,32));draw=ImageDraw.Draw(canvas)
        for col,name in enumerate(('current','soft2','soft3')):
            p=pixels(SOURCE,r['frames'][index]) if name=='current' else arrays[name][(REF,index)]
            f=r['frames'][index];pad=12
            if name=='current':p=np.pad(p,((pad,pad),(pad,pad),(0,0)))
            im=Image.fromarray(np.minimum(p[...,:3].astype(np.uint16)+32,255).astype(np.uint8))
            # Fixed world anchor; per-frame native centres keep the animated shapes aligned.
            canvas.paste(im,(col*360+95-f['centre_x1'][0]*4-pad,460-f['centre_x1'][1]*4-pad))
            draw.text((col*360+15,10),('Actuel','Doux sigma2','Plus large sigma3')[col],font=font,fill='white')
        frames.append(canvas)
    frames[0].save(OUT/'comparison.gif',save_all=True,append_images=frames[1:],duration=[30,30,40]*12,loop=0)

if __name__=='__main__':main()
