"""Build from exact installed layered runtime; only native empty-quadrant delta."""
import difflib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
parent=ROOT/'sprite/.work/q3m-monster-layered-full-x2-20261004-v1/runtime-src'
assert file_sha(parent/'src/iee/creature_sprite_x2.cpp')=='410acf6a4ce3e2470aee1bdcb0b92456195e4df78252f1658e700298293569b0'
if not SRC.exists():shutil.copytree(parent,SRC)
changes={
'src/iee/creature_sprite_x2.cpp':[
('struct Frame {\n  int logicalWidth{};', 'struct Frame {\n  bool nativeEmptyQuadrant{};\n  int logicalWidth{};'),
('!reader.read(frameReserved) || !reader.read(storedBytes) || width == 0 ||\n          height == 0)', '!reader.read(frameReserved) || !reader.read(storedBytes))'),
('      const bool compressedRegistry =\n', '''      const std::string_view nativeRef(resource.resref.data(),
          std::find(resource.resref.begin(), resource.resref.end(), '\\0') - resource.resref.begin());
      const bool nativeEmpty = width == 0 && height == 0 &&
          parsed.version == kXnPartnerRegistryVersion && resource.partnerProfile &&
          resource.partnerProfile->nativeKind == 0 &&
          (nativeRef == "MWYVG22" || nativeRef == "MWYVG23" ||
           nativeRef == "MWYVG24" || nativeRef == "MTANG21E");
      if ((width == 0 || height == 0) && !nativeEmpty)
        throw std::runtime_error("invalid non-quadrant empty frame");
      frame.nativeEmptyQuadrant = nativeEmpty;
      const bool compressedRegistry =
'''),
('if (!core::palette_fraction::validate(logicalI, logicalF, frame.dependencies, frame.fractionProfile, frame.fractionRule, frame.partnerProfile.get())) {', '''if ((nativeEmpty && (fractionPresent || frameCodec != kRegistryFrameCodecRaw ||
              std::any_of(frame.dependencies.begin(), frame.dependencies.end(), [](auto b){return b != 0;}))) ||
            (!nativeEmpty && !core::palette_fraction::validate(logicalI, logicalF, frame.dependencies, frame.fractionProfile, frame.fractionRule, frame.partnerProfile.get()))) {'''),
('if (frame.lazyShardIndex == kResidentFrameShard) return &frame.indices;', 'if (frame.nativeEmptyQuadrant || frame.lazyShardIndex == kResidentFrameShard) return &frame.indices;'),
('if (!frame.fractional || frame.lazyShardIndex == kResidentFrameShard) return &frame.fractions;', 'if (frame.nativeEmptyQuadrant || !frame.fractional || frame.lazyShardIndex == kResidentFrameShard) return &frame.fractions;'),
('bool ensure_frame_payload_available(FrameHandle handle) noexcept {', '''bool frame_is_native_empty_quadrant(FrameHandle handle) noexcept {
  try {
    std::lock_guard lock(g_mutex);
    if (!g_ready.load(std::memory_order_acquire) || !validate_lazy_frame_source_locked(handle)) return false;
    const auto* resource = resource_for_handle_locked(handle);
    return resource && handle.frameIndex < resource->frames.size() &&
           resource->frames[handle.frameIndex].nativeEmptyQuadrant;
  } catch (...) { return false; }
}

bool ensure_frame_payload_available(FrameHandle handle) noexcept {''')],
'src/iee/creature_sprite_x2.h':[
('bool ensure_frame_payload_available(FrameHandle handle) noexcept;', 'bool ensure_frame_payload_available(FrameHandle handle) noexcept;\n// Authenticated V7 0x0 stock quadrant declaration: no draw, unchanged cycles.\nbool frame_is_native_empty_quadrant(FrameHandle handle) noexcept;')],
'src/iee/hooks.cpp':[
('  scope.animationId = animationId;\n  for (std::size_t index = 0; index < expectedCount; ++index) {\n    if (!append_creature_sprite_layer(scope, resolved[index])) return false;\n  }', '''  scope.animationId = animationId;
  std::size_t nativeEmptyParts = 0;
  for (std::size_t index = 0; index < expectedCount; ++index) {
    if (owner == CreatureSpriteOwner::MonsterQuadrant &&
        creature_sprite_x2::frame_is_native_empty_quadrant(resolved[index].handle)) {
      ++nativeEmptyParts; continue;
    }
    if (!append_creature_sprite_layer(scope, resolved[index])) return false;
  }'''),
('  return scope.layerCount == expectedCount;', '  return scope.layerCount + nativeEmptyParts == expectedCount;')]
}
if not (HERE/'runtime-delta.patch').exists():
    delta=[]
    for name,replacements in changes.items():
        p=SRC/name;before=p.read_text(encoding='utf-8');after=before
        for old,new in replacements:
            assert after.count(old)==1,(name,old,after.count(old));after=after.replace(old,new)
        if name.endswith('creature_sprite_x2.cpp'):
            start=after.index('bool reconstruct_frame_pixels(');end=after.index('\nbool ',start+1)
            chunk=after[start:end];old='    auto realized = palette.colors;';assert chunk.count(old)==1
            after=after[:start]+chunk.replace(old,'    if (frame.nativeEmptyQuadrant) return true;\n'+old)+after[end:]
        p.write_text(after,encoding='utf-8',newline='\n');delta.extend(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='installed/'+name,tofile='quadrant/'+name))
        # Preserve unrelated canonical V10 stock code; apply only matching local delta.
        p=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'/name;t=p.read_text(encoding='utf-8')
        for old,new in replacements:assert t.count(old)==1,(name,old);t=t.replace(old,new)
        if name.endswith('creature_sprite_x2.cpp'):
            start=t.index('bool reconstruct_frame_pixels(');end=t.index('\nbool ',start+1);chunk=t[start:end];old='    auto realized = palette.colors;';assert chunk.count(old)==1
            t=t[:start]+chunk.replace(old,'    if (frame.nativeEmptyQuadrant) return true;\n'+old)+t[end:]
        p.write_text(t,encoding='utf-8',newline='\n')
    (HERE/'runtime-delta.patch').write_text(''.join(delta),encoding='utf-8')
    p=SRC/'tests/palette_partner_tests.cpp';t=p.read_text();t=t.replace('nr<=128','nr<=256')
    needle='''        cs::CompositeLayer layer{};layer.frame=handle;'''
    assert t.count(needle)==1
    t=t.replace(needle,'''        if (w == 0 && h == 0) {
          require(cs::frame_is_native_empty_quadrant(handle) && cs::ensure_frame_payload_available(handle),"empty native quadrant contract");
          ++frames; continue;
        }
        cs::CompositeLayer layer{};layer.frame=handle;''');p.write_text(t,encoding='utf-8')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps';cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[[cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ('minhook','spdlog','zlib')]],
 [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6']]
with (HERE/'build.log').open('w',encoding='utf-8') as log:
    for cmd in commands:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
print('Exact installed runtime plus authenticated empty-quadrant support built; general tests passed.',flush=True)
