"""Prepare metadata-only contracts and two isolated QA resources, no new images."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bg2lib import load_key,resolve_resource
from workspace_paths import get_path
from projectile_tracking import ability_projectiles

GAME=get_path('bg2ee_game_root',required=True)
OUT=ROOT/'projectiles/analysis/masque-capture-v12-20261028-v1'
sha=lambda b:hashlib.sha256(b).hexdigest().upper()


def main():
    assert not OUT.exists()
    bifs,entries=load_key()
    key={(n.upper(),t):loc for n,t,loc in entries}
    def read(n,t,ext):
        p=GAME/'override'/f'{n}.{ext}'
        return p.read_bytes() if p.exists() else resolve_resource(bifs,key[n,t])[0]
    for name in ['XQTARG','XQSEED']:
        assert not any(n==name for n,t in key)
        assert not list((GAME/'override').glob(name+'.*'))
    OUT.mkdir()
    (OUT/'qa').mkdir()
    source=read('OGRE01',1009,'cre')
    target=bytearray(source)
    struct.pack_into('<HH',target,0x24,500,500)
    target[0x248:0x270]=bytes(40)  # Five scripts: no autonomous combat/movement.
    target[0x280:0x2a0]=b'XQTARG'.ljust(32,b'\0')
    target[0x2cc:0x2d4]=bytes(8)
    allowed=set(range(0x24,0x28))|set(range(0x248,0x270))|set(range(0x280,0x2a0))|set(range(0x2cc,0x2d4))
    assert target[:8]==b'CRE V1.0' and len(target)==len(source) and target[0x270]==255
    assert all(i in allowed for i,(a,b) in enumerate(zip(source,target)) if a!=b)
    assert not any(target[0x248:0x270]) and struct.unpack_from('<HH',target,0x24)==(500,500)
    (OUT/'qa/XQTARG.cre').write_bytes(target)
    spell=read('SPWI304',1006,'spl')
    seed=bytearray(spell)
    fields=ability_projectiles(spell,'SPL')
    assert len(fields)==6 and all(n==234 for _,_,n in fields)
    for _,off,_ in fields:struct.pack_into('<H',seed,off,226)
    allowed={p for _,off,_ in fields for p in (off,off+1)}
    changed=[i for i,(a,b) in enumerate(zip(spell,seed)) if a!=b]
    assert set(changed)<=allowed and len(changed)==6
    assert all(n==226 for _,_,n in ability_projectiles(seed,'SPL'))
    item=read('FIRESEED',1005,'itm')
    assert ability_projectiles(item,'ITM')[0][2]==226
    (OUT/'qa/XQSEED.spl').write_bytes(seed)
    m=json.loads((GAME/'iee-assets/effects/manifest.json').read_text(encoding='utf-8-sig'))
    names=['SPMAGMIS','SPFIRSE2','SPCHLGT1','SPCHLGT2','SPCHLGT3']
    contracts=[]
    for name in names:
        r=next(r for r in m['resources'] if r['resref']==name)
        frames={f['resource_frame']:f for f in m['frames'] if f['resref']==name}
        timing=r['timeline']
        for seq,cycle in enumerate(r['cycles']):
            native=timing.get('native_frame_indices_by_cycle',[timing.get('native_frame_indices')])[seq]
            phases=timing.get('timeline_frame_indices_by_cycle',[timing.get('timeline_frame_indices')])[seq]
            count=len(cycle['frame_indices'])
            assert len(native)==count and len(phases)==count*2
            for phase,index in enumerate(phases):
                slot=phase//2
                w,h=frames[index]['logical_size_x1']
                assert frames[index]['physical_size_x4']==[w*4,h*4]
                for n in (name,name.lower()):
                    contracts.append(f'{n}\t{slot}\t{w}\t{h}\t{phase}\t{seq}\t{native[slot]}\t{index}\t0')
    (OUT/'contracts.tsv').write_text('\n'.join(contracts)+'\n',encoding='ascii')
    plan=dict(scope_added='SPMAGMIS only',cause='Missing FX per-pass scope leaves enclosing glow+flight capture incompatible; simulated regression covers64x78 and69x78',
        native_contracts=len(contracts),contract_resources=names,
        QA_resources={n:dict(bytes=len(d),sha256=sha(d)) for n,d in [('XQTARG.cre',target),('XQSEED.spl',seed)]},
        source_hashes={'OGRE01.cre':sha(source),'SPWI304.spl':sha(spell),'FIRESEED.itm':sha(item)},
        target_changes='500HP, five scripts empty, unique QA script name and no dialogue; graphics/animation/items/EA preserved',
        seed_changes='Only six projectile words234->226; same native BOLT2 as FIRESEED.ITM, ordinary Fireball damage retained',
        intended_distances=[[320,-80],[384,0],[320,80]],
        root_confirmation='Pending ingame; no promise that every MaskRejected case has been removed',
        no_image_PRO_metadata_or_motion_changes=True,
        sources=['https://gibberlings3.github.io/iesdp/file_formats/ie_formats/cre_v1.htm',
                 'https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm#252'])
    (OUT/'prepare.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Prepared SPMAGMIS fix proof,',len(contracts),'native contracts and two new QA resources')


if __name__=='__main__':main()
