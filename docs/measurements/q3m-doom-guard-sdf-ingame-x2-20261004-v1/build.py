"""Installed stable runtime + V9 native range palette support; unchanged hooks/shaders."""
import difflib,io,json,subprocess,zipfile,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
assert not SRC.exists()
raw=subprocess.check_output(['git','archive','--format=zip','16b01e52','engine/InfinityEngine-Enhancer/source-patchee'],cwd=ROOT)
prefix='engine/InfinityEngine-Enhancer/source-patchee/'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for e in z.infolist():
        if e.is_dir():continue
        assert e.filename.startswith(prefix)
        p=SRC/e.filename[len(prefix):];assert p.resolve().is_relative_to(SRC.resolve())
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(e))
p=SRC/'src/iee/creature_sprite_x2.cpp';before=p.read_bytes()
assert hashlib.sha256(before).hexdigest()=='6f5cae441cd78928085053b3a477401a084699c901d174cc938f9fec274a42ae'
old=b'frame.partnerProfile->nativeKind != 0 ||';new=b'frame.partnerProfile->nativeKind > 1 ||'
assert before.count(old)==1;after=before.replace(old,new);p.write_bytes(after)
(HERE/'runtime-delta.patch').write_text(''.join(difflib.unified_diff(before.decode().splitlines(True),after.decode().splitlines(True),fromfile='installed-stable/creature_sprite_x2.cpp',tofile='native-range-SDF/creature_sprite_x2.cpp')),encoding='utf-8')
p=SRC/'tools/generate_water_route2_registry.py';t=p.read_text(encoding='utf-8');p.write_text(t.replace('WORKSPACE_ROOT = SOURCE_ROOT.parents[2]',f'WORKSPACE_ROOT = Path({ROOT.as_posix()!r})'),encoding='utf-8')
p=SRC/'CMakeLists.txt';t=p.read_text(encoding='utf-8');p.write_text(t.replace('${CMAKE_SOURCE_DIR}/../../../pipeline/water/route2-registry-v1.json',(ROOT/'pipeline/water/route2-registry-v1.json').as_posix()),encoding='utf-8')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps';cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[[cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ['minhook','spdlog','zlib']]],
[cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6']]
with (HERE/'build.log').open('w',encoding='utf-8') as log:
    for cmd in commands:
        print('Build:',cmd[1],flush=True);subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
assert (BUILD/'generated/iee/water_route2_registry.generated.h').read_bytes()==(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-q3m-sdf-stable-20261004-v1/generated/iee/water_route2_registry.generated.h').read_bytes()
print('Stable DLL + native-kind-1 V9 support built; general tests passed.',flush=True)
