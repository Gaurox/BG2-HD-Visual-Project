"""Codex: compare palette quantization on all four scaler bases, offline only."""
from pathlib import Path
import csv,json,sys
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.ndimage import gaussian_filter,binary_erosion
from palette_lab import quantize_modes,linear,encode,palette_from_rows,srgb_u8_to_oklab,OUT,BAYER

STUDY=OUT.parent
FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',14)
PROFILES={'reference':[30,47,57,12,39,21,3], 'contrast':[30,63,3,12,39,21,57], 'pale':[30,55,30,0,39,30,0]}
rows=np.array(Image.open(OUT/'RANGES12.bmp').convert('RGB'))


def rgb_view(rgb,guide,scale):
    # Neutral offline background; shadow model is illustrative, not engine lighting.
    im=rgb.copy(); im[guide==0]=(53,57,62); im[guide==1]=(27,29,31)
    return Image.fromarray(im).resize((guide.shape[1]*8//scale,guide.shape[0]*8//scale),Image.Resampling.NEAREST)


def metrics(rgb,target,mask,scale):
    e=np.linalg.norm(srgb_u8_to_oklab(rgb)-srgb_u8_to_oklab(target),axis=-1)
    # Same kernel in logical pixels; conservative common foreground avoids halos.
    m=binary_erosion(mask,iterations=max(1,scale))
    a=gaussian_filter(linear(rgb),sigma=(.5*scale,.5*scale,0))
    b=gaussian_filter(linear(target),sigma=(.5*scale,.5*scale,0))
    ee=np.sqrt(np.mean((a-b)**2,-1))
    return dict(oklab_mean=float(e[mask].mean()) if mask.any() else 0,
                filtered_linear_rmse=float(np.sqrt(np.mean(ee[m]**2))) if m.any() else None,
                visible_pixels=int(mask.sum()),interior_pixels=int(m.sum()))


def plate(data,name):
    tiles=[]
    for base in ['xbr2','xbr4','rebout2','rebout4']:
        s=int(base[-1]);g=data[f'guide_x{s}'];p=data['palette']
        t=p[g] if base.startswith('xbr') else data[f'target_rgb_x{s}']
        q=quantize_modes(t,g,p,anchor=tuple(data['center']*s))
        tiles.append((base,g,s,[p[q['nearest']],p[q['ordered']],q['continuous']]))
    size=rgb_view(tiles[0][3][0],tiles[0][1],tiles[0][2]).size
    tw,th=size; gap=18; left=115
    image=Image.new('RGB',(left+3*(tw+gap)+20,90+4*(th+40)),(21,25,31));d=ImageDraw.Draw(image)
    d.text((16,10),f'Codex | {name} | meme taille logique, agrandissement x8',font=FONT,fill='white')
    for j,label in enumerate(['12/8 nuances, sans tramage','Bayer 4x4 fixe (non attenue)','Interpolation runtime simulee']):
        d.text((left+j*(tw+gap),48),label,font=SMALL,fill='#cbd8e7')
    for i,(base,g,s,rgbs) in enumerate(tiles):
        y=80+i*(th+40);d.text((12,y+15),base,font=FONT,fill='white')
        for j,r in enumerate(rgbs):image.paste(rgb_view(r,g,s),(left+j*(tw+gap),y))
    image.save(OUT/f'{name}_palette_modes.png')


def repeat_animation(data):
    g=data['guide_x4'];p=data['palette'];t=data['target_rgb_x4'];center=tuple(data['center']*4)
    frames=[]; prev=None; changed=[]
    for i in range(14):
        q=quantize_modes(t,g,p,anchor=center,seed=17+i)
        views=[rgb_view(p[q['nearest']],g,4),rgb_view(p[q['ordered']],g,4),rgb_view(p[q['random']],g,4)]
        w,h=views[0].size;im=Image.new('RGB',(3*(w+16)+16,h+70),(21,25,31));d=ImageDraw.Draw(im)
        d.text((10,7),'Frame source identique repetee : test de scintillement cree par le tramage',font=SMALL,fill='white')
        for k,v in enumerate(views):
            d.text((16+k*(w+16),34),['Sans tramage','Bayer fixe','Bruit aleatoire par frame'][k],font=SMALL,fill='white'); im.paste(v,(16+k*(w+16),64))
        if prev is not None:
            changed.append(float(np.mean(q['random'][g>=4]!=prev[g>=4])))
        prev=q['random'];frames.append(im)
    frames[0].save(OUT/'repeated_frame_dither.webp',save_all=True,append_images=frames[1:],duration=100,loop=0,lossless=True)
    return {'test':'same source frame repeated 14 times; not a measurement of deforming motion',
            'fixed_bayer_changed_fraction':0,'random_mean_changed_fraction':float(np.mean(changed))}


def body_motion():
    paths=sorted((STUDY/'upscale/samples').glob('CHFB1A1_00[01][0-9]/data.npz'))
    paths=[p for p in paths if int(p.parent.name.rsplit('_',1)[1])<14]
    samples=[dict(np.load(p)) for p in paths]
    s=4
    x0=min(-int(a['center'][0])*s for a in samples);y0=min(-int(a['center'][1])*s for a in samples)
    x1=max(a['guide_x4'].shape[1]-int(a['center'][0])*s for a in samples)
    y1=max(a['guide_x4'].shape[0]-int(a['center'][1])*s for a in samples)
    w,h=x1-x0,y1-y0;frames=[];prev=None;stable_count=0;changes={'ordered':0,'random':0,'nearest':0}
    for i,data in enumerate(samples):
        g=data['guide_x4'];p=data['palette'];t=data['target_rgb_x4'];q=quantize_modes(t,g,p,anchor=tuple(data['center']*s),seed=i+17)
        dx=-int(data['center'][0])*s-x0;dy=-int(data['center'][1])*s-y0
        shape=(h,w);guide=np.zeros(shape,np.uint8);target=np.zeros((*shape,3),np.uint8)
        sl=np.s_[dy:dy+g.shape[0],dx:dx+g.shape[1]];guide[sl]=g;target[sl]=t
        canvas_idx={}
        for k in ['nearest','ordered','random']:
            canvas_idx[k]=np.zeros(shape,np.uint8);canvas_idx[k][sl]=q[k]
        if prev is not None:
            pg,pt,pi=prev
            stable=(guide>=4)&(guide==pg)&(np.max(abs(target.astype(int)-pt.astype(int)),axis=-1)<=2)
            stable_count+=int(stable.sum())
            for k in changes:changes[k]+=int(np.sum(canvas_idx[k][stable]!=pi[k][stable]))
        prev=(guide,target,canvas_idx)
        display=[]
        for k in ['nearest','ordered','random']:
            display.append(rgb_view(p[canvas_idx[k]],guide,4))
        tw,th=display[0].size;image=Image.new('RGB',(3*(tw+16)+16,th+80),(21,25,31));draw=ImageDraw.Draw(image)
        draw.text((10,7),'CHFB1A1 cycle 0, 14 frames | aligne sur centre BAM | 100 ms/frame illustratifs',font=SMALL,fill='white')
        for j,tile in enumerate(display):
            draw.text((16+j*(tw+16),39),['Sans tramage','Bayer fixe sur origine acteur','Bruit aleatoire par frame'][j],font=SMALL,fill='white')
            image.paste(tile,(16+j*(tw+16),72))
        frames.append(image)
    frames[0].save(OUT/'body_motion_dither.webp',save_all=True,append_images=frames[1:],duration=100,loop=0,lossless=True)
    return dict(frames=len(frames),stable_support_pixels=stable_count,
                support_definition='actor-aligned, identical guide index >=4, target RGB change <=2 per component; no optical flow',
                changed_fraction={k:v/stable_count for k,v in changes.items()})


def main():
    results=[];picked=None;count=0
    for path in sorted((STUDY/'upscale/samples').glob('*/data.npz')):
        data=dict(np.load(path));source=data['source_indices']
        if source.size<=1:continue
        count+=1;name=path.parent.name
        if name=='CHFB1A1_0000':picked=data
        for base in ['xbr2','xbr4','rebout2','rebout4']:
            s=int(base[-1]);g=data[f'guide_x{s}'];p=data['palette'];t=p[g] if base.startswith('xbr') else data[f'target_rgb_x{s}']
            q=quantize_modes(t,g,p,anchor=tuple(data['center']*s))
            for mode in ['nearest','ordered','continuous']:
                rgb=q[mode] if mode=='continuous' else p[q[mode]]
                result=dict(sample=name,base=base,mode=mode,**metrics(rgb,t,g>=4,s))
                result['changed_vs_nearest_fraction']=None if mode=='continuous' else float(np.mean(q[mode][g>=4]!=q['nearest'][g>=4]))
                results.append(result)
            if name in ['CHFB1A1_0000','CHFF4A1_0045']:
                np.savez_compressed(OUT/f'{name}_{base}_weights.npz',lo=q['lo'],hi=q['hi'],weight=q['weight'],guide=g)
        if name in ['CHFB1A1_0000','CHFF4A1_0045']:plate(data,name)
    assert picked is not None
    temporal=repeat_animation(picked)
    # Recolor fixed indices/weights without rerunning the scaler or quantizer.
    g=picked['guide_x4'];p=picked['palette'];q=quantize_modes(picked['target_rgb_x4'],g,p,anchor=tuple(picked['center']*4))
    ims=[]
    for label,ids in PROFILES.items():
        pp=palette_from_rows(rows[ids]);a=linear(pp[q['lo']]);b=linear(pp[q['hi']])
        rgb=encode(a*(1-q['weight'][...,None])+b*q['weight'][...,None])
        ims.append((label,rgb_view(rgb,g,4)))
    w,h=ims[0][1].size;im=Image.new('RGB',(3*(w+20)+20,h+85),(21,25,31));d=ImageDraw.Draw(im)
    d.text((15,8),'Memes indices + memes poids ; 3 palettes joueur. Simulation sans eclairage.',font=SMALL,fill='white')
    for i,(label,tile) in enumerate(ims):d.text((20+i*(w+20),40),label,font=FONT,fill='white');im.paste(tile,(20+i*(w+20),72))
    im.save(OUT/'runtime_interpolation_recolor.png')
    with (OUT/'palette_trials.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=results[0]);writer.writeheader();writer.writerows(results)
    summary={'nonempty_frames':count,'temporal_synthetic':temporal,'temporal_real_cycle':body_motion(),'aggregates':[]}
    for base in ['xbr2','xbr4','rebout2','rebout4']:
        for mode in ['nearest','ordered','continuous']:
            entries=[r for r in results if r['base']==base and r['mode']==mode]
            vals=[r['filtered_linear_rmse'] for r in entries if r['filtered_linear_rmse'] is not None]
            summary['aggregates'].append(dict(base=base,mode=mode,mean_oklab=float(np.mean([r['oklab_mean'] for r in entries])),mean_filtered_linear_rmse=float(np.mean(vals)),frame_count=len(entries)))
    (OUT/'palette_trials_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
