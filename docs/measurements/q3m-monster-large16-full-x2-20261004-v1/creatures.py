"""Read live CRE consumers; build a reversible A200 test CRE if stock has none."""
from itertools import groupby
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex
from workspace_paths import get_path
from palette_work_plan import write_json
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game)
overrides={p.stem.upper():p for p in (game/'override').iterdir() if p.is_file() and p.suffix.lower()=='.cre'}
entries=index.resource_map(0x3f1);found=[];ids={0xA000:'MWYV',0xA100:'MCAR',0xA200:'MWYV'}
assert not (HERE/'creatures.json').exists(),'new run required'
def examine(ref,raw,source):
    assert len(raw)>=0x33 and raw[:8]==b'CRE V1.0',ref
    aid=struct.unpack_from('<H',raw,0x28)[0]
    if aid in ids:found.append(dict(resref=ref,animation_id=f'0x{aid:04X}',body_resref=ids[aid],source=source,
                                  sha256=hashlib.sha256(raw).hexdigest(),clua=f'C:CreateCreature("{ref}")'))
for _,group in groupby(sorted(entries.items(),key=lambda pair:pair[1][2]>>20),key=lambda pair:pair[1][2]>>20):
    for ref,entry in group:
        if ref in overrides:continue
        raw,source=index.resolve(entry);examine(ref,raw,'stock:'+source)
    index._bif_cache.clear()
for ref,p in sorted(overrides.items()):examine(ref,p.read_bytes(),'config://bg2ee_game_root/override/'+p.name)
found.sort(key=lambda r:r['resref']);representatives=[next(r for r in found if r['resref']==ref) for ref in ('WYVBAB01','CARCRA01')]
white=next((r for r in found if r['animation_id']=='0xA200'),None);fixture=None
if white is None:
    ref='QMWYVW01';assert ref not in entries and ref not in overrides
    if 'WYVBAB01' in overrides:source=overrides['WYVBAB01'].read_bytes()
    else:source,_=index.resolve(entries['WYVBAB01'])
    assert struct.unpack_from('<H',source,0x28)[0]==0xA000
    data=bytearray(source);struct.pack_into('<H',data,0x28,0xA200)
    assert bytes(data[:0x28])+bytes(data[0x2A:])==source[:0x28]+source[0x2A:]
    target=ROOT/'sprite/.work/q3m-monster-large16-full-x2-20261004-v1'/(''+ref+'.cre')
    target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();target.write_bytes(data)
    fixture=dict(path=target.relative_to(ROOT).as_posix(),target='override/'+ref+'.cre',sha256=hashlib.sha256(data).hexdigest(),
                 bytes=len(data),parent_target_existed=False,derived_from='WYVBAB01',source_sha256=hashlib.sha256(source).hexdigest(),
                 only_change='CRE V1.0 animation uint16 at 0x28: A000 -> A200')
    white=dict(resref=ref,animation_id='0xA200',body_resref='MWYV',source='generated-test-fixture',sha256=fixture['sha256'],clua=f'C:CreateCreature("{ref}")')
representatives.append(white)
write_json(HERE/'creatures.json',dict(schema='bg2-Large16-live-CRE-v1',stock_cre_scanned=len(entries),override_cre_scanned=len(overrides),
    precedence='override first; KEY/BIF otherwise',stock_or_override_consumers=found,stock_or_override_consumer_count=len(found),
    representatives=representatives,fixture=fixture,distinct_original_sprite_models=2,available_animation_ids=3,ingame_spawn_verified=False))
(HERE/'CLUA-generiques.txt').write_text('\n'.join(r['clua'] for r in representatives)+'\n',encoding='utf-8',newline='\n')
(HERE/'CLUA-tous-consommateurs.txt').write_text('\n'.join(r['clua'] for r in found+([white] if fixture else []))+'\n',encoding='utf-8',newline='\n')
print(json.dumps(dict(consumers=len(found),representatives=representatives,fixture=fixture)))
