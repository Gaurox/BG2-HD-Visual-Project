"""Independent Codex inventory: reads KEY/BIFF only, never local audits/override content."""
from pathlib import Path
import collections, csv, hashlib, json, re, struct, sys, zlib
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import bg2lib
from bam_export import decode_bam

BIFS, RES = bg2lib.load_key()
RES_BY = {(n.upper(), t):(n,t,l) for n,t,l in RES}
INDEX = {}
GAME = Path(bg2lib.GAME_DIR)
EXTRACT = OUT / 'vanilla_inventory'
EXTRACT.mkdir(exist_ok=True)

def read(entry):
    n,t,loc=entry
    bif=BIFS[(loc>>20)&0xfff]
    buf=bg2lib.get_bif_buffer(bif)
    if bif not in INDEX:
        count,_,off=struct.unpack_from('<III',buf,8)
        INDEX[bif] = {struct.unpack_from('<I',buf,off+i*16)[0]&0x3fff:struct.unpack_from('<II',buf,off+i*16+4) for i in range(count)}
    off,size=INDEX[bif][loc&0x3fff]
    return buf[off:off+size],bif

def put_csv(name,rows):
    with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]))
        w.writeheader();w.writerows(rows)

def get_tlk():
    p=GAME/'lang/en_US/dialog.tlk'
    if not p.exists(): return lambda _: ''
    data=p.read_bytes();base=struct.unpack_from('<I',data,14)[0]; count=struct.unpack_from('<I',data,10)[0]
    def name(i):
        if i>=count:return ''
        off,size=struct.unpack_from('<II',data,18+i*26+18)
        return data[base+off:base+off+size].decode('utf-8',errors='replace').replace('\r',' ').replace('\n',' ')
    return name

tlk=get_tlk()
items=[]; code_items=collections.defaultdict(list)
for key,e in RES_BY.items():
    if e[1]!=1005:continue
    d,b=read(e)
    if d[:8]!=b'ITM V1  ':continue
    code=d[0x22:0x24].decode('ascii',errors='replace').strip(' \0')
    cat=struct.unpack_from('<H',d,0x1c)[0]
    if not code and cat not in (2,7,12,32,41):continue
    flags=struct.unpack_from('<I',d,0x18)[0];unusable=struct.unpack_from('<I',d,0x1e)[0]
    ext=struct.unpack_from('<I',d,0x64)[0];num=struct.unpack_from('<H',d,0x68)[0]
    fx=struct.unpack_from('<I',d,0x6a)[0];idx,nfx=struct.unpack_from('<HH',d,0x6e)
    color=[];other_visual=[]
    for i in range(nfx):
        o=fx+(idx+i)*48
        op=struct.unpack_from('<H',d,o)[0];p1,p2=struct.unpack_from('<II',d,o+4)
        if op in (7,8,9,50,51,52): color.append({'opcode':op,'p1':p1,'p2':p2})
        if op in (53,57,65,100,135,138,146,215,232,272,321):other_visual.append({'opcode':op,'p1':p1,'p2':p2,'resource':d[o+20:o+28].split(b'\0')[0].decode('ascii',errors='replace')})
    item={'resref':e[0], 'name':tlk(struct.unpack_from('<I',d,12)[0]),'category':cat,'appearance':code,'two_handed':bool(flags&2),'fighter_allowed_by_base_mask':not bool(unusable&(1<<11)),'human_allowed_by_base_mask':not bool(unusable&(1<<27)),'ability_types':','.join(str(d[ext+i*56]) for i in range(num)),'inventory_icon':d[0x3a:0x42].split(b'\0')[0].decode('ascii',errors='replace'),'ground_icon':d[0x44:0x4c].split(b'\0')[0].decode('ascii',errors='replace'),'source_archive':b,'color_effects':json.dumps(color,separators=(',',':')),'other_visual_effects':json.dumps(other_visual,separators=(',',':'))}
    items.append(item)
    if code:code_items[code].append(item)

all_codes=sorted({n[3:5] for n,t in RES_BY if t==1000 and n.startswith('WQN')})
BODY=[f'CHFB{i}' for i in [1,2,3]]+['CHFF4']
assets=[]; details=[]
for (name,typ),entry in sorted(RES_BY.items()):
    if typ!=1000:continue
    if any(name.startswith(p) for p in BODY) and not name.endswith('INV'):
        role='world_body'; family=name[:5]; code=''; suffix=name[5:]
    elif re.fullmatch('CHFF[1-4]INV',name):
        role='paperdoll_body';family='CHFF';code=name[4];suffix='INV'
    elif name.startswith('WQN'):
        code=name[3:5];suffix=name[5:]; family=name[:5]
        role='world_helmet' if code.startswith(('H','J')) and code!='HB' else ('world_wings' if code=='ZW' else ('world_shield' if re.fullmatch('[CD][0-7]',code) else ('world_weapon_offhand' if suffix.startswith('O') else 'world_weapon')))
    elif re.fullmatch('WPN..(INV|OIN)',name):
        role='paperdoll_equipment';family=name[:5];code=name[3:5];suffix=name[5:]
    else:continue
    raw,bif=read(entry)
    d=zlib.decompress(raw[12:]) if raw[:4]==b'BAMC' else raw
    if d[:8]!=b'BAM V1  ': raise ValueError((name,d[:8]))
    nf,nc,tr=struct.unpack_from('<HBB',d,8);of,op,ol=struct.unpack_from('<III',d,12)
    cycles=[]
    for c in range(nc):
        count,start=struct.unpack_from('<HH',d,of+nf*12+c*4)
        indices=list(struct.unpack_from('<'+str(count)+'H',d,ol+start*2))
        cycles.append({'cycle':c,'frame_count':count,'lookup_start':start,'frames':indices})
    frames,pal,tr=decode_bam(d)
    substantial=[a.size>1 for a,_,_,_ in frames]
    for c in cycles:
        c['substantial_frame_references']=sum(substantial[i] for i in c['frames'])
    hist=np.zeros(256,dtype=np.int64)
    for arr,cx,cy,_ in frames:hist+=np.bincount(arr.ravel(),minlength=256)
    used=np.flatnonzero(hist)
    linked=code_items.get(code,[])
    if role in ('world_helmet','world_wings'):linked=[i for i in linked if i['category']==7]
    elif role=='world_shield':linked=[i for i in linked if i['category'] in (12,41)]
    elif role.startswith('world_weapon'):linked=[i for i in linked if i['category'] in range(15,31)]
    eligible=[i for i in linked if i['fighter_allowed_by_base_mask'] and i['human_allowed_by_base_mask']]
    active=[c for c in cycles if c['frame_count']]
    row={'resref':name,'role':role,'family':family,'appearance_code':code,'suffix':suffix,'source_archive':bif,'source_kind':'KEY_BIFF_no_override','sha256_source':hashlib.sha256(raw).hexdigest(),'bytes_source':len(raw),'frames':nf,'frames_larger_than_1px':sum(substantial),'cycles':nc,'nonempty_cycles':len(active),'frame_references':sum(c['frame_count'] for c in cycles),'max_width':max(a.shape[1] for a,_,_,_ in frames),'max_height':max(a.shape[0] for a,_,_,_ in frames),'transparent_index':tr,'shadow_index1_pixels':int(hist[1]),'pixels_2_87':int(hist[2:88].sum()),'pixels_88_167':int(hist[88:168].sum()),'pixels_168_254':int(hist[168:255].sum()),'pixels_255':int(hist[255]),'used_indices':','.join(map(str,used)),'linked_itm_count':len(linked),'base_mask_eligible_itm_count':len(eligible),'itm_examples':','.join(i['resref'] for i in eligible[:8] or linked[:8]),'override_file_exists':(GAME/'override'/(name+'.bam')).exists()}
    assets.append(row)
    details.append(dict(row,cycle_details=cycles,palette_rgb=pal.tolist(),index_histogram=hist.tolist(),frame_geometry=[{'frame':j,'width':a.shape[1],'height':a.shape[0],'cx':cx,'cy':cy} for j,(a,cx,cy,_) in enumerate(frames)]))
    if role=='world_body':
        selected={'G1':range(9,18),'G11':range(0,9),'G12':range(18,27),'G13':range(27,36),'G14':range(36,45),'G15':range(45,54),'G16':range(54,63),'G17':range(63,72),'G18':range(72,81),'G19':range(81,99)}.get(suffix,range(nc))
        details[-1]['body_cycle_groups_expected']=list(selected)
        details[-1]['referenced_unique_frames_expected']=len({i for c in cycles if c['cycle'] in selected for i in c['frames']})
    (EXTRACT/(name+'.BAM')).write_bytes(raw)
    if len(assets)%100==0: print('BAM processed',len(assets),flush=True)

for name,typ,ext in [('6110',2050,'INI'),('ANIMATE',1008,'IDS'),('ANISND',1008,'IDS'),('ITEMANIM',1012,'2DA'),('EXTANIM',1012,'2DA')]:
    raw,bif=read(RES_BY[(name,typ)]);(EXTRACT/(name+'.'+ext)).write_bytes(raw)

put_csv('assets_inventory.csv',assets)
put_csv('assets_inventory_items.csv',sorted(items,key=lambda x:(x['appearance'],x['resref'])))
summary={'animation_id':'0x6110','inventory_scope':'World body complete; all WQN equipment archive stock; CHFF body paperdolls; all WPN inventory equipment stock (includes unused variants)','source_key':'config://bg2ee_game_root/chitin.key','source_key_sha256':hashlib.sha256((GAME/'chitin.key').read_bytes()).hexdigest(),'archives_used':sorted({r['source_archive'] for r in assets}),'body_prefixes':BODY,'asset_count':len(assets),'roles':dict(collections.Counter(r['role'] for r in assets)),'frames_by_role':dict((role,sum(x['frames'] for x in assets if x['role']==role)) for role in sorted({r['role'] for r in assets})),'substantial_frames_by_role':dict((role,sum(x['frames_larger_than_1px'] for x in assets if x['role']==role)) for role in sorted({r['role'] for r in assets})),'equipment_codes':all_codes,'code_item_counts_all_categories':{c:len(code_items.get(c,[])) for c in all_codes},'nonempty_override_count':sum(r['override_file_exists'] for r in assets),'items_total_with_appearance_or_armor_helmet_shield_cloak_category':len(items),'eligibility_note':'base-mask human/fighter flags only; alignment, kit, stat, plot and slot restrictions deliberately not inferred. World assets additionally filter ITM category appropriate to layer. 1px-frame count is a cost heuristic, not a deletion authorization.','assets':details}
(OUT/'assets_inventory.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in summary.items() if k!='assets'},ensure_ascii=False,indent=2))
