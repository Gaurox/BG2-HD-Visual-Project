"""Accept the installed33 impacts; SPDEATH3 uses the final Bezier/soft4 pack."""
from collections import defaultdict
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

BATCH=ROOT/'effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1'
DEATH=ROOT/'effects/batches/spdeath3-bezier-soft4-runtime-20261018-v2'
INSTALL=ROOT/'effects/installations/lot33-native-impacts-20261018-v1'
FIX=ROOT/'effects/installations/spdeath3-bezier-soft4-20261018-v1'
OUT=ROOT/'effects/batches/lot33-impacts-accepted-20261018-v1'
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
evidence=lambda p:workflow.file_evidence(ROOT,p)
sha=workflow.sha256_file
DECISION='ok tout est bon, les 33 effets sont validés ingame. mets à jour le suivi et committe.'
DATE='2026-10-18'


def save(name,value):
    path=OUT/name
    assert not path.exists(),'Final evidence is immutable'
    path.write_bytes(workflow.json_bytes(value))


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'acceptance.json').exists(),'Final acceptance already exists'
    assets=load(BATCH/'batch.json')['assets']
    death=load(DEATH/'batch.json')['assets'][0]
    assets=[death if a['resref']=='SPDEATH3' else a for a in assets]
    assert len(assets)==33 and death['interpolation_run']=='spdeath3-bezier-soft4-20261018-v2'
    game=get_path('bg2ee_game_root',required=True)
    manifest_path=game/'iee-assets/effects/manifest.json';installed=load(manifest_path)
    assert sha(manifest_path)==load(FIX/'installation.json')['manifest_sha256']
    assert installed['registry_version']==3 and installed['resource_count']==322 and installed['frame_count']==43357
    assert sha(game/'iee-assets/effects/EffectAnimations-X4.registry')==installed['registry_sha256']
    preserved=load(FIX/'before.json')['preserved']
    assert all(sha(game/name)==value['sha256'] for name,value in preserved.items())
    members={r['resref']:r for r in installed['resources']};frames=defaultdict(list)
    for f in installed['frames']:frames[f['resref']].append(f)
    main_clua={r['bam']:r for r in load(INSTALL/'clua.json')}
    controls={};runtime=[];final_assets=[];aliases={}
    for a in assets:
        ref=a['resref'];source_batch=DEATH if ref=='SPDEATH3' else BATCH
        check=load(source_batch/'checks'/f'{ref}.json')
        assert sha(ROOT/a['pack']/'manifest.json')==check['pack_manifest_sha256']
        stage=ROOT/'effects/ressources'/ref/'runs'/a['interpolation_run']/'02-interpolation'
        m=load(stage/'manifest.json');descriptor=stage.parent/'run.json'
        assert load(descriptor)['result']['sealed']
        command=main_clua[ref]
        variants=[ref]+a['reuse_aliases']+[f'X33N{a["ordinal"]:02d}']
        for alias in a['reuse_aliases']:
            aliases[alias]={'canonical':ref,'runtime_reuse_bound':True,'separate_production_or_qa_row_inferred':False}
        for runtime_ref in variants:
            r=members[runtime_ref]
            assert r['production_bam']==ref and r['interpolation_run']==a['interpolation_run']
            key='straight_raw_rgba_x4' if r['rgb_encoding']=='straight' else 'raw_rgba_x4'
            sources={(stage/f[key]).as_posix():f for f in m['frames']}
            assert len(frames[runtime_ref])==r['frame_count']
            for f in frames[runtime_ref]:
                source=sources[(ROOT/f['source']).as_posix()]
                assert f['sha256']==source[key+'_sha256']
                assert f['physical_size_x4']==source['physical_size_x4']
                assert f['source_centre_x1']==source['centre_x1']
            c=next(c for c in installed['runtime_bam_carriers'] if c['resref']==runtime_ref)
            assert c['sha256']==m['runtime_carrier']['sha256'] and sha(game/c['asset'])==c['sha256']
            runtime.append({'runtime_resref':runtime_ref,'production_bam':ref,
                'interpolation_run':a['interpolation_run'],'rgb_encoding':r['rgb_encoding'],
                'backings':len(frames[runtime_ref]),'run':evidence(descriptor),
                'interpolation_manifest':evidence(stage/'manifest.json'),
                'carrier':c,'primary_test_binding':runtime_ref==command['runtime_bam'],
                'contract_bound_to_accepted_production':True,
                'all_profiles_or_comparison_modes_individually_tested_inferred':False})
        name=command['vvc'];control=next(c for c in installed['runtime_vvc_controllers'] if c['asset']==f'override/{name}.vvc')
        assert sha(game/control['asset'])==control['sha256'] and control['bam']==command['runtime_bam']
        controls[name]=control
        final_assets.append({'ordinal':a['ordinal'],'resref':ref,'pack':a['pack'],
             'interpolation_run':a['interpolation_run'],'pack_manifest':evidence(ROOT/a['pack']/'manifest.json'),
             'primary_test':command,'sigma_x4':4 if ref=='SPDEATH3' else None})
    assert len(runtime)==69 and len(controls)==33 and len(aliases)==3
    before_path=OUT/'processing-before.csv'
    assert not before_path.exists();before_path.write_bytes((ROOT/'effects/index/processing.csv').read_bytes())
    before={r['asset_key']:r for r in workflow.read_csv(before_path,workflow.PROCESSING_FIELDS)}
    accepted=[];names={a['resref'] for a in assets}
    for a in assets:
        accepted.append(workflow.accept_asset(ROOT,a['resref'],pack_path=a['pack'],decision=DECISION,decision_date=DATE,write=True))
        print('accepted',a['resref'],flush=True)
    proof=[]
    for row in workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS):
        previous=before[row['asset_key']];ref=row['asset_key'].rsplit(':',1)[-1]
        if ref not in names:
            assert row==previous,row['asset_key'];continue
        assert row['qa_state']=='passed' and row['spatial_state']==row['interpolation_state']=='verified'
        assert row['selected_run']==row['interpolation_run']
        assert all(row[k]==previous[k] for k in ['installation_state','installation_receipt','release_state','release_candidate'])
        selection=load(ROOT/f'effects/index/selections/{ref}.json')
        assert selection['selected_run']==row['selected_run']
        assert selection['qa_evidence']['path']==row['qa_evidence']
        assert sha(ROOT/row['qa_evidence'])==selection['qa_evidence']['sha256']
        proof.append({'resref':ref,'passed':True,'selection':evidence(ROOT/f'effects/index/selections/{ref}.json'),
                      'qa_evidence':evidence(ROOT/row['qa_evidence'])})
    assert len(proof)==33
    clua=load(INSTALL/'clua.json');save('clua.json',clua)
    text='# Lot33 impacts accepté — commandes validées\n\n33effets validés ingame2026-10-18 ; SPDEATH3 final Bézier+fondu sigma4. Lancer via InfinityLoader, une commande à la fois.\n\n```lua\n'
    for r in clua:text+=f'-- {r["ordinal"]:02d} {r["bam"]} / {r["profile"]}\n{r["clua"]}\n'
    text+='```\n\nLes182profils et66comparaisons restent disponibles dans le reçu d’installation ; aucun test individuel de chaque profil/mode n’est déduit de la validation des33assets.\n'
    (OUT/'CLUA.md').write_text(text,encoding='utf-8')
    save('verification.json',{'schema':'bg2-effects-acceptance-verification-v1','passed':True,
         'accepted_count':33,'runtime_resources_bound':69,'primary_controllers_bound':33,'assets':proof,
         'other_rows_unchanged':True,'installation_and_release_authorities_unchanged':True,
         'normal_and_alias_metadata_bound_to_final_frames':True,'spdeath3_selected_final_soft4':True})
    save('acceptance.json',{'schema':'bg2-effects-batch-user-acceptance-v1','decision_date':DATE,
         'user_decision':DECISION,'status':'accepted','accepted_count':33,'accepted':accepted,
         'final_assets':final_assets,'bound_runtime_variants':runtime,'source_aliases':aliases,
         'production':evidence(BATCH/'production.json'),'spdeath3_production':evidence(DEATH/'production.json'),
         'base_installation':evidence(INSTALL/'installation.json'),'spdeath3_installation':evidence(FIX/'installation.json'),
         'installed_manifest_sha256':sha(manifest_path),'installed_registry_sha256':installed['registry_sha256'],
         'preserved_runtime_profile':preserved,'accepted_primary_controllers':controls,
         'runtime_contract':{'registry_version':3,'production_assets_total':278,'runtime_resources':322,
             'backings':43357,'model':'seedvr2_7b_int8_convrot.safetensors','scale':4,
             'filter':'NEAREST','target_fps':[30,1],'lot_phases':5244,'lot_profiles':182,
             'duplicate_native_poses_removed_duration_preserved':True,'spdeath3_bezier_gaussian_sigma_x4':4,
             'native_contracts_verified_at_installation':92632,'metadata_mib':32},
         'ingame_qa':'explicit-user-validation-of-installed33-effects-including-spdeath3-soft4',
         'instrumented_native_owner_coverage':'no-new-owner-blend-or-substitution-trace-inferred',
         'measured_presentation_cadence':'no-new-instrumented-measurement-inferred',
         'historical_receipts_and_previews_immutable':True,'installed_files_changed':False,'release_mutation':False})
    print('33 accepted;69runtime bindings; SPDEATH3 final soft4; installation/release and other rows unchanged.',flush=True)


if __name__=='__main__':main()
