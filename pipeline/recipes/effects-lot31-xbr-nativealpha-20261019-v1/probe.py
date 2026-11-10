"""Read-only native pixel/consumer probe for22/27; no engine execution."""
from common import *
from PIL import Image
import numpy as np
import struct,re,bisect
from workspace_paths import get_path
from bg2lib import load_key,resolve_resource
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

def main():
    report=[]
    for a in jobs():
        if a['ordinal'] not in (22,27):continue
        source=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'00-frames-x1';m=load(source/'manifest.json');black=near=covered=0
        for f in m['frames']:
            rgba=np.array(Image.open(source/'rgba'/f['file']).convert('RGBA'));v=rgba[:,:,3]>0;energy=rgba[:,:,:3].max(2);black+=int((v&(energy==0)).sum());near+=int((v&(energy<=8)).sum());covered+=int(v.sum())
        report.append({'ordinal':a['ordinal'],'resref':a['resref'],'covered_native_pixels':covered,'covered_exact_black':black,'covered_nearblack_le8':near,'source_bam':evidence(ROOT/'effects/ressources'/a['resref']/'source.bam')})
    b,e=load_key();lookup={(n.upper(),t):l for n,t,l in e};data,bif=resolve_resource(b,lookup['OHRSHAD',1006]);pos=0xfa
    owner={'resource':'OHRSHAD.SPL','bif':bif,'sha256':sha(data),'effect_offset':hex(pos),'opcode':struct.unpack_from('<H',data,pos)[0],
        'parameter1':struct.unpack_from('<I',data,pos+4)[0],'parameter2':struct.unpack_from('<I',data,pos+8)[0],'bam':data[pos+20:pos+28].rstrip(b'\0').decode('ascii')}
    exe=get_path('bg2ee_game_root',required=True)/'BaldurReal.exe';raw=exe.read_bytes();pe=struct.unpack_from('<I',raw,0x3c)[0];count=struct.unpack_from('<H',raw,pe+6)[0];optional=struct.unpack_from('<H',raw,pe+20)[0];base=struct.unpack_from('<Q',raw,pe+48)[0]
    sections=[struct.unpack_from('<8sIIII',raw,pe+24+optional+i*40) for i in range(count)]
    def rva(offset):
        return next(va+offset-off for _,_,va,size,off in sections if off<=offset<off+size)
    def read(address,n):
        return next(raw[off+address-va:off+address-va+n] for _,_,va,size,off in sections if va<=address<va+size)
    literal=raw.upper().find(b'SPENTACI\0');target=rva(literal);refs=[]
    pdata=next(s for s in sections if s[0].startswith(b'.pdata'));ranges=[struct.unpack_from('<III',raw,pdata[4]+o)[:2] for o in range(0,pdata[3]-11,12)];ranges.sort();starts=[s for s,e in ranges]
    decoder=Cs(CS_ARCH_X86,CS_MODE_64)
    for _,_,va,size,off in [s for s in sections if s[0].startswith(b'.text')]:
        for match in re.finditer(rb'[\x48\x4c]\x8d[\x05\x0d\x15\x1d\x25\x2d\x35\x3d][\s\S]{4}',raw[off:off+size]):
            ins=va+match.start();disp=struct.unpack('<i',match[0][-4:])[0]
            if ins+7+disp!=target:continue
            start,end=ranges[bisect.bisect_right(starts,ins)-1];refs.append({'xref_rva':hex(ins),'function_start':hex(start),'function_end':hex(end)})
            assembly='\n'.join(f'{i.address-base:08X} {i.mnemonic:8} {i.op_str}' for i in decoder.disasm(read(start,end-start),base+start))+'\n'
            path=OUT/'native'/f'SPENTACI-{start:X}.asm';path.parent.mkdir(parents=True,exist_ok=True);path.write_text(assembly,encoding='utf-8')
    save(OUT/'native/probe.json',{'pixels':report,'opcode215':owner,'executable':{'path':'config://bg2ee_game_root/BaldurReal.exe','sha256':sha(raw)},'spentaci_literal_offset':hex(literal),'spentaci_literal_rva':hex(target),'spentaci_xrefs':refs,
        'iesdp':{'215':'https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op215','154':'https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op154'},'static_reference_is_not_runtime_blend_measurement':True})
    print(report,refs,flush=True)

if __name__=='__main__':main()
