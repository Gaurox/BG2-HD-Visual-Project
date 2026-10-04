"""Pinned executable evidence; no game execution or mutation."""
import sys,subprocess,re,json,hashlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from palette_oracle import pe_rva,EXE_SHA256
from palette_work_plan import write_json
game=get_path('bg2ee_game_root',required=True);exe=game/'BaldurReal.exe';raw=exe.read_bytes()
assert hashlib.sha256(raw).hexdigest()==EXE_SHA256.lower()
dump='C:/Program Files (x86)/Microsoft Visual Studio/2019/BuildTools/VC/Tools/MSVC/14.29.30133/bin/Hostx64/x64/dumpbin.exe'
report={'exe_sha256':EXE_SHA256,'paths':[]}
for name,start,end in [('ctor2000',0x311300,0x3119a0),('ctor8000',0x3119a0,0x312300),('parser8000',0x340610,0x340870),('render2000',0x32ee90,0x32f3b0),('render8000',0x32f3b0,0x32f8d0)]:
    text=subprocess.check_output([dump,'/disasm:nobytes',f'/range:{0x140000000+start:#x},{0x140000000+end:#x}',str(exe)],text=True)
    (HERE/(name+'.asm')).write_text(text,encoding='utf-8')
    strings={}
    for address in re.findall(r'\[([0-9A-F]{16})h?\]',text):
        rva=int(address,16)-0x140000000
        if 0x589000<rva<0x660000:
            b=pe_rva(raw,rva,80).split(b'\0')[0]
            if b and all(32<=x<127 for x in b):strings[hex(rva)]=b.decode()
    report['paths'].append(dict(name=name,strings=strings))
report['hook_prefix_8000']=pe_rva(raw,0x32f3b0,32).hex(' ').upper()
report['vtables']={hex(vt):[hex(p-0x140000000) for p in struct.unpack('<62Q',pe_rva(raw,vt,496))] for vt in (0x5aa650,0x5aa840)}
write_json(HERE/'native-evidence.json',report)
print(json.dumps(report['paths']));print(report['hook_prefix_8000']);print(report['vtables']['0x5aa650'])
