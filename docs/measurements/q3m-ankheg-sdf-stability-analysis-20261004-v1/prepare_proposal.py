"""Generate a reviewable patch and isolated compile inputs; leave engine/game untouched."""
from pathlib import Path
import difflib
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee';overlay=HERE/'work/proposal-src/iee';overlay.mkdir(parents=True,exist_ok=True)
changes={
 'src/iee/creature_sprite_x2.h':[(
  '  WaitForCharacterMetadata,',
  '  WaitForCharacterMetadata,\n  // Authenticated owner-9 Ankheg resources must be ready on their first draw.\n  WaitForAnkhegMetadata,')],
 'src/iee/creature_sprite_x2.cpp':[(
  'constexpr std::uint32_t kCatalogMultiNewOwner = 5;',
  'constexpr std::uint32_t kCatalogMultiNewOwner = 5;\nconstexpr std::uint32_t kCatalogAnkhegOwner = 9;'),(
  '''      const bool waitForMetadata =
          mode == FrameResolveMode::WaitForCharacterMetadata &&
          g_catalog.version == kRegistryCatalogDirectoryVersion &&
          animation->owner == kCatalogCharacterOwner;''',
  '''      const bool waitForMetadata =
          g_catalog.version == kRegistryCatalogDirectoryVersion &&
          ((mode == FrameResolveMode::WaitForCharacterMetadata &&
            animation->owner == kCatalogCharacterOwner) ||
           (mode == FrameResolveMode::WaitForAnkhegMetadata &&
            animationId == 0x3000u && animation->owner == kCatalogAnkhegOwner));'''),(
  '"Character metadata load exceeded the 5-second render deadline"',
  '"Registered sprite metadata load exceeded the 5-second render deadline"')],
 'src/iee/hooks.cpp':[(
  '''              ? creature_sprite_x2::FrameResolveMode::WaitForCharacterMetadata
              : creature_sprite_x2::FrameResolveMode::NonBlocking''',
  '''              ? creature_sprite_x2::FrameResolveMode::WaitForCharacterMetadata
              : (animationId == 0x3000u
                  ? creature_sprite_x2::FrameResolveMode::WaitForAnkhegMetadata
                  : creature_sprite_x2::FrameResolveMode::NonBlocking)''')]
}
diff=[]
for name,replacements in changes.items():
    original=(E/name).read_text(encoding='utf-8');proposed=original
    for old,new in replacements:
        assert proposed.count(old)==1,(name,old)
        proposed=proposed.replace(old,new)
    path=(E/name).relative_to(ROOT).as_posix()
    diff.append(f'diff --git a/{path} b/{path}\n')
    diff.extend(difflib.unified_diff(original.splitlines(True),proposed.splitlines(True),fromfile='a/'+path,tofile='b/'+path))
    (overlay/Path(name).name).write_text(proposed,encoding='utf-8',newline='\n')
(HERE/'proposed-fix.patch').write_text(''.join(diff),encoding='utf-8',newline='\n')
probe=(HERE/'cold_lookup_probe.cpp').read_text()
probe=probe.replace('WaitForCharacterMetadata','WaitForAnkhegMetadata').replace('coldMisses==12 && warmHits==12','coldMisses==0 && warmHits==12')
(HERE/'work/proposed_lookup_probe.cpp').write_text(probe,encoding='utf-8',newline='\n')
script=(HERE/'build_probe.cmd').read_text()
script=script.replace('cl /nologo ', 'cl /nologo /utf-8 ')
script=script.replace(' /I..\\src ', ' /I"%PROBE_RUN%\\work\\proposal-src" /I..\\src /I..\\src\\iee ')
script=script.replace('"%PROBE_RUN%\\cold_lookup_probe.cpp"', '"%PROBE_RUN%\\work\\proposed_lookup_probe.cpp" "%PROBE_RUN%\\work\\proposal-src\\iee\\creature_sprite_x2.cpp"')
script=script.replace('/Fo"%PROBE_RUN%\\cold_lookup_probe.obj"','/Fo%PROBE_RUN%\\work\\')
script=script.replace('/Fe"%PROBE_RUN%\\cold_lookup_probe.exe"','/Fe"%PROBE_RUN%\\work\\proposed_lookup_probe.exe"')
script=script.replace('iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj ','')
(HERE/'build_proposed_probe.cmd').write_text(script,encoding='utf-8',newline='\r\n')
