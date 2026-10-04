"""Trace factory constructor call sites and native weapon string naming from pinned PE."""
import sys,json,struct,subprocess,re,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_oracle import pe_rva,EXE_SHA256
from palette_work_plan import write_json
exe=get_path('bg2ee_game_root',required=True)/'BaldurReal.exe';raw=exe.read_bytes();assert hashlib.sha256(raw).hexdigest()==EXE_SHA256
pe=struct.unpack_from('<I',raw,0x3c)[0];nc=struct.unpack_from('<H',raw,pe+6)[0];opt=struct.unpack_from('<H',raw,pe+20)[0];sections=pe+24+opt;sites=[]
for n in range(nc):
    p=sections+n*40;name=raw[p:p+8].rstrip(b'\0')
    if name!=b'.text':continue
    size,rva,rawsize,offset=struct.unpack_from('<4I',raw,p+8);text=raw[offset:offset+rawsize]
    for i in range(len(text)-5):
        if text[i]!=0xe8:continue
        target=rva+i+5+struct.unpack_from('<i',text,i+1)[0]
        if target in (0x311300,0x3119a0):sites.append(dict(call_rva=hex(rva+i),constructor_rva=hex(target)))
dump='C:/Program Files (x86)/Microsoft Visual Studio/2019/BuildTools/VC/Tools/MSVC/14.29.30133/bin/Hostx64/x64/dumpbin.exe'
for s in sites:
    r=int(s['call_rva'],16);out=subprocess.check_output([dump,'/disasm:nobytes',f'/range:{0x140000000+r-100:#x},{0x140000000+r+40:#x}',str(exe)],text=True)
    (HERE/f'factory-{r:x}.asm').write_text(out,encoding='utf-8')
factory=subprocess.check_output([dump,'/disasm:nobytes','/range:0x140330D70,0x1403313B0',str(exe)],text=True)
(HERE/'factory-native.asm').write_text(factory,encoding='utf-8')
assert all(s in factory for s in ('140330DD4: cmp         eax,2000h','140330E03: call        00000001403119A0','14033122B: cmp         eax,8000h','140331230: je          00000001403312A6','1403312CA: call        0000000140311300'))
prefix=pe_rva(raw,0x32f3b0,32).hex(' ').upper();manifest=(ROOT/'sprite/.work'/HERE.name/'runtime-src/src/iee/game/build_manifest.cpp').read_text()
assert f'0x32f3b0, 0x5aa840, 8, 0, 0, true, "{prefix}"' in manifest
assert '0x32ee90, 0x5aa650, 8, 0, 0, true' in manifest
weapon=(HERE/'weapon-bindings.asm').read_text(encoding='utf-8-sig')
assert all(s in weapon for s in ('14032617D: call        00000001403FE840','140326190: call        00000001403FD8E0','1405AB498','1405ABA80','1405AB5A8','1405ABAEC'))
write_json(HERE/'native-routes.json',dict(exe_sha256=EXE_SHA256,factory_call_sites=sites,proposal_constructor_association_corrected=True,verified_render_hooks=[dict(animation_type='8000',animation_ids=['0x8000','0x8100','0x8200'],constructor='0x311300',render='0x32ee90',vtable='0x5aa650',owner=8,already_installed=True),dict(animation_type='2000',animation_ids=['0x2000','0x2100','0x2200','0x2300'],constructor='0x3119a0',render='0x32f3b0',vtable='0x5aa840',owner=8,new=True)],additional_prefix_32_bytes=prefix,weapon_naming='prefix + first character of allowed weapon resref + G1/G2/G1E/G2E',excluded_orphan=dict(resref='MSIRG2BE',expected_native_ref='MSIRBG2E',zero_height_frames=30,source_bytes_modified=False),native_palette_default='311300 always assigns native range palette to both body and weapon cells; 3119a0 false_color1738 defaults1, fixed Volo/MDKN explicit0',game_executed=False))
print(json.dumps(sites))
