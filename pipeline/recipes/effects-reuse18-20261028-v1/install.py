"""Reuse installed productions: no inference, no temporal interpolation generation."""
from pathlib import Path
import sys,struct,json,copy,importlib.util,os,shutil,argparse
from dataclasses import asdict
import numpy as np
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
base=module('reuse_base','pipeline/recipes/effects-insectes-install-20261027-v1/install.py')
tx=base.tx;workflow=base.workflow;authority=base.authority
load,save,sha,digest,rel=base.load,base.save,base.sha,base.digest,base.rel
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam
GAME=base.GAME;OUT=ROOT/'effects/installations/reuse18-20261028-v1';CANDIDATE=OUT/'candidate'
PARENT=ROOT/'effects/installations/insectes-continu-reference060-20261027-v1'
ALIASES=dict(SPARMOUR='OHNVIS1',SPFDETH3='SPFDEATH',SPFIRIMP='FIREH',SPFLMSTI='FLMSTRK',SPHLHI01='SPHLEFT',SPHLHI02='SPHRIGHT',SPICEIMP='COLDH',SPILUSIO='SPILLUS',SPSDRBUR='SPSDBUR')
ANIMS=['BDFORCEW','OHDLPORT','OHHNECR','OHRSGATE','SPDIMNDR']
ALREADY=['BURNHAND','SPIPLARI','SPPRISM3','SPPRISMT']
base.OUT=OUT;base.CANDIDATE=CANDIDATE
tx.MANAGED_FILES+=('override/SPARM2.vvc',)
PRESERVED=base.PRESERVED+['iee-assets/AreaAnimations-X4.registry']
PRESERVED=[p for p in PRESERVED if (GAME/p).exists()]

def make_carrier(ref,size,centre):
 raw=read_bam(ROOT/'effects/ressources'/ref/'source.bam');fs,pal,tr=decode_bam(raw)
 nf,nc,_=struct.unpack_from('<HBB',raw,8);of,op,ol=struct.unpack_from('<III',raw,12)
 cs=cycle_metadata(raw,nf);cc=raw[of+nf*12:of+nf*12+nc*4];lc=max(c['lookup_start']+len(c['frame_indices']) for c in cs)
 lookup=raw[ol:ol+lc*2];palette=raw[op:op+1024];w,h=size
 off=24+nf*12+len(cc)+1024+len(lookup);table=bytearray();pixels=[]
 for idx,cx,cy,_ in fs:
  x,y=centre[0]-cx,centre[1]-cy;assert x>=0 and y>=0 and x+idx.shape[1]<=w and y+idx.shape[0]<=h
  canvas=np.full((h,w),tr,np.uint8);canvas[y:y+idx.shape[0],x:x+idx.shape[1]]=idx
  table.extend(struct.pack('<HHhhI',w,h,*centre,off|0x80000000));pixels.append(canvas.tobytes());off+=w*h
 out=struct.pack('<8sHBBIII',b'BAM V1  ',nf,nc,tr,24,24+nf*12+len(cc),24+nf*12+len(cc)+1024)+table+cc+palette+lookup+b''.join(pixels)
 nfs,npa,ntr=decode_bam(out);assert np.array_equal(npa,pal) and tr==ntr and cycle_metadata(out,nf)==cs
 for (idx,cx,cy,_),(pad,ncx,ncy,_) in zip(fs,nfs):
  x,y=ncx-cx,ncy-cy;assert np.array_equal(idx,pad[y:y+idx.shape[0],x:x+idx.shape[1]])
 return out,cs

def animation(ref):
 sel=load(ROOT/'animations/index/selections'/f'{ref}.json');finalpath=ROOT/sel['selected_run']['manifest_path']
 assert sha(finalpath)==sel['selected_run']['manifest_sha256'];final=load(finalpath)
 assert sha(ROOT/final['source_run']/'manifest.json')==final['source_run_manifest_sha256'].upper()
 source=ROOT/final['source_pack'];assert sha(source/'manifest.json')==final['source_pack_manifest_sha256'].upper()
 choices=[]
 for p in sorted(source.rglob('manifest.json')):
  for r in load(p).get('resources',[]):
   if r['resref']==ref:choices.append((p,r))
 assert choices,ref
 p,r=choices[0]
 for pp,rr in choices[1:]:assert rr==r,ref
 fs,pal,tr=decode_bam(read_bam(ROOT/'effects/ressources'/ref/'source.bam'))
 bounds=[(-cx,-cy,idx.shape[1]-cx,idx.shape[0]-cy) for idx,cx,cy,_ in fs]
 for f in r['frames']:
  cx,cy=f['centre_x1'];w,h=f['logical_size_x1'];bounds.append((-cx,-cy,w-cx,h-cy))
 l=min(b[0] for b in bounds);t=min(b[1] for b in bounds);right=max(b[2] for b in bounds);bottom=max(b[3] for b in bounds)
 size=[right-l,bottom-t];centre=[-l,-t];carrier,cycles=make_carrier(ref,size,centre)
 frames=[];copies=[];checks=[]
 for f in r['frames']:
  src=p.parent/f['asset'];assert sha(src)==f['sha256'].upper()
  w,h=f['logical_size_x1'];rgba=np.frombuffer(src.read_bytes(),np.uint8).reshape(h*4,w*4,4)
  canvas=np.zeros((size[1]*4,size[0]*4,4),np.uint8);x=(centre[0]-f['centre_x1'][0])*4;y=(centre[1]-f['centre_x1'][1])*4
  canvas[y:y+h*4,x:x+w*4]=rgba
  assert np.array_equal(canvas[y:y+h*4,x:x+w*4],rgba)
  name=f'EFX4-{ref}-frame{f["frame"]:03d}.rgba';dest=OUT/'derived'/ref/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(canvas.tobytes())
  frames.append(dict(frame=f['frame'],asset=name,resref=ref,resource_frame=f['frame'],source=rel(dest),sha256=sha(dest),bytes=dest.stat().st_size,logical_size_x1=size,physical_size_x4=[v*4 for v in size],source_centre_x1=centre))
  copies.append((dest,name));checks.append(dict(source=rel(src),source_sha256=sha(src),padded_sha256=sha(dest),pixels_alpha_world_positions_exact=True))
 native=[c['native_frame_indices'] for c in r['cycles']];tables=[c['timeline_frame_indices'] for c in r['cycles']]
 assert len(native)==len(cycles) and all(len(n)==len(c['frame_indices']) for n,c in zip(native,cycles))
 assert r['native_fps']==dict(numerator=15,denominator=1) and r['target_fps']==dict(numerator=30,denominator=1)
 maximum=max(map(len,tables));block=bytearray(ref.encode().ljust(8,b'\0')+struct.pack('<II',len(frames),len(native)))
 for f in frames:block.extend(struct.pack('<II',*size))
 for n in native:block.extend(struct.pack(f'<I{len(n)}I',len(n),*n))
 block.extend(struct.pack('<IIIII',15,1,30,1,maximum))
 for n,tt in zip(native,tables):
  assert len(tt)==2*len(n);block.extend(struct.pack(f'<{maximum}I',*(tt+[tt[-1]]*(maximum-len(tt)))))
 block.extend(struct.pack('<I',0));contracts=[]
 for c,(n,tt) in enumerate(zip(native,tables)):
  for once in (0,1):
   for ph,target in enumerate(tt):
    slot=ph//2;fallback=n[slot]
    for name in [ref,ref.lower()]:contracts.append(f'{name}\t{slot}\t{size[0]}\t{size[1]}\t{ph}\t{c}\t{fallback}\t{target}\t{once}')
 resource=dict(resref=ref,frame_count=len(frames),cycles=cycles,production_bam='animations:'+ref,rgb_encoding='premultiplied',reuse_source_manifest=rel(p),reuse_source_manifest_sha256=sha(p),timeline=dict(native_fps=[15,1],target_fps=[30,1],phase_count=maximum,native_frame_indices_by_cycle=native,timeline_frame_indices_by_cycle=tables,actual_phase_counts_by_cycle=list(map(len,tables)),cycle_profiles=['retained-area-cycle'+str(i) for i in range(len(native))]))
 save(OUT/'checks'/f'{ref}.json',dict(source_selection=sel,source_run=final['source_run'],padding_checks=checks,neural_inference=0,new_interpolation=0,area_specific_placement_not_applied=True))
 return bytes(block),resource,frames,copies,carrier,contracts

def prepare():
 assert not (OUT/'plan.json').exists();CANDIDATE.mkdir(parents=True,exist_ok=True);active=GAME/'iee-assets/effects';old=load(active/'manifest.json')
 assert sha(active/'manifest.json')=='33EABE45E817E000E33BA9A96DD0B758E356FC1DAEC79BBF548774E669C60316'
 registry=(active/'EffectAnimations-X4.registry').read_bytes();blocks=base.registry_blocks(registry)
 before=dict(manifest_sha256=sha(active/'manifest.json'),registry_sha256=digest(registry),preserved={n:asdict(tx.snapshot_file(GAME/n)) for n in PRESERVED})
 # Preserve every installed area registry and source production metadata.
 before['preserved'].update({str(p.relative_to(GAME)).replace('\\','/'):asdict(tx.snapshot_file(p)) for p in (GAME/'iee-assets/areas').glob('*/AreaAnimations-X4.registry')})
 save(OUT/'before.json',before);manifest=copy.deepcopy(old);files={};baselines={};contracts=(PARENT/'runtime-contracts.tsv').read_text().splitlines();oldcontracts=list(contracts)
 def add(name,raw=None,source=None):
  dest=tx.managed_path(CANDIDATE,name,create_parents=True)
  if source is not None:shutil.copy2(source,dest)
  else:dest.write_bytes(raw)
  files[name]=dict(name=name,**asdict(tx.snapshot_file(dest)));b=tx.optional_snapshot(GAME/name);baselines[name]=asdict(b) if b else None
 newblocks=[];bindings=[]
 for target,parent in ALIASES.items():
  assert target not in blocks
  res=copy.deepcopy(next(r for r in old['resources'] if r['resref']==parent));res.update(resref=target,reuse_parent=parent)
  raw=target.encode().ljust(8,b'\0')+blocks[parent][8:];newblocks.append(raw);manifest['resources'].append(res)
  for f in old['frames']:
   if f['resref']==parent:
    nf=copy.deepcopy(f);nf.update(frame=len(manifest['frames']),resref=target,asset=f['asset'].replace('EFX4-'+parent+'-','EFX4-'+target+'-'))
    add('iee-assets/effects/'+nf['asset'],source=active/f['asset']);manifest['frames'].append(nf)
  carrier=next((c for c in old['runtime_bam_carriers'] if c['resref']==parent),None)
  if carrier:
   add('override/'+target+'.bam',source=GAME/carrier['asset']);manifest['runtime_bam_carriers'].append(dict(carrier,resref=target,asset='override/'+target+'.bam',reuse_parent=parent))
  else:assert not (GAME/'override'/f'{target}.bam').exists(),target
  for line in oldcontracts:
   fields=line.split('\t')
   if fields[0].upper()==parent:fields[0]=target if fields[0].isupper() else target.lower();contracts.append('\t'.join(fields))
  bindings.append(dict(resref=target,kind='effects-alias',parent=parent,neural_inference=0))
 for ref in ANIMS:
  block,res,frames,copies,carrier,checks=animation(ref);newblocks.append(block);manifest['resources'].append(res)
  for src,name in copies:add('iee-assets/effects/'+name,source=src)
  for f in frames:f['frame']=len(manifest['frames']);manifest['frames'].append(f)
  add('override/'+ref+'.bam',carrier);manifest['runtime_bam_carriers'].append(dict(resref=ref,asset='override/'+ref+'.bam',sha256=digest(carrier),bytes=len(carrier),policy='source indexed pixels/palette/cycles/world anchors exact; transparent common canvas'))
  contracts.extend(checks);bindings.append(dict(resref=ref,kind='animation-import',parent='animations:'+ref,neural_inference=0))
 # One native SPARMOUR owner uses normal alpha: encoding-only companion.
 ref='R18ARMN';parent='OHNVIS1';block=ref.encode().ljust(8,b'\0')+blocks[parent][8:];newblocks.append(block)
 resource=copy.deepcopy(next(r for r in old['resources'] if r['resref']==parent));resource.update(resref=ref,rgb_encoding='straight',reuse_parent=parent);manifest['resources'].append(resource)
 for f in old['frames']:
  if f['resref']!=parent:continue
  rgba=np.frombuffer((active/f['asset']).read_bytes(),np.uint8).reshape(-1,4).copy();a=rgba[:,3].astype(np.uint32);prem=rgba[:,:3].copy();rgb=np.minimum(255,(rgba[:,:3].astype(np.uint32)*255+a[:,None]//2)//np.maximum(1,a[:,None]));rgba[:,:3]=rgb
  assert np.abs(((rgb*a[:,None]+127)//255).astype(int)-prem.astype(int)).max()<=1
  name=f['asset'].replace('EFX4-'+parent+'-','EFX4-'+ref+'-');raw=rgba.tobytes();add('iee-assets/effects/'+name,raw)
  nf=copy.deepcopy(f);nf.update(frame=len(manifest['frames']),resref=ref,asset=name,sha256=digest(raw),rgb_encoding='straight');manifest['frames'].append(nf)
 car=next(c for c in old['runtime_bam_carriers'] if c['resref']==parent);add('override/'+ref+'.bam',source=GAME/car['asset']);manifest['runtime_bam_carriers'].append(dict(car,resref=ref,asset='override/'+ref+'.bam'))
 for line in oldcontracts:
  ff=line.split('\t')
  if ff[0].upper()==parent:ff[0]=ref if ff[0].isupper() else ref.lower();contracts.append('\t'.join(ff))
 source=ROOT/'effects/source/vvc/SPARM2.vvc';raw=source.read_bytes();assert raw[8:16].rstrip(b'\0')==b'SPARMOUR'
 assert not (GAME/'override/SPARM2.vvc').exists() or (GAME/'override/SPARM2.vvc').read_bytes()==raw
 changed=raw[:8]+ref.encode().ljust(8,b'\0')+raw[16:];add('override/SPARM2.vvc',changed)
 manifest['runtime_vvc_controllers'].append(dict(asset='override/SPARM2.vvc',bam=ref,sha256=digest(changed),bytes=len(changed),purpose='native normal-alpha SPARMOUR consumer; reference only'))
 # Isolated test wrappers, existing native controllers otherwise unchanged.
 clua=[]
 for i,ref in enumerate(list(ALIASES)+ANIMS,1):
  rr=next(r for r in manifest['resources'] if r['resref']==ref);cycle=next(c for c in rr['cycles'] if c['frame_indices']);cc=cycle['cycle'];slots=len(cycle['frame_indices']);name=f'ZR18{i:02d}'
  assert not (GAME/f'override/{name}.vvc').exists()
  loop=ref!='SPDIMNDR';v=base.builder.make_vvc(ref,cc,loop,15,slots,True);add(f'override/{name}.vvc',v)
  manifest['runtime_vvc_controllers'].append(dict(asset=f'override/{name}.vvc',bam=ref,sha256=digest(v),bytes=len(v),purpose='reuse isolated visual test'))
  clua.append(dict(resref=ref,vvc=name,cycle=cc,clua=f'C:Eval(\'CreateVisualEffectObject("{name}",Player1)\',0)'))
 registry=registry+b''.join(newblocks);registry=registry[:16]+struct.pack('<I',len(manifest['resources']))+registry[20:];parsed=base.registry_blocks(registry)
 assert all(parsed[n]==b for n,b in blocks.items());assert manifest['frames'][:len(old['frames'])]==old['frames'] and manifest['resources'][:len(old['resources'])]==old['resources']
 manifest.update(resource_count=len(manifest['resources']),frame_count=len(manifest['frames']),registry_bytes=len(registry),registry_sha256=digest(registry))
 manifest.setdefault('runtime_corrections',[]).append(dict(installation=rel(OUT),reuse_only=True,new_inference=0,resrefs=list(ALIASES)+ANIMS,qa='new VVC bindings pending ingame'))
 add('iee-assets/effects/EffectAnimations-X4.registry',registry);add('iee-assets/effects/manifest.json',(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode())
 save(OUT/'target-baselines.json',baselines);save(OUT/'bindings.json',bindings);save(OUT/'clua.json',clua)
 (OUT/'runtime-contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
 (OUT/'CLUA.md').write_text('# Réemplois14 — tests des nouvelles liaisons\n\n```lua\n'+'\n'.join('-- '+c['resref']+'\n'+c['clua'] for c in clua)+'\n```\n',encoding='utf-8')
 save(OUT/'plan.json',dict(files=list(files.values()),retired=[],runtime_resources=len(manifest['resources']),total_backings=len(manifest['frames']),native_contracts=len(contracts),other_resources_unchanged=len(blocks),other_backings_unchanged=len(old['frames']),manifest_sha256=sha(CANDIDATE/'iee-assets/effects/manifest.json'),neural_inference=0,qa_accepted=False,release_changed=False))
 # Catalogue-only probe reads metadata and zero RGBA files; unchanged payloads stay in game.
 base.probe(CANDIDATE/'iee-assets/effects','candidate-native-loader.log')
 print('READY',len(files),'files; resources',len(manifest['resources']),flush=True)

def finish():
 receipt=load(OUT/'transaction.json');assert receipt['status']=='installed';plan=load(OUT/'plan.json');base.preserved(load(OUT/'before.json'))
 bindings={b['resref']:b for b in load(OUT/'bindings.json')};runtime=load(GAME/'iee-assets/effects/manifest.json')
 for ref in ALREADY:bindings[ref]=dict(resref=ref,kind='already-installed',parent=next(r.get('production_bam',r.get('reuse_parent',ref)) for r in runtime['resources'] if r['resref']==ref))
 timestamp=workflow.utc_now();updates={};runids={}
 for ref,b in bindings.items():
  ids={stage:ref.lower()+'-reuse-'+stage+'-20261028-v1' for stage in workflow.STAGES};runids[ref]=ids
  for stage,rid in ids.items():
   d=ROOT/'effects/ressources'/ref/'runs'/rid;d.mkdir(parents=True,exist_ok=True)
   recipe=dict(schema='bg2-effects-reuse-recipe-v1',operation='reuse-existing-production',stage=stage,neural_inference=0,new_interpolation=0,binding=b,installation=rel(OUT/'transaction.json'),qa='existing source QA retained; new bindings not ingame validated')
   save(d/'recipe.json',recipe);resource=next(r for r in runtime['resources'] if r['resref']==ref)
   save(d/'binding.json',dict(binding=b,runtime_resource=resource,installation=rel(OUT/'transaction.json'),frames=[f for f in runtime['frames'] if f['resref']==ref]))
   def ev(p,role):return dict(role=role,path=rel(p),sha256=sha(p),bytes=p.stat().st_size)
   inputs=[ev(ROOT/'effects/ressources'/ref/'source.bam','source-bam'),ev(OUT/'bindings.json','reuse-bindings')]
   if stage=='interpolation':inputs.append(ev(ROOT/'effects/ressources'/ref/'runs'/ids['spatial']/'binding.json','parent-spatial-output'))
   desc={'$schema':'docs/workspace-run.schema.json','schema_version':1,'run_id':rid,'domain':'effects','asset_ids':['effects:bam:'+ref],'pipeline':dict(id=workflow.STAGES[stage],version='reuse-existing.v1',recipe_path=rel(d/'recipe.json'),recipe_sha256=sha(d/'recipe.json')),'inputs':inputs,'outputs':[ev(d/'binding.json','reused-runtime-binding')],'provenance':dict(created_at_utc=timestamp,generator=rel(Path(__file__)),parents=[ids['spatial']] if stage=='interpolation' else []),'result':dict(status='completed',sealed=True,completed_at_utc=timestamp)}
   save(d/'run.json',desc)
   verified=workflow.verify_run_descriptor(ROOT,d.parent.parent,ref,rid,stage=stage,spatial_run=ids['spatial']);assert verified['ok'],verified
 with authority.guard(ROOT,write=True):
  rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS);save(OUT/'processing-before.json',rows)
  for row in rows:
   ref=row['asset_key'].rsplit(':',1)[-1]
   if ref not in bindings:continue
   assert row['spatial_state']=='not-started' and not row['selected_run'],ref
   row.update(spatial_run=runids[ref]['spatial'],spatial_state='produced',interpolation_run=runids[ref]['interpolation'],interpolation_state='produced',installation_state='installed',installation_receipt=rel(OUT/'transaction.json'))
   row['notes']=(row['notes']+'; ' if row['notes'] else '')+'reuse='+bindings[ref]['parent']+'; no-inference; binding='+rel(OUT/'bindings.json')+'; QA source retained, new VVC binding not assessed'
  authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
 save(OUT/'installation.json',dict(status='installed-offline-verified',bindings_added=14,already_installed_reconciled=4,encoding_companion='R18ARMN',new_neural_inference=0,new_interpolation=0,qa_accepted=False,release_changed=False,transaction=rel(OUT/'transaction.json'),manifest_sha256=plan['manifest_sha256'],runtime_resources=plan['runtime_resources'],native_contracts=plan['native_contracts']))
 print('DONE 14 links installed, 18 tracking rows reconciled; QA not inferred',flush=True)

base.finish=finish
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('action',choices=['prepare','verify','install','finish']);args=p.parse_args();OUT.mkdir(parents=True,exist_ok=True)
 if args.action=='install':base.install()
 elif args.action=='verify':base.probe(CANDIDATE/'iee-assets/effects','candidate-native-loader.log')
 else:globals()[args.action]()
