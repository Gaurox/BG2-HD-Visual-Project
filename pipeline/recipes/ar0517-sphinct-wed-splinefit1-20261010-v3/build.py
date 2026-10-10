"""Bake the chosen world-space WED coverage into one exact AR0517 occurrence."""
from pathlib import Path
import copy,hashlib,json,sys,shutil
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
import split_animation_pack_by_area as splitter
import merge_area_pack_resources as merge
from workspace_paths import get_path
TAG='ar0517-sphinct-wed-splinefit1-20261010-v3'
OUT=ROOT/'animations/batches'/TAG
RUN=ROOT/'animations/ressources/SPHINCT/runs'/TAG
PACK=ROOT/'animations/packs-par-zone'/TAG
BASE=ROOT/'animations/packs-par-zone/combined-20260917-active-plus-visual-regression-fix/AR0517'
METHODS=ROOT/'animations/batches/ar0517-sphinct-wed-methods-20261010-v2'
MASK=METHODS/'spline1-g8-f8-coverage.png'
GAME=get_path('bg2ee_game_root')
def payload(path):
 return {p.name:v2.sha256_file(p) for p in path.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
assert not RUN.exists() and not OUT.exists() and not PACK.exists()
assert payload(GAME/'iee-assets/areas/AR0517')==payload(BASE),'installed AR0517 source drift'
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='ee85fdaba70fd99d0fbf114c6dcee46cf21ccc60a93f8e650a2dbb50abaf42b0'
report=v2.load_json(METHODS/'comparison.json');assert report['recommendation']=='spline1-g8-f8'
meta=next(m for m in report['methods'] if m['id']==report['recommendation'])
assert meta['blocked_on_any_active_frame']==0 and meta['no_occluded_pixel_revealed']
source_manifest,resources=v2.validate_v2_pack(BASE);assert len(resources)==1
resource=copy.deepcopy(resources[0]);assert resource['resref']=='SPHINCT'
coverage=np.asarray(Image.open(MASK).convert('L'))
transfer=np.fromfile(ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1/arch-transfer.rgba',np.uint8).reshape(120,160,4)
native_clear=(transfer[:,:,0]==0).repeat(4,0).repeat(4,1)
assert not coverage[native_clear].any()
OUT.mkdir(parents=True);scratch=RUN/'.work/assets';scratch.mkdir(parents=True)
provenance=RUN/'provenance';provenance.mkdir()
shutil.copy2(MASK,provenance/'world-coverage.png')
sources={};checks=[];assets={a['name']:a for a in resource['assets']}
for frame,original in zip(resource['frames'],resources[0]['frames'],strict=True):
 assert frame['logical_size_x1']==[160,120] and frame['centre_x1']==[77,55]
 w,h=frame['physical_size_x4'];assert coverage.shape==(h,w)
 raw=np.frombuffer((BASE/frame['asset']).read_bytes(),np.uint8).reshape(h,w,4)
 baked=raw.copy();baked[:,:,3]=np.rint(raw[:,:,3].astype(np.float64)*coverage/255.).astype(np.uint8)
 assert np.array_equal(baked[:,:,:3],raw[:,:,:3])
 assert np.all(baked[:,:,3]<=raw[:,:,3]) and not baked[native_clear,3].any()
 assert np.array_equal(baked[coverage==255],raw[coverage==255])
 path=scratch/frame['asset'];path.write_bytes(baked.tobytes());sources[frame['asset']]=path
 digest=v2.sha256_file(path);frame['sha256']=digest;assets[frame['asset']]['sha256']=digest
 checks.append(dict(frame=frame['frame'],source_sha256=original['sha256'],sha256=digest,
  RGB_identical=True,alpha_never_increased=True,unmasked_pixels_exact=True))
# A position-bound v3 entry intentionally bypasses the native bridge: its world
# mask is already baked, so the old guard4/fade16 must not be applied again.
resource['position']=[497,452]
leaf=RUN/'03_runtime_pack'
splitter.write_area_pack(leaf,BASE,source_manifest,[resource],sources,'AR0517')
merge.merge([str(leaf)+'::SPHINCT::497,452'],'AR0517',PACK,False)
_,selected=v2.validate_v2_pack(PACK/'AR0517')
assert selected[0]['position']==[497,452]
assert selected[0]['cycles']==resources[0]['cycles']
v2.write_json(RUN/'manifest.json',dict(schema='bg2-upscale-animation-world-occlusion-spline-v1',
 status='completed',created_utc=v2.utc_now(),resrefs=['SPHINCT'],source_pack=BASE.relative_to(ROOT).as_posix(),
 source_pack_manifest_sha256=v2.sha256_file(BASE/'manifest.json'),runtime_pack='03_runtime_pack',
 runtime_pack_manifest_sha256=v2.sha256_file(leaf/'manifest.json'),output_split_root=PACK.relative_to(ROOT).as_posix(),
 output_manifest_sha256=v2.sha256_file(PACK/'manifest.json'),
 occlusion=dict(area='AR0517',position=[497,452],polygon=3,fit_error_x4=1,supersampling=4,
  guard_x4=8,feather_x4=8,mask='provenance/world-coverage.png',mask_sha256=v2.sha256_file(provenance/'world-coverage.png'),
  mask_origin_world_x4=[1680,1588],semantics='white keeps, black occludes',native_clear_guard_baked=True),
 runtime_contract=dict(position_bound=True,native_bridge_bypassed=True,no_double_feather=True,
  straight_alpha=True,RGB_centres_cycles_geometry_preserved=True),qa='pending-user-ingame-retest'))
v2.write_json(OUT/'checks.json',dict(passed=True,frames=checks,geometry_centres_cycles_preserved=True,
 fixed_world_mask=True,RGB_preserved=True,no_occluded_pixels_revealed=True,
 runtime_registry_position=[497,452],native_bridge_bypassed_by_v3_position_binding=True))
v2.write_json(OUT/'plan.json',dict(status='prepared',run=RUN.relative_to(ROOT).as_posix(),
 pack=PACK.relative_to(ROOT).as_posix(),mask_sha256=v2.sha256_file(MASK),area='AR0517',
 resref='SPHINCT',position=[497,452],before_payload=payload(BASE),
 renderer_sha256=v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll'),
 ini_sha256=v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini'),release='not-selected'))
print('49 frames / exact-position registry / no double feather / AR0517 pack ready',flush=True)
