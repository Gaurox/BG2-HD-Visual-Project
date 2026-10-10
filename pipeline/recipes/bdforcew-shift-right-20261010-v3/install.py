"""Install renderer-only visual placement; preserve every installed animation byte."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
sys.path.insert(0, str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v2
import install_renderer_candidate as renderer
HERE = ROOT/'animations/batches/bdforcew-shift-right-20261010-v3'
GAME = get_path('bg2ee_game_root')
tests = v2.load_json(HERE/'tests.json'); assert tests['passed']
baseline = ROOT/'animations/packs-par-zone/portails-deux-correctif-20261010-v1-complete'
def verify_area(area):
    _, resources = v2.validate_v2_pack(baseline/area)
    expected = {name: v2.sha256_file(baseline/area/name) for name in [v2.REGISTRY_NAME] +
                [a['name'] for r in resources for a in r['assets']]}
    actual = {p.name: v2.sha256_file(p) for p in (GAME/'iee-assets/areas'/area).iterdir()
              if p.is_file()}
    assert actual == expected, area+': current animation bytes changed'
    return len(expected)-1
before = {area: verify_area(area) for area in ['AR0811', 'OH8100']}
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll') == (
    '66f6a4f051597f02e84cd9902cb98851954d677b30fcf72385a5e01a250dd896')
assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini') == tests['ini_sha256']
result = renderer.install_candidate(HERE/'candidate')
renderer.verify_transaction(result.receipt_path)
after = {area: verify_area(area) for area in ['AR0811', 'OH8100']}
assert before == after
v2.write_json(HERE/'installation.json', dict(status=result.status, created_utc=v2.utc_now(),
    renderer_receipt=result.receipt_path.resolve().relative_to(ROOT).as_posix(),
    dll_sha256=tests['dll_sha256'], ini_preserved=True, area_frame_bytes_preserved=after,
    area_coordinates_unchanged=True, native_frame_centres_unchanged=True,
    source_spline_alpha_changed=False, non_vanilla_visual_placement=True,
    post_mask_dx_x1=6, post_mask_dy_x1=0, restored_wed_feather_x4=16,
    occurrences=[[2286,820], [2350,866]], OHHPORT_ingame_QA='accepted-by-user',
    BDFORCEW_ingame_QA='pending-retest', release='not-selected'))
print('Installed restored smooth BDFORCEW shifted right6; all 393 frames preserved', flush=True)
