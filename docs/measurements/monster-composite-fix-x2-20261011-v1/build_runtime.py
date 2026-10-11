"""Build only the Monster delta on the source of the installed renderer."""
import difflib, hashlib, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).parent
WORK = ROOT / 'sprite/.work' / HERE.name
SRC = WORK / 'runtime-src'
BUILD = WORK / 'runtime-build'
CANONICAL = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee'
PARENT = ROOT / 'animations/batches/planar-sphinct-wed-crisp-20261010-v7/.work/runtime-src'
PARENT_DLL = PARENT.parent / 'runtime-build/Release/InfinityEngine-Enhancer.dll'
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
from workspace_paths import get_path

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def identity(path):
    return dict(path=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size)

game = get_path('bg2ee_game_root', required=True)
expected = '73730a6deb3efb5b7ff1284967cc019ff28b2402f57d5874da9ef0ba281fba24'
assert sha(PARENT_DLL) == sha(game / 'InfinityEngine-Enhancer.dll') == expected
finishing = '--finish' in sys.argv
assert not (HERE / 'runtime.json').exists(), 'choose a new run'
if finishing:
    assert SRC.exists() and (BUILD / 'Release/InfinityEngine-Enhancer.dll').is_file()
else:
    assert not SRC.exists(), 'choose a new run'
    shutil.copytree(PARENT, SRC)
paths = ['src/iee/hooks.cpp', 'src/iee/creature_sprite_x2.cpp', 'tests/iee_tests.cpp']
patch = []
for name in paths:
    before = (PARENT / name).read_text(encoding='utf-8')
    canonical = (CANONICAL / name).read_text(encoding='utf-8')
    if name.endswith('hooks.cpp'):
        # The installed source and canonical hook were identical before this delta.
        start = before.index('    if (scope.animationId == 0x7F09u) {')
        end = before.index('  // Every Monster invocation masks', start)
        new_start = canonical.index('    {\n      // Every native Monster may submit')
        new_end = canonical.index('  // Every Monster invocation masks', new_start)
        after = before[:start] + canonical[new_start:new_end] + before[end:]
        assert after == canonical, 'unrelated hook changes would enter this candidate'
    elif name.endswith('creature_sprite_x2.cpp'):
        old = 'layer.frame.animationId == 0x7F09u ? "Monster" : "Character"'
        assert before.count(old) == 1
        after = before.replace(old, 'core::sprite_family_owner(layer.frame.animationId) == 3 ? "Monster" : "Creature"')
    else:
        anchor = '  // Regression: the live MDR12100 draw'
        start = canonical.index('  // Actual MFIGG12/MFIGG1WH frame 551')
        addition = canonical[start:canonical.index(anchor, start)]
        assert before.count(anchor) == 1
        after = before.replace(anchor, addition + anchor)
    if finishing:
        assert (SRC / name).read_text(encoding='utf-8') == after, name
    else:
        (SRC / name).write_text(after, encoding='utf-8', newline='\n')
    patch.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                    fromfile='installed/' + name, tofile='candidate/' + name))
if finishing:
    assert (HERE / 'runtime-delta.patch').read_text(encoding='utf-8') == ''.join(patch)
else:
    (HERE / 'runtime-delta.patch').write_text(''.join(patch), encoding='utf-8', newline='\n')
for path in PARENT.rglob('*'):
    if path.is_file() and path.relative_to(PARENT).as_posix() not in paths:
        assert sha(path) == sha(SRC / path.relative_to(PARENT)), path

cmake = 'C:/Program Files/CMake/bin/cmake.exe'
deps = CANONICAL / 'build-vs2019-30fps-multicycle/_deps'
commands = [
    [cmake, '-S', str(SRC), '-B', str(BUILD), '-G', 'Visual Studio 16 2019', '-A', 'x64',
     '-DBUILD_TESTING=ON', '-DIEE_BUILD_WINDOWS_DLL=ON', '-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',
     f'-DPython3_EXECUTABLE={sys.executable}',
     *[f'-DFETCHCONTENT_SOURCE_DIR_{name.upper()}={deps/(name+"-src")}' for name in ('minhook','spdlog','zlib')]],
    [cmake, '--build', str(BUILD), '--config', 'Release', '--target', 'InfinityEngine-Enhancer',
     'iee_tests', '--parallel', '6', '--', '/nodeReuse:false'],
    [str(BUILD / 'Release/iee_tests.exe')],
]
if finishing:
    commands = commands[-1:]
with (HERE / ('native-tests.log' if finishing else 'runtime-build.log')).open('w', encoding='utf-8') as log:
    for command in commands:
        subprocess.run(command, cwd=SRC, stdout=log, stderr=subprocess.STDOUT, check=True)

candidate = WORK / 'candidate'
candidate.mkdir()
shutil.copy2(BUILD / 'Release/InfinityEngine-Enhancer.dll', candidate / 'InfinityEngine-Enhancer.dll')
shutil.copy2(game / 'InfinityEngine-Enhancer.ini', candidate / 'InfinityEngine-Enhancer.ini')
report = dict(schema='bg2-monster-composite-runtime-candidate-v1', runtime_id=HERE.name,
    baseline_dll=identity(PARENT_DLL), baseline_source=PARENT.relative_to(ROOT).as_posix(),
    dll=identity(candidate / 'InfinityEngine-Enhancer.dll'), ini=identity(candidate / 'InfinityEngine-Enhancer.ini'),
    runtime_patch=identity(HERE / 'runtime-delta.patch'), source_provenance=[identity(SRC / name) for name in paths],
    unrelated_source_files_identical=True, native_tests_passed=True,
    sprites_recalculated=0, catalog_changed=False, palette_guards_changed=False,
    installation=False, ingame_QA=False, release=False)
(HERE / 'runtime.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(stage='runtime-built', dll_sha256=report['dll']['sha256'])), flush=True)
