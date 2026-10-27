"""Render each native insect pixel as an individually antialiased x4 dot.

No temporal object tracking is inferred: dot shapes are fixed by canvas position
and native clock/linear alpha mixing are inherited from accepted frames.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'effects/batches/insectes-particules-preview-20261027-v1'
REVIEW=OUT/'review'
BASE=ROOT/'effects/batches/lot26-seedvr7b-apollo30-20261017-v2/review'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def rel(p):return p.relative_to(ROOT).as_posix()


MASK_CACHE={}
def templates(w,h):
    assert w%4==0 and h%4==0
    if (w,h) in MASK_CACHE:return MASK_CACHE[(w,h)]
    # 16 deterministic subpixel offsets/sizes, fixed in world-aligned canvas
    # coordinates so every frame uses the same rule. Compute per-pixel coverage
    # at 8x8 supersampling, separately for each 4x4 native pixel footprint.
    yy,xx=np.indices((h//4,w//4),dtype=np.uint32)
    types=((xx*17+yy*31+(xx*yy)*7)%16).astype(np.uint8)
    sample=(np.arange(32,dtype=np.float32)+.5)/8-2
    sy,sx=np.meshgrid(sample,sample,indexing='ij')
    result=[]
    for base in (1.60,1.15):
        kernels=[]
        for k in range(16):
            dx=((k%4)-1.5)*.15;dy=((k//4)-1.5)*.15
            radius=base+((k*7%5)-2)*.055
            fine=((sx-dx)**2+(sy-dy)**2)<=radius**2
            mask=np.rint(fine.reshape(4,8,4,8).mean(axis=(1,3))*255).astype(np.uint8)
            assert mask.max()>127
            kernels.append(mask)
        kernel=np.asarray(kernels,dtype=np.uint8)[types]
        result.append(kernel.transpose(0,2,1,3).reshape(h,w))
    MASK_CACHE[(w,h)]=result
    return result


def mask_variants(original):
    h,w=original.shape[:2];alpha=original[:,:,3];blocks=alpha.reshape(h//4,4,w//4,4)
    # Every footprint still carries the unchanged native/temporal coverage;
    # do not silently treat a different or already retouched mask as pixels.
    native=blocks[:,0,:,0]
    assert np.all(blocks==native[:,None,:,None]),'native alpha is not constant per x4 cell'
    results=[]
    for kernel in templates(w,h):
        mask=np.rint(alpha.astype(np.float32)*kernel.astype(np.float32)/255).astype(np.uint8)
        out=original.copy();out[:,:,3]=mask;out[mask==0]=0
        active=mask.reshape(h//4,4,w//4,4).max(axis=(1,3))
        assert np.all(active[native>0]>0),'a native particle disappeared'
        assert np.array_equal(out[:,:,:3][mask>0],original[:,:,:3][mask>0])
        assert not out[[0,-1],:,:].any() and not out[:,[0,-1],:].any()
        results.append(out)
    return results


def composed(rgba,bg):
    image=Image.fromarray(rgba,'RGBA'); back=Image.new('RGBA',image.size,(*bg,255))
    return Image.alpha_composite(back,image).convert('RGB')


def main():
    assert not (OUT/'result.json').exists(), 'Preview is sealed; use a new version'
    profiles=[]; all_stats=[]
    for ref in ['SPIPLAAI','SPIPLAUI','SPINSECT']:
        spatial=ROOT/'effects/ressources'/ref/'runs'/f'{ref.lower()}-seedvr7b-x4-20261017-v1'/'01-spatial-x4/manifest.json'
        stage=ROOT/'effects/ressources'/ref/'runs'/f'{ref.lower()}-apollo30-retimed-strict-20261017-v2'/'02-interpolation'
        m=load(stage/'manifest.json');sp=load(spatial);w,h=[v*4 for v in sp['aligned_canvas_size_x1']]
        bg=(110,94,70) if ref=='SPIPLAAI' else (0,0,0)
        for cycle in [c for c in m['timing']['cycles'] if c['loop_closed']]:
            label=f'{ref}-cycle{cycle["cycle"]:03d}-loop';videos=[[],[],[]];stats=[];frame_records=[]
            for phase,index in enumerate(cycle['timeline_frame_indices']):
                frame=m['frames'][index];path=stage/frame['straight_raw_rgba_x4']
                data=path.read_bytes();assert sha(data)==frame['straight_raw_rgba_x4_sha256'].upper()
                fw,fh=frame['physical_size_x4'];crop=np.frombuffer(data,np.uint8).reshape(fh,fw,4)
                l,t,r,b=frame['runtime_crop_box_x4'];assert [r-l,b-t]==[fw,fh]
                canvas=np.zeros((h+16,w+16,4),np.uint8);canvas[t+8:b+8,l+8:r+8]=crop
                rounded,refined=mask_variants(canvas)
                outputs=[]
                for mode,img in [('arrondi',rounded),('affine',refined)]:
                    dest=OUT/'frames'/label/mode/f'{phase:03d}.png';dest.parent.mkdir(parents=True,exist_ok=True)
                    Image.fromarray(img,'RGBA').save(dest,compress_level=2)
                    outputs.append({'mode':mode,'path':rel(dest),'sha256':workflow.sha256_file(dest)})
                counts=[int(x[:,:,3].sum()) for x in (canvas,rounded,refined)]
                assert counts[0]==0 or counts[1]>0 and counts[2]>0,(ref,label,phase,counts)
                stats.append(counts)
                frame_records.append({'phase':phase,'source_frame':index,'source_sha256':sha(data),'outputs':outputs,'alpha_mass':counts})
                for arr,rgba in zip(videos,(canvas,rounded,refined),strict=True):arr.append(composed(rgba,bg))
            assert len(videos[0])==cycle['phase_count']
            durations=[round((p+1)*1000/30)-round(p*1000/30) for p in range(len(videos[0]))]
            assert abs(sum(durations)-len(cycle['native_slots'])*1000/15)<=1
            REVIEW.mkdir(parents=True,exist_ok=True)
            paths=[]
            for mode,images in zip(['actuel','arrondi','affine'],videos,strict=True):
                dest=REVIEW/f'{label}-{mode}.webp'
                images[0].save(dest,format='WEBP',save_all=True,append_images=images[1:],duration=durations,loop=0,lossless=True,method=3)
                probe=Image.open(dest);assert probe.n_frames==len(images)
                paths.append(dest.name)
            evidence={'resref':ref,'profile':cycle['id'],'duration_rational':cycle['duration_rational'],
                'frames':len(videos[0]),'canvas_x4':[w+16,h+16], 'padding_x4':8,
                'sources':{'temporal_manifest':workflow.file_evidence(ROOT,stage/'manifest.json'),
                           'spatial_manifest':workflow.file_evidence(ROOT,spatial)},
                'variants':paths,'frame_records':frame_records,
                'alpha_mass_ratios':[sum(x[i] for x in stats)/max(1,sum(x[0] for x in stats)) for i in (1,2)]}
            profiles.append(evidence);all_stats.extend(stats)
            print(label,len(videos[0]),'phases; alpha ratios',evidence['alpha_mass_ratios'],flush=True)
    page=['<!doctype html><html lang="fr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">',
        '<title>Insectes — essais contours</title><style>body{font:15px system-ui;background:#111822;color:#ecf1f8;margin:24px}article{background:#1d2938;border-radius:12px;padding:16px;margin:16px 0}.views{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}figure{margin:0}img{width:100%;height:280px;object-fit:contain;image-rendering:pixelated;background:#080808}figcaption{padding-top:6px;color:#c9d6e4}p{max-width:1100px}</style>',
        '<h1>Nuées d’insectes — particules individuelles</h1><p>Chaque pixel natif devient un petit point arrondi en x4 : une taille arrondie et une taille plus fine. Les couleurs et les phases restent celles de la version actuelle. Formes antialiasées et petites variations stables selon la position ; aucun flou global. Essais non installés.</p>']
    labels={'SPIPLAAI':'Trajectoire / anneau (SPIPLARI / SPIPLAAI)','SPIPLAUI':'Nuée à l’impact (SPIPLAUI)','SPINSECT':'Autre nuée (SPINSECT)'}
    for p in profiles:
        page.append('<article><h2>'+labels[p['resref']]+' · '+p['profile']+'</h2><div class="views">')
        for path,title in zip(p['variants'],['Actuel · carrés x4','Particules arrondies','Particules plus fines'],strict=True):
            page.append(f'<figure><img src="{path}"><figcaption>{title}</figcaption></figure>')
        page.append('</div></article>')
    page.append('</html>');(REVIEW/'index.html').write_text('\n'.join(page),encoding='utf-8')
    save(OUT/'result.json',{'schema':'bg2-insect-particle-preview-v1','status':'completed',
        'profiles':profiles,'assets':3,'native_cycles':4,'phases':sum(p['frames'] for p in profiles),
        'method':{'arrondi':'one antialiased dot per native pixel: radius1.60±0.11 x4, supersampling8',
                  'affine':'one antialiased dot per native pixel: radius1.15±0.11 x4, supersampling8',
                  'variation':'16 stable per-position subpixel offset/size templates; no inter-frame randomization or inferred particle tracking',
                  'rgb':'accepted straight RGB exact on retained coverage; no pixels or blur outside the original alpha',
                  'durations':'accepted loop profiles at 30fps; identical native lengths',
                  'padding':'8px x4 to avoid clipping'},
        'installed':False,'accepted':False,'production_changed':False,'release_changed':False})
    print('COMPLETED',sum(p['frames'] for p in profiles),'phases',flush=True)


if __name__=='__main__':main()
