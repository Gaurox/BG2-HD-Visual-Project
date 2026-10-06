"""Installed-runtime successor; only owner-2 cold loads/native playback added."""
import difflib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
PARENT=ROOT/'sprite/.work/q3m-multi-new-frame-stability-20261005-v2/runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def apply_changes(text,replacements):
    for old,new in replacements:
        if text.count(new)==1:continue
        assert text.count(old)==1,old
        text=text.replace(old,new)
    return text
changes={
'src/iee/creature_sprite_x2.h':[
('  WaitForMultiNewMetadata,','  WaitForMultiNewMetadata,\n  WaitForIcewindMetadata,'),
('// Native CVidCell playback is opt-in and restricted to owner-5 IDs.',
 '// Native CVidCell playback is opt-in for MultiNew (owner5) and Icewind (owner2).')],
'src/iee/creature_sprite_x2.cpp':[
('''  const bool nativePlayback = mode == FrameResolveMode::WaitForMultiNewMetadata &&
      is_multi_new_animation(animationId) &&''',
'''  const bool nativePlayback =
      ((mode == FrameResolveMode::WaitForMultiNewMetadata && is_multi_new_animation(animationId)) ||
       (mode == FrameResolveMode::WaitForIcewindMetadata && (animationId & 0xF000u) == 0xE000u)) &&'''),
('''            animation->owner == kCatalogMultiNewOwner));''',
'''            animation->owner == kCatalogMultiNewOwner) ||
           (mode == FrameResolveMode::WaitForIcewindMetadata &&
            (animationId & 0xF000u) == 0xE000u &&
            animation->owner == kCatalogMonsterIcewindOwner));''')],
'src/iee/hooks.cpp':[
('''  if ((animationId >= 0x1200u && animationId <= 0x1208u) || animationId == 0x1300u) {
    // Same CVidCell playback field used by the native item-icon bridge.''',
'''  const bool icewind = (animationId & 0xF000u) == 0xE000u;
  if (icewind || (animationId >= 0x1200u && animationId <= 0x1208u) || animationId == 0x1300u) {
    // Icewind native sizing (RVA 0x3175B0) calls GetCurrentFrameSize for
    // both body (+0xCD8) and equipped weapon (+0x2F10). Same playback field.'''),
('''                      : creature_sprite_x2::FrameResolveMode::NonBlocking), playback)) {''',
'''                      : (icewind ? creature_sprite_x2::FrameResolveMode::WaitForIcewindMetadata
                                 : creature_sprite_x2::FrameResolveMode::NonBlocking)), playback)) {''')]
}

def main():
    parent=load(ROOT/'docs/measurements/q3m-multi-new-frame-stability-20261005-v2/current-generation.json')
    assert file_sha(get_path('bg2ee_game_root',required=True)/'InfinityEngine-Enhancer.dll')==parent['dll']['sha256']
    runtime=load(ROOT/parent['runtime']['path'])
    for p in runtime['source_provenance']:assert file_sha(ROOT/p['path'])==p['sha256']
    if not SRC.exists():
        for name,replacements in changes.items():
            for base in(PARENT,ROOT/'engine/InfinityEngine-Enhancer/source-patchee'):
                text=(base/name).read_text(encoding='utf-8')
                apply_changes(text,replacements)
        shutil.copytree(PARENT,SRC);delta=[]
        for name,replacements in changes.items():
            before=(SRC/name).read_text(encoding='utf-8')
            for base in(SRC,ROOT/'engine/InfinityEngine-Enhancer/source-patchee'):
                path=base/name;text=path.read_text(encoding='utf-8')
                text=apply_changes(text,replacements)
                path.write_text(text,encoding='utf-8',newline='\n')
            after=(SRC/name).read_text(encoding='utf-8')
            delta.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='installed/'+name,tofile='icewind/'+name,n=3))
        (HERE/'runtime-delta.patch').write_text(''.join(delta),encoding='utf-8')
    deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps';cmake='C:/Program Files/CMake/bin/cmake.exe'
    commands=[
      [cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in('minhook','spdlog','zlib')]],
      [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6','--','/nodeReuse:false']]
    with(HERE/'runtime-build.log').open('w',encoding='utf-8') as log:
        for cmd in commands:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
    dll=BUILD/'Release/InfinityEngine-Enhancer.dll'
    write_json(HERE/'runtime.json',dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id=HERE.name,
        inherited_runtime=parent['runtime'],inherited_dll=parent['dll'],dll=dict(path=dll.relative_to(ROOT).as_posix(),sha256=file_sha(dll),bytes=dll.stat().st_size),
        runtime_patch=dict(path=(HERE/'runtime-delta.patch').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'runtime-delta.patch')),
        source_provenance=[dict(path=(SRC/name).relative_to(ROOT).as_posix(),sha256=file_sha(SRC/name)) for name in changes],
        capability_delta=dict(owner=2,metadata_wait='body and weapon; directory V2; five-second existing deadline',native_playback='CVidCell+0x11C; signed loop/clamp; invalid sequence -> zero',
        opt_in_only='WaitForIcewindMetadata; owner2 catalog entries; E000 family',composite='complete native layer order/palettes/translucency retained',other_owners_unchanged=True),
        native_general_tests_passed=True,installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='runtime-built',dll_sha256=file_sha(dll),native_general_tests_passed=True,installation=False)),flush=True)

if __name__=='__main__':main()
