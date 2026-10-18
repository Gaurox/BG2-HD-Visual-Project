"""SPDEATH3 approved Bezier base: compare two Gaussian premultiplied edge fades."""
from pathlib import Path
import json
import re
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

BASE=ROOT/'effects/batches/spdeath3-bezier-continuous-alpha-preview-20261018-v1'
OUT=ROOT/'effects/batches/spdeath3-bezier-edgefade-preview-20261018-v1'
REVIEW=OUT/'review'
REFERENCE=ROOT/'pipeline/recipes/am3000e-contour-soft-20261011-v1/build.py'
VARIANTS={'soft2':2.,'soft4':4.}
PAD=16
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
save=lambda p,v:p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
ev=lambda p:workflow.file_evidence(ROOT,p)


def soften(p,sigma):
    original=np.pad(p,((PAD,PAD),(PAD,PAD),(0,0)))
    distance=distance_transform_edt(original[:,:,3]>0)
    full,core=2*sigma,4*sigma
    t=np.clip((distance-full)/(core-full),0,1)
    weight=1-t*t*(3-2*t)
    blurred=gaussian_filter(original.astype(np.float32),sigma=(sigma,sigma,0),mode='constant',cval=0,truncate=4)
    result=np.rint(original*(1-weight[:,:,None])+blurred*weight[:,:,None]).clip(0,255).astype(np.uint8)
    result[result[:,:,3]==0]=0
    interior=distance>=core
    assert np.array_equal(result[interior],original[interior])
    assert np.all(result[:,:,:3]<=result[:,:,3:4])
    assert not result[[0,-1],:,:].any() and not result[:,[0,-1],:].any(),'blur clipped'
    return result,original,interior


def gallery(data):
    page=(BASE/'review/index.html').read_text(encoding='utf-8')
    page=re.sub(r'const D=.*?, pics=new Map\(\);',lambda _:'const D='+json.dumps(data,ensure_ascii=False)+', pics=new Map();',page,count=1)
    page=page.replace('<title>SPDEATH3 — courbes Bézier et alpha continu</title>','<title>SPDEATH3 — fondu gaussien des contours</title>')
    page=page.replace('<h1>33 · SPDEATH3 — Bézier et alpha continu</h1>','<h1>33 · SPDEATH3 — fondu des contours</h1>')
    page=re.sub(r'<p>Trois versions synchronisées:?.*?</p>',
        '<p>Base Bézier validée / fondu doux sigma2 / fondu plus diffus sigma4. Filtre gaussien RGBA prémultiplié limité au contour ; cœur exact au-delà de8 ou16pixels x4. Mêmes124phases et durées, aucun retrait systématique. Aperçu uniquement, jeu inchangé.</p>',page,count=1,flags=re.S)
    page=page.replace('<figcaption>Masque installé actuel</figcaption>','<figcaption>Bézier validé — témoin</figcaption>')
    page=page.replace('<figcaption>Essai SDF Ankheg précédent</figcaption><canvas id="sdf">','<figcaption>Fondu doux · sigma2</figcaption><canvas id="soft2">')
    page=page.replace('<figcaption>Bézier + alpha continu</figcaption><canvas id="after">','<figcaption>Fondu diffus · sigma4</figcaption><canvas id="soft4">')
    page=page.replace("names=['before','sdf','after']","names=['before','soft2','soft4']")
    page=page.replace("['Actuel','SDF Ankheg','Bézier + alpha continu'][j]","['Bézier validé','Fondu doux sigma2','Fondu diffus sigma4'][j]")
    page=page.replace('La marge transparente de4pixels sert à montrer les bords reconstruits sans les couper ; mêmes coordonnées et marge sur les trois vues.',
        'La marge transparente supplémentaire de16pixels évite de couper le fondu ; mêmes coordonnées et marge sur les trois vues.')
    assert "names=['before','soft2','soft4']" in page and 'Base Bézier validée / fondu doux' in page
    (REVIEW/'index.html').write_text(page,encoding='utf-8')


def main():
    assert not OUT.exists(),'Use a new version instead of overwriting a completed preview'
    (REVIEW/'frames').mkdir(parents=True)
    old=load(BASE/'result.json');summary=old['summary'];bw,bh=224,384
    installed=get_path('bg2ee_game_root',required=True)/'iee-assets/effects/manifest.json'
    installed_sha=workflow.sha256_file(installed)
    save(OUT/'accepted-base.json',{'scope':'SPDEATH3 Bezier preview contour only',
         'user_statement':'super ! validé ! peux tu ajouter un flou gaussien / fondu transparance sur les contours pour que ca s\'integre mieux aux décors',
         'reference':ev(BASE/'result.json'),'visual_preview_accepted':True,
         'ingame_acceptance_inferred':False,'whole_lot_acceptance_inferred':False})
    records=[];sample=None;sample_id=summary['sample_frame']
    for f in old['frames']:
        n=f['frame'];stem=f'{n:03d}'
        primary_path=ROOT/f['premultiplied']['path'];straight_path=ROOT/f['straight']['path']
        assert ev(primary_path)==f['premultiplied'] and ev(straight_path)==f['straight']
        primary=np.fromfile(primary_path,np.uint8).reshape(bh,bw,4)
        straight=np.fromfile(straight_path,np.uint8).reshape(bh,bw,4)
        padded=np.pad(straight,((PAD,PAD),(PAD,PAD),(0,0)))
        Image.fromarray(padded).save(REVIEW/'frames'/f'before_{stem}.png',compress_level=3)
        variants={};display={'before':padded}
        for key,sigma in VARIANTS.items():
            result,original,core=soften(primary,sigma)
            a=result[:,:,3:4].astype(np.float32)
            normal=result.copy()
            normal[:,:,:3]=np.rint(np.clip(result[:,:,:3].astype(np.float32)*255/np.maximum(a,1),0,255)).astype(np.uint8)
            normal[core]=padded[core]  # preserve straight RGB and opacity in the core too
            normal[normal[:,:,3]==0]=0
            assert np.array_equal(normal[core],padded[core])
            reconstructed=np.rint(normal[:,:,:3].astype(np.float32)*normal[:,:,3:4]/255).astype(np.uint8)
            assert np.abs(reconstructed.astype(np.int16)-result[:,:,:3].astype(np.int16)).max()<=1
            assert normal[:,:,3].any()
            Image.fromarray(normal).save(REVIEW/'frames'/f'{key}_{stem}.png',compress_level=3)
            raw=REVIEW/'frames'/f'{key}_{stem}-premultiplied.rgba';raw.write_bytes(result.tobytes())
            raw_s=REVIEW/'frames'/f'{key}_{stem}-straight.rgba';raw_s.write_bytes(normal.tobytes())
            variants[key]={'sigma_x4':sigma,'unchanged_core_beyond_x4':4*sigma,
                           'premultiplied':ev(raw),'straight':ev(raw_s),'core_rgba_exact':True,
                           'alpha_mass_ratio':float(result[:,:,3].sum())/float(original[:,:,3].sum()),
                           'premultiplied_rgb_flux_ratio':float(result[:,:,:3].sum())/float(original[:,:,:3].sum()),
                           'no_new_empty_frame':True,'transparent_border_clear':True}
            display[key]=normal
        if n==sample_id:sample={k:v.copy() for k,v in display.items()}
        records.append({'frame':n,'variants':variants})
    width,height=bw+2*PAD,bh+2*PAD
    focus=[v+PAD for v in summary['detail_focus']]
    gallery({'profiles':old['profiles'],'size':[width,height],'detail_focus':focus})
    cx,cy=focus
    full=Image.new('RGB',(3*(width+16),height+40),(25,32,42));draw=ImageDraw.Draw(full)
    detail=Image.new('RGB',(1230,510),(25,32,42));dd=ImageDraw.Draw(detail)
    for col,(key,title) in enumerate([('before','Bezier valide'),('soft2','Fondu doux - sigma2'),('soft4','Fondu diffus - sigma4')]):
        im=Image.fromarray(sample[key]);im.save(REVIEW/f'{key}-poster.png')
        bg=Image.new('RGBA',im.size,(110,94,70,255))
        full.paste(Image.alpha_composite(bg,im).convert('RGB'),(col*(width+16)+8,32));draw.text((col*(width+16)+8,8),title,fill='white')
        region=im.crop((cx-24,cy-24,cx+24,cy+24)).resize((384,384),Image.Resampling.NEAREST)
        bg=Image.new('RGBA',region.size,(110,94,70,255))
        detail.paste(Image.alpha_composite(bg,region).convert('RGB'),(col*410+8,35))
        detail.paste(region.getchannel('A').resize((76,76),Image.Resampling.NEAREST).convert('RGB'),(col*410+8,426))
        dd.text((col*410+8,10),title,fill='white');dd.text((col*410+92,442),f'Alpha / phase {sample_id}',fill='white')
    full.save(REVIEW/'full-comparison.png');detail.save(REVIEW/'detail.png')
    metrics={}
    for key,sigma in VARIANTS.items():
        rows=[r['variants'][key] for r in records]
        metrics[key]={'sigma_x4':sigma,'full_filter_within_x4':2*sigma,'core_exact_beyond_x4':4*sigma,
                      'alpha_mass_ratio_range':[min(r['alpha_mass_ratio'] for r in rows),max(r['alpha_mass_ratio'] for r in rows)],
                      'max_absolute_rgb_flux_change_percent':max(abs(r['premultiplied_rgb_flux_ratio']-1)*100 for r in rows),
                      'all_cores_exact':True,'no_new_empty_frames':True,'fade_not_clipped':True}
    assert workflow.sha256_file(installed)==installed_sha
    report={'asset':'SPDEATH3','phases':len(records),'base_bezier_preview_accepted':True,
            'method':'Gaussian edge-only premultiplied RGBA; smooth transition to exact interior',
            'variants':metrics,'extra_preview_padding_x4':PAD,'preview_size_x4':[width,height],
            'profiles':old['profiles'],'native_timing_and_phase_selection_unchanged':True,
            'installed':False,'production_authorities_changed':False,'qa':'new fade awaiting preview review',
            'installed_manifest_unchanged_sha256':installed_sha}
    save(OUT/'summary.json',report)
    save(OUT/'result.json',{'summary':report,'frames':records,'base':ev(BASE/'result.json'),
         'accepted_base':ev(OUT/'accepted-base.json'),'producer':ev(Path(__file__)),
         'formula_reference':ev(REFERENCE),'gallery_template':ev(BASE/'review/index.html'),
         'new_neural_inference':0,'premultiplication':'input already premultiplied; no second multiplication'})
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
