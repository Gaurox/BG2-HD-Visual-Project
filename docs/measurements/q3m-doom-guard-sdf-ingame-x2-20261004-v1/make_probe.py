"""Reuse native complete-layer probe; additionally compare independent SDF union goldens."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];WORK=ROOT/'sprite/.work'/HERE.name
s=(HERE.parent/'q3m-character-old-runtime-fix-x2-20261004-v1/composite_probe.cpp').read_text(encoding='utf-8')
s=s.replace('for(unsigned a:{0x6400u,0x6401u,0x6403u})','for(unsigned a:{0x6405u,0x6406u})').replace('require(missing==3,"old catalog must reproduce the three missing shadow dependencies")','require(missing==2,"parent guard shadow routing regression")').replace('old_catalog_missing_shadows\\\":3','old_catalog_missing_shadows\\\":2')
old='require(sha(pixels)==expected,"complete composite pixels differ");pixelsTotal+=pixels.size();layersTotal+=count;++cases;'
new='''require(sha(pixels)==expected,"complete composite pixels differ");pixelsTotal+=pixels.size();layersTotal+=count;++cases;
    read(f,expected);require(cs::reconstruct_composite_sdf_pixels(layers.data(),layers.size(),pixels,bounds),"SDF composite unavailable");
    require(sha(pixels)==expected,"SDF composite union differs");'''
assert s.count(old)==1;s=s.replace(old,new);(HERE/'composite_probe.cpp').write_text(s,encoding='utf-8')
base=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
cmd=f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{WORK/'runtime-build'}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{WORK/'runtime-src/src'}" /I"{base/'spdlog-src/include'}" /I"{base/'zlib-src'}" "{HERE/'composite_probe.cpp'}" /Fo"{HERE/'composite_probe.obj'}" /Fe"{HERE/'composite_probe.exe'}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
(HERE/'build_probe.cmd').write_text(cmd,encoding='utf-8')
