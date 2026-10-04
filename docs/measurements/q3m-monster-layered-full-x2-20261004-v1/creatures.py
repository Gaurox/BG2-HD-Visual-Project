"""Census actual live CRE consumers; stock CLUA when available, neutral fixture only if absent."""
import sys,json,struct,hashlib
from itertools import groupby
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex
from workspace_paths import get_path
from palette_work_plan import write_json
selection=json.loads((HERE/'selection.json').read_text());ids={int(w['animation_id'],16):w for w in selection['witnesses']}
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);entries=index.resource_map(0x3f1)
overrides={p.stem.upper():p for p in (game/'override').iterdir() if p.is_file() and p.suffix.lower()=='.cre'}
found=[]
def examine(ref,raw,source):
    assert raw[:8]==b'CRE V1.0' and len(raw)>=0x33,ref
    aid=struct.unpack_from('<H',raw,0x28)[0]
    if aid in ids:found.append(dict(resref=ref,animation_id=f'0x{aid:04X}',source=source,sha256=hashlib.sha256(raw).hexdigest(),clua=f'C:CreateCreature("{ref}")'))
for _,group in groupby(sorted(entries.items(),key=lambda p:p[1][2]>>20),key=lambda p:p[1][2]>>20):
    for ref,entry in group:
        if ref not in overrides:
            raw,source=index.resolve(entry);examine(ref,raw,'stock:'+source)
    index._bif_cache.clear()
for ref,p in overrides.items():examine(ref,p.read_bytes(),'config://bg2ee_game_root/override/'+p.name)
found.sort(key=lambda r:r['resref']);preferred={0x2000:'SIRINE01',0x2100:'ENDVOLO',0x2200:'OGREMA01',0x2300:'DEATHKNI',0x8000:'GNOLL01',0x8100:'HOBGOB01',0x8200:'KOBALD01'}
representatives=[];fixtures=[];seed_ref='ARNMAN01';seed=index.resolve(entries[seed_ref])[0]
for aid,w in ids.items():
    candidates=[r for r in found if r['animation_id']==w['animation_id']]
    existing=next((r for r in candidates if r['resref']==preferred[aid]),candidates[0] if candidates else None)
    if existing and aid!=0x2100:representatives.append(dict(existing,name=w['name']));continue
    if aid==0x2100:
        # Preserve native Volo inventory/palette; remove finale scripts/dialogue in test copy.
        seed_ref=existing['resref'];seed=overrides[seed_ref].read_bytes() if seed_ref in overrides else index.resolve(entries[seed_ref])[0]
    ref=f'QLYR{aid:04X}';assert ref not in entries and ref not in overrides
    data=bytearray(seed);struct.pack_into('<H',data,0x28,aid)
    for offset in (0x248,0x250,0x258,0x260,0x268,0x2cc):data[offset:offset+8]=b'\0'*8
    allowed={0x28,0x29}|{i for o in (0x248,0x250,0x258,0x260,0x268,0x2cc) for i in range(o,o+8)}
    assert len(seed)==len(data) and all(a==b or i in allowed for i,(a,b) in enumerate(zip(seed,data)))
    path=ROOT/'sprite/.work'/HERE.name/(ref+'.cre');path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists();path.write_bytes(data)
    fixtures.append(dict(path=path.relative_to(ROOT).as_posix(),target=f'override/{ref}.cre',sha256=hashlib.sha256(data).hexdigest(),derived_from=seed_ref,source_sha256=hashlib.sha256(seed).hexdigest(),parent_target_existed=False))
    representatives.append(dict(resref=ref,animation_id=w['animation_id'],name=w['name'],source='generated-neutral-fixture',clua=f'C:CreateCreature("{ref}")'))
write_json(HERE/'creatures.json',dict(stock_or_override_consumers=found,stock_or_override_consumer_count=len(found),representatives=representatives,fixtures=fixtures,ingame_spawn_verified=False))
(HERE/'CLUA.txt').write_text('\n'.join(r['clua']+' -- '+r['name'] for r in representatives)+'\n',encoding='utf-8')
print(json.dumps(dict(consumers=len(found),fixtures=fixtures,representatives=representatives)),flush=True)
