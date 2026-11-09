"""Install only the three retained projectile images, their runtime links and QA VVCs."""
from pathlib import Path
from dataclasses import asdict
import copy,importlib.util,json,shutil,struct,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import effect_workflow as w
import effect_authority as authority
import install_renderer_candidate as tx
from compose_effect_runtime_packs import validate_pack
from workspace_paths import get_path
BATCH=ROOT/'effects/batches/projectiles3-production-20261109-v1'
OUT=ROOT/'effects/installations/projectiles3-selected-20261109-v1';CANDIDATE=OUT/'candidate'
GAME=get_path('bg2ee_game_root',required=True)
BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'
PROBE=ROOT/'build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe'
SOURCE=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
spec=importlib.util.spec_from_file_location('projectiles3_resource_builder',ROOT/'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest
sha=w.sha256_file
REPLACED={'InfinityEngine-Enhancer.dll','iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry'}

def snap(p):return asdict(tx.snapshot_file(p))
def clua(ref):return f'C:Eval(\'CreateVisualEffectObject("{ref}",Player1)\',0)'
def assets():
 pointer=load(BATCH/'current-production.json');assert sha(ROOT/pointer['path'])==pointer['sha256']
 current=load(ROOT/pointer['path']);batch={a['resref']:a for a in load(BATCH/'batch.json')['assets']}
 jobs=[{**batch[a['resref']],**a,'native_cycles':batch[a['resref']]['native_cycles']} for a in current['assets']]
 assert {a['resref']:a['selected_version'] for a in jobs}=={'BGLRYU':'SeedVR7B','SPCL236U':'SeedVR7B','SPGLYPHI':'xBR4X'}
 return jobs,pointer

def build_resource(a,ref,normal):
 if not normal:return builder.build_resource(a,ref,False)
 # Use the selected run's already-verified black-neutral straight companion.
 # Historical builder receives a copy in memory; no run/recipe/image is rewritten.
 path=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation/manifest.json'
 m=copy.deepcopy(load(path))
 for f in m['frames']:
  f['straight_raw_rgba_x4']=f['neutral_raw_rgba_x4']
  f['straight_raw_rgba_x4_sha256']=f['neutral_raw_rgba_x4_sha256']
 old=builder.load
 try:
  builder.load=lambda p:m if Path(p)==path else old(p)
  return builder.build_resource(a,ref,True)
 finally:builder.load=old

def probe(target,name):
 with (OUT/name).open('w',encoding='utf-8') as log:subprocess.run([str(PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)

def preserved(before):
 for name,value in before['preserved'].items():assert snap(GAME/name)==value,name
 for name,value in before['owner_overrides'].items():
  value_now=tx.optional_snapshot(GAME/name)
  assert (asdict(value_now) if value_now else None)==value,name

def prepare():
 assert not (OUT/'plan.json').exists(),'Prepared installation is immutable; use its install action or a new version'
 OUT.mkdir(parents=True,exist_ok=True);CANDIDATE.mkdir(exist_ok=True);jobs,pointer=assets()
 log=ROOT/'.tmp/projectiles3-20261109-v1/ingame-tests.log'
 assert '100% tests passed, 0 tests failed out of 5' in log.read_text(encoding='utf-8')
 old=load(GAME/'iee-assets/effects/manifest.json');registry=(GAME/'iee-assets/effects/EffectAnimations-X4.registry').read_bytes()
 assert old['registry_version']==3 and digest(registry)==old['registry_sha256']
 assert not {'BGLRYU','SPCL236U','SPGLYPHI','X3N001','X3N002','X3N003'}&{r['resref'] for r in old['resources']}
 protected=['InfinityEngine-Enhancer.ini','BaldurReal.exe','override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl','iee-assets/creature-sprites/CreatureSprites-XN.catalog','iee-assets/AreaAnimations-X4.registry']
 protected=[n for n in protected if (GAME/n).is_file()]
 owners=[f'override/{n}.pro' for n in ['BGLRY','SPCL236','TRAPGLPN','TRAPGLYP']]
 before=dict(manifest_sha256=sha(GAME/'iee-assets/effects/manifest.json'),registry_sha256=digest(registry),dll=snap(GAME/'InfinityEngine-Enhancer.dll'),preserved={n:snap(GAME/n) for n in protected},owner_overrides={n:(asdict(tx.optional_snapshot(GAME/n)) if tx.optional_snapshot(GAME/n) else None) for n in owners},production_pointer=pointer)
 save(OUT/'before.json',before)
 manifest=copy.deepcopy(old);records=bytearray();files=[];contracts=[];primary=[];profiles=[];normal_controls=[];provenance=[]
 def add(name,raw=None,source=None):
  assert not (GAME/name).exists() or name in REPLACED,name
  dest=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is not None:
   if dest.exists():assert snap(dest)==snap(source)
   else:shutil.copy2(source,dest)
  elif dest.exists():assert dest.read_bytes()==raw
  else:dest.write_bytes(raw)
  files.append(dict(name=name,**snap(dest)))
 def vvc(code,ref,cycle,loop,slots,blended,purpose):
  raw=bytearray(builder.make_vvc(ref,cycle,loop,15,slots,blended))
  if loop:struct.pack_into('<I',raw,0x5c,180) # 12 seconds, no gameplay effect.
  add('override/'+code+'.vvc',bytes(raw));manifest.setdefault('runtime_vvc_controllers',[]).append(dict(asset='override/'+code+'.vvc',bam=ref,sha256=digest(raw),bytes=len(raw),purpose=purpose))
 for number,a in enumerate(jobs,1):
  n=a['resref'];unit=validate_pack(ROOT/a['pack']);assert unit.manifest_sha256==a['pack_manifest_sha256'];normal=f'X3N{number:03d}'
  for ref,is_normal in [(n,False),(normal,True)]:
   raw,res,frames,copies,checks,m=build_resource(a,ref,is_normal)
   res.update(production_pack=a['pack'],production_pack_sha256=unit.manifest_sha256,selected_method=a['selected_version'],alpha_variant='black-neutral-straight' if is_normal else 'native-premultiplied',owner_contract='INI multiply_blend=1; normal-profile companion selected only for normal draw flags')
   records.extend(raw);manifest['resources'].append(res);contracts+=checks
   for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
   for source,name in copies:add('iee-assets/effects/'+name,source=source)
   carrier=ROOT/m['runtime_carrier']['path'];assert sha(carrier)==m['runtime_carrier']['sha256'];add('override/'+ref+'.bam',source=carrier)
   manifest.setdefault('runtime_bam_carriers',[]).append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=sha(carrier),bytes=carrier.stat().st_size,production_bam=n,policy='Native pixels, palette, cycles and world anchors; transparent padding only.'))
  for profile in m['timing']['cycles']:
   code=f'ZP3P{len(profiles)+1:04d}';vvc(code,n,profile['cycle'],profile['loop_closed'],len(profile['native_slots']),True,'projectiles3 selected isolated profile')
   profiles.append(dict(resref=n,profile=profile['id'],vvc=code,clua=clua(code)))
  profile=next(p for p in m['timing']['cycles'] if p['cycle']==0 and p['loop_closed'])
  code=f'ZP3T{number:02d}';vvc(code,n,0,True,len(profile['native_slots']),True,'projectiles3 main visual test: retained spatial version, luminous native blend')
  primary.append(dict(resref=n,version=a['selected_version'],vvc=code,clua=clua(code)))
  code=f'ZP3N{number:02d}';vvc(code,normal,0,True,len(profile['native_slots']),False,'projectiles3 black-neutral normal transparency comparison')
  normal_controls.append(dict(resref=n,version=a['selected_version'],vvc=code,clua=clua(code)))
  provenance.append(dict(resref=n,version=a['selected_version'],normal_alias=normal,pack=a['pack'],pack_manifest_sha256=unit.manifest_sha256,spatial_run=a['spatial_run'],interpolation_run=a['interpolation_run']))
 assert len(primary)==3 and len(profiles)==14 and len(contracts)==1440
 assert manifest['resources'][:old['resource_count']]==old['resources'] and manifest['frames'][:old['frame_count']]==old['frames']
 reg=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+records
 assert reg[24:len(registry)]==registry[24:]
 manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(reg),registry_sha256=digest(reg));manifest.setdefault('source_packs',[]).extend(provenance)
 add('iee-assets/effects/EffectAnimations-X4.registry',reg);add('iee-assets/effects/manifest.json',w.json_bytes(manifest))
 add('InfinityEngine-Enhancer.dll',source=BUILD/'Release/InfinityEngine-Enhancer.dll')
 (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii');shutil.copy2(log,OUT/'engine-tests.log')
 probe(CANDIDATE/'iee-assets/effects','candidate-native-loader.log')
 save(OUT/'clua.json',primary);save(OUT/'clua-all-profiles.json',profiles);save(OUT/'clua-normal.json',normal_controls)
 source_names=['src/iee/hooks.cpp','src/iee/core/effect_secondary_scope.h','src/iee/core/effect_texture_alias.h','tests/effect_surface_owner_tests.cpp']
 save(OUT/'plan.json',dict(files=files,production=provenance,old_resources=old['resource_count'],old_backings=old['frame_count'],new_resources=6,new_backings=manifest['frame_count']-old['frame_count'],resources=manifest['resource_count'],backings=manifest['frame_count'],manifest_sha256=sha(CANDIDATE/'iee-assets/effects/manifest.json'),new_dll=snap(CANDIDATE/'InfinityEngine-Enhancer.dll'),native_contracts=len(contracts),source_sha256={n:sha(SOURCE/n) for n in source_names},tests=rel(OUT/'engine-tests.log'),no_inference=True,no_release=True,ingame_qa=False))
 lines=['# Projectiles3 — CLUA après relance via InfinityLoader','','## Tests visuels isolés, sans dégâts','','Une commande à la fois, dépausé ; chaque boucle dure12secondes. Ces tests vérifient les images et la transparence, pas le trajet/les conditions des PRO.','']
 for c in primary:lines += [f"### {c['resref']} — {c['version']}",'','```lua',c['clua'],'```','']
 lines += ['## Vrais sorts / propriétaires natifs','','Partie de test non sauvegardée ; cible vivante éloignée. Ces sorts peuvent infliger des dégâts.','', '```lua','-- BGLRY / BGLRYU : Éclair de gloire','C:Eval(\'ForceSpellRES("SPPR612",Player2)\',0)','-- SPCL236 / SPCL236U : Rayon solaire','C:Eval(\'ForceSpellRES("SPCL236",Player2)\',0)','-- TRAPGLYP / SPGLYPHI : Glyphe de garde','C:Eval(\'ForceSpellRES("SPPR304",Player2)\',0)','```','','Glyphe : apparition des fragments au déclenchement ; placer le glyphe puis faire entrer un ennemi vivant dans sa zone. TRAPGLPN partage la même image, sans sort stock direct identifié.','', '## Comparaisons alpha normal','','À utiliser seulement si la transparence du test principal pose problème.','', '```lua']+[c['clua'] for c in normal_controls]+['```','','Les14profils : [CLUA-tous-profils.md](CLUA-tous-profils.md).']
 (OUT/'CLUA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 (OUT/'CLUA-tous-profils.md').write_text('# Projectiles3 — profils isolés\n\n'+''.join(f"## {c['resref']} / {c['profile']}\n\n```lua\n{c['clua']}\n```\n\n" for c in profiles),encoding='utf-8')
 print('READY: 3 selected images +3 normal companions;',len(files),'targets;',manifest['resource_count'],'resources;',len(contracts),'contracts',flush=True)

def rollback(receipt):
 for item in reversed(receipt['files']):
  target=tx.managed_path(GAME,item['name'],create_parents=True);current=tx.optional_snapshot(target)
  expected=tx.FileSnapshot(item['bytes'],item['sha256']);old=tx.FileSnapshot(**item['before']) if item['before'] else None
  assert current in (old,expected),target
  if current==old:continue
  if old:tx.atomic_copy(tx.managed_path(OUT/'before',item['name']),target,old)
  else:tx.safe_unlink(target,expected)
 receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt)

def install():
 assert not (OUT/'transaction.json').exists(),'Installation already recorded; inspect instead of replaying'
 (OUT/'before').mkdir(exist_ok=True)
 before=load(OUT/'before.json');plan=load(OUT/'plan.json');tx.ensure_game_stopped(tx.running_game_processes);preserved(before)
 assert snap(GAME/'InfinityEngine-Enhancer.dll')==before['dll']
 for f in ['manifest.json','EffectAnimations-X4.registry']:assert sha(GAME/'iee-assets/effects'/f)==before['manifest_sha256' if f=='manifest.json' else 'registry_sha256']
 for n,h in plan['source_sha256'].items():assert sha(SOURCE/n)==h,n
 entries=[]
 for item in plan['files']:
  expected=tx.FileSnapshot(item['bytes'],item['sha256']);assert tx.snapshot_file(tx.managed_path(CANDIDATE,item['name']))==expected
  target=tx.managed_path(GAME,item['name']);old=tx.optional_snapshot(target)
  if old:
   assert item['name'] in REPLACED;tx.atomic_copy(target,tx.managed_path(OUT/'before',item['name'],create_parents=True),old)
  entries.append({**item,'before':asdict(old) if old else None})
 receipt=dict(schema='bg2-projectiles-selected-delta-transaction-v1',status='prepared',game_root=str(GAME),candidate_root=rel(CANDIDATE),created_utc=tx.utc_now(),files=entries)
 tx.write_json_atomic(OUT/'transaction.json',receipt)
 try:
  tx.ensure_game_stopped(tx.running_game_processes);receipt['status']='installing';tx.write_json_atomic(OUT/'transaction.json',receipt)
  for item in entries:
   target=tx.managed_path(GAME,item['name'],create_parents=True);old=tx.FileSnapshot(**item['before']) if item['before'] else None
   assert tx.optional_snapshot(target)==old
   tx.atomic_copy(tx.managed_path(CANDIDATE,item['name']),target,tx.FileSnapshot(item['bytes'],item['sha256']))
  for item in entries:assert tx.snapshot_file(tx.managed_path(GAME,item['name']))==tx.FileSnapshot(item['bytes'],item['sha256'])
  preserved(before);probe(GAME/'iee-assets/effects','installed-native-loader.log')
  receipt.update(status='installed',installed_utc=tx.utc_now());tx.write_json_atomic(OUT/'transaction.json',receipt)
 except Exception:rollback(receipt);raise
 finish()

def finish():
 receipt=load(OUT/'transaction.json');plan=load(OUT/'plan.json');assert receipt['status']=='installed';preserved(load(OUT/'before.json'))
 assert sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];assert snap(GAME/'InfinityEngine-Enhancer.dll')==plan['new_dll']
 with authority.guard(ROOT,True):
  rows=w.read_csv(ROOT/'effects/index/processing.csv');save(OUT/'processing-before.json',rows)
  for row in rows:
   if row['asset_key'].rsplit(':',1)[-1] in {'BGLRYU','SPCL236U','SPGLYPHI'}:row.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
  authority.commit(ROOT,{'effects/index/processing.csv':w.csv_bytes(rows)})
 save(OUT/'installation.json',dict(status='installed-awaiting-ingame-review',transaction=rel(OUT/'transaction.json'),versions={a['resref']:a['version'] for a in plan['production']},dll=plan['new_dll'],resources=plan['resources'],backings=plan['backings'],old_resources_preserved=plan['old_resources'],old_backings_preserved=plan['old_backings'],native_contracts_candidate_and_installed=plan['native_contracts']*2,engine_tests='5/5 passed',game_and_loader_stopped=True,game_launched=False,owner_PRO_INI_preserved=True,release_changed=False,gpu_inference=False,ingame_accepted=False))
 (OUT/'README.md').write_text('# Projectiles3 installés pour test —2026-11-09\n\n- BGLRYU/SPCL236U SeedVR7B ; SPGLYPHI xBR4X ; Apollo30. CLUA principales ZP3T01/02/03 dans `CLUA.md`.\n- 3noms natifs +3compagnons normaux noirs neutres ;14profils isolés +3comparaisons de transparence. DLL compilée avec whitelist et routage par blend ; INI/PRO/sorts natifs/personnages/cartes conservés.\n- Reçu réversible `transaction.json`, sauvegardes `before/`. Ancien catalogue inchangé, nouvelles textures seules copiées ; aucune QA ingame/release inférée.\n- Restauration ciblée : `python -B pipeline/recipes/projectiles3-production-20261109-v1/install_ingame.py restore`, jeu/loader arrêtés.\n',encoding='utf-8')
 print('INSTALLED: BGLRYU/ SPCL236U SeedVR; SPGLYPHI xBR. CLUA ZP3T01..03; game not launched.',flush=True)

def restore():
 tx.ensure_game_stopped(tx.running_game_processes);rollback(load(OUT/'transaction.json'))
 previous={r['asset_key']:r for r in load(OUT/'processing-before.json')}
 with authority.guard(ROOT,True):
  rows=w.read_csv(ROOT/'effects/index/processing.csv')
  for row in rows:
   if row['installation_receipt']==rel(OUT/'transaction.json'):
    for k in ['installation_state','installation_receipt']:row[k]=previous[row['asset_key']][k]
  authority.commit(ROOT,{'effects/index/processing.csv':w.csv_bytes(rows)})
 print('Restored installation delta and three tracking installation fields.')

if __name__=='__main__':{'prepare':prepare,'install':install,'restore':restore}[sys.argv[1]]()
