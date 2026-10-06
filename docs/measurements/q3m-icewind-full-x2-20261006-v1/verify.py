"""Verify the isolated production, native geometry/cycles and all-hit resume."""
import builtins
import json
import subprocess
import struct
import sys
from functools import lru_cache
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan, produce, exclusive, native_representatives
from palette_work_plan import file_sha, write_json
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    assert not (HERE/'verification.json').exists(), 'final verification already exists'
    prod = load(HERE/'production.json')
    output = ROOT/prod['pack_directory']
    resources,works,plan = source_plan(HERE/'selection.json','monster_icewind')
    assert plan == prod['plan']
    cache = ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1'
    original = builtins.__import__
    def no_torch(name,*args,**kwargs):
        if name.split('.')[0] == 'torch':
            raise RuntimeError('Torch imported on all-hit resume')
        return original(name,*args,**kwargs)
    with exclusive(cache):
        builtins.__import__ = no_torch
        try:
            resume,_ = produce(resources,works,cache)
        finally:
            builtins.__import__ = original
    assert resume == dict(encoded_cache_hits=len(works)),resume
    print(json.dumps(dict(stage='resume',**resume,torch_imported=False)),flush=True)
    cat = registry.read_sealed_catalog_index(output/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
    routes = {(r['animation_id'],r['resref']):r for r in cat['directory']}
    assert set(routes) == {(r['witness']['animation_id'],r['resref']) for r in resources}
    assert {a['animation_id'] for a in cat['animations']} == {w['animation_id'] for w in plan['witnesses']}
    assert all(a['owner'] == 2 for a in cat['animations'])
    encoded = ROOT/prod['encoded_directory']
    @lru_cache(maxsize=1024)
    def cached(key):
        with np.load(encoded/(key+'.npz'),allow_pickle=False) as data:
            return {name:data[name].copy() for name in data.files}
    # Geometry is checked per occurrence; identical pixel keys share the same
    # native representative table, just as they share the encoded planes.
    representatives={key:native_representatives(work['frame'].indices) for key,work in works.items()}
    checked,large = 0,[]
    for number,r in enumerate(resources,1):
        aid=r['witness']['animation_id'];route=routes[(aid,r['resref'])]
        shard=cat['shards'][route['shard_index']]
        path=output/Path(shard['registry']).name
        assert file_sha(path).upper()==shard['sha256']
        info=leaves.inspect(path,include_frames=True)
        assert info['version']==7 and info['decode_rule_id']==3
        leaf=info['resources'][0]
        assert leaf['resref']==r['resref'] and leaf['source_sha256'].lower()==r['source_sha256'].lower()
        assert leaf['cycles']==r['cycles'] and leaf['profile'].metadata()==r['profile'].metadata()
        assert len(leaf['frames'])==len(r['frames'])
        for row,frame in zip(r['frames'],leaf['frames'],strict=True):
            assert tuple(frame['geometry'])==tuple(row['geometry']) and not {'S','M','A'}&set(frame)
            arrays=cached(row['key'])
            assert np.array_equal(frame['I'],arrays['I']) and np.array_equal(frame['F'],arrays['F'])
            assert frame['dep']==arrays['dep'].tobytes()
            assert np.array_equal(frame['representatives'],representatives[row['key']])
            if row['geometry'][0]*row['geometry'][1]>=65535:
                large.append(dict(animation_id=aid,resref=r['resref'],frame_index=row['frame_index'],geometry=row['geometry']))
            checked+=1
        print(json.dumps(dict(stage='verify-leaves',done=number,total=len(resources),bound_frames=checked)),flush=True)
    assert checked==plan['physical_frames'] ==76955 and not large
    exe=ROOT/'sprite/.work/q3m-icewind-full-x2-20261006-v1/runtime-build/Release/iee_palette_partner_tests.exe'
    native=verify_native_batches(exe,output,resources)
    assert native['passed'] and native['frames']==checked
    write_json(HERE/'verification.json',dict(passed=True,resources=len(resources),bound_frames=checked,
               physical_resources=prod['pack']['resources'],physical_frames=prod['pack']['frames'],
               all_geometry_cycles_profiles_representatives_cache_preserved=True,native_world=native,
               native_test=dict(path=exe.relative_to(ROOT).as_posix(),sha256=file_sha(exe)),
               large_native_frames=large,resume=resume,resume_torch_import_blocked=True,
               SDF=False,installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='verified',passed=True,frames=checked,native_world=native)),flush=True)

def load_native(path):
    return json.loads(next(line for line in reversed(path.read_text(encoding='utf-8').splitlines()) if line.startswith('{')))

def verify_native_batches(exe,output,resources):
    # Acquired native test caps its oracle at 256 resources. Bound batches also
    # release decoder caches between processes; the complete catalog is tested.
    raw=(output/'witnesses.oracle').read_bytes()
    assert struct.unpack_from('<8sI',raw)==(b'IEEQP7\0\0',len(resources))
    offset=12;blocks=[]
    for r in resources:
        start=offset
        aid,owner,name,nf,nc=struct.unpack_from('<II8sII',raw,offset)
        assert (aid,owner,name.rstrip(b'\0').decode(),nf,nc)==(int(r['witness']['animation_id'],16),2,r['resref'],len(r['frames']),len(r['cycles']))
        offset+=24+6*256*4+len(r['profile'].metadata())
        for cycle in r['cycles']:
            count=struct.unpack_from('<I',raw,offset)[0];assert count==len(cycle)
            offset+=4+count*4
        offset+=nf*(16+6*32)
        blocks.append((start,offset))
    assert offset==len(raw),'oracle parse/trailing bytes'
    directory=output.parent/'native-verification';directory.mkdir(exist_ok=True)
    totals=dict(resources=0,frames=0,native_cycle_slots=0,decoded_pixels=0,palette_encodings=3,K=6,passed=True,batches=[])
    for start in range(0,len(blocks),32):
        batch=blocks[start:start+32];number=start//32+1
        oracle=directory/f'batch-{number:02}.oracle';log=directory/f'batch-{number:02}.log'
        assert not oracle.exists() and not log.exists(),'native proof destination already exists'
        oracle.write_bytes(struct.pack('<8sI',b'IEEQP7\0\0',len(batch))+raw[batch[0][0]:batch[-1][1]])
        with log.open('w',encoding='utf-8') as stream:
            result=subprocess.run([str(exe),str(output),str(oracle)],stdout=stream,stderr=subprocess.STDOUT)
        assert result.returncode==0,f'native decoder failed: {log}'
        report=load_native(log);assert report['passed'] and report['K']==6 and report['palette_encodings']==3
        for key in ('resources','frames','native_cycle_slots','decoded_pixels'):totals[key]+=report[key]
        totals['batches'].append(dict(oracle=oracle.relative_to(ROOT).as_posix(),sha256=file_sha(oracle),log=log.relative_to(ROOT).as_posix(),result=report))
        print(json.dumps(dict(stage='native-decoder',done=start+len(batch),total=len(resources),frames=totals['frames'])),flush=True)
    return totals

if __name__=='__main__':
    main()
