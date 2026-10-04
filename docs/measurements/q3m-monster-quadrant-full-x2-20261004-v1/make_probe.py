"""Compile four-part assembly oracle against exact new reader objects."""
import subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
t=(HERE.parent/'q3m-monster-layered-full-x2-20261004-v1/composite_probe.cpp').read_text()
start=t.index('  const auto& renders=');end=t.index('  require(argc==3',start)
t=t[:start]+'''  require(manifest->get().areaAnimations.monsterQuadrantRender==0x3305a0,"native Quadrant hook differs");
'''+t[end:]
t=t.replace('metadata[0]),8)','metadata[0]),4)')
t=t.replace('require(count>0&&count<=8,"layer count")','require(count==4,"native four quadrants")')
needle='    std::array<int,4> expectedBounds{};';assert t.count(needle)==1
t=t.replace(needle,'''    const auto nativeCount=layers.size();
    layers.erase(std::remove_if(layers.begin(),layers.end(),[](const auto& layer){return cs::frame_is_native_empty_quadrant(layer.frame);}),layers.end());
    require(!layers.empty(),"fully empty native case");
    std::array<int,4> expectedBounds{};''')
t='#include <algorithm>\n'+t;t=t.replace('layersTotal+=count','layersTotal+=nativeCount')
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
print('Four-quadrant native reader/assembly oracle compiled.')
