"""Read-only audit of remaining effects against production and active game bytes."""
from installed import *
import time
from run_animation_upscale_30fps_v2 import resource_binary_v2
before={str(p):sha(p.read_bytes()) for p in [R/'effects/index/processing.csv',R/'animations/index/animation_upscale_registry.csv',A/'effects/manifest.json',G/'InfinityEngine-Enhancer.ini',cat]}
m=load(A/'effects/manifest.json');resources={r['resref']:r for r in m['resources']}
assert sha((A/'effects'/m['registry']).read_bytes())==m['registry_sha256'].upper()
assert sha((A/'effects/manifest.json').read_bytes())=='33EABE45E817E000E33BA9A96DD0B758E356FC1DAEC79BBF548774E669C60316'
verified={};evidence=[]
def check(p,digest,size=None):
 key=str(p)
 if key not in verified:
  assert p.is_file(),key
  if size is not None:assert p.stat().st_size==size,key
  actual=sha(p.read_bytes());assert actual==digest.upper(),key
  verified[key]=dict(path=key,bytes=p.stat().st_size,sha256=actual)
 else:assert verified[key]['sha256']==digest.upper()
def effect(name):
 assert name in resources,name
 for f in m['frames']:
  if f['resref']==name:check(A/'effects'/f['asset'],f['sha256'],f['bytes'])
 for c in m['runtime_bam_carriers']:
  if c['resref']==name:check(G/c['asset'],c['sha256'],c['bytes'])
 return dict(kind='effects-registry',resref=name,resource=resources[name],frame_files_verified=sum(f['resref']==name for f in m['frames']))
def animation(name):
 sel=load(R/'animations/index/selections'/f'{name}.json');sp=sel['source_pack']
 check(R/sel['selected_run']['manifest_path'],sel['selected_run']['manifest_sha256'])
 check(R/sel['qa_decision']['path'],sel['qa_decision']['sha256'])
 hits=[]
 for ar in sp['areas']:
  p=R/ar['manifest_path'];check(p,ar['manifest_sha256']);pm=load(p)
  for res in pm['resources']:
   if res['resref']!=name:continue
   matches=[x for x in area if x['resref']==name and Path(x['path']).parent.name==ar['area']]
   expected=sha(resource_binary_v2(res,pm['registry_version']))
   assert any(x['block_sha256']==expected for x in matches),(name,ar['area'])
   for f in res['assets']:check(A/'areas'/ar['area']/f['name'],f['sha256'],f['bytes'])
   hits.append(dict(area=ar['area'],registry_block_sha256=expected,assets_verified=len(res['assets'])))
 assert hits,name
 return dict(kind='area-registry',resref=name,hits=hits,scope='covered for listed area-animation routes; effect/VVC routes are separate')
result=[]
cross=load(OUT/'cross183.json')
for o in cross:
 n=o['resref'];p=R/'effects/ressources'/n/'source.bam';assert sha(read_bam(p))==work[n]['canonical_sha256']
 reuse=[x for x in o['visual_matches'] if (x[0]=='effects' and x[2] not in ('not-started','blocked')) or (x[0]=='animations' and x[2]=='selected')]
 row=dict(resref=n,canonical_sha256=work[n]['canonical_sha256'],matches=o['matches'],visual_matches=o['visual_matches'],source_verified=True)
 if reuse:
  domain,target,_=reuse[0];row['reuse_target']=domain+':'+target
  if domain=='animations':row['status']='already-installed-area';proof=animation(target)
  else:
   proof=effect(target)
   if n in resources:row['status']='already-installed-effect';row['own_installed_proof']=effect(n)
   else:row['status']='link-existing-production'
  row['proof']=proof
 else:
  row['status']='new-production'
  row['cohort_aliases']=[x[1] for x in o['visual_matches'] if x[0]=='effects' and x[2]=='not-started']
 result.append(row)
new=[r for r in result if r['status']=='new-production'];groups={}
for r in new:
 k=min([r['resref']]+r['cohort_aliases']);groups.setdefault(k,[]).append(r['resref'])
summary=dict(scope_rows=len(result),statuses=dict(Counter(r['status'] for r in result)),new_resrefs=len(new),new_distinct_productions=len(groups),new_alias_groups=[v for v in groups.values() if len(v)>1],verified_files=len(verified),verified_bytes=sum(v['bytes'] for v in verified.values()),production_started=False,installation_changed=False)
for p,d in before.items():assert sha(Path(p).read_bytes())==d,p
payload=dict(date='2026-10-28',summary=summary,rows=result,verified_files=list(verified.values()),unchanged_inputs=before,limits=['Installation is verified offline by registry and file hashes, not by a new ingame observation.','Area routes do not automatically substitute effect/VVC routes.','New means no reusable completed production identified, not proven native usage.','The source effects inventory contains scenery and creature resources; new distinct productions are not a count of active spells.','Sprite canonical hashes and current catalog directory checked; no match for these183.'])
(OUT/'audit.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
with (OUT/'audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
 writer=csv.DictWriter(f,fieldnames=['resref','status','reuse_target','new_group','canonical_sha256']);writer.writeheader()
 for r in result:writer.writerow(dict(resref=r['resref'],status=r['status'],reuse_target=r.get('reuse_target',''),new_group=min([r['resref']]+r.get('cohort_aliases',[])) if r['status']=='new-production' else '',canonical_sha256=r['canonical_sha256']))
print(json.dumps(summary,indent=2))
