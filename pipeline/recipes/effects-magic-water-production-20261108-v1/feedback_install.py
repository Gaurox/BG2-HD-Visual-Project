"""CPU feedback delta: WHIRLY green repair, native06 comparison, mask visibility probes."""
import sys,copy,json,struct,shutil,subprocess,importlib.util
from pathlib import Path
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import effect_workflow as workflow,effect_authority as authority
import install_renderer_candidate as tx
from workspace_paths import get_path
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam
def module(name,p):
 spec=importlib.util.spec_from_file_location(name,ROOT/p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('feedback_install_base','pipeline/recipes/effects-lot50-install-20261108-v1/install.py');builder=base.builder
load,save,rel,digest=builder.load,builder.save,builder.rel,builder.digest;sha=workflow.sha256_file
BATCH=ROOT/'effects/batches/lot50-magic-water-production-20261108-v1';FEEDBACK=BATCH/'review-feedback-20261108-v1'
OUT=ROOT/'effects/installations/magic-feedback-0613343545-20261108-v2';CANDIDATE=OUT/'candidate';GAME=get_path('bg2ee_game_root',required=True)
def probe(target,name):
 with (OUT/name).open('w',encoding='utf-8') as log:subprocess.run([str(base.PROBE),'--catalogue-only',str(target),str(OUT/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def preserved(before):assert all(asdict(tx.snapshot_file(GAME/n))==v for n,v in before['preserved'].items())
def native_bam(name,color=None,scale=1,dx=0):
 raw=read_bam(ROOT/'effects/ressources'/name/'source.bam');frames,pal,tr=decode_bam(raw);cycles=cycle_metadata(raw,len(frames));count,cc,_=struct.unpack_from('<HBB',raw,8);of,op,ol=struct.unpack_from('<III',raw,12)
 palette=bytearray(raw[op:op+1024])
 if color:
  for i in range(256):
   if i!=tr:palette[i*4:i*4+3]=bytes(reversed(color))
 lookupcount=max(c['lookup_start']+len(c['frame_indices']) for c in cycles);lookup=raw[ol:ol+lookupcount*2];ct=raw[of+count*12:of+count*12+cc*4];nf=24;npal=nf+count*12+len(ct);nl=npal+1024;cursor=nl+len(lookup);table=bytearray();pixels=[]
 for idx,cx,cy,_ in frames:
  arr=idx.repeat(scale,0).repeat(scale,1);h,w=arr.shape;table.extend(struct.pack('<HHhhI',w,h,cx*scale-dx,cy*scale,cursor|0x80000000));pixels.append(arr.tobytes());cursor+=arr.size
 return struct.pack('<8sHBBIII',b'BAM V1  ',count,cc,tr,nf,npal,nl)+table+ct+palette+lookup+b''.join(pixels)
def prepare():
 if (OUT/'plan.json').exists():print('Feedback candidate retained');return
 OUT.mkdir(parents=True,exist_ok=True);active=GAME/'iee-assets/effects';old=load(active/'manifest.json');registry=(active/'EffectAnimations-X4.registry').read_bytes();assert digest(registry)==old['registry_sha256']
 before=dict(manifest_sha256=sha(active/'manifest.json'),registry_sha256=digest(registry),preserved={n:asdict(tx.snapshot_file(GAME/n)) for n in base.PRESERVED if (GAME/n).is_file()});save(OUT/'before.json',before)
 manifest=copy.deepcopy(old);files=[];allowed=[];target=CANDIDATE/'iee-assets/effects';target.mkdir(parents=True,exist_ok=True)
 def add(name,raw=None,source=None,replace=False):
  assert replace or not (GAME/name).exists(),name
  dest=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is not None:
   if not dest.exists():shutil.copy2(source,dest)
   assert tx.snapshot_file(dest)==tx.snapshot_file(source)
  elif dest.exists():assert dest.read_bytes()==raw
  else:dest.write_bytes(raw)
  files.append(dict(name=name,**asdict(tx.snapshot_file(dest))))
  if replace:allowed.append(name)
 def vvc(code,ref,slots=30):
  raw=builder.make_vvc(ref,0,True,15,slots,False);add('override/'+code+'.vvc',raw);manifest.setdefault('runtime_vvc_controllers',[]).append(dict(asset='override/'+code+'.vvc',bam=ref,sha256=digest(raw),bytes=len(raw),purpose='Feedback comparison/visibility test, no gameplay'))
 def native(ref,name,**options):
  raw=native_bam(name,**options);add('override/'+ref+'.bam',raw);manifest.setdefault('runtime_bam_carriers',[]).append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=digest(raw),bytes=len(raw),production_bam=name,policy='Native source diagnostic only; '+str(options)))
 batch=load(BATCH/'batch.json');orig=next(a for a in batch['assets'] if a['resref']=='WHIRLY');fix=load(FEEDBACK/'whirly-correction-final.json');a=fix['asset'];newstage=ROOT/'effects/ressources/WHIRLY/runs'/a['interpolation_run']/'02-interpolation';new=load(newstage/'manifest.json');oldstage=ROOT/'effects/ressources/WHIRLY/runs'/orig['interpolation_run']/'02-interpolation';oldm=load(oldstage/'manifest.json')
 maps={}
 for key in ['raw_rgba_x4','straight_raw_rgba_x4']:
  mapping={}
  for f,g in zip(oldm['frames'],new['frames']):
   ident=(f[key+'_sha256'],tuple(f['physical_size_x4']));value=(newstage/g[key],g[key+'_sha256']);assert ident not in mapping or mapping[ident][1]==value[1];mapping.setdefault(ident,value)
  maps[key]=mapping
 touched=0
 for f in manifest['frames']:
  if f['resref'] not in {'WHIRLY','XMWN13'}:continue
  key='raw_rgba_x4' if f['resref']=='WHIRLY' else 'straight_raw_rgba_x4';src,newsha=maps[key][(f['sha256'],tuple(f['physical_size_x4']))];assert sha(src)==newsha
  add('iee-assets/effects/'+f['asset'],source=src,replace=True);f.update(sha256=newsha,source=rel(src));touched+=1
 assert touched==50,touched
 for r in manifest['resources']:
  if r['resref'] in {'WHIRLY','XMWN13'}:r.update(interpolation_run=a['interpolation_run'],production_pack=fix['result']['pack'],production_pack_sha256=fix['result']['pack_manifest_sha256'],alpha_revision='enclosed green key + mixed-edge matte + SeedVR green despill; CPU-only')
 # Retain the old installed appearance under a new alias for comparison.
 raw,res,frames,copies,contracts,m=builder.build_resource(orig,'MFR13B',True);manifest['resources'].append(res)
 for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
 for src,file in copies:add('iee-assets/effects/'+file,source=src)
 carrier=ROOT/oldm['runtime_carrier']['path'];add('override/MFR13B.bam',source=carrier);manifest.setdefault('runtime_bam_carriers',[]).append(dict(resref='MFR13B',asset='override/MFR13B.bam',sha256=sha(carrier),bytes=carrier.stat().st_size,production_bam='WHIRLY',policy='Old HD comparison uses exact padded carrier, not unpadded source.'));vvc('ZFR13B','MFR13B',12)
 native('MFR06O','SPARMOR2');vvc('ZFR06O','MFR06O',40);vvc('ZFR06N','XMWN06',40)
 for number,name in [(34,'SPSDRAE2'),(35,'SPSHADOW')]:
  native(f'MFR{number}N',name,dx=100);vvc(f'ZFR{number}N',f'MFR{number}N')
  native(f'MFR{number}C',name,color=(255,60,60),scale=4 if number==35 else 1,dx=100);vvc(f'ZFR{number}C',f'MFR{number}C')
 native('MFR45O','WTRBODY2');vvc('ZFR45O','MFR45O',10);vvc('ZFR45N','XMWN45',10)
 reg=struct.pack('<8sIIII',b'IEEEFX4\0',3,4,len(manifest['resources']),0)+registry[24:]+raw
 manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(reg),registry_sha256=digest(reg));manifest.setdefault('runtime_corrections',[]).append(dict(source='WHIRLY green repair',run=a['interpolation_run'],qa='pending-user-retest',gpu_used=False))
 add('iee-assets/effects/EffectAnimations-X4.registry',reg,replace=True);add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode(),replace=True)
 prior=ROOT/'effects/installations/magic-water50-20261108-v1/runtime-contracts.tsv';contracts=prior.read_text(encoding='ascii').splitlines()+contracts;(OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii');probe(target,'candidate-native-loader.log')
 save(OUT/'plan.json',dict(files=files,allowed_replacements=allowed,manifest_sha256=sha(target/'manifest.json'),native_contracts=len(contracts),corrected_resource_refs=['WHIRLY','XMWN13'],source_pixels_timing_centres_retained=True,new_comparison_resource='MFR13B',resources=len(manifest['resources']),backings=len(manifest['frames']),gpu_used=False,qa_accepted=False,release_changed=False))
 print('READY feedback:',touched,'corrected backings;',len(files),'targets;',len(contracts),'contracts',flush=True)
def rollback(receipt):
 for item in reversed(receipt['files']):
  target=tx.managed_path(GAME,item['name'],create_parents=True);old=tx.FileSnapshot(**item['before']) if item['before'] else None
  if old:tx.atomic_copy(OUT/'before'/item['name'],target,old)
  else:tx.safe_unlink(target,tx.FileSnapshot(item['bytes'],item['sha256']))
 receipt['status']='restored';tx.write_json_atomic(OUT/'transaction.json',receipt)
def install():
 assert not (OUT/'transaction.json').exists();tx.ensure_game_stopped(tx.running_game_processes);(OUT/'before').mkdir(exist_ok=True);before=load(OUT/'before.json');plan=load(OUT/'plan.json');preserved(before);assert sha(GAME/'iee-assets/effects/manifest.json')==before['manifest_sha256'];entries=[]
 for item in plan['files']:
  expected=tx.FileSnapshot(item['bytes'],item['sha256']);assert tx.snapshot_file(tx.managed_path(CANDIDATE,item['name']))==expected;target=tx.managed_path(GAME,item['name']);old=tx.optional_snapshot(target)
  if old:
   assert item['name'] in plan['allowed_replacements'];tx.atomic_copy(target,tx.managed_path(OUT/'before',item['name'],create_parents=True),old)
  entries.append({**item,'before':asdict(old) if old else None})
 receipt=dict(schema='bg2-effects-feedback-transaction-v1',status='prepared',game_root=str(GAME),files=entries);tx.write_json_atomic(OUT/'transaction.json',receipt)
 try:
  tx.ensure_game_stopped(tx.running_game_processes)
  for item in entries:
   target=tx.managed_path(GAME,item['name'],create_parents=True);old=tx.FileSnapshot(**item['before']) if item['before'] else None;assert tx.optional_snapshot(target)==old;tx.atomic_copy(tx.managed_path(CANDIDATE,item['name']),target,tx.FileSnapshot(item['bytes'],item['sha256']))
  for item in entries:assert tx.snapshot_file(tx.managed_path(GAME,item['name']))==tx.FileSnapshot(item['bytes'],item['sha256'])
  probe(GAME/'iee-assets/effects','installed-native-loader.log');preserved(before);receipt.update(status='installed',installed_utc=tx.utc_now());tx.write_json_atomic(OUT/'transaction.json',receipt)
 except Exception:rollback(receipt);raise
 with authority.guard(ROOT,write=True):
  rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
  for row in rows:
   if row['asset_key']=='effects:bam:WHIRLY':row.update(installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
  authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
 save(OUT/'installation.json',dict(status='installed-offline-verified',corrected='WHIRLY',comparison_original='SPARMOR2',visibility_probes=['SPSDRAE2','SPSHADOW'],water_context='AR0502 usesWTRBODY1 only, WTRBODY2 native placement unconfirmed',gpu_used=False,qa='pending-user-retest'))
 print('INSTALLED feedback; GPU untouched; QA pending.',flush=True)
if __name__=='__main__':
 if sys.argv[-1]=='install':install()
 else:prepare()
