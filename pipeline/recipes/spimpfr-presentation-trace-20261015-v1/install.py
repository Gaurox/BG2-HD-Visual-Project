"""Install diagnostic DLL only, with identical INI and preserved asset hashes."""
from pathlib import Path
import hashlib
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools')]
from workspace_paths import get_path
import install_renderer_candidate as installer

OUT=ROOT/'engine/InfinityEngine-Enhancer/installations/spimpfr-presentation-trace-20261015-v1'
BUILD=ROOT/'build/iee-map-first-frame-refresh-20261014-v1'
BASE=ROOT/'effects/installations/lot33-retimed-7b-x4-nearest-20261014-v2/installation.json'


def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,j):p.write_text(json.dumps(j,indent=2)+'\n',encoding='utf-8')
def hashes(game,names):return {n:installer.sha256_file(game/n) for n in names}


def main():
    game=get_path('bg2ee_game_root',required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    baseline=load(BASE);manifest=load(game/'iee-assets/effects/manifest.json')
    assert manifest['resource_count']==97
    assert installer.sha256_file(game/'iee-assets/effects/manifest.json')==baseline['manifest_sha256']
    assert installer.sha256_file(game/'InfinityEngine-Enhancer.dll')==baseline['dll_sha256']
    names=list(baseline['profile_sha256'])+['iee-assets/effects/manifest.json','iee-assets/effects/EffectAnimations-X4.registry']
    names += [c['asset'] for c in manifest['runtime_bam_carriers']]
    spimpfr=[f for f in manifest['frames'] if f['resref']=='SPIMPFR'];assert len(spimpfr)==118
    names += ['iee-assets/effects/'+f['asset'] for f in spimpfr]
    preserved=hashes(game,names)
    assert {n:preserved[n] for n in baseline['profile_sha256']}==baseline['profile_sha256']
    assert preserved['iee-assets/effects/EffectAnimations-X4.registry']==manifest['registry_sha256']
    for f in spimpfr:assert preserved['iee-assets/effects/'+f['asset']]==f['sha256']
    for c in manifest['runtime_bam_carriers']:assert preserved[c['asset']]==c['sha256']
    dll=BUILD/'Release/InfinityEngine-Enhancer.dll';data=dll.read_bytes()
    for marker in [b'SPIMPFR_PRESENT_BEGIN',b'SPIMPFR_PRESENT_ROW',b'SPIMPFR_PRESENT_END',b'Renderer startup barrier released']:
        assert marker in data,marker
    OUT.mkdir(parents=True,exist_ok=False);candidate=OUT/'candidate';candidate.mkdir()
    shutil.copy2(dll,candidate/'InfinityEngine-Enhancer.dll')
    shutil.copy2(game/'InfinityEngine-Enhancer.ini',candidate/'InfinityEngine-Enhancer.ini')
    save(OUT/'before.json',{'dll_sha256':baseline['dll_sha256'],'preserved_sha256':preserved})
    result=installer.install_candidate(candidate,game_root=game,backup_root=OUT/'backups')
    installer.verify_transaction(result.receipt_path,game_root=game)
    assert set(result.files)=={'InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini'}
    assert hashes(game,names)==preserved
    assert installer.sha256_file(game/'InfinityEngine-Enhancer.dll')==installer.sha256_file(dll)
    report={'schema':'bg2-spimpfr-presentation-trace-install-v1','status':'installed-awaiting-user-controlled-test',
        'dll_sha256':installer.sha256_file(dll),'previous_dll_sha256':baseline['dll_sha256'],
        'receipt':result.receipt_path.relative_to(ROOT).as_posix(),'preserved_sha256':preserved,
        'effect_resources':97,'spimpfr_phases':118,'model':'seedvr2_7b_int8_convrot.safetensors',
        'scale':4,'filter':'NEAREST','target_fps':[30,1],'character_profile':'NearestRGB-SilhouetteAlphaAA',
        'asset_payloads_changed':False,'map_assets_changed':False,'scheduler_changed':False,'shader_changes':False,
        'trace_stage':'post-occlusion draw and actual swap return','max_occurrences':8,'max_swaps_per_occurrence':2048,
        'hot_capture_file_io':False,'gpu_readback':False,'renderer_ctest_passed':7,'analyzer_tests_passed':6,
        'game_launched_by_agent':False,'visual_qa':'pending-user-controlled-game'}
    save(OUT/'installation.json',report)
    print(json.dumps({k:v for k,v in report.items() if k!='preserved_sha256'},indent=2))


if __name__=='__main__':main()
