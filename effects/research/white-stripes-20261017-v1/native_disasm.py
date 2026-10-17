"""Read-only disassembly of the exact game PE, never executes game code."""
from pathlib import Path
import sys,struct,hashlib,json
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
GAME=get_path('bg2ee_game_root',required=True)
raw=(GAME/'BaldurReal.exe').read_bytes();pe=struct.unpack_from('<I',raw,0x3c)[0]
count=struct.unpack_from('<H',raw,pe+6)[0];optional=struct.unpack_from('<H',raw,pe+20)[0]
base=struct.unpack_from('<Q',raw,pe+24+24)[0]
sections=[struct.unpack_from('<8sIIII',raw,pe+24+optional+i*40) for i in range(count)]
def read(rva,n):
 for _,_,va,size,off in sections:
  if va<=rva and rva+n<=va+size:return raw[off+rva-va:off+rva-va+n]
 raise ValueError(hex(rva))
pdata=next(s for s in sections if s[0].startswith(b'.pdata'))
ranges=[struct.unpack_from('<III',raw,pdata[4]+o)[:2] for o in range(0,pdata[3]-11,12)]
decoder=Cs(CS_ARCH_X86,CS_MODE_64)
def disassemble(name,rva,n=None):
 if n is None:
  rr=next(((s,e) for s,e in ranges if s==rva),None)
  n=rr[1]-rva if rr else 256
 text='\n'.join(f'{i.address-base:08X}  {i.mnemonic:8} {i.op_str}' for i in decoder.disasm(read(rva,n),base+rva))+'\n'
 (Path(__file__).parent/(name+'.asm')).write_text(text,encoding='utf-8')
 return text
targets={'DrawFlushGL':0x42B350,'TexImage':0x4135E0,'DrawGenTexture':0x413270}
targets.update(DrawBindTextureGL=0x42A840,DrawPushStateGL=0x42CDE0,
 DrawPopStateGL=0x42CDB0,TexImageGL=0x42D030)
for name,offset in [('DrawBindTexture',0x6E),('DrawPushState',0x91),('DrawPopState',0x1AD),('DrawBegin',0xC0),('DrawEnd',0x17A)]:
 rva=0x4257C0+offset;disp=struct.unpack('<i',read(rva+1,4))[0];targets[name]=rva+5+disp
for name,rva in targets.items():
 text=disassemble(name,rva,0x8D0 if name=='DrawFlushGL' else None); print(name,hex(rva),len(text.splitlines()),'instructions')
disassemble('RenderTexture',0x4257C0)
identity={'executable_sha256':hashlib.sha256(raw).hexdigest().upper(),
 'dll_sha256':hashlib.sha256((GAME/'InfinityEngine-Enhancer.dll').read_bytes()).hexdigest().upper(),
 'rvas':{k:hex(v) for k,v in targets.items()},'game_executed':False}
(Path(__file__).parent/'native-identity.json').write_text(json.dumps(identity,indent=2)+'\n',encoding='utf-8')
