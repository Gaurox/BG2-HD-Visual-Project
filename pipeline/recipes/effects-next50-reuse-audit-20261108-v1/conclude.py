"""Supplement exact-source audit with owner roles, palette variants and related families."""
import importlib.util
from collections import Counter
from pathlib import Path

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('audit',HERE/'audit.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
root=m.ROOT;out=m.OUT
a=m.load(out/'audit.json')
snapshot=m.load(root/'projectiles/index/work-analysis-current.json')
contexts=m.load(root/snapshot['snapshot']/'contexts.json')
native=set('SHAREAB SPSDIMSP SPSDRABU SPSDRAE2 SPSHADOW TRAVELB'.split())
notes={
 'WTRBODY2':('new-source-proven-recipe','Variante de WTRBODY1 accepté : 10 poses sans égalité RGBA contre 20 records/10 poses. Eau et séquence distinctes ; reprendre la recette xBR/Apollo, conserver son contrat propre.'),
 'BUBLES':('palette-variant-adaptation','AMOH7300 accepté : 108/108 matrices indexées, alphas, géométries et cycles identiques ; palette différente. Réutiliser la recette xBR2blend/Apollo prémultiplié. Les RGB verts finaux ne sont pas directement substituables.'),
 'TRBLOBA':('spatial-reuse-candidate','TRGOOYAA accepté : même famille de dessins, contour et géométrie différents. Tenter adaptation du spatial existant ; pas de copie directe ni de nouvelle inférence avant contrôle des ancres, contours, couleurs et cycles.'),
 'TRBLOBB':('spatial-reuse-candidate','TRGOOYBB accepté : 70 tailles identiques, 68/70 alphas identiques ; RGB proches (MAE 1.696/255), centres et frontière de cycles différents. Tenter réemploi spatial adapté ; reconstruire contrat temporel propre, pas copier le pack final.'),
}
result=[]
for r in a['assets']:
 n=r['resref'];cs=[c for c in contexts.values() if n in c.get('bam_names',[]) and c.get('action')=='native-mask-no-ai']
 if n in native:
  assert cs
  decision='native-owner-mask-no-ai';note='Masque projectile déjà classé native-mask-no-ai ; conserver le rendu natif dans ces propriétaires. Ne pas traiter les RGB noirs par IA. Tout autre usage éventuel reste à qualifier séparément.'
 else:decision,note=notes.get(n,('new-source-no-reuse-found','Aucun réemploi exact de poses RGBA détecté dans les 623 sources produites/sélectionnées ; candidat au traitement propre.'))
 result.append(dict(ordinal=r['ordinal'],resref=n,decision=decision,note=note,projectile_contexts=[dict(context_id=c['context_id'],bam_names=c['bam_names'],action=c['action'],coverage_level=c['coverage_level'],black_only=c['black_only'],uses=c['uses']) for c in cs]))
for p,h in a['unchanged_authorities'].items():assert m.sha((root/p).read_bytes())==h,p
data=dict(date='2026-11-08',source_audit='audit.json',summary=dict(Counter(r['decision'] for r in result)),assets=result,limits=['No new inference, QA, installation, domain-index or release writes.','41 source-specific candidates including WTRBODY2; 3 adaptations/reuse candidates; 6 native owner masks.','No exact RGBA matches does not prove absence of perceptually related variants.','Native owner decisions do not grant global QA to every use of the BAM.'])
assert not (out/'conclusions.json').exists()
m.save(out/'conclusions.json',data)
lines=['# Lot50 : réemploi inter-domaines — 2026-11-08','','623 sources produites/sélectionnées comparées ; aucun doublon strict de poses RGBA. Les masques propriétaires et variantes de palette échappaient au premier filtre par BAM complet / état effects.','', '**Décision : 41 candidats avec source propre (WTRBODY2 compris), 3 adaptations à étudier avant toute nouvelle inférence, 6 masques natifs exclus des jobs IA.**','','- WTRBODY1 : animations/index/selections/WTRBODY1.json ; recette xBR/Apollo 30 validée. WTRBODY2 distinct, aucun run local.','- BUBLES ↔ AMOH7300 : mêmes 108 matrices indexées/alphas/centres/cycles ; autre palette. Recette déterministe réutilisable, pas substitution des RGB verts.','- TRBLOBA/BB ↔ TRGOOYAA/BB : spatial SeedVR validé disponible ; variantes de contours/couleurs/ancrages/cycles. Réemploi candidat, pas pack interchangeable.','- Six masques : projectiles/index/visual-assets.csv et snapshot '+snapshot['snapshot']+'/contexts.json, champ bam_names.','- Aucun suivi production/QA/install/release modifié. conclusions.json complète audit.json (champ contextuel bams de ce premier audit erroné, bam_names corrigé ici).','','| # | Source | Décision | Motif |','|---|---|---|---|']
lines.extend(f"| {r['ordinal']:02d} | {r['resref']} | {r['decision']} | {r['note']} |" for r in result)
(out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
# New board namespace; original proposal, source catalog and images preserved.
board=root/'effects/batches/lot50-magic-water-proposal-20261108-v1/review'
rev=board/'revisions/reuse-audit-20261108-v1';rev.mkdir(parents=True,exist_ok=True)
catalog=m.load(board/'catalog.json');by={r['resref']:r for r in result}
for x in catalog['assets']:
 x['image']='../../'+x['image'];x['review_decision']=by[x['resref']]['decision'];x['review_note']=by[x['resref']]['note']
template=(root/'pipeline/recipes/effects-next50-magic-water-proposal-20261108-v1/board.html').read_text(encoding='utf-8')
template=template.replace('50 productions distinctes / 51 RESREF avec l’alias SP_DEMGT.','41 candidats à produire · 3 adaptations/réemplois à étudier · 6 masques natifs sans IA. 51 RESREF avec l’alias SP_DEMGT.')
template=template.replace('À traiter · source native, sans upscale','${a.review_decision}<br>${a.review_note}')
template=template.replace("c.a.resref+' '+c.a.group","c.a.resref+' '+c.a.group+' '+c.a.review_decision")
import json
(rev/'index.html').write_text(template.replace('__CATALOG__',json.dumps(catalog,ensure_ascii=False)),encoding='utf-8')
original=board/'revisions/initial-proposal-20261108-v1';original.mkdir(parents=True,exist_ok=True)
original_page=(board/'index.html').read_text(encoding='utf-8')
if 'http-equiv="refresh"' not in original_page:
 (original/'index.html').write_text(original_page.replace('"image": "images/','"image": "../../images/'),encoding='utf-8')
(board/'index.html').write_text('<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url=revisions/reuse-audit-20261108-v1/index.html"><a href="revisions/reuse-audit-20261108-v1/index.html">Planche avec décisions de réemploi</a>',encoding='utf-8')
print(json.dumps(data['summary'],ensure_ascii=False))
