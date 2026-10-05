"""Build the installed stable branch plus only the Large16 metadata wait delta."""
import io, json, subprocess, zipfile, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work/q3m-large16-sdf-ingame-x2-20261004-v1'
SRC=WORK/'runtime-src'; BUILD=WORK/'runtime-build'
assert not SRC.exists() or '--resume' in sys.argv
raw=subprocess.check_output(['git','archive','--format=zip','16b01e52','engine/InfinityEngine-Enhancer/source-patchee'],cwd=ROOT)
prefix='engine/InfinityEngine-Enhancer/source-patchee/'
with zipfile.ZipFile(io.BytesIO(raw)) as z:
    for entry in z.infolist():
        if entry.is_dir():continue
        assert entry.filename.startswith(prefix)
        target=SRC/entry.filename[len(prefix):]
        assert target.resolve().is_relative_to(SRC.resolve())
        target.parent.mkdir(parents=True,exist_ok=True)
        if '--resume' not in sys.argv:target.write_bytes(z.read(entry))
changes={
 'creature_sprite_x2.h':('  WaitForAnkhegMetadata,','  WaitForAnkhegMetadata,\n  WaitForLarge16Metadata,'),
 'creature_sprite_x2.cpp':('            animationId == 0x3000u && animation->owner == kCatalogAnkhegOwner));','            animationId == 0x3000u && animation->owner == kCatalogAnkhegOwner) ||\n           (mode == FrameResolveMode::WaitForLarge16Metadata &&\n            (animationId == 0xA000u || animationId == 0xA100u || animationId == 0xA200u) &&\n            animation->owner == 11u));'),
 'hooks.cpp':('                  : creature_sprite_x2::FrameResolveMode::NonBlocking))) {','                  : ((animationId == 0xA000u || animationId == 0xA100u || animationId == 0xA200u)\n                      ? creature_sprite_x2::FrameResolveMode::WaitForLarge16Metadata\n                      : creature_sprite_x2::FrameResolveMode::NonBlocking)))) {')}
for name,(old,new) in changes.items():
    p=SRC/'src/iee'/name;text=p.read_text(encoding='utf-8')
    if '--resume' in sys.argv:assert new in text,name
    else:
        assert text.count(old)==1,name
        p.write_text(text.replace(old,new),encoding='utf-8')
(HERE/'runtime-delta.patch').write_bytes(subprocess.check_output(['git','diff','--','engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.h','engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp','engine/InfinityEngine-Enhancer/source-patchee/src/iee/hooks.cpp'],cwd=ROOT))
# Archived source has a different depth: keep the same pinned water inputs.
p=SRC/'tools/generate_water_route2_registry.py';text=p.read_text(encoding='utf-8')
text=text.replace('WORKSPACE_ROOT = SOURCE_ROOT.parents[2]',f'WORKSPACE_ROOT = Path({str(ROOT.as_posix())!r})')
p.write_text(text,encoding='utf-8')
p=SRC/'CMakeLists.txt';text=p.read_text(encoding='utf-8')
text=text.replace('${CMAKE_SOURCE_DIR}/../../../pipeline/water/route2-registry-v1.json',str((ROOT/'pipeline/water/route2-registry-v1.json').as_posix()))
p.write_text(text,encoding='utf-8')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[[cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ['minhook','spdlog','zlib']]],
 [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6']]
with (HERE/'build.log').open('w',encoding='utf-8') as log:
    for command in commands:
        print('Build step:',command[1],flush=True)
        subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
assert (BUILD/'generated/iee/water_route2_registry.generated.h').read_bytes()==(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-q3m-sdf-stable-20261004-v1/generated/iee/water_route2_registry.generated.h').read_bytes()
print(json.dumps(dict(built=True,base_commit='16b01e52',Character_V10_not_in_build=True)),flush=True)
