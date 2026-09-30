"""Freeze P2 source/artifact hashes and existing successful checks; no installation."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tarfile

ROOT=next(p for p in Path(__file__).resolve().parents if (p/'pipeline/scripts').is_dir())
OUTPUT=Path(__file__).resolve().parents[1]
RESEARCH=OUTPUT.parent
PRE=RESEARCH/'palette-pre-p2-20260930-v1'
P1=RESEARCH/'palette-q3m-p1-20260930-v1'
P0=RESEARCH/'palette-oracles-p0-20260930-v4'
ENGINE=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
BUILD=ROOT/'build'/OUTPUT.name/'cmake'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_creature_sprite_x2 as registry
from workspace_paths import get_path


def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path,data):
    with Path(path).open('x',encoding='utf-8',newline='\n') as out:out.write(json.dumps(data,indent=2)+'\n')


def inventory():
    files=[ENGINE/'CMakeLists.txt',ENGINE/'assets/water-route2/registry-v2.json',
           ROOT/'pipeline/water/route2-registry-v1.json']
    for directory in ('src','tests','tools'):
        files.extend(p for p in (ENGINE/directory).rglob('*')
                     if p.is_file() and p.suffix in ('.cpp','.c','.h','.hpp','.in','.py'))
    scripts=['palette_registry.py','palette_p2.py','run_creature_sprite_x2.py','reboutcx_catalog.py',
             'palette_frac_encode.py','palette_eval.py','reboutcx_multipal.py','palette_oracle.py',
             'workspace_paths.py','Install-CreatureSprite-XN-Test.ps1']
    files.extend(ROOT/'pipeline/scripts'/name for name in scripts)
    files.extend(ROOT/'pipeline/tests'/name for name in
                 ('test_palette_registry.py','test_creature_sprite_x2_pipeline.py'))
    files.append(ROOT/'pipeline/PALETTE_Q3M_V6.md')
    files.append(Path(__file__))
    return {p.relative_to(ROOT).as_posix():sha(p) for p in sorted(set(files))}


def artifact_hashes():
    return {name:sha(BUILD/'Release'/name) for name in
            ('InfinityEngine-Enhancer.dll','iee_tests.exe','iee_palette_fraction_tests.exe',
             'iee_effect_animation_x4_registry_tests.exe','iee_bridge_worker_tests.exe')}


def json_line(path,field):
    return next(json.loads(line) for line in Path(path).read_text(encoding='utf-8-sig',errors='replace').splitlines()
                if line.startswith('{') and field in json.loads(line))


def finalize():
    assert not (OUTPUT/'verification.json').exists(),'Completed P2 proof is immutable'
    before=read(OUTPUT/'source-before.json')
    current=inventory()
    proof_script=Path(__file__).relative_to(ROOT).as_posix()
    assert {k:v for k,v in current.items() if k!=proof_script}==\
           {k:v for k,v in before['sha256'].items() if k!=proof_script},'Runtime/producer source changed during final build/tests'
    binaries=artifact_hashes()
    assert binaries['iee_palette_fraction_tests.exe']==before['artifacts_sha256']['iee_palette_fraction_tests.exe'],\
           'Pack checks must be rerun with changed native test executable'
    py=(OUTPUT/'python-final.log').read_text(encoding='utf-8-sig')
    match=re.search(r'Ran (\d+) tests',py)
    assert match and int(match[1])==146 and '\nOK' in py and 'FAILED' not in py
    ctest=(OUTPUT/'ctest-final.log').read_text(encoding='utf-8-sig')
    assert '100% tests passed, 0 tests failed out of 4' in ctest
    native=json_line(BUILD/'Testing/Temporary/LastTest.log','accepted')
    assert native['accepted']==8 and native['rejected']==35
    fixture_base=BUILD/'generated/palette-fraction-fixtures'
    fixture=fixture_base/(fixture_base/'ready.txt').read_text().strip()
    fixture_proof=read(fixture/'fixtures.json')
    for name,h in fixture_proof['sha256'].items():assert sha(fixture/name)==h,name
    packs=read(OUTPUT/'packs.json')
    verified_packs=[]
    for pack in packs['packs']:
        label=f"x{pack['scale']}-{pack['method'].lower()}"
        check=json_line(OUTPUT/f'native-{label}.log','pack_frames')
        assert check['pack_frames']==4230 and check['palettes']==18
        assert sha(OUTPUT/pack['decoder_oracle'])==pack['oracle_sha256']
        assets=OUTPUT/pack['assets']
        parsed=registry.inspect_registry_catalog(assets/registry.XN_REGISTRY_CATALOG_FILENAME)
        assert parsed['sha256']==pack['info']['sha256'] and parsed['shard_registry_version']==6
        assert parsed['logical_content_sha256']==pack['info']['logical_content_sha256']
        physical={p.relative_to(OUTPUT).as_posix():sha(p) for p in sorted(assets.iterdir()) if p.is_file()}
        verified_packs.append(dict(label=label,scale=pack['scale'],method=pack['method'],
                                   assets=pack['assets'],decoder_oracle=pack['decoder_oracle'],
                                   oracle_sha256=pack['oracle_sha256'],sha256=physical,
                                   registry_bytes=pack['info']['total_registry_bytes'],
                                   native_check=check,native_log=f'native-{label}.log'))
    assert len(verified_packs)==4
    # Inputs consumed by P2 and all named historical proof files remain identical.
    preserved={}
    for name,h in read(PRE/'inputs.json')['proof_hashes'].items():
        prefix,relative=name.split('/',1);path=(P0 if prefix=='P0' else P1)/relative
        assert sha(path)==h,name;preserved[name]=h
    for name,h in packs['p1_files_sha256'].items():assert sha(P1/name)==h,name
    pre=read(PRE/'verification.json')
    live={}
    for ref,h in pre['live_local_inputs_sha256'].items():
        spec=ref.removeprefix('config://');key,_,tail=spec.partition('/')
        path=get_path(key)/tail if tail else get_path(key)
        assert sha(path)==h,ref;live[ref]=h
    for name,record in read(PRE/'inputs.json')['script_provenance'].items():
        assert sha(ROOT/'pipeline/scripts'/name)==record['p1_sha256'],name
    native_before=read(PRE/'native.json')['source_sha256']
    intended={'CMakeLists.txt','src/iee/creature_sprite_x2.cpp','src/iee/creature_sprite_x2.h'}
    for name,h in native_before.items():
        if name not in intended:assert sha(ENGINE/name)==h,name
    for ref,h in packs['source_sha256'].items():
        source=read(P1/'experiment.json')['sources'][ref]['canonical_bam']
        assert sha(ROOT/source)==h,ref
    dependencies={}
    for name,record in read(PRE/'native.json')['dependencies'].items():
        archive=ROOT/'build'/PRE.name/'dependencies'/f'{name}.tar'
        assert sha(archive)==record['archive_sha256']
        folder=ROOT/'build'/OUTPUT.name/'dependencies'/name
        count=0
        with tarfile.open(archive) as tar:
            for member in tar.getmembers():
                if member.isfile():
                    assert sha(folder/member.name)==hashlib.sha256(tar.extractfile(member).read()).hexdigest()
                    count+=1
        dependencies[name]={**record,'source':str(folder),'verified_archive_files':count}
    candidate=OUTPUT/'candidate';candidate.mkdir()
    dll=candidate/'InfinityEngine-Enhancer.dll';shutil.copy2(BUILD/'Release'/dll.name,dll)
    assert sha(dll)==binaries[dll.name]
    data=dll.read_bytes();pe=struct.unpack_from('<I',data,60)[0]
    assert data[:2]==b'MZ' and data[pe:pe+4]==b'PE\0\0'
    assert struct.unpack_from('<H',data,pe+4)[0]==0x8664 and struct.unpack_from('<H',data,pe+22)[0]&0x2000
    assert struct.unpack_from('<H',data,pe+24)[0]==0x20b
    frozen=[]
    for name,h in current.items():
        if name.startswith('pipeline/') or name.removeprefix(ENGINE.relative_to(ROOT).as_posix()+'/') in intended or\
           name.endswith('/palette_fraction.h') or name.endswith('/palette_fraction_tests.cpp'):
            destination=OUTPUT/'provenance/source'/name;destination.parent.mkdir(parents=True,exist_ok=True)
            assert not destination.exists();shutil.copy2(ROOT/name,destination)
            assert sha(destination)==h;frozen.append(name)
    guide=ROOT/'sprite/Etudes_Sprite_codex_claude/GUIDE_DEFINITIF_SPRITES_HD_BG2EE.md'
    report=dict(schema='bg2-upscale-character-palette-p2-verification-v1',status='passed',
        created_utc=datetime.now(timezone.utc).isoformat(),p2_complete_offgame=True,ready_for_p3_preparation=True,
        p3_started=False,installation_performed=False,ingame_validated=False,global_production=False,release_modified=False,
        commit_performed_in_p2=False,git_base=before['git_base'],
        contract=dict(registry_version=6,catalog_version=2,class_profile_id=1,decode_rule_id=1,
                      fractions='optional u8 per pixel, values 0..7; no bit packing',k=6,boundary_mixing=False,
                      fallback='native BAM; explicit Q0 A/B packs',logical_digests_include_I_F_dep_profiles=True),
        python_tests_total=146,python_tests_status='passed',native_ctest_suites_passed=4,
        native_fraction_tests=native,host_fixture_sha256=sha(fixture/'fixtures.json'),
        reference_fixture=dict(path='P1/decoder-golden.npz',sha256=packs['p1_golden_sha256'],
                               distinct_reference_decodings=32832,reference_palettes=18,extra_rgba_palettes=32,
                               native_encodings=['RGBA/u8','BGRA/u8','BGRA/u32_8888_REV'],alpha='P1 synthetic; extra arbitrary'),
        pack_scope=dict(animation='0x6110',resrefs=packs['source_resrefs'],native_frames=4230,
                        sampled_P1_frames=84,common_xbr_frames=4146,placeholders=756,complete_native_tables=True),
        packs=verified_packs,pack_reference_frame_decodes=sum(p['native_check']['pack_frames']*18 for p in verified_packs),
        pack_reference_pixels=sum(p['native_check']['decoded_pixels'] for p in verified_packs),
        candidate_dll=dict(path=dll.relative_to(OUTPUT).as_posix(),sha256=sha(dll),bytes=dll.stat().st_size,
                           pe='AMD64 PE32+ DLL',installed=False),artifacts_sha256=binaries,
        engine_source_contract_sha256=registry.source_tree_hash(ENGINE),source_sha256=current,
        frozen_sources=frozen,source_stable_during_final_build=True,
        toolchain={**pre['toolchain'],**dict(generator='Visual Studio 16 2019',python='3.11.5',
                                          python_reference='config://chainner_python',dependencies=dependencies)},
        preserved_proofs_sha256=preserved,preserved_consumed_p1_files=len(packs['p1_files_sha256']),
        live_local_inputs_sha256=live,
        guide=dict(path=str(guide.relative_to(ROOT)),sha256=sha(guide),modified_by_p2=False,
                   notes=['Registry V6 now reserved; logical specification concretized',
                          'LUT fills used pairs only, exact dependency mask',
                          'Pulse invalidation follows actual dependency changes',
                          'Current fallback is native BAM; no automatic parallel V5/xBR branch']),
        ref_error_increase_percent=pre['summary']['ref_error_increase_percent'],
        remaining_native_or_ingame_proofs=['Actual realized palette/alpha/effects capture in BG2EE',
            'Live GL upload/queue, WGL context recreation and frame timing',
            'Visual REF regression decision, recoloring/seams, world/paperdoll and inventory vertical'],
        commands=[
            'cmake --build build/palette-q3m-p2-20260930-v1/cmake --config Release --target iee_tests iee_palette_fraction_tests iee_effect_animation_x4_registry_tests iee_bridge_worker_tests InfinityEngine-Enhancer --parallel 4',
            'ctest --test-dir build/palette-q3m-p2-20260930-v1/cmake -C Release --output-on-failure --no-tests=error',
            'python -B -m unittest pipeline.tests.test_palette_registry pipeline.tests.test_creature_sprite_xn_catalog pipeline.tests.test_reboutcx_catalog pipeline.tests.test_palette_frac_encode pipeline.tests.test_palette_eval pipeline.tests.test_reboutcx_multipal pipeline.tests.test_creature_sprite_x2_pipeline pipeline.tests.test_reboutcx_full pipeline.tests.test_reboutcx_pipeline',
            'python -B pipeline/scripts/palette_p2.py packs --output <fresh-run>',
            'iee_palette_fraction_tests.exe --pack <pack>/iee-assets/creature-sprites <pack>/decoder-oracle.bin'],
        log_sha256={name:sha(OUTPUT/name) for name in ('build-final.log','ctest-final.log','python-final.log',
                    'native-x2-q0.log','native-x2-q3m-k6.log','native-x4-q0.log','native-x4-q3m-k6.log')},
        evidence_sha256={'packs.json':sha(OUTPUT/'packs.json'),'source-before.json':sha(OUTPUT/'source-before.json')})
    save(OUTPUT/'verification.json',report)
    print(json.dumps({k:report[k] for k in ('status','python_tests_total','native_ctest_suites_passed',
                                          'pack_reference_frame_decodes','pack_reference_pixels','candidate_dll')},indent=2))


if __name__=='__main__':
    if sys.argv[1:]==['--begin']:
        save(OUTPUT/'source-before.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
            git_base=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
            sha256=inventory(),artifacts_sha256=artifact_hashes()))
    elif not sys.argv[1:]:finalize()
    else:raise SystemExit('usage: finalize.py [--begin]')
