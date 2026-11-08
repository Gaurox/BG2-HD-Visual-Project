"""Source-specific recipe recommendations only; no inference or domain registration."""
import hashlib,json,sys,math
from pathlib import Path
from collections import Counter
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam
OUT=ROOT/'effects/batches/lot50-magic-water-recipes-20261108-v1'
PROPOSAL=ROOT/'effects/batches/lot50-magic-water-proposal-20261108-v1'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
# A historical success is evidence for the starting recipe, not QA of a new source.
profiles={
 'R-SOFT':dict(spatial='ReboutCX x4',alpha='Native alpha nearest4; soft premultiplied RGBA sigma2 x4, canvas edge ramp2 x4, runtime geometry unchanged',history='animations/ressources/AM3000E/runs/am3000e-contour-native-accepted-20261011-v1/manifest.json',fallback='Native alpha, no soft2 if plume energy or fine fringes are lost.'),
 'R-COLUMN':dict(spatial='ReboutCX x4',alpha='Native alpha, inner feather16 x4 on broad column only, premultiply once; keep all detached grains. Native-alpha witness mandatory for transfer of this setting.',history='animations/batches/am6200a-selection-accepted-20260922/manifest.json',fallback='Native-alpha feather0 if16 suppresses thin ends; SeedVR7B/LAB only if actual veins are erased as on AM6200E/F.'),
 'R-PORTAL':dict(spatial='ReboutCX x4',alpha='Native alpha nearest4, feather0; preserve opaque door frame, recess and central spiral',history='pipeline/recipes/portails-deux-correctif-20261010-v1/build_fix.py',fallback='xBR4X, no blend, if frame ornament or spiral changes. No luminous flux conversion on stone.'),
 'S-GLOW':dict(spatial='SeedVR2 7B INT8/LAB x4',model='seedvr2_7b_int8_convrot.safetensors',workflow='pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json',rgb_gauss_sigma_x4=1.2,alpha='Native support nearest4, feather0; apply explicit per-asset black-matte policy after premultiplied temporal composition',history='effects/batches/lot50-accepted-20261108-v1/acceptance.json',fallback='xBR4X if symbols, false texture, hue drift or unstable core are introduced; reduce sigma to0 if grains disappear.'),
 'X-STRUCT':dict(spatial='xBR4X, blend_colors=false, scale4',rgb_gauss_sigma_x4=0,alpha='Native alpha nearest4, feather0, erosion0',history='effects/batches/lot50-xbr-small-20261108-v1/production.json',fallback='Keep xBR; no generative repair of tiny glyphs, spokes, lightning or lattices.'),
 'X-PARTICLE':dict(spatial='xBR4X, blend_colors=false, scale4',rgb_gauss_sigma_x4=0,alpha='Native alpha nearest4, feather0, erosion0; preserve every particle and centre',history='effects/batches/lot50-xbr-small-20261108-v1/production.json',fallback='If temporal merge/splitting occurs, retain native anchors and use alpha interpolation from the same anchor pair; do not add blur or reshape into discs.'),
 'X-WATER':dict(spatial='xBR2x -> Gaussian sigma0.45 at x2 -> nearest2 to x4',alpha='xBR2x twice; feather0 baseline for droplets; no FOUNT1 feather12/aura5 on thin components by default',history='animations/ressources/FOUNT1/runs/fount1-xbr2x-gaussian045-30fps-contour-aura-accepted-20260915/manifest.json',fallback='xBR4X/no RGB blur if spray vanishes. FOUNT1 aura gain0.9/sigma5, feather12 only as separate broad-mass comparison, not automatic transfer.'),
 'X-BODY':dict(spatial='xBR2x -> nearest2 to x4',alpha='Native alpha retained, no threshold on dark corpse or water',history='pipeline/recipes/wtrbody1-xbr-apo8-collapse-20261011-v1/build.py',fallback='Own WTRBODY2 source and cycles; do not copy WTRBODY1 pixels, duplicate holds or 7.5 FPS input setting.'),
 'A-BUBBLE':dict(spatial='Own BUBLES palette: xBR2 blend -> nearest2 to x4; reuse AMOH7300 method and exact matching source geometry',alpha='Reuse matching native masks; xBR alpha as AMOH7300, no feather; premultiply once',history='animations/index/qa-decisions/AMOH7300/2026-10-10-accepted-amoh7300-bulles-xbr2blend-apo8-premul-v1.json',fallback='Do not recolor final green AMOH7300 RGB blindly: source palette contains color collapses; regenerate deterministic RGB from BUBLES palette. No new SeedVR.'),
 'A-BLOB':dict(spatial='Attempt existing accepted TRGOOY spatial anchors; adapt palette/contour/geometry from target source',alpha='Target native alpha nearest4; target centres and rectangles; preserve dark outlines',history='effects/index/processing.csv',fallback='Not a proven byte-equivalent reuse. If adaptation changes source drawing/contour, use target xBR4X+Apollo30; no SeedVR by default. Never substitute final retimed TRGOOY pack.'),
 'N-MASK':dict(spatial='No new spatial or AI job; retain native owner mask',alpha='Preserve native black RGB and graduated alpha/owner role; no flux conversion, feather or erosion',history='projectiles/index/visual-assets.csv',fallback='If another visible non-mask owner is discovered, qualify that owner separately; this decision is not global acceptance of every BAM use.'),
}
assign={}
def add(names,p,reason):
 for n in names.split():
  assert n not in assign,n
  assign[n]=(p,reason)
add('AM3000G','R-SOFT','Grande bouffée claire ; AM3000E donne un précédent ReboutCX avec adoucissement léger et géométrie native restaurée.')
add('AM6200C AM6200D','R-COLUMN','Colonnes vertes de la famille AM6200 : partir du choix ReboutCX validé sur A/B, conserver les extrémités et grains.')
add('SPDIMDR1 SPDIMDR2','R-PORTAL','Cadre matériel et spirale : préserver angles, pierre et décor interne ; ne pas convertir les parties sombres en transparence.')
add('SPRESURI SPCCWOUI SPGENHLB SPHOLMIG','S-GLOW','Masse lumineuse assez large pour SeedVR ; protéger cœur/halo et comparer aux ancres natives.')
add('AMDEMGT HARPDISC SPARMOR2 SPMIRROI SPWIRBLA WHIRL01 WHIRLY HIHEDGE SPBASEWT SPCCOLDE SPCHROMI SPCSPRAI SPENTAXI SPHLYSMT SPHOLYWD SPRWRA2I SPSNRAYI SPUNHBLT RIPPLE_1 RIPPLE_2 RIPPLE_3 WTRDROP1 WEBBOMB WEBC','X-STRUCT','Dessins structurés, fins ou sensibles : préserver anneaux, runes, rayons, pointes, ondes et croisements ; éviter les inventions SeedVR observées au lot précédent.')
add('DUST SNOWFAL1 SNOWFAL2 BUBBLES1 SPLASH','X-PARTICLE','Grains/gouttes minuscules ; fidélité au nombre, à la séparation et au placement avant enrichissement de texture.')
add('FOUNT2 FOUNTN','X-WATER','Reprendre le lissage RGB léger éprouvé sur FOUNT1 sans appliquer son large feather/aura aux gouttelettes.')
add('WTRBODY2','X-BODY','Variante réelle de WTRBODY1, 10 poses propres ; conserver matière sombre et durée propre.')
add('BUBLES','A-BUBBLE','108 matrices indexées/alphas/centres/cycles identiques à AMOH7300 accepté ; seule la palette diffère.')
add('TRBLOBA TRBLOBB','A-BLOB','TRGOOYAA/BB déjà validés spatialement ; réemploi à vérifier avec dessins proches, contours/couleurs/centres/cycles différents.')
add('SHAREAB SPSDIMSP SPSDRABU SPSDRAE2 SPSHADOW TRAVELB','N-MASK','Masques natifs propriétaires déjà classés côté projectiles ; noir et alpha font partie du rendu voulu.')
flux=set('HIHEDGE SPCCOLDE SPCCWOUI SPGENHLB SPHOLMIG SPHOLYWD SPRESURI SPCHROMI SPCSPRAI SPSNRAYI BUBBLES1 RIPPLE_1'.split())
def main():
 assert not OUT.exists(),'Use a new recipe-plan version'
 OUT.mkdir(parents=True)
 authorities=[ROOT/'effects/index/processing.csv',ROOT/'projectiles/index/work-tracking.json',ROOT/'animations/index/animation_upscale_registry.csv']
 before={str(p.relative_to(ROOT)):sha(p) for p in authorities}
 proposal=load(PROPOSAL/'batch.json');conclusions=load(ROOT/'effects/research/next50-reuse-audit-20261108-v1/conclusions.json');by={r['resref']:r for r in conclusions['assets']}
 assets=[]
 for a in proposal['assets']:
  n=a['resref'];profile,reason=assign[n];source=ROOT/a['source'];assert sha(source)==a['source_sha256']
  raw=read_bam(source);frames,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr)
  used=sorted({i for c in a['native_cycles'] for i in c['frame_indices']});keys=[]
  for idx,cx,cy,_ in frames:
   rgba=np.dstack((pal[idx],alpha[idx]));rgba[rgba[:,:,3]==0]=0
   keys.append(hashlib.sha256(rgba.tobytes()+str((rgba.shape,cx,cy)).encode()).hexdigest())
  cycles=[]
  rate=int(a['native_fps'].split(';')[0]) if a['native_fps'] else 15
  for c in a['native_cycles']:
   ids=c['frame_indices'];cycles.append(dict(cycle=c['cycle'],native_slots=len(ids),phases30=math.ceil(len(ids)*30/rate),duration_seconds=len(ids)/rate,constant=bool(ids) and len({keys[i] for i in ids})==1,empty=not ids,repeated_slots=len(ids)-len({keys[i] for i in ids})))
  matte='Native alpha and RGB darkness preserved; no generic black key or luminance cutoff.'
  if n in flux:matte='Light-only black-matte candidate: keep native-alpha witness; proposed normal preview A=max(P.r,P.g,P.b), P=round(A_native*C/255), straight RGB=round(255*P/A). Keep P exact, roundtrip<=1. Apply only to luminous layer; unknown owner blend is not established by this proposal.'
  if profile=='N-MASK':matte='Black mask is meaningful: native owner rendering preserved; no A=max(RGB), no black removal.'
  green=None
  if n=='WHIRLY':
   green=dict(palette_indices=np.flatnonzero(np.all(pal==[0,255,0],axis=1)).tolist(),policy='Working export only: remove exact indexed green connected to source-frame border before xBR; never hue-threshold foreground. Preserve canonical BAM and native-alpha witness.',reference='pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/spatial_one.py',status='proposed-derivation-not-yet-reviewed')
  extra=[]
  if n=='AMDEMGT':extra.append('SP_DEMGT is a source alias: one spatial production, separate resource binding; no second inference.')
  if profile=='A-BLOB':extra.append('Parent spatial '+('TRGOOYAA' if n=='TRBLOBA' else 'TRGOOYBB')+' SeedVR7B x4 accepted; rebuild temporal from target source cycles, never copy parent timing.')
  if n in {'WTRBODY2','RIPPLE_2','RIPPLE_3'}:extra.append('Dark source is not evidence of a disposable matte; do not use global flux-alpha conversion.')
  assets.append(dict(ordinal=a['ordinal'],resref=n,profile=profile,reason=reason,source=a['source'],source_sha256=a['source_sha256'],reuse_decision=by[n]['decision'],canvas_x1=a['native_canvas'],alpha_levels=len(a['normal_palette_alpha_levels']),recipe=profiles[profile],black_policy=matte,green_derivation=green,cycles=cycles,used_records=used,temporal=dict(target_fps=30,model='apo-8' if profile!='N-MASK' else None,input_fps=rate,rate_basis='indexed consumer' if a['native_fps'] else '15 FPS compatibility assumption; runtime rate not measured',status='retain-native-no-new-job' if profile=='N-MASK' else 'planned',preserve_native_holds=True,closed_loop='Only loop profile interpolates last-to-first; separate once profile when owner unresolved',constant_cycle='Store one image, preserve native duration; no hallucinated motion',empty_cycle='Preserve source carrier entry, no inference or playable profile',tiny_frame='Temporary Apollo padding min128/multiple32, exact crop; world origin unchanged'),extra=extra))
 assert len(assets)==50 and set(assign)=={a['resref'] for a in assets}
 assert sum(a['profile']=='N-MASK' for a in assets)==6
 for p in authorities:assert sha(p)==before[str(p.relative_to(ROOT))]
 data=dict(schema='bg2-effects-recipe-plan-v1',date='2026-11-08',status='recommendations-not-produced-not-QA',summary=dict(Counter(a['profile'] for a in assets)),global_contract=dict(scale=4,target_fps=30,alpha_runtime='premultiplied exactly once; transparent RGB nearest-opaque filled only for model input; runtime zero under alpha0',geometry='Native per-frame centres, logical rectangles and alternative cycles preserved; padding temporary only',timing='Keep native slot lookup and pauses; source dedup never redistributes duration. Apollo anchor pairs sampled onto original slot-time axis; constant and transparent phases handled explicitly.',confidence='Historical recipe transfer plus source inspection, not validation of new pixels',source_fps='Most sources lack owner evidence:15 FPS compatibility assumption, not measured ingame',native_masks='6 retain native timing; no claim of new interpolation30',scope='No model execution, installation, QA acceptance, domain-index or release update'),assets=assets,unchanged_authorities=before)
 save(OUT/'recipes.json',data)
 lines=['# Formules du lot magie/eau — 2026-11-08','','Plan complet : `recipes.json` ; recommandations, aucune production/QA acquise.','', '**Répartition : 4 SeedVR7B, 5 ReboutCX, 32 recettes xBR propres, 1 adaptation de palette xBR, 2 réemplois spatiaux à vérifier, 6 masques natifs.**','','## Contrat commun','','- x4 ; Apollo apo-8 vers30 FPS sur les productions animées nouvelles. 15 FPS entrée = hypothèse de compatibilité si propriétaire inconnu, pas mesure runtime. Les6masques restent natifs.','- Cycles séparés, ancres/centres/rectangles/pauses conservés. Dédupliquer pour le calcul sans redistribuer les slots ; boucle fermée et once distincts si rôle inconnu. Cycle constant : image unique durée conservée ; cycle vide : carrier seul.','- Alpha natif conservé hors dérivations listées ; prémultiplication unique. Aucun retrait/feather global. Noir sombre de WTRBODY2/RIPPLE2/3 et masques conservé.','- Alpha lumineux candidat : P=round(A_native*C/255), A_flux=max(P), C_droit=round(255*P/A_flux), zéro siA=0. P conservé, reconstruction erreur≤1. Témoin natif ; ne vaut pas preuve du blend propriétaire.','- WHIRLY : vert indexé exact connecté au bord retiré dans copie de travail, avant spatial ; source immuable.','- Réemplois TRBLOBA/BB non démontrés comme interchangeables ; adaptation testée avant nouveau spatial, repli xBR si nécessaire. BUBLES exige ses RGB propres, pas une copie des bulles vertes.','','## Profils','','| ID | Spatial | Alpha | Référence et repli |','|---|---|---|---|']
 for p,r in profiles.items():lines.append(f"| {p} | {r['spatial']} | {r['alpha']} | `{r['history']}` ; {r['fallback']} |")
 lines+=['','## Affectation exhaustive','','| # | Effet | Formule | Noir / particularité | Phases à30 par cycle non vide* |','|---|---|---|---|---|']
 for a in assets:
  n=a['resref'];black='Masque noir natif' if a['profile']=='N-MASK' else 'Variante alpha de flux + témoin natif' if n in flux else 'Alpha natif, matière sombre préservée'
  if a['green_derivation']:black='Détourage du vert indexé de bord, puis alpha natif'
  if a['extra']:black+=' ; '+' '.join(a['extra'])
  counts='natif' if a['profile']=='N-MASK' else '/'.join(str(c['phases30']) for c in a['cycles'] if not c['empty'])
  lines.append(f"| {a['ordinal']:02d} | {n} | {a['profile']} | {black} | {counts} |")
 lines+=['','*Prévision au taux source retenu ; cycles constants peuvent réutiliser une seule image. Phases de playback ≠ fichiers distincts.','', 'Les précédents établissent un point de départ. Les paramètres transférés (soft2, feather16, flux-alpha, vert) doivent être jugés sur la nouvelle sortie, sans déduire une acceptation ingame.']
 (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps(data['summary'],ensure_ascii=False))
if __name__=='__main__':main()
