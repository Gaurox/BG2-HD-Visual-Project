"""Extend accepted crisp world-spline occlusion to all affected planar occurrences."""
from pathlib import Path
import copy,sys,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from scipy.interpolate import splprep,splev
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as splitter
import merge_area_pack_resources as merge
from build_spline_alpha_mask import resample_closed
from workspace_paths import get_path
TAG='planar-sphinct-wed-crisp-20261010-v6';OUT=ROOT/'animations/batches'/TAG
RUN=ROOT/'animations/ressources/SPHINCT/runs'/TAG;PACK=ROOT/'animations/packs-par-zone'/TAG
GAME=get_path('bg2ee_game_root');report=v2.load_json(OUT/'analysis-all-phases.json');assert not RUN.exists() and not PACK.exists()
RUN.mkdir(parents=True);scratch=RUN/'.work';scratch.mkdir();provenance=RUN/'provenance';provenance.mkdir()
def payload(path):
 return {p.name:v2.sha256_file(p) for p in path.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
def coverage(polygons,origin,size):
 pad=32;ss=4;padded=(size[0]+pad*2,size[1]+pad*2);high=Image.new('L',(padded[0]*ss,padded[1]*ss),0);draw=ImageDraw.Draw(high)
 for p in polygons:
  points=np.array(p['points'],float)*4;samples=resample_closed(points,1.5)
  tck,_=splprep(samples.T,s=len(samples),per=True,k=3)
  curve=np.asarray(splev(np.linspace(0,1,len(samples)*3,endpoint=False),tck)).T
  draw.polygon([tuple((v-origin+pad)*ss) for v in curve],fill=255)
 clear=255-np.array(high);return np.array(Image.fromarray(clear).resize(padded,Image.Resampling.BOX))[pad:-pad,pad:-pad]
def native_coverage(polygons,origin,size):
 small=Image.new('L',(size[0]//4,size[1]//4),0);draw=ImageDraw.Draw(small)
 for p in polygons:draw.polygon([tuple(np.array(v)-origin/4) for v in p['points']],fill=255)
 return (255-np.array(small)).repeat(4,0).repeat(4,1)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def show(bg,raw,cov,origin,box):
 back=np.asarray(bg.crop(box)).astype(float);alpha=np.rint(raw[:,:,3].astype(float)*cov/255)[:,:,None]/255
 scene=Image.fromarray(np.rint(back*(1-alpha)+raw[:,:,:3]*alpha).clip(0,255).astype(np.uint8))
 return scene
cellsbg=Image.open(ROOT/'maps/AR0517/runs/seedvr2-7b-int8-lab-direct-x4/tuiles-principales/01_upscale/AR0517-tuiles-principales-x4-seedvr2-7b-int8-lab.png').convert('RGB')
mainbg=Image.open(ROOT/'maps/AR0516/runs/seedvr2-7b-int8-lab-grid-2x3-x4/tuiles-principales/03_assemble/AR0516-tuiles-principales-x4-seedvr2-7b-int8-lab-overlap.png').convert('RGB')
checks=[];areas=[];preserved=[]
for area,info in report['areas'].items():
 base=ROOT/info['base'];manifest,originals=v2.validate_v2_pack(base)
 assert payload(GAME/'iee-assets/areas'/area)==payload(base),area+' installed drift'
 new=[];sources={};area_checks=[]
 if area=='AR0516':
  # Native fallback serves occurrence0 only; other animations and SPHINCT2 keep exact bytes/contract.
  new=copy.deepcopy(originals);sources={a['name']:base/a['name'] for r in originals for a in r['assets']}
 for occ in info['occurrences']:
  pos=[occ['x'],occ['y']];resref=occ['resource_resref']
  r=copy.deepcopy(next(r for r in originals if r['resref']==resref))
  if area=='AR0516':
   chosen=[d['polygon'] for d in info['intersections'] if d['occurrence']==occ['occurrence_index'] and d['polygon']['flags']&8 and d['polygon']['active_pixels_max_all_frames']>0]
   if not chosen:
    preserved.append(dict(area=area,resref=resref,position=pos,reason='No active cover polygon intersects any frame'));continue
  else:
   assert info['wed_sha256']==report['areas']['AR0517']['wed_sha256']
   chosen=[next(d['polygon'] for d in info['intersections'] if d['polygon']['index']==3)]
  # For cells use the original unmasked source, including AR0517's accepted reference.
  if area=='AR0517':
   source_base=ROOT/'animations/packs-par-zone/combined-20260917-active-plus-visual-regression-fix/AR0517'
   r=copy.deepcopy(v2.validate_v2_pack(source_base)[1][0])
  else:source_base=base
  w,h=r['frames'][0]['physical_size_x4'];cx,cy=r['frames'][0]['centre_x1'];origin=(np.array(pos)-[cx,cy])*4
  cov=coverage(chosen,origin,(w,h));name=f'{area}-{resref}-{pos[0]}-{pos[1]}'
  Image.fromarray(cov).save(provenance/(name+'-coverage.png'))
  if area=='AR0517':
   accepted=np.array(Image.open(ROOT/'animations/ressources/SPHINCT/runs/ar0517-sphinct-wed-crisp-20261010-v5/provenance/world-coverage.png'))
   assert np.array_equal(accepted,cov),'reference differs from accepted AR0517'
  bound=copy.deepcopy(r);bound['position']=pos
  aset={a['name']:a for a in bound['assets']};local_sources={};fchecks=[]
  work=scratch/name;work.mkdir()
  for f,old in zip(bound['frames'],r['frames'],strict=True):
   assert f['centre_x1']==[cx,cy] and f['physical_size_x4']==[w,h]
   raw=np.frombuffer((source_base/f['asset']).read_bytes(),np.uint8).reshape(h,w,4);baked=raw.copy()
   baked[:,:,3]=np.rint(raw[:,:,3].astype(float)*cov/255).astype(np.uint8)
   assert np.array_equal(baked[:,:,:3],raw[:,:,:3]) and np.all(baked[:,:,3]<=raw[:,:,3])
   assert not baked[cov==0,3].any() and np.array_equal(baked[cov==255],raw[cov==255])
   if area=='AR0517':
    active=next(a for a in originals[0]['frames'] if a['frame']==f['frame'])
    assert baked.tobytes()==(base/active['asset']).read_bytes(),'accepted reference bytes changed'
   path=work/f['asset'];path.write_bytes(baked.tobytes());local_sources[f['asset']]=path
   digest=v2.sha256_file(path);f['sha256']=digest;aset[f['asset']]['sha256']=digest
   fchecks.append(dict(frame=f['frame'],sha256=digest,RGB_preserved=True,fully_occluded_alpha_zero=True))
   if f['frame']==8:
    bg=mainbg if area=='AR0516' else cellsbg;box=(*origin,*(origin+[w,h]));before=native_coverage(chosen,origin,(w,h))
    board=Image.new('RGB',(w*2,h+35),(20,23,29));draw=ImageDraw.Draw(board)
    draw.text((8,8),name+' : natif x1',font=font,fill='white');draw.text((w+8,8),'Spline Fit1 / coupe nette',font=font,fill='white')
    board.paste(show(bg,raw,before,origin,box),(0,35));board.paste(show(bg,raw,cov,origin,box),(w,35));board.save(OUT/(name+'-comparison.png'))
  # Distinct exact-position variants use native-free baked occlusion, no fallback collision.
  variant=len([v for v in new if v['resref']==resref]);local_sources=merge.retarget_variant(bound,variant,local_sources)
  new.append(bound);sources.update(local_sources)
  meta=dict(area=area,resref=resref,position=pos,polygons=[p['index'] for p in chosen],frames=len(fchecks),mask='provenance/'+name+'-coverage.png',
   mask_sha256=v2.sha256_file(provenance/(name+'-coverage.png')),origin_world_x4=origin.tolist(),guard_x4=0,feather_x4=0,fit_error_x4=1,supersampling=4,
   frames_verified=fchecks,source_pack=source_base.relative_to(ROOT).as_posix(),native_bridge_bypassed=True,reference_unchanged=area=='AR0517')
  checks.append(meta);area_checks.append(meta)
 if area=='AR0517':
  areas.append(dict(area=area,status='already-installed-identical-reference',base=info['base'],before_payload=payload(base)));continue
 # Sort variants exactly as registry_v2_from_resources requires; assign stable variant0 fallback and bound variants by position.
 renamed_sources={}
 for resref in sorted({r['resref'] for r in new}):
  variants=sorted([r for r in new if r['resref']==resref],key=lambda r:(v2.resource_position(r) is not None,v2.resource_position(r) or (0,0)))
  for idx,variant in enumerate(variants):renamed_sources.update(merge.retarget_variant(variant,idx,sources))
 new=sorted(new,key=v2.resource_sort_key);dest=PACK/area
 splitter.write_area_pack(dest,base,manifest,new,renamed_sources,area)
 _,built=v2.validate_v2_pack(dest)
 for old in originals:
  if area=='AR0516':
   unchanged=next(r for r in built if r['resref']==old['resref'] and r.get('position') is None)
   assert unchanged['cycles']==old['cycles'] and unchanged['frames']==old['frames']
   for a in old['assets']:assert (dest/a['name']).read_bytes()==(base/a['name']).read_bytes()
 assert all(r['position']==c['position'] for r,c in zip([r for r in built if r.get('position') is not None],sorted(area_checks,key=lambda c:tuple(c['position'])),strict=True))
 areas.append(dict(area=area,status='prepared',pack=dest.relative_to(ROOT).as_posix(),base=info['base'],before_payload=payload(base),target_positions=[c['position'] for c in area_checks]))
v2.write_json(PACK/'manifest.json',dict(schema='bg2-upscale-area-animation-split-index-v1',status='completed',created_utc=v2.utc_now(),areas=areas))
v2.write_json(RUN/'manifest.json',dict(schema='bg2-upscale-animation-world-occlusion-planar-v1',status='completed',created_utc=v2.utc_now(),resrefs=['SPHINCT'],areas=areas,
 occlusion=checks,preserved_occurrences=preserved,QA='AR0517 user accepted reference; modified AR0516/18/19/20/21 pending ingame',release='not-selected'))
v2.write_json(OUT/'checks.json',dict(passed=True,occurrences=checks,preserved_occurrences=preserved,AR0517_reference_byte_identical=True,AR0516_fallback_and_sibling_resources_byte_identical=True))
v2.write_json(OUT/'plan.json',dict(status='prepared',areas=areas,run=RUN.relative_to(ROOT).as_posix(),pack=PACK.relative_to(ROOT).as_posix(),
 renderer_sha256=v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll'),ini_sha256=v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini'),
 protected_areas=['AR0811','OH8100'],reference_area='AR0517',release='not-selected'))
print('Prepared AR0516 3 bound variants + AR0518-21 4 cells; accepted AR0517 exact; source RGB/cycles unchanged',flush=True)
