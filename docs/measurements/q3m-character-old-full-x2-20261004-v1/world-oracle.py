"""Derive a native world oracle; preserve CMNKINV's two frames and empty source cycle."""
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
import palette_partner_registry as leaves
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
production=load(HERE/'production.json');isolated=ROOT/production['pack_directory']
source=isolated/'witnesses.oracle';raw=source.read_bytes()
assert hashlib.sha256(raw).hexdigest()==production['pack']['oracle_sha256']
assert not (HERE/'world-oracle.json').exists()
catalog=registry.read_sealed_catalog_index(isolated/'CreatureSprites-XN.catalog',production['pack']['catalog_sha256'])
magic,count=struct.unpack_from('<8sI',raw);assert magic==b'IEEQP7\0\0' and count==121
records=[];aux=[];offset=12;frames=0
for _ in range(count):
    start=offset;aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',raw,offset);offset+=24
    ref=ref.rstrip(b'\0').decode('ascii')
    route=next(r for r in catalog['directory'] if r['animation_id']==f'0x{aid:04X}' and r['resref']==ref)
    shard=catalog['shards'][route['shard_index']]
    info=leaves.inspect(isolated/Path(shard['registry']).name,include_frames=True);leaf=info['resources'][0]
    assert nf==len(leaf['frames']) and nc==len(leaf['cycles'])
    offset+=6*256*4+len(leaf['profile'].metadata());cycles=[]
    for cycle in leaf['cycles']:
        slots=struct.unpack_from('<I',raw,offset)[0];offset+=4
        indices=list(struct.unpack_from(f'<{slots}I',raw,offset));offset+=slots*4
        assert indices==cycle;cycles.append(indices)
    offset+=nf*(16+6*32)
    if any(i<nf for c in cycles for i in c):records.append(raw[start:offset]);frames+=nf
    else:
        assert ref=='CMNKINV' and nf==2 and cycles==[[]]
        aux.append(dict(animation_id=f'0x{aid:04X}',resref=ref,frames=nf,cycles=cycles,
            registry=shard['registry'],sha256=shard['sha256'],reason='no valid native cycle slots; direct leaf/cache validation'))
assert offset==len(raw) and len(records)==120 and frames==5659 and len(aux)==1
target=isolated/'witnesses-world.oracle';target.write_bytes(struct.pack('<8sI',magic,len(records))+b''.join(records))
write_json(HERE/'world-oracle.json',dict(source_sha256=file_sha(source),world_oracle=target.relative_to(ROOT).as_posix(),
    world_oracle_sha256=file_sha(target),native_world_bindings=120,native_world_bound_frames=5659,auxiliary=aux,
    source_cycles_unchanged=True,ingame_QA=False,release=False))
print(json.dumps(dict(native_world_bindings=120,native_world_bound_frames=5659,auxiliary=aux)))
