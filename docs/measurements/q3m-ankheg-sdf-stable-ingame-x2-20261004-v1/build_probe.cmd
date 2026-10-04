@echo off
call "C:\Program Files (x86)\Microsoft Visual Studio\2019\BuildTools\VC\Auxiliary\Build\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "G:\AI\BG2_Upscale\engine\InfinityEngine-Enhancer\source-patchee\build-q3m-sdf-stable-20261004-v1"
set "PROBE_RUN=G:\AI\BG2_Upscale\docs\measurements\q3m-ankheg-sdf-stable-ingame-x2-20261004-v1"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I..\src /I..\build-vs2019-30fps-multicycle\_deps\spdlog-src\include /I..\build-vs2019-30fps-multicycle\_deps\zlib-src "%PROBE_RUN%\cold_lookup_probe.cpp" /Fo"%PROBE_RUN%\cold_lookup_probe.obj" /Fe"%PROBE_RUN%\cold_lookup_probe.exe" /link iee_palette_partner_tests.dir\Release\creature_sprite_x2.obj iee_palette_partner_tests.dir\Release\opengl_types.obj Release\iee_common.lib _deps\spdlog-build\Release\spdlog.lib _deps\zlib-build\Release\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
