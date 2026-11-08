"""Record produced pack and board, without QA acceptance, installation or release writes."""
import json,re,subprocess
from collections import Counter
from pathlib import Path
from PIL import Image
from temporal import ROOT,BATCH,load,save,rel
from publish_review import build,contact,OUT
def main():
 batch=load(BATCH/'batch.json');assert build()==50
 results=[]
 for a in batch['assets']:
  n=a['resref'];v=load(BATCH/'verification'/f'{n}.json');r=load(BATCH/'runtime-verification'/f'{n}.json')
  assert v['passed'] and r['passed']
  sp=load(ROOT/'effects/ressources'/n/'runs'/a['spatial_run']/'01-spatial-x4/manifest.json')
  method=sp['parameters']['model']
  assert method in {'seedvr2_7b_int8_convrot.safetensors','XBR/xbr4X','XBR/xbr2blend-nearest2'}
  results.append(dict(ordinal=a['ordinal'],resref=n,source=a['source'],source_sha256=a['source_sha256'],method=method,spatial_run=a['spatial_run'],interpolation_run=a['interpolation_run'],pack=r['pack'],pack_manifest_sha256=r['pack_manifest_sha256'],verification=rel(BATCH/'verification'/f'{n}.json'),runtime_verification=rel(BATCH/'runtime-verification'/f'{n}.json'),phases=r['phases'],profiles=r['profiles'],native_contracts=r['native_contracts'],raw_bytes=r['raw_bytes'],backings=r['backings'],reuse_aliases=a['reuse_aliases'],visual_qa='pending-user-review',installed=False,normal_flux_companion=a['profile']=='H'))
 cards=load(OUT/'current-cards.json')['assets'];assert len(cards)==50 and {c['ordinal'] for c in cards}==set(range(1,51))
 checked={}
 for c in cards:
  assert c['profiles']
  atlas=OUT/c['native']['image'];assert atlas.is_file()
  for p in c['profiles']:
   assert len(p['frames'])==len(p['native'])*2
   assert p['duration']==len(p['native'])/15
   assert all(0<=i<len(c['frames']) for i in p['frames'])
  for f in c['frames']:
   assert 0<=f['x'] and 0<=f['y'] and f['x']+f['w']<=c['width'] and f['y']+f['h']<=c['height']
   for key in ['image','neutral']:
    if key not in f:continue
    p=OUT/f[key]
    if p not in checked:
     with Image.open(p) as im:checked[p]=im.size
    assert checked[p]==(f['w'],f['h'])
 h=(OUT/'index.html').read_text(encoding='utf-8');js=ROOT/'.tmp/effects-next50-reuse-20261108/final-production-board.js';js.write_text(re.search(r'<script>(.*?)</script>',h,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 summary=dict(new_productions=len(results),native_masks_preserved=len(batch['native_masks']),board_entries=50,methods=dict(Counter(r['method'] for r in results)),phases=sum(r['phases'] for r in results),profiles=sum(r['profiles'] for r in results),native_contracts=sum(r['native_contracts'] for r in results),backings=sum(r['backings'] for r in results),raw_bytes=sum(r['raw_bytes'] for r in results),unique_review_pngs=len(checked),interpolation_fps=30,native_mask_interpolation='unchanged native, no new interpolation',native_rate_basis='15 FPS compatibility default; ingame cadence not measured')
 save(BATCH/'production.json',dict(schema='bg2-effects-production-batch-result-v1',status='completed-production-pending-visual-QA',summary=summary,assets=results,native_masks=[dict(ordinal=a['ordinal'],resref=a['resref'],source=a['source'],source_sha256=a['source_sha256'],decision='native-owner-mask-no-ai',installed=False) for a in batch['native_masks']],board='http://127.0.0.1:8799/',blob_reuse_decision=rel(BATCH/'blob-reuse-decision.json'),scope='New production only; QA acceptance, game installation and release untouched.'))
 contact()
 lines=['# Magie/eau — pack traité, 2026-11-08','','- [Planche50 natif/traité](http://127.0.0.1:8799/) : pause/phase/vitesse/cycles/fonds ; halos alpha lumineux sélectionnés par défaut, témoin alpha natif accessible.','- **37 SeedVR7B INT8/LAB x4 +6 xBR4X +BUBLES xBR2blend/nearest2 palette propre ;6 masques natifs conservés**. TRBLOBA/BB : réemploi direct non équivalent, repli SeedVR autorisé exécuté ; parents acceptés inchangés.','- Apollo apo-8 vers30FPS sur44productions, cycles once/loop et poses tenues conservés ; cadence source15FPS = compatibilité si propriétaire inconnu, pas mesure ingame.6masques natifs non nouvellement interpolés.',f"- {summary['phases']}phases /{summary['profiles']}profils /{summary['backings']}backings ; {summary['native_contracts']}contrats natifs passants. Source/carrier : pixels, palettes, centres et cycles natifs conservés ; WHIRLY dérivation du vert indexé178 de bord dans copie de travail.",'- Packs courants exclusivement dans `production.json`, registrev3 ; `*-initial-*` sont intermédiaires. Alias SP_DEMGT documenté mais aucune nouvelle liaison ingame installée.','- QA visuelle utilisateur en attente ; aucune installation/release. Planche peut afficher des compagnons de flux sans changer les octets du pack alpha natif ; routage propriétaire à choisir lors de l’intégration.','- `verification/*.json` : géométrie/timing/alpha/pixels ; `runtime-verification/*.json` : lecteur natif. Recette : `pipeline/recipes/effects-magic-water-production-20261108-v1/`.','','| # | Source | Production | Pack |','|---|---|---|---|']
 for r in sorted(results,key=lambda r:r['ordinal']):lines.append(f"| {r['ordinal']:02d} | {r['resref']} | {r['method']} | `{r['pack']}` |")
 for a in batch['native_masks']:lines.append(f"| {a['ordinal']:02d} | {a['resref']} | natif conservé | pas de nouveau pack |")
 (BATCH/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 for p in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
  s=p.read_text(encoding='utf-8-sig');pos=s.index('\n')+1;note=f'\n**Pack magie/eau traité2026-11-08** : [production](batches/lot50-magic-water-production-20261108-v1/README.md), [planche50](http://127.0.0.1:8799/).37SeedVR7B/LAB,6xBR4X,1BUBLES xBR2blend ;6masques natifs conservés.44productions Apollo30,{summary["phases"]}phases/{summary["profiles"]}profils,{summary["native_contracts"]}contrats natifs passants. TRBLOBA/BB repli SeedVR exécuté après diagnostic de réemploi. QA utilisateur en attente, aucune installation/release.\n\n'
  if '**Pack magie/eau traité2026-11-08**' not in s:p.write_text(s[:pos]+note+s[pos:].lstrip('\n'),encoding='utf-8')
 print(json.dumps(summary,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
