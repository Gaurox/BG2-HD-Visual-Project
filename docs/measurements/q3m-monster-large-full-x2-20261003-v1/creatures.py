"""List live stock+override CRE consumers of the Ogre animation; no game writes."""
from itertools import groupby
import hashlib,json,struct,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from run_creature_sprite_x2 import KeyIndex
from workspace_paths import get_path
from palette_work_plan import write_json

def scan():
    game=get_path('bg2ee_game_root',required=True);index=KeyIndex(game)
    overrides={p.stem.upper():p for p in (game/'override').iterdir() if p.is_file() and p.suffix.lower()=='.cre'}
    entries=index.resource_map(0x3f1);found=[];stock_count=0
    tlkpath=game/'lang/fr_FR/dialog.tlk'
    if not tlkpath.exists():tlkpath=game/'lang/en_US/dialog.tlk'
    tlk=tlkpath.read_bytes();assert tlk[:8]==b'TLK V1  '
    count,base=struct.unpack_from('<II',tlk,10)
    def name(ref):
        if ref>=count:return ''
        offset,length=struct.unpack_from('<II',tlk,18+26*ref+18)
        text=tlk[base+offset:base+offset+length]
        try:return text.decode('utf-8')
        except UnicodeDecodeError:return text.decode('cp1252')
    def examine(ref,raw,source):
        if len(raw)<0x33 or raw[:8]!=b'CRE V1.0':raise ValueError('unknown live CRE: '+ref)
        if struct.unpack_from('<H',raw,0x28)[0]!=0x9000:return
        longname=struct.unpack_from('<I',raw,8)[0]
        found.append(dict(resref=ref,name=name(longname),animation_id='0x9000',
                          source=source,sha256=hashlib.sha256(raw).hexdigest(),
                          colour_ranges=list(raw[0x2c:0x33]),clua=f'C:CreateCreature("{ref}")'))
    for bif,group in groupby(sorted(entries.items(),key=lambda pair:pair[1][2]>>20),key=lambda pair:pair[1][2]>>20):
        for ref,entry in group:
            stock_count+=1
            if ref in overrides:continue
            raw,source=index.resolve(entry);examine(ref,raw,'stock:'+source)
        index._bif_cache.clear()
    for ref,path in sorted(overrides.items()):examine(ref,path.read_bytes(),'config://bg2ee_game_root/override/'+path.name)
    found.sort(key=lambda row:row['resref'])
    report=dict(schema='bg2-monster-large-live-CRE-v1',animation_id='0x9000',
                stock_cre_scanned=stock_count,override_cre_scanned=len(overrides),
                precedence='override first; KEY/BIF otherwise',tlk='config://bg2ee_game_root/'+tlkpath.relative_to(game).as_posix(),
                creatures=found,count=len(found),ingame_spawn_verified=False)
    assert found and not (HERE/'creatures.json').exists()
    write_json(HERE/'creatures.json',report)
    (HERE/'CLUA.txt').write_text('\n'.join(r['clua'] for r in found)+'\n',encoding='utf-8')
    print(json.dumps(dict(count=len(found),creatures=[dict(resref=r['resref'],name=r['name']) for r in found]),ensure_ascii=False))

if __name__=='__main__':scan()
