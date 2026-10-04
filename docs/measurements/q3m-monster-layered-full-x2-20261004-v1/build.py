"""Installed stable runtime with only additional layered render hook; V9 guards retained."""
import io,zipfile,subprocess,json,sys,hashlib,difflib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
assert not SRC.exists()
archive=subprocess.check_output(['git','archive','--format=zip','16b01e52','engine/InfinityEngine-Enhancer/source-patchee'],cwd=ROOT)
prefix='engine/InfinityEngine-Enhancer/source-patchee/'
with zipfile.ZipFile(io.BytesIO(archive)) as z:
    for e in z.infolist():
        if e.is_dir():continue
        assert e.filename.startswith(prefix)
        p=SRC/e.filename[len(prefix):];assert p.resolve().is_relative_to(SRC.resolve())
        p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(e))
p=SRC/'src/iee/creature_sprite_x2.cpp';raw=p.read_bytes()
assert hashlib.sha256(raw).hexdigest()=='6f5cae441cd78928085053b3a477401a084699c901d174cc938f9fec274a42ae'
p.write_bytes(raw.replace(b'frame.partnerProfile->nativeKind != 0 ||',b'frame.partnerProfile->nativeKind > 1 ||'))
assert file_sha(p)=='410acf6a4ce3e2470aee1bdcb0b92456195e4df78252f1658e700298293569b0'
delta=[]
for name,replacements in {
 'src/iee/game/build_manifest.h': [('std::array<AdditionalCreatureRender, 9>','std::array<AdditionalCreatureRender, 10>')],
 'src/iee/hooks.cpp': [('std::array<core::Hook<MonsterRenderFn>, 9>','std::array<core::Hook<MonsterRenderFn>, 10>'),('std::array<bool, 9>','std::array<bool, 10>'),('std::array<MonsterRenderFn, 9>','std::array<MonsterRenderFn, 10>'),('detour_additional_creature_render<8>}}','detour_additional_creature_render<8>, detour_additional_creature_render<9>}}')],
 'src/iee/game/build_manifest.cpp': [('            }},\n            0x130,','                {0x32f3b0, 0x5aa840, 8, 0, 0, true, "40 55 56 57 41 54 41 55 41 56 41 57 48 8D 6C 24 F9 48 81 EC A0 00 00 00 48 8B 05 09 56 33 00 48"},\n            }},\n            0x130,')]
}.items():
    p=SRC/name;before=p.read_text(encoding='utf-8');after=before
    for old,new in replacements:
        assert old in after,(name,old);after=after.replace(old,new)
    p.write_text(after,encoding='utf-8',newline='\n')
    delta.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='installed/'+name,tofile='layered/'+name))
(HERE/'runtime-delta.patch').write_text(''.join(delta),encoding='utf-8')
# Reuse stable generator inputs, relocated source tree only.
p=SRC/'tools/generate_water_route2_registry.py';t=p.read_text();p.write_text(t.replace('WORKSPACE_ROOT = SOURCE_ROOT.parents[2]',f'WORKSPACE_ROOT = Path({ROOT.as_posix()!r})'),encoding='utf-8')
p=SRC/'CMakeLists.txt';t=p.read_text();p.write_text(t.replace('${CMAKE_SOURCE_DIR}/../../../pipeline/water/route2-registry-v1.json',(ROOT/'pipeline/water/route2-registry-v1.json').as_posix()),encoding='utf-8')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps';cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[[cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ['minhook','spdlog','zlib']]],
 [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6']]
with (HERE/'build.log').open('w',encoding='utf-8') as log:
    for cmd in commands:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
assert (BUILD/'generated/iee/water_route2_registry.generated.h').read_bytes()==(ROOT/'sprite/.work/q3m-doom-guard-sdf-ingame-x2-20261004-v1/runtime-build/generated/iee/water_route2_registry.generated.h').read_bytes()
print('Stable runtime plus second layered hook built; general tests passed.',flush=True)
