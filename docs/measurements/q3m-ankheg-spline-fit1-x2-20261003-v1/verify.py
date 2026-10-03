"""Seal native tests; authentic malformed V8 catalogs must fail closed."""
import hashlib,json,os,struct,subprocess,sys,zlib,copy
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha,write_json
def load(path):return json.loads(path.read_text(encoding='utf-8-sig'))
def identity(path):return dict(path=path.relative_to(ROOT).as_posix(),sha256=file_sha(path),bytes=path.stat().st_size)
def result(path):return next(json.loads(line) for line in reversed(path.read_text(encoding='utf-8',errors='replace').splitlines()) if line.startswith('{'))
work=ROOT/'sprite/.work/q3m-ankheg-spline-fit1-x2-20261003-v1';isolated=work/'isolated'
native=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-q3m-spline-20261003-v1/Release/iee_palette_partner_tests.exe'
assert not (HERE/'verification.json').exists(),'fresh verification required'
new=result(ROOT/'sprite/.work/q3m-spline-native-new-20261003-v1.log')
old=result(ROOT/'sprite/.work/q3m-spline-native-original-20261003-v1.log')
flying=result(ROOT/'sprite/.work/q3m-spline-native-flying-20261003-v1.log')
assert all(r['passed'] for r in (new,old,flying)) and new['frames']==old['frames']==516 and flying['frames']==279
assert 'All InfinityEngine-Enhancer native tests passed' in (ROOT/'sprite/.work/q3m-spline-core-tests-20261003-v1.log').read_text()
assert 'OK' in (ROOT/'sprite/.work/q3m-spline-python-regression-20261003-v1.log').read_text()
assert 'OK' in (ROOT/'sprite/.work/q3m-spline-python-new-20261003-v1.log').read_text()
meta=load(isolated/'pack.json');catalog=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',meta['catalog']['sha256'])
first=catalog['shards'][0];leaf=isolated/Path(first['registry']).name
parsed=leaves.inspect(leaf,include_frames=True);r=parsed['resources'][0]
for frame in r['frames']:frame['guide']=frame['I'];frame['dep']=np.frombuffer(frame['dep'],np.uint8).copy()
uncompressed=work/'raw-valid.registry';info=leaves.write(uncompressed,[r],r['profile'],version=8,compress=False)
raw=uncompressed.read_bytes();pos=32+48+2052;target=None
for frame in r['frames']:
    flags,res=raw[pos+10],raw[pos+11];si=struct.unpack_from('<I',raw,pos+12)[0];sf=struct.unpack_from('<I',raw,pos+560)[0]
    ah=pos+568;sa=struct.unpack_from('<I',raw,ah)[0];start=ah+8+si+sf
    if res and np.any(frame['I']<3):target=(ah,start,int(np.flatnonzero(frame['I']<3)[0]));break
    pos=start+sa
assert target
cases=[]
for name,reason in [('length','invalid V8 coverage header/limit'),('special','V8 coverage changes a native special class')]:
    changed=bytearray(raw);ah,start,special=target
    if name=='length':struct.pack_into('<I',changed,ah,struct.unpack_from('<I',raw,ah)[0]-1)
    else:changed[start+special]=0
    folder=work/('malformed-'+name);folder.mkdir();digest=hashlib.sha256(changed).hexdigest().upper()
    filename=registry.catalog_shard_filename(digest);(folder/filename).write_bytes(changed)
    c=copy.deepcopy(catalog);new_info=dict(info,sha256=digest,crc32=zlib.crc32(changed)&0xffffffff,registry_bytes=len(changed))
    c['shards'][0]=dict(c['shards'][0],registry='iee-assets/creature-sprites/'+filename,**new_info)
    entry=registry.catalog_shard_entry_bytes(new_info,folder);c['components'][0]['digest']=registry.catalog_component_digest(2,[entry])
    c['components'][0]['registry_bytes']=len(changed)
    for shard in c['shards'][1:]:os.link(isolated/Path(shard['registry']).name,folder/Path(shard['registry']).name)
    registry.write_registry_catalog_index(folder/'CreatureSprites-XN.catalog',2,c['animations'],c['components'],c['shards'],c['directory'],[x['digest'] for x in c['components']],dict(shard_registry_versions=[8]))
    run=subprocess.run([str(native),str(folder),str(isolated/'witnesses.oracle')],cwd=ROOT,capture_output=True,text=True)
    (folder/'native.log').write_text(run.stdout+run.stderr,encoding='utf-8')
    assert run.returncode!=0 and reason in run.stdout+run.stderr,(name,run.returncode,run.stdout[-1000:],run.stderr)
    cases.append(dict(case=name,expected_rejection=reason,passed=True))
write_json(HERE/'verification.json',dict(schema='bg2-ankheg-spline-host-verification-v1',V8_spline=new,V7_original_unchanged=old,
    V7_flying_unchanged=flying,core_native_suite_passed=True,python_existing_tests=8,python_contour_tests=6,
    native_malformed_catalogs=cases,application='coverage multiplied at frame_pixel before texture/composite upload; RGB preserved for positive alpha',
    dll=identity(native.with_name('InfinityEngine-Enhancer.dll')),source=identity(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp'),
    mask_processor=identity(ROOT/'pipeline/scripts/sprite_spline_coverage.py'),leaf_writer=identity(ROOT/'pipeline/scripts/palette_partner_registry.py'),ingame_QA=False))
print(json.dumps(dict(native_passed=True,malformed_cases=len(cases),old_V7_preserved=True)))
