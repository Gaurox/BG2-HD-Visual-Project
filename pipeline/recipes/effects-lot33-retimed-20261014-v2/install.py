"""One transaction: corrected renderer + 33 padded BAM carriers + 97-effect pack."""
from produce import ROOT,BATCH,ORIGINAL,load,save,rel
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import sys
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
from compose_effect_runtime_packs import validate_pack,compose,write_pack,sha256_file
from workspace_paths import get_path
import install_renderer_candidate as installer
import effect_workflow as workflow
import effect_authority as authority

OUT=ROOT/'effects/installations/lot33-retimed-7b-x4-nearest-20261014-v2'
CANDIDATE=OUT/'candidate'
BUILD=ROOT/'build/iee-map-first-frame-refresh-20261014-v1'
BASE64=ROOT/'effects/installations/lot33-seedvr7b-apollo30-nearest-20261014-v1/installed-before/effects'
PRESERVED=['InfinityEngine-Enhancer.ini','override/fpDraw.glsl','override/fpSprite.glsl',
    'override/fpSELECT.glsl','iee-assets/creature-sprites/CreatureSprites-XN.catalog']


def profile(game):return {n:sha256_file(game/n) for n in PRESERVED}


def prepare():
    assert not (OUT/'installation.json').exists()
    verification=load(BATCH/'verification.json');assert verification['passed']==33 and verification['duplicates']==0
    game=get_path('bg2ee_game_root',required=True)
    current=validate_pack(game/'iee-assets/effects');base=validate_pack(BASE64)
    names={a['resref'] for a in load(ORIGINAL)['assets']}
    assert current.resource_count==97 and base.resource_count==64
    old={r['resref']:r for r in current.resources if r['resref'] not in names}
    assert old=={r['resref']:r for r in base.resources}
    assert {f['asset']:f['sha256'] for f in current.frames if f['resref'] not in names}=={f['asset']:f['sha256'] for f in base.frames}
    accepted_profile=load(ROOT/'engine/InfinityEngine-Enhancer/installations/renderer-startup-barrier-20261014-v1/installation.json')['preserved_sha256']
    preserved=profile(game);assert preserved=={n:accepted_profile[n] for n in PRESERVED}
    before={'dll_sha256':sha256_file(game/'InfinityEngine-Enhancer.dll'),
        'effects_manifest_sha256':current.manifest_sha256,'profile_sha256':preserved,
        'previous_resources':97,'previous_unchanged_resources':64}
    OUT.mkdir(parents=True,exist_ok=True)
    if (OUT/'before.json').exists():assert load(OUT/'before.json')==before
    else:save(OUT/'before.json',before)
    CANDIDATE.mkdir(exist_ok=True)
    shutil.copy2(BUILD/'Release/InfinityEngine-Enhancer.dll',CANDIDATE/'InfinityEngine-Enhancer.dll')
    shutil.copy2(game/'InfinityEngine-Enhancer.ini',CANDIDATE/'InfinityEngine-Enhancer.ini')
    reports=[load(BATCH/'checks'/(a['resref']+'.json')) for a in load(ORIGINAL)['assets']]
    packs=[base]+[validate_pack(ROOT/r['pack']) for r in reports]
    target=CANDIDATE/'iee-assets/effects'
    if not target.exists():
        registry,manifest,copies=compose(packs)
        manifest['runtime_bam_carriers']=[]
        (CANDIDATE/'override').mkdir()
        for r in reports:
            name='override/'+r['resref']+'.bam';source=ROOT/r['runtime_bam'];shutil.copy2(source,CANDIDATE/name)
            manifest['runtime_bam_carriers'].append({'resref':r['resref'],'asset':name,
                'sha256':sha256_file(source),'bytes':source.stat().st_size,
                'policy':'transparent padding only; native world pixels, palette and cycles unchanged'})
        write_pack(target,registry,manifest,copies)
    pack=validate_pack(target)
    assert pack.resource_count==97 and sum(f['bytes'] for f in pack.frames)<4294967296
    assert {r['resref'] for r in pack.resources}==names|set(old)
    assert {f['asset']:f['sha256'] for f in pack.frames if f['resref'] not in names}=={f['asset']:f['sha256'] for f in base.frames}
    for r in reports:
        unit=validate_pack(ROOT/r['pack'])
        assert next(x for x in pack.resources if x['resref']==r['resref'])==unit.resources[0]
        assert {f['asset']:f['sha256'] for f in pack.frames if f['resref']==r['resref']}=={f['asset']:f['sha256'] for f in unit.frames}
    with (OUT/'native-loader-all-phases.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(BUILD/'Release/iee_effect_animation_x4_registry_tests.exe'),str(target),
            str(BATCH/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True)
    installer.install_candidate(CANDIDATE,game_root=game,backup_root=OUT/'backups',verify_only=True)
    save(OUT/'plan.json',{'resources':97,'replaced_effects':33,'previous_effects_byte_identical':64,
        'phases':verification['phases'],'duplicates':0,'raw_bytes':sum(f['bytes'] for f in pack.frames),
        'manifest_sha256':pack.manifest_sha256,'dll_sha256':sha256_file(CANDIDATE/'InfinityEngine-Enhancer.dll'),
        'profile_sha256':preserved,'runtime_contract_rows':verification['runtime_contract_rows'],
        'case_insensitive_lookup':True,'native_world_geometry_preserved':True,
        'model':'seedvr2_7b_int8_convrot.safetensors','scale':4,'target_fps':[30,1],'filter':'NEAREST',
        'startup_barrier_and_map_refresh_preserved':True,'visual_qa':'pending-user-controlled-game'})
    print('Candidate prepared and all 33 resources/all phases passed native loader.',flush=True)


def install():
    assert not (OUT/'installation.json').exists()
    game=get_path('bg2ee_game_root',required=True)
    installer.ensure_game_stopped(installer.running_game_processes)
    before=load(OUT/'before.json');plan=load(OUT/'plan.json')
    assert profile(game)==before['profile_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.dll')==before['dll_sha256']
    assert sha256_file(game/'iee-assets/effects/manifest.json')==before['effects_manifest_sha256']
    result=installer.install_candidate(CANDIDATE,game_root=game,backup_root=OUT/'backups')
    installer.verify_transaction(result.receipt_path,game_root=game)
    installed=validate_pack(game/'iee-assets/effects')
    assert installed.manifest_sha256==plan['manifest_sha256'] and profile(game)==plan['profile_sha256']
    assert sha256_file(game/'InfinityEngine-Enhancer.dll')==plan['dll_sha256']
    assert set(result.files)=={'InfinityEngine-Enhancer.dll','InfinityEngine-Enhancer.ini'}|{
        'iee-assets/effects/'+p.name for p in (CANDIDATE/'iee-assets/effects').iterdir()}|{
        'override/'+p.name for p in (CANDIDATE/'override').iterdir()}
    for c in installed.manifest['runtime_bam_carriers']:
        assert sha256_file(game/c['asset'])==c['sha256']
    with (OUT/'installed-native-loader-all-phases.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(BUILD/'Release/iee_effect_animation_x4_registry_tests.exe'),str(installed.root),
            str(BATCH/'runtime-contracts.tsv')],stdout=log,stderr=subprocess.STDOUT,check=True)
    receipt=rel(result.receipt_path)
    names={a['resref'] for a in load(ORIGINAL)['assets']}
    with authority.guard(ROOT,write=True):
        rows=workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS)
        save(OUT/'processing-before.json',rows)
        for row in rows:
            if row['asset_key'].rsplit(':',1)[-1] in names:
                row['installation_state']='installed';row['installation_receipt']=receipt
        authority.commit(ROOT,{'effects/index/processing.csv':workflow.csv_bytes(rows)})
    final={**plan,'schema':'bg2-effects-retimed-installation-v1','status':'installed-offline-verified',
        'receipt':receipt,'runtime_bam_carriers':33,'character_profile':'NearestRGB-SilhouetteAlphaAA',
        'character_files_byte_identical':True,'game_launched_by_agent':False,'map_assets_changed':False,
        'release_changed':False}
    save(OUT/'installation.json',final)
    shutil.copy2(ROOT/'effects/installations/lot33-seedvr7b-apollo30-nearest-20261014-v1/CLUA.md',OUT/'CLUA.md')
    print(json.dumps(final,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','install']);args=parser.parse_args()
    {'prepare':prepare,'install':install}[args.action]()
