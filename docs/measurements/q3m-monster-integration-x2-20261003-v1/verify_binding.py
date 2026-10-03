"""Exercise six Monster profile bindings inside the new mixed catalog; reuse phase-5 pixel oracles."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from palette_monster_work_plan import require
from workspace_paths import get_path


def read(p):return json.loads(p.read_text())


def main():
    out=HERE/'work/binding';require(not out.exists(),'new native binding proof required');out.mkdir(parents=True)
    pointer=read(HERE/'current-generation.json');packroot=ROOT/pointer['generation_dir'];pack=read(packroot/'pack.json')
    require(file_sha(packroot/'pack.json')==pointer['manifest_sha256'],'integrated manifest changed')
    phase5=read(ROOT/'docs/measurements/q3m-monster-complete-x2-20261003-v1/verification.json')
    exe=ROOT/'.work/q3m-monster-phase4-20261003-v1/build/Release/iee_palette_monster_tests.exe'
    require(file_sha(exe)==phase5['native']['host_executable_sha256'],'acquired reader changed')
    wanted={'MBEHG1','MBEHG2','MGLCG1','MGLCG2','NBOHG1','NBOHG2'}
    resources=[r for r in phase5['pack']['resources'] if r['resref'] in wanted]
    require(len(resources)==6,'six profile representatives missing')
    def check(resource):
        oracle=ROOT/resource['oracle']['path'];require(file_sha(oracle)==resource['oracle']['sha256'],'oracle changed')
        result=subprocess.run([str(exe),'--pack',str(packroot/'iee-assets/creature-sprites'),str(oracle)],
                              cwd=ROOT,capture_output=True,text=True,encoding='utf-8',errors='replace')
        log=out/(resource['resref']+'.log');log.write_text(result.stdout+result.stderr,encoding='utf-8')
        require(result.returncode==0,f'mixed native binding failed: {resource["resref"]}; {log}')
        data=json.loads(result.stdout.splitlines()[-1])
        require(data['profile_id']==resource['profile_id'] and data['frames']==resource['native_frames'] and
                data['decoded_pixels']==resource['decoded_pixels']*27,'native binding coverage changed')
        return dict(data,oracle_reused=True,log=log.relative_to(ROOT).as_posix(),log_sha256=file_sha(log))
    with ThreadPoolExecutor(max_workers=3) as pool:checks=list(pool.map(check,resources))
    baseline=read(HERE/'baseline.json');game=get_path('bg2ee_game_root',required=True)
    require(all(file_sha(game/f['relative_path'])==f['sha256'] for f in baseline['live_files']),'live baseline changed during integration')
    report=dict(schema='bg2-q3m-monster-integration-verification-v1',status='ready-for-installation',phase=6,
                completed_at_utc=datetime.now(timezone.utc).isoformat(),catalog_sha256=pointer['catalog_sha256'],
                catalog_manifest_sha256=pointer['manifest_sha256'],animation_count=81,resources=4549,native_frames=1584979,
                character=pack['proof'],monster=dict(profiles=[2,3,4,5,6,7],rule=2,owner=3,resources=39,
                                                   new_routes_exact=True,pixel_proof_reused=phase5['pack_manifest_sha256']),
                native_mixed_catalog_bindings=checks,host_executable_sha256=file_sha(exe),
                runtime=dict(manifest=pack['runtime_manifest'],sha256=pack['runtime_manifest_sha256'],
                             dll=baseline['runtime_dll'],rebuilt=False),
                baseline_unchanged=True,installation_changed=False,QA_changed=False,release_changed=False,
                source_sha256={p.relative_to(ROOT).as_posix():file_sha(p) for p in HERE.glob('*.py')})
    write_json(HERE/'verification.json',report)
    pointer['status']='integrated-native-binding-verified-ready-for-installation'
    write_json(HERE/'current-generation.json',pointer)
    print(dict(status=report['status'],profiles=6,animations=81,preserved_character_routes=50190))


if __name__=='__main__':main()
