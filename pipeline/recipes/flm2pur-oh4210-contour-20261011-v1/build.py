"""Compare small-flame edge fades in premultiplied space, retaining native geometry and sparks."""
from pathlib import Path
import sys,copy,hashlib
import numpy as np
from scipy.ndimage import gaussian_filter,distance_transform_edt,label
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/recipes/lot45-final-20261011-v1'))
from common import v,pixels,write_pack,rel
from build_alpha_feather import canvas_edge_ramp
from bam_export import decode_bam
from export_bam_frames import read_bam
REF='FLM2PUR'
TAG='flm2pur-oh4210-contour-20261011-v1'
SOURCE=ROOT/'animations/batches/lot45-final-20261011-v1/final-FLM2PUR-PLT_PURP'
OUT=ROOT/'animations/batches'/TAG

def soft(p,sigma):
    h,w=p.shape[:2];gate=canvas_edge_ramp(w,h,1,('top','right','bottom','left'))
    ids,count=label(p[...,3]>0,np.ones((3,3)))
    sizes=np.bincount(ids.ravel());tiny_ids=[i for i in range(1,count+1) if sizes[i]<=48]
    tiny=np.isin(ids,tiny_ids)
    main=p.copy();main[tiny]=0
    distance=distance_transform_edt(np.pad(main[...,3]>0,1))[1:-1,1:-1]
    t=np.clip((distance-2*sigma)/(2*sigma),0,1);weight=1-t*t*(3-2*t)
    blurred=gaussian_filter(main.astype(float),(sigma,sigma,0),mode='constant',cval=0,truncate=4)
    result=(main*(1-weight[...,None])+blurred*weight[...,None])*gate[...,None]
    spark_stats=[]
    for component in tiny_ids:
        original=np.where((ids==component)[...,None],p,0).astype(float)
        # Tiny sparks get a narrower fade and conserve channel flux within the original rectangle.
        q=gaussian_filter(original,(.8,.8,0),mode='constant',cval=0,truncate=4)*gate[...,None]
        for channel in range(4):
            target=original[...,channel].sum();kernel=q[...,channel].copy();peak=original[...,channel].max()
            if target and kernel.sum()>0:
                low,high=0.,max(1.,target/kernel.sum())
                while np.minimum(kernel*high,peak).sum()<target-1e-6:
                    high*=2
                    assert high<1e9,'insufficient in-canvas support for spark flux'
                for _ in range(35):
                    scale=(low+high)/2
                    if np.minimum(kernel*scale,peak).sum()<target:low=scale
                    else:high=scale
                q[...,channel]=np.minimum(kernel*high,peak)
        spark_stats.append(dict(component=component,pixels=int(sizes[component]),flux_preserved=True))
        result+=q
    result=np.rint(result).clip(0,255).astype(np.uint8)
    result[result[...,3]==0,:3]=0
    assert not result[0].any() and not result[-1].any() and not result[:,0].any() and not result[:,-1].any()
    core=distance>=4*sigma
    # Spark spread may reach the core; preserve the core itself exactly.
    result[core]=main[core]
    return result,spark_stats

def main():
    assert not (OUT/'manifest.json').exists(),'completed output is immutable; use a new version'
    assert not OUT.exists() or not any(OUT.iterdir()),'partial payload already exists'
    OUT.mkdir(parents=True,exist_ok=True)
    r=v.validate_v2_pack(SOURCE)[1][0]
    native=decode_bam(read_bam(ROOT/f'animations/ressources/{REF}/source.bam'))[0]
    assert len(native)==16
    for i,(idx,cx,cy,tr) in enumerate(native):
        assert r['frames'][i]['logical_size_x1']==[idx.shape[1],idx.shape[0]] and r['frames'][i]['centre_x1']==[cx,cy]
    variants={};images={};lum=np.array([.2126,.7152,.0722])
    for name,sigma in [('soft125',1.25),('soft2',2.)]:
        arrays={};metrics=[]
        for f in r['frames']:
            p=pixels(SOURCE,f);q,sparks=soft(p,sigma)
            assert q.shape==p.shape
            arrays[(REF,f['frame'])]=q
            metrics.append(dict(frame=f['frame'],additive_energy_change_pct=100*((q[...,:3]@lum).sum()/max((p[...,:3]@lum).sum(),1)-1),sparks=sparks))
        assert len({hashlib.sha256(p.tobytes()).hexdigest() for p in arrays.values()})==32
        pack=write_pack(OUT/name,[copy.deepcopy(r)],arrays)
        rr=v.validate_v2_pack(pack)[1][0]
        assert rr['cycles']==r['cycles']
        assert all(all(a[k]==b[k] for k in ('frame','logical_size_x1','physical_size_x4','centre_x1')) for a,b in zip(r['frames'],rr['frames']))
        variants[name]=dict(sigma_x4=sigma,spark_sigma_x4=.8,canvas_fade_x4=1,pack=rel(pack),pack_manifest_sha256=v.sha256_file(pack/'manifest.json'),
            max_absolute_additive_energy_change_pct=max(abs(m['additive_energy_change_pct']) for m in metrics),
            mean_additive_energy_change_pct=float(np.mean([m['additive_energy_change_pct'] for m in metrics])),
            preserved_tiny_components=sum(len(m['sparks']) for m in metrics),frames=metrics)
        images[name]=arrays
    preview(r,images)
    v.write_json(OUT/'manifest.json',dict(schema='bg2-upscale-animation-trial-v1',status='completed',created_utc=v.utc_now(),resref=REF,area_scope=['OH4210'],
        source_pack=rel(SOURCE),source_pack_manifest_sha256=v.sha256_file(SOURCE/'manifest.json'),
        recipe='Gaussian premultiplied RGBA edge fade; exact native rectangles/centres; tiny components sigma0.8 with preserved channel flux; canvas1px x4',
        palette='PLT_PURP realized before ReboutCX x4; AR1008 embedded variant unaffected',native_geometry_verified_frames=16,
        stored_frames=32,target_fps=30,cycle_phases=32,cycle_duration_seconds=32/30,
        original_cycles_aliases_and_timeline_slots_preserved=True,variants=variants,comparison=rel(OUT/'comparison.png'),
        qa_status='pending-user-review',installation_status='not-installed',release_status='not-selected'))
    v.write_json(Path(__file__).resolve().parent/'result.json',dict(trial=rel(OUT),area_scope=['OH4210'],installation_status='not-installed',
        variants={k:{kk:vv for kk,vv in data.items() if kk!='frames'} for k,data in variants.items()},frames=32,duration_seconds=32/30,native_geometry_verified=True))
    print({name:dict(energy_change_pct=round(data['mean_additive_energy_change_pct'],3),sparks=data['preserved_tiny_components']) for name,data in variants.items()},flush=True)

def preview(r,images):
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    sheet=Image.new('RGB',(1050,1150),(32,32,32));draw=ImageDraw.Draw(sheet)
    names=('current','soft125','soft2');titles=('Actuel PLT_PURP','Lissage doux sigma1.25','Lissage plus large sigma2')
    for col,title in enumerate(titles):draw.text((col*350+10,10),title,font=font,fill='white')
    timeline=r['cycles'][0]['timeline_frame_indices'];frames=[]
    def cell(name,index):
        p=pixels(SOURCE,r['frames'][index]) if name=='current' else images[name][(REF,index)]
        im=Image.fromarray(np.minimum(p[...,:3].astype(np.uint16)+32,255).astype(np.uint8))
        return im.resize((im.width*3,im.height*3),Image.Resampling.NEAREST)
    for row,phase in enumerate((0,8,16,24)):
        index=timeline[phase]
        for col,name in enumerate(names):
            im=cell(name,index);x=col*350+(350-im.width)//2;y=row*275+60
            sheet.paste(im,(x,y));draw.text((col*350+10,row*275+36),f'Phase {phase}/32 - zoom x3',font=small,fill=(185,185,185))
    sheet.save(OUT/'comparison.png')
    for index in timeline:
        canvas=Image.new('RGB',(1050,330),(32,32,32));d=ImageDraw.Draw(canvas)
        for col,name in enumerate(names):
            f=r['frames'][index];im=cell(name,index)
            # Each native-pixel position is magnified by4*3, constant world anchor per column.
            canvas.paste(im,(col*350+180-f['centre_x1'][0]*12,285-f['centre_x1'][1]*12))
            d.text((col*350+10,10),titles[col],font=font,fill='white')
        frames.append(canvas)
    # GIF delay units: 10ms; quantize each 33.333ms phase without changing the animation pack.
    duration=[(round((i+1)*10/3)-round(i*10/3))*10 for i in range(32)]
    frames[0].save(OUT/'comparison.gif',save_all=True,append_images=frames[1:],duration=duration,loop=0)

if __name__=='__main__':main()
