"""Append WRITHING's already-produced straight/native-alpha companion, DLL+delta transaction."""
from pathlib import Path
from dataclasses import asdict
import copy,hashlib,importlib.util,json,os,re,shutil,struct,subprocess,sys
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
import install_renderer_candidate as tx
GAME=tx.get_path('bg2ee_game_root',required=True)
OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-writhing-normal-20261028-v7'
CAND=OUT/'candidate';BUILD=ROOT/'build/iee-projectile-secondary-links-20261028-v1'
ALIAS='X28WRTH';RUN='writhing-apollo30-retimed-strict-20261017-v1'
PRESERVE=['InfinityEngine-Enhancer.ini','BaldurReal.exe','override/WRITHING.bam',
 'override/fpDraw.glsl','override/fpSprite.glsl','override/fpSELECT.glsl',
 'iee-assets/creature-sprites/CreatureSprites-XN.catalog']
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(raw):return hashlib.sha256(raw).hexdigest().upper()
def snap(p):return asdict(tx.snapshot_file(p))
def save(p,value):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
def rawwrite(p,data):
 p.parent.mkdir(parents=True,exist_ok=True)
 with p.open('xb') as f:f.write(data)
def prepare():
 OUT.mkdir(parents=True,exist_ok=True);assert not (OUT/'plan.json').exists()
 active=GAME/'iee-assets/effects';old=js(active/'manifest.json');reg=(active/'EffectAnimations-X4.registry').read_bytes()
 assert old['resource_count']==537 and sha(reg)==old['registry_sha256'].upper()
 assert tx.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='9CA03C3C6CB3AFAA2EFF79398094519A728DB66833BE311E18B3FE698E9F37E4'
 assert ALIAS not in {r['resref'] for r in old['resources']}
 assert not (GAME/f'override/{ALIAS}.bam').exists()
 original=next(r for r in old['resources'] if r['resref']=='WRITHING')
 before=dict(files={n:snap(GAME/n) for n in PRESERVE+['InfinityEngine-Enhancer.dll',
  'iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry']},
  PROs={p.name:snap(p) for p in (GAME/'override').glob('*.pro')})
 spec=importlib.util.spec_from_file_location('existing_assembler',ROOT/'pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
 assembler=importlib.util.module_from_spec(spec);spec.loader.exec_module(assembler)
 a=dict(resref='WRITHING',interpolation_run=RUN,native_cycles=original['cycles'],native_fps=[15,1])
 record,resource,frames,copies,contracts,temporal=assembler.build_resource(a,ALIAS,True)
 assert resource['cycles']==original['cycles']
 for k in ('native_fps','target_fps','actual_phase_counts_by_cycle','cycle_profiles','once_profiles'):
  assert resource['timeline'][k]==original['timeline'][k],k
 oldframes=[f for f in old['frames'] if f['resref']=='WRITHING']
 for key in ('native_frame_indices_by_cycle','timeline_frame_indices_by_cycle'):
  for x,y in zip(original['timeline'][key],resource['timeline'][key]):
   assert len(x)==len(y)
   for i,j in zip(x,y):
    for field in ('logical_size_x1','physical_size_x4','source_centre_x1'):assert oldframes[i][field]==frames[j][field],(key,i,j,field)
 manifest=copy.deepcopy(old);manifest['resources'].append(resource)
 delta=[]
 def add(name,data):
  rawwrite(CAND/name,data);delta.append(dict(name=name,bytes=len(data),sha256=sha(data)))
 target=CAND/'iee-assets/effects';target.mkdir(parents=True,exist_ok=True)
 for source,name in copies:
  # Independent byte copies; never alter or make writable the sealed source.
  dest=target/name
  if dest.exists():assert tx.sha256_file(dest)==tx.sha256_file(source)
  else:shutil.copy2(source,dest)
 for f in frames:
  f['frame']=len(manifest['frames']);manifest['frames'].append(f)
  delta.append(dict(name='iee-assets/effects/'+f['asset'],bytes=f['bytes'],sha256=f['sha256']))
 carrier=(GAME/'override/WRITHING.bam').read_bytes();add(f'override/{ALIAS}.bam',carrier)
 manifest['runtime_bam_carriers'].append(dict(resref=ALIAS,asset=f'override/{ALIAS}.bam',bytes=len(carrier),
  sha256=sha(carrier),production_bam='WRITHING',policy='Existing straight/native-alpha companion; native carrier identical'))
 magic,version,scale,count,reserved=struct.unpack_from('<8sIIII',reg)
 registry=struct.pack('<8sIIII',magic,version,scale,count+1,reserved)+reg[24:]+record
 assert registry[24:24+len(reg)-24]==reg[24:]
 manifest.update(created_utc=tx.utc_now(),resource_count=count+1,frame_count=len(manifest['frames']),
  registry_bytes=len(registry),registry_sha256=sha(registry))
 assert manifest['resources'][:-1]==old['resources'] and manifest['frames'][:len(old['frames'])]==old['frames']
 assert manifest['runtime_vvc_controllers']==old['runtime_vvc_controllers']
 add('iee-assets/effects/EffectAnimations-X4.registry',registry)
 add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8'))
 dll=(BUILD/'Release/InfinityEngine-Enhancer.dll').read_bytes();add('InfinityEngine-Enhancer.dll',dll)
 rawwrite(OUT/'contracts.tsv',('\n'.join(contracts)+'\n').encode('ascii'))
 middle=temporal['frames'][len(temporal['frames'])//2]
 stage=ROOT/'effects/ressources/WRITHING/runs'/RUN/'02-interpolation'
 oldpixels=np.frombuffer((stage/middle['raw_rgba_x4']).read_bytes(),np.uint8).reshape(-1,4)
 newpixels=np.frombuffer((stage/middle['straight_raw_rgba_x4']).read_bytes(),np.uint8).reshape(-1,4)
 support=oldpixels[:,3]>0
 sources={p.relative_to(ROOT).as_posix():tx.sha256_file(p) for p in
  (ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee').rglob('*') if p.suffix in ('.cpp','.h')}
 save(OUT/'before.json',before)
 save(OUT/'plan.json',dict(alias=ALIAS,production_run=RUN,files=delta,source_sha256=sources,
  old_resources_unchanged=537,old_frames_unchanged=len(old['frames']),new_frames=len(frames),
  copied_existing_straight_bytes=sum(f['bytes'] for f in frames),native_contracts=len(contracts),
  alpha_sample=dict(temporal_frame=middle['frame'],old_median=float(np.median(oldpixels[support,3])),
   native_normal_median=float(np.median(newpixels[support,3]))),
  source_manifest_sha256=tx.sha256_file(stage/'manifest.json'),normal_only=True,inference_jobs=0))
 print('Prepared existing companions:',len(frames),'backings;',len(contracts),'contracts',flush=True)
def probe(path,logname):
 # Match the installed runtime budget, not the probe's historical16MiB default.
 ini=(GAME/'InfinityEngine-Enhancer.ini').read_text(encoding='utf-8-sig')
 metadata=re.search(r'(?m)^EffectMetadataMiB\s*=\s*(\d+)',ini).group(1)
 with (OUT/logname).open('x',encoding='utf-8') as f:
  subprocess.run([str(BUILD/'Release/iee_effect_animation_x4_registry_tests.exe'),'--metadata-mib',metadata,'--catalogue-only',str(path),str(OUT/'contracts.tsv')],
   stdout=f,stderr=subprocess.STDOUT,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
def verify():
 plan=js(OUT/'plan.json')
 for e in plan['files']:assert snap(CAND/e['name'])==dict(bytes=e['bytes'],sha256=e['sha256']),e['name']
 probe(CAND/'iee-assets/effects','candidate-native-loader-metadata32.log')
 log=BUILD/'writhing-normal-v7-tests-final.log';assert '100% tests passed' in log.read_text()
 save(OUT/'verification.json',dict(status='passed',candidate_catalogue_native_contracts=plan['native_contracts'],
  checks='Every new backing hash-bound to an existing straight companion; original537 descriptors/62099 frames and registry prefix identical',
  tests=str(log.relative_to(ROOT)),tests_sha256=tx.sha256_file(log)))
 print('Candidate verified')
def install():
 assert not (OUT/'installation.json').exists() and not (OUT/'transaction.json').exists()
 before=js(OUT/'before.json');plan=js(OUT/'plan.json');v=js(OUT/'verification.json');assert v['status']=='passed'
 assert tx.sha256_file(ROOT/v['tests'])==v['tests_sha256']
 tx.ensure_game_stopped(tx.running_game_processes)
 for n,s in before['files'].items():assert snap(GAME/n)==s,n
 for n,s in before['PROs'].items():assert snap(GAME/'override'/n)==s,n
 for n,h in plan['source_sha256'].items():assert tx.sha256_file(ROOT/n)==h,n
 (OUT/'before').mkdir(exist_ok=True)
 entries=[]
 for e in plan['files']:
  source=tx.managed_path(CAND,e['name']);expected=tx.FileSnapshot(e['bytes'],e['sha256']);assert tx.snapshot_file(source)==expected
  target=tx.managed_path(GAME,e['name']);old=tx.optional_snapshot(target)
  if old:
   assert e['name'] in ('InfinityEngine-Enhancer.dll','iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry')
   tx.atomic_copy(target,tx.managed_path(OUT/'before',e['name'],create_parents=True),old)
  entries.append({**e,'before':asdict(old) if old else None})
 receipt=dict(schema='bg2-projectile-existing-companion-delta-v1',status='prepared',game_root=str(GAME),files=entries)
 tx.write_json_atomic(OUT/'transaction.json',receipt)
 try:
  receipt['status']='installing';tx.write_json_atomic(OUT/'transaction.json',receipt)
  for e in entries:
   target=tx.managed_path(GAME,e['name'],create_parents=True)
   assert tx.optional_snapshot(target)==(tx.FileSnapshot(**e['before']) if e['before'] else None)
   tx.atomic_copy(tx.managed_path(CAND,e['name']),target,tx.FileSnapshot(e['bytes'],e['sha256']))
  for e in entries:assert snap(tx.managed_path(GAME,e['name']))==dict(bytes=e['bytes'],sha256=e['sha256'])
  for n in PRESERVE:assert snap(GAME/n)==before['files'][n],n
  for n,s in before['PROs'].items():assert snap(GAME/'override'/n)==s,n
  probe(GAME/'iee-assets/effects','installed-native-loader.log')
  receipt['status']='installed';receipt['installed_utc']=tx.utc_now();tx.write_json_atomic(OUT/'transaction.json',receipt)
 except Exception:
  for e in reversed(entries):
   target=tx.managed_path(GAME,e['name']);new=tx.FileSnapshot(e['bytes'],e['sha256']);old=tx.FileSnapshot(**e['before']) if e['before'] else None
   actual=tx.optional_snapshot(target);assert actual in (old,new)
   if actual==old:continue
   if old:tx.atomic_copy(tx.managed_path(OUT/'before',e['name']),target,old)
   else:tx.safe_unlink(target,new)
  receipt['status']='rolled-back';tx.write_json_atomic(OUT/'transaction.json',receipt);raise
 save(OUT/'installation.json',dict(status='installed-awaiting-runtime-evidence',utc=tx.utc_now(),dll=snap(GAME/'InfinityEngine-Enhancer.dll'),
  manifest=snap(GAME/'iee-assets/effects/manifest.json'),registry=snap(GAME/'iee-assets/effects/EffectAnimations-X4.registry'),
  alias=ALIAS,resources=538,frames=62099+plan['new_frames'],new_backings=plan['new_frames'],existing_images_changed=False,
  existing537_descriptors_and_frames_unchanged=True,PROs_unchanged=True,inference_jobs=0,release_changed=False,ingame_validated=False))
 print('Installed existing straight companion; preserved original537 resources',flush=True)
if __name__=='__main__':{'prepare':prepare,'verify':verify,'install':install}[sys.argv[1]]()
