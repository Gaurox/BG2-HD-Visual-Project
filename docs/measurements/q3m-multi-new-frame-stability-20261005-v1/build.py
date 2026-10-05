"""Minimal runtime delta from the installed DLL source; no asset regeneration."""
import difflib, hashlib, json, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
WORK = ROOT / 'sprite/.work' / HERE.name
SRC, BUILD = WORK / 'runtime-src', WORK / 'runtime-build'
PARENT = ROOT / 'sprite/.work/q3m-monster-quadrant-full-x2-20261004-v1/runtime-src'
changes = {
    'src/iee/creature_sprite_x2.h': [
        ('  WaitForAnkhegMetadata,\n', '  WaitForAnkhegMetadata,\n  // Owner-5 dragons/Demogorgon: cold action/direction changes stay HD.\n  WaitForMultiNewMetadata,\n')],
    'src/iee/creature_sprite_x2.cpp': [
        ('animationId == 0x3000u && animation->owner == kCatalogAnkhegOwner));',
         'animationId == 0x3000u && animation->owner == kCatalogAnkhegOwner) ||\n           (mode == FrameResolveMode::WaitForMultiNewMetadata &&\n            is_multi_new_animation(animationId) &&\n            animation->owner == kCatalogMultiNewOwner));')],
    'src/iee/hooks.cpp': [
        ('                  : creature_sprite_x2::FrameResolveMode::NonBlocking))) {',
         '                  : ((animationId >= 0x1200u && animationId <= 0x1208u) ||\n                     animationId == 0x1300u)\n                      ? creature_sprite_x2::FrameResolveMode::WaitForMultiNewMetadata\n                      : creature_sprite_x2::FrameResolveMode::NonBlocking))) {'),
        ('  const auto cellsBase = reinterpret_cast<std::uintptr_t>(cells);\n  for (std::size_t index = 0; index < expectedCount; ++index) {',
         '''  const auto cellsBase = reinterpret_cast<std::uintptr_t>(cells);
  if ((animationId >= 0x1200u && animationId <= 0x1208u) || animationId == 0x1300u) {
    // Queue the current 4/9-cell group together. Resolve below waits for each
    // authenticated resource instead of exposing a transient all-native draw.
    // Frame payloads remain lazy; invalid resources still fail closed.
    for (std::size_t index = 0; index < expectedCount; ++index) {
      if (index > (std::numeric_limits<std::uintptr_t>::max)() / runtime.vidCellStride)
        return false;
      const auto offset = index * runtime.vidCellStride;
      if (cellsBase > (std::numeric_limits<std::uintptr_t>::max)() - offset ||
          cellsBase + offset > (std::numeric_limits<std::uintptr_t>::max)() - runtime.vidCellResref)
        return false;
      std::array<char, 8> ref{};
      if (!core::safe_read(reinterpret_cast<const void*>(cellsBase + offset + runtime.vidCellResref), ref))
        return false;
      if (!creature_sprite_x2::contains_resource(animationId, ref)) return false;
    }
  }
  for (std::size_t index = 0; index < expectedCount; ++index) {''')]
}

def prepare_sources():
    if SRC.exists():
        return
    inherited = json.loads((ROOT / 'docs/measurements/q3m-monster-quadrant-full-x2-20261004-v1/runtime.json').read_text(encoding='utf-8'))
    for item in inherited['source_provenance']:
        assert hashlib.sha256((ROOT / item['path']).read_bytes()).hexdigest() == item['sha256'], item['path']
    shutil.copytree(PARENT, SRC)
    delta = []
    for name, replacements in changes.items():
        path = SRC / name
        before = path.read_text(encoding='utf-8')
        after = before
        for old, new in replacements:
            assert after.count(old) == 1, (name, old, after.count(old))
            after = after.replace(old, new)
        path.write_text(after, encoding='utf-8', newline='\n')
        delta.extend(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                    fromfile='installed/' + name, tofile='stable/' + name))
        canonical = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee' / name
        text = canonical.read_text(encoding='utf-8')
        for old, new in replacements:
            assert text.count(old) == 1, (name, old, text.count(old))
            text = text.replace(old, new)
        canonical.write_text(text, encoding='utf-8', newline='\n')
    (HERE / 'runtime-delta.patch').write_text(''.join(delta), encoding='utf-8')

if __name__ == '__main__':
    prepare_sources()
    deps = ROOT / 'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
    cmake = 'C:/Program Files/CMake/bin/cmake.exe'
    commands = [
        [cmake, '-S', str(SRC), '-B', str(BUILD), '-G', 'Visual Studio 16 2019', '-A', 'x64',
         '-DBUILD_TESTING=ON', '-DIEE_BUILD_WINDOWS_DLL=ON', f'-DPython3_EXECUTABLE={sys.executable}',
         '-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',
         *[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ('minhook','spdlog','zlib')]],
        [cmake, '--build', str(BUILD), '--config', 'Release', '--target',
         'InfinityEngine-Enhancer', 'iee_palette_partner_tests', 'iee_tests', '--parallel', '6']]
    with (HERE / 'build.log').open('w', encoding='utf-8') as log:
        for command in commands:
            subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True)
        subprocess.run([str(BUILD / 'Release/iee_tests.exe')], cwd=SRC,
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    print('Runtime built; general native tests passed.', flush=True)
