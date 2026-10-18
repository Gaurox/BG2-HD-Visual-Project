"""Audit all33 native palettes and5244 final frame pairs; no production mutation."""
from pathlib import Path
import hashlib
import json
import struct
import sys
import numpy as np
from scipy.ndimage import distance_transform_edt
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam
from workspace_paths import get_path
import effect_workflow as workflow

BATCH=ROOT/'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'
OUT=Path(__file__).parent
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
digest=lambda raw:hashlib.sha256(raw).hexdigest().upper()


def main():
    assert not (OUT/'audit.json').exists(),'Final audit must remain immutable'
    assets=load(BATCH/'batch.json')['assets'];results=[];previews=[]
    for a in assets:
        name=a['resref'];raw=read_bam(ROOT/a['source']);fs,pal,tr=decode_bam(raw);ap=native_palette_alpha(raw,tr)
        po=struct.unpack_from('<I',raw,16)[0]
        palette_a=np.frombuffer(raw,np.uint8,count=1024,offset=po).reshape(256,4)[:,3]
        used=np.unique(np.concatenate([i.ravel() for i,*_ in fs]));used=used[used!=tr]
        black_exact=used[pal[used].max(1)==0];black_near=used[pal[used].max(1)<=8]
        levels=sorted(int(v) for v in np.unique(ap[used]));assert levels==[255],name
        source_exact_pixels=sum(int(((pal[i].max(2)==0)&(i!=tr)).sum()) for i,*_ in fs)
        source_near_pixels=sum(int(((pal[i].max(2)<=8)&(i!=tr)).sum()) for i,*_ in fs)
        stage=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']/'02-interpolation'
        m=load(stage/'manifest.json');sp_path=ROOT/m['parent']['spatial_manifest'];sp=load(sp_path);cw,ch=sp['aligned_canvas_size_x1']
        cores={}
        for k,(idx,_,_,_) in enumerate(fs):
            x,y=sp['frames'][k]['canvas_offset_x1'];mask=np.zeros((ch,cw),bool)
            mask[y:y+idx.shape[0],x:x+idx.shape[1]]=(pal[idx].max(2)==0)&(idx!=tr)
            core=distance_transform_edt(np.pad(mask,1))[1:-1,1:-1]>2
            cores[k]=np.repeat(np.repeat(core,4,0),4,1)
        count=dict(phases=0,transparent_pixels=0,opaque_nearblack_pixels=0,
                   black_core_samples=0,black_core_rgb_max=0,black_core_over8_pixels=0)
        worst=None
        for f in m['frames']:
            w,h=f['physical_size_x4'];p=(stage/f['raw_rgba_x4']).read_bytes();s=(stage/f['straight_raw_rgba_x4']).read_bytes()
            assert digest(p)==f['raw_rgba_x4_sha256'] and digest(s)==f['straight_raw_rgba_x4_sha256']
            primary=np.frombuffer(p,np.uint8).reshape(h,w,4);straight=np.frombuffer(s,np.uint8).reshape(h,w,4)
            assert np.array_equal(primary[:,:,3],straight[:,:,3]),name
            transparent=primary[:,:,3]==0
            assert not primary[transparent].any() and not straight[transparent].any(),name
            assert np.all(primary[:,:,:3]<=primary[:,:,3:4]),name
            reconstructed=np.rint(straight[:,:,:3].astype(np.float32)*straight[:,:,3:4]/255).astype(np.uint8)
            assert np.abs(primary[:,:,:3].astype(np.int16)-reconstructed.astype(np.int16)).max()<=1,name
            opaque_black=(straight[:,:,3]>=240)&(straight[:,:,:3].max(2)<=8)
            count['phases']+=1;count['transparent_pixels']+=int(transparent.sum())
            count['opaque_nearblack_pixels']+=int(opaque_black.sum())
            left,right=f['temporal_source_frames'];l,t,r,b=f['runtime_crop_box_x4']
            core=(cores[left]&cores[right])[t:b,l:r] & (primary[:,:,3]>0)
            if core.any():
                values=primary[:,:,:3].max(2)[core]
                count['black_core_samples']+=len(values);count['black_core_rgb_max']=max(count['black_core_rgb_max'],int(values.max()))
                count['black_core_over8_pixels']+=int((values>8).sum())
            if worst is None or int(opaque_black.sum())>worst[0]:worst=(int(opaque_black.sum()),f['frame'],straight.copy())
        mode='requires-native-blend-contract' if source_near_pixels else 'index-transparency-no-native-nearblack-background'
        result={'resref':name,'aliases':a['reuse_aliases'],'frames_verified':count['phases'],
            'source_used_palette_a_raw':sorted(int(v) for v in np.unique(palette_a[used])),
            'source_effective_alpha_levels':levels,'native_gradated_alpha_entries':0,
            'source_exactblack_palette_indices':[int(v) for v in black_exact],
            'source_nearblack_palette_indices':[int(v) for v in black_near],
            'source_exactblack_pixels':source_exact_pixels,'source_nearblack_pixels':source_near_pixels,
            'output':count,'classification':mode,
            'export_alpha_verified':True,'transparent_rgb_zero_verified':True,'premultiplication_verified':True,
            'native_blend_at_runtime':'not-captured; no current installation for this lot',
            'normal_alpha_warning':bool(count['opaque_nearblack_pixels']),
            'run':workflow.file_evidence(ROOT,stage.parent/'run.json'),
            'manifest':workflow.file_evidence(ROOT,stage/'manifest.json')}
        results.append(result)
        if name in {'SPCCOLDL','SPHLYSM2','SPGENHLA','SPSPARKS','SPHORPUF','SPSMPUFF'}:
            previews.append((name,worst[1],worst[2]))
        print(name,'checked',count['phases'],'native black',source_exact_pixels,'nearblack',source_near_pixels,
              'opaque output',count['opaque_nearblack_pixels'],'core max',count['black_core_rgb_max'],flush=True)
    game=get_path('bg2ee_game_root',required=True);active=load(game/'iee-assets/effects/manifest.json')
    installed={r['resref'] for r in active['resources']}
    assert not installed & {a['resref'] for a in assets}
    summary={'assets':len(results),'frames_verified':sum(a['frames_verified'] for a in results),
        'all_transparent_pixels_rgb_zero':True,'all_companion_alpha_identical':True,'all_premultiplication_verified':True,
        'assets_with_native_nearblack_opaque_pixels':[a['resref'] for a in results if a['source_nearblack_pixels']],
        'assets_with_native_exactblack_opaque_pixels':[a['resref'] for a in results if a['source_exactblack_pixels']],
        'assets_with_output_opaque_nearblack_pixels':[a['resref'] for a in results if a['output']['opaque_nearblack_pixels']],
        'palette_gradated_alpha_assets':0,'installed_assets_from_this_lot':0,
        'native_blend_captured_assets':0,'all_ingame_transparency_guaranteed':False,
        'conclusion':'Exports preserve source alpha; RGB-black neutrality depends on native blend. Never route all33 to normal alpha. Actual native owner/blend/substitution must be verified during integration; no ingame success inferred.'}
    report={'schema':'bg2-effects-transparency-audit-v1','summary':summary,'assets':results,
        'production':workflow.file_evidence(ROOT,BATCH/'production.json'),
        'active_manifest_sha256':workflow.sha256_file(game/'iee-assets/effects/manifest.json'),
        'installed_dll_sha256':workflow.sha256_file(game/'InfinityEngine-Enhancer.dll'),
        'native_executable_sha256':workflow.sha256_file(game/'BaldurReal.exe'),
        'scope':'read-only33targeted; no installed/production/QA/release changes'}
    (OUT/'audit.json').write_bytes(workflow.json_bytes(report))
    sheet=Image.new('RGB',(1120,len(previews)*260),(32,36,42));draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    bg=np.array([110,94,70],np.float32)/255
    for row,(name,phase,arr) in enumerate(previews):
        src=arr[:,:,:3].astype(np.float32)/255;alpha=arr[:,:,3:4].astype(np.float32)/255
        normal=src*alpha+bg*(1-alpha)
        premult=src*alpha
        light=np.clip(premult+bg*(1-premult),0,1)
        black=np.clip(premult,0,1)
        draw.text((8,row*260+3),f'{name} phase{phase}: modes diagnostiques, pas une capture ingame',font=font,fill='white')
        for col,(pixels,label) in enumerate([(black,'RGB sur noir'),(normal,'Alpha normal / terrain'),(light,'Simulation RGB lumineuse')]):
            im=Image.fromarray(np.rint(pixels*255).astype(np.uint8));im.thumbnail((355,215),Image.Resampling.NEAREST)
            x=col*370;sheet.paste(im,(x+(355-im.width)//2,row*260+38+(215-im.height)//2));draw.text((x+4,row*260+23),label,font=font,fill=(190,205,220))
    sheet.save(OUT/'blend-diagnostic.png')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
