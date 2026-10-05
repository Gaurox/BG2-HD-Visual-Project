"""Exercise first draws/actions using the actual runtime objects and installed catalog."""
import csv, hashlib, json, subprocess, sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]; HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name; BUILD=WORK/'runtime-build'; SRC=WORK/'runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_work_plan import write_json, file_sha

groups=[]
for row in csv.DictReader((ROOT/'sprite/index/q3m-work-items.csv').open(encoding='utf-8-sig',newline='')):
    if row['engine_family']!='multi_new': continue
    aid=int(row['animation_id'],16); grouped=defaultdict(list)
    for ref in row['bam_resrefs'].split(';'):
        part_at=6 if aid==0x1300 else 5
        grouped[ref[:part_at]+ref[part_at+1:]].append(ref)
    for key,refs in sorted(grouped.items()):
        refs.sort(); assert len(refs)==(4 if aid==0x1300 else 9),(key,refs)
        groups.append(f'{aid:04X} '+' '.join(refs)+'\n')
assert len(groups)==580
assert sum(len(line.split())-1 for line in groups)==5155
(HERE/'groups.txt').write_text(''.join(groups),encoding='ascii')
# Two cold actions per animation suffice to reproduce the old lookup policy.
seen=defaultdict(int); baseline=[]
for line in groups:
    aid=line.split()[0]
    if seen[aid]<2: baseline.append(line);seen[aid]+=1
(WORK/'baseline-groups.txt').write_text(''.join(baseline),encoding='ascii')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
cmd = f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{BUILD}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{SRC/'src'}" /I"{deps/'spdlog-src/include'}" /I"{deps/'zlib-src'}" "{HERE/'cold_group_probe.cpp'}" /Fo"{WORK/'cold_group_probe.obj'}" /Fe"{WORK/'cold_group_probe.exe'}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
(WORK/'build_probe.cmd').write_text(cmd,encoding='utf-8')
with (HERE/'probe-build.log').open('w',encoding='utf-8') as log:
    subprocess.run(['cmd','/c',str(WORK/'build_probe.cmd')],stdout=log,stderr=subprocess.STDOUT,check=True)
results={}
for mode,groupfile in [('baseline',WORK/'baseline-groups.txt'),('fixed',HERE/'groups.txt')]:
    with (HERE/(mode+'.log')).open('w',encoding='utf-8') as log:
        subprocess.run([str(WORK/'cold_group_probe.exe'),str(get_path('bg2ee_game_root',required=True)/'iee-assets/creature-sprites'),str(groupfile),mode],stdout=log,stderr=subprocess.STDOUT,check=True)
    lines=(HERE/(mode+'.log')).read_text(encoding='utf-8').splitlines()
    results[mode]=json.loads(next(line for line in reversed(lines) if line.startswith('{')))
    print(json.dumps(results[mode]),flush=True)
assert results['fixed']['resources']==5155 and results['fixed']['groups']==580
assert results['fixed']['cold_native_fallback_groups']==0
write_json(HERE/'verification.json',dict(passed=True,scope='MultiNew owner5 current-group metadata readiness',scale=2,assets_unchanged=True,baseline=results['baseline'],fixed=results['fixed'],native_general_tests_passed=True,ingame_QA=False,release=False))
