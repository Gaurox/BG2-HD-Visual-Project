"""Register only the three authorized projectile animation sources and recipes."""
from pathlib import Path
import csv, io, json, sys, hashlib
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as w
import effect_authority as authority
import effect_tracking as tracking
from bg2lib import load_key,resolve_resource
from export_bam_frames import read_bam,cycle_metadata
from bam_export import decode_bam,native_palette_alpha

OUT=ROOT/'effects/batches/projectiles3-production-20261109-v1'
SOURCES={'BGLRYU':('0x0101','smoke-animation',['BGLRY']),
         'SPCL236U':('0x0102','smoke-animation',['SPCL236']),
         'SPGLYPHI':('0x0410','fragment-animation',['TRAPGLPN','TRAPGLYP'])}
def save(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 if (OUT/'batch.json').exists():print('Prepared batch retained');return
 bifs,entries=load_key();key={(n.upper(),t):l for n,t,l in entries}
 inventory=w.read_csv(ROOT/'effects/index/bam-assets.csv');processing=w.read_csv(ROOT/'effects/index/processing.csv')
 work=w.read_csv(ROOT/'effects/index/work-items.csv');consumers=w.read_csv(ROOT/'effects/index/consumers.csv')
 sprites={r['bam_resref']:r for r in w.read_csv(ROOT/'sprite/index/sprite_resources.csv')}
 pros={r['resref']:r for r in w.read_csv(ROOT/'projectiles/index/resources.csv')}
 assert not set(SOURCES)&{r['resref'] for r in inventory},'Already inventoried; inspect before preparing again'
 assets=[];extension=[]
 for ordinal,(n,(aid,role,owners)) in enumerate(SOURCES.items(),1):
  raw,bif=resolve_resource(bifs,key[n,1000]);h=hashlib.sha256(raw).hexdigest().upper();sr=sprites[n]
  assert h==sr['source_sha256'].upper()
  source=ROOT/f'effects/ressources/{n}/source.bam';source.parent.mkdir(parents=True,exist_ok=True)
  if source.exists():assert source.read_bytes()==raw
  else:source.write_bytes(raw)
  decoded=read_bam(source);frames,pal,tr=decode_bam(decoded);cycles=cycle_metadata(decoded,len(frames))
  alpha=native_palette_alpha(decoded,tr)
  info,_,_=tracking.inspect_bam(source,h)
  item={k:'' for k in inventory[0]};item.update(asset_key=f'effects:bam:{n}',resref=n,origin='projectile-animation-member',controller_count=0,projectile_count=len(owners),projectile_keys=';'.join('projectile:'+o for o in owners),bam_container=sr['bam_container'],bam_version=sr['bam_version'],frame_count=len(frames),cycle_count=len(cycles),source_bif=sr['source_bif'],locator=sr['locator'],source_size=len(raw),source_sha256=h,source_state='available',extracted_path=source.relative_to(ROOT).as_posix());inventory.append(item)
  p={k:'' for k in processing[0]};p.update(asset_key=item['asset_key'],asset_directory=source.parent.relative_to(ROOT).as_posix(),spatial_state='not-started',interpolation_state='not-started',qa_state='not-assessed',installation_state='not-installed',release_state='not-evaluated',notes='Authorized 2026-11-09: implicit projectile ANIMATE source; one shared production.');processing.append(p)
  wi={k:'' for k in work[0]};wi.update(asset_key=item['asset_key'],resref=n,source_state='available',canonical_sha256=info['canonical_sha256'],frames=info['frames'],used_frames=info['used_frames'],cycles=len(cycles),empty_cycles=info['empty_cycles'],static=int(info['static']),variable_geometry=int(info['variable_geometry']),raw_x4_bytes=info['raw_x4_bytes'],consumer_count=len(owners),owner_routes='projectile-animation',playback='unknown',tags='alpha;unresolved',usage='known',priority=20,recipe='seedvr2-7b-int8-lab-x4/apollo30',technical_notes='native-animation-owner-rate-to-observe;once-loop-production-profiles',notes=f'ANIMATE {aid}; owners '+','.join(owners));work.append(wi)
  for owner in owners:
   c={k:'' for k in consumers[0]};c.update(asset_key=item['asset_key'],consumer_key='projectile:'+owner,relation=role,via='ANIMATE:'+aid,source_sha256=pros[owner]['source_sha256'],owner_route='projectile-animation',flags_json=json.dumps({'animation_id':aid,'rate_basis':'15FPS compatibility; not measured ingame'},sort_keys=True));consumers.append(c)
  a=dict(ordinal=ordinal,resref=n,source=item['extracted_path'],source_sha256=h,native_cycles=cycles,native_fps=[],profile='H',sigma_x4=0,inner_feather_x4=0,mask_alpha_authoritative=True,green_index=None,reuse_aliases=[],spatial_run=f'{n.lower()}-seedvr7b-x4-20261109-v1',interpolation_run=f'{n.lower()}-apollo30-20261109-v1',pack=f'effects/ressources/{n}/packs/{n.lower()}-apollo30-initial-20261109-v1',final_pack=f'effects/ressources/{n}/packs/{n.lower()}-x4-apollo30-profiles-20261109-v1',animation_id=aid,role=role,owners=owners,source_alpha_levels=sorted(set(int(x) for x in alpha)))
  assets.append(a);extension.append(dict(resref=n,animation_id=aid,role=role,projectiles=owners,source_sha256=h))
 changes={}
 for path,rows in [('effects/index/bam-assets.csv',inventory),('effects/index/processing.csv',processing),('effects/index/work-items.csv',work),('effects/index/consumers.csv',consumers)]:
  rows.sort(key=lambda r:(r['asset_key'],r.get('consumer_key',''),r.get('relation','')))
  stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=tuple(rows[0]),lineterminator='\r\n');writer.writeheader();writer.writerows(rows)
  changes[path]=b'\xef\xbb\xbf'+stream.getvalue().encode('utf-8')
 changes['effects/index/projectile-animation-sources.json']=w.json_bytes({'schema':'bg2-effects-projectile-animation-sources-v1','assets':extension,'evidence':'projectiles/analysis/20261109-finalisation-analyse-v1/README.md'})
 with authority.guard(ROOT,True):authority.commit(ROOT,changes)
 save(OUT/'batch.json',dict(schema='bg2-effects-production-batch-v1',date='2026-11-09',authorization='User: ok vas y pour les 3; BGLRYU/SPCL236U/SPGLYPHI production only.',assets=assets,native_masks=[],scope='New sources only; no prior QA, installation or release promotion.'))
 print('Prepared',len(assets),'sources,',sum(len(a['native_cycles']) for a in assets),'cycles,',sum(len(decode_bam(read_bam(ROOT/a['source']))[0]) for a in assets),'frames')
if __name__=='__main__':main()
