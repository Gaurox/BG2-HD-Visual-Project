"""Install tested scoped renderer only; no map/animation/INI bytes change."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import run_animation_upscale_30fps_v2 as v2
import install_renderer_candidate as renderer
from workspace_paths import get_path
OUT=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1';GAME=get_path('bg2ee_game_root')
tests=v2.load_json(OUT/'native-tests.json');gpu=v2.load_json(OUT/'gpu-tests.json')
assert tests['passed'] and gpu['passed'] and gpu['existing_shader_modes_0_1_byte_identical']
assert not (OUT/'installation.json').exists()
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='748fe476d24ffa32007d33d34f5c6e506b56147570772ee40b810556ad317c56'
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==tests['ini_sha256']
def area_payload(area):
 return {p.name:v2.sha256_file(p) for p in (GAME/'iee-assets/areas'/area).iterdir() if p.is_file()}
areas=['AR0516','AR0517','AR0518','AR0519','AR0520','AR0521','AR0811','OH8100']
before={a:area_payload(a) for a in areas}
renderer.ensure_game_stopped(renderer.running_game_processes)
result=renderer.install_candidate(OUT/'candidate')
renderer.verify_transaction(result.receipt_path)
assert {a:area_payload(a) for a in areas}==before
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==tests['ini_sha256']
v2.write_json(OUT/'installation.json',dict(status=result.status,created_utc=v2.utc_now(),
 renderer_receipt=result.receipt_path.resolve().relative_to(ROOT).as_posix(),
 dll_sha256=tests['dll_sha256'],ini_preserved=True,area_payloads_preserved=before,
 area='AR0517',resref='SPHINCT',occurrence=[497,452],guard_x4=4,feather_x4=16,
 native_frame_centres_unchanged=True,area_coordinates_unchanged=True,wed_files_unchanged=True,
 existing_shader_modes_0_1_byte_identical=True,ingame_QA='pending-user-retest',release='not-selected'))
print('Installed AR0517 SPHINCT WED smoothing; animation/map/INI bytes preserved',flush=True)
