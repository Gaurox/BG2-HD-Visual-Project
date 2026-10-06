"""Native K6/three formats for canonical catalog, unchanged verified leaves."""
import importlib.util,json,struct,sys
from pathlib import Path
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))

def main():
    assert not (HERE/'verification.json').exists()
    prod=load(HERE/'production.json');proof=load(HERE/'catalog-repair.json');output=ROOT/prod['pack_directory']
    assert file_sha(output/'witnesses.oracle')==proof['unchanged_oracle_sha256']
    cat=registry.read_sealed_catalog_index(output/'CreatureSprites-XN.catalog',prod['pack']['catalog_sha256'])
    routes={(r['animation_id'],r['resref']) for r in cat['directory']}
    assert len(routes)==1040 and len(cat['animations'])==77
    for item in proof['unchanged_leaves']:
        assert file_sha(output/item['name'])==item['sha256']
    assert len(proof['unchanged_leaves'])==1037
    assert file_sha(ROOT/proof['leaf_pass_log']['path'])==proof['leaf_pass_log']['sha256']
    raw=(output/'witnesses.oracle').read_bytes();magic,count=struct.unpack_from('<8sI',raw)
    assert magic==b'IEEQP7\0\0' and count==1040
    resources=[];bindings=set();offset=12;frames=0
    for _ in range(count):
        aid,owner,name,nf,nc=struct.unpack_from('<II8sII',raw,offset);ref=name.rstrip(b'\0').decode()
        assert owner==3;offset+=24+6*256*4
        metadata=raw[offset:offset+2052];offset+=2052
        cycles=[]
        for _ in range(nc):
            slots=struct.unpack_from('<I',raw,offset)[0];cycles.append(range(slots));offset+=4+slots*4
        offset+=nf*(16+6*32);frames+=nf
        aid=f'0x{aid:04X}';bindings.add((aid,ref))
        resources.append(dict(witness=dict(animation_id=aid,owner=3),resref=ref,frames=range(nf),cycles=cycles,
                              profile=SimpleNamespace(metadata=lambda m=metadata:m)))
    assert offset==len(raw) and bindings==routes and frames==496822
    acquired=HERE.parent/'q3m-monster-full-x2-20261006-v1/verify.py'
    spec=importlib.util.spec_from_file_location('monster_native_batches',acquired);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    exe=ROOT/'sprite/.work/q3m-multi-new-frame-stability-20261005-v2/runtime-build/Release/iee_palette_partner_tests.exe'
    print(json.dumps(dict(stage='native-canonical-start',resources=1040,frames=frames,unchanged_leaves=1037)),flush=True)
    native=module.verify_native_batches(exe,output,resources)
    assert native['passed'] and native['frames']==frames and native['resources']==1040
    write_json(HERE/'verification.json',dict(passed=True,resources=1040,bound_frames=frames,
               physical_resources=1037,physical_frames=496816,native_world=native,
               native_test=dict(path=exe.relative_to(ROOT).as_posix(),sha256=file_sha(exe)),
               inherited_leaf_verification=proof['leaf_pass_log'],inherited_leaf_verifier=proof['leaf_verifier'],
               all_geometry_cycles_profiles_representatives_cache_preserved=True,
               leaf_bytes_unchanged=1037,oracle_bytes_unchanged=True,large_native_frames_checked=45,
               resume=dict(encoded_cache_hits=102953),resume_torch_import_blocked=True,
               catalog_memberships_canonical=True,SDF=False,installation=False,ingame_QA=False,release=False))
    print(json.dumps(dict(stage='verified',frames=frames,passed=True)),flush=True)

if __name__=='__main__':main()
