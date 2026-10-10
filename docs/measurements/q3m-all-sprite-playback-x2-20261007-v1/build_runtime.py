"""Fork the acquired runtime; common CVidCell playback and authenticated cold metadata."""
import difflib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
PARENT=ROOT/'sprite/.work/q3m-mfie-native-palettes-x2-20261007-v3/runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
identity=lambda p:dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
old=load(HERE.parent/'q3m-monster-g2-palettes-x2-20261007-v1/current-generation.json')
assert file_sha(get_path('bg2ee_game_root',required=True)/'InfinityEngine-Enhancer.dll')==old['dll']['sha256']
assert not(HERE/'runtime.json').exists()

def transform(name,text):
    def replace(a,b):
        nonlocal text
        assert text.count(a)==1,(name,a)
        text=text.replace(a,b)
    if name.endswith('.h'):
        replace('  WaitForMonsterMetadata,\n};','  WaitForMonsterMetadata,\n  // Any authenticated catalog owner: wait for this exact resource only.\n  WaitForRegisteredMetadata,\n};')
        replace('// Native CVidCell playback is opt-in for MultiNew, Icewind and generic Monster.',
                '// Native CVidCell playback is explicit; Strict remains the default for offline callers.')
    elif name=='creature_sprite_x2.cpp':
        replace('      ((mode == FrameResolveMode::WaitForMultiNewMetadata && is_multi_new_animation(animationId)) ||',
                '      ((mode == FrameResolveMode::WaitForRegisteredMetadata) ||\n       (mode == FrameResolveMode::WaitForMultiNewMetadata && is_multi_new_animation(animationId)) ||')
        replace('      if (mode == FrameResolveMode::WaitForMonsterMetadata &&',
                '      if (mode == FrameResolveMode::WaitForRegisteredMetadata &&\n          !catalog_owner_matches_animation(animation->owner, animationId)) return false;\n      if (mode == FrameResolveMode::WaitForMonsterMetadata &&')
        replace('          ((mode == FrameResolveMode::WaitForCharacterMetadata &&',
                '          ((mode == FrameResolveMode::WaitForRegisteredMetadata &&\n            catalog_owner_matches_animation(animation->owner, animationId)) ||\n           (mode == FrameResolveMode::WaitForCharacterMetadata &&')
        replace('      // Do not change native cell state or normalize other sprite families.',
                '      // All owners share this CVidCell rule; do not change native cell state.')
    else:
        replace('                                   ResolvedCreatureSpriteFrame& resolved,\n                                   bool waitForCharacterMetadata = false) noexcept {',
                '                                   ResolvedCreatureSpriteFrame& resolved) noexcept {')
        start=text.index('  auto playback = creature_sprite_x2::FramePlaybackMode::Strict;',text.index('bool read_registered_creature_cell'))
        end=text.index('    if (g_ctx->cfg.enableCreatureSpritePaletteTrace',start)
        text=text[:start]+'''  // The same CVidCell::GetCurrentFrameSize playback field applies to every
  // registered body, equipment layer and spatial part, independent of owner.
  const auto playbackOffset = g_ctx->manifest->itemIcons.vidCellPlaybackMode;
  std::int32_t nativeMode = 0;
  if (!playbackOffset || !core::safe_read(
      reinterpret_cast<const void*>(cellBase + playbackOffset), nativeMode)) return false;
  const auto playback = nativeMode != 0 ? creature_sprite_x2::FramePlaybackMode::Loop
                                      : creature_sprite_x2::FramePlaybackMode::Clamp;
  if (!creature_sprite_x2::resolve_frame(animationId, resref, currentSequence,
          currentFrame, resolved.handle,
          creature_sprite_x2::FrameResolveMode::WaitForRegisteredMetadata, playback)) {
'''+text[end:]
        replace('ownerLabel, resolved,\n                                     owner == CreatureSpriteOwner::Character)', 'ownerLabel, resolved)')
        replace('kOverlayLabels[index], overlay, true)', 'kOverlayLabels[index], overlay)')
        replace('creature_sprite_owner_label(scope->owner), current,\n                                       scope->owner == CreatureSpriteOwner::Character)',
                'creature_sprite_owner_label(scope->owner), current)')
        replace('    static std::atomic<bool> unresolvedFrameLogged{false};\n    if (!unresolvedFrameLogged.exchange(true, std::memory_order_relaxed)) {',
                '    static std::array<std::atomic<bool>, 65\'536> unresolvedFrameLogged{};\n    if (!unresolvedFrameLogged[animationId].exchange(true, std::memory_order_relaxed)) {')
        replace('"animation=0x{:04X}, resref={}, sequence={}, slot={}; native rendering "',
                '"animation=0x{:04X}, resref={}, sequence={}, slot={}, playback={}; native rendering "')
        replace('          currentSequence, currentFrame);\n    }\n    return false;\n  }\n  resolved.resref',
                '          currentSequence, currentFrame, nativeMode);\n    }\n    return false;\n  }\n  resolved.resref')
    return text

names=['creature_sprite_x2.h','creature_sprite_x2.cpp','hooks.cpp']
if not SRC.exists():
    shutil.copytree(PARENT,SRC);patch=[]
    for name in names:
        parent=PARENT/'src/iee'/name;before=parent.read_text(encoding='utf-8');after=transform(name,before)
        (SRC/'src/iee'/name).write_text(after,encoding='utf-8',newline='\n')
        patch.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='acquired/'+name,tofile='common/'+name))
        # Canonical source carries independent Character stock code; apply only this delta.
        canonical=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee'/name
        canonical.write_text(transform(name,canonical.read_text(encoding='utf-8')),encoding='utf-8',newline='\n')
    (HERE/'runtime-delta.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps';cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[
    [cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ('minhook','spdlog','zlib')]],
    [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6','--','/nodeReuse:false']]
with(HERE/'runtime-build.log').open('w',encoding='utf-8') as log:
    for cmd in commands:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
write_json(HERE/'runtime.json',dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id=HERE.name,
    inherited_runtime=old['runtime'],inherited_dll=old['dll'],dll=identity(BUILD/'Release/InfinityEngine-Enhancer.dll'),
    runtime_patch=identity(HERE/'runtime-delta.patch'),source_provenance=[identity(SRC/'src/iee'/n) for n in names],
    capability_delta=dict(scope='every registered creature CVidCell; bodies/equipment/spatial parts',
        native_playback='signed Loop/Clamp from native CVidCell+0x11C; invalid sequence->0',
        metadata='exact authenticated resource; existing 5-second bound; payloads lazy',
        diagnostics='first unresolved frame per animation ID, includes native playback',
        sprites_recalculated=0,catalog_changed=False,palette_guards_changed=False),
    native_general_tests_passed=True,installation=False,ingame_QA=False,release=False))
print(json.dumps(dict(stage='runtime-built',dll_sha256=file_sha(BUILD/'Release/InfinityEngine-Enhancer.dll'))),flush=True)
