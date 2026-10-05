"""Native executable oracle + every installed owner-5 BAM cycle transition."""
import hashlib,json,struct,subprocess,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
WORK=ROOT/'sprite/.work'/HERE.name;BUILD=WORK/'runtime-build';SRC=WORK/'runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_work_plan import write_json,file_sha
import run_creature_sprite_x2 as registry
from palette_q3m_partners import PROFILE_BYTES
import palette_registry as v6
from native_oracle import verify_native
parent=ROOT/'docs/measurements/q3m-multi-new-frame-stability-20261005-v1'
gen=json.loads((parent/'current-generation.json').read_text())
game=get_path('bg2ee_game_root',required=True);assets=game/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
ids=set(gen['animation_ids']);routes=sorted((r for r in cat['directory'] if r['animation_id'] in ids),key=lambda r:(r['animation_id'],r['resref']))
assert len(routes)==5155
native=verify_native();print(json.dumps(native),flush=True)
oracle=WORK/'native-playback.oracle';observed=[];cycleTotal=0;nonempty=0
cases=[('0x1200','MDR12103',3,8),('0x1201','MDR22102',2,14),('0x1202','MDR32103',3,14),('0x1203','MDR12102',2,8),('0x1204','MDR12102',2,8),('0x1205','MDR12102',2,8),('0x1206','MDR12104',4,8),('0x1207','MDR12105',5,8),('0x1208','MDR12102',2,8),('0x1300','MDEMG11',12,18)]
with oracle.open('wb') as f:
    f.write(struct.pack('<8sI',b'IEENAT02',len(routes)))
    for route in routes:
        aid,ref=route['animation_id'],route['resref'];shard=cat['shards'][route['shard_index']]
        raw=(game/shard['registry']).read_bytes()
        assert hashlib.sha256(raw).hexdigest().upper()==shard['sha256']
        assert struct.unpack_from('<I',raw,8)[0]==7 and struct.unpack_from('<I',raw,16)[0]==1
        nf,nc=struct.unpack_from('<II',raw,72);pos=80+PROFILE_BYTES
        for _ in range(nf):
            si=struct.unpack_from('<I',raw,pos+12)[0];sf=struct.unpack_from('<I',raw,pos+560)[0]
            pos+=v6.FRAME_BYTES+si+sf
        f.write(struct.pack('<I8sII',int(aid,16),ref.encode().ljust(8,b'\0'),nf,nc))
        for seq in range(nc):
            n=struct.unpack_from('<I',raw,pos)[0];size=4+n*4
            f.write(raw[pos:pos+size]);cycleTotal+=1;nonempty+=n>0
            for ca,cr,cs,slot in cases:
                if (aid,ref,seq)==(ca,cr,cs):
                    assert slot==n and n>0
                    first,last=struct.unpack_from('<I',raw,pos+4)[0],struct.unpack_from('<I',raw,pos+4+(n-1)*4)[0]
                    assert first<nf and last<nf
                    observed.append(dict(animation_id=aid,resref=ref,sequence=seq,native_requested_slot=slot,cycle_length=n,strict_v1_rejects=True,loop_expected_frame=first,clamp_expected_frame=last))
            pos+=size
        assert pos==len(raw)
assert len(observed)==10
write_json(HERE/'observed-transitions.json',dict(session_start='2026-10-05 20:59:54.737 Europe/Paris',events=observed))
print(json.dumps(dict(oracle_resources=len(routes),oracle_cycles=cycleTotal,nonempty_cycles=nonempty,observed_regressions=10)),flush=True)
deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
cmd=f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{BUILD}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{SRC/'src'}" /I"{deps/'spdlog-src/include'}" /I"{deps/'zlib-src'}" "{HERE/'playback_probe.cpp'}" /Fo"{WORK/'playback_probe.obj'}" /Fe"{WORK/'playback_probe.exe'}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
(WORK/'build_probe.cmd').write_text(cmd,encoding='utf-8')
with (HERE/'probe-build.log').open('w',encoding='utf-8') as log:
    subprocess.run(['cmd','/c',str(WORK/'build_probe.cmd')],stdout=log,stderr=subprocess.STDOUT,check=True)
with (HERE/'playback.log').open('w',encoding='utf-8') as log:
    subprocess.run([str(WORK/'playback_probe.exe'),str(assets),str(oracle)],stdout=log,stderr=subprocess.STDOUT,check=True)
result=json.loads(next(line for line in reversed((HERE/'playback.log').read_text().splitlines()) if line.startswith('{')))
assert result['passed'] and result['cycles']==cycleTotal and result['resources']==5155
write_json(HERE/'verification.json',dict(passed=True,scale=2,assets_unchanged=True,native_x64_oracle=native,playback=result,observed_regressions_verified=10,
    input_oracle=dict(path=oracle.relative_to(ROOT).as_posix(),sha256=file_sha(oracle),bytes=oracle.stat().st_size),
    inherited_cold_load_verification='docs/measurements/'+parent.name+'/verification.json',native_general_tests_passed=True,ingame_QA=False,release=False))
print(json.dumps(result),flush=True)
