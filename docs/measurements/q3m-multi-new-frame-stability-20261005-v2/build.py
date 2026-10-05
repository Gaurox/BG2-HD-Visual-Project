"""Exact installed runtime plus owner-5 native CVidCell playback semantics."""
import difflib,hashlib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
PARENT=ROOT/'sprite/.work/q3m-multi-new-frame-stability-20261005-v1/runtime-src'
changes={
'src/iee/creature_sprite_x2.h':[
('bool resolve_frame(std::uint16_t animationId, const std::array<char, 8>& resref,',
 '''// Native CVidCell playback is opt-in and restricted to owner-5 IDs.
enum class FramePlaybackMode : std::uint8_t { Strict, Clamp, Loop };
bool resolve_frame(std::uint16_t animationId, const std::array<char, 8>& resref,'''),
('FrameResolveMode mode = FrameResolveMode::NonBlocking) noexcept;',
 'FrameResolveMode mode = FrameResolveMode::NonBlocking,\n                   FramePlaybackMode playback = FramePlaybackMode::Strict) noexcept;')],
'src/iee/creature_sprite_x2.cpp':[
('FrameResolveMode mode) noexcept {\n  out = {};\n  if (!g_ready.load(std::memory_order_acquire) || sequence < 0 || currentFrame < 0) return false;',
 '''FrameResolveMode mode, FramePlaybackMode playback) noexcept {
  out = {};
  const bool nativePlayback = mode == FrameResolveMode::WaitForMultiNewMetadata &&
      is_multi_new_animation(animationId) &&
      (playback == FramePlaybackMode::Clamp || playback == FramePlaybackMode::Loop);
  if (!g_ready.load(std::memory_order_acquire) ||
      (!nativePlayback && (sequence < 0 || currentFrame < 0))) return false;'''),
('''    if (static_cast<std::size_t>(sequence) >= resource.cycles.size()) {
      return false;
    }
    const auto& cycle = resource.cycles[static_cast<std::size_t>(sequence)];
    if (static_cast<std::size_t>(currentFrame) >= cycle.size()) return false;''',
 '''    if (sequence < 0 || static_cast<std::size_t>(sequence) >= resource.cycles.size()) {
      if (!nativePlayback || resource.cycles.empty()) return false;
      sequence = 0;
    }
    const auto& cycle = resource.cycles[static_cast<std::size_t>(sequence)];
    if (cycle.empty()) return false;
    if (nativePlayback) {
      // CVidCell::GetCurrentFrameSize (BG2EE 2.7.3, RVA 0x4117F8..0x41185F):
      // mode!=0 wraps signed slots; mode==0 clamps to first/last frame.
      // Do not change native cell state or normalize other sprite families.
      const int count = static_cast<int>(cycle.size());
      if (currentFrame >= count)
        currentFrame = playback == FramePlaybackMode::Loop ? currentFrame % count : count - 1;
      if (currentFrame < 0)
        currentFrame = playback == FramePlaybackMode::Loop
            ? ((currentFrame % count) + count) % count : 0;
    } else if (static_cast<std::size_t>(currentFrame) >= cycle.size()) return false;''')],
'src/iee/hooks.cpp':[
('''  if (!creature_sprite_x2::resolve_frame(animationId, resref, currentSequence,
          currentFrame, resolved.handle,''',
 '''  auto playback = creature_sprite_x2::FramePlaybackMode::Strict;
  if ((animationId >= 0x1200u && animationId <= 0x1208u) || animationId == 0x1300u) {
    // Same CVidCell playback field used by the native item-icon bridge.
    const auto playbackOffset = g_ctx->manifest->itemIcons.vidCellPlaybackMode;
    std::int32_t nativeMode = 0;
    if (!playbackOffset || !core::safe_read(
        reinterpret_cast<const void*>(cellBase + playbackOffset), nativeMode)) return false;
    playback = nativeMode != 0 ? creature_sprite_x2::FramePlaybackMode::Loop
                               : creature_sprite_x2::FramePlaybackMode::Clamp;
  }
  if (!creature_sprite_x2::resolve_frame(animationId, resref, currentSequence,
          currentFrame, resolved.handle,'''),
('                      : creature_sprite_x2::FrameResolveMode::NonBlocking))) {',
 '                      : creature_sprite_x2::FrameResolveMode::NonBlocking), playback)) {')]
}
if not SRC.exists():
    parent=json.loads((ROOT/'docs/measurements/q3m-multi-new-frame-stability-20261005-v1/runtime.json').read_text())
    for entry in parent['source_provenance']:
        assert hashlib.sha256((ROOT/entry['path']).read_bytes()).hexdigest()==entry['sha256']
    # Validate every replacement before creating the successor.
    for name,replacements in changes.items():
        for root in (PARENT,ROOT/'engine/InfinityEngine-Enhancer/source-patchee'):
            t=(root/name).read_text(encoding='utf-8')
            for old,new in replacements:assert t.count(old)==1,(name,old);t=t.replace(old,new)
    shutil.copytree(PARENT,SRC);delta=[]
    for name,replacements in changes.items():
        before=(SRC/name).read_text(encoding='utf-8')
        for root in (SRC,ROOT/'engine/InfinityEngine-Enhancer/source-patchee'):
            p=root/name;t=p.read_text(encoding='utf-8')
            for old,new in replacements:t=t.replace(old,new)
            p.write_text(t,encoding='utf-8',newline='\n')
        after=(SRC/name).read_text(encoding='utf-8')
        delta.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v1/'+name,tofile='v2/'+name,n=0))
    (HERE/'runtime-delta.patch').write_text(''.join(delta),encoding='utf-8')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[
 [cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ('minhook','spdlog','zlib')]],
 [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6','--','/nodeReuse:false']]
with (HERE/'build.log').open('w',encoding='utf-8') as log:
    for cmd in commands:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Owner-5 native playback runtime built; general native tests passed.',flush=True)
