"""Add normalized RGBA diffusion as a distinct optional preview, no grid."""
from pathlib import Path
import importlib.util,json
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('continuous_insects',HERE/'preview.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
ROOT,OUT,REVIEW=base.ROOT,base.OUT,base.REVIEW


def main():
    assert not (OUT/'soft-result.json').exists()
    result=base.load(OUT/'result.json');records=[]
    for profile in result['profiles']:
        stage=(ROOT/profile['sources']['temporal_manifest']['path']).parent
        m=base.load(stage/'manifest.json');cycle=next(c for c in m['timing']['cycles'] if c['id']==profile['profile'])
        w,h=profile['canvas_x4'];frames=[];checks=[]
        label=profile['resref']+'-'+profile['profile']
        bg=(110,94,70) if profile['resref']=='SPIPLAAI' else (0,0,0)
        for phase,index in enumerate(cycle['timeline_frame_indices']):
            f=m['frames'][index];data=(stage/f['straight_raw_rgba_x4']).read_bytes()
            assert base.sha(data)==f['straight_raw_rgba_x4_sha256'].upper()
            fw,fh=f['physical_size_x4'];crop=np.frombuffer(data,np.uint8).reshape(fh,fw,4)
            l,t,r,b=f['runtime_crop_box_x4'];image=np.zeros((h,w,4),np.uint8);image[t+8:b+8,l+8:r+8]=crop
            alpha=image[:,:,3].astype(np.float32)/255
            prem=image[:,:,:3].astype(np.float32)*alpha[:,:,None]
            blurred_a=gaussian_filter(alpha,1.15,mode='constant',cval=0,truncate=4)
            blurred_p=np.stack([gaussian_filter(prem[:,:,c],1.15,mode='constant',cval=0,truncate=4) for c in range(3)],axis=2)
            out=np.zeros_like(image);out[:,:,3]=np.rint(blurred_a*255).clip(0,255).astype(np.uint8)
            visible=out[:,:,3]>0
            out[:,:,:3][visible]=np.rint(blurred_p[visible]/np.maximum(blurred_a[visible,None],1e-8)).clip(0,255).astype(np.uint8)
            assert not out[[0,-1],:,:].any() and not out[:,[0,-1],:].any()
            dest=OUT/'frames'/label/'diffus'/f'{phase:03d}.png';dest.parent.mkdir(parents=True,exist_ok=True)
            Image.fromarray(out,'RGBA').save(dest,compress_level=2)
            checks.append({'phase':phase,'path':base.rel(dest),'sha256':base.workflow.sha256_file(dest),
                           'source_sha256':base.sha(data),'alpha_mass_ratio':float(out[:,:,3].sum()/max(1,image[:,:,3].sum()))})
            frames.append(base.composed(out,bg))
        durations=[round((p+1)*1000/30)-round(p*1000/30) for p in range(len(frames))]
        dest=REVIEW/f'{label}-diffus.webp'
        frames[0].save(dest,format='WEBP',save_all=True,append_images=frames[1:],duration=durations,loop=0,lossless=True,method=3)
        assert Image.open(dest).n_frames==len(frames)
        records.append({'resref':profile['resref'],'profile':profile['profile'],'video':dest.name,'frames':checks})
        print(label,'soft RGBA complete',flush=True)
    base.save(OUT/'soft-result.json',{'status':'completed','method':'premultiplied RGB and alpha Gaussian sigma1.15 x4, normal RGB recovered after blur; no tiling or threshold',
        'profiles':records,'phases':sum(len(r['frames']) for r in records),'installed':False,'accepted':False})
    # The original3-view board remains reproducible and unchanged; publish the
    # extended comparison under a separate filename.
    page=(REVIEW/'index.html').read_text(encoding='utf-8').replace('repeat(3,minmax','repeat(4,minmax')
    page=page.replace('Essais non installés.</p>','La quatrième vue applique un micro-flou sur la couleur et la transparence. Essais non installés.</p>')
    for record in records:
        marker=f'<figure><img src="{record["resref"]}-{record["profile"]}-affine.webp"><figcaption>Contour continu plus fin</figcaption></figure>'
        assert marker in page
        page=page.replace(marker,marker+f'<figure><img src="{record["video"]}"><figcaption>Micro-flou couleur + alpha</figcaption></figure>')
    (REVIEW/'comparatif.html').write_text(page,encoding='utf-8')


if __name__=='__main__':main()
