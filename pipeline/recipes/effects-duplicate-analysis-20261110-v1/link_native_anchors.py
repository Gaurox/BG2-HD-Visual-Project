"""Map native duplicate drawings to existing HD anchor frames; never assume interpolation equality."""
from collections import defaultdict
import json,struct,zlib,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from analyze import ROOT,OUT,RELEASE,load,save,table

def main():
 assert not (OUT/'native-runtime-anchor-summary.json').exists()
 natives={n['resref']:n for n in load(OUT/'native-assets.json') if n['status']=='verified'}
 hashes=defaultdict(list)
 for n,r in natives.items():hashes[r['source_sha256']].append(n)
 dup=load(OUT/'native_pixel_key-groups.json');keys={}
 for g in dup:
  for f in g['members']:keys[f['resref'],f['frame']]=f
 pack=load(RELEASE/'release-inputs/effects/accepted-20261110-v1/manifest.json')
 frames={(f['resref'],f['resource_frame']):f for f in pack['frames']}
 cycles={}
 for n,r in natives.items():
  raw=(ROOT/r['source']).read_bytes();b=zlib.decompress(raw[12:]) if raw[:4]==b'BAMC' else raw
  fo,_,lo=struct.unpack_from('<III',b,12);seq=[]
  for i in range(r['cycle_count']):
   count,start=struct.unpack_from('<HH',b,fo+r['frame_count']*12+i*4);seq.append(list(struct.unpack_from(f'<{count}H',b,lo+start*2)))
  cycles[n]=seq
 links=[];coverage=[]
 for r in pack['resources']:
  ref=r['resref'];origin=r.get('production_bam',ref).split(':')[-1]
  if origin not in natives:
   candidates=hashes.get(r.get('source',{}).get('source_bam_sha256','').upper(),[])
   origin=candidates[0] if candidates else None
  if not origin:
   coverage.append(dict(runtime_ref=ref,status='no-effects-native-source',source='sprite domain or unresolved'));continue
  timing=r.get('timeline',{});mapping=set();method=''
  if 'native_frame_indices_by_cycle' in timing:
   tt=timing['native_frame_indices_by_cycle'];ss=cycles[origin]
   if len(tt)<=len(ss) and all(len(t)==len(ss[i]) for i,t in enumerate(tt)):
    for i,t in enumerate(tt):mapping.update(zip(ss[i],t))
    method='native-cycle-slot-to-anchor'
  elif len(timing.get('native_frame_indices',[]))==natives[origin]['frame_count']:
   mapping.update(enumerate(timing['native_frame_indices']));method='native-frame-to-anchor'
  if not method:
   coverage.append(dict(runtime_ref=ref,source_resref=origin,status='manual-provenance-adapter-required'));continue
  coverage.append(dict(runtime_ref=ref,source_resref=origin,status='mapped',anchors=len(mapping),method=method))
  for nf,hd in sorted(mapping):
   if (origin,nf) not in keys:continue
   f=frames[ref,hd];native=keys[origin,nf]
   links.append(dict(source_resref=origin,native_frame=nf,native_pixel_key=native['native_pixel_key'],
       centre_x=native['centre_x'],centre_y=native['centre_y'],runtime_ref=ref,runtime_frame=hd,
       final_asset=f['asset'],final_sha256=f['sha256'],final_bytes=f['bytes'],
       rgb_encoding=r.get('rgb_encoding','legacy'),palette_context=r.get('palette_job','native/default-or-owner'),
       interpolation_run=r.get('interpolation_run',r.get('source',{}).get('interpolation_run','')),mapping=method))
 table('native-frame-to-runtime-anchor-map.csv',links)
 groups=defaultdict(list)
 for link in links:groups[link['native_pixel_key']].append(link)
 candidates=[]
 for k,members in groups.items():
  if len({x['source_resref'] for x in members})<2:continue
  variants={x['final_sha256'] for x in members}
  candidates.append(dict(native_pixel_key=k,source_resrefs=sorted({x['source_resref'] for x in members}),
      distinct_final_outputs=len(variants),hd_outputs_diverge=len(variants)>1,members=members,
      qualification='Native indexed drawing and palette identical; centres/owner palettes/blend/lighting, generation recipe and interpolation neighbours remain independent. Not automatically mergeable.'))
 save('native-frame-runtime-reuse-candidates.json',candidates);save('native-runtime-anchor-coverage.json',coverage)
 summary=dict(runtime_resources=len(coverage),mapped=sum(x['status']=='mapped' for x in coverage),
      manual_provenance_adapters=sum(x['status']=='manual-provenance-adapter-required' for x in coverage),
      outside_effect_native_inventory=sum(x['status']=='no-effects-native-source' for x in coverage),
      duplicate_native_anchors_mapped=len(links),cross_source_groups_linked=len(candidates),
      cross_source_groups_with_different_HD_outputs=sum(x['hd_outputs_diverge'] for x in candidates),
      no_savings_assumed_for_divergent_outputs=True)
 save('native-runtime-anchor-summary.json',summary);print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
