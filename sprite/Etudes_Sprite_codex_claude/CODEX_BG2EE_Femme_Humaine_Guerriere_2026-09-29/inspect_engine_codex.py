"""Independent read-only palette inspection; never execute or patch game binary."""
from pathlib import Path
import sys, hashlib, json, re, struct
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'research_deps'))
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

GAME = Path("G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition")
EXE = GAME / 'BaldurReal.exe'
data = EXE.read_bytes()
pe = pefile.PE(data=data)
base = pe.OPTIONAL_HEADER.ImageBase
dis = Cs(CS_ARCH_X86, CS_MODE_64)
dis.detail = True
result = [f'EXE={EXE}', f'SHA256={hashlib.sha256(data).hexdigest()}', f'ImageBase=0x{base:x}']
for v in pe.VS_FIXEDFILEINFO:
    result.append(f'FileVersion={v.FileVersionMS >> 16}.{v.FileVersionMS & 65535}.{v.FileVersionLS >> 16}.{v.FileVersionLS & 65535}')

for rva, length, name in [(0x421da0, 0x440, 'RealizeRange'), (0x4221c0, 0x200, 'SetRange')]:
    result.append(f'\n=== {name} RVA=0x{rva:x} length={length:x} ===')
    for ins in dis.disasm(pe.get_data(rva, length), base + rva):
        result.append(f'{ins.address-base:08x}: {ins.mnemonic:9s} {ins.op_str}')

targets = {}
for term in [b'RANGES12', b'MPALETTE', b'MPAL256', b'CLRGRAD', b'CLOWNCLR']:
    offsets = []
    start = 0
    while True:
        offset = data.upper().find(term, start)
        if offset < 0: break
        offsets.append({'file_offset': hex(offset), 'rva': hex(pe.get_rva_from_offset(offset))})
        targets[pe.get_rva_from_offset(offset)] = term.decode()
        start = offset+1
    result.append(f'\nSTRING {term.decode()}: {offsets}')

extra = []
callers=[]
for sec in pe.sections:
    if not sec.Characteristics & 0x20000000: continue
    raw = sec.get_data()
    for match in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d]....', raw, re.DOTALL):
        instr = sec.VirtualAddress + match.start()
        target = instr+7+struct.unpack('<i', match.group()[3:])[0]
        if target in targets:
            result.append(f'XREF {targets[target]} RVA=0x{instr:x}')
            extra.append((max(0,instr-50), 220, targets[target]+' xref context'))
    for match in re.finditer(rb'\xe8....', raw, re.DOTALL):
        instr=sec.VirtualAddress+match.start()
        target=instr+5+struct.unpack('<i',match.group()[1:])[0]
        if target==0x4221c0:
            callers.append(instr)
result.append('SetRange callers RVAs='+','.join(hex(x) for x in callers))
for rva in callers[:8]:
    extra.append((rva-50, 70, 'SetRange call context'))
for rva,length,name in extra:
    result.append(f'\n=== {name} RVA=0x{rva:x} ===')
    for ins in dis.disasm(pe.get_data(rva, length), base+rva):
        result.append(f'{ins.address-base:08x}: {ins.mnemonic:9s} {ins.op_str}')
text='\n'.join(result)+'\n'
(HERE/'engine_disassembly_codex.txt').write_text(text, encoding='utf-8')
print(text)
