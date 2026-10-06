"""Fresh canonical catalog; acquired leaves/oracle and failed proof immutable."""
import hashlib,json,shutil,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry

def main():
    destination=HERE.parent/'q3m-monster-full-x2-20261006-v2'
    assert not destination.exists(),'fresh generation required'
    old=json.loads((HERE/'production.json').read_text());oldgen=json.loads((HERE/'current-generation.json').read_text())
    source=ROOT/old['pack_directory'];output=ROOT/'sprite/.work'/destination.name/'isolated'
    destination.mkdir();output.mkdir(parents=True)
    for name in ('selection.json','source-scope.json','plan.json','preview.py','finalize_tracking.py'):
        shutil.copyfile(HERE/name,destination/name)
    raw=bytearray((source/'CreatureSprites-XN.catalog').read_bytes())
    magic,version,scale,na,nc,nm,ns=struct.unpack_from('<8s6I',raw)
    assert (magic,version,scale)==(b'IEECSNC\0',2,2)
    animations_offset=registry.REGISTRY_CATALOG_HEADER_BYTES
    memberships_offset=animations_offset+na*registry.REGISTRY_CATALOG_ANIMATION_ENTRY_BYTES
    changed=[]
    for i in range(na):
        aid,owner,start,count=struct.unpack_from('<4I',raw,animations_offset+i*16)
        indices=struct.unpack_from(f'<{count}I',raw,memberships_offset+start*4)
        canonical=sorted(set(indices));assert len(canonical)==count
        if list(indices)!=canonical:
            changed.append(dict(animation_id=f'0x{aid:04X}',before=list(indices),after=canonical))
            struct.pack_into(f'<{count}I',raw,memberships_offset+start*4,*canonical)
    assert len(changed)==3
    copied=[]
    for path in sorted(source.glob('*.registry')):
        target=output/path.name;shutil.copyfile(path,target)
        sha=file_sha(path);assert file_sha(target)==sha
        copied.append(dict(name=path.name,sha256=sha))
    assert len(copied)==1037
    shutil.copyfile(source/'witnesses.oracle',output/'witnesses.oracle')
    assert file_sha(output/'witnesses.oracle')==old['pack']['oracle_sha256']
    (output/'CreatureSprites-XN.catalog').write_bytes(raw)
    catalog_sha=hashlib.sha256(raw).hexdigest()
    validated=registry.read_sealed_catalog_index(output/'CreatureSprites-XN.catalog',catalog_sha)
    assert all(a['component_indices']==sorted(set(a['component_indices'])) for a in validated['animations'])
    # The successful source/cache/leaf pass reached native dispatch. Preserve
    # its complete log and input hashes rather than rerunning unchanged leaves.
    state=json.loads((ROOT/'sprite/.work'/HERE.name/'finish-process.json').read_text(encoding='utf-8-sig'))
    log=Path(state['stdout']);lines=[json.loads(s) for s in log.read_text().splitlines() if s.startswith('{')]
    leaves=[r for r in lines if r.get('stage')=='verify-leaves']
    assert [r['done'] for r in leaves]==list(range(1,1041)) and leaves[-1]['bound_frames']==496822
    resume=next(r for r in lines if r.get('stage')=='resume')
    assert resume['encoded_cache_hits']==102953 and resume['torch_imported'] is False
    rejected=ROOT/'sprite/.work'/HERE.name/'native-verification/batch-01.log'
    assert 'non-canonical creature-sprite animation membership' in rejected.read_text()
    proof=dict(leaf_pass_log=dict(path=log.relative_to(ROOT).as_posix(),sha256=file_sha(log)),
               leaf_verifier=dict(path=(HERE/'verify.py').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'verify.py')),
               verified_bindings=1040,verified_bound_frames=496822,large_native_frames_checked=45,
               resume=resume,unchanged_leaves=copied,unchanged_oracle_sha256=old['pack']['oracle_sha256'],
               rejected_catalog_log=dict(path=rejected.relative_to(ROOT).as_posix(),sha256=file_sha(rejected)),
               canonical_memberships=changed,new_inference=0,new_encoding=0)
    write_json(destination/'catalog-repair.json',proof)
    recipe=dict(method='Q3m-K6-four-partners-eight-levels',scale=2,SDF=False,
                encoding_recipe=dict(path=(HERE/'recipe.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'recipe.json')),
                pack_recipe=dict(path=(HERE/'recipe-packing-v2.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'recipe-packing-v2.json')),
                catalog_kernel=dict(path='pipeline/scripts/q3m_family_witnesses.py',sha256=file_sha(ROOT/'pipeline/scripts/q3m_family_witnesses.py')),
                canonicalizer=dict(path=(HERE/'canonicalize.py').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'canonicalize.py')),
                change='strict ascending unique component memberships; all leaf/oracle bytes retained')
    write_json(destination/'recipe.json',recipe)
    old['pack_directory']=output.relative_to(ROOT).as_posix();old['pack']['catalog_sha256']=catalog_sha
    old['catalog_repair']=dict(path=(destination/'catalog-repair.json').relative_to(ROOT).as_posix(),sha256=file_sha(destination/'catalog-repair.json'))
    old['parent_production']=dict(path=(HERE/'production.json').relative_to(ROOT).as_posix(),sha256=file_sha(HERE/'production.json'))
    write_json(output/'pack.json',old['pack']);write_json(destination/'production.json',old)
    oldgen['generation_dir']=output.relative_to(ROOT).as_posix()
    oldgen['catalog']=dict(path=(output/'CreatureSprites-XN.catalog').relative_to(ROOT).as_posix(),sha256=catalog_sha)
    oldgen['production']=dict(path=(destination/'production.json').relative_to(ROOT).as_posix(),sha256=file_sha(destination/'production.json'))
    oldgen['recipe']=dict(path=(destination/'recipe.json').relative_to(ROOT).as_posix(),sha256=file_sha(destination/'recipe.json'))
    write_json(destination/'current-generation.json',oldgen)
    print(json.dumps(dict(stage='canonical-catalog',animations_changed=3,leaves_unchanged=len(copied),oracle_unchanged=True,generation=destination.relative_to(ROOT).as_posix())),flush=True)

if __name__=='__main__':main()
