"""Pin latest-session sprite diagnostics and inspect the short Burning Man palette."""
import hashlib,json,re,runpy,struct,sys
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(ROOT/'sprite/.work/q3m-runtime-tools-20261003-v1'))
from palette_work_plan import write_json,file_sha
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
from palette_q3m_partners import Profile
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(HERE/'analysis.json').exists()
game=get_path('bg2ee_game_root',required=True);WORK.mkdir(parents=True,exist_ok=True)
rawlog=(game/'InfinityEngine-Enhancer.log').read_bytes();lines=rawlog.decode('utf-8-sig').splitlines()
start=max(i for i,s in enumerate(lines) if 'Infinity Engine Enhancer initializing' in s);session=lines[start:]
(WORK/'last-session.log').write_text('\n'.join(session)+'\n',encoding='utf-8',newline='\n')
sprite=[s for s in session if 'creature' in s.lower() or 'q3m' in s.lower()]
evidence=[s for s in sprite if '[warning]' in s or '[error]' in s or 'catalog ready' in s or any(a in s for a in ('0x7314','0x7F0B','0x7F2C','0x7F36'))]
(HERE/'last-session-sprite-evidence.txt').write_text('\n'.join(evidence)+'\n',encoding='utf-8',newline='\n')
gen=load(HERE.parent/'q3m-monster-ingame-x2-20261007-v1/current-generation.json')
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==gen['catalog']['sha256']
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
original=load(HERE.parent/'q3m-monster-full-x2-20261006-v2/current-generation.json')
oracle=(ROOT/original['generation_dir']/'witnesses.oracle').read_bytes()
magic,n=struct.unpack_from('<8sI',oracle);assert magic==b'IEEQP7\0\0' and n==1040
offset=12;used=set();frames=0;resources=0;palette=None;playback=WORK/'native-playback.oracle'
with playback.open('wb') as out:
    out.write(struct.pack('<8sI',b'IEENAT02',n))
    for _ in range(n):
        aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',oracle,offset);offset+=24+6*256*4
        metadata=oracle[offset:offset+2052];offset+=2052
        out.write(struct.pack('<I8sII',aid,ref,nf,nc))
        for _ in range(nc):
            slots=struct.unpack_from('<I',oracle,offset)[0];out.write(oracle[offset:offset+4+4*slots]);offset+=4+4*slots
        if aid==0x7314 and not ref.rstrip(b'\0').endswith(b'INV'):
            resources+=1;frames+=nf
            current=np.frombuffer(metadata[4:1028],'<u4').copy()
            if palette is None:palette=current
            assert np.array_equal(palette,current)
        offset+=nf*(16+6*32)
assert offset==len(oracle)
assert palette is not None
index=registry.KeyIndex(game);bmp,source=index.resolve(index.resource_map(1)['MFIEG3B'])
entries=struct.unpack_from('<I',bmp,46)[0];assert entries==252
native=np.frombuffer(bmp[54:54+entries*4],'<u4')
assert np.array_equal(palette[:entries],native) and np.all(palette[entries:]==0)
# Native Realize with 252 entries: only its declared prefix is read/written.
NativeFixed=runpy.run_path(str(ROOT/'docs/measurements/q3m-monster-contract-x2-20261002-v1/build_contract.py'))['NativeFixed']
exe=(game/'BaldurReal.exe').read_bytes();native_oracle=NativeFixed(exe);reg=native_oracle.reg;uc=native_oracle.uc
uc.mem_write(0x10004000,bmp[54:54+entries*4]+bytes([0xcd])*16)
uc.mem_write(0x10003000,struct.pack('<QQQI',0,1,0x10004000,entries)+bytes(20))
uc.mem_write(0x10006000,bytes([0xa5])*1024);uc.mem_write(0x10005000,bytes([255,255,255])+bytes(0xcd))
stack=0x1001F000;uc.mem_write(stack,struct.pack('<Q',0x1000F000));uc.mem_write(stack+0x28,struct.pack('<II',255,0))
for name,value in (('RCX',0x10003000),('RDX',0x10006000),('R8',5),('R9',0x10005000),('RSP',stack)):uc.reg_write(getattr(reg,'UC_X86_REG_'+name),value)
uc.emu_start(0x421430,0x1000F000,count=100000)
assert uc.reg_read(reg.UC_X86_REG_RIP)==0x1000F000
output=bytes(uc.mem_read(0x10006000,1024));prefix=np.frombuffer(output[:entries*4],'<u4')
expected=palette.copy();expected|=0xff000000;expected[0]&=0x00ffffff;expected[1]=(expected[1]&0xffffff)|0x7f000000
assert np.array_equal(prefix,expected[:entries])
assert output[entries*4:]==bytes([0xa5])*16
report=dict(passed=True,session_begin=session[0],session_end=session[-1][:25],session_lines=len(session),
    log_sha256=hashlib.sha256(rawlog).hexdigest(),sprite_evidence='last-session-sprite-evidence.txt',
    installed_generation=gen,excluded_QA_ids=['0x7314','0x7F0B','0x7F2C','0x7F36'],other_user_accepted_ids=73,
    observations=dict(burning_man='target Realize=1, captured=0; strict hook requires 256 source entries',
        generic_monster='NonBlocking metadata plus strict slots; first warning MEAEG12 sequence18 slot19',
        click_flashes='later G12->G1 metadata loads; individual fallbacks suppressed by global once-only warning'),
    short_palette=dict(resref='MFIEG3B',source_bif=source,sha256=hashlib.sha256(bmp).hexdigest(),entries=entries,
        source_profile_prefix_exact=True,profile_tail_zero=True,native_Realize_prefix_exact=True,native_Realize_does_not_write_tail=True,
        world_resources=resources,world_frames=frames),
    native_playback_oracle=dict(path=playback.relative_to(ROOT).as_posix(),sha256=file_sha(playback),resources=1040),
    requested_fix_scope='Monster owner3 only; metadata wait/native Loop-Clamp; short 7314 palette prefix reads',release=False)
write_json(HERE/'analysis.json',report)
print(json.dumps(dict(passed=True,session_begin=session[0][:25],entries=entries,burning_man_resources=resources,playback_resources=1040)),flush=True)
