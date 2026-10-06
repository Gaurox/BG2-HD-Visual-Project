"""Fork installed v1; MFIE unused-tail guard and bounded diagnostic only."""
import difflib,json,shutil,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
WORK=ROOT/'sprite/.work'/HERE.name;SRC=WORK/'runtime-src';BUILD=WORK/'runtime-build'
PARENT=ROOT/'sprite/.work/q3m-mfie-palette-stability-x2-20261007-v2/runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import write_json,file_sha
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
old=load(HERE.parent/'q3m-mfie-palette-stability-x2-20261007-v2/current-generation.json')
assert file_sha(get_path('bg2ee_game_root',required=True)/'InfinityEngine-Enhancer.dll')==old['dll']['sha256']
assert not(HERE/'runtime.json').exists()
names=['creature_sprite_x2.cpp','hooks.cpp']
if not SRC.exists():
    shutil.copytree(PARENT,SRC);patch=[]
    for name in names:
        before=(WORK/('before-'+name)).read_text(encoding='utf-8')
        after=(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee'/name).read_text(encoding='utf-8')
        diff=list(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='v1/'+name,tofile='v2/'+name,n=3))
        target=SRC/'src/iee'/name;text=target.read_text(encoding='utf-8');hunks=[];hunk=[]
        for line in diff[2:]:
            if line.startswith('@@'):
                if hunk:hunks.append(hunk)
                hunk=[]
            else:hunk.append(line)
        if hunk:hunks.append(hunk)
        for h in hunks:
            a=''.join(l[1:] for l in h if l[0] in ' -');b=''.join(l[1:] for l in h if l[0] in ' +')
            assert text.count(a)==1,(name,a);text=text.replace(a,b)
        target.write_text(text,encoding='utf-8',newline='\n');patch.extend(diff)
    (HERE/'runtime-delta.patch').write_text(''.join(patch),encoding='utf-8',newline='\n')
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps';cmake='C:/Program Files/CMake/bin/cmake.exe'
commands=[
    [cmake,'-S',str(SRC),'-B',str(BUILD),'-G','Visual Studio 16 2019','-A','x64','-DBUILD_TESTING=ON','-DIEE_BUILD_WINDOWS_DLL=ON',f'-DPython3_EXECUTABLE={sys.executable}','-DFETCHCONTENT_UPDATES_DISCONNECTED=ON',*[f'-DFETCHCONTENT_SOURCE_DIR_{n.upper()}={deps/(n+"-src")}' for n in ('minhook','spdlog','zlib')]],
    [cmake,'--build',str(BUILD),'--config','Release','--target','InfinityEngine-Enhancer','iee_palette_partner_tests','iee_tests','--parallel','6','--','/nodeReuse:false']]
with(HERE/'runtime-build.log').open('w',encoding='utf-8') as log:
    for cmd in commands:subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([str(BUILD/'Release/iee_tests.exe')],cwd=SRC,stdout=log,stderr=subprocess.STDOUT,check=True)
dll=BUILD/'Release/InfinityEngine-Enhancer.dll'
write_json(HERE/'runtime.json',dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id=HERE.name,
    inherited_runtime=old['runtime'],inherited_dll=old['dll'],dll=dict(path=dll.relative_to(ROOT).as_posix(),sha256=file_sha(dll),bytes=dll.stat().st_size),
    runtime_patch=dict(path=(HERE/'runtime-delta.patch').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'runtime-delta.patch')),
    source_provenance=[dict(path=(SRC/'src/iee'/n).relative_to(ROOT).as_posix(),sha256=file_sha(SRC/'src/iee'/n)) for n in names],
    capability_delta=dict(animation_id='0x7314',palette='G1 palette1 MFIEG31/253, G2 palette2 MFIEG3B/252; exact declared prefix, optional 256 advertised; unused zero padding guarded by frame dependencies',
        diagnostic='MFIE_PALETTE: kind/count/source colors/accepted/globalOutput, at most eight unique palettes',
        actual_live_palette_G1_observed_exact=True,other_animation_contracts_unchanged=True),native_general_tests_passed=True,installation=False,ingame_QA=False,release=False))
print(json.dumps(dict(stage='built',dll_sha256=file_sha(dll))),flush=True)
