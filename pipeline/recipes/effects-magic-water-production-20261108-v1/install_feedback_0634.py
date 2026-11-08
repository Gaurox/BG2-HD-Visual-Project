"""CPU-only06 xBR replacement and34 visible-cycle launchers, with RGBA fallback probe."""
import sys,copy,json,struct,shutil,subprocess,importlib.util
from pathlib import Path
from dataclasses import asdict
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow,effect_authority as authority
import install_renderer_candidate as tx
from workspace_paths import get_path
def mod(n,p):
 s=importlib.util.spec_from_file_location(n,ROOT/p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
base=mod('fb0634_base','pipeline/recipes/effects-lot50-install-20261108-v1/install.py');builder=base.builder
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest;sha=workflow.sha256_file
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1';DATA=BATCH/'review-feedback-0634-20261108-v1';OUT=ROOT/'effects/installations/magic-feedback-0634-20261108-v1';CANDIDATE=OUT/'candidate';GAME=get_path('bg2ee_game_root',required=True)
def probe(target,name):
 with (OUT/name).open('w',encoding='utf-8') as f:subprocess.run([str(base.PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],stdout=f,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def preserved(before):assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
def prepare():
 if (OUT/'plan.json').exists():return
 OUT.mkdir(parents=True,exist_ok=True);old=load(GAME/'iee-assets/effects/manifest.json');registry=(GAME/'iee-assets/effects/EffectAnimations-X4.registry').read_bytes();assert digest(registry)==old['registry_sha256'];manifest=copy.deepcopy(old)
 before=dict(manifest_sha256=sha(GAME/'iee-assets/effects/manifest.json'),registry_sha256=digest(registry),preserved={n:asdict(tx.snapshot_file(GAME/n)) for n in base.PRESERVED if (GAME/n).is_file()});save(OUT/'before.json',before);files=[];replace=[];target=CANDIDATE/'iee-assets/effects';target.mkdir(parents=True,exist_ok=True)
 def add(name,raw=None,source=None,overwrite=False):
  assert overwrite or not (GAME/name).exists(),name
  p=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is not None:
   if not p.exists():shutil.copy2(source,p)
   assert tx.snapshot_file(p)==tx.snapshot_file(source)
  elif p.exists():assert p.read_bytes()==raw
  else:p.write_bytes(raw)
  files.append(dict(name=name,**asdict(tx.snapshot_file(p))))
  if overwrite:replace.append(name)
 def controller(name,ref,cycle,slots,overwrite=False):
  raw=bytearray(builder.make_vvc(ref,cycle,True,15,slots,False));struct.pack_into('<I',raw,0x5c,180);add('override/'+name+'.vvc',bytes(raw),overwrite=overwrite)
  entry=dict(asset='override/'+name+'.vvc',bam=ref,sha256=digest(raw),bytes=len(raw),purpose='06 xBR comparison /34 real visible cycle,12s isolated visual test')
  if overwrite:
   previous=next(c for c in manifest['runtime_vvc_controllers'] if c['asset']==entry['asset']);previous.clear();previous.update(entry)
  else:manifest['runtime_vvc_controllers'].append(entry)
 batch=load(BATCH/'batch.json');oldjob=next(a for a in batch['assets'] if a['resref']=='SPARMOR2');fix=load(DATA/'SPARMOR2-result.json');a=fix['asset'];oldstage=ROOT/'effects/ressources/SPARMOR2/runs'/oldjob['interpolation_run']/'02-interpolation';newstage=ROOT/'effects/ressources/SPARMOR2/runs'/a['interpolation_run']/'02-interpolation';m=load(oldstage/'manifest.json');n=load(newstage/'manifest.json');maps={}
 for key in ['raw_rgba_x4','straight_raw_rgba_x4']:
  lookup={}
  for f,g in zip(m['frames'],n['frames']):
   assert f['physical_size_x4']==g['physical_size_x4'] and f['centre_x1']==g['centre_x1'];k=(f[key+'_sha256'],tuple(f['physical_size_x4']));v=(newstage/g[key],g[key+'_sha256']);assert k not in lookup or lookup[k][1]==v[1];lookup.setdefault(k,v)
  maps[key]=lookup
 count=0
 for f in manifest['frames']:
  if f['resref'] not in {'SPARMOR2','XMWN06'}:continue
  key='raw_rgba_x4' if f['resref']=='SPARMOR2' else 'straight_raw_rgba_x4';source,h=maps[key][(f['sha256'],tuple(f['physical_size_x4']))];add('iee-assets/effects/'+f['asset'],source=source,overwrite=True);f.update(sha256=h,source=rel(source));count+=1
 assert count==122
 for r in manifest['resources']:
  if r['resref'] in {'SPARMOR2','XMWN06'}:r.update(interpolation_run=a['interpolation_run'],production_pack=fix['result']['pack'],production_pack_sha256=fix['result']['pack_manifest_sha256'],model='XBR/xbr4X',temporal_model='CPU/ffmpeg-minterpolate-mci')
 contracts=(ROOT/'effects/installations/magic-feedback-0613343545-20261108-v2/runtime-contracts.tsv').read_text(encoding='ascii').splitlines();records=bytearray()
 for asset,ref in [(oldjob,'MFX06S'),(load(DATA/'SPSDRAE2-result.json')['asset'],'MFX34R')]:
  raw,res,frames,copies,checks,tm=builder.build_resource(asset,ref,True);records.extend(raw);manifest['resources'].append(res);contracts+=checks
  for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
  for source,file in copies:add('iee-assets/effects/'+file,source=source)
  carrier=ROOT/tm['runtime_carrier']['path'];add('override/'+ref+'.bam',source=carrier);manifest['runtime_bam_carriers'].append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=sha(carrier),bytes=carrier.stat().st_size,production_bam=asset['resref'],policy='Exact padded carrier from compared stage'))
 controller('ZFX06S','MFX06S',0,40)
 # Original0 is a transparent control, not a visible animation.
 controller('ZMWT34','MWM34',1,50,overwrite=True);controller('ZFR34N','MFR34N',1,50,overwrite=True);controller('ZFR34C','MFR34C',1,50,overwrite=True)
 controller('ZFX34B','MWM34',2,50);controller('ZFX34R','MFX34R',1,50)
 reg=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+records
 manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(reg),registry_sha256=digest(reg));add('iee-assets/effects/EffectAnimations-X4.registry',reg,overwrite=True);add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode(),overwrite=True)
 (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii');probe(target,'candidate-native-loader.log');save(OUT/'plan.json',dict(files=files,allowed_replacements=replace,manifest_sha256=sha(target/'manifest.json'),native_contracts=len(contracts),resources=len(manifest['resources']),backings=len(manifest['frames']),replaced_backings=count,gpu_used=False,qa='pending-user-retest'))
 print('READY06 xBR +34 visible cycles;',count,'backings replaced;',len(contracts),'contracts',flush=True)
def install():
 assert not (OUT/'transaction.json').exists();tx.ensure_game_stopped(tx.running_game_processes);(OUT/'before').mkdir(exist_ok=True);before=load(OUT/'before.json');p=load(OUT/'plan.json');preserved(before);assert sha(GAME/'iee-assets/effects/manifest.json')==before['manifest_sha256'];entries=[]
 for f in p['files']:
  expected=tx.FileSnapshot(f['bytes'],f['sha256']);assert tx.snapshot_file(tx.managed_path(CANDIDATE,f['name']))==expected;target=tx.managed_path(GAME,f['name']);old=tx.optional_snapshot(target)
  if old:assert f['name'] in p['allowed_replacements'];tx.atomic_copy(target,tx.managed_path(OUT/'before',f['name'],create_parents=True),old)
  entries.append({**f,'before':asdict(old) if old else None})
 receipt=dict(status='prepared',game_root=str(GAME),files=entries);tx.write_json_atomic(OUT/'transaction.json',receipt)
 try:
  tx.ensure_game_stopped(tx.running_game_processes)
  for f in entries:
   target=tx.managed_path(GAME,f['name'],create_parents=True);old=tx.FileSnapshot(**f['before']) if f['before'] else None;assert tx.optional_snapshot(target)==old;tx.atomic_copy(tx.managed_path(CANDIDATE,f['name']),target,tx.FileSnapshot(f['bytes'],f['sha256']))
  for f in entries:assert tx.snapshot_file(tx.managed_path(GAME,f['name']))==tx.FileSnapshot(f['bytes'],f['sha256'])
  probe(GAME/'iee-assets/effects','installed-native-loader.log');preserved(before);receipt.update(status='installed',installed_utc=tx.utc_now());tx.write_json_atomic(OUT/'transaction.json',receipt)
 except Exception:
  for f in reversed(entries):
   target=tx.managed_path(GAME,f['name'],create_parents=True)
   if f['before']:tx.atomic_copy(OUT/'before'/f['name'],target,tx.FileSnapshot(**f['before']))
   else:tx.safe_unlink(target,tx.FileSnapshot(f['bytes'],f['sha256']))
  receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt);raise
 with authority.guard(ROOT,write=True):
  rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
  for r in rows:
   if r['asset_key']=='effects:bam:SPARMOR2':r.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
  authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
 save(OUT/'installation.json',dict(status='installed-offline-verified',sparmor2='xBR4X + CPU motion interpolation30, all native anchors/holds retained',spsdrae2='primary corrected to native visible cycle1, cycle2 and RGBA-alpha comparisons added',gpu_used=False,qa='pending-user-retest'));print('INSTALLED06 xBR and34 cycle fix; GPU untouched.',flush=True)
if __name__=='__main__':
 if sys.argv[-1]=='install':install()
 else:prepare()
