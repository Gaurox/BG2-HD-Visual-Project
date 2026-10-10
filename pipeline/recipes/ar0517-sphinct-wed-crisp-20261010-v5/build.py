"""Build the exact user-selected v4 right preview; AR0517 occurrence only."""
from pathlib import Path
import copy,sys,shutil
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as splitter
import merge_area_pack_resources as merge
from workspace_paths import get_path
TAG='ar0517-sphinct-wed-crisp-20261010-v5'
OUT=ROOT/'animations/batches'/TAG
RUN=ROOT/'animations/ressources/SPHINCT/runs'/TAG
PACK=ROOT/'animations/packs-par-zone'/TAG
BASE=ROOT/'animations/packs-par-zone/combined-20260917-active-plus-visual-regression-fix/AR0517'
BEFORE=ROOT/'animations/packs-par-zone/ar0517-sphinct-wed-splinefit1-20261010-v3/AR0517'
PREVIEW=ROOT/'animations/batches/ar0517-sphinct-wed-crisp-analysis-20261010-v4'
MASK=PREVIEW/'crisp-g0-coverage.png'
GAME=get_path('bg2ee_game_root')
def payload(path):
 return {p.name:v2.sha256_file(p) for p in path.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
assert not RUN.exists() and not OUT.exists() and not PACK.exists()
assert payload(GAME/'iee-assets/areas/AR0517')==payload(BEFORE),'installed AR0517 drift'
report=v2.load_json(PREVIEW/'analysis.json');assert report['recommendation']=='crisp-g0'
assert report['fit_error_x4']==1 and report['supersampling']==4
source_manifest,resources=v2.validate_v2_pack(BASE);assert len(resources)==1
resource=copy.deepcopy(resources[0]);assert resource['resref']=='SPHINCT'
coverage=np.array(Image.open(MASK).convert('L'));assert coverage.shape==(480,640)
OUT.mkdir(parents=True);scratch=RUN/'.work/assets';scratch.mkdir(parents=True)
provenance=RUN/'provenance';provenance.mkdir();shutil.copy2(MASK,provenance/'world-coverage.png')
sources={};checks=[];assets={a['name']:a for a in resource['assets']}
bg=Image.open(ROOT/'maps/AR0517/runs/seedvr2-7b-int8-lab-direct-x4/tuiles-principales/01_upscale/AR0517-tuiles-principales-x4-seedvr2-7b-int8-lab.png').convert('RGB')
for frame,original in zip(resource['frames'],resources[0]['frames'],strict=True):
 assert frame['logical_size_x1']==[160,120] and frame['centre_x1']==[77,55]
 w,h=frame['physical_size_x4'];assert coverage.shape==(h,w)
 raw=np.frombuffer((BASE/frame['asset']).read_bytes(),np.uint8).reshape(h,w,4)
 baked=raw.copy();baked[:,:,3]=np.rint(raw[:,:,3].astype(float)*coverage/255).astype(np.uint8)
 assert np.array_equal(baked[:,:,:3],raw[:,:,:3])
 assert np.all(baked[:,:,3]<=raw[:,:,3]) and not baked[coverage==0,3].any()
 assert np.array_equal(baked[coverage==255],raw[coverage==255])
 if frame['frame']==8:
  origin=(1680,1588);box=(1680,1588,2320,2068);back=np.asarray(bg.crop(box)).astype(float)
  alpha=baked[:,:,3,None].astype(float)/255;scene=bg.copy()
  scene.paste(Image.fromarray(np.rint(back*(1-alpha)+baked[:,:,:3]*alpha).clip(0,255).astype(np.uint8)),origin)
  assert np.array_equal(np.asarray(scene.crop((1600,1528,2360,2128))),np.asarray(Image.open(PREVIEW/'crisp-g0-frame8.png'))),'shown preview differs from candidate'
 path=scratch/frame['asset'];path.write_bytes(baked.tobytes());sources[frame['asset']]=path
 digest=v2.sha256_file(path);frame['sha256']=digest;assets[frame['asset']]['sha256']=digest
 checks.append(dict(frame=frame['frame'],source_sha256=original['sha256'],sha256=digest,RGB_identical=True,alpha_never_increased=True,unmasked_pixels_exact=True))
# Keep the selected continuous spline; no clamp to the stair-stepped x1 gate.
# Bound registry skips native occlusion so the baked mask is applied once.
resource['position']=[497,452];leaf=RUN/'03_runtime_pack'
splitter.write_area_pack(leaf,BASE,source_manifest,[resource],sources,'AR0517')
merge.merge([str(leaf)+'::SPHINCT::497,452'],'AR0517',PACK,False)
_,selected=v2.validate_v2_pack(PACK/'AR0517')
assert selected[0]['position']==[497,452] and selected[0]['cycles']==resources[0]['cycles']
v2.write_json(RUN/'manifest.json',dict(schema='bg2-upscale-animation-world-occlusion-spline-v1',status='completed',created_utc=v2.utc_now(),resrefs=['SPHINCT'],
 source_pack=BASE.relative_to(ROOT).as_posix(),runtime_pack='03_runtime_pack',output_split_root=PACK.relative_to(ROOT).as_posix(),
 preview_source=PREVIEW.relative_to(ROOT).as_posix(),preview_variant='crisp-g0',preview_frame8_exact=True,
 occlusion=dict(area='AR0517',position=[497,452],polygon=3,fit_error_x4=1,supersampling=4,guard_x4=0,feather_x4=0,
  mask='provenance/world-coverage.png',mask_sha256=v2.sha256_file(MASK),mask_origin_world_x4=[1680,1588],semantics='white keeps, black occludes',
  native_clear_guard_baked=False,edge_coverage='SS4 BOX antialias only'),
 runtime_contract=dict(position_bound=True,native_bridge_bypassed=True,no_double_feather=True,straight_alpha=True,RGB_centres_cycles_geometry_preserved=True),qa='pending-user-ingame-retest'))
v2.write_json(OUT/'checks.json',dict(passed=True,frames=checks,geometry_centres_cycles_preserved=True,fixed_world_mask=True,RGB_preserved=True,
 preview_frame8_exact=True,fully_occluded_alpha_zero=True,runtime_registry_position=[497,452],native_bridge_bypassed_by_position_binding=True))
v2.write_json(OUT/'plan.json',dict(status='prepared',run=RUN.relative_to(ROOT).as_posix(),pack=PACK.relative_to(ROOT).as_posix(),mask_sha256=v2.sha256_file(MASK),
 area='AR0517',resref='SPHINCT',position=[497,452],before_payload=payload(BEFORE),renderer_sha256=v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll'),
 ini_sha256=v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini'),release='not-selected'))
print('49 frames / exact right preview / Fit1 SS4 / guard0 fade0 / AR0517 only',flush=True)
