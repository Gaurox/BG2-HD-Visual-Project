"""Census live CRE consumers and make one spawnable representative per model."""
import hashlib,json,struct,sys
from itertools import groupby
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex
from workspace_paths import get_path
from palette_work_plan import write_json
selection=json.loads((HERE/'selection.json').read_text(encoding='utf-8-sig'));ids={int(w['animation_id'],16):w for w in selection['witnesses']}
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);entries=index.resource_map(0x3f1)
overrides={p.stem.upper():p for p in (game/'override').iterdir() if p.is_file() and p.suffix.lower()=='.cre'}
found=[]
def examine(ref,raw,source):
    assert raw[:8]==b'CRE V1.0' and len(raw)>=0x33,ref
    aid=struct.unpack_from('<H',raw,0x28)[0]
    if aid in ids:found.append(dict(resref=ref,animation_id=f'0x{aid:04X}',source=source,sha256=hashlib.sha256(raw).hexdigest(),clua=f'C:CreateCreature("{ref}")'))
for _,group in groupby(sorted(entries.items(),key=lambda pair:pair[1][2]>>20),key=lambda pair:pair[1][2]>>20):
    for ref,entry in group:
        if ref in overrides:continue
        raw,source=index.resolve(entry);examine(ref,raw,'stock:'+source)
    index._bif_cache.clear()
for ref,p in sorted(overrides.items()):examine(ref,p.read_bytes(),'config://bg2ee_game_root/override/'+p.name)
found.sort(key=lambda r:r['resref']);representatives=[];fixtures=[]
seed=dict(resref='ARNMAN01'); seed_raw=index.resolve(entries[seed['resref']])[0]; seed['sha256']=hashlib.sha256(seed_raw).hexdigest()
seed_raw=overrides[seed['resref']].read_bytes() if seed['resref'] in overrides else index.resolve(entries[seed['resref']])[0]
assert struct.unpack_from('<H',seed_raw,0x28)[0]==0xB200 and hashlib.sha256(seed_raw).hexdigest()==seed['sha256']
preferred={0x6400:'DRIZZT',0x6401:'AMELM01',0x6402:'MONKTU1',0x6403:'SKELET01',0x6404:'SAREVOKD'}
for aid,w in ids.items():
    existing=next((r for r in found if r['animation_id']==w['animation_id'] and r['resref']==preferred.get(aid)),None)
    if existing is None:existing=next((r for r in found if r['animation_id']==w['animation_id']),None)
    if existing and aid not in (0x6405,0x6406):representatives.append(dict(existing,name=w['name']));continue
    ref=f'QCOL{aid:04X}';assert ref not in entries and ref not in overrides
    data=bytearray(seed_raw);struct.pack_into('<H',data,0x28,aid)
    changes=[dict(offset=0x28,bytes=2,field='animation',value=f'{aid:04X}')]
    if aid in (0x6405,0x6406):
        # CRE V1.0: five script resrefs and dialogue, empty for test witnesses.
        for offset in (0x248,0x250,0x258,0x260,0x268,0x2cc):
            data[offset:offset+8]=b'\0'*8
            changes.append(dict(offset=offset,bytes=8,field='script' if offset<0x2cc else 'dialogue',value='empty'))
    allowed={i for c in changes for i in range(c['offset'],c['offset']+c['bytes'])}
    assert len(data)==len(seed_raw) and all(a==b or i in allowed for i,(a,b) in enumerate(zip(seed_raw,data)))
    target=ROOT/'sprite/.work/q3m-character-old-full-x2-20261004-v1'/f'{ref}.cre';target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists();target.write_bytes(data)
    fixture=dict(path=target.relative_to(ROOT).as_posix(),target=f'override/{ref}.cre',sha256=hashlib.sha256(data).hexdigest(),derived_from=seed['resref'],source_sha256=seed['sha256'],changed_fields=changes,unrelated_bytes_unchanged=True,parent_target_existed=False)
    fixtures.append(fixture);representatives.append(dict(resref=ref,animation_id=w['animation_id'],name=w['name'],source='generated-test-fixture',clua=f'C:CreateCreature("{ref}")'))
write_json(HERE/'creatures.json',dict(stock_or_override_consumers=found,stock_or_override_consumer_count=len(found),representatives=representatives,fixtures=fixtures,ingame_spawn_verified=False))
(HERE/'CLUA-generiques.txt').write_text('\n'.join(r['clua']+' -- '+r['name'] for r in representatives)+'\n',encoding='utf-8')
print(json.dumps(dict(consumers=len(found),fixtures=len(fixtures),representatives=representatives)))
