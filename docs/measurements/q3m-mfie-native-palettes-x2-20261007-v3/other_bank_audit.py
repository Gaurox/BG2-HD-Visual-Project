"""Read-only follow-up evidence; never changes accepted IDs or their QA."""
import hashlib,json,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_work_plan import write_json
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
game=get_path('bg2ee_game_root',required=True);idx=registry.KeyIndex(game);bmp=idx.resource_map(1)
gen=json.loads((HERE/'current-generation.json').read_text())
assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
items=[]
for aid,prefix in [('0x7312','MFIE'),('0x7313','MFIS')]:
    palettes=[];sources=[]
    for bank in '12':
        ref=prefix+'G'+bank+'B';raw,source=idx.resolve(bmp[ref]);count=struct.unpack_from('<I',raw,46)[0] or 256
        assert count==256
        palettes.append(np.frombuffer(raw[54:54+count*4],'<u4'))
        sources.append(dict(resref=ref,entries=count,sha256=hashlib.sha256(raw).hexdigest(),source_BIF=source))
    routes=[r for r in cat['directory'] if r['animation_id']==aid and r['resref'].startswith(prefix+'G2')]
    comparisons=[]
    for r in routes:
        info=leaves.inspect(assets/Path(cat['shards'][r['shard_index']]['registry']).name,include_frames=True)
        actual=np.frombuffer(info['resources'][r['resource_ordinal']]['profile'].source.tobytes(),'<u4')
        comparisons.append(dict(resref=r['resref'],source_matches_G1=bool(np.array_equal(actual&0xffffff,palettes[0]&0xffffff)),
            source_RGB_mismatches_against_native_G2=int(np.count_nonzero((actual&0xffffff)!=(palettes[1]&0xffffff)))))
    assert routes and all(c['source_matches_G1'] for c in comparisons)
    items.append(dict(animation_id=aid,native_palettes=sources,G1_G2_RGB_differences=int(np.count_nonzero((palettes[0]&0xffffff)!=(palettes[1]&0xffffff))),
        G2_bindings=comparisons,observation='static source/native bank discrepancy; live G2 capture not observed',
        ingame_failure_confirmed=False,historical_user_QA_preserved=True,assets_modified=False))
assert not(HERE/'other-bank-audit.json').exists()
write_json(HERE/'other-bank-audit.json',dict(scope='read-only additional bank audit',items=items,other_IDs_modified=False,QA_decisions_modified=False,
    follow_up='Observe G2 attacks for QMON7312/QMON7313 separately; no inferred ingame failure or automatic family regeneration.'))
print(json.dumps(dict(read_only=True,possible_follow_up_ids=[i['animation_id'] for i in items])),flush=True)
