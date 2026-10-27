"""Reconstruct continuous native contours, before temporal alpha mixing.

No independent discs or modulation inside4x4 cells. Solid neighbouring source
pixels remain a single filled shape; threshold a continuous field at4xSS.
"""
from pathlib import Path
import hashlib,json,sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, distance_transform_edt, binary_erosion

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'effects/batches/insectes-continu-preview-20261027-v1'
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


def native_masks(ref,spatial):
    source=spatial.parent.parent/'00-frames-x1';fm=load(source/'manifest.json');images={}
    evidence=[];ss=4
    for f in fm['frames']:
        path=source/'rgba'/f['file'];alpha=np.asarray(Image.open(path).convert('RGBA'))[:,:,3]
        assert set(np.unique(alpha))<={0,255}
        base=np.pad(alpha,2)>0  # 2 nativepx = 8px x4, same visual margin
        high=base.repeat(4*ss,0).repeat(4*ss,1).astype(np.float32)
        field=gaussian_filter(high,sigma=ss,mode='constant',cval=0,truncate=4)
        versions=[];h,w=base.shape
        interior=binary_erosion(base,structure=np.ones((3,3),bool))
        interior4=interior.repeat(4,0).repeat(4,1)
        for level in (.5,.6):
            coverage=np.rint((field>=level).reshape(h*4,ss,w*4,ss).mean(axis=(1,3))*255).astype(np.uint8)
            # An originally solid local region must stay filled: this directly
            # rejects the interior perforation responsible for the old grid.
            assert np.all(coverage[interior4]==255),'solid source region perforated'
            alive=coverage.reshape(h,4,w,4).max(axis=(1,3))
            assert np.all(alive[base]>0),'native speck removed'
            versions.append(coverage)
        images[f['frame']]=versions
        evidence.append({'frame':f['frame'],'source_sha256':workflow.sha256_file(path),
            'solid_interior_pixels_preserved':int(interior4.sum()),'all_native_specks_retained':True})
    return images,evidence


def mask_variants(original,frame,sources):
    alpha=original[:,:,3]
    left,right=frame['temporal_source_frames'];fraction=frame['temporal_fraction']
    masks=[np.rint(sources[left][v].astype(np.float32)*(1-fraction)+sources[right][v].astype(np.float32)*fraction).astype(np.uint8) for v in (0,1)]
    visible=alpha>0
    if visible.any():
        indices=distance_transform_edt(~visible,return_distances=False,return_indices=True)
        rgb=original[:,:,:3][tuple(indices)]
    else:rgb=np.zeros_like(original[:,:,:3])
    results=[]
    for mask in masks:
        assert mask.shape==alpha.shape
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
        sources,source_checks=native_masks(ref,spatial)
        save(OUT/'native-checks'/f'{ref}.json',source_checks)
        print(ref,len(sources),'native masks; no solid interior perforated',flush=True)
        bg=(110,94,70) if ref=='SPIPLAAI' else (0,0,0)
        for cycle in [c for c in m['timing']['cycles'] if c['loop_closed']]:
            label=f'{ref}-cycle{cycle["cycle"]:03d}-loop';videos=[[],[],[]];stats=[];frame_records=[]
            for phase,index in enumerate(cycle['timeline_frame_indices']):
                frame=m['frames'][index];path=stage/frame['straight_raw_rgba_x4']
                data=path.read_bytes();assert sha(data)==frame['straight_raw_rgba_x4_sha256'].upper()
                fw,fh=frame['physical_size_x4'];crop=np.frombuffer(data,np.uint8).reshape(fh,fw,4)
                l,t,r,b=frame['runtime_crop_box_x4'];assert [r-l,b-t]==[fw,fh]
                canvas=np.zeros((h+16,w+16,4),np.uint8);canvas[t+8:b+8,l+8:r+8]=crop
                rounded,refined=mask_variants(canvas,frame,sources)
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
        '<h1>Nuées d’insectes — formes continues</h1><p>Les pixels voisins restent reliés : reconstruction des contours natifs, puis interpolation des masques arrondis. Aucun disque indépendant, découpage en cases ou motif ajouté. Deux niveaux à comparer : arrondi conservateur et légèrement affiné. Les couleurs et les durées restent celles de la version actuelle. Essais non installés.</p>']
    labels={'SPIPLAAI':'Trajectoire / anneau (SPIPLARI / SPIPLAAI)','SPIPLAUI':'Nuée à l’impact (SPIPLAUI)','SPINSECT':'Autre nuée (SPINSECT)'}
    for p in profiles:
        page.append('<article><h2>'+labels[p['resref']]+' · '+p['profile']+'</h2><div class="views">')
        for path,title in zip(p['variants'],['Actuel','Contour continu arrondi','Contour continu plus fin'],strict=True):
            page.append(f'<figure><img src="{path}"><figcaption>{title}</figcaption></figure>')
        page.append('</div></article>')
    page.append('</html>');(REVIEW/'index.html').write_text('\n'.join(page),encoding='utf-8')
    save(OUT/'result.json',{'schema':'bg2-insect-continuous-outline-preview-v1','status':'completed',
        'profiles':profiles,'assets':3,'native_cycles':4,'phases':sum(p['frames'] for p in profiles),
        'method':{'arrondi':'native binary mask nearest16, Gaussian sigma4 at SS4, isocontour0.50, area coverage4x4',
                  'affine':'same continuous field, isocontour0.60',
                  'temporal':'reconstruct native source masks FIRST, then original temporal_source_frames/fraction mixing; no threshold on mixed temporal alpha',
                  'anti_grid':'no per-cell modulation; original solid3x3-native interiors remain filled; all original native specks retain nonzero coverage',
                  'rgb':'accepted straight RGB exact on shared coverage; nearest covered RGB extended only to new coverage',
                  'durations':'accepted loop profiles at 30fps; identical native lengths',
                  'padding':'8px x4 to avoid clipping'},
        'installed':False,'accepted':False,'production_changed':False,'release_changed':False})
    print('COMPLETED',sum(p['frames'] for p in profiles),'phases',flush=True)


if __name__=='__main__':main()
