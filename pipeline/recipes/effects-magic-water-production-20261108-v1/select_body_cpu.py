"""CPU-only current review selection; historical production/SeedVR baseline retained."""
import copy,json,hashlib,re,subprocess
from pathlib import Path
from collections import Counter
from PIL import Image
from temporal import ROOT,BATCH,load,save,rel
from publish_review import OUT,build,contact
def main():
 assert (BATCH/'gpu-paused.json').exists()
 archive=OUT/'revisions/seedvr-baseline-20261108-v1';archive.mkdir(parents=True,exist_ok=True)
 if not (archive/'index.html').exists():
  html=(OUT/'index.html').read_text(encoding='utf-8').replace('<head>','<head><base href="../../">')
  # Template has no explicit head element; inject base immediately after doctype.
  if '<base ' not in html:html=html.replace('<html lang="fr">','<html lang="fr"><base href="../../">')
  html=html.replace("const el=document.createElement('article');el.innerHTML=","const el=document.createElement('article');el.id=a.resref;el.innerHTML=")
  (archive/'index.html').write_text(html,encoding='utf-8')
 old=load(BATCH/'production.json');data=copy.deepcopy(old);f=load(BATCH/'body-fallback.json');r=f['result'];a=f['asset']
 row=next(v for v in data['assets'] if v['resref']=='WTRBODY2')
 row.update(method='XBR/xbr2-nearest2',spatial_run=a['spatial_run'],interpolation_run=a['interpolation_run'],pack=r['pack'],pack_manifest_sha256=r['pack_manifest_sha256'],verification=f['verification'],runtime_verification=f['runtime_verification'],phases=r['phases'],profiles=r['profiles'],native_contracts=r['native_contracts'],raw_bytes=r['raw_bytes'],backings=r['backings'],selection_reason=f['reason'],seedvr_alternative=next(v for v in old['assets'] if v['resref']=='WTRBODY2'))
 s=data['summary'];s.update(methods=dict(Counter(v['method'] for v in data['assets'])),backings=sum(v['backings'] for v in data['assets']),raw_bytes=sum(v['raw_bytes'] for v in data['assets']))
 data.update(supersedes='production.json',gpu_state='paused-by-user-no-new-GPU-until-explicit-signal',selection='WTRBODY2 faithful xBR fallback displayed; SeedVR baseline retained for comparison.')
 assert build()==50
 cards=load(OUT/'current-cards.json')['assets'];assert len(cards)==50
 for c in cards:
  assert all(0<=i<len(c['frames']) for p in c['profiles'] for i in p['frames'])
  for item in c['frames']:
   for k in ['image','neutral']:
    if k in item:
     with Image.open(OUT/item[k]) as im:assert im.size==(item['w'],item['h'])
 html=(OUT/'index.html').read_text(encoding='utf-8');script=ROOT/'.tmp/effects-next50-reuse-20261108/production-current-v2.js';script.write_text(re.search(r'<script>(.*?)</script>',html,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(script)],check=True)
 save(BATCH/'production-current-v2.json',data)
 save(BATCH/'current-production.json',dict(path=rel(BATCH/'production-current-v2.json'),sha256=hashlib.sha256((BATCH/'production-current-v2.json').read_bytes()).hexdigest().upper(),gpu_paused=True))
 contact()
 note='\n**Sélection courante v2 / pause GPU utilisateur** : `current-production.json` → `production-current-v2.json`.36SeedVR7B,6xBR4X,1BUBLES xBR2blend,1WTRBODY2 xBR2/nearest2,6masques natifs ;44productions Apollo30/50cartes. WTRBODY2 SeedVR surinterprète le corps/reflets32px : repli fidèle affiché, variante SeedVR/production.json baseline conservées. GPU déchargé,30.04/31.82Gio libres constatés ; aucun nouveau GPU avant signal explicite. Dernières opérations planche/classement = CPU seulement.\n\n'
 p=BATCH/'README.md';text=p.read_text(encoding='utf-8');i=text.index('\n')+1;p.write_text(text[:i]+note+text[i:].lstrip('\n'),encoding='utf-8')
 for p in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
  text=p.read_text(encoding='utf-8-sig');i=text.index('\n')+1
  line='\n**Pack magie/eau courant v2 — GPU en pause utilisateur** : [résultat](batches/lot50-magic-water-production-20261108-v1/README.md), [planche50](http://127.0.0.1:8799/).36SeedVR7B,8xBR (dont repli WTRBODY2 fidèle),6masques natifs ;44productions30FPS/5460phases/140profils,10920contrats natifs passants. Source30FPS = cible sur base15FPS de compatibilité ; pas de mesure ingame. Aucun nouveau GPU avant signal explicite ; modèles déchargés,30.04Gio libres sur31.82. QA utilisateur en attente ; aucune installation/release.\n\n'
  p.write_text(text[:i]+line+text[i:].lstrip('\n'),encoding='utf-8')
 print(json.dumps(s,ensure_ascii=False));print('CPU-only selection done. GPU remains paused.')
if __name__=='__main__':main()
