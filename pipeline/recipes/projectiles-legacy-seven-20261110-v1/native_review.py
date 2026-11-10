"""Bounded native evidence for legacy IDs; no new hooks, builds or game writes."""
from pathlib import Path
import hashlib
import json
import struct
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'pipeline/recipes/projectiles-secondary-links-20261028-v1')]
from native import PE
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from projectile_tracking import ids_entries,ability_projectiles
OUT=ROOT/'projectiles/analysis/legacy-seven-usage-20261110-v1'
TARGET_RAW={22,25,26,45,93,97,242}
NAMES={b'SPBRNHND',b'SPSMKJET',b'COLRSPRY',b'SPHOLYMT',b'LIGHTSTO',b'MAGMIS'}


def digest(raw):return hashlib.sha256(raw).hexdigest().upper()
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')


def main():
    assert not (OUT/'native-review.json').exists()
    pe=PE();assert digest(pe.data)=='B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57'
    va,off,size=next(s for s in pe.sections if s[0]==0x1000)
    text=pe.data[off:off+size]
    def direct_refs(target):
        refs=[]
        # Scan every byte, not one linear disassembly through embedded jump tables.
        for i,op in enumerate(text[:-4]):
            if op not in (0xe8,0xe9):continue
            address=va+i;dest=address+5+struct.unpack_from('<i',text,i+1)[0]
            if dest==target:
                ins=next(pe.instructions(address,address+5));assert ins.size==5 and ins.mnemonic in ('call','jmp')
                refs.append((address,ins.mnemonic))
        return refs
    callers=[];asm=[]
    for address,kind in direct_refs(0x22bf00):
        region=next((s,e) for s,e in pe.funcs if s<=address<e)
        ins=list(pe.instructions(region[0],region[1]));at=next(i for i,v in enumerate(ins) if v.address==address)
        window=ins[max(0,at-20):min(len(ins),at+5)]
        lines=[f'{v.address:x}: {v.mnemonic} {v.op_str}' for v in window]
        writes=[v.op_str for v in window if v.address<address and v.mnemonic=='mov' and v.op_str.startswith('ecx, 0x')]
        immediate=int(writes[-1].split(', ')[1],16) if writes else None
        # An immediate is reported as a local observation, not a complete CFG/dataflow result.
        callers.append(dict(call=hex(address),instruction=kind,unwind_region=[hex(x) for x in region],
            local_ecx_immediate=immediate,local_immediate_hits_legacy=immediate in TARGET_RAW))
        asm.append('\n'.join(lines))
    literalrefs=[]
    for i in range(len(text)-6):
        # RIP-relative LEA/MOV of a64-bit literal pointer, decoded independently.
        if text[i] not in (0x48,0x4c) or text[i+1] not in (0x8d,0x8b) or text[i+2]&0xc7!=5:continue
        address=va+i;target=address+7+struct.unpack_from('<i',text,i+3)[0];p=pe.off(target)
        if p is None:continue
        value=pe.data[p:p+24].split(b'\0')[0].upper()
        if value in NAMES:
            literalrefs.append(dict(instruction=hex(address),literal=value.decode('ascii'),target=hex(target)))
    ranges=[('cone-constructor',0x227800,0x22792a),('legacy-factory-21',0x22bffc,0x22c156),
        ('legacy-factory-44',0x22c1e6,0x22c32c),('legacy-factory-96',0x22c8c7,0x22c9e4),
        ('legacy-factory-241',0x22e7b4,0x22e83c),('effect-provenance-factory',0x14c930,0x14ca6e),
        ('spell-item-projectile-helper',0x353e90,0x3540e0),
        ('SPHOLYMT-215-name',0x3c0aa1,0x3c0ab4),('SPHOLYMT-215-dispatch',0x3c0d7c,0x3c0e33),
        ('opcode327-index-range',0x1cab18,0x1cab43)]
    (OUT/'native').mkdir()
    for name,start,stop in ranges:(OUT/'native'/(name+'.asm')).write_text(pe.dump(start,stop)+'\n',encoding='utf-8')
    (OUT/'native/factory-callers.asm').write_text('\n\n'.join(asm)+'\n',encoding='utf-8')
    assert not any(r['local_immediate_hits_legacy'] for r in callers)
    assert len(direct_refs(0x227800))==2
    assert "mov edx, 0xd7" in pe.dump(0x3c0d7c,0x3c0e33)
    game=get_path('bg2ee_game_root',required=True);manifest=json.loads((game/'iee-assets/effects/manifest.json').read_text(encoding='utf-8'))
    catalog={r['resref']:r for r in manifest['resources']}
    bifs,entries=load_key();key={(n.upper(),t):loc for n,t,loc in entries};projectl=ids_entries(resolve_resource(bifs,key['PROJECTL',1008])[0])
    normal=[]
    for name,label in [('SPWI103','Burning Hands'),('SPWI105','Color Spray'),('SPWI503','Cone of Cold'),('SPPR302','Call Lightning'),('SPPR412','Negative Plane Protection')]:
        raw=resolve_resource(bifs,key[name,1006])[0]
        normal.append(dict(spell=name,label=label,source_sha256=digest(raw),
            ability_routes=sorted({f'{v-1}:{projectl.get(v-1,"engine")}' for _,_,v in ability_projectiles(raw,'SPL')})))
    selected={}
    for name in ['SPBRNHND','SPSMKJET','SPHOLYMT']:
        p=ROOT/f'effects/index/selections/{name}.json';s=json.loads(p.read_text(encoding='utf-8'))
        for evidence in [s['qa_evidence'],s['runtime_pack']['manifest']]:assert digest((ROOT/evidence['path']).read_bytes())==evidence['sha256']
        selected[name]=dict(selection_sha256=digest(p.read_bytes()),QA=s['qa_evidence'],pack=s['runtime_pack']['manifest'],catalogued=name in catalog)
    save(OUT/'native-review.json',dict(executable_sha256=digest(pe.data),factory_RVA='0x22bf00',direct_factory_references=callers,
        address_taken_absolute_pointers=pe.data.count(struct.pack('<Q',0x14022bf00)),literal_references=literalrefs,
        cone_constructor_calls=[hex(a) for a,_ in direct_refs(0x227800)],ordinary_spell_examples=normal,
        selected_assets=selected,COLRSPRY=dict(stock_BAM_present=('COLRSPRY',1000) in key,installed_catalogue_present='COLRSPRY' in catalog),
        MAGMIS=dict(stock_BAM_present=('MAGMIS',1000) in key,override_BAM_present=(game/'override/MAGMIS.bam').exists()),
        SPHOLYMT_secondary_literal='Native0x3c0aa1 resref dispatch prepares opcode215 at0x3c0dbb;not a factory241 launch.',
        limits=['Local register windows are observations,not a whole-program proof of every computed runtime ID.',
            'Native optional runtime parameters,console,savegames,future mods or another multiplayer client may introduce an ID;preserve native behavior.',
            'Asset usage through215 orCreateVisualEffectObject is distinct from using a legacy PROJECTL ID.']))
    print('Native pinned: factory refs',len(callers),'literal refs',len(literalrefs),'no local fixed legacy argument;SPHOLYMT auxiliary route is opcode215.')


if __name__=='__main__':main()
