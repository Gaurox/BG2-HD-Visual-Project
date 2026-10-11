"""Compare aura-only treatments of installed 30fps FIRE_3; no installation."""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation, distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v
from area_pack_state import game_areas_dir

SOURCE = ROOT/'animations/packs-par-zone/fire3-apo8-30fps-ar0202-zero-20261011-v1/AR0202'

def smooth(x):
    x=np.clip(x,0,1)
    return x*x*(3-2*x)

def main():
    assert not (HERE/'comparison.png').exists(), 'Immutable preview exists'
    _,resources=v.validate_v2_pack(SOURCE)
    resource=next(r for r in resources if r['resref']=='FIRE_3')
    frames=resource['frames']
    left=min(-f['centre_x1'][0]*4 for f in frames)
    top=min(-f['centre_x1'][1]*4 for f in frames)
    right=max((f['logical_size_x1'][0]-f['centre_x1'][0])*4 for f in frames)
    bottom=max((f['logical_size_x1'][1]-f['centre_x1'][1])*4 for f in frames)
    arrays=[];boxes=[];live=game_areas_dir()/'AR0202'
    for f in frames:
        raw=(live/f['asset']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==f['sha256']
        w,h=f['physical_size_x4']
        a=np.frombuffer(raw,np.uint8).reshape(h,w,4).copy()
        canvas=np.zeros((bottom-top,right-left,4),np.uint8)
        x=-f['centre_x1'][0]*4-left;y=-f['centre_x1'][1]*4-top
        canvas[y:y+h,x:x+w]=a
        arrays.append(canvas);boxes.append((x,y,w,h))
    # Loop-wide protection in BAM-centred space: avoids a moving treatment mask.
    seed=np.max(np.stack([a[:,:,:3].astype(np.float32).mean(axis=2) for a in arrays]),axis=0)>=140
    core=binary_dilation(seed,iterations=2)
    protect=1-smooth(distance_transform_edt(~core)/4)
    variants=[('Actuel',0,0),('Fondu seul 4 px',4,0),('Fondu 4 + flou 1,5',4,1.5),('Fondu 6 + flou 2,5',6,2.5)]
    samples=[1,6,12]
    cellw=230;cellh=360
    board=Image.new('RGB',(cellw*4,cellh*3+40),(30,30,30))
    draw=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',16)
    draw.text((8,6),'FIRE_3 : RGB additionne sur fond sombre. Simulation, pas capture ingame.',font=font,fill='white')
    report={}
    for col,(name,radius,sigma) in enumerate(variants):
        out=[];metric=[]
        directory=HERE/f'variant-{col}'
        directory.mkdir()
        for index,source in enumerate(arrays):
            if radius:
                padded=np.pad(source,((8,8),(8,8),(0,0)))
                dist=distance_transform_edt(padded[:,:,3]>0)[8:-8,8:-8]
                factor=protect+(1-protect)*smooth((dist-1)/radius)
                feathered=source.astype(np.float32)*factor[:,:,None]
                blurred=gaussian_filter(feathered,(sigma,sigma,0),mode='constant',truncate=4) if sigma else feathered
                result=feathered*protect[:,:,None]+blurred*(1-protect[:,:,None])
                # Keep the native physical rectangles and centres. No new canvas padding.
                x,y,w,h=boxes[index]
                cropped=np.rint(result[y:y+h,x:x+w]).clip(0,255).astype(np.uint8)
                cropped[cropped[:,:,3]==0,:3]=0
                aligned=np.zeros_like(source);aligned[y:y+h,x:x+w]=cropped
                # Restore fully protected bright pixels byte-exactly.
                aligned[core]=source[core]
                assert np.array_equal(aligned[core],source[core])
            else:
                aligned=source.copy()
                x,y,w,h=boxes[index];cropped=aligned[y:y+h,x:x+w]
            out.append(aligned)
            (directory/frames[index]['asset']).write_bytes(cropped.tobytes())
            metric.append(float(aligned[:,:,:3].sum()/max(1,source[:,:,:3].sum())))
        hashes=[hashlib.sha256(a.tobytes()).hexdigest() for a in out]
        assert len(set(hashes))==28
        report[name]=dict(distinct_aligned_frames=28,core_byte_identical=True,
                         rgb_energy_ratio_min=min(metric),rgb_energy_ratio_max=max(metric),
                         geometry_unchanged=True,temporal_contract_unchanged=True)
        for row,index in enumerate(samples):
            shown=np.minimum(out[index][:,:,:3].astype(np.uint16)+30,255).astype(np.uint8)
            img=Image.fromarray(shown).resize((shown.shape[1]*2,shown.shape[0]*2),Image.Resampling.NEAREST)
            draw.text((col*cellw+5,40+row*cellh),name,font=font,fill='white')
            board.paste(img,(col*cellw+14,65+row*cellh))
    board.save(HERE/'comparison.png')
    with (HERE/'review.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(source_pack=SOURCE.relative_to(ROOT).as_posix(),resref='FIRE_3',area='AR0202',
            user_temporal_feedback='animation pas terrible mais acceptable',
            requested_visual_issue='aura pixelisee derriere la flamme',
            protected_core='loop-wide mean RGB >=140, dilation2 x4; soft outer band4 x4',
            policy='multiply existing premultiplied RGBA by new fade only; no second premultiplication',
            variants=report,status='preview-only; not installed; no QA or release mutation'),stream,ensure_ascii=False,indent=2)
        stream.write('\n')
    print(json.dumps(report,ensure_ascii=False))

if __name__=='__main__':
    main()
