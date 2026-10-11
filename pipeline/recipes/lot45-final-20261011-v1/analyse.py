from pathlib import Path
import sys,io,json,hashlib
import numpy as np
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam
from export_bam_frames import read_bam,cycle_metadata
from bg2lib import load_key,resolve_resource
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v

def main():
    dest=ROOT/'animations/tmp/lot45-analysis-20261011-v1';dest.mkdir(parents=True,exist_ok=True)
    game=get_path('bg2ee_game_root');b,entries=load_key();palettes={}
    for n in ['PLT_MAGE','PLT_PURP']:
        override=game/'override'/(n+'.BMP')
        data=override.read_bytes() if override.exists() else resolve_resource(b,next(loc for ref,t,loc in entries if ref.upper()==n and t==1))[0]
        (dest/(n+'.bmp')).write_bytes(data)
        image=Image.open(io.BytesIO(data));palettes[n]=dict(size=image.size,mode=image.mode,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),
                bmp_palette=list(image.getpalette() or []))
        print(n,palettes[n]['size'],image.mode,len(data),flush=True)
    report={};sheet=Image.new('RGB',(1000,700),(32,32,32));draw=ImageDraw.Draw(sheet)
    for row,ref in enumerate(['AM0510A','AM3000E','FLM2PUR','AMWRPGT1']):
        data=read_bam(ROOT/f'animations/ressources/{ref}/source.bam');frames,palette,tr=decode_bam(data)
        groups={};geometries=[];rgba=[]
        for i,(idx,cx,cy,tr) in enumerate(frames):
            p=np.dstack([palette[idx],(idx!=tr).astype(np.uint8)*255]);p[p[...,3]==0,:3]=0
            key=hashlib.sha256(p.tobytes()+np.array([cx,cy,*idx.shape],np.int32).tobytes()).hexdigest()
            groups.setdefault(key,[]).append(i);rgba.append(p)
            geometries.append(dict(frame=i,size=[idx.shape[1],idx.shape[0]],centre=[cx,cy],visible_pixels=int((idx!=tr).sum())))
        cycles=cycle_metadata(data,len(frames))
        report[ref]=dict(frames=geometries,cycles=cycles,duplicate_groups=[g for g in groups.values() if len(g)>1],
            used_indices=sorted(set(int(i) for idx,*_ in frames for i in np.unique(idx))),palette_rgb=palette.tolist())
        draw.text((12,row*175+8),ref,fill='white')
        for col,i in enumerate([0,len(frames)//3,len(frames)*2//3]):
            im=Image.fromarray(rgba[i]);im=im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST)
            if im.height>145:im.thumbnail((280,145),Image.Resampling.NEAREST)
            bg=Image.new('RGBA',im.size,(32,32,32,255));im=Image.alpha_composite(bg,im).convert('RGB')
            sheet.paste(im,(col*330+20,row*175+25))
        print(ref,'frames',len(frames),'cycles',cycles,'duplicates',report[ref]['duplicate_groups'],flush=True)
    sheet.save(dest/'native-overview.png')
    v.write_json(dest/'analysis.json',dict(resources=report,palettes=palettes))
    for ref,pal in [('AM3000E','PLT_MAGE'),('FLM2PUR','PLT_PURP')]:
        used=report[ref]['used_indices'];external=np.array(palettes[pal]['bmp_palette']).reshape(-1,3).astype(np.uint8)
        print(ref,pal,'changed used colors',sum(not np.array_equal(report[ref]['palette_rgb'][i],external[i]) for i in used),flush=True)
        idx,cx,cy,tr=decode_bam(read_bam(ROOT/f'animations/ressources/{ref}/source.bam'))[0][len(report[ref]['frames'])//2]
        rgba=np.dstack([external[idx],(idx!=tr).astype(np.uint8)*255])
        Image.fromarray(rgba).resize((rgba.shape[1]*4,rgba.shape[0]*4),Image.Resampling.NEAREST).save(dest/(ref+'-'+pal+'.png'))
    lock=v.load_json(ROOT/'animations/index/area-pack-lock.json')
    for ref in report:print(ref,'first geometries',report[ref]['frames'][:2],flush=True)
    for area in ['AR0510','AR1008','OH4210','AR3000','AR3003','AR3011','AR3016','AR3017']:
        print(area,lock['areas'].get(area,{}).get('build'),flush=True)

if __name__=='__main__':main()
