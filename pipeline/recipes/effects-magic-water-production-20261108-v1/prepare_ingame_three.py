"""Prepare6 isolated CLUA variants; CPU-only, keep canonical resources and game session intact."""
import sys,json,copy,struct,shutil,subprocess,importlib.util
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import install_renderer_candidate as tx
from workspace_paths import get_path
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('three_install_base','pipeline/recipes/effects-lot50-install-20261108-v1/install.py')
builder=base.builder;transaction=base.transaction
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest
sha=workflow.sha256_file
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
OUT=ROOT/'effects/installations/magic-three-comparisons-20261108-v1'
CANDIDATE=OUT/'candidate';GAME=get_path('bg2ee_game_root',required=True)
PROBE=base.PROBE
transaction.OUT=OUT;transaction.CANDIDATE=CANDIDATE;transaction.GAME=GAME
def probe(target,name):
 with (OUT/name).open('w',encoding='utf-8') as log:subprocess.run([str(PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
transaction.probe=probe
def preserved(before):
 assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
transaction.preserved=preserved
def prepare():
 if (OUT/'plan.json').exists():print('Prepared candidate retained');return
 OUT.mkdir(parents=True,exist_ok=True)
 full={a['resref']:a for a in load(BATCH/'batch.json')['assets']};prod={a['resref']:a for a in load(BATCH/'production-current-v2.json')['assets']}
 parents={n:{**full[n],**prod[n]} for n in ['SPBASEWT','SPENTAXI','SPCSPRAI']}
 # Reuse exact-flux derivation from the preceding accepted lot, new assets/runs only.
 corr=module('three_alpha_pack','pipeline/recipes/effects-lot50-black-transparent-20261108-v1/correct.py')
 corr.OUT=BATCH/'alternatives/black-alpha-check-20261108-v1/packs';corr.OUT.mkdir(parents=True,exist_ok=True)
 original_register=workflow.register_run;workflow.register_run=lambda *args,**kwargs:dict(comparison_only=True,registered=False)
 try:alphas={n:corr.produce(parents[n]) for n in ['SPBASEWT','SPENTAXI']}
 finally:workflow.register_run=original_register
 seed=load(BATCH/'alternatives/spcsprai-seedvr7b-test-20261108-v1/result.json')['asset']
 jobs=[('SPBASEWT','Alpha natif',parents['SPBASEWT'],'M3BASN','Z3BASN',True,False),('SPBASEWT','Noir transparent',alphas['SPBASEWT'],'M3BAST','Z3BAST',True,False),('SPENTAXI','Alpha natif',parents['SPENTAXI'],'M3ENTN','Z3ENTN',True,False),('SPENTAXI','Noir transparent',alphas['SPENTAXI'],'M3ENTT','Z3ENTT',True,False),('SPCSPRAI','xBR4X',parents['SPCSPRAI'],'M3SPCX','Z3SPCX',False,True),('SPCSPRAI','SeedVR7B',seed,'M3SPCS','Z3SPCS',False,True)]
 active=GAME/'iee-assets/effects';old=load(active/'manifest.json');registry=(active/'EffectAnimations-X4.registry').read_bytes();assert digest(registry)==old['registry_sha256'] and old['registry_version']==3
 before=dict(manifest_sha256=sha(active/'manifest.json'),registry_sha256=digest(registry),preserved={n:asdict(tx.snapshot_file(GAME/n)) for n in base.PRESERVED if (GAME/n).is_file()})
 save(OUT/'before.json',before);manifest=copy.deepcopy(old);files=[];records=bytearray();contracts=[];clua=[]
 target=CANDIDATE/'iee-assets/effects';target.mkdir(parents=True,exist_ok=True)
 def add(name,raw=None,source=None):
  assert not (GAME/name).exists() or name in {'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry'},name
  dest=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is None:
   if dest.exists():assert dest.read_bytes()==raw
   else:dest.write_bytes(raw)
  else:
   if not dest.exists():shutil.copy2(source,dest)
   assert tx.snapshot_file(dest)==tx.snapshot_file(source)
  files.append(dict(name=name,**asdict(tx.snapshot_file(dest))))
 for name,label,asset,ref,vvc,straight,blend in jobs:
  a=copy.deepcopy(asset)
  while not a['native_cycles'][-1]['frame_indices']:a['native_cycles'].pop()
  raw,res,frames,copies,checks,m=builder.build_resource(a,ref,straight);records.extend(raw);manifest['resources'].append(res);contracts+=checks
  for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
  for source,file in copies:add('iee-assets/effects/'+file,source=source)
  carrier=ROOT/m['runtime_carrier']['path'];add('override/'+ref+'.bam',source=carrier)
  manifest.setdefault('runtime_bam_carriers',[]).append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=sha(carrier),bytes=carrier.stat().st_size,production_bam=name,policy='Isolated comparison alias, canonical BAM untouched.'))
  loop=next(c for c in m['timing']['cycles'] if c['cycle']==0 and c['loop_closed']);vraw=builder.make_vvc(ref,0,True,15,len(loop['native_slots']),blend);add('override/'+vvc+'.vvc',vraw)
  manifest.setdefault('runtime_vvc_controllers',[]).append(dict(asset='override/'+vvc+'.vvc',bam=ref,sha256=digest(vraw),bytes=len(vraw),purpose='Isolated visual comparison; cycle0, no gameplay changes'))
  clua.append(dict(resref=name,variant=label,vvc=vvc,clua=f'C:Eval(\'CreateVisualEffectObject("{vvc}",Player1)\',0)'))
 assert manifest['resources'][:len(old['resources'])]==old['resources'] and manifest['frames'][:len(old['frames'])]==old['frames']
 reg=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+records
 manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(reg),registry_sha256=digest(reg))
 add('iee-assets/effects/EffectAnimations-X4.registry',reg);add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
 (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii');save(OUT/'clua.json',clua)
 text=['# Trois effets —6comparaisons CLUA','','**Candidat préparé, pas encore installé. Jeu/InfinityLoader doivent être fermés avant installation.**','','Après installation et relance via InfinityLoader : une commande à la fois. Tests visuels sans dégâts, cycle0 répété environ4s.','']
 for c in clua:text+=[c['resref']+' — '+c['variant'],'','```lua',c['clua'],'```','']
 (OUT/'CLUA.md').write_text('\n'.join(text),encoding='utf-8')
 probe(target,'candidate-native-loader.log')
 save(OUT/'plan.json',dict(files=files,count=3,primary_tests=6,runtime_resources=manifest['resource_count'],total_backings=manifest['frame_count'],old_resources_unchanged=old['resource_count'],old_backings_unchanged=old['frame_count'],native_contracts=len(contracts),manifest_sha256=sha(target/'manifest.json'),qa_accepted=False,release_changed=False,gpu_used=False,canonical_assets_unchanged=True,source_production=rel(BATCH/'three-tests-review.json')))
 print('READY6 comparisons;',len(files),'files;',len(contracts),'contracts; game untouched.',flush=True)
def finish():
 receipt=load(OUT/'transaction.json');plan=load(OUT/'plan.json');assert receipt['status']=='installed' and sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];preserved(load(OUT/'before.json'))
 save(OUT/'installation.json',dict(status='installed-offline-verified',transaction=rel(OUT/'transaction.json'),tests=6,canonical_assets_unchanged=True,production_qa_unchanged=True,gpu_used=False))
 p=OUT/'CLUA.md';p.write_text(p.read_text(encoding='utf-8').replace('**Candidat préparé, pas encore installé. Jeu/InfinityLoader doivent être fermés avant installation.**','**Six comparaisons installées ; relancer via InfinityLoader.**'),encoding='utf-8')
 print('INSTALLED6 comparisons; canonical assets and production QA unchanged.',flush=True)
transaction.finish=finish
if __name__=='__main__':
 if sys.argv[-1]=='install':transaction.install()
 else:prepare()
