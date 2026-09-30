"""Independent Codex experiment: original KEY/BIF -> xBR2/4 and ReboutCX4/Box2.

Run using config://chainner_python. Writes only beside this file; no installation.
Native xBR uses original false-color RGB for its geometry, exact palette provenance.
Rebout inference uses realized RANGES12 RGB; guide classes/alpha come from native xBR.
"""
from pathlib import Path
import sys, json, io, hashlib, time, argparse
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key, resolve_resource
from bam_export import load_bam, decode_bam
from run_creature_sprite_x2 import SourceFrame, run_xbr, direct_upscale_contract, xbr_provenance_indices, has_duplicate_used_rgba_indices, map_output, bam_cycles
from reboutcx_batch import load_model, infer_x4_box_x2
from reboutcx_quantize import character_chmb1_palette_rgb, character_chmb1_classes, quantize_classed_oklab, srgb_u8_to_oklab, index_class_table

OUT = Path(__file__).resolve().parent
FONT = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
PROFILES = {'reference':[30,47,57,12,39,21,3], 'contrast':[30,63,3,12,39,21,57], 'pale':[30,55,30,0,39,30,0]}

def digest(b): return hashlib.sha256(b).hexdigest()
def rgba(idx,pal):
    a=np.full(idx.shape,255,dtype=np.uint8); a[idx==0]=0; a[idx==1]=128
    return np.dstack([pal[idx],a])
def save_png(path,array): Image.fromarray(array).save(path)
def backdrop(sz):
    w,h=sz; y,x=np.indices((h,w)); v=np.where((x//16+y//16)%2,50,65).astype('uint8')
    return Image.fromarray(np.dstack([v,v,v,np.full_like(v,255)]))
def panel(images, labels, title, out, logical_scale=6):
    # images = (RGBA array, actual scale). Every displayed pixel covers same native area.
    ww=max(210,max(a.shape[1]//s for a,s in images)*logical_scale)
    hh=max(a.shape[0]//s for a,s in images)*logical_scale
    sheet=Image.new('RGBA',(len(images)*(ww+20)+20,hh+88),(24,27,33,255)); d=ImageDraw.Draw(sheet)
    d.text((16,8),title,font=FONT,fill='white')
    for j,((a,s),label) in enumerate(zip(images,labels)):
        dest=Image.fromarray(a).resize((a.shape[1]*logical_scale//s,a.shape[0]*logical_scale//s),Image.Resampling.NEAREST)
        tile=backdrop((ww,hh)); tile.alpha_composite(dest,((ww-dest.width)//2,hh-dest.height))
        sheet.alpha_composite(tile,(20+j*(ww+20),68)); d.text((20+j*(ww+20),39),label,font=FONT,fill='white')
    sheet.convert('RGB').save(out)
    return sheet.convert('RGB')

def run():
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/'samples').mkdir(exist_ok=True)
    bifs, resources=load_key(); lookup={(n.upper(),t):(n,t,l) for n,t,l in resources}
    ranges_raw,bif=resolve_resource(bifs,lookup['RANGES12',1][2]); ramps=np.asarray(Image.open(io.BytesIO(ranges_raw)).convert('RGB'))
    pal=character_chmb1_palette_rgb(ramps[PROFILES['reference']]); classes=character_chmb1_classes()
    class_table,_=index_class_table(classes)
    cache={}; provenance=[]
    def fetch(name):
        if name not in cache:
            entry=lookup[name,1000]; packed,bif=resolve_resource(bifs,entry[2]); raw=load_bam(bifs,entry)
            frames,palette,tr=decode_bam(raw)
            cache[name]=(frames,palette,tr,bam_cycles(raw))
            provenance.append({'resref':name,'locator':hex(entry[2]),'bif':bif,'sha256_bif_resource':digest(packed),'sha256_bam_decoded':digest(raw),'frames':len(frames)})
        return cache[name]
    selections=[]
    for n in ['CHFB1A1','CHFB2A1','CHFB3A1','CHFF4A1']:
        selections.append((n,fetch(n)[3][3]['frame_indices'][0]))
    for n in ['CHFB1A1','WQNS0A1','WQNC0A1','WQNJ6A1']:
        selections.extend((n,i) for i in fetch(n)[3][0]['frame_indices'])
    records=[]; frames=[]
    for n,i in selections:
        fs,p,tr,cycles=fetch(n); idx,cx,cy,_=fs[i]; h,w=idx.shape
        if w*h<=1: raise ValueError(f'Null/split-BAM marker selected: {n} {i}')
        # Original source false-color palette for the exact xBR geometry algorithm.
        original=np.dstack([p[idx],np.where(idx==tr,0,255).astype('uint8')])
        frame=SourceFrame(n,i,w,h,cx,cy,tr,idx,p,original.tobytes()); frames.append(frame)
        records.append({'resref':n,'frame':i,'width':w,'height':h,'center':[cx,cy]})
    xbrs={}; timings={}
    for scale in [2,4]:
        start=time.perf_counter(); rendered=run_xbr(frames,get_path('mmpx_scalepix',required=True),'node',direct_upscale_contract(scale)); timings[f'xbr{scale}_batch_s']=time.perf_counter()-start
        start=time.perf_counter(); xbrs[scale]=[]
        for frame,(w,h,raw) in zip(frames,rendered):
            prov=xbr_provenance_indices(frame,scale) if has_duplicate_used_rgba_indices(frame) else None
            idx,_=map_output(frame,raw,prov); xbrs[scale].append(idx.reshape(h,w))
        timings[f'xbr{scale}_map_provenance_s']=time.perf_counter()-start
    start=time.perf_counter(); descriptor,versions=load_model(get_path('reboutcx_model',required=True),device='cuda:0',fp16=True); timings['model_load_s']=time.perf_counter()-start
    metrics=[]; all_results={}
    for k,(frame,rec) in enumerate(zip(frames,records)):
        n=frame.resref; i=frame.index; key=f'{n}_{i:04d}'; folder=OUT/'samples'/key; folder.mkdir(exist_ok=True)
        rgb=pal[frame.indices]; opaque=frame.indices!=0
        nearest=distance_transform_edt(~opaque,return_distances=False,return_indices=True)
        filled=rgb[tuple(nearest)]
        start=time.perf_counter(); rgb4,rgb2=infer_x4_box_x2(descriptor,filled,fp16=True); elapsed=time.perf_counter()-start
        rec['rebout_inference_s']=elapsed
        targets={2:rgb2,4:rgb4}; data={'source_indices':frame.indices,'source_palette':frame.palette,'palette':pal,'ramps':ramps,'center':np.array([frame.center_x,frame.center_y])}
        results={'vanilla':rgba(frame.indices,pal)}
        save_png(folder/'vanilla.png',results['vanilla'])
        for scale in [2,4]:
            guide=xbrs[scale][k]; target=targets[scale]
            q_used,_=quantize_classed_oklab(target,guide,pal,np.unique(frame.indices),classes,transparent_index=0)
            q_full,_=quantize_classed_oklab(target,guide,pal,np.arange(256),classes,transparent_index=0)
            visible=guide>1
            targetlab=srgb_u8_to_oklab(target); usedlab=srgb_u8_to_oklab(pal[q_used]); fulllab=srgb_u8_to_oklab(pal[q_full]); guidelab=srgb_u8_to_oklab(pal[guide])
            nn=frame.indices.repeat(scale,0).repeat(scale,1)
            metric={'sample':key,'scale':scale,'pixels_visible':int(visible.sum()),'source_indices':len(np.unique(frame.indices)),
                'xbr_indices':len(np.unique(guide)),'rebout_used_indices':len(np.unique(q_used)),'rebout_full_indices':len(np.unique(q_full)),
                'rebout_raw_rgb_unique_visible':len(np.unique(target[visible],axis=0)),
                'xbr_vs_nn_changed_pct_all':100*float(np.mean(guide!=nn)),
                'mask_symmetric_difference_vs_nn_px':int(np.count_nonzero((guide==0)!=(nn==0))),
                'full_vs_used_different_pct_visible':100*float(np.mean(q_full[visible]!=q_used[visible])),
                'introduced_indices_absent_source':sorted(set(np.unique(q_full).tolist())-set(np.unique(frame.indices).tolist())),
                'oklab_error_used_mean':float(np.linalg.norm(targetlab[visible]-usedlab[visible],axis=1).mean()),
                'oklab_error_full_mean':float(np.linalg.norm(targetlab[visible]-fulllab[visible],axis=1).mean()),
                'oklab_target_distance_xbr_mean':float(np.linalg.norm(targetlab[visible]-guidelab[visible],axis=1).mean()),
                'class_changes_full':int(np.count_nonzero(class_table[q_full]!=class_table[guide])),
                'alpha_changes_full':int(np.count_nonzero((q_full==0)!=(guide==0)))}
            metrics.append(metric)
            data[f'guide_x{scale}']=guide; data[f'target_rgb_x{scale}']=target; data[f'quant_used_x{scale}']=q_used; data[f'quant_full_x{scale}']=q_full
            results[f'xbr{scale}']=rgba(guide,pal); results[f'rebout{scale}']=rgba(q_full,pal); results[f'rebout_used{scale}']=rgba(q_used,pal)
            results[f'rebout_raw{scale}']=np.dstack([target,rgba(guide,pal)[:,:,3]])
            for variant in [f'xbr{scale}',f'rebout{scale}',f'rebout_used{scale}',f'rebout_raw{scale}']: save_png(folder/f'{variant}.png',results[variant])
        np.savez_compressed(folder/'data.npz',**data)
        (folder/'metadata.json').write_text(json.dumps(rec,indent=2)+'\n')
        all_results[key]=results
        # First four walking-armour frames + representative attack/equipment frame 6.
        if k<4 or frame.index==6:
            panel([(results['vanilla'],1),(results['xbr2'],2),(results['xbr4'],4),(results['rebout2'],2),(results['rebout4'],4)],['Vanilla','XBR x2','XBR x4 direct','ReboutCX x2','ReboutCX x4'],key+' | reference; classes completes; affichage x8 natif',folder/'compare_four.png',8)
            panel([(results['rebout_used4'],4),(results['rebout4'],4),(results['rebout_raw4'],4)],['Palette source','Classes completes','RGB avant palette'],key+' | ReboutCX x4; meme silhouette XBR; affichage x8',folder/'compare_quantization.png',8)
        if k==0: print('FIRST_NPZ_READY',folder/'data.npz',flush=True)
        print('DONE',key,round(elapsed,3),flush=True)
    # Aligned animated body only: no assertion on direction-dependent equipment z-order.
    anim=[]; variants=[('vanilla',1),('xbr2',2),('xbr4',4),('rebout2',2),('rebout4',4)]
    for i in range(14):
        key=f'CHFB1A1_{i:04d}'; result=all_results[key]; rec=next(r for r in records if r['resref']=='CHFB1A1' and r['frame']==i)
        imgs=[]
        for variant,scale in variants:
            canvas=Image.new('RGBA',(96*scale,90*scale)); cx,cy=rec['center']; canvas.alpha_composite(Image.fromarray(result[variant]),((48-cx)*scale,(66-cy)*scale)); imgs.append((np.asarray(canvas),scale))
        anim.append(panel(imgs,['Vanilla','XBR x2','XBR x4 direct','ReboutCX x2','ReboutCX x4'],f'CHFB1A1 cycle 0 | frame {i:02d} | anchor fixe | 100 ms',OUT/f'animation_frame_{i:02d}.png',4))
    anim[0].save(OUT/'attack_comparison.webp',save_all=True,append_images=anim[1:],duration=100,loop=0,lossless=True)
    # Rerender the same indexed samples with distinct player-color selections.
    key='CHFB1A1_0045'; folder=OUT/'samples'/key; data=np.load(folder/'data.npz')
    for profile,colors in PROFILES.items():
        p=character_chmb1_palette_rgb(ramps[colors])
        ims=[(rgba(data['source_indices'],p),1),(rgba(data['guide_x2'],p),2),(rgba(data['guide_x4'],p),4),(rgba(data['quant_full_x2'],p),2),(rgba(data['quant_full_x4'],p),4)]
        panel(ims,['Vanilla','XBR x2','XBR x4 direct','ReboutCX x2','ReboutCX x4'],f'{key} | recoloration {profile} {colors} | indices identiques',OUT/f'recolor_{profile}.png',8)
    timings['total_inference_s']=sum(r['rebout_inference_s'] for r in records)
    manifest={'author':'Codex independent experiment 2026-09-29','inputs':provenance,'ranges12':{'sha256':digest(ranges_raw),'dimensions':list(ramps.shape),'profiles':PROFILES},'versions':versions,'model_sha256':digest(get_path('reboutcx_model').read_bytes()),'scalepix_sha256':digest(get_path('mmpx_scalepix').read_bytes()),'timings':timings,'frames':records,'metrics':metrics,'notes':['xBR direct: original false-color RGB geometry, no blending, exact index provenance.','ReboutCX model x4 native, x2 generated by Box on x4 float before uint8 rounding.','ReboutCX alpha and semantic class masks supplied by xBR at matching scale.','Full-class quantization is an experimental asset recipe; runtime source representative restrictions must be changed before installation.','Reference colors are illustrative. No lights, palette effects, engine occlusion, or ingame claim.','WEBP animation timing 100ms is a comparison cadence, not inferred native engine speed.']}
    (OUT/'results.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('FINISHED',OUT/'results.json',flush=True)

if __name__=='__main__': run()
