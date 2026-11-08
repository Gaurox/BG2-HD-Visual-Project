"""Annotate native source board with planned formulas, without changing source proposal."""
import json,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'effects/batches/lot50-magic-water-recipes-20261108-v1'
plan=json.loads((OUT/'recipes.json').read_text(encoding='utf-8'))
by={a['resref']:a for a in plan['assets']}
board=ROOT/'effects/batches/lot50-magic-water-proposal-20261108-v1/review'
catalog=json.loads((board/'catalog.json').read_text(encoding='utf-8'))
for a in catalog['assets']:
 r=by[a['resref']];a['image']='../../'+a['image']
 a['review_decision']=r['profile']+' · '+r['recipe']['spatial']
 a['review_note']=r['reason']+' Alpha : '+r['recipe']['alpha']+'. '+r['black_policy']
 if r['green_derivation']:a['review_note']+=' WHIRLY : retirer le vert indexé connecté au bord dans la copie de travail avant xBR.'
 a['review_note']+=' · '+('Conserver natif, pas de nouvelle interpolation.' if r['profile']=='N-MASK' else 'Apollo apo-8 →30 FPS ; '+r['temporal']['rate_basis'])
template=(ROOT/'pipeline/recipes/effects-next50-magic-water-proposal-20261108-v1/board.html').read_text(encoding='utf-8')
template=template.replace('50 productions distinctes / 51 RESREF avec l’alias SP_DEMGT.','Formules prévues : 4 SeedVR7B · 5 ReboutCX · 32 xBR · 1 palette xBR · 2 réemplois à vérifier · 6 natifs sans IA. 51 RESREF avec SP_DEMGT.')
template=template.replace('À traiter · source native, sans upscale','${a.review_decision}<br>${a.review_note}')
template=template.replace("c.a.resref+' '+c.a.group","c.a.resref+' '+c.a.group+' '+c.a.review_decision")
page=template.replace('__CATALOG__',json.dumps(catalog,ensure_ascii=False))
rev=board/'revisions/recipe-plan-20261108-v1';rev.mkdir(parents=True,exist_ok=False)
(rev/'index.html').write_text(page,encoding='utf-8')
assert len(catalog['assets'])==50 and all((rev/a['image']).is_file() for a in catalog['assets'])
tmp=ROOT/'.tmp/effects-next50-reuse-20261108/recipe-board.js';tmp.write_text(re.search(r'<script>(.*?)</script>',page,re.S)[1],encoding='utf-8')
subprocess.run(['node','--check',str(tmp)],check=True)
for a in plan['assets']:
 assert (ROOT/a['source']).is_file()
 assert (ROOT/a['recipe']['history']).is_file(),a['recipe']['history']
(board/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=revisions/recipe-plan-20261108-v1/index.html"><a href="revisions/recipe-plan-20261108-v1/index.html">Planche avec formules prévues</a>',encoding='utf-8')
for file in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
 s=file.read_text(encoding='utf-8-sig');i=s.index('\n')+1
 note='\n**Formules prochain lot50 — 2026-11-08** : [affectations et paramètres](batches/lot50-magic-water-recipes-20261108-v1/README.md), `recipes.json`, [planche annotée](http://127.0.0.1:8798/). 4SeedVR7B/LAB,5ReboutCX,32xBR propres,1palette xBR,2réemplois spatiaux à vérifier,6masques natifs. Apollo30 prévu hors6natifs ; source15FPS souvent hypothèse de compatibilité. WHIRLY vert indexé ; variantes de flux lumineuses avec témoin natif ; aucune production/installation/QA lancée.\n\n'
 file.write_text(s[:i]+note+s[i:].lstrip('\n'),encoding='utf-8')
print('50 recipes; source/history references valid; 50 board images; JS syntax OK; no domain authority writes.')
