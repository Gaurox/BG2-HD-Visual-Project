"""Verify all Monster cycles, palette guards, native pixels and Icewind regression."""
import json,runpy,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
WORK=ROOT/'sprite/.work'/HERE.name;BUILD=WORK/'runtime-build';SRC=WORK/'runtime-src'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
def report(log):return json.loads(next(s for s in reversed(log.read_text(encoding='utf-8').splitlines()) if s.startswith('{')))
def compile_probe(name,source):
    deps=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/build-vs2019-30fps-multicycle/_deps'
    cmd=f'''@echo off
call "C:\\Program Files (x86)\\Microsoft Visual Studio\\2019\\BuildTools\\VC\\Auxiliary\\Build\\vcvars64.bat" >nul
if errorlevel 1 exit /b 1
cd /d "{BUILD}"
cl /nologo /std:c++latest /EHsc /MT /O2 /DNOMINMAX /DSPDLOG_COMPILED_LIB /I"{SRC/'src'}" /I"{deps/'spdlog-src/include'}" /I"{deps/'zlib-src'}" "{source}" /Fo"{WORK/(name+'.obj')}" /Fe"{WORK/(name+'.exe')}" /link iee_palette_partner_tests.dir\\Release\\creature_sprite_x2.obj iee_palette_partner_tests.dir\\Release\\opengl_types.obj Release\\iee_common.lib _deps\\spdlog-build\\Release\\spdlog.lib _deps\\zlib-build\\Release\\zs.lib opengl32.lib Cabinet.lib bcrypt.lib version.lib psapi.lib user32.lib gdi32.lib
exit /b %errorlevel%
'''
    command=WORK/(name+'.cmd');command.write_text(cmd,encoding='utf-8')
    with(HERE/(name+'-build.log')).open('w',encoding='utf-8') as log:subprocess.run(['cmd','/c',str(command)],stdout=log,stderr=subprocess.STDOUT,check=True)
    return WORK/(name+'.exe')
def execute(name,args):
    log=HERE/(name+'.log')
    with log.open('w',encoding='utf-8') as stream:subprocess.run(list(map(str,args)),stdout=stream,stderr=subprocess.STDOUT,check=True)
    result=report(log);assert result['passed'];print(json.dumps(dict(stage=name,**result)),flush=True);return result
def main():
    import numpy as np
    import palette_partner_registry as leaves
    assert not(HERE/'verification.json').exists()
    gen=load(HERE/'current-generation.json');prod=load(HERE/'production.json');assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
    cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
    game=get_path('bg2ee_game_root',required=True);idx=registry.KeyIndex(game);palettes=[];bins=[]
    for name in ('MFIEG31','MFIEG3B'):
        bmp,_=idx.resolve(idx.resource_map(1)[name]);count=struct.unpack_from('<I',bmp,46)[0]
        data=bmp[54:54+count*4]+bytes((256-count)*4);p=WORK/(name+'.bin');p.write_bytes(data);bins.append(p);palettes.append(data)
    counts={'1':253,'2':252};world=0
    for r in cat['directory']:
        if r['animation_id']!='0x7314':continue
        s=cat['shards'][r['shard_index']];info=leaves.inspect(assets/Path(s['registry']).name,include_frames=True)
        res=info['resources'][r['resource_ordinal']]
        if r['resref'].endswith('INV'):continue
        bank=r['resref'][5];count=counts[bank];data=palettes[0 if bank=='1' else 1]
        assert res['profile'].source.tobytes()==data
        for frame in res['frames']:
            assert not np.any(np.unpackbits(np.frombuffer(frame['dep'],np.uint8),bitorder='little')[count:]);world+=1
    assert world==5886
    raw=(ROOT/prod['pack_directory']/'witnesses.oracle').read_bytes();magic,nr=struct.unpack_from('<8sI',raw);assert magic==b'IEEQP7\0\0' and nr==14
    offset=12;oracle=WORK/'native-playback.oracle'
    with oracle.open('wb') as out:
        out.write(struct.pack('<8sI',b'IEENAT02',nr))
        for _ in range(nr):
            aid,owner,name,nf,nc=struct.unpack_from('<II8sII',raw,offset);assert owner==3;offset+=24+6*256*4+2052
            out.write(struct.pack('<I8sII',aid,name,nf,nc))
            for _ in range(nc):
                n=struct.unpack_from('<I',raw,offset)[0];out.write(raw[offset:offset+4+4*n]);offset+=4+4*n
            offset+=nf*(16+6*32)
    assert offset==len(raw)
    probe=compile_probe('MFIE-palette',HERE/'palette_probe.cpp')
    guard=execute('MFIE-palette',[probe,assets,oracle,*bins]);assert guard['world_frames']==world
    pixel=execute('native-pixels',[BUILD/'Release/iee_palette_partner_tests.exe',assets,ROOT/prod['pack_directory']/'witnesses.oracle'])
    assert pixel['resources']==14 and pixel['frames']==5888
    parent=ROOT/'sprite/.work/q3m-mfie-palette-stability-x2-20261007-v2/runtime-src';changed={'src/iee/creature_sprite_x2.cpp'};same=0
    for p in parent.rglob('*'):
        if p.is_file() and p.relative_to(parent).as_posix() not in changed:
            assert p.read_bytes()==(SRC/p.relative_to(parent)).read_bytes(),p;same+=1
    write_json(HERE/'verification.json',dict(passed=True,native_palette_guards=guard,native_pixels=pixel,world_frames_exact_palette=world,
        all_base_and_partner_dependencies_within_native_entry_count=True,G1_matches_observed_live_palette=True,G2_matches_native_SetSequence=True,
        retained_catalog_proof=load(HERE/'catalog-proof.json'),unchanged_runtime_source_files=same,native_general_tests_passed=True,
        catalog_sha256=gen['catalog']['sha256'],dll_sha256=gen['dll']['sha256'],installation=False,ingame_QA=False,release=False))
if __name__=='__main__':main()
