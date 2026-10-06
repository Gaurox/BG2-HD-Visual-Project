"""Verify all Monster cycles, palette guards, native pixels and Icewind regression."""
import json,runpy,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
WORK=ROOT/'sprite/.work'/HERE.name;BUILD=WORK/'runtime-build';SRC=WORK/'runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def report(log):return json.loads(next(s for s in reversed(log.read_text(encoding='utf-8').splitlines()) if s.startswith('{')))
def compile_probe(name,source):
    deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
    cmd=f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{BUILD}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{SRC/'src'}" /I"{deps/'spdlog-src/include'}" /I"{deps/'zlib-src'}" "{source}" /Fo"{WORK/(name+'.obj')}" /Fe"{WORK/(name+'.exe')}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
    command=WORK/(name+'.cmd');command.write_text(cmd,encoding='utf-8')
    with(HERE/(name+'-build.log')).open('w',encoding='utf-8') as log:subprocess.run(['cmd','/c',str(command)],stdout=log,stderr=subprocess.STDOUT,check=True)
    return WORK/(name+'.exe')
def execute(name,args):
    log=HERE/(name+'.log')
    with log.open('w',encoding='utf-8') as stream:subprocess.run(list(map(str,args)),stdout=stream,stderr=subprocess.STDOUT,check=True)
    result=report(log);assert result['passed'];print(json.dumps(dict(stage=name,**result)),flush=True);return result
def main():
    assert not(HERE/'runtime-verification.json').exists()
    gen=load(HERE.parent/'q3m-monster-stability-x2-20261007-v1/current-generation.json')
    assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
    assert file_sha(assets/'CreatureSprites-XN.catalog')==gen['catalog']['sha256']
    game=get_path('bg2ee_game_root',required=True);idx=registry.KeyIndex(game)
    bmp,_=idx.resolve(idx.resource_map(1)['MFIEG3B']);assert struct.unpack_from('<I',bmp,46)[0]==252
    short=WORK/'MFIEG3B-prefix.bin';short.write_bytes(bmp[54:54+252*4]+bytes(16))
    native=runpy.run_path(str(ROOT/'docs/measurements/q3m-multi-new-frame-stability-20261005-v2/native_oracle.py'))['verify_native']()
    probe=compile_probe('monster-playback',HERE/'playback_probe.cpp')
    monster=execute('monster-playback',[probe,assets,WORK/'native-playback.oracle',short])
    assert monster['resources']==1040 and monster['missing_or_wrong_frames']==0
    probe=compile_probe('icewind-regression',ROOT/'docs/measurements/q3m-icewind-full-x2-20261006-v1/playback_probe.cpp')
    icewind=execute('icewind-regression',[probe,assets,ROOT/'sprite/.work/q3m-icewind-full-x2-20261006-v1/native-playback.oracle'])
    pixel_results=[];exe=BUILD/'Release/iee_palette_partner_tests.exe'
    for n in range(1,4):
        oracle=ROOT/f'sprite/.work/q3m-monster-ingame-x2-20261007-v1/native-routing/batch-{n:02}.oracle'
        pixel_results.append(execute(f'native-pixels-{n:02}',[exe,assets,oracle]))
    assert sum(r['resources'] for r in pixel_results)==79 and sum(r['frames'] for r in pixel_results)==40358
    # Successor is an installed-source fork; unrelated Character work must not enter it.
    parent=ROOT/'sprite/.work/q3m-monster-stability-x2-20261007-v1/runtime-src'
    changed={r['path'].split('/runtime-src/')[1] for r in load(HERE/'runtime.json')['source_provenance']}
    same=0
    for p in parent.rglob('*'):
        if p.is_file() and p.relative_to(parent).as_posix() not in changed:
            assert p.read_bytes()==(SRC/p.relative_to(parent)).read_bytes(),p;same+=1
    write_json(HERE/'runtime-verification.json',dict(passed=True,native_x64_oracle=native,monster=monster,icewind_regression=icewind,
        native_pixel_samples=pixel_results,sampled_ids=77,sampled_resources=79,sampled_frames=40358,K=6,palette_encodings=3,
        unchanged_parent_source_files=same,catalog_sha256=gen['catalog']['sha256'],dll_sha256=load(HERE/'runtime.json')['dll']['sha256'],
        native_general_tests_passed=True,installation=False,ingame_QA=False,release=False))
if __name__=='__main__':main()
