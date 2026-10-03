"""Find native CRE consumers; one representative CLUA per distinct bird resource."""
from itertools import groupby
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex
from workspace_paths import get_path
from palette_work_plan import write_json
game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game)
ids={0xd000:'AEAGG1',0xd100:'AGULG1',0xd200:'AVULG1',0xd300:'ABIRG1',0xd400:'ABIRG1'}
overrides={p.stem.upper():p for p in (game/'override').iterdir() if p.is_file() and p.suffix.lower()=='.cre'}
entries=index.resource_map(0x3f1);found=[]
def examine(ref,raw,source):
    if len(raw)<0x33 or raw[:8]!=b'CRE V1.0':raise ValueError('unknown live CRE: '+ref)
    aid=struct.unpack_from('<H',raw,0x28)[0]
    if aid in ids:found.append(dict(resref=ref,animation_id=f'0x{aid:04X}',bam=ids[aid],source=source,
        sha256=hashlib.sha256(raw).hexdigest(),clua=f'C:CreateCreature("{ref}")'))
for bif,group in groupby(sorted(entries.items(),key=lambda pair:pair[1][2]>>20),key=lambda pair:pair[1][2]>>20):
    for ref,entry in group:
        if ref in overrides:continue
        raw,source=index.resolve(entry);examine(ref,raw,'stock:'+source)
    index._bif_cache.clear()
for ref,path in sorted(overrides.items()):examine(ref,path.read_bytes(),'config://bg2ee_game_root/override/'+path.name)
found.sort(key=lambda r:r['resref']);representatives=[]
for ref in ('AEAGG1','AGULG1','AVULG1','ABIRG1'):
    group=[r for r in found if r['bam']==ref]
    if group:representatives.append(group[0])
assert not (HERE/'creatures.json').exists()
write_json(HERE/'creatures.json',dict(schema='bg2-flying-live-CRE-v1',stock_cre_scanned=len(entries),
    override_cre_scanned=len(overrides),precedence='override first; KEY/BIF otherwise',creatures=found,
    representatives=representatives,missing_BAM_representatives=sorted(set(ids.values())-{r['bam'] for r in representatives}),ingame_spawn_verified=False))
(HERE/'CLUA.txt').write_text('\n'.join(r['clua'] for r in representatives)+'\n',encoding='utf-8')
print(json.dumps(dict(consumers=len(found),representatives=representatives)))
