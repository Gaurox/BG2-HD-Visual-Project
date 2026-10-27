"""Preview rounded and refined insect-particle alpha on the accepted frames.

Preserve accepted RGB where the old alpha is nonzero; extend edge RGB only into
new feather coverage. Compare all native looping cycles, no game mutation.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, minimum_filter, distance_transform_edt

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'effects/batches/insectes-contours-preview-20261027-v1'
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


def mask_variants(original):
    alpha=original[:,:,3]
    source=alpha.astype(np.float32)
    # 1.25 px at x4 = 0.3125 native pixels. Smooth the tiny square
    # footprints without thresholding away the gradually interpolated pixels.
    rounded=np.rint(gaussian_filter(source,1.25,mode='constant',cval=0,truncate=3)).clip(0,255).astype(np.uint8)
    # Optional 1 px x4 inset, then the same smooth curve: 0.25 native px.
    inward=minimum_filter(source,size=3,mode='constant',cval=0)
    refined=np.rint(gaussian_filter(inward,1.0,mode='constant',cval=0,truncate=3)).clip(0,255).astype(np.uint8)
    assert np.all(inward<=source)
    visible=alpha>0
    if visible.any():
        indices=distance_transform_edt(~visible,return_distances=False,return_indices=True)
        rgb=original[:,:,:3][tuple(indices)]
    else:rgb=np.zeros_like(original[:,:,:3])
    results=[]
    for mask in (rounded,refined):
        output=np.dstack((rgb,mask));output[mask==0]=0
        assert np.array_equal(output[:,:,:3][visible & (mask>0)],original[:,:,:3][visible & (mask>0)])
        assert not output[[0,-1],:,:].any() and not output[:,[0,-1],:].any()
        results.append(output)
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
        '<h1>Nuées d’insectes — essais de contours</h1><p>Mêmes couleurs et mêmes animations que la version actuelle. Arrondi : adoucissement des carrés ; affiné : retrait de 1 pixel en x4 puis adoucissement. Les fonds correspondent aux aperçus précédents. Essais non installés.</p>']
    labels={'SPIPLAAI':'Trajectoire / anneau (SPIPLARI / SPIPLAAI)','SPIPLAUI':'Nuée à l’impact (SPIPLAUI)','SPINSECT':'Autre nuée (SPINSECT)'}
    for p in profiles:
        page.append('<article><h2>'+labels[p['resref']]+' · '+p['profile']+'</h2><div class="views">')
        for path,title in zip(p['variants'],['Actuel','Arrondi','Affiné + arrondi'],strict=True):
            page.append(f'<figure><img src="{path}"><figcaption>{title}</figcaption></figure>')
        page.append('</div></article>')
    page.append('</html>');(REVIEW/'index.html').write_text('\n'.join(page),encoding='utf-8')
    save(OUT/'result.json',{'schema':'bg2-insect-outline-preview-v1','status':'completed',
        'profiles':profiles,'assets':3,'native_cycles':4,'phases':sum(p['frames'] for p in profiles),
        'method':{'arrondi':'Gaussian alpha sigma1.25 x4, no erosion',
                  'affine':'minimum-filter inset1 x4 then Gaussian alpha sigma1.0 x4',
                  'rgb':'accepted straight RGB exact on shared coverage; nearest covered RGB extended only to new coverage',
                  'durations':'accepted loop profiles at 30fps; identical native lengths',
                  'padding':'8px x4 to avoid clipping'},
        'installed':False,'accepted':False,'production_changed':False,'release_changed':False})
    print('COMPLETED',sum(p['frames'] for p in profiles),'phases',flush=True)


if __name__=='__main__':main()
