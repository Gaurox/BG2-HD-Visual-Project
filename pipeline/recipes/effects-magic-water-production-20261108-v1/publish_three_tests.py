"""CPU-only50-card revision with per-asset choices for two alphas and SPCSPRAI SeedVR."""
import copy,json,re,subprocess
from pathlib import Path
from PIL import Image
from temporal import ROOT,BATCH,load,save
from publish_review import OUT
def main():
 records=load(OUT/'current-cards.json')['assets']
 alpha=BATCH/'alternatives/black-alpha-check-20261108-v1'
 seed=load(BATCH/'alternatives/spcsprai-seedvr7b-test-20261108-v1/result.json')
 # Use existing reviewed50 board template; runtime/production choices remain unchanged.
 template=(OUT/'index.html').read_text(encoding='utf-8');template=re.sub(r'const records=.*?, \$=s=>', 'const records=__CARDS__, $=s=>',template,count=1,flags=re.S)
 assert '__CARDS__' in template
 for i,c in enumerate(records):
  if c['resref'] in ['SPBASEWT','SPENTAXI']:
   witness=copy.deepcopy(c);variant=load(alpha/f"{c['resref']}.json")['card']
   c=copy.deepcopy(variant);c['variants']=[dict(label='Noir transparent progressif',card=variant),dict(label='Alpha natif / témoin',card=witness)];records[i]=c
  elif c['resref']=='SPCSPRAI':
   witness=copy.deepcopy(c);test=seed['card'];c=copy.deepcopy(test);c['variants']=[dict(label='Test SeedVR7B/LAB',card=test),dict(label='xBR4X actuel',card=witness)];records[i]=c
 # Add a formula selector only on the3 affected cards; profile selector stays independent.
 template=template.replace('<div class="controls"><button class="pause">','<div class="controls">${a.variants?`<select class="version">${a.variants.map((v,i)=>`<option value="${i}">${v.label}</option>`).join(\'\')}</select>`:\'\'}<button class="pause">')
 template=template.replace('<select>${a.profiles.map','<select class="profile">${a.profiles.map')
 template=template.replace("el.querySelector('select').onchange=e=>c.setProfile(Number(e.target.value));","el.querySelector('.profile').onchange=e=>c.setProfile(Number(e.target.value));if(a.variants)el.querySelector('.version').onchange=e=>{const v=a.variants[Number(e.target.value)].card;c.a=v;const pick=el.querySelector('.profile');pick.innerHTML=v.profiles.map((p,i)=>`<option value=\"${i}\">${p.id} · ${p.duration.toFixed(2)}s</option>`).join('');el.querySelector('.view:nth-child(2) .caption').textContent=v.method;el.querySelector('.meta').textContent=v.method+' · comparaison, aucune installation';c.setProfile(0)};")
 # setProfile must read the currently selected version, not initial closure a.
 template=template.replace('el.querySelector(\'.phase\').max=a.profiles[i].frames.length-1','el.querySelector(\'.phase\').max=c.a.profiles[i].frames.length-1')
 note='<p>Tests du 08/11 : SPBASEWT/SPENTAXI — noir transparent progressif ou témoin alpha natif ; SPCSPRAI — SeedVR7B ou xBR4X. Choisir la version dans chaque carte concernée. Comparaisons uniquement, packs actifs inchangés. GPU à nouveau en pause après ce test.</p>'
 template=template.replace('</header>',note+'</header>')
 archive=OUT/'revisions/before-three-tests-20261108-v1';archive.mkdir(parents=True,exist_ok=True)
 if not (archive/'index.html').exists():(archive/'index.html').write_text((OUT/'index.html').read_text(encoding='utf-8').replace('<html lang="fr">','<html lang="fr"><base href="../../">'),encoding='utf-8')
 page=template.replace('__CARDS__',json.dumps(records,ensure_ascii=False))
 for c in records:
  versions=[c]+[v['card'] for v in c.get('variants',[])]
  for v in versions:
   assert (OUT/v['native']['image']).is_file()
   for f in v['frames']:
    for k in ['image','neutral']:
     if k in f:
      with Image.open(OUT/f[k]) as im:assert im.size==(f['w'],f['h'])
 js=ROOT/'.tmp/effects-next50-reuse-20261108/three-tests-board.js';js.write_text(re.search(r'<script>(.*?)</script>',page,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 save(OUT/'three-tests-cards.json',dict(count=50,assets=records));(OUT/'index.html').write_text(page,encoding='utf-8')
 save(BATCH/'three-tests-review.json',dict(resrefs=['SPBASEWT','SPENTAXI','SPCSPRAI'],board='http://127.0.0.1:8799/',active_production_unchanged=True,installed=False,qa='pending-user-choice',gpu_scope='Single SPCSPRAI test finished, models unloaded, global pause retained.'))
 print('50 cards,3 version selectors, sources and all variant images checked; JS syntax valid.')
if __name__=='__main__':main()
