"""Narrow BDFORCEW coverage; successor of installed v1, no animation bytes touched."""
from pathlib import Path
import difflib, shutil, subprocess, sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v2
HERE=ROOT/'animations/batches/bdforcew-wed-edge-20261010-v2'
BASE=ROOT/'animations/batches/portails-deux-correctif-20261010-v1/.work/runtime-src'
CANON=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
DEST=HERE/'.work/runtime-src'; BUILD=HERE/'.work/runtime-build'
assert v2.sha256_file(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.dll')=='c1bc43f8070b5b47115b54f786891573f9c7c3827036e54faaff5edee9d9c13e'
assert not DEST.exists()
shutil.copytree(BASE,DEST)
changed=['src/iee/core/native_occlusion_feather.h','tests/native_occlusion_feather_tests.cpp'];patch=[]
for name in changed:
    old=(BASE/name).read_text().splitlines(True);new=(CANON/name).read_text().splitlines(True)
    patch.extend(difflib.unified_diff(old,new,fromfile='installed-v1/'+name,tofile='narrow-v2/'+name));shutil.copy2(CANON/name,DEST/name)
for file in BASE.rglob('*'):
    if file.is_file() and file.relative_to(BASE).as_posix() not in changed:
        assert file.read_bytes()==(DEST/file.relative_to(BASE)).read_bytes()
(HERE/'renderer-delta.patch').write_text(''.join(patch),encoding='utf-8')
v2.write_json(HERE/'source.json',dict(baseline_dll_sha256='c1bc43f8070b5b47115b54f786891573f9c7c3827036e54faaff5edee9d9c13e',baseline_source=str(BASE.relative_to(ROOT)),changed=changed,delta_sha256=v2.sha256_file(HERE/'renderer-delta.patch'),other_sources_identical=True,scope='BDFORCEW binary/non-dithered WED coverage: fade16 -> fade4 x4; guard4 retained; no geometry change'))
deps=CANON/'build-vs2019-30fps-multicycle/_deps'
args=['cmake','-S',str(DEST),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DIEE_BUILD_WINDOWS_DLL=ON','-DBUILD_TESTING=ON','-DPython3_EXECUTABLE='+sys.executable]+['-DFETCHCONTENT_SOURCE_DIR_'+n.upper()+'='+str(deps/(n+'-src')) for n in ['spdlog','zlib','minhook']]
with (HERE/'configure.log').open('w') as log: subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
with (HERE/'build.log').open('w') as log: subprocess.run(['cmake','--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_native_occlusion_feather_tests'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([str(BUILD/'Release/iee_native_occlusion_feather_tests.exe')],check=True)
for number in [1,2]:
    subprocess.run([str(BUILD/'Release/iee_native_occlusion_feather_tests.exe'),'134','192',str(HERE/f'instance-{number}-transfer.rgba'),str(HERE/f'instance-{number}-actual-coverage.rgba')],check=True)
    assert (HERE/f'instance-{number}-expected-coverage.rgba').read_bytes()==(HERE/f'instance-{number}-actual-coverage.rgba').read_bytes()
oldgen=BASE.parent/'runtime-build/generated';newgen=BUILD/'generated'
assert all(p.read_bytes()==(oldgen/p.relative_to(newgen)).read_bytes() for p in newgen.rglob('*') if p.is_file())
candidate=HERE/'candidate';candidate.mkdir()
shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',candidate/'InfinityEngine-Enhancer.dll')
shutil.copy2(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.ini',candidate/'InfinityEngine-Enhancer.ini')
v2.write_json(HERE/'tests.json',dict(passed=True,feather_native_tests=True,actual_coverage_matches_gpu_preview_both_occurrences=True,shader_unchanged=True,other_sources_unchanged=True,water_generated_header_unchanged=True,dll_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.dll'),ini_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.ini')))
print('Narrow WED renderer candidate ready',flush=True)
