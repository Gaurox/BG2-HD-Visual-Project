"""Seal completed native/GPU checks and new Character runtime; never install."""
import hashlib,json,struct,subprocess,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_registry as v6
import run_creature_sprite_x2 as registry
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def write(p,value):
    assert not p.exists(),p
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def result(name):return json.loads([x for x in (HERE/name).read_text().splitlines() if x.startswith('{')][-1])
production=load(HERE/'production.json');work=ROOT/production['work_dir']
native=result('native-sdf.log');original=result('native-original.log');ankheg=result('native-ankheg.log');gpu=load(HERE/'gpu-verification.json')
assert native['passed'] and native['cold_misses']==0 and native['frames']==10323 and original['passed'] and ankheg['passed'] and gpu['passed']
assert 'All InfinityEngine-Enhancer native tests passed' in (HERE/'core.log').read_text()
info=production['new_shards'][0];raw=(work/'isolated'/registry.catalog_shard_filename(info['sha256'])).read_bytes()
w,h=struct.unpack_from('<HH',raw,80);sn=(w*2+12)*(h*2+12)
si=struct.unpack_from('<I',raw,92)[0];sf=struct.unpack_from('<I',raw,640)[0]
ss,sc=struct.unpack_from('<IB',raw,648);ms,mc=struct.unpack_from('<IB',raw,656)
start=664+si+sf
with v6._Codec(compress=False) as codec:
    sdf=v6._decode_plane(sc,raw[start:start+ss],sn,codec)
    material=v6._decode_plane(mc,raw[start+ss:start+ss+ms],sn*4,codec)
bad=[]
for name in ('SDF-code','SDF-material','profile'):
    if name=='profile':
        data=bytearray(raw);struct.pack_into('<II',data,24,8,3)
    else:
        s=bytearray(sdf);m=bytearray(material)
        if name=='SDF-code':s[0]=128
        else:struct.pack_into('<I',m,0,0xffffffff)
        data=bytearray(raw[:648]);data.extend(struct.pack('<IB3xIB3x',len(s),0,len(m),0))
        data.extend(raw[664:start]);data.extend(s);data.extend(m);data.extend(raw[start+ss+ms:])
    folder=work/name;folder.mkdir();digest=hashlib.sha256(data).hexdigest().upper()
    file=folder/registry.catalog_shard_filename(digest);file.write_bytes(data)
    changed=dict(info,sha256=digest,crc32=zlib.crc32(data)&0xffffffff,registry_bytes=len(data))
    entry=registry.catalog_shard_entry_bytes(changed,folder);cd=registry.catalog_component_digest(2,[entry])
    component=dict(index=0,digest=cd,shard_start=0,shard_count=1,resource_count=1,frame_count=info['frame_count'],index_bytes=info['index_bytes'],registry_bytes=len(data))
    registry.write_registry_catalog_index(folder/'CreatureSprites-XN.catalog',2,[dict(animation_id='0x6110',owner=1,component_indices=[0])],[component],[changed],[dict(animation_id='0x6110',resref=production['details'][0]['resref'],component_index=0,shard_index=0,resource_ordinal=0)],[cd],dict(shard_registry_versions=[10]))
    output=subprocess.run([str(HERE/'native_probe.exe'),str(folder),str(work/'isolated/character-sdf.oracle'),'reject'],cwd=ROOT,capture_output=True,check=True)
    log=HERE/(name+'.log');log.write_bytes(output.stdout+output.stderr)
    assert b'"rejected":true' in output.stdout
    bad.append(dict(case=name,rejected=True,log=identity(log)))
engine=ROOT/'engine/InfinityEngine-Enhancer/source-patchee';build=engine/'build-q3m-character-sdf-20261004-v1/Release'
dll=identity(build/'InfinityEngine-Enhancer.dll')
sources=[identity(engine/'src/iee'/name) for name in ('creature_sprite_x2.cpp','creature_sprite_filter.h','creature_sprite_filter.cpp','shader_uniform_bridge.h','shader_uniform_bridge.cpp')]
shaders=[dict(identity(engine/'assets/override'/(name+'.glsl')),target='override/'+name+'.glsl') for name in ('fpDraw','fpSprite','fpSELECT')]
write(HERE/'verification.json',dict(passed=True,Character_SDF=native,Character_original=original,Ankheg_SDF=ankheg,core_passed=True,malformed=bad,GPU=identity(HERE/'gpu-verification.json'),native_logs=[identity(HERE/name) for name in ('native-sdf.log','native-original.log','native-ankheg.log','core.log')],source_provenance=sources,writer=identity(ROOT/'pipeline/scripts/character_sdf_registry.py'),dll=dll,ingame_QA=False,release=False))
baseline=load(HERE/'baseline.json')
write(HERE/'runtime.json',dict(schema='bg2-upscale-runtime-capabilities-delta-v1',runtime_id='iee-q3m-character-sdf-x2-20261004-v1',inherited_runtime=baseline['parent_runtime'],dll=dll,shaders=shaders,source_provenance=sources,capability_delta=dict(character_SDF=dict(registry_version=10,colour_base='acquired-V6',scale=2,owner=1,profile=1,decode_rule=1,colour_I_F_stored_bytes_unchanged=True,shadow_alpha=128,shader_marker='uIeeCreatureSdfCharacter',metadata_wait='existing WaitForCharacterMetadata',installed_scope='0x6110 CHFB1 only')),verification=identity(HERE/'verification.json'),ingame_QA=False,release=False))
write(HERE/'current-generation.json',dict(schema='bg2-character-SDF-trial-current-v1',scope=production['scope'],animation_ids=['0x6110'],resources=23,frames=10323,scale=2,registry_version=10,production=identity(HERE/'production.json'),catalog=production['catalog'],runtime=identity(HERE/'runtime.json'),dll=dll,verification=identity(HERE/'verification.json'),ingame_QA=False,release=False))
print(json.dumps(dict(native=True,GPU=True,malformed_rejected=3,frames=10323,dll=dll)))
