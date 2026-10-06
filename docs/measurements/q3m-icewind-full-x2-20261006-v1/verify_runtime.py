"""Native arithmetic oracle and cold owner-2 body/equipment cycle resolution."""
import json,runpy,sqlite3,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;BUILD=WORK/'runtime-build';SRC=WORK/'runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    assert not(HERE/'runtime-verification.json').exists()
    native=runpy.run_path(str(ROOT/'docs/measurements/q3m-multi-new-frame-stability-20261005-v2/native_oracle.py'))['verify_native']()
    selection=load(HERE/'selection.json');prod=load(HERE/'production.json');assets=ROOT/prod['pack_directory']
    descriptor=load(ROOT/'sprite/index/q3m-source-work-plan.json')
    db=sqlite3.connect((ROOT/descriptor['path']).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    oracle=WORK/'native-playback.oracle';total=0
    with oracle.open('wb') as out:
        out.write(struct.pack('<8sI',b'IEENAT02',1140))
        for w in selection['witnesses']:
            for ref in w['refs']:
                r=db.execute('SELECT * FROM resources WHERE resref=?',(ref,)).fetchone()
                out.write(struct.pack('<I8sII',int(w['animation_id'],16),ref.encode().ljust(8,b'\0'),r['frame_count'],r['cycle_count']))
                for c in db.execute('SELECT * FROM cycles WHERE resource_id=? ORDER BY cycle_index',(r['resource_id'],)):
                    values=struct.unpack(f"<{c['slot_count']}H",c['frame_indices_le_u16'])
                    out.write(struct.pack('<I',len(values))+struct.pack(f'<{len(values)}I',*values));total+=1
    db.close()
    deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
    cmd=f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{BUILD}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{SRC/'src'}" /I"{deps/'spdlog-src/include'}" /I"{deps/'zlib-src'}" "{HERE/'playback_probe.cpp'}" /Fo"{WORK/'playback_probe.obj'}" /Fe"{WORK/'playback_probe.exe'}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
    (WORK/'build_probe.cmd').write_text(cmd,encoding='utf-8')
    with(HERE/'probe-build.log').open('w',encoding='utf-8') as log:
        subprocess.run(['cmd','/c',str(WORK/'build_probe.cmd')],stdout=log,stderr=subprocess.STDOUT,check=True)
    with(HERE/'playback.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(WORK/'playback_probe.exe'),str(assets),str(oracle)],stdout=log,stderr=subprocess.STDOUT,check=True)
    result=json.loads(next(line for line in reversed((HERE/'playback.log').read_text(encoding='utf-8').splitlines()) if line.startswith('{')))
    assert result['passed'] and result['resources']==1140 and result['cycles']==total
    write_json(HERE/'runtime-verification.json',dict(passed=True,native_x64_oracle=native,playback=result,
        native_general_tests_passed=load(HERE/'runtime.json')['native_general_tests_passed'],
        cold_body_and_equipment_metadata_wait=True,strict_and_other_owner_guards_preserved=True,
        oracle=dict(path=oracle.relative_to(ROOT).as_posix(),sha256=file_sha(oracle)),installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='runtime-verified',**result)),flush=True)

if __name__=='__main__':main()
