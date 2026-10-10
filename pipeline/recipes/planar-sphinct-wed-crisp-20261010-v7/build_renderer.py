"""Scoped AR0517 branch occlusion smoothing; preserve the installed renderer lineage."""
from pathlib import Path
import difflib,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
from workspace_paths import get_path
HERE=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7'
BASE=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1/.work/runtime-src'
CANON=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
DEST=HERE/'.work/runtime-src';BUILD=HERE/'.work/runtime-build'
BASE_SHA='ee85fdaba70fd99d0fbf114c6dcee46cf21ccc60a93f8e650a2dbb50abaf42b0'
assert v2.sha256_file(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.dll')==BASE_SHA
assert not DEST.exists()
shutil.copytree(BASE,DEST)
changed=['src/iee/core/planar_sphinct_world_masks.h','src/iee/core/area_occlusion_smoothing.h','src/iee/hooks.cpp',
         'src/iee/native_occlusion_bridge.h','src/iee/native_occlusion_bridge.cpp',
         'tests/native_occlusion_feather_tests.cpp']
patch=[]
for name in changed:
 old=(BASE/name).read_text().splitlines(True) if (BASE/name).exists() else []
 new=(CANON/name).read_text().splitlines(True)
 patch.extend(difflib.unified_diff(old,new,fromfile='installed/'+name,tofile='ar0517/'+name))
 shutil.copy2(CANON/name,DEST/name)
for file in BASE.rglob('*'):
 if file.is_file() and file.relative_to(BASE).as_posix() not in changed:
  assert file.read_bytes()==(DEST/file.relative_to(BASE)).read_bytes()
(HERE/'renderer-delta.patch').write_text(''.join(patch),encoding='utf-8')
v2.write_json(HERE/'source.json',dict(baseline_dll_sha256=BASE_SHA,
 baseline_source=BASE.relative_to(ROOT).as_posix(),changed=changed,other_sources_identical=True,
 scope='AR0516 SPHINCT positions1520,1287;1529,1447;2948,1776 / AreaRegistry / full x4 spline transfer',
 geometry_coordinates_frames_unchanged=True,wed_file_unchanged=True,
 guard_x4=0,feather_x4=0,straight_alpha_RGB_preserved=True))
deps=CANON/'build-vs2019-30fps-multicycle/_deps'
args=['cmake','-S',str(DEST),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64',
      '-DIEE_BUILD_WINDOWS_DLL=ON','-DBUILD_TESTING=ON','-DPython3_EXECUTABLE='+sys.executable]+[
      '-DFETCHCONTENT_SOURCE_DIR_'+n.upper()+'='+str(deps/(n+'-src')) for n in ['spdlog','zlib','minhook']]
print('Configuring scoped planar renderer',flush=True)
with (HERE/'configure.log').open('w') as log:
 subprocess.run(args,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Building renderer and native scope/coverage tests',flush=True)
with (HERE/'build.log').open('w') as log:
 subprocess.run(['cmake','--build',str(BUILD),'--config','Release','--target',
                 'InfinityEngine-Enhancer','iee_native_occlusion_feather_tests'],
                cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
exe=BUILD/'Release/iee_native_occlusion_feather_tests.exe'
subprocess.run([str(exe)],check=True)
# Existing accepted BDFORCEW mask/placement output stays exact.
for number in [1,2]:
 old=ROOT/'animations/batches/bdforcew-shift-right-20261010-v3'
 dest=HERE/f'bdforcew-{number}-coverage.rgba'
 subprocess.run([str(exe),'134','192',str(old/f'instance-{number}-transfer.rgba'),str(dest)],check=True)
 assert dest.read_bytes()==(old/f'instance-{number}-actual-coverage.rgba').read_bytes()
oldgen=BASE.parent/'runtime-build/generated';newgen=BUILD/'generated'
assert all(p.read_bytes()==(oldgen/p.relative_to(newgen)).read_bytes() for p in newgen.rglob('*') if p.is_file())
candidate=HERE/'candidate';candidate.mkdir()
shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',candidate/'InfinityEngine-Enhancer.dll')
shutil.copy2(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.ini',candidate/'InfinityEngine-Enhancer.ini')
v2.write_json(HERE/'native-tests.json',dict(passed=True,scoped_sphinct_native_tests=True,
 bdforcew_coverage_byte_identical=True,other_sources_identical=True,generated_headers_identical=True,
 dll_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.dll'),
 ini_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.ini')))
print('Planar renderer candidate ready',flush=True)
