"""Emulate the game's own x64 normalization instructions; no game/process control."""
import hashlib,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
sys.path.insert(0,str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1'))
from unicorn import Uc,UC_ARCH_X86,UC_MODE_64
from unicorn.x86_const import UC_X86_REG_RDI,UC_X86_REG_R11,UC_X86_REG_R10D,UC_X86_REG_EDX,UC_X86_REG_EBX,UC_X86_REG_ECX,UC_X86_REG_R8D

def verify_native():
    raw=(get_path('bg2ee_game_root',required=True)/'BaldurReal.exe').read_bytes()
    sha=hashlib.sha256(raw).hexdigest()
    assert sha=='b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57'
    pe=struct.unpack_from('<I',raw,0x3c)[0];n=struct.unpack_from('<H',raw,pe+6)[0];opt=struct.unpack_from('<H',raw,pe+20)[0]
    def code(rva,size):
        for i in range(n):
            vsize,base,rsize,off=struct.unpack_from('<4I',raw,pe+24+opt+i*40+8)
            if base<=rva<base+max(vsize,rsize):return raw[off+rva-base:off+rva-base+size]
        raise ValueError(rva)
    uc=Uc(UC_ARCH_X86,UC_MODE_64);nativeBase=0x140411000
    uc.mem_map(nativeBase,0x1000);uc.mem_write(nativeBase,code(0x411000,0x1000))
    uc.mem_map(0x100000,0x3000)
    cell,res,table=0x100000,0x101000,0x102000
    uc.mem_write(res+0x88,struct.pack('<Q',table))
    cases=0
    for count in (1,2,8,14,18,36,255):
        uc.mem_write(table,struct.pack('<HH',count,0))
        for mode in (0,1,-1):
            uc.mem_write(cell+0x11c,struct.pack('<i',mode))
            for slot in (0,1,count-1,count,count+1,2*count+1,-1,-count,-count-1,32767,-32768):
                for reg,value in ((UC_X86_REG_RDI,cell),(UC_X86_REG_R11,res),(UC_X86_REG_R10D,0),(UC_X86_REG_ECX,0),(UC_X86_REG_EDX,slot&0xffff),(UC_X86_REG_EBX,0)):
                    uc.reg_write(reg,value)
                uc.emu_start(0x1404117f8,0x140411863,count=128)
                native=uc.reg_read(UC_X86_REG_R8D)
                expected=slot%count if mode else max(0,min(count-1,slot))
                assert native==expected,(count,slot,mode,native,expected)
                cases+=1
    return dict(passed=True,native_instruction_cases=cases,exe_sha256=sha,
                native_rva_start='0x4117F8',native_rva_end='0x411863',playback_field='CVidCell+0x11C',no_game_launched=True)
if __name__=='__main__':
    import json
    print(json.dumps(verify_native()))
