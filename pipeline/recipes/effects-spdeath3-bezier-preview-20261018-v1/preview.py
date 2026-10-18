"""Trace native SPDEATH3 masks before temporal mixing; keep RGB and timing."""
from pathlib import Path
import json
import re
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.append(str(ROOT/'.tools/potracer'))  # append: never replace active NumPy
import effect_workflow as workflow
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam
from workspace_paths import get_path
from build_spatial_spline_alpha import potrace_alpha

OUT = ROOT/'effects/batches/spdeath3-bezier-continuous-alpha-preview-20261018-v1'
REVIEW = OUT/'review'
PREVIOUS = ROOT/'effects/batches/spdeath3-sdf-ankheg-preview-20261018-v1'
STAGE = ROOT/'effects/ressources/SPDEATH3/runs/spdeath3-apollo30-native-retimed-20261017-v1/02-interpolation'
load = lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
save = lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
sha = workflow.sha256_file
ev = lambda p:workflow.file_evidence(ROOT,p)


def gallery(data):
    page=(PREVIOUS/'review/index.html').read_text(encoding='utf-8')
    page=re.sub(r'const D=.*?, pics=new Map\(\);',lambda _: 'const D='+json.dumps(data,ensure_ascii=False)+', pics=new Map();',page,count=1)
    page=page.replace('<title>SPDEATH3 — masque SDF Ankheg</title>','<title>SPDEATH3 — courbes Bézier et alpha continu</title>')
    page=page.replace('<h1>33 · SPDEATH3 — lissage du masque SDF Ankheg</h1>','<h1>33 · SPDEATH3 — Bézier et alpha continu</h1>')
    page=page.replace('Avant / après synchronisés, RGB existants réutilisés. SDF borné : sigma4, correction du champ ±2 pixels x4, couverture8×8, sans retrait systématique. Durée et30FPS conservés. Aperçu uniquement ; version ingame inchangée.',
        'Trois versions synchronisées : installé / essai SDF / nouveau contour Bézier. Masques natifs vectorisés, couverture8×8, puis mélange alpha continu entre les poses avec les poids temporels existants. RGB et durée conservés. Cette méthode arrondit davantage les détails ; aperçu uniquement, jeu inchangé.')
    page=page.replace('<figure><figcaption>SDF Ankheg proposé</figcaption><canvas id="after"></canvas></figure>',
        '<figure><figcaption>Essai SDF Ankheg précédent</figcaption><canvas id="sdf"></canvas></figure><figure><figcaption>Bézier + alpha continu</figcaption><canvas id="after"></canvas></figure>')
    page=page.replace("names=['before','after']","names=['before','sdf','after']")
    page=page.replace('width="800" height="450"','width="1200" height="450"')
    page=page.replace('clearRect(0,0,800,450)','clearRect(0,0,1200,450)').replace('j<2;j++','j<names.length;j++')
    page=page.replace("j?'SDF Ankheg':'Actuel'","['Actuel','SDF Ankheg','Bézier + alpha continu'][j]")
    assert "names=['before','sdf','after']" in page and 'j<names.length' in page
    (REVIEW/'index.html').write_text(page,encoding='utf-8')


def main():
    assert not OUT.exists(),'Preserve previous preview; new version required'
    (REVIEW/'frames').mkdir(parents=True)
    installed=get_path('bg2ee_game_root',required=True)/'iee-assets/effects/manifest.json'
    installed_sha=sha(installed);source_evidence=ev(STAGE/'manifest.json')
    m=load(STAGE/'manifest.json');sp=load(ROOT/m['parent']['spatial_manifest'])
    cw,ch=sp['aligned_canvas_size_x1'];width,height=cw*4+8,ch*4+8
    bam=ROOT/'effects/ressources/SPDEATH3/source.bam';raw=read_bam(bam)
    frames,palette,transparent=decode_bam(raw);ap=native_palette_alpha(raw,transparent)
    native,traced,key_checks={},{},[]
    for k,(idx,*_) in enumerate(frames):
        a=np.zeros((ch,cw),np.uint8);x,y=sp['frames'][k]['canvas_offset_x1']
        a[y:y+idx.shape[0],x:x+idx.shape[1]]=ap[idx]
        native[k]=np.pad(a.repeat(4,0).repeat(4,1),4)
        # Unlimited boundary band: do not clamp the vector contour by old steps.
        traced[k],check=potrace_alpha(native[k],threshold=0,alphamax=1.334,
                                     opttolerance=0.1,supersample=8,band=10000)
        labels,count=ndimage.label(native[k]>0,np.ones((3,3)))
        masses=np.bincount(labels.ravel(),weights=traced[k].ravel(),minlength=count+1)
        assert not np.count_nonzero(masses[1:]==0),(k,'lost source component')
        key_checks.append({'native_frame':k,**check,'source_components':count,
                           'source_components_lost':0,'alpha_mass_ratio':float(traced[k].sum())/float(native[k].sum())})
    records=[];best=-1;sample=None;detail_focus=None;sample_id=None
    for f in m['frames']:
        n=f['frame'];stem=f'{n:03d}'
        source=np.array(Image.open(PREVIOUS/'review/frames'/f'before_{stem}.png').convert('RGBA'))
        previous=np.array(Image.open(PREVIOUS/'review/frames'/f'after_{stem}.png').convert('RGBA'))
        assert source.shape==(height,width,4)
        left,right=f['temporal_source_frames'];fraction=f['temporal_fraction']
        def mix(masks):
            return np.rint(masks[left].astype(np.float32)*(1-fraction)+masks[right].astype(np.float32)*fraction).astype(np.uint8)
        assert np.array_equal(mix(native),source[:,:,3]),'native alpha reconstruction must match all input phases'
        candidate=source.copy();candidate[:,:,3]=mix(traced)
        fg=source[:,:,3]>0;added=(candidate[:,:,3]>0)&~fg
        nearest=ndimage.distance_transform_edt(~fg,return_distances=False,return_indices=True)
        candidate[:,:,:3][added]=source[nearest[0][added],nearest[1][added],:3]
        visible=fg&(candidate[:,:,3]>0)
        assert np.array_equal(source[:,:,:3][visible],candidate[:,:,:3][visible])
        candidate[candidate[:,:,3]==0]=0
        assert candidate[:,:,3].any() and not candidate[[0,-1],:,:].any() and not candidate[:,[0,-1],:].any()
        primary=candidate.copy()
        primary[:,:,:3]=np.rint(primary[:,:,:3].astype(np.float32)*primary[:,:,3:4]/255).astype(np.uint8)
        assert np.all(primary[:,:,:3]<=primary[:,:,3:4])
        distance=ndimage.distance_transform_edt(~fg)
        maximum=float(distance[added].max()) if added.any() else 0
        assert maximum<=8,maximum
        for mode,pixels in [('before',source),('sdf',previous),('after',candidate)]:
            Image.fromarray(pixels).save(REVIEW/'frames'/f'{mode}_{stem}.png',compress_level=3)
        straight=REVIEW/'frames'/f'after_{stem}-straight.rgba';straight.write_bytes(candidate.tobytes())
        premult=REVIEW/'frames'/f'after_{stem}-premultiplied.rgba';premult.write_bytes(primary.tobytes())
        new_delta=np.abs(candidate[:,:,3].astype(float)-previous[:,:,3])
        untouched=previous[:,:,3]==source[:,:,3]
        residual=ndimage.gaussian_filter(new_delta*untouched,3)
        score=float(residual.max())
        if score>best:
            best=score;sample={'before':source.copy(),'sdf':previous.copy(),'after':candidate.copy()};sample_id=n
            cy,cx=np.unravel_index(residual.argmax(),residual.shape);detail_focus=[int(cx),int(cy)]
        fractional=int(((candidate[:,:,3]>0)&(candidate[:,:,3]<255)).sum())
        assert fractional>0,(n,'hard-only phase')
        records.append({'frame':n,'temporal_source_frames':[left,right],'temporal_fraction':fraction,
                        'native_temporal_alpha_reconstruction_exact':True,'visible_rgb_identical':True,
                        'fractional_alpha_pixels':fractional,'max_new_edge_distance_x4':maximum,
                        'alpha_mass_ratio':float(candidate[:,:,3].sum())/float(source[:,:,3].sum()),
                        'alpha_changed_from_previous_sdf':int(np.count_nonzero(candidate[:,:,3]!=previous[:,:,3])),
                        'straight':ev(straight),'premultiplied':ev(premult)})
    data={'profiles':load(PREVIOUS/'result.json')['profiles'],'size':[width,height],'detail_focus':detail_focus}
    gallery(data)
    cx,cy=detail_focus
    detail=Image.new('RGB',(1230,510),(25,32,42));draw=ImageDraw.Draw(detail)
    full=Image.new('RGB',(3*(width+16),height+40),(25,32,42));fd=ImageDraw.Draw(full)
    for col,(mode,title) in enumerate([('before','Installe'),('sdf','SDF precedent'),('after','Bezier + alpha continu')]):
        im=Image.fromarray(sample[mode]);im.save(REVIEW/f'{mode}-poster.png')
        region=im.crop((cx-24,cy-24,cx+24,cy+24)).resize((384,384),Image.Resampling.NEAREST)
        bg=Image.new('RGBA',region.size,(110,94,70,255))
        detail.paste(Image.alpha_composite(bg,region).convert('RGB'),(col*410+8,35))
        detail.paste(region.getchannel('A').resize((76,76),Image.Resampling.NEAREST).convert('RGB'),(col*410+8,426))
        draw.text((col*410+8,10),title,fill='white');draw.text((col*410+92,442),f'Alpha / phase {sample_id}',fill='white')
        bg=Image.new('RGBA',im.size,(110,94,70,255));full.paste(Image.alpha_composite(bg,im).convert('RGB'),(col*(width+16)+8,32));fd.text((col*(width+16)+8,8),title,fill='white')
    detail.save(REVIEW/'detail.png');full.save(REVIEW/'full-comparison.png')
    assert sha(installed)==installed_sha and ev(STAGE/'manifest.json')==source_evidence
    summary={'asset':'SPDEATH3','phases':len(records),'native_masks_vectorized':len(native),
             'method':'Potrace Bezier curves before temporal alpha interpolation',
             'alphamax':1.334,'opttolerance':0.1,'supersample':8,'inset_x4':0,'support_not_clamped_to_nearest':True,
             'alpha_mass_ratio_range':[min(r['alpha_mass_ratio'] for r in records),max(r['alpha_mass_ratio'] for r in records)],
             'max_added_edge_distance_x4':max(r['max_new_edge_distance_x4'] for r in records),
             'minimum_fractional_alpha_pixels_per_phase':min(r['fractional_alpha_pixels'] for r in records),
             'source_components_lost':0,'timing_and_existing_rgb_preserved':True,
             'sample_frame':sample_id,'detail_focus':detail_focus,'installed':False,'production_authorities_changed':False}
    save(OUT/'summary.json',summary)
    save(OUT/'result.json',{'summary':summary,'frames':records,'native_masks':key_checks,'profiles':data['profiles'],
         'source':source_evidence,'native_bam':ev(bam),'previous_sdf':ev(PREVIOUS/'result.json'),
         'vector_function':ev(ROOT/'pipeline/scripts/build_spatial_spline_alpha.py'),
         'producer':ev(Path(__file__)),'gallery_template':ev(PREVIOUS/'review/index.html'),
         'installed_manifest_unchanged_sha256':installed_sha,
         'algorithm_reference':'https://potrace.sourceforge.net/potrace.1.html',
         'difference':'vectorize each native pose first, interpolate continuous alpha by original fractions; no nearest opacity envelope or geometric core clamp',
         'qa':'pending-user-preview; no new neural inference or installation'})
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
