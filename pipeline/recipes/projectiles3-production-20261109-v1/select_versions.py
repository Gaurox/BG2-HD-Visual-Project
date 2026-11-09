"""Pin the user's spatial-version choices; runtime QA remains independent."""
from pathlib import Path
import copy,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[3];BATCH=ROOT/'effects/batches/projectiles3-production-20261109-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
import effect_authority as authority
CHOICES={'BGLRYU':'SeedVR7B','SPCL236U':'SeedVR7B','SPGLYPHI':'xBR4X'}
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rel(p):return p.relative_to(ROOT).as_posix()
def immutable(p,d):
 raw=w.json_bytes(d)
 if p.exists():assert p.read_bytes()==raw,'Existing decision differs; use a new version'
 else:p.write_bytes(raw)
def main():
 old=load(BATCH/'production-current-v2.json');seed=load(BATCH/'production.json')
 before={r['asset_key']:r for r in w.read_csv(ROOT/'effects/index/processing.csv')}
 current=copy.deepcopy(old);selected=[]
 from compose_effect_runtime_packs import validate_pack
 for n,choice in CHOICES.items():
  source=seed if choice=='SeedVR7B' else old
  a=copy.deepcopy(next(a for a in source['assets'] if a['resref']==n));a.pop('seedvr_version',None)
  a.update(method='seedvr2_7b_int8_convrot.safetensors' if choice=='SeedVR7B' else 'XBR/xbr4X',selected_version=choice,visual_qa='user-version-choice-on-animated-board',ingame_qa='not-assessed')
  p=validate_pack(ROOT/a['pack']);assert p.manifest_sha256==a['pack_manifest_sha256']
  assert all(w.sha256_file(ROOT/c['pack']/'manifest.json')==c['manifest_sha256'] for c in a['companions'])
  for stage in ['spatial','interpolation']:
   row=next(r for r in w.read_csv(ROOT/'effects/index/processing.csv') if r['asset_key']=='effects:bam:'+n)
   if row[stage+'_run']!=a[stage+'_run']:w.register_run(ROOT,n,stage,a[stage+'_run'],write=True)
  selected.append(a)
 decision=dict(schema='bg2-projectiles-visual-version-choice-v1',date='2026-11-09',user_message='garde BGLRYU et BGLRYU en seedVR et SPGLYPHI en XBR',clarification_question='Le deuxième BGLRYU désigne-t-il SPCL236U, également à garder en SeedVR ?',user_clarification='Oui, SPCL236U en SeedVR',choices=CHOICES,assets=[dict(resref=a['resref'],version=a['selected_version'],spatial_run=a['spatial_run'],interpolation_run=a['interpolation_run'],pack=w.file_evidence(ROOT,ROOT/a['pack']/'manifest.json')) for a in selected],scope='User retained spatial versions on animated board. No ingame test, native owner contract, alpha companion selection, installation or release acceptance inferred.')
 immutable(BATCH/'version-choice-20261109-v1.json',decision)
 current.update(status='user-versions-selected-runtime-review-pending',assets=selected,default_version='user-selection',default_versions=CHOICES,decision='BGLRYU + SPCL236U SeedVR7B; SPGLYPHI xBR4X. User confirmed duplicated name.',version_choice=rel(BATCH/'version-choice-20261109-v1.json'))
 current['summary'].update(methods={'SeedVR7B':2,'xBR4X':1},backings=sum(a['backings'] for a in selected),raw_bytes=sum(a['raw_bytes'] for a in selected))
 immutable(BATCH/'production-current-v3.json',current)
 (BATCH/'current-production.json').write_bytes(w.json_bytes(dict(path=rel(BATCH/'production-current-v3.json'),sha256=w.sha256_file(BATCH/'production-current-v3.json'))))
 plan=load(BATCH/'integration-plan-current-v2.json');plan['current_production']=rel(BATCH/'production-current-v3.json');plan['default_method']='user-selection';plan['version_choices']=CHOICES
 for a in plan['assets']:a['pack']=next(x['pack'] for x in selected if x['resref']==a['resref'])
 immutable(BATCH/'integration-plan-current-v3.json',plan)
 # Only the working board changes; all version frames and previous manifests remain.
 board=BATCH/'review-versions/index.html';html=board.read_text(encoding='utf-8')
 html=html.replace('xBR fidèle affiché par défaut ; SeedVR7B disponible pour comparaison.','Choix retenus : BGLRYU et SPCL236U en SeedVR7B ; SPGLYPHI en xBR4X.')
 html=html.replace('<select id="method">','<select id="method"><option value="selected" selected>Choix retenus</option>')
 html=html.replace("el.classList.toggle('hidden',a.version!=='xBR4X');","el.classList.toggle('hidden',a.version!==retained[a.resref]);")
 html=html.replace("function filter(){",'const retained='+json.dumps(CHOICES)+';function filter(){')
 # retained is needed during card creation, before the final filtering callback.
 declaration='const retained='+json.dumps(CHOICES)+';'
 html=html.replace(declaration,'');html=html.replace('<script>','<script>\n'+declaration+'\n',1)
 html=html.replace("(m==='all'||c.a.version===m)","(m==='all'||(m==='selected'?c.a.version===retained[c.a.resref]:c.a.version===m))")
 js=ROOT/'.tmp/projectiles3-20261109-v1/selected-board.js';js.write_text(re.search(r'<script>(.*?)</script>',html,re.S)[1],encoding='utf-8');subprocess.run(['node','--check',str(js)],check=True)
 board.write_text(html,encoding='utf-8')
 completion=load(ROOT/'effects/index/completion.json');completion.update(processing_sha256=w.sha256_file(ROOT/'effects/index/processing.csv'),extension=rel(BATCH/'production-current-v3.json'),version_choice=rel(BATCH/'version-choice-20261109-v1.json'),scope='Initial494 closed entries retained. Three new spatial versions chosen on animated board; owner/runtime QA and alpha route remain independent, no ingame acceptance inferred.')
 with authority.guard(ROOT,True):authority.commit(ROOT,{'effects/index/completion.json':w.json_bytes(completion)})
 after={r['asset_key']:r for r in w.read_csv(ROOT/'effects/index/processing.csv')}
 for k,r in before.items():
  if k.rsplit(':',1)[-1] not in CHOICES:assert after[k]==r
  else:assert all(after[k][f]==r[f] for f in ['qa_state','qa_evidence','installation_state','installation_receipt','release_state','release_candidate'])
 print('Retained: BGLRYU=SeedVR7B, SPCL236U=SeedVR7B, SPGLYPHI=xBR4X. Other QA/install/release preserved.')
if __name__=='__main__':main()
