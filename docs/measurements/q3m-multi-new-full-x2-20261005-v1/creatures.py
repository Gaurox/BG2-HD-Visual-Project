"""Ten neutral visible fixtures; never inherit cinematic/combat equipment effects."""
import json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import hashlib
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game);entries=index.resource_map(1009)
seed,source=index.resolve(entries['ARNMAN01']);u=lambda o:struct.unpack_from('<I',seed,o)[0]
assert u(0x20)==0 and seed[0x7e]==0 and u(0x2c8)==u(0x2c0)==0
fixtures=[];representatives=[];selection=json.loads((HERE/'selection.json').read_text())
WORK.mkdir(exist_ok=True)
for w in selection['witnesses']:
    ref='QMUL'+w['animation_id'][2:];target=game/'override'/(ref+'.cre');assert ref not in entries and not target.exists()
    b=bytearray(seed);struct.pack_into('<I',b,0x28,int(w['animation_id'],16));b[0x270]=128
    for o in (0x248,0x250,0x258,0x260,0x268,0x2cc):b[o:o+8]=bytes(8)
    b[0x280:0x2a0]=ref.encode().ljust(32,b'\0')
    path=WORK/(ref+'.cre');assert not path.exists();path.write_bytes(b)
    allowed=set(range(0x28,0x2c))|{0x270}|set(range(0x280,0x2a0))|{i for o in (0x248,0x250,0x258,0x260,0x268,0x2cc) for i in range(o,o+8)}
    assert len(b)==len(seed) and all(a==v or i in allowed for i,(a,v) in enumerate(zip(seed,b)))
    assert struct.unpack_from('<I',b,0x20)[0]==0 and b[0x7e]==0 and struct.unpack_from('<I',b,0x2c8)[0]==struct.unpack_from('<I',b,0x2c0)[0]==0
    fixtures.append(dict(path=path.relative_to(ROOT).as_posix(),target='override/'+ref+'.cre',sha256=file_sha(path),derived_from='ARNMAN01',source_BIF=source,source_sha256=hashlib.sha256(seed).hexdigest(),parent_target_existed=False,invisible_states_effects_equipment_absent=True))
    representatives.append(dict(resref=ref,animation_id=w['animation_id'],name=w['name'],clua=f'C:CreateCreature("{ref}")'))
write_json(HERE/'creatures.json',dict(fixtures=fixtures,representatives=representatives,ingame_spawn_verified=False))
(HERE/'CLUA.txt').write_text('\n'.join(r['clua']+' -- '+r['name'] for r in representatives)+'\n',encoding='utf-8')
print(json.dumps(dict(fixtures=len(fixtures),neutral_no_scripts_no_effects_no_items=True)))
