"""User correction: SeedVR is default; xBR only for tiny grains, preserve reuse/native decisions."""
from pathlib import Path
from collections import Counter
import json,copy,hashlib,re,subprocess
ROOT=Path(__file__).resolve().parents[3]
OLD=ROOT/'effects/batches/lot50-magic-water-recipes-20261108-v1'
OUT=ROOT/'effects/batches/lot50-magic-water-recipes-20261108-v2'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest().upper()
def main():
 assert not OUT.exists(),'Use new version'
 OUT.mkdir()
 data=copy.deepcopy(load(OLD/'recipes.json'))
 before={p:sha(ROOT/p) for p in data['unchanged_authorities']}
 tiny=set('BUBBLES1 SPCSPRAI DUST SNOWFAL1 SNOWFAL2 SPLASH'.split())
 for a in data['assets']:
  n=a['resref'];old=copy.deepcopy(a['recipe']);a['previous_recommendation']=dict(profile=a['profile'],recipe=old,reason=a['reason'])
  if a['profile'] in {'N-MASK','A-BLOB','A-BUBBLE'}:continue
  if n in tiny:
   a['profile']='X-TINY';a['reason']='Très petits grains, flocons, points lumineux ou gouttes : conserver séparation et silhouette ; exception xBR à la priorité SeedVR demandée.'
   a['recipe']=dict(spatial='xBR4X, blend_colors=false, scale4',rgb_gauss_sigma_x4=0,alpha='Native alpha nearest4; feather0, erosion0; protect each particle',history='effects/batches/lot50-xbr-small-20261108-v1/production.json',fallback='SeedVR comparison only if xBR result is insufficient; no automatic blur or merging of grains.')
  else:
   soft=n in {'AM3000G','SPRESURI','SPCCWOUI','SPGENHLB','SPHOLMIG'}
   a['profile']='S-SOFT' if soft else 'S-DETAIL'
   a['reason']='SeedVR prioritaire selon correction utilisateur ; '+('masse diffuse/lumineuse, lissage RGB léger.' if soft else 'détail RGB SeedVR sans flou ajouté ; préserver dessin, palette et géométrie natives.')
   a['recipe']=dict(spatial='SeedVR2 7B INT8/LAB x4',model='seedvr2_7b_int8_convrot.safetensors',workflow='pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json',rgb_gauss_sigma_x4=1.2 if soft else 0,alpha='Native alpha nearest4, feather0 and erosion0 baseline; retain per-asset matte and green derivations; premultiply once',history='effects/batches/lot50-accepted-20261108-v1/acceptance.json',fallback='Inspect new SeedVR anchors first. Earlier recipe is a fallback/comparison only, never automatic xBR substitution: '+old['spatial'])
   if n in {'AM6200C','AM6200D'}:a['extra'].append('ReboutCX/inner16 precedent AM6200A/B retained as comparison only; main source is SeedVR, feather0 baseline.')
   if n=='WTRBODY2':a['extra'].append('User priority SeedVR overrides previous xBR recommendation. WTRBODY1 xBR2->nearest2 remains fallback; own dark corpse/water and native10-slot timing preserved.')
   if a['green_derivation']:a['green_derivation']['policy']=a['green_derivation']['policy'].replace('before xBR','before SeedVR');a['green_derivation']['policy']+=' Fill transparent input RGB without green spill; restore derived native mask after inference.'
 data['summary']=dict(Counter(a['profile'] for a in data['assets']))
 data['supersedes']='effects/batches/lot50-magic-water-recipes-20261108-v1/recipes.json'
 data['user_direction']='Most effects must use SeedVR; xBR reserved for very small elements such as bubbles. No new treatment execution requested in this correction.'
 data['unchanged_authorities']=before
 data['global_contract']['spatial_priority']='SeedVR7B INT8/LAB x4 default for35 new sources; xBR only6 tiny sources plus BUBLES palette adaptation;2 spatial reuse attempts;6 native masks.'
 assert sum(a['profile'].startswith('S-') for a in data['assets'])==35
 assert {a['resref'] for a in data['assets'] if a['profile']=='X-TINY'}==tiny
 for p,h in before.items():assert sha(ROOT/p)==h
 (OUT/'recipes.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 lines=['# Lot50 — priorité SeedVR — v2, 2026-11-08','','Correction explicite utilisateur ; remplace le plan v1. Aucune inférence ou installation lancée.','','- **35 SeedVR2 7B INT8/LAB x4** :30 sans flou RGB ajouté,5diffus avec sigma1.2 x4.','- **6 xBR minuscules** : BUBBLES1, SPCSPRAI, DUST, SNOWFAL1, SNOWFAL2, SPLASH.','- **1 adaptation BUBLES** : xBR2blend→nearest2, palette propre, recette AMOH7300.','- **2 réemplois TRBLOBA/BB** : parents TRGOOYAA/BB SeedVR déjà validés ; adaptation spatiale à vérifier, cycles propres. Si impossible : nouveau SeedVR7B/LAB, pas xBR automatique.','- **6 masques natifs** : SHAREAB, SPSDIMSP, SPSDRABU, SPSDRAE2, SPSHADOW, TRAVELB ; aucun job IA.','','Contrat : Apollo apo-8→30FPS hors6natifs, durées/pauses/centres/cycles conservés ; 15FPS source par défaut de compatibilité si propriétaire inconnu. Alpha natif nearest4, feather0/érosion0 de départ ; variantes de flux lumineuses avec témoin natif. WHIRLY : vert indexé de bord retiré dans copie de travail avant SeedVR ; pas de vert injecté au modèle. WTRBODY2 : matière sombre conservée. ReboutCX/xBR antérieurement proposés deviennent des replis comparatifs, sans substitution automatique.','','| # | Effet | Formule principale | Particularité |','|---|---|---|---|']
 for a in data['assets']:
  if a['profile']=='A-BLOB':
   a['recipe']['fallback']='If spatial adaptation cannot preserve target drawing, produce own SeedVR7B INT8/LAB x4, sigma0, native alpha nearest4, then Apollo30 on target cycles. Do not copy parent retimed pack.'
  extra=' ; '.join(a['extra'])
  if a['green_derivation']:extra+=' ; masque vert indexé dérivé avant SeedVR'
  lines.append(f"| {a['ordinal']:02d} | {a['resref']} | {a['profile']} · {a['recipe']['spatial']} | {extra} |")
 # Save final corrected fallback as well.
 (OUT/'recipes.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 board=ROOT/'effects/batches/lot50-magic-water-proposal-20261108-v1/review'
 catalog=load(board/'catalog.json');by={a['resref']:a for a in data['assets']}
 for a in catalog['assets']:
  r=by[a['resref']];a['image']='../../'+a['image'];a['formula']=r['profile']+' · '+r['recipe']['spatial'];a['note']=r['reason']+' '+r['recipe']['alpha']+' '+r['black_policy']
  if r['green_derivation']:a['note']+=' Vert indexé connecté au bord retiré avant SeedVR, source conservée.'
 t=(ROOT/'pipeline/recipes/effects-next50-magic-water-proposal-20261108-v1/board.html').read_text(encoding='utf-8')
 t=t.replace('50 productions distinctes / 51 RESREF avec l’alias SP_DEMGT.','Plan v2 : 35 SeedVR · 6 xBR minuscules · 1 palette xBR · 2 réemplois SeedVR · 6 natifs sans IA.')
 t=t.replace('À traiter · source native, sans upscale','${a.formula}<br>${a.note}')
 t=t.replace("c.a.resref+' '+c.a.group","c.a.resref+' '+c.a.group+' '+c.a.formula")
 page=t.replace('__CATALOG__',json.dumps(catalog,ensure_ascii=False));rev=board/'revisions/recipe-plan-20261108-v2';rev.mkdir(parents=True)
 (rev/'index.html').write_text(page,encoding='utf-8')
 assert len(catalog['assets'])==50 and all((rev/a['image']).is_file() for a in catalog['assets'])
 js=ROOT/'.tmp/effects-next50-reuse-20261108/recipe-v2.js';js.write_text(re.search(r'<script>(.*?)</script>',page,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 (board/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=revisions/recipe-plan-20261108-v2/index.html"><a href="revisions/recipe-plan-20261108-v2/index.html">Plan SeedVR v2</a>',encoding='utf-8')
 for file in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
  s=file.read_text(encoding='utf-8-sig');i=s.index('\n')+1
  note='\n**Plan courant v2 — priorité SeedVR, correction utilisateur2026-11-08** : [formules50](batches/lot50-magic-water-recipes-20261108-v2/README.md), [planche](http://127.0.0.1:8798/).35SeedVR7B/LAB,6xBR minuscules,1palette BUBLES xBR,2réemplois spatiaux SeedVR,6masques natifs ; Apollo30 prévu horsnatifs. Remplace la répartition trop prudente du planv1. Aucune nouvelle inférence/installation/QA.\n\n'
  file.write_text(s[:i]+note+s[i:].lstrip('\n'),encoding='utf-8')
 print(json.dumps(data['summary']));print('50 annotated cards; images and JS valid; domain authorities unchanged.')
if __name__=='__main__':main()
