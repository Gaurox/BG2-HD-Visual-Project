"""Reuse exhaustive leaf proof; verify merged routing and a native sample per ID."""
import json,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
PROD=HERE.parent/'q3m-monster-full-x2-20261006-v2';WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(HERE/'verification.json').exists()
gen=load(HERE/'current-generation.json');original=load(PROD/'current-generation.json')
assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
pack=load(ROOT/gen['generation_dir']/'pack.json')
for s in pack['monster_shards']:assert file_sha(assets/Path(s['registry']).name).upper()==s['sha256']
raw=(ROOT/original['generation_dir']/'witnesses.oracle').read_bytes()
magic,count=struct.unpack_from('<8sI',raw);assert magic==b'IEEQP7\0\0' and count==1040
offset=12;blocks=[];first={};extras=[];source_bindings=set();totalframes=0
for _ in range(count):
    start=offset;aid,owner,name,nf,nc=struct.unpack_from('<II8sII',raw,offset)
    ref=name.rstrip(b'\0').decode();assert owner==3
    offset+=24+6*256*4+2052
    for _ in range(nc):
        slots=struct.unpack_from('<I',raw,offset)[0];offset+=4+4*slots
    offset+=nf*(16+6*32);totalframes+=nf
    block=dict(start=start,end=offset,aid=f'0x{aid:04X}',resref=ref,frames=nf)
    blocks.append(block);first.setdefault(aid,block);source_bindings.add((block['aid'],ref))
    if ref=='MKUOG2SL':extras.append(block)
inv=next(b for b in blocks if b['resref'].endswith('INV'));extras.append(inv)
assert offset==len(raw) and totalframes==496822 and len(first)==77
ids=set(gen['animation_ids'])
assert source_bindings=={(r['animation_id'],r['resref']) for r in cat['directory'] if r['animation_id'] in ids}
selected={b['start']:b for b in [*first.values(),*extras]};samples=sorted(selected.values(),key=lambda b:b['start'])
exe=ROOT/'sprite/.work/q3m-icewind-full-x2-20261006-v1/runtime-build/Release/iee_palette_partner_tests.exe'
directory=WORK/'native-routing';directory.mkdir()
totals=dict(passed=True,resources=0,frames=0,native_cycle_slots=0,decoded_pixels=0,K=6,palette_encodings=3,batches=[])
for start in range(0,len(samples),32):
    batch=samples[start:start+32];n=start//32+1;oracle=directory/f'batch-{n:02}.oracle';log=directory/f'batch-{n:02}.log'
    oracle.write_bytes(struct.pack('<8sI',magic,len(batch))+b''.join(raw[b['start']:b['end']] for b in batch))
    with log.open('w',encoding='utf-8') as stream:
        subprocess.run([str(exe),str(assets),str(oracle)],stdout=stream,stderr=subprocess.STDOUT,check=True)
    report=json.loads(next(line for line in reversed(log.read_text(encoding='utf-8').splitlines()) if line.startswith('{')))
    assert report['passed'] and report['resources']==len(batch) and report['frames']==sum(b['frames'] for b in batch)
    for k in ('resources','frames','native_cycle_slots','decoded_pixels'):totals[k]+=report[k]
    totals['batches'].append(dict(oracle=oracle.relative_to(ROOT).as_posix(),sha256=file_sha(oracle),result=report))
    print(json.dumps(dict(stage='native-merged-routing',done=start+len(batch),total=len(samples),frames=totals['frames'])),flush=True)
fixtures=load(HERE/'creatures.json')['fixtures']
assert len(fixtures)==77
for f in fixtures:
    p=ROOT/f['path'];assert file_sha(p)==f['sha256'];b=p.read_bytes()
    assert b[:8]==b'CRE V1.0' and struct.unpack_from('<I',b,0x28)[0]==int(f['animation_id'],16)
    assert struct.unpack_from('<I',b,0x20)[0]==0 and b[0x7e]==0 and b[0x270]==128
    assert struct.unpack_from('<I',b,0x2c8)[0]==struct.unpack_from('<I',b,0x2c0)[0]==0
    assert not any(b[o:o+8].strip(b'\0 ') for o in (0x248,0x250,0x258,0x260,0x268,0x2cc))
write_json(HERE/'verification.json',dict(passed=True,catalog_sha256=gen['catalog']['sha256'],monster_leaf_hashes_verified=1037,
    source_bindings_verified=1040,production_exhaustive_native=gen['production_verification'],exhaustive_proven_bound_frames=496822,
    native_routing=totals,native_routing_animation_ids=sorted(ids),native_test=dict(path=exe.relative_to(ROOT).as_posix(),sha256=file_sha(exe)),
    neutral_fixtures_verified=77,catalog_structure=pack['proof'],runtime_changed=False,ingame_QA=False,release=False))
print(json.dumps(dict(stage='verified',ids=77,leaves=1037,fixtures=77,native_samples=len(samples),passed=True)),flush=True)
