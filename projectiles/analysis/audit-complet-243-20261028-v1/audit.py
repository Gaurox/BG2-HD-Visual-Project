"""Audit every live stock PRO, recursive controller and projectile edge. No game writes."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,json,sys,struct,hashlib,zlib
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
if (OUT/'physical-checks.json').exists():
 raise SystemExit('Sealed audit: copy the recipe into a NEW version directory before rerunning.')
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from projectile_tracking import parse_pro,dependency_activity,ids_entries
GAME=get_path('bg2ee_game_root',required=True);SNAP=ROOT/'projectiles/analysis/20261028-v2'
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4194304),b''):h.update(b)
 return h.hexdigest().upper()
def csvread(p):return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))
def savecsv(name,rows):
 with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def ref(b,o):return b[o:o+8].split(b'\0')[0].decode('ascii').upper()
def save(name,data):(OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
bifs,entries=load_key();key={(n.upper(),t):loc for n,t,loc in entries};ext={1:'bmp',1000:'bam',1019:'vvc',1020:'vef',1021:'pro',1008:'ids',2050:'ini'}
read_cache={};input_hashes={}
def read(n,t):
 if (n,t) in read_cache:return read_cache[n,t]
 over=GAME/'override'/f'{n}.{ext[t]}'
 if over.is_file():raw=over.read_bytes();origin=str(over)
 elif (n,t) in key:raw=resolve_resource(bifs,key[n,t])[0];origin=f'KEY://{n}.{ext[t]}'
 else:return None
 input_hashes[origin]=hashlib.sha256(raw).hexdigest().upper();read_cache[n,t]=raw;return raw
m=js(GAME/'iee-assets/effects/manifest.json');manifest_sha=sha(GAME/'iee-assets/effects/manifest.json');catalog={r['resref']:r for r in m['resources']}
contexts=js(SNAP/'contexts.json');source_uses=defaultdict(list)
for c in contexts.values():
 for u in c['uses']:source_uses[u['projectile'],u['role']].append((c,u))
source_rows=csvread(ROOT/'projectiles/index/resources.csv');names={r['resref'] for r in source_rows};projectl=ids_entries(read('PROJECTL',1008))
sprite={int(r['animation_id'],16):r for r in csvread(ROOT/'sprite/index/sprite_animations.csv')}
stock={r['resref']:(ROOT/r['extracted_path']).read_bytes() for r in source_rows};active={n:read(n,1021) for n in names};pros={n:parse_pro(b) for n,b in active.items()}
expected={n:bytearray(b) for n,b in stock.items()}
for r in js(ROOT/'effects/installations/lot31-latest-20261019-v1/palette-routes.json'):
 expected[r['owner']][0x104:0x10c]=r['runtime_bam'].encode().ljust(8,b'\0')
for r in js(ROOT/'effects/installations/insectes-continu-reference060-20261027-v1/palette-routes.json'):
 o=int(r['offset'],16);expected[r['owner']][o:o+8]=r['target'].encode().ljust(8,b'\0')
pro_issues=[n for n in names if active[n]!=bytes(expected[n])]
components=[];links=[];controller_checks=[]
def add(owner,role,target,activity,state,production,route,path,detail='',cycle=''):
 components.append(dict(pro=owner,role=role,resource=target,activity=activity,state=state,production=production,route=route,path='>'.join(path),detail=detail,cycle=cycle))
def bam(owner,role,n,activity,path,scope,cycle='',inherited=None):
 raw=read(n,1000)
 if raw is None:add(owner,role,n,activity,'missing-resource','missing','missing',path);return
 matches=source_uses[owner,role];cs=[c for c,u in matches if u['bam']==n or catalog.get(n,{}).get('production_bam')==u['bam']]
 if not cs and len(matches)==1:cs=[matches[0][0]]
 black=any(c.get('black_only') for c in cs) or any(c.get('black_only') and n in c['bam_names'] for c in contexts.values())
 produced=any(c.get('action')=='reuse-existing-output' for c in cs)
 if black:add(owner,role,n,activity,'native-mask','native','native-preserved',path,cycle=cycle);return
 if n not in catalog:
  add(owner,role,n,activity,'produced-not-linked' if produced else 'not-produced','produced' if produced else 'missing','no-catalogue',path,cycle=cycle);return
 r=catalog[n];job=r.get('palette_job');jobs={cnd.get('job_id') for c in cs for cnd in c['candidates'] if cnd.get('job_id')}
 palette_ok=not jobs or job in jobs
 cycle_ok=cycle=='' or any(x['cycle']==cycle for x in r.get('cycles',[]))
 details=[]
 if not palette_ok:details.append('palette-job mismatch')
 if not cycle_ok:details.append('cycle absent: native fallback requires review')
 if inherited and inherited.get('palette'):details.append('VVC palette override')
 if not palette_ok or not cycle_ok or details:state='contract-review'
 elif scope in ('primary','vvc'):state='hd-linked-static'
 else:state='produced-scope-unproven'
 add(owner,role,n,activity,state,'produced',scope,path,';'.join(details),cycle)
def expand(owner,role,n,types,activity,path,scope,cycle='',seen=()):
 typ=next((t for t in types if read(n,t) is not None),None)
 if typ is None:add(owner,role,n,activity,'missing-resource','missing','missing',path);return
 if (n,typ) in seen:add(owner,role,n,activity,'controller-cycle','unknown','unknown',path);return
 raw=read(n,typ)
 if typ==1000:bam(owner,role,n,activity,path,scope,cycle);return
 if typ==1:add(owner,role,n,'metadata','palette-data','not-image','native',path);return
 controller_checks.append({'pro':owner,'role':role,'controller':n,'format':ext[typ],'sha256':hashlib.sha256(raw).hexdigest().upper(),'override':(GAME/'override'/f'{n}.{ext[typ]}').exists()})
 if typ==1019:
  if raw[:8]!=b'VVC V1.0':raise ValueError(n)
  for off in (8,0x88):
   child=ref(raw,off)
   if child:bam(owner,role,child,activity,path+[f'{n}.vvc:{hex(off)}',child],'vvc','',{'palette':ref(raw,0x44)})
 elif typ==1020:
  for oa,ca in ((8,12),(16,20)):
   off,count=struct.unpack_from('<I',raw,oa)[0],struct.unpack_from('<I',raw,ca)[0]
   for i in range(count):
    pos=off+i*0xe0;kind=struct.unpack_from('<I',raw,pos+12)[0];child=ref(raw,pos+16)
    if child and kind in (1,2):expand(owner,role,child,(1019,1000) if kind==1 else (1020,1019,1000),activity,path+[f'{n}.vef:{i}',child],'vvc','',seen+((n,typ),))
def animate(owner,role,aid,activity):
 sr=sprite.get(aid,{});n=sr.get('resref','')
 # Native executable references, separately saved in native-animation-dispatch.txt.
 fallback={0x300:['SPSMPUFF'],0x301:['SPSMPUFF'],0x400:['SKLH','SPSHADOW']}
 resolved=[n] if n else fallback.get(aid,[])
 if not resolved:add(owner,role,f'ANIMATE:{aid:#06x}',activity,'engine-route-unresolved','unknown','engine-native',[f'ANIMATE:{aid:#06x}']);return
 for child in resolved:bam(owner,role,child,activity,[f'ANIMATE:{aid:#06x}',child],'animation-effect')
for n,p in sorted(pros.items()):
 for role,off,target,types in p['resources']:
  activity,why=dependency_activity(p,role)
  # 0x14e/150/152 are sequence IDs, NOT temporal periods.
  if role.startswith('trailing-animation'):activity='potential'
  if role=='explosion-animation' and not p.get('area_flags',0)&1024:types=(1000,)
  cycle=p.get('travel_cycle','') if role=='travel-animation' else p.get('shadow_cycle','') if role=='shadow-animation' else p['trailing_periods'][int(role[-1])-1] if role.startswith('trailing-animation') else ''
  expand(n,role,target,types,activity,[target],'primary' if role=='travel-animation' else 'shadow' if role=='shadow-animation' else 'trailing' if role.startswith('trailing-animation') else 'area-bam',cycle)
 if p.get('bam_flags',0)&2:animate(n,'smoke-animation',p['smoke_animation_id'],'conditional' if p['extended_flags']&16384 else 'potential')
 if p.get('area_flags',0)&32:animate(n,'fragment-animation',p['fragment_animation_id'],'disabled' if p['ray_count'] else 'potential')
 if p['sparking_flags']&1:add(n,'sparks',f'SPRKCLR:{p["particle_color"]}','potential','native-procedural','not-image','native-preserved',['sparks'])
 if 'explosion_effect' in p and p['explosion_effect'] not in (254,255):add(n,'native-explosion-effect',f'FIREBALL:{p["explosion_effect"]}','potential','engine-route-unresolved','unknown','engine-native',['FIREBALL.IDS'],'Enum/mode is not an independently identified BAM')
 if 'secondary_raw' in p:
  if p['area_flags']&16:links.append(dict(pro=n,role='secondary-projectile',id=p['secondary_raw']+1))
  if p['explosion_projectile_raw']:links.append(dict(pro=n,role='explosion-projectile',id=p['explosion_projectile_raw']))
 if p['extended_flags']&1024:
  for id,name in projectl.items():
   if name==n:links.append(dict(pro=n,role='multiple-previous',id=id-1))
for l in links:l['target']=projectl.get(l['id'],f'engine-id:{l["id"]}')
graph=defaultdict(set);engine_edges=defaultdict(list)
for l in links:
 if l['target'] in names:graph[l['pro']].add(l['target'])
 else:engine_edges[l['pro']].append(l)
def closure(n):
 seen=set();todo=[n]
 while todo:
  x=todo.pop()
  if x in seen:continue
  seen.add(x);todo.extend(graph[x]-seen)
 return seen
byowner=defaultdict(list)
for c in components:
 if c['activity'] not in ('disabled','metadata'):byowner[c['pro']].append(c)
badstates={'missing-resource','not-produced','produced-not-linked','contract-review','controller-cycle','engine-route-unresolved','produced-scope-unproven'}
summary=[]
for n in sorted(names):
 family=closure(n);allc=[c for x in family for c in byowner[x]];bad=[c for c in allc if c['state'] in badstates];hard=[l for x in family for l in engine_edges[x]]
 states={c['state'] for c in allc};hd=sum(c['state']=='hd-linked-static' for c in allc)
 if 'missing-resource' in states:verdict='dependency-missing'
 elif 'not-produced' in states:verdict='image-missing'
 elif 'produced-not-linked' in states:verdict='image-produced-link-missing'
 elif 'contract-review' in states:verdict='contract-review'
 elif bad or hard:verdict='partial-route-unproven'
 elif hd:verdict='hd-linked-static'
 else:verdict='native-only-no-image-job'
 own=byowner[n];primary=[c for c in own if c['role']=='travel-animation'];summary.append(dict(pro=n,verdict=verdict,primary=';'.join(c['state'] for c in primary) or 'no-primary',closure=';'.join(sorted(family)),components=len(allc),hd_links=hd,produced_components=sum(c['production']=='produced' for c in allc),missing_images=';'.join(sorted({c['resource'] for c in allc if c['state'] in ('not-produced','missing-resource')})),unproven=';'.join(sorted({f'{c["pro"]}/{c["role"]}:{c["resource"]}' for c in bad})),engine_children=';'.join(sorted({str(l['id']) for l in hard}))))
savecsv('projectiles-243.csv',summary);savecsv('components.csv',components);savecsv('projectile-links.csv',links);savecsv('controllers.csv',controller_checks)
relevant={c['resource'] for c in components if c['resource'] in catalog};frame_checks=[f for f in m['frames'] if f['resref'] in relevant]
save('summary.json',{'manifest_sha256':manifest_sha,'catalogue_resources':len(catalog),'stock_pro':len(names),'PRO_byte_issues':pro_issues,'verdicts':dict(Counter(r['verdict'] for r in summary)),'component_states':dict(Counter(c['state'] for c in components if c['activity'] not in ('disabled','metadata'))),'relevant_catalogue_resources':len(relevant),'frames_to_check':len(frame_checks),'bytes_to_check':sum(f['bytes'] for f in frame_checks),'context_coverage':js(SNAP/'analysis.json')['coverage_levels'],'limits':['Static audit, not 243 ingame visual acceptances','Unproved native scopes are listed explicitly, never counted as HD covered'],'input_hashes':input_hashes})
print((OUT/'summary.json').read_text()[:1500],flush=True)
issues=[];count=0;total=0
for f in frame_checks:
 path=GAME/'iee-assets/effects'/f['asset'];count+=1;total+=f['bytes']
 if not path.is_file() or path.stat().st_size!=f['bytes'] or sha(path)!=f['sha256'].upper():issues.append(f['asset'])
 if count%2000==0:print('SHA',count,'/',len(frame_checks),flush=True)
carrier_issues=[];carriercount=0
for c in m['runtime_bam_carriers']:
 if c['resref'] not in relevant:continue
 carriercount+=1
 if not (GAME/c['asset']).is_file() or sha(GAME/c['asset'])!=c['sha256'].upper():carrier_issues.append(c['resref'])
save('physical-checks.json',{'manifest_sha256_start':manifest_sha,'manifest_unchanged':sha(GAME/'iee-assets/effects/manifest.json')==manifest_sha,'registry_sha_matches':sha(GAME/'iee-assets/effects'/m['registry'])==m['registry_sha256'].upper(),'frames_checked':count,'bytes_checked':total,'frame_issues':issues,'carriers_checked':carriercount,'carrier_issues':carrier_issues})
print('Finished physical checks',count,'issues',issues,carrier_issues)
