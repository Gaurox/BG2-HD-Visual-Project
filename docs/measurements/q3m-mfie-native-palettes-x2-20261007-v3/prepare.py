"""Pin actual MFIE palette, native G1/G2 selection and missing cache work."""
import hashlib,json,re,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path[:0]=[str(ROOT/'pipeline/scripts'),str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1')]
from workspace_paths import get_path
from palette_work_plan import write_json,file_sha
from palette_oracle import pe_rva
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from q3m_family_witnesses import source_plan
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(HERE/'analysis.json').exists()
game=get_path('bg2ee_game_root',required=True);gen=load(HERE.parent/'q3m-mfie-palette-stability-x2-20261007-v2/current-generation.json')
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
rawlog=(game/'InfinityEngine-Enhancer.log').read_bytes();lines=rawlog.decode('utf-8-sig').splitlines()
start=max(i for i,s in enumerate(lines) if 'Infinity Engine Enhancer initializing' in s);session=lines[start:]
(WORK/'last-session.log').write_text('\n'.join(session)+'\n',encoding='utf-8',newline='\n')
evidence=[s for s in session if 'MFIE' in s or '0x7314' in s or 'initializing' in s]
(HERE/'session-evidence.txt').write_text('\n'.join(evidence)+'\n',encoding='utf-8',newline='\n')
line=next(s for s in session if 'MFIE_PALETTE ' in s);live=np.array([int(v,16) for v in re.findall('.{8}',line.split(' colors=')[1])],dtype='<u4')
assert live.size==256 and 'entries=253 accepted=false' in line
index=registry.KeyIndex(game);entries=index.resource_map(1);palettes={};comparisons=[]
for ref in ('MFIEG31','MFIEG3B'):
    bmp,source=index.resolve(entries[ref]);count=struct.unpack_from('<I',bmp,46)[0] or 256
    palette=np.frombuffer(bmp[54:54+count*4],'<u4');diff=np.flatnonzero((live[:count]&0xffffff)!=(palette&0xffffff))
    palettes[ref]=dict(resref=ref,sha256=hashlib.sha256(bmp).hexdigest())
    comparisons.append(dict(resref=ref,source_BIF=source,entries=count,RGB_mismatches=len(diff),exact=(len(diff)==0)))
assert comparisons[0]['exact'] and comparisons[0]['entries']==253 and comparisons[1]['RGB_mismatches']==209
exe=(game/'BaldurReal.exe').read_bytes();assert hashlib.sha256(exe).hexdigest()=='b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57'
md=Cs(CS_ARCH_X86,CS_MODE_64)
blocks=[(0x3390A2,0xDE),(0x3398D8,0xFE),(0x32DA8F,0x48)]
disassembly='\n\n'.join('\n'.join(f'{a-0x140000000:08X} {m} {o}' for a,z,m,o in md.disasm_lite(pe_rva(exe,base,size),0x140000000+base)) for base,size in blocks)
(HERE/'native-bank-selection.txt').write_text(disassembly+'\n',encoding='utf-8',newline='\n')
g2=pe_rva(exe,0x3390B7+0x2729C9,16).split(b'\0')[0].decode();g1=pe_rva(exe,0x3398ED+0x271BAB,16).split(b'\0')[0].decode()
assert 'G2' in g2 and 'G1' in g1,(g1,g2)
selection=load(HERE.parent/'q3m-monster-full-x2-20261006-v2/selection.json')
selection['witnesses']=[w for w in selection['witnesses'] if w['animation_id']=='0x7314'];w=selection['witnesses'][0]
w.pop('palette_override');w['palette_overrides_by_bank']={'1':palettes['MFIEG31'],'2':palettes['MFIEG3B']}
selection['scope']='single-ID native palette bank correction; not complete-family production'
write_json(HERE/'selection.json',selection)
resources,works,plan=source_plan(HERE/'selection.json','monster',animation_ids=['0x7314']);assert len(resources)==14
cache=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';namespace=file_sha(ROOT/'pipeline/scripts/palette_q3m_partners.py')
hits=sum((cache/'encoded'/namespace/(key+'.npz')).exists() for key in works)
write_json(HERE/'plan.json',dict(**plan,scope='single-ID',compatible_encoded_hits=hits,missing_encoded=len(works)-hits))
write_json(HERE/'analysis.json',dict(passed=True,session_begin=session[0][:25],log_sha256=hashlib.sha256(rawlog).hexdigest(),installed_generation=gen,
    actual_palette=dict(kind=0,entries=253,matched_resref='MFIEG31',exact_RGB_prefix=True),comparisons=comparisons,
    native_banks=dict(G1='palette1/MFIEG31/253',G2='palette2/MFIEG3B/252',native_format_strings=[g1,g2],
        G1_selection_rva='0x3399A8',G2_selection_rva='0x339176',bitmap_bind_rva='0x3399BC',render_palette_rva='0x32DA8F'),
    correction_scope=['0x7314'],other_ids_unchanged=330,QA_accepted_ids_preserved=76,release=False))
print(json.dumps(dict(prepared=True,resources=len(resources),frames=plan['physical_frames'],encoded_work=len(works),hits=hits,missing=len(works)-hits,G1=g1,G2=g2)),flush=True)
