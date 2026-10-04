"""Compile complete-layer native oracle against the exact new runtime objects."""
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
t=(HERE.parent/'q3m-character-old-runtime-fix-x2-20261004-v1/composite_probe.cpp').read_text()
t=t.replace('#include "iee/creature_sprite_x2.h"','#include "iee/creature_sprite_x2.h"\n#include "iee/game/build_manifest.h"')
t=t.replace('metadata[0]),6)','metadata[0]),8)')
t=t.replace('require(argc==3,"usage:', '''const auto manifest=iee::game::find_manifest("BG2EE 2.7.3.x");
  require(bool(manifest),"BG2EE manifest absent");
  const auto& renders=manifest->get().areaAnimations.additionalCreatureRenders;
  require(renders.size()==10,"layered hook extent");
  unsigned layered=0;
  for(const auto& e:renders)if(e.owner==8){
    require(e.composite&&((e.render==0x32ee90&&e.vtable==0x5aa650)||(e.render==0x32f3b0&&e.vtable==0x5aa840)),"layered render/vtable mismatch");++layered;
  }
  require(layered==2,"both layered native paths required");
  require(argc==3,"usage:''')
(HERE/'composite_probe.cpp').write_text(t,encoding='utf-8')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
cmd=f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{WORK/'runtime-build'}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{WORK/'runtime-src/src'}" /I"{deps/'spdlog-src/include'}" /I"{deps/'zlib-src'}" "{HERE/'composite_probe.cpp'}" /Fo"{HERE/'composite_probe.obj'}" /Fe"{HERE/'composite_probe.exe'}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
(HERE/'build_probe.cmd').write_text(cmd,encoding='utf-8')
with (HERE/'probe-build.log').open('w') as log:subprocess.run(['cmd','/c',str(HERE/'build_probe.cmd')],stdout=log,stderr=subprocess.STDOUT,check=True)
print('Native complete-layer and both-manifest-path oracle compiled.')
