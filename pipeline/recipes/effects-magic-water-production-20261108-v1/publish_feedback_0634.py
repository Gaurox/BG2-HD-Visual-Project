"""CPU board/bookkeeping after requested06 xBR, accepted13/35, fixed34 cycle selectors."""
import copy,json,re,subprocess,hashlib,sys,struct
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from temporal import ROOT,BATCH,load,save,rel
from workspace_paths import get_path
OUT=BATCH/'review-feedback-0634-20261108-v1';REVIEW=BATCH/'review';INSTALL=ROOT/'effects/installations/magic-feedback-0634-20261108-v1'
def visible_first(c):
 c=copy.deepcopy(c);c['profiles'].sort(key=lambda p:(p['cycle']!=1,not p['loop'],p['cycle']));return c
def main():
 records=copy.deepcopy(load(REVIEW/'feedback-cards.json')['assets']);xbr=load(OUT/'SPARMOR2-result.json');mask=load(OUT/'SPSDRAE2-result.json')
 for i,c in enumerate(records):
  if c['resref']=='SPARMOR2':
   original=copy.deepcopy(c);new=copy.deepcopy(xbr['card']);new['variants']=[dict(label='xBR4X · CPU30 actuel',card=xbr['card']),dict(label='Ancien SeedVR',card=original)];records[i]=new
  elif c['resref']=='SPSDRAE2':
   variants=[dict(label='Natif : cycle1 visible',card=visible_first(v['card'])) if j==0 else dict(label='Témoin rouge : cycle1 visible',card=visible_first(v['card'])) for j,v in enumerate(c['variants'])]
   variants.append(dict(label='RGBA natif / alpha CPU30',card=visible_first(mask['card'])));new=copy.deepcopy(variants[0]['card']);new['method']='Masque natif · cycle1 visible (cycle0 vide)';new['variants']=variants;records[i]=new
  elif c['resref']=='WHIRLY':c['method']+=' · validé'
  elif c['resref']=='SPSHADOW':c['method']='Masque natif validé · diagnostics non retenus'
 template=(REVIEW/'index.html').read_text(encoding='utf-8');archive=REVIEW/'revisions/before-feedback-0634-20261108-v1';archive.mkdir(parents=True,exist_ok=True)
 if not (archive/'index.html').exists():(archive/'index.html').write_text(template.replace('<html lang="fr">','<html lang="fr"><base href="../../">'),encoding='utf-8')
 template=re.sub(r'const records=.*?, \$=s=>','const records=__CARDS__, $=s=>',template,count=1,flags=re.S);assert '__CARDS__' in template
 template=template.replace('36 SeedVR7B/LAB · 6 xBR minuscules','35 SeedVR7B/LAB · 6 xBR minuscules · SPARMOR2 xBR4X/CPU30')
 template=template.replace('</header>','<p>Dernier retour : 06 passé en xBR4X avec interpolation CPU30 ; 13 et35 validés.34 : cycle0 = pose transparente de réserve, affichage corrigé sur cycle1 (cycle2 conservé). Les tests34 durent12s avec les pauses natives. GPU toujours en pause.</p></header>')
 page=template.replace('__CARDS__',json.dumps(records,ensure_ascii=False));js=ROOT/'.tmp/effects-next50-reuse-20261108/feedback-0634-board.js';js.write_text(re.search(r'<script>(.*?)</script>',page,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 assert len(records)==50
 for c in records:
  for v in [c]+[r['card'] for r in c.get('variants',[])]:
   for f in v['frames']:
    for k in ['image','neutral']:
     if k in f:assert (REVIEW/f[k]).is_file()
 save(REVIEW/'feedback-0634-cards.json',dict(count=50,assets=records));(REVIEW/'index.html').write_text(page,encoding='utf-8')
 prod=copy.deepcopy(load(BATCH/'production-current-v3.json'))
 for a in prod['assets']:
  if a['resref']=='SPARMOR2':a.update(method='XBR/xbr4X',spatial_run=xbr['asset']['spatial_run'],interpolation_run=xbr['asset']['interpolation_run'],pack=xbr['result']['pack'],pack_manifest_sha256=xbr['result']['pack_manifest_sha256'],backings=xbr['result']['backings'],raw_bytes=xbr['result']['raw_bytes'],verification=rel(OUT/'verification/SPARMOR2.json'),runtime_verification=rel(OUT/'runtime-verification/SPARMOR2.json'),visual_qa='pending-user-retest',temporal_model='CPU/ffmpeg-minterpolate-mci')
  if a['resref']=='WHIRLY':a.update(visual_qa='accepted-explicit-user',qa_evidence=load(ROOT/'effects/index/selections/WHIRLY.json')['qa_evidence'])
 for a in prod['native_masks']:
  if a['resref']=='SPSHADOW':a.update(visual_qa='accepted-native-explicit-user',qa_evidence=load(ROOT/'effects/index/selections/SPSHADOW.json')['qa_evidence'])
  if a['resref']=='SPSDRAE2':a.update(visual_qa='pending-visible-cycle-retest',test_cycle=1,diagnosis='Cycle0 points to source frame19, fully transparent.')
 prod['summary']['methods']=dict(Counter(a['method'] for a in prod['assets']));prod['summary']['backings']=sum(a['backings'] for a in prod['assets']);prod['summary']['raw_bytes']=sum(a['raw_bytes'] for a in prod['assets']);prod.update(supersedes='production-current-v3.json',latest_installation=rel(INSTALL/'installation.json'),gpu_state='paused',qa_scope='WTRBODY2,WHIRLY,SPSHADOW explicitly accepted; remaining entries not inferred.')
 save(BATCH/'production-current-v4.json',prod);save(BATCH/'current-production.json',dict(path=rel(BATCH/'production-current-v4.json'),sha256=hashlib.sha256((BATCH/'production-current-v4.json').read_bytes()).hexdigest().upper(),gpu_paused=True))
 # Preserve concise causal evidence from the installed controller backups.
 game=get_path('bg2ee_game_root',required=True);controllers=[]
 for name in ['ZMWT34','ZFR34N','ZFR34C']:
  old=(INSTALL/'before/override'/f'{name}.vvc').read_bytes();new=(game/'override'/f'{name}.vvc').read_bytes();controllers.append(dict(vvc=name,old_cycle=struct.unpack_from('<I',old,0x68)[0]-1,new_cycle=struct.unpack_from('<I',new,0x68)[0]-1,new_lifetime_ticks=struct.unpack_from('<I',new,0x5c)[0]))
 assert all(c['old_cycle']==0 and c['new_cycle']==1 for c in controllers)
 save(OUT/'cause-34.json',dict(source='SPSDRAE2',reserved_cycle=0,reserved_frame=19,reserved_frame_alpha_max=0,visible_cycles=[1,2],controllers=controllers,engine_change_required=False,native_pause_slots_preserved=True,gpu_used=False))
 lines=['# Retour06/13/34/35','','- 06 SPARMOR2 : xBR4X sans flou, interpolation **CPU minterpolate MCI** vers30FPS ; pas Apollo/GPU. Ancres/centres/pauses natifs conservés. CanoniqueSPARMOR2 +XMWN06 remplacés, ancienSeedVR conservé MFX06S/ZFX06S.','- 13 WHIRLY corrigé : explicitement accepté, QA immuable +sélection.','- 35 SPSHADOW : explicitement accepté **natif**, ni rouge ni agrandi en production.','- 34 : défaut de lanceur. Cycle0 référence seulementframe19,alpha0 ; les cycles1/2 sont visibles puis tiennent longtempsframe19. ZMWT34/ZFR34N/ZFR34C corrigés surcycle1, durée12s ; ZFX34B pourcycle2 ; ZFX34R = témoin RGBA noir avec alpha natif/x4nearest et interpolation alphaCPU, sansIA.','- Logs : rendus XMWN06/XMWN13 présents, pas de traceHD des anciens témoins34 (chemin natif). Absence de traceHD ne prouve pas un échec natif. Cause confirmée en lisant VVC +lookupBAM +alpha : cycle0vide. Aucun moteur/DLL/INI modifié.','- Installation `transaction.json` :122backings06 remplacés avec sauvegarde +2comparaisons HD ajoutées ;24936contrats natifs passent candidat+installé ; GPU toujours en pause. QA06/34 àretester.','', 'Relancer via InfinityLoader. Une commande àlafois.','','## 06 xBR actuel / ancien SeedVR','','```lua',"C:Eval('CreateVisualEffectObject(\"ZMWT06\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFX06S\",Player1)',0)",'```','','## 34 cycle1 noir / cycle1 rouge / cycle2 noir / témoin RGBA','','Laisser tourner12s après fermeture de la console ; les pauses natives sont conservées.','','```lua',"C:Eval('CreateVisualEffectObject(\"ZMWT34\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFR34C\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFX34B\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFX34R\",Player1)',0)",'```']
 (OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');(INSTALL/'CLUA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 for p in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
  text=p.read_text(encoding='utf-8-sig');i=text.index('\n')+1;note='\n**Retours magie/eau06/13/34/35** : [résultat et CLUA](batches/lot50-magic-water-production-20261108-v1/review-feedback-0634-20261108-v1/README.md), [planche50](http://127.0.0.1:8799/).06xBR4X/CPU-motion30 installé ;13WHIRLY corrigé accepté ;35SPSHADOW natif accepté.34invisible = cycle0frame19 entièrement transparent ; contrôleurs corrigéscycle1, cycle2/témoinRGBA disponibles, pauses intactes, durée12s.24936contrats passants, DLL/INI inchangés, GPUenpause. Production courantev4 ; autres QA/release inchangées.\n\n';p.write_text(text[:i]+note+text[i:].lstrip('\n'),encoding='utf-8')
 print('Board50/currentv4 updated;13/35 accepted;06 xBR and34 cycle fix installed; GPU pause retained.')
if __name__=='__main__':main()
