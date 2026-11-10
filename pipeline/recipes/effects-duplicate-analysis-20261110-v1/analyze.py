"""Read-only native-source and delivered-byte duplicate audit; no asset promotion."""
from collections import defaultdict, Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import csv, hashlib, json, struct, sys, zlib

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'effects/research/duplicate-analysis-20261110-v1'
RELEASE=ROOT/'releases/BG2-HD-Upscale'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))

def digest(raw):return hashlib.sha256(raw).hexdigest().upper()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(name,value):
 p=OUT/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def table(name,rows,fields=None):
 with (OUT/name).open('w',encoding='utf-8',newline='') as f:
  w=csv.DictWriter(f,fieldnames=fields or list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
def rel(p):return p.relative_to(ROOT).as_posix()

def indices(data,offset,n,tr,compressed):
 if not compressed:return data[offset:offset+n]
 out=bytearray();marker=bytes([tr]);p=offset
 while len(out)<n:
  stop=data.find(marker,p);remaining=n-len(out)
  take=remaining if stop<0 else min(stop-p,remaining)
  out.extend(data[p:p+take]);p+=take
  if len(out)==n:break
  assert data[p]==tr and p+1<len(data)
  count=min(data[p+1]+1,n-len(out));out.extend(marker*count);p+=2
 assert len(out)==n
 return bytes(out)

def native(row):
 path=ROOT/row['extracted_path']
 if row['source_state']!='available':return dict(resref=row['resref'],status='source-missing'),[]
 raw=path.read_bytes();assert digest(raw)==row['source_sha256'].upper(),path
 data=zlib.decompress(raw[12:]) if raw[:4]==b'BAMC' else raw
 assert data[:8]==b'BAM V1  ',path
 nf,nc,tr=struct.unpack_from('<HBB',data,8);fo,po,lo=struct.unpack_from('<III',data,12)
 palette=data[po:po+1024];assert len(palette)==1024
 frames=[];geometry=[];pixels=[]
 for i in range(nf):
  w,h,cx,cy,off=struct.unpack_from('<HHhhI',data,fo+i*12)
  pix=indices(data,off&0x7fffffff,w*h,tr,not bool(off&0x80000000))
  assert len(pix)==w*h
  # Full native BGRA palette and index identity preserve palette/normal/additive semantics.
  key=digest(struct.pack('<HHB',w,h,tr)+palette+pix)
  geom=digest(bytes.fromhex(key)+struct.pack('<hh',cx,cy))
  frames.append(dict(resref=row['resref'],frame=i,width=w,height=h,centre_x=cx,centre_y=cy,
                     indexed_pixels_sha256=digest(pix),palette_sha256=digest(palette),transparent_index=tr,
                     native_pixel_key=key,native_geometry_key=geom,empty_geometry=not(w and h)))
  pixels.append(key);geometry.append(geom)
 cycles=[]
 for i in range(nc):
  n,start=struct.unpack_from('<HH',data,fo+nf*12+i*4)
  seq=list(struct.unpack_from(f'<{n}H',data,lo+start*2));assert all(x<nf for x in seq)
  cycles.append(seq)
 semantic=digest(json.dumps([geometry,cycles],separators=(',',':')).encode())
 return dict(resref=row['resref'],status='verified',source=rel(path),source_bytes=len(raw),
             source_sha256=digest(raw),uncompressed_sha256=digest(data),semantic_sha256=semantic,
             frame_count=nf,cycle_count=nc,palette_sha256=digest(palette),transparent_index=tr),frames

def main():
 assert not (OUT/'summary.json').exists(),'Use a new analysis version'
 OUT.mkdir(parents=True,exist_ok=True)
 rows=list(csv.DictReader((ROOT/'effects/index/bam-assets.csv').open(encoding='utf-8-sig',newline='')))
 natives=[];native_frames=[]
 with ThreadPoolExecutor(max_workers=8) as pool:
  for i,(record,frames) in enumerate(pool.map(native,rows)):
   natives.append(record);native_frames+=frames
   if (i+1)%100==0:print(f'Native sources {i+1}/{len(rows)}',flush=True)
 # Independently cross-check the decoder against the existing pipeline on three complete BAMs.
 from bam_export import decode_bam
 by_native={n['resref']:n for n in natives};by_nf=defaultdict(list)
 for f in native_frames:by_nf[f['resref']].append(f)
 for name in ['1WDCCDAM','SPMAGMIS','ARARROW']:
  raw=(ROOT/by_native[name]['source']).read_bytes();data=zlib.decompress(raw[12:]) if raw[:4]==b'BAMC' else raw
  decoded,_,_=decode_bam(data)
  for a,b in zip(decoded,by_nf[name]):
   if not b['empty_geometry']:assert digest(a[0].tobytes())==b['indexed_pixels_sha256'] and (a[1],a[2])==(b['centre_x'],b['centre_y'])
 save('native-assets.json',natives)
 native_group_counts={}
 for mode in ['source_sha256','uncompressed_sha256','semantic_sha256']:
  groups=defaultdict(list)
  for r in natives:
   if r['status']=='verified':groups[r[mode]].append(r['resref'])
  dup=[dict(identity=k,resrefs=v) for k,v in sorted(groups.items()) if len(v)>1]
  save('native-'+mode+'-groups.json',dup);native_group_counts[mode]=dict(groups=len(dup),assets=sum(len(g['resrefs']) for g in dup))
 for mode in ['native_pixel_key','native_geometry_key']:
  groups=defaultdict(list)
  for r in native_frames:groups[r[mode]].append(r)
  dup=[dict(identity=k,members=v,cross_resref=len({f['resref'] for f in v})>1) for k,v in sorted(groups.items()) if len(v)>1]
  save(mode+'-groups.json',dup)
  native_group_counts[mode]=dict(groups=len(dup),members=sum(len(g['members']) for g in dup),cross_resref_groups=sum(g['cross_resref'] for g in dup))
 selections={p.stem:load(p) for p in (ROOT/'effects/index/selections').glob('*.json')}
 current=[e for e in load(RELEASE/'manifests/content.json')['entries'] if e['kind']=='effect']
 pack=load(ROOT/next(e['source'] for e in current if e['destination']=='iee-assets/effects/manifest.json'))
 fm={f['asset']:f for f in pack['frames']};resources={r['resref']:r for r in pack['resources']}
 def verify(e):
  p=ROOT/e['source'];before=p.stat();raw=p.read_bytes();after=p.stat()
  assert len(raw)==e['bytes'] and digest(raw)==e['sha256'],e['source']
  assert (before.st_size,before.st_mtime_ns)==(after.st_size,after.st_mtime_ns)
  stage=RELEASE/'bg2hd/payload-allvalidated'/e['payload_group']/p.name
  assert stage.stat().st_size==e['bytes']
  return dict(e,inode=after.st_ino,device=after.st_dev,nlink=after.st_nlink,stage=rel(stage))
 verified=[]
 with ThreadPoolExecutor(max_workers=12) as pool:
  for i,e in enumerate(pool.map(verify,current)):
   verified.append(e)
   if (i+1)%10000==0:print(f'Final bytes verified {i+1}/{len(current)}',flush=True)
 groups=defaultdict(list)
 for e in verified:groups[(e['sha256'],e['bytes'])].append(e)
 duplicate_groups=[(k,v) for k,v in groups.items() if len(v)>1]
 def verify_group(item):
  (sha,size),members=item;members=sorted(members,key=lambda e:(Path(e['source']).name not in fm or fm[Path(e['source']).name]['resref'] not in selections,e['source']))
  canonical=members[0];raw=(ROOT/canonical['source']).read_bytes()
  for e in members:
   assert (ROOT/e['source']).read_bytes()==raw,e['source']
   assert (ROOT/e['stage']).read_bytes()==raw,e['stage']
  details=[]
  for e in members:
   f=fm.get(Path(e['source']).name);r=resources[f['resref']] if f else {}
   details.append(dict(source=e['source'],stage=e['stage'],destination=e['destination'],
         resref=f['resref'] if f else Path(e['source']).stem,resource_frame=f['resource_frame'] if f else None,
         dimensions=f['physical_size_x4'] if f else None,production_bam=r.get('production_bam'),rgb_encoding=r.get('rgb_encoding','legacy')))
  is_image=all(x['dimensions'] is not None for x in details)
  comp=zlib.compressobj(6,zlib.DEFLATED,-15);compressed=len(comp.compress(raw))+len(comp.flush())
  return dict(blob_sha256=sha,bytes=size,copies=len(members),redundant_bytes=size*(len(members)-1),
      type='rgba' if is_image else Path(canonical['source']).suffix.lower(),canonical_source=canonical['source'],
      bytewise_source_and_stage_verified=True,all_zero=raw.count(0)==len(raw),
      mixed_dimensions=len({tuple(x['dimensions']) for x in details if x['dimensions']})>1,
      mixed_encodings=len({x['rgb_encoding'] for x in details})>1,
      deflate6_duplicate_payload_bytes=compressed*(len(members)-1),members=details)
 with ThreadPoolExecutor(max_workers=8) as pool:dups=list(pool.map(verify_group,duplicate_groups))
 dups.sort(key=lambda g:(-g['redundant_bytes'],g['blob_sha256']))
 save('final-identical-byte-groups.json',dups)
 mapping=[];per_resource=defaultdict(lambda:dict(files=0,bytes=0,redundant_files=0,redundant_bytes=0))
 dup_lookup={m['source']:g for g in dups for m in g['members']}
 for e in verified:
  f=fm.get(Path(e['source']).name);ref=f['resref'] if f else Path(e['source']).stem;g=dup_lookup.get(e['source']);canonical=g['canonical_source'] if g else e['source'];redundant=canonical!=e['source']
  mapping.append(dict(source=e['source'],stage=e['stage'],destination=e['destination'],resref=ref,
      frame=f['resource_frame'] if f else '',physical_width=f['physical_size_x4'][0] if f else '',physical_height=f['physical_size_x4'][1] if f else '',
      blob_sha256=e['sha256'],bytes=e['bytes'],canonical_source=canonical,redundant=int(redundant),
      plan='shared-image-blob' if f and g else ('installer-native-copy-only' if g else 'unique-retain')))
  rr=per_resource[ref];rr['files']+=1;rr['bytes']+=e['bytes'];rr['redundant_files']+=redundant;rr['redundant_bytes']+=e['bytes'] if redundant else 0
 table('final-file-to-blob-map.csv',mapping)
 table('final-savings-by-resource.csv',[dict(resref=k,**v) for k,v in sorted(per_resource.items(),key=lambda kv:-kv[1]['redundant_bytes'])])
 # Whole native source equality predicts candidates, not safe equality of neural outputs.
 native_candidates=[]
 for g in load(OUT/'native-semantic_sha256-groups.json'):
  members=[]
  for name in g['resrefs']:
   s=selections.get(name);signature=None;raw_bytes=0
   if s and s['mode']=='x4':
    m=load(ROOT/s['runtime_pack']['manifest']['path']);ff=[f for f in m['frames'] if f.get('resref',m.get('resref'))==name]
    signature=digest(json.dumps([(f['sha256'],f['physical_size_x4']) for f in ff],separators=(',',':')).encode());raw_bytes=sum(f['bytes'] for f in ff)
   members.append(dict(resref=name,selection_mode=s.get('mode') if s else 'not-selected',selected_run=s.get('selected_run') if s else None,selected_output_signature=signature,selected_raw_bytes=raw_bytes))
  sigs={m['selected_output_signature'] for m in members if m['selected_output_signature']}
  native_candidates.append(dict(native_identity=g['identity'],members=members,selected_outputs_differ=len(sigs)>1,
      automatic_sharing_allowed=False,reason='Native identity only; retain each runtime geometry/palette/clock and QA. Output convergence requires an explicit retained-reference choice.'))
 save('native-whole-source-reuse-candidates.json',native_candidates)
 categories={}
 for kind in sorted({g['type'] for g in dups}):
  gg=[g for g in dups if g['type']==kind];categories[kind]=dict(groups=len(gg),redundant_files=sum(g['copies']-1 for g in gg),saved_bytes=sum(g['redundant_bytes'] for g in gg),deflate6_duplicate_payload_bytes=sum(g['deflate6_duplicate_payload_bytes'] for g in gg))
 summary=dict(status='complete',scope='alpha.8 effects: native inventory497 + all72756 final effect files; no cropping or source replacement',native_assets=len(natives),native_verified=sum(n['status']=='verified' for n in natives),native_frames=len(native_frames),native_duplicate_counts=native_group_counts,
      native_equal_whole_sources_with_divergent_selected_outputs=sum(g['selected_outputs_differ'] for g in native_candidates),
      final_files=len(verified),final_bytes=sum(e['bytes'] for e in verified),unique_final_bytes=sum(k[1] for k in groups),
      exact_redundant_files=sum(g['copies']-1 for g in dups),exact_saved_bytes=sum(g['redundant_bytes'] for g in dups),
      categories=categories,all_zero_duplicate_groups=sum(g['all_zero'] for g in dups),mixed_dimension_groups=sum(g['mixed_dimensions'] for g in dups),
      distinct_source_file_ids=len({(e['device'],e['inode']) for e in verified}),
      implementation='Keep registry v3 logical frames, cycles, centres and independent palette/GPU cache identities. Add compact optional storage indirection; adapt both preload and streaming readers. Preserve native BAM/VVC/PRO destinations via installer copies; do not collapse their engine identities.',
      net_index_cost_example_bytes=len(pack['frames'])*4,
      archive_gain='Exact sum of redundant independently DEFLATE6-compressed file payloads measured; container/path/index overhead excluded.',
      native_opportunity_gain='Not counted as an immediately realizable byte saving when selected outputs differ; requires selection and compatibility work.',
      assets_modified=False,release_modified=False,new_QA=False)
 save('summary.json',summary);print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':main()
