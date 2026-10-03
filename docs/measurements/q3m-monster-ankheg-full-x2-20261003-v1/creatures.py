"""Resolve actual live CRE consumers; one CLUA for the single Ankheg sprite model."""
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
entries=index.resource_map(0x3f1);found=[]
def examine(ref,raw,source):
    if len(raw)<0x33 or raw[:8]!=b'CRE V1.0':raise ValueError('unknown live CRE: '+ref)
    aid=struct.unpack_from('<H',raw,0x28)[0]
    if aid==0x3000:found.append(dict(resref=ref,animation_id='0x3000',body_resref='MAKH',source=source,
        sha256=hashlib.sha256(raw).hexdigest(),clua=f'C:CreateCreature("{ref}")'))
assert not (HERE/'creatures.json').exists(),'new run required'
for bif,group in groupby(sorted(entries.items(),key=lambda pair:pair[1][2]>>20),key=lambda pair:pair[1][2]>>20):
    for ref,entry in group:
        if ref in overrides:continue
        raw,source=index.resolve(entry);examine(ref,raw,'stock:'+source)
    index._bif_cache.clear()
for ref,path in sorted(overrides.items()):examine(ref,path.read_bytes(),'config://bg2ee_game_root/override/'+path.name)
found.sort(key=lambda r:r['resref']);require_generic=next((r for r in found if r['resref']=='ANKHEG01'),None)
assert require_generic is not None,'generic Ankheg CRE absent; inspect census before choosing a representative'
write_json(HERE/'creatures.json',dict(schema='bg2-ankheg-live-CRE-v1',stock_cre_scanned=len(entries),
    override_cre_scanned=len(overrides),precedence='override first; KEY/BIF otherwise',creatures=found,
    representatives=[require_generic],distinct_sprite_models=1,ingame_spawn_verified=False))
(HERE/'CLUA.txt').write_text(require_generic['clua']+'\n',encoding='utf-8')
print(json.dumps(dict(consumers=len(found),representatives=[require_generic])))
