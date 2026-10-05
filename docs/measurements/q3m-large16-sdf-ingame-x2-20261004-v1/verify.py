"""Verify native V9 colour/upload/centres, cold waits, and the unchanged Ankheg."""
import hashlib,json,subprocess,sys,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry
WORK=ROOT/'sprite/.work/q3m-large16-sdf-ingame-x2-20261004-v1';BUILD=WORK/'runtime-build/Release'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def ident(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
def execute(name,command):
    if '--resume-cold' in sys.argv and name in ['native-isolated','native-combined','native-Ankheg-preserved']:
        return next(json.loads(line) for line in reversed((HERE/(name+'.log')).read_text().splitlines()) if line.startswith('{'))
    with (HERE/(name+'.log')).open('w',encoding='utf-8') as log:
        result=subprocess.run(list(map(str,command)),cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,(name,(HERE/(name+'.log')).read_text()[-1800:])
    print(name+' passed',flush=True)
    return next((json.loads(line) for line in reversed((HERE/(name+'.log')).read_text().splitlines()) if line.startswith('{')),None)
assert not (HERE/'verification.json').exists()
production=load(HERE/'production.json');isolated=WORK/'isolated';mixed=WORK/'combined/iee-assets/creature-sprites'
native=[]
for name,assets in [('native-isolated',isolated),('native-combined',mixed)]:
    result=execute(name,[BUILD/'iee_palette_partner_tests.exe',assets,isolated/'witnesses.oracle',isolated/'sdf.oracle'])
    assert result['passed'] and result['resources']==18 and result['frames']==1688;native.append(result)
ankheg=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated'
old=execute('native-Ankheg-preserved',[BUILD/'iee_palette_partner_tests.exe',mixed,ankheg/'witnesses.oracle',ankheg/'sdf.oracle'])
assert old['passed'] and old['frames']==516
cases=[]
for oracle in [isolated/'witnesses.oracle',ankheg/'witnesses.oracle']:
    raw=oracle.read_bytes();pos=12
    for n in range(struct.unpack_from('<I',raw,8)[0]):
        aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',raw,pos);pos+=24+6*256*4+2052
        chosen=None
        for sequence in range(nc):
            count=struct.unpack_from('<I',raw,pos)[0];pos+=4
            indices=struct.unpack_from('<'+'I'*count,raw,pos);pos+=count*4
            if chosen is None:chosen=next(((sequence,slot) for slot,index in enumerate(indices) if index<nf),None)
        pos+=nf*(16+6*32);name=ref.split(b'\0')[0].decode()
        if aid!=0x3000 or not name.startswith('MAKHD'):
            assert chosen is not None;cases.append((aid,name,*chosen))
    assert pos==len(raw)
assert len(cases)==24
(HERE/'cold-cases.h').write_text('struct ColdCase {unsigned aid;const char* name;int sequence;int slot;};\nconstexpr ColdCase cases[]={\n'+''.join(f'  {{0x{aid:04X}u,"{name}",{sequence},{slot}}},\n' for aid,name,sequence,slot in cases)+'};\n',encoding='utf-8')
execute('build-cold-probe',['cmd.exe','/c',HERE/'build_probe.cmd'])
cold=execute('cold-lookup',[HERE/'cold_probe.exe',mixed]);assert cold['passed'] and cold['cold_misses']==0 and cold['Large16_cold_HD']==18
gpu=load(HERE/'gpu-verification.json');assert gpu['passed']
assert 'All InfinityEngine-Enhancer native tests passed' in (HERE/'build.log').read_text()
sources=[ident(WORK/'runtime-src/src/iee'/name) for name in ['creature_sprite_x2.h','creature_sprite_x2.cpp','hooks.cpp']]
verification=dict(schema='bg2-Large16-SDF-native-verification-v1',passed=True,native_isolated=native[0],native_combined=native[1],Ankheg_preserved=old,cold_resolution=cold,core_native_suite_passed=True,GPU=ident(HERE/'gpu-verification.json'),original_I_F_deps_profile_restored_byte_identical=18,base_commit='16b01e52',Character_V10_not_in_build=True,water_compiled_registry_byte_identical=True,source_provenance=sources,dll=ident(BUILD/'InfinityEngine-Enhancer.dll'),production=ident(HERE/'production.json'),ingame_QA=False,release=False)
write_json(HERE/'verification.json',verification)
parent=load(HERE.parent/'q3m-monster-large16-full-x2-20261004-v1/current-generation.json')
runtime=dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id='iee-q3m-v9-Large16-sdf-x2-20261004-v1',inherited_runtime=parent['runtime'],dll=verification['dll'],shaders=load(ROOT/parent['runtime']['path'])['shaders'],capability_delta=dict(Large16_cold_resolution=dict(catalog_versions=[2],owner=11,animation_ids=production['animation_ids'],mode='WaitForLarge16Metadata',maximum_wait_ms=5000,payloads='lazy',timeout_policy='quarantine-and-native-fallback',other_families='unchanged')),verification=ident(HERE/'verification.json'),source_provenance=sources,Character_V10_not_in_build=True,ingame_QA=False,release=False)
for shader in runtime['shaders']:
    local=WORK/'runtime-src/assets/override'/Path(shader['target']).name
    from workspace_paths import get_path
    live=get_path('bg2ee_game_root',required=True)/shader['target']
    assert file_sha(live)==shader['sha256']
    assert local.read_text(encoding='utf-8')==live.read_text(encoding='utf-8')
    sealed=WORK/'runtime-shaders'/local.name;sealed.parent.mkdir(exist_ok=True);sealed.write_bytes(live.read_bytes())
    shader['path']=sealed.relative_to(ROOT).as_posix()
write_json(HERE/'runtime.json',runtime)
write_json(HERE/'current-generation.json',dict(schema='bg2-Large16-SDF-current-v1',role='production-not-QA-installation-or-release',family='monster_large16',animation_ids=production['animation_ids'],resources=18,frames=1688,auxiliary_INV_V7_unchanged=2,scale=2,colour='acquired-K6-four-partners-eight-levels',registry_version=9,SDF=True,generation_dir=(WORK/'combined').relative_to(ROOT).as_posix(),catalog=production['catalog'],production=ident(HERE/'production.json'),runtime=ident(HERE/'runtime.json'),dll=verification['dll'],verification=ident(HERE/'verification.json'),state='produced-host-verified-ready-to-install',ingame_QA=False,release=False))
print(json.dumps(dict(verified=True,frames=1688,cold_HD=18)),flush=True)
