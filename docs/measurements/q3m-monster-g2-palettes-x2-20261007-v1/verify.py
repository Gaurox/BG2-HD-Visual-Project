"""Check both corrected banks against native DLL, cycles, K6 pixels; DLL unchanged."""
import csv,json,runpy,struct,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;WORK=ROOT/'sprite/.work'/HERE.name
PARENT=HERE.parent/'q3m-mfie-native-palettes-x2-20261007-v3';AUDIT=HERE.parent/'q3m-monster-final-checks-x2-20261007-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
import run_creature_sprite_x2 as registry
import palette_partner_registry as leaves
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert not(HERE/'verification.json').exists()
gen=load(HERE/'current-generation.json');prod=load(HERE/'production.json');assets=ROOT/gen['generation_dir']/'iee-assets/creature-sprites'
cat=registry.read_sealed_catalog_index(assets/'CreatureSprites-XN.catalog',gen['catalog']['sha256'])
game=get_path('bg2ee_game_root',required=True);idx=registry.KeyIndex(game);bmps=idx.resource_map(1);bams=idx.resource_map(1000)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
native={r['animation_id']:r for r in csv.DictReader((ROOT/'sprite/index/sprite_animations.csv').open(encoding='utf-8-sig'))}
routes=[r for r in cat['directory'] if r['animation_id'] in gen['correction_animation_ids']];assert len(routes)==27
world=0;oracle=WORK/'native-banks.oracle'
with oracle.open('wb') as out:
    out.write(struct.pack('<8sI',b'IEEBANK1',len(routes)))
    for r in routes:
        aid=r['animation_id'];ref=r['resref'];info=leaves.inspect(assets/Path(cat['shards'][r['shard_index']]['registry']).name,include_frames=True)
        res=info['resources'][r['resource_ordinal']]
        raw,_=idx.resolve(bams[ref]);bam,_=registry.canonical_bam(raw);cycles=[c['frame_indices'] for c in registry.bam_cycles(bam)]
        assert cycles==res['cycles'] and res['source_sha256']==__import__('hashlib').sha256(bam).hexdigest()
        ini=json.loads(native[aid]['ini_sections_json']);palettes=[]
        for bank in '12':
            raw,_=idx.resolve(bmps[ini['monster']['palette'+bank]]);assert (struct.unpack_from('<I',raw,46)[0] or 256)==256
            palettes.append(raw[54:54+1024])
        if not ref.endswith('INV'):
            assert res['profile'].source.tobytes()==palettes[int(ref[5])-1];world+=res['frame_count']
        out.write(struct.pack('<I8sII',int(aid,16),ref.encode().ljust(8,b'\0'),res['frame_count'],len(cycles))+b''.join(palettes))
        for cycle in cycles:out.write(struct.pack('<I',len(cycle))+struct.pack(f'<{len(cycle)}I',*cycle))
assert world==11772
source=(AUDIT/'check_banks.cpp').read_text(encoding='utf-8')
old='g1==g1Accepted&&g2>0&&g2Accepted==0&&g2G1Accepted==g2'
new='g1==g1Accepted&&g2>0&&g2Accepted==g2&&g2G1Accepted==0'
assert old in source and 'G2_defect_confirmed\\\":true' in source
source=source.replace(old,new).replace('G2_defect_confirmed\\\":true','G2_defect_confirmed\\\":false,\\\"native_palettes_correct\\\":true')
(HERE/'palette_probe.cpp').write_text(source,encoding='utf-8',newline='\n')
ns=runpy.run_path(str(PARENT/'verify.py'));ns['compile_probe'].__globals__.update(HERE=HERE,WORK=WORK)
exe=ns['compile_probe']('G2-native-palettes',HERE/'palette_probe.cpp')
with(HERE/'native-palettes.log').open('w',encoding='utf-8') as out:subprocess.run([str(exe),str(assets),str(oracle)],stdout=out,stderr=subprocess.STDOUT,check=True)
guard=json.loads((HERE/'native-palettes.log').read_text().splitlines()[-1]);assert guard['native_palettes_correct'] and not guard['G2_defect_confirmed']
print(json.dumps(dict(stage='native-palette-cycles',**guard)),flush=True)
pixel_exe=ROOT/'sprite/.work'/PARENT.name/'runtime-build/Release/iee_palette_partner_tests.exe'
with(HERE/'native-pixels.log').open('w',encoding='utf-8') as out:subprocess.run([str(pixel_exe),str(assets),str(ROOT/prod['pack_directory']/'witnesses.oracle')],stdout=out,stderr=subprocess.STDOUT,check=True)
pixel=json.loads((HERE/'native-pixels.log').read_text().splitlines()[-1]);assert pixel['passed'] and pixel['resources']==27 and pixel['frames']==11774
assert file_sha(game/'InfinityEngine-Enhancer.dll')==gen['dll']['sha256']
write_json(HERE/'verification.json',dict(passed=True,native_palette_guards=guard,native_pixels=pixel,world_frames_exact_native_palette=world,
    retained_catalog_proof=load(HERE/'catalog-proof.json'),runtime_changed=False,dll_sha256=gen['dll']['sha256'],catalog_sha256=gen['catalog']['sha256'],
    prior_defect_G2_palette_acceptance='0/5292',corrected_G2_palette_acceptance='5292/5292',installation=False,ingame_QA=False,release=False))
print(json.dumps(dict(stage='native-pixels',**pixel)),flush=True)
