"""Read-only semantic correspondence, including native slots, loop/once profiles and RGB."""
from pathlib import Path
import struct,json,hashlib,sys,collections,time
import numpy as np
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'));from workspace_paths import get_path
GAME=get_path('bg2ee_game_root',required=True);PACK=GAME/'iee-assets/effects'
if (OUT/'alias-correspondence.json').exists():raise SystemExit('Historical verification exists')
m=json.loads((PACK/'manifest.json').read_text());names=['BDWOFOGA','X58WFOG'];resources={r['resref']:r for r in m['resources'] if r['resref'] in names};frames={n:{f['resource_frame']:f for f in m['frames'] if f['resref']==n} for n in names}
a,b=map(resources.get,names)
assert a['cycles']==b['cycles'] and a['rgb_encoding']==b['rgb_encoding']=='straight'
for field in ['native_fps','target_fps','actual_phase_counts_by_cycle','cycle_profiles','once_profiles']:assert a['timeline'][field]==b['timeline'][field],field
# Parse exact active registry; numeric backing IDs can change after alpha deduplication.
raw=(PACK/'EffectAnimations-X4.registry').read_bytes();magic,version,scale,count,res=struct.unpack_from('<8sIIII',raw);assert version==3 and scale==4;pos=24;records={}
def take(fmt):
 global pos
 value=struct.unpack_from('<'+fmt,raw,pos);pos+=struct.calcsize('<'+fmt);return value
for _ in range(count):
 name=raw[pos:pos+8].rstrip(b'\0').decode();pos+=8;fc,cc=take('II');dims=[take('II') for i in range(fc)];native=[]
 for c in range(cc):length,=take('I');native.append(list(take(str(length)+'I')))
 nf,nd,tf,td,maximum=take('IIIII');timeline=[list(take(str(maximum)+'I')) for c in range(cc)];extra,=take('I');once={}
 for e in range(extra):c,length=take('II');once[c]=list(take(str(length)+'I'))
 if name in names:records[name]=dict(dims=dims,native=native,timeline=timeline,once=once,rate=(nf,nd,tf,td),maximum=maximum)
assert pos==len(raw)
x,y=map(records.get,names);assert x['rate']==y['rate'] and x['maximum']==y['maximum'] and x['once'].keys()==y['once'].keys()
pairs=set();contracts=[];semantic_lookups=0
for field in ['native','timeline','once']:
 xx=x[field];yy=y[field];keys=xx.keys() if isinstance(xx,dict) else range(len(xx));assert len(xx)==len(yy)
 for c in keys:
  assert len(xx[c])==len(yy[c])
  for i,j in zip(xx[c],yy[c]):
   for f in ['logical_size_x1','physical_size_x4','source_centre_x1']:assert frames[names[0]][i][f]==frames[names[1]][j][f],(field,c,i,j,f)
   pairs.add((i,j));semantic_lookups+=1
# Independent loader expectations use corrected record, not old numeric indices.
for c,cy in enumerate(b['cycles']):
 for once,table in [(0,y['timeline'][c][:b['timeline']['actual_phase_counts_by_cycle'][c]])]+([(1,y['once'][c])] if c in y['once'] else []):
  for phase,target in enumerate(table):
   slot=min(len(cy['frame_indices'])-1,phase//2);native=table[slot*2] if once else y['native'][c][slot];w,h=y['dims'][target];assert (w,h)==y['dims'][native]
   for n in ['X58WFOG','x58wfog']:contracts.append(f'{n}\t{slot}\t{w}\t{h}\t{phase}\t{c}\t{native}\t{target}\t{once}')
cache={};changed=0;checked=set();alpha_samples=[];start=time.monotonic()
def rgba(n,i):
 f=frames[n][i];data=(PACK/f['asset']).read_bytes();assert len(data)==f['bytes'] and hashlib.sha256(data).hexdigest().upper()==f['sha256'].upper();checked.add((n,i));v=np.frombuffer(data,np.uint8).reshape(-1,4)
 return hashlib.sha256(v[:,:3].tobytes()).hexdigest(),f['sha256'],int(np.unique(v[:,3]).size),float(np.median(v[v[:,3]>0,3])) if np.any(v[:,3]) else 0
for i,j in sorted(pairs):
 for n,v in [('BDWOFOGA',i),('X58WFOG',j)]:
  if (n,v) not in cache:cache[n,v]=rgba(n,v)
 old,new=cache['BDWOFOGA',i],cache['X58WFOG',j];assert old[0]==new[0],(i,j,'RGB differs')
 if old[1]!=new[1]:
  changed+=1
  if len(alpha_samples)<8:alpha_samples.append(dict(old=i,new=j,old_levels=old[2],new_levels=new[2],old_median_nonzero=old[3],new_median_nonzero=new[3]))
proof=dict(schema='bg2-cloud-semantic-alias-correspondence-v1',native='BDWOFOGA',alias='X58WFOG',original_frames=a['frame_count'],corrected_frames=b['frame_count'],numeric_tables_equal=a['timeline']==b['timeline'],native_cycles_equal=True,profile_rates_durations_equal=True,semantic_lookups=semantic_lookups,unique_backing_pairs=len(pairs),physical_backings_SHA_checked=len(checked),visible_and_hidden_RGB_identical=True,geometry_centres_equal=True,alpha_changed_pairs=changed,alpha_samples=alpha_samples,loader_contracts=len(contracts),seconds=time.monotonic()-start,conclusion='Compatible semantic timelines. Numeric backing differences follow alpha deduplication, not changed timing. Reuse existing installed alias only for non-Blended consumers.',inference_jobs=0,images_written=0)
(OUT/'alias-correspondence.json').write_text(json.dumps(proof,indent=2)+'\n',encoding='utf-8');(OUT/'contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii');print(json.dumps(proof),flush=True)
