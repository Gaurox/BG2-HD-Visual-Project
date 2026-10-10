"""Native CVidCell oracle, all installed owners/cycles, unchanged decoder pixels."""
import json,runpy,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
WORK=ROOT/'sprite/.work'/HERE.name;BUILD=WORK/'runtime-build';SRC=WORK/'runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def result(path):return json.loads(next(s for s in reversed(path.read_text(encoding='utf-8').splitlines()) if s.startswith('{')))
assert not(HERE/'runtime-verification.json').exists()
ns=runpy.run_path(str(HERE.parent/'q3m-monster-stability-x2-20261007-v1/verify_runtime.py'))
ns['compile_probe'].__globals__.update(HERE=HERE,WORK=WORK,BUILD=BUILD,SRC=SRC)
exe=ns['compile_probe']('all-playback',HERE/'playback_probe.cpp')
native=runpy.run_path(str(HERE.parent/'q3m-multi-new-frame-stability-20261005-v2/native_oracle.py'))['verify_native']()
game=get_path('bg2ee_game_root',required=True);assets=game/'iee-assets/creature-sprites'
analysis=load(HERE/'analysis.json');runtime=load(HERE/'runtime.json')
assert file_sha(WORK/'all-native-cycles.oracle')==analysis['oracle_sha256']
log=HERE/'all-playback.log'
if not log.exists():
    with log.open('w',encoding='utf-8') as out:subprocess.run([str(exe),str(assets),str(WORK/'all-native-cycles.oracle')],stdout=out,stderr=subprocess.STDOUT,check=True)
playback=result(log);assert playback['passed'] and playback['routes']==analysis['routes'] and playback['resources']==analysis['oracle_rows']
print(json.dumps(dict(stage='all-playback',**playback)),flush=True)
# The only decoder cpp changes concern resolve_frame; reuse acquired pixel oracle with the new binary.
pixels=[];pixel_exe=BUILD/'Release/iee_palette_partner_tests.exe'
prod=load(HERE.parent/'q3m-monster-g2-palettes-x2-20261007-v1/production.json')
oracles=[ROOT/prod['pack_directory']/'witnesses.oracle']
for i,oracle in enumerate(oracles,1):
    log=HERE/f'native-pixels-{i:02}.log'
    with log.open('w',encoding='utf-8') as out:subprocess.run([str(pixel_exe),str(assets),str(oracle)],stdout=out,stderr=subprocess.STDOUT,check=True)
    p=result(log);assert p['passed'];pixels.append(p);print(json.dumps(dict(stage='native-pixels',**p)),flush=True)
unchanged=0;changed={'src/iee/'+n for n in ('creature_sprite_x2.cpp','creature_sprite_x2.h','hooks.cpp')}
parent=ROOT/'sprite/.work/q3m-mfie-native-palettes-x2-20261007-v3/runtime-src'
for p in parent.rglob('*'):
    if p.is_file() and p.relative_to(parent).as_posix() not in changed:
        assert p.read_bytes()==(SRC/p.relative_to(parent)).read_bytes(),p;unchanged+=1
write_json(HERE/'runtime-verification.json',dict(passed=True,native_x64_oracle=native,all_playback=playback,
    native_pixels=pixels,unchanged_parent_source_files=unchanged,
    dll_sha256=runtime['dll']['sha256'],catalog_sha256=load(HERE/'baseline.json')['catalog_sha256'],
    sprites_recalculated=0,palette_guards_changed=False,source_geometry_changed=False,
    installation=False,ingame_QA=False,release=False))
print(json.dumps(dict(stage='runtime-verified',passed=True)),flush=True)
