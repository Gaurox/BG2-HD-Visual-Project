"""Full50 review installation:44 produced sources +6 native masks,6 targeted comparisons."""
import sys,copy,json,struct,shutil,subprocess,importlib.util
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow
import effect_authority as authority
import install_renderer_candidate as tx
from workspace_paths import get_path
from compose_effect_runtime_packs import validate_pack
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('magic_install_base','pipeline/recipes/effects-lot50-install-20261108-v1/install.py')
builder,transaction=base.builder,base.transaction
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest
sha=workflow.sha256_file
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1'
OUT=ROOT/'effects/installations/magic-water50-20261108-v1';CANDIDATE=OUT/'candidate';GAME=get_path('bg2ee_game_root',required=True)
THREE=ROOT/'effects/installations/magic-three-comparisons-20261108-v1'
transaction.OUT=OUT;transaction.CANDIDATE=CANDIDATE;transaction.GAME=GAME
def command(vvc):return f'C:Eval(\'CreateVisualEffectObject("{vvc}",Player1)\',0)'
def probe(target,name):
 with (OUT/name).open('w',encoding='utf-8') as log:subprocess.run([str(base.PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
transaction.probe=probe
def preserved(before):assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
transaction.preserved=preserved
def assets():
 batch=load(BATCH/'batch.json');parents={a['resref']:a for a in batch['assets']};current=load(BATCH/'production-current-v2.json')
 jobs=[]
 for r in current['assets']:
  a={**parents[r['resref']],**r}
  if a['resref'] in {'SPBASEWT','SPENTAXI'}:a.update(load(BATCH/'alternatives/black-alpha-check-20261108-v1/packs/verification'/f"{a['resref']}.json"))
  jobs.append(a)
 return jobs,batch['native_masks']
def prepare():
 if (OUT/'plan.json').exists():print('Prepared full50 candidate retained');return
 OUT.mkdir(parents=True,exist_ok=True);jobs,masks=assets();assert len(jobs)==44 and len(masks)==6
 active=GAME/'iee-assets/effects';old=load(active/'manifest.json');registry=(active/'EffectAnimations-X4.registry').read_bytes();assert old['registry_version']==3 and digest(registry)==old['registry_sha256']
 assert not {a['resref'] for a in jobs}&{r['resref'] for r in old['resources']}
 paths=[n for n in base.PRESERVED if (GAME/n).is_file()];paths += [str(p.relative_to(GAME)) for p in (GAME/'iee-assets/areas').glob('*/AreaAnimations-X4.registry')]
 before=dict(manifest_sha256=sha(active/'manifest.json'),registry_sha256=digest(registry),preserved={n:asdict(tx.snapshot_file(GAME/n)) for n in paths})
 save(OUT/'before.json',before);manifest=copy.deepcopy(old);files=[];records=bytearray();contracts=[];clua=[];profiles=[];controls=[];provenance=[]
 target=CANDIDATE/'iee-assets/effects';target.mkdir(parents=True,exist_ok=True)
 def add(name,raw=None,source=None):
  assert not (GAME/name).exists() or name in {'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry'},name
  dest=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is not None:
   if not dest.exists():shutil.copy2(source,dest)
   assert tx.snapshot_file(dest)==tx.snapshot_file(source)
  elif dest.exists():assert dest.read_bytes()==raw
  else:dest.write_bytes(raw)
  files.append(dict(name=name,**asdict(tx.snapshot_file(dest))))
 def vvc(name,ref,raw,purpose):
  add('override/'+name+'.vvc',raw)
  manifest.setdefault('runtime_vvc_controllers',[]).append(dict(asset='override/'+name+'.vvc',bam=ref,sha256=digest(raw),bytes=len(raw),purpose=purpose))
 for asset in jobs:
  a=copy.deepcopy(asset);name=a['resref'];number=a['ordinal'];unit=validate_pack(ROOT/a['pack']);assert unit.manifest_sha256==a['pack_manifest_sha256']
  sourcecycles=copy.deepcopy(a['native_cycles'])
  while not a['native_cycles'][-1]['frame_indices']:a['native_cycles'].pop()
  normal=f'XMWN{number:02d}'
  for ref,straight in [(name,False),(normal,True)]+[(alias,False) for alias in a.get('reuse_aliases',[])]:
   raw,res,frames,copies,checks,m=builder.build_resource(a,ref,straight);res.update(native_source_cycles=sourcecycles,production_pack=a['pack'],production_pack_sha256=unit.manifest_sha256)
   records.extend(raw);manifest['resources'].append(res);contracts+=checks
   for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
   for source,file in copies:add('iee-assets/effects/'+file,source=source)
   carrier=ROOT/m['runtime_carrier']['path'];add('override/'+ref+'.bam',source=carrier)
   manifest.setdefault('runtime_bam_carriers',[]).append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=sha(carrier),bytes=carrier.stat().st_size,production_bam=name,policy='Native world indexed geometry retained, inherited transparent padding.'))
  light=a['profile']=='H' and name not in {'SPBASEWT','SPENTAXI'};primary=name if light else normal
  if name=='SPCSPRAI':primary='M3SPCS';light=True
  for p in m['timing']['cycles']:
   code=f'ZMWP{len(profiles)+1:04d}';vvc(code,primary,builder.make_vvc(primary,p['cycle'],p['loop_closed'],15,len(p['native_slots']),light),'magic50 isolated native profile')
   profiles.append(dict(resref=name,profile=p['id'],vvc=code,clua=command(code)))
  p=next(p for p in m['timing']['cycles'] if p['cycle']==0 and p['loop_closed']);code=f'ZMWT{number:02d}';vvc(code,primary,builder.make_vvc(primary,0,True,15,len(p['native_slots']),light),'magic50 primary isolated visual test, no damage')
  clua.append(dict(ordinal=number,resref=name,variant='SeedVR test' if name=='SPCSPRAI' else 'transparent alpha' if name in {'SPBASEWT','SPENTAXI'} else a['method'],vvc=code,clua=command(code)))
  for tag,ref,blend in [('N',normal,False),('B',name,True)]:
   code=f'ZMW{tag}{number:02d}';vvc(code,ref,builder.make_vvc(ref,0,True,15,len(p['native_slots']),blend),'magic50 normal/luminous comparison');controls.append(dict(resref=name,variant='luminous' if blend else 'normal',vvc=code,clua=command(code)))
  provenance.append(dict(resref=name,pack=a['pack'],pack_manifest_sha256=unit.manifest_sha256,spatial_run=a['spatial_run'],interpolation_run=a['interpolation_run'],normal_alias=normal,qa='pending-user-ingame'))
  print(name,'prepared',flush=True)
 for a in masks:
  n=a['resref'];number=a['ordinal'];ref=f'MWM{number:02d}';add('override/'+ref+'.bam',source=ROOT/a['source']);p=next(c for c in a['native_cycles'] if c['cycle']==0);code=f'ZMWT{number:02d}'
  vvc(code,ref,builder.make_vvc(ref,0,True,15,len(p['frame_indices']),False),'Native mask copied without AI or HD registry; canonical original unchanged')
  manifest.setdefault('runtime_bam_carriers',[]).append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=sha(ROOT/a['source']),bytes=(ROOT/a['source']).stat().st_size,production_bam=n,policy='Exact unmodified native BAM; no new interpolation.'))
  clua.append(dict(ordinal=number,resref=n,variant='native mask preserved',vvc=code,clua=command(code)))
 # Merge the already-verified six comparisons, including both versions of SPCSPRAI.
 threebefore=load(THREE/'before.json');assert threebefore['manifest_sha256']==before['manifest_sha256']
 tm=load(THREE/'candidate/iee-assets/effects/manifest.json');tr=(THREE/'candidate/iee-assets/effects/EffectAnimations-X4.registry').read_bytes()
 records.extend(tr[len(registry):]);manifest['resources']+=copy.deepcopy(tm['resources'][old['resource_count']:])
 for f in copy.deepcopy(tm['frames'][old['frame_count']:]):f['frame']=len(manifest['frames']);manifest['frames'].append(f)
 for k in ['runtime_vvc_controllers','runtime_bam_carriers']:manifest.setdefault(k,[]).extend(copy.deepcopy(tm[k][len(old.get(k,[])):]))
 for item in load(THREE/'plan.json')['files']:
  if item['name'] not in {'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry'}:add(item['name'],source=THREE/'candidate'/item['name'])
 contracts+=(THREE/'runtime-contracts.tsv').read_text(encoding='ascii').splitlines()
 assert len(clua)==50 and len(profiles)==140
 assert manifest['resources'][:len(old['resources'])]==old['resources'] and manifest['frames'][:len(old['frames'])]==old['frames']
 reg=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+records;assert reg[24:len(registry)]==registry[24:]
 manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(reg),registry_sha256=digest(reg));manifest.setdefault('source_packs',[]).extend(provenance)
 add('iee-assets/effects/EffectAnimations-X4.registry',reg);add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
 (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii');clua.sort(key=lambda r:r['ordinal']);save(OUT/'clua.json',clua);save(OUT/'clua-all-profiles.json',profiles);save(OUT/'clua-controls.json',controls);save(OUT/'clua-three-comparisons.json',load(THREE/'clua.json'))
 lines=['# Magie/eau50 — CLUA','','**À utiliser après installation et relance via InfinityLoader.** Une commande à la fois ; boucle courte sans dégâts. Ordre identique à la planche50.','SPBASEWT/SPENTAXI : alpha transparent ; SPCSPRAI : test SeedVR.6masques natifs inchangés.','', '```lua']+[c['clua'] for c in clua]+['```','','## Correspondance','','| # | Effet | Version |','|---|---|---|']+[f"| {c['ordinal']:02d} | {c['resref']} | {c['variant']} |" for c in clua]
 (OUT/'CLUA.md').write_text('\n'.join(lines)+'\n',encoding='utf-8');probe(target,'candidate-native-loader.log')
 save(OUT/'plan.json',dict(files=files,count=50,primary_tests=50,profiles=140,comparisons=6,old_resources_unchanged=old['resource_count'],old_backings_unchanged=old['frame_count'],runtime_resources=manifest['resource_count'],total_backings=manifest['frame_count'],native_contracts=len(contracts),manifest_sha256=sha(target/'manifest.json'),gpu_used=False,qa_accepted=False,release_changed=False,production_sources=provenance,native_masks_preserved=[a['resref'] for a in masks]))
 print('READY full50;',len(files),'files;',manifest['resource_count'],'resources;',len(contracts),'contracts',flush=True)
def finish():
 receipt=load(OUT/'transaction.json');plan=load(OUT/'plan.json');assert receipt['status']=='installed' and sha(GAME/'iee-assets/effects/manifest.json')==plan['manifest_sha256'];preserved(load(OUT/'before.json'))
 jobs,masks=assets();names={a['resref'] for a in jobs}|{alias for a in jobs for alias in a.get('reuse_aliases',[])}
 with authority.guard(ROOT,write=True):
  rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS);save(OUT/'processing-before.json',rows)
  for r in rows:
   if r['asset_key'].rsplit(':',1)[-1] in names:r.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
  authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
 save(OUT/'installation.json',dict(status='installed-offline-verified',transaction=rel(OUT/'transaction.json'),primary_tests=50,new_production_sources=44,native_masks_preserved=6,comparisons=6,game_and_loader_stopped=True,game_launched=False,gpu_used=False,qa_accepted=False,release_changed=False))
 comparisons=load(OUT/'clua-three-comparisons.json');lines=['# Comparaisons des trois effets','','Installées dans le lot50 ; relancer via InfinityLoader. Une commande à la fois, sans dégâts.','']
 for c in comparisons:lines += [c['resref']+' — '+c['variant'],'','```lua',c['clua'],'```','']
 (OUT/'CLUA-comparaisons.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 (OUT/'README.md').write_text('# Magie/eau50 installé pour test\n\n50CLUA dans `CLUA.md`, ordre de la planche ;44productions x4/30FPS +6masques natifs préservés ;6comparaisons ciblées.\n\nSPBASEWT/SPENTAXI alpha transparent, SPCSPRAI test SeedVR en test principal (xBR conservé comme production et comparaison).\n\nAnciennes ressources/backings, DLL/INI/shaders/cartes/personnages conservés. Réception `transaction.json` ; QA utilisateur et release inchangées. GPU en pause, installation CPU seule.\n',encoding='utf-8')
 print('INSTALLED full50; CLUA ZMWT01..ZMWT50;6comparisons; QA pending.',flush=True)
transaction.finish=finish
if __name__=='__main__':
 if sys.argv[-1]=='install':transaction.install()
 else:prepare()
