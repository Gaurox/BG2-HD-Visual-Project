"""Read-only native references and blend API inspection; never executes game code."""
from pathlib import Path
import bisect
import json
import re
import struct
import sys
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path

OUT=Path(__file__).parent
raw=(get_path('bg2ee_game_root',required=True)/'BaldurReal.exe').read_bytes()
pe=struct.unpack_from('<I',raw,0x3c)[0]
count,optional=struct.unpack_from('<H',raw,pe+6)[0],struct.unpack_from('<H',raw,pe+20)[0]
base=struct.unpack_from('<Q',raw,pe+48)[0]
sections=[struct.unpack_from('<8sIIII',raw,pe+24+optional+i*40) for i in range(count)]
cs=Cs(CS_ARCH_X86,CS_MODE_64)


def offset(rva):
    s=next(s for s in sections if s[2]<=rva<s[2]+s[3]);return s[4]+rva-s[2]


def rva_of(pos):
    s=next(s for s in sections if s[4]<=pos<s[4]+s[3]);return s[2]+pos-s[4]


pdata=next(s for s in sections if s[0].rstrip(b'\0')==b'.pdata')
funcs=[struct.unpack_from('<III',raw,i)[:2] for i in range(pdata[4],pdata[4]+pdata[3]-11,12)]
funcs=sorted((b,e) for b,e in funcs if b and b<e);starts=[b for b,e in funcs]


def function(addr):
    i=bisect.bisect_right(starts,addr)-1
    return funcs[i] if i>=0 and funcs[i][0]<=addr<funcs[i][1] else None


def dump(b,e,label):
    path=OUT/(label+f'-{b:08X}.asm')
    path.write_text('\n'.join(f'{i.address-base:08X} {i.mnemonic:8} {i.op_str}' for i in cs.disasm(raw[offset(b):offset(b)+e-b],base+b))+'\n',encoding='utf-8')
    return path.name


def main():
    batch=json.loads((ROOT/'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1/batch.json').read_text())
    targets={}
    for a in batch['assets']:
        for n in [a['resref']]+a['reuse_aliases']:
            for m in re.finditer(rb'(?<![A-Z0-9_])'+n.encode()+rb'\0',raw.upper()):targets[rva_of(m.start())]=n
    text=next(s for s in sections if s[0].rstrip(b'\0')==b'.text')
    code=raw[text[4]:text[4]+text[3]]
    references=[];dumped={}
    for m in re.finditer(rb'[\x48-\x4f][\x8d\x8b][\x05\x0d\x15\x1d\x25\x2d\x35\x3d]',code):
        p=m.start();addr=text[2]+p;target=addr+7+struct.unpack_from('<i',code,p+3)[0]
        if target not in targets:continue
        f=function(addr)
        if f and f not in dumped:dumped[f]=dump(*f,'reference')
        ins=next(cs.disasm(code[p:p+7],base+addr))
        references.append({'resref':targets[target],'instruction':hex(addr),'operation':ins.mnemonic+' '+ins.op_str,
            'literal_rva':hex(target),'function':[hex(v) for v in f] if f else None,'dump':dumped.get(f)})
    # Enumerate imported blend APIs and their native call sites.
    imp_rva=struct.unpack_from('<I',raw,pe+24+112+8)[0];p=offset(imp_rva);imports={}
    while True:
        oft,stamp,chain,name,iat=struct.unpack_from('<IIIII',raw,p);p+=20
        if not any((oft,name,iat)):break
        dll=raw[offset(name):].split(b'\0',1)[0].decode(errors='replace')
        thunk=offset(oft or iat);i=0
        while True:
            val=struct.unpack_from('<Q',raw,thunk+i*8)[0]
            if not val:break
            if not(val>>63):
                n=raw[offset(val)+2:].split(b'\0',1)[0].decode(errors='replace')
                if 'blend' in n.lower():imports[iat+i*8]={'dll':dll,'name':n}
            i+=1
    calls=[]
    for m in re.finditer(b'\xff\x15',code):
        p=m.start();addr=text[2]+p;target=addr+6+struct.unpack_from('<i',code,p+2)[0]
        if target in imports:
            f=function(addr)
            if f and f not in dumped:dumped[f]=dump(*f,'blend')
            calls.append({'call':hex(addr),'api':imports[target],'function':[hex(v) for v in f] if f else None,'dump':dumped.get(f)})
    (OUT/'native-references.json').write_text(json.dumps({'references':references,'blend_imports':{hex(k):v for k,v in imports.items()},'blend_calls':calls},indent=2)+'\n',encoding='utf-8')
    print('References',len(references),'native functions',len(dumped),'blend calls',len(calls))
    for f in sorted(set(r['dump'] for r in references if r['dump'])):print(f,','.join(r['resref'] for r in references if r['dump']==f))
    print('blend',calls)


if __name__=='__main__':main()
