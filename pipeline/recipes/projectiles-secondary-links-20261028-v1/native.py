from pathlib import Path
import struct,sys
sys.path.insert(0,str(Path.cwd()/'pipeline/scripts'))
from workspace_paths import get_path
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
class PE:
 def __init__(self):
  self.data=(get_path('bg2ee_game_root',required=True)/'BaldurReal.exe').read_bytes();b=self.data;p=struct.unpack_from('<I',b,60)[0];n=struct.unpack_from('<H',b,p+6)[0];sz=struct.unpack_from('<H',b,p+20)[0];self.sections=[]
  for i in range(n):
   o=p+24+sz+40*i;vsz,va,rs,raw=struct.unpack_from('<IIII',b,o+8);self.sections.append((va,raw,rs))
  r,s=struct.unpack_from('<II',b,p+24+112+24);pos=self.off(r);self.funcs=[struct.unpack_from('<III',b,o)[:2] for o in range(pos,pos+s,12)];self.md=Cs(CS_ARCH_X86,CS_MODE_64);self.md.skipdata=True
 def off(self,r):
  for v,p,s in self.sections:
   if v<=r<v+s:return r-v+p
 def at(self,r,n):return self.data[self.off(r):self.off(r)+n]
 def instructions(self,start,end):return self.md.disasm(self.at(start,end-start),start)
 def dump(self,start,end):
  lines=[]
  for a in self.instructions(start,end):
   line=f'{a.address:x}: {a.mnemonic} {a.op_str}'
   if 'rip +' in a.op_str:
    try:
     d=int(a.op_str.split('rip + ')[1].split(']')[0],16);p=self.off(a.address+a.size+d)
     if p is not None:line+=' ; '+repr(self.data[p:p+35].split(b'\0')[0])
    except:pass
   lines.append(line)
  return '\n'.join(lines)
if __name__=='__main__':
 p=PE()
 for start,end in p.funcs:
  if not 0x30a000<=start<=0x30d000:continue
  calls=[i for i in p.instructions(start,end) if i.mnemonic=='call' and i.op_str in ['0x29df60','0x424780','0x42b350']]
  if calls:print(hex(start),hex(end),[(hex(i.address),i.op_str) for i in calls])
