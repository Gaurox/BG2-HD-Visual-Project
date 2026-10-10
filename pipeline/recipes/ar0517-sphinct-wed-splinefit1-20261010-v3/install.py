"""Install only the new AR0517 occurrence pack with transactional rollback."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
import run_animation_upscale_30fps_v2 as v2
import area_animation_area_test as installer
from workspace_paths import get_path
TAG='ar0517-sphinct-wed-splinefit1-20261010-v3'
OUT=ROOT/'animations/batches'/TAG;GAME=get_path('bg2ee_game_root')
plan=v2.load_json(OUT/'plan.json');checks=v2.load_json(OUT/'checks.json');assert checks['passed']
PACK=ROOT/plan['pack']/'AR0517'
def payload(path):
 return {p.name:v2.sha256_file(p) for p in path.iterdir() if p.is_file() and (p.name==v2.REGISTRY_NAME or p.suffix=='.rgba')}
assert not (OUT/'installation.json').exists()
assert payload(GAME/'iee-assets/areas/AR0517')==plan['before_payload']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==plan['renderer_sha256']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']
others=['AR0516','AR0518','AR0519','AR0520','AR0521','AR0811','OH8100']
before={a:payload(GAME/'iee-assets/areas'/a) for a in others}
dry=installer.install_area_pack(PACK,verify_only=True)
assert not dry.dropped and dry.area_id=='AR0517'
result=installer.install_area_pack(PACK)
installer.record_lock('AR0517',PACK,GAME)
assert payload(GAME/'iee-assets/areas/AR0517')==payload(PACK)
assert before=={a:payload(GAME/'iee-assets/areas'/a) for a in others}
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==plan['renderer_sha256']
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==plan['ini_sha256']
v2.write_json(OUT/'installation.json',dict(status=result.status,created_utc=v2.utc_now(),
 area='AR0517',resref='SPHINCT',occurrence=[497,452],frames=49,
 receipt=result.receipt_path.resolve().relative_to(ROOT).as_posix(),
 source_pack=plan['pack'],source_run=plan['run'],
 mask_sha256=plan['mask_sha256'],fit_error_x4=1,guard_x4=8,feather_x4=8,
 renderer_unchanged=True,ini_unchanged=True,other_area_payloads_preserved=before,
 geometry_centres_cycles_preserved=True,RGB_preserved=True,native_double_feather_avoided=True,
 ingame_QA='pending-user-retest',release='not-selected'))
print('Installed AR0517 SplineFit1 / guard8 / fade8; 49 frames, exact occurrence',flush=True)
