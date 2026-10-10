"""Restore smooth WED16 and translate the two OH8100 masked draws right by 6 x1."""
from pathlib import Path
import difflib, shutil, subprocess, sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
import run_animation_upscale_30fps_v2 as v2
HERE = ROOT/'animations/batches/bdforcew-shift-right-20261010-v3'
BASE = ROOT/'animations/batches/bdforcew-wed-edge-20261010-v2/.work/runtime-src'
CANON = ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
DEST = HERE/'.work/runtime-src'; BUILD = HERE/'.work/runtime-build'
BASE_SHA = '66f6a4f051597f02e84cd9902cb98851954d677b30fcf72385a5e01a250dd896'
assert v2.sha256_file(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.dll') == BASE_SHA
assert not DEST.exists()
shutil.copytree(BASE, DEST)
changed = ['src/iee/core/native_occlusion_feather.h',
           'src/iee/core/bdforcew_visual_placement.h',
           'src/iee/hooks.cpp', 'tests/native_occlusion_feather_tests.cpp']
patch = []
for name in changed:
    old = (BASE/name).read_text().splitlines(True) if (BASE/name).exists() else []
    new = (CANON/name).read_text().splitlines(True)
    patch.extend(difflib.unified_diff(old, new, fromfile='installed-v2/'+name,
                                     tofile='smooth-shift-v3/'+name))
    shutil.copy2(CANON/name, DEST/name)
for file in BASE.rglob('*'):
    if file.is_file() and file.relative_to(BASE).as_posix() not in changed:
        assert file.read_bytes() == (DEST/file.relative_to(BASE)).read_bytes()
(HERE/'renderer-delta.patch').write_text(''.join(patch), encoding='utf-8')
v2.write_json(HERE/'source.json', dict(baseline_dll_sha256=BASE_SHA,
    baseline_source=str(BASE.relative_to(ROOT)), changed=changed,
    delta_sha256=v2.sha256_file(HERE/'renderer-delta.patch'), other_sources_identical=True,
    scope='BDFORCEW WED fade4 -> fade16 x4; final draw +6 x1 only at two OH8100 occurrences',
    non_vanilla_visual_placement=True, area_coordinates_unchanged=True))
deps = CANON/'build-vs2019-30fps-multicycle/_deps'
args = ['cmake', '-S', str(DEST), '-B', str(BUILD), '-G', 'Visual Studio 16 2019',
        '-A', 'x64', '-DIEE_BUILD_WINDOWS_DLL=ON', '-DBUILD_TESTING=ON',
        '-DPython3_EXECUTABLE='+sys.executable] + [
        '-DFETCHCONTENT_SOURCE_DIR_'+n.upper()+'='+str(deps/(n+'-src'))
        for n in ['spdlog', 'zlib', 'minhook']]
print('Configuring smooth/shift renderer', flush=True)
with (HERE/'configure.log').open('w') as log:
    subprocess.run(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
print('Building renderer and scoped tests', flush=True)
with (HERE/'build.log').open('w') as log:
    subprocess.run(['cmake', '--build', str(BUILD), '--config', 'Release', '--target',
                    'InfinityEngine-Enhancer', 'iee_native_occlusion_feather_tests'],
                   cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
exe = BUILD/'Release/iee_native_occlusion_feather_tests.exe'
subprocess.run([str(exe)], check=True)
for number in [1, 2]:
    subprocess.run([str(exe), '134', '192', str(HERE/f'instance-{number}-transfer.rgba'),
                    str(HERE/f'instance-{number}-actual-coverage.rgba')], check=True)
    assert (HERE/f'instance-{number}-expected-coverage.rgba').read_bytes() == (
            HERE/f'instance-{number}-actual-coverage.rgba').read_bytes()
oldgen = BASE.parent/'runtime-build/generated'; newgen = BUILD/'generated'
assert all(p.read_bytes() == (oldgen/p.relative_to(newgen)).read_bytes()
           for p in newgen.rglob('*') if p.is_file())
candidate = HERE/'candidate'; candidate.mkdir()
shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll', candidate/'InfinityEngine-Enhancer.dll')
shutil.copy2(get_path('bg2ee_game_root')/'InfinityEngine-Enhancer.ini', candidate/'InfinityEngine-Enhancer.ini')
v2.write_json(HERE/'tests.json', dict(passed=True, feather_and_placement_native_tests=True,
    actual_coverage_matches_gpu_preview_both_occurrences=True, shader_unchanged=True,
    other_sources_unchanged=True, water_generated_header_unchanged=True,
    dll_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.dll'),
    ini_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.ini')))
print('Smooth WED16 / right-shift6 candidate ready', flush=True)
