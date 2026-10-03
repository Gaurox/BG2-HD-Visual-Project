"""V9 native upload goldens, compatibility and malformed auxiliary-plane checks."""
import sys,json,struct,zlib,hashlib,subprocess,copy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)
E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee';build=E/'build-q3m-sdf-20261004-v1/Release'
work=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1'
def native(label,assets,oracle,*extra):
    result=subprocess.run([str(build/'iee_palette_partner_tests.exe'),str(assets),str(oracle),*map(str,extra)],cwd=ROOT,capture_output=True,text=True)
    (HERE/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode==0,(label,result.stderr)
    return next(json.loads(s) for s in reversed(result.stdout.splitlines()) if s.startswith('{'))
def read_pass(p):
    return next(json.loads(s) for s in reversed(p.read_text().splitlines()) if s.startswith('{'))
sdf=read_pass(HERE/'native-sdf.log');original=read_pass(HERE/'native-original.log')
assert sdf['passed'] and sdf['frames']==516 and sdf['resources']==12 and sdf['native_cycle_slots']==1485
flying_p=load(HERE.parent/'q3m-flying-full-x2-20261003-v1/production.json')
flying_dir=ROOT/flying_p['pack_directory']
flying=native('native-flying',flying_dir,flying_dir/'witnesses.oracle')
alpha_dir=ROOT/'sprite/.work/q3m-ankheg-alpha-light-x2-20261004-v1/isolated'
alpha=native('native-alpha',alpha_dir,alpha_dir/'witnesses.oracle')
assert 'All InfinityEngine-Enhancer native tests passed' in (HERE/'core-tests.log').read_text()
gpu=load(HERE/'gpu-verification.json');assert gpu['passed']
# Roundtrip older byte contracts with the extended writer, using sealed material.
roundtrips=[]
for label,directory in [('V7',ROOT/'sprite/.work/q3m-monster-ankheg-full-x2-20261003-v1/isolated'),('V8',alpha_dir),('V7-flying',flying_dir)]:
    source=next(directory.glob('CreatureSprites-XN-*.registry'));p=leaves.inspect(source,include_frames=True)
    resources=p['resources'];profile=resources[0]['profile']
    for r in resources:
        for f in r['frames']:f['guide']=f['I'];f['dep']=np.frombuffer(f['dep'],np.uint8)
    target=work/(label+'-roundtrip.registry');assert not target.exists()
    leaves.write(target,resources,profile,version=p['version'])
    assert target.read_bytes()==source.read_bytes(),label
    roundtrips.append(dict(format=label,byte_identical=True))
# Invalid SDF values/references retain correct catalog hashes: test parser itself.
pack=load(work/'isolated/pack.json');info=pack['leaves'][0]
p=leaves.inspect(work/'isolated'/registry.catalog_shard_filename(info['sha256']),include_frames=True)
r=p['resources'][0];profile=r['profile']
for f in r['frames']:f['guide']=f['I'];f['dep']=np.frombuffer(f['dep'],np.uint8)
raw_path=work/'malformed-base.registry';leaves.write(raw_path,[r],profile,compress=False,version=9)
raw=raw_path.read_bytes();header=32+48+2052;w,h,_,_,_,_,flags=struct.unpack_from('<HHhhBBB',raw,header)
si=struct.unpack_from('<I',raw,header+12)[0];sf=struct.unpack_from('<I',raw,header+560)[0]
s_start=header+568+16+si+sf;m_start=s_start+(w*2+12)*(h*2+12)
bad=[]
for label,offset,payload in [('SDF-code',s_start,b'\x80'),('SDF-material',m_start,struct.pack('<I',0xffffffff))]:
    data=bytearray(raw);data[offset:offset+len(payload)]=payload
    sha=hashlib.sha256(data).hexdigest().upper();folder=work/label;folder.mkdir()
    (folder/registry.catalog_shard_filename(sha)).write_bytes(data)
    new=dict(info,sha256=sha,crc32=zlib.crc32(data)&0xffffffff,registry_bytes=len(data))
    entry=registry.catalog_shard_entry_bytes(new,folder);digest=registry.catalog_component_digest(2,[entry])
    component=dict(index=0,digest=digest,shard_start=0,shard_count=1,resource_count=1,frame_count=new['frame_count'],index_bytes=new['index_bytes'],registry_bytes=new['registry_bytes'])
    shard=dict(new,index=0,registry='iee-assets/creature-sprites/'+registry.catalog_shard_filename(sha))
    registry.write_registry_catalog_index(folder/'CreatureSprites-XN.catalog',2,[dict(animation_id='0x3000',owner=9,component_indices=[0])],[component],[shard],
        [dict(animation_id='0x3000',resref=r['resref'],component_index=0,shard_index=0,resource_ordinal=0)],[digest],dict(shard_registry_versions=[9]))
    result=subprocess.run([str(build/'iee_palette_partner_tests.exe'),str(folder),str(work/'isolated/witnesses.oracle')],capture_output=True,text=True)
    (HERE/(label+'.log')).write_text(result.stdout+result.stderr,encoding='utf-8')
    assert result.returncode!=0 and 'invalid V9 SDF material reference' in result.stdout,(label,result.stdout,result.stderr)
    bad.append(dict(case=label,rejected_by_native_parser=True))
production=load(HERE/'production.json')
assert production['Q3m_colour_planes_byte_identical'] and production['source_geometry_cycles_byte_identical']
write_json(HERE/'verification.json',dict(schema='bg2-ankheg-sdf-native-host-verification-v1',V9_SDF=sdf,V7_original_unchanged=original,V8_alpha_compatible=alpha,
    V7_flying_unchanged=flying,core_native_suite_passed=True,GPU=identity(HERE/'gpu-verification.json'),roundtrips=roundtrips,
    native_malformed_catalogs=bad,dll=identity(build/'InfinityEngine-Enhancer.dll'),source=identity(E/'src/iee/creature_sprite_x2.cpp'),
    shader_bridge=identity(E/'src/iee/shader_uniform_bridge.cpp'),leaf_writer=identity(ROOT/'pipeline/scripts/palette_partner_registry.py'),
    SDF_encoder=identity(ROOT/'pipeline/scripts/sprite_sdf_registry.py'),reference_processor=identity(HERE.parent/'q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py'),
    ingame_QA=False,release=False))
print(json.dumps(dict(native=True,GPU=True,complete_frames=516,older_byte_contracts_preserved=True)))
