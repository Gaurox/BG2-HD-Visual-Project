"""Read-only source analysis + proposed recipes; does not run inference or register work."""
import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from bam_export import decode_bam, native_palette_alpha
from export_bam_frames import read_bam, cycle_metadata

OUT = ROOT / 'effects/research/lot50-recipe-analysis-20261108-v1'
PROPOSAL = ROOT / 'effects/batches/lot50-fire-smoke-proposal-20261028-v1'

# Selection is visual/morphological judgement, not a classifier or a QA decision.
CHOICES = '''
FIM1YEL|F|SPBRNHND|Petite flamme, protéger pointes et scintillement.
FIM2YEL|F|SPBRNHND|Flamme jaune-verte compacte, même précaution sur les bords.
FIRE_1B|T|SPBURN|Flamme avec traîne sombre ; garder le brun de fumée en alpha normal.
FIRE_1C|T|SPBURN|Flamme étroite avec traîne ; pas de fondu interne large.
FIRE_1GR|H|SPSCHGI|Flamme verte sur matte sombre rectangulaire ; compagnon normal neutre conditionnel.
FIRE_1GS|H|SPSCHGI|Flamme et halo sur matte noire ; ne pas mélanger la matte avec le décor en normal.
FIRE_2|H|SPENTACI|Boule verte texturée et halo sombre ; conserver énergie lumineuse.
FIRE_2A|H|SPENTACI|Variante verte brillante ; palette indépendante, même géométrie à conserver.
FIRE_4BL|F|SPBRNHND|Petite flamme cyan, faible épaisseur ; aucun feather12.
FIRE_4G2|H|SPSCHGI|Petite flamme verte, majorité sombre ; RGB sans gauss sur ce petit motif.
FIRE_4GR|F|SPBRNHND|Petite flamme verte-jaune ; préserver franges et variations de teinte.
FISM1YEL|F|SPBRNHND|Très petite flamme, le flou peut la faire disparaître.
FLLGBLU|F|SPBRNHND|Flamme orange malgré le nom ; se baser sur la palette réellement extraite.
FLLGBLUE|G|SPBRNHND|Fond vert opaque index47 ; essai de masque indexé exact avant toute inférence.
FLLGRED|T|SPBURN|Flamme orange plus large ; préserver les petits fragments détachés.
FLM1PUR|F|SPBRNHND|Flamme violette minuscule, garder la silhouette et la couleur.
FLM1RED|F|SPBRNHND|Petite flamme orange ; traitement sans flou additionnel.
FLM2RED|F|SPBRNHND|Flamme compacte ; conserver détail et variations de taille.
FLMDBLU|G|SPBRNHND|Fond vert opaque index39, plus de90% du support ; ne pas envoyer ce fond au modèle.
FLML|F|SPBRNHND|Flamme très étroite, six poses ; protéger la structure verticale.
FLSM1PUR|G|SPBRNHND|Fond vert opaque index245 ; masque dérivé conditionnel, source conservée.
FLSM1RED|F|SPBRNHND|Flamme minuscule, priorité à la couverture des pixels lumineux.
LAVAFIR1|H|SPENTACI|Lave et pointes sur grande matte noire ; pas de détourage par seuil de luminance.
EXPLODE|T|SPBOOM|Explosion dense avec grains périphériques ; feather0 initial pour garder ces grains.
SPBDBUR|F|SPBRNHND|Petit impact vert clair ; pas de retrait ni feather large.
SPBDBURS|H|SPRDRABU|Neuf directions et réserves vides ; corriger le temps avant de juger la texture.
SPBURNS1|T|SPBURN|Trois cycles de feu ; préserver alternatives et couleurs, pas de concaténation.
SPFBSMAL|P|SPSPARKS|Petit jet de particules blanches ; ne pas fusionner les grains.
SPFINODI|H|SPENTACI|Éclat rose avec cœur, trait vertical et halo ; ne pas vectoriser le halo.
SPFIRE|P|SPSMPUFF|Petites bouffées espacées ; conserver séparation et placement.
SPFIRET|H|SPSCHGI|Petite boule lumineuse à bord sombre ; pas de feather supplémentaire sur le halo.
SPFLADOW|T|SPBRNHND|Grande colonne de feu, dents et particules à conserver.
SPFLSTRI|T|SPBRNHND|Colonne similaire mais BAM distinct ; aucun réemploi déduit de la seule ressemblance.
SPFSTRMI|H|SPENTACI|Feu diffus sur fond noir et dernière pose noire ; préserver la fin d'extinction.
SPPFIRAI|H|SPENTACI|Masse de feu avec bord noir ; vérifier séparément les trois cycles.
SPPFIRXI|H|SPENTACI|Grande colonne vive, régions sombres et langues fines ; ne pas éroder.
SPRDRAEX|D|SPRDRASI|Explosion feu-fumée diffuse ; feather12 plafonné par épaisseur pour garder les franges.
SPMETSWN|P|SPMETSWM|Météores et nombreuses particules ; centres/trajectoires natifs, jamais de fusion.
DSTDVL2A|D|STNKCLDD|Nuage de poussière large ;17poses visibles puis90slots transparents, ne pas étirer le mouvement sur107slots.
FALLMIST|S|SPSMPUFF|Petit nuage de31px ; feather2x4 de départ, pas12.
STEAM1|D|SPHORPUF|Grande vapeur avec zones noires ; conserver la fumée sombre, pas de neutralisation globale.
STEAM4|D|SPHORPUF|Vapeur large, même protection des creux et teintes sombres.
SPSMOLD|S|SPSMKJET|Fumée de9px de large ; feather0, chaque pose tenue trois slots.
SPSTINK|S|SPSMPUFF|Petites volutes séparées ; feather2x4 plafonné, ne pas remplir les trous.
SPAGSCHO|P|SPSPARKS|Traînée blanche granuleuse ; masque fin sans feather12 ni vectorisation globale.
SPGREACI|H|SPENTACI|Nappe violette avec halo ; conserver la structure interne, ne pas tracer le halo en Bézier.
ACIDDTH|H|SPSCHGI|Petite flamme verte sur noir ; seuls21des63records sont utilisés par les deux cycles.
LAVABUB1|P|SPSPARKS|Quelques gouttes orange sur grand canevas ; pas de crop qui déplace les centres.
LAVABUB2|P|SPSPARKS|Gouttes minuscules puis huit poses noires ; préserver cette pause.
SPOUTA|H|SPRDRABU|Trois phases d'éruption et pauses décalées ; garder la position temporelle des apparitions.
'''.strip()

PROFILES = {
 'F': dict(name='Flammes fines', spatial='SeedVR2 7B INT8 / LAB x4', rgb_gauss_sigma_x4=0,
           inner_feather_x4=0, mask='alpha natif nearest4, interpolation alpha selon ancres temporelles',
           alternative='Contour continu0.60 seulement si marches visibles ; adaptation à comparer, pas encore validée sur ces flammes.'),
 'T': dict(name='Feu texturé', spatial='SeedVR2 7B INT8 / LAB x4', rgb_gauss_sigma_x4=1.2,
           inner_feather_x4=0, mask='alpha natif nearest4 ; particules natives protégées',
           alternative='Réduire gauss à0 si disparition de grains ; contour continu local si silhouette crénelée.'),
 'H': dict(name='Énergie / halo', spatial='SeedVR2 7B INT8 / LAB x4', rgb_gauss_sigma_x4=1.2,
           inner_feather_x4=0, mask='support natif ; dégradé lumineux conservé dans RGB',
           normal_variant='Si propriétaire lumineux établi : alpha de flux A2=round(A*max(RGB)/255), RGB droit reconstruit ; vérifier énergie prémultipliée erreur<=1. Sinon témoin alpha natif conservé.',
           alternative='Jamais de clé noire globale ni Bézier du halo ; conversion de flux en alpha est une variante conditionnelle.'),
 'D': dict(name='Grand diffus', spatial='SeedVR2 7B INT8 / LAB x4', rgb_gauss_sigma_x4=1.2,
           inner_feather_x4=12, mask='alpha natif, feather interne12 limité localement aux grosses masses',
           alternative='Témoin feather0 et couverture des petites composantes ; plafonnement local = adaptation à comparer.'),
 'S': dict(name='Fumée fine', spatial='SeedVR2 7B INT8 / LAB x4', rgb_gauss_sigma_x4=0,
           inner_feather_x4=2, mask='fondu2x4 de départ, borné par épaisseur ; pas de retrait',
           alternative='Paramètre2 adapté, pas une recette déjà acceptée ; témoin0. SPSMOLD impose0.'),
 'P': dict(name='Particules / gouttes', spatial='SeedVR2 7B INT8 / LAB x4', rgb_gauss_sigma_x4=0,
           inner_feather_x4=0, mask='alpha natif nearest4 ; chaque composante/centre conservé',
           alternative='Essai continu0.60 hérité des nuées seulement si escalier gênant ; évaluer grains et masse alpha, pas de disques ni micro-flou.'),
 'G': dict(name='Fond vert à résoudre', spatial='Préparer une dérivation source ; ensuite profilF SeedVR7B x4', rgb_gauss_sigma_x4=0,
           inner_feather_x4=0, mask='hypothèse : seul index vert exact connecté au bord devient transparent dans une copie de travail',
           alternative='Conserver source et témoin inchangés. Hypothèse non validée par usage/blend natif ; ne pas lancer directement sur le rectangle vert.'),
}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    proposal = json.loads((PROPOSAL/'batch.json').read_text(encoding='utf-8'))
    audit = {a['resref']:a for a in json.loads((PROPOSAL/'native-duplicate-audit.json').read_text())['assets']}
    state = {r['asset_key']:r for r in csv.DictReader((ROOT/'effects/index/processing.csv').open(encoding='utf-8-sig',newline=''))}
    choices = {line.split('|')[0]:line.split('|')[1:] for line in CHOICES.splitlines()}
    assets=[];green_tiles=[]
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    for a in proposal['assets']:
        name=a['resref'];profile,analog,reason=choices[name]
        path=ROOT/a['source'];raw=read_bam(path)
        assert hashlib.sha256(path.read_bytes()).hexdigest().upper()==a['source_sha256']
        frames,palette,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr)
        assert cycle_metadata(raw,len(frames))==a['native_cycles']
        assert state[a['asset_key']]['spatial_state']=='not-started' and not state[a['asset_key']]['selected_run']
        covered=black=green=graded=tiny=0; blanks=[];keys=[];used=set();transparent_frames=[]
        green_ids=np.flatnonzero((palette[:,0]==0)&(palette[:,1]==255)&(palette[:,2]==0)).tolist()
        for i,(idx,cx,cy,_) in enumerate(frames):
            mask=alpha[idx]>0;rgb=palette[idx][mask].astype(int);n=len(rgb);covered+=n
            black+=int((rgb.max(1)<=8).sum()) if n else 0
            green+=int(((rgb[:,0]==0)&(rgb[:,1]==255)&(rgb[:,2]==0)).sum()) if n else 0
            graded+=int(((alpha[idx]>0)&(alpha[idx]<255)).sum())
            if not n:transparent_frames.append(i)
            if not n or not rgb.max():blanks.append(i)
            labels,count=ndi.label(mask,np.ones((3,3)));sizes=np.bincount(labels.ravel())[1:]
            tiny+=int(sizes[sizes<=4].sum())
            rgba=np.dstack((palette[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
            # Identity includes centre and shape; the original anchored audit remains authoritative.
            keys.append(hashlib.sha256(rgba.tobytes()+str((rgba.shape,cx,cy)).encode()).hexdigest())
        cycles=[]
        for cy in a['native_cycles']:
            ids=cy['frame_indices'];used.update(ids)
            empty=[i for i,k in enumerate(ids) if k in blanks]
            cycles.append(dict(cycle=cy['cycle'],slots=len(ids),black_or_transparent_slots=empty,
                               fully_transparent_slots=[i for i,k in enumerate(ids) if k in transparent_frames],
                               adjacent_equal_pairs=[i for i in range(1,len(ids)) if keys[ids[i]]==keys[ids[i-1]]],
                               returns_after_intervening_pose=any(keys[k] in [keys[v] for v in ids[:max(0,i-1)]] and keys[k]!=keys[ids[i-1]] for i,k in enumerate(ids) if i>1)))
        settings=dict(PROFILES[profile])
        if name in {'FIRE_4G2','SPFIRET','ACIDDTH'}:settings['rgb_gauss_sigma_x4']=0
        if name=='SPSMOLD':settings['inner_feather_x4']=0
        temporal_special=any(c['black_or_transparent_slots'] or c['adjacent_equal_pairs'] or c['returns_after_intervening_pose'] for c in cycles)
        notes=[]
        if temporal_special:notes.append('Ancres15->30, poses vides/holds à leur place ; pas de redistribution uniforme des poses distinctes.')
        if any(not c['slots'] for c in cycles):notes.append('Cycles vides conservés dans carrier, exclus de l’inférence et des profils animés.')
        if len(used)<len(frames):notes.append(f'{len(frames)-len(used)} records non référencés : préserver source/carrier, ne pas inventer de cycle.')
        if a['native_canvas'][0]*4<128 or a['native_canvas'][1]*4<128:notes.append('Apollo : padding temporaire min128 et multiple32, recadrage exact ; aucun déplacement monde.')
        assets.append(dict(ordinal=a['ordinal'],resref=name,profile=profile,recipe=settings,reason=reason,
                           nearest_historical_analogue=analog,confidence='analogie historique ; nouvelle QA nécessaire',
                           source=a['source'],source_sha256=a['source_sha256'],canvas_x1=a['native_canvas'],source_records=len(frames),
                           used_records=len(used),unreferenced_records=sorted(set(range(len(frames)))-used),
                           native_cycles=cycles,normal_graded_pixels=graded,opaque_nearblack_percent=round(100*black/max(covered,1),3),
                           opaque_exact_green_percent=round(100*green/max(covered,1),3),green_palette_indices=green_ids,
                           tiny_component_pixel_percent=round(100*tiny/max(covered,1),3),
                           repeated_slots_anchored=sum(c['repeated_slots'] for c in audit[name]['cycles']),
                           temporal_special=temporal_special,notes=notes))
        if profile=='G':
            tile=Image.new('RGB',(750,220),(35,40,49));d=ImageDraw.Draw(tile)
            d.text((10,5),f'{name}: natif / hypothese index vert de bord (non validee)',font=font,fill='white')
            for j,k in enumerate([0,len(frames)//2,len(frames)-1]):
                idx=frames[k][0];rgba=np.dstack((palette[idx],alpha[idx]));candidate=rgba.copy()
                gm=np.isin(idx,[i for i in green_ids if i!=tr]);labs,n=ndi.label(gm)
                boundary=set(np.concatenate((labs[0],labs[-1],labs[:,0],labs[:,-1])).tolist())-{0}
                candidate[np.isin(labs,list(boundary))]=0
                for col,array in enumerate([rgba,candidate]):
                    im=Image.fromarray(array);im.thumbnail((100,160),Image.Resampling.NEAREST)
                    im=im.resize((im.width*min(3,100//max(1,im.width)),im.height*min(3,100//max(1,im.width))),Image.Resampling.NEAREST)
                    tile.paste(im,(j*250+col*120+10,45),im)
            green_tiles.append(tile)
    report=dict(date='2026-11-08',status='analysis-only-no-inference',proposal=str(PROPOSAL.relative_to(ROOT)),
                profile_counts=dict(Counter(a['profile'] for a in assets)),profiles=PROFILES,assets=assets,
                temporal_policy='Apollo apo-8 30FPS, independent native cycles and once/loop profiles;15FPS compatibility only; preserve every native anchor/hold/blank and nonadjacent returns. Decode/storage deduplication must not redistribute timeline.',
                integration_policy='Native source/palette/centres/cycles/carrier preserved. Straight/premultiplied variants explicit. Owner/tint/blend/cadence unresolved; no installation/release/QA inferred.')
    (OUT/'analysis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    columns=['ordinal','resref','profile','reason','nearest_historical_analogue','canvas_x1','source_records','used_records','opaque_nearblack_percent','opaque_exact_green_percent','temporal_special']
    with (OUT/'recipes.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=columns,extrasaction='ignore');w.writeheader();w.writerows(assets)
    sheet=Image.new('RGB',(750,220*len(green_tiles)))
    for i,im in enumerate(green_tiles):sheet.paste(im,(0,i*220))
    sheet.save(OUT/'green-mask-hypotheses.png')
    print(json.dumps(dict(counts=report['profile_counts'],temporal_special=[a['resref'] for a in assets if a['temporal_special']],all_native_alpha_binary=all(not a['normal_graded_pixels'] for a in assets)),ensure_ascii=False))

if __name__=='__main__':main()
