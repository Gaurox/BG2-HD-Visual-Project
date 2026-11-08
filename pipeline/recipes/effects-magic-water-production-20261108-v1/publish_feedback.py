"""Publish CPU feedback comparisons and record the user's one-asset acceptance."""
import copy,json,re,subprocess,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from temporal import ROOT,BATCH,load,save,rel
OUT=BATCH/'review-feedback-20261108-v1';REVIEW=BATCH/'review'
INSTALL=ROOT/'effects/installations/magic-feedback-0613343545-20261108-v2'
def tint_card(c,name):
 d=copy.deepcopy(c);d.pop('variants',None);d.update(method='Diagnostic rouge : alpha natif visible, sans IA',nativeOnly=False,profile='ALPHA-DIAGNOSTIC')
 folder=REVIEW/'alternatives/feedback-mask-diagnostics'/name;folder.mkdir(parents=True,exist_ok=True)
 for i,f in enumerate(d['frames']):
  arr=np.array(Image.open(REVIEW/f['image']).convert('RGBA'));mask=arr[:,:,3]>0;arr[:,:,:3][mask]=[255,60,60];p=folder/f'frame_{i:03d}.png';Image.fromarray(arr).save(p);f['image']=p.relative_to(REVIEW).as_posix()
 return d
def main():
 records=copy.deepcopy(load(REVIEW/'three-tests-cards.json')['assets']);old13=next(c for c in records if c['resref']=='WHIRLY');fix=load(OUT/'whirly-correction-final.json');correct=copy.deepcopy(fix['card']);correct['variants']=[dict(label='Détourage vert corrigé',card=fix['card']),dict(label='Avant correction',card=old13)]
 for i,c in enumerate(records):
  if c['resref']=='WHIRLY':records[i]=correct
  elif c['resref'] in {'SPSDRAE2','SPSHADOW'}:
   original=copy.deepcopy(c);diagnostic=tint_card(c,c['resref']);c['variants']=[dict(label='Masque noir natif',card=original),dict(label='Diagnostic rouge / alpha',card=diagnostic)]
 template=(REVIEW/'index.html').read_text(encoding='utf-8');archive=REVIEW/'revisions/before-feedback-0613343545-20261108-v1';archive.mkdir(parents=True,exist_ok=True)
 if not (archive/'index.html').exists():(archive/'index.html').write_text(template.replace('<html lang="fr">','<html lang="fr"><base href="../../">'),encoding='utf-8')
 template=re.sub(r'const records=.*?, \$=s=>','const records=__CARDS__, $=s=>',template,count=1,flags=re.S);assert '__CARDS__' in template
 template=template.replace("const el=document.createElement('article');el.innerHTML=","const el=document.createElement('article');el.id=a.resref;el.innerHTML=")
 template=template.replace('comparaison, aucune installation','comparaison, QA utilisateur en attente')
 template=template.replace('QA visuelle en attente, aucune installation en jeu.','Installé pour test ; QA utilisateur en cours. WTRBODY2 accepté explicitement, sans test de carte native déduit.')
 note='<p>Retour de revue : <a href="#SPARMOR2">06 original/SeedVR</a> · <a href="#WHIRLY">13 détourage corrigé/ancien</a> · <a href="#SPSDRAE2">34 masque/diagnostic</a> · <a href="#SPSHADOW">35 masque/diagnostic</a>. WTRBODY2 accepté par l’utilisateur ; aucune carte native confirmée. Diagnostics colorés uniquement, aucune nouvelle IA.</p>'
 template=template.replace('</header>',note+'</header>');page=template.replace('__CARDS__',json.dumps(records,ensure_ascii=False));js=ROOT/'.tmp/effects-next50-reuse-20261108/feedback-board.js';js.write_text(re.search(r'<script>(.*?)</script>',page,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 assert len(records)==50
 for c in records:
  for v in [c]+[r['card'] for r in c.get('variants',[])]:
   for f in v['frames']:
    for k in ['image','neutral']:
     if k in f:assert (REVIEW/f[k]).is_file()
 save(REVIEW/'feedback-cards.json',dict(count=50,assets=records));(REVIEW/'index.html').write_text(page,encoding='utf-8')
 # Current working production points to installed repaired bytes; older results immutable.
 prod=copy.deepcopy(load(BATCH/'production-current-v2.json'))
 for row in prod['assets']:
  if row['resref']=='WHIRLY':row.update(spatial_run=fix['asset']['spatial_run'],interpolation_run=fix['asset']['interpolation_run'],pack=fix['result']['pack'],pack_manifest_sha256=fix['result']['pack_manifest_sha256'],verification=rel(OUT/'whirly-correction-final.json'),runtime_verification=rel(OUT/'green-v2-runtime/runtime-verification/WHIRLY.json'),visual_qa='pending-user-retest')
  elif row['resref'] in {'SPBASEWT','SPENTAXI'}:
   r=load(BATCH/'alternatives/black-alpha-check-20261108-v1/packs/verification'/f"{row['resref']}.json");row.update(interpolation_run=r['interpolation_run'],pack=r['pack'],pack_manifest_sha256=r['pack_manifest_sha256'],verification=rel(BATCH/'alternatives/black-alpha-check-20261108-v1/packs/verification'/f"{row['resref']}.json"),runtime_verification=rel(BATCH/'alternatives/black-alpha-check-20261108-v1/packs/verification'/f"{row['resref']}.json"))
  elif row['resref']=='WTRBODY2':row.update(visual_qa='accepted-explicit-user',qa_evidence=load(ROOT/'effects/index/selections/WTRBODY2.json')['qa_evidence'],native_map_confirmed=False)
 prod.update(supersedes='production-current-v2.json',feedback_installation=rel(INSTALL/'installation.json'),gpu_state='paused',qa_scope='Only WTRBODY2 newly accepted;06/13/34/35 pending retest.')
 save(BATCH/'production-current-v3.json',prod);save(BATCH/'current-production.json',dict(path=rel(BATCH/'production-current-v3.json'),sha256=hashlib.sha256((BATCH/'production-current-v3.json').read_bytes()).hexdigest().upper(),gpu_paused=True))
 lines=['# Retours06/13/34/35/45 — 2026-11-08','','- 06 SPARMOR2 : original natif ZFR06O / nouveau ZMWT06 ; même durée source, IA seulement dans le nouveau.','- 13 WHIRLY : ZMWT13 corrigé CPU (canonique WHIRLY et XMWN13 corrigés aussi) ; ZFR13B conserve l’ancien HD. Tous les verts178, y compris2408pixels enfermés, sont retirés ; alpha de mélange de palette +despill, 0pixels verts couverts selonG>max(R,B)+8. Centres/durées/carrier inchangés.','- 34 SPSDRAE2 : vrai masque RGBnoir, alphamax196, usage potentiel spread CDDRBLCK. ZFR34N = natif décalé100px àdroite ; ZFR34C = même alpha en rouge.','- 35 SPSHADOW : ombre noire native5–7px, usage potentiel shadow SPATTCK2. ZFR35N = minuscule natif décalé100px ; ZFR35C = diagnostic rouge agrandi4×monde, uniquement diagnostic.','- 45 WTRBODY2 : utilisateur «non je ne sais pas. c’est pas grave on le valide» ; accepté uniquementxBR2/nearest2/Apollo30 installé, décision immuable et sélection. Aucune carte native confirmée, aucun test surmap déduit. WTRBODY1 seul trouvéAR0502(499,182) ; aucune carte modifiée.','- Recherche WTRBODY2 : AREnatifs+overrides ;5410BCS/VVC/EFF/PRO ;8550tables/IDS/INI/dialogues/sorts/items ; aucun appel natif trouvé. Une référence de notretest ZMWB45 ignorée. Pas preuve d’absence de toute construction dynamique.','- Installation `effects/installations/magic-feedback-0613343545-20261108-v2/transaction.json` ;93cibles,50backings WHIRLY remplacés avec sauvegarde, ancienHD conservé sousalias ;23808contrats passent avant+après, GPUintouché, aucunerelease.','','## CLUA','','Original06 puis nouveau :','','```lua',"C:Eval('CreateVisualEffectObject(\"ZFR06O\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZMWT06\",Player1)',0)",'```','','13corrigé puis ancienHD :','','```lua',"C:Eval('CreateVisualEffectObject(\"ZMWT13\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFR13B\",Player1)',0)",'```','','34natif décalé puis témoin rouge :','','```lua',"C:Eval('CreateVisualEffectObject(\"ZFR34N\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFR34C\",Player1)',0)",'```','','35natif décalé puis témoin rouge agrandi :','','```lua',"C:Eval('CreateVisualEffectObject(\"ZFR35N\",Player1)',0)","C:Eval('CreateVisualEffectObject(\"ZFR35C\",Player1)',0)",'```']
 (INSTALL/'CLUA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');(OUT/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 for p in [ROOT/'effects/README.md',ROOT/'effects/REPRISE.md']:
  text=p.read_text(encoding='utf-8-sig');i=text.index('\n')+1;note='\n**Retours magie/eau06/13/34/35/45 — 2026-11-08** : [résultat/CLUA](batches/lot50-magic-water-production-20261108-v1/review-feedback-20261108-v1/README.md), [planche50](http://127.0.0.1:8799/).06original natif ajouté ;13WHIRLY corrigé CPU installé (vert enfermé+franges/despill, canonique et normal), ancienHD conservé ;34/35masques noirs : diagnostics rouges décalés,35agrandi4×diagnostic seulement.45WTRBODY2 accepté explicitement sans carte native confirmée ; sélectionxBR2/Apollo30, aucune QA map déduite. Production courantev3 ; autres QA/release inchangées, GPUenpause.\n\n';p.write_text(text[:i]+note+text[i:].lstrip('\n'),encoding='utf-8')
 print('Feedback board50 updated; WHIRLY installed corrected; WTRBODY2 accepted only; GPU remains paused.')
if __name__=='__main__':main()
