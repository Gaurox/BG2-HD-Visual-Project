"""Seal installed insect0.60 bytes and record explicit user ingame acceptance."""
from pathlib import Path
from dataclasses import replace
from collections import defaultdict
import copy,importlib.util,json,os,shutil,sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
import run_effect_interpolation as interpolation
from workspace_paths import get_path


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


base=module('accepted_insect_temporal','pipeline/recipes/effects-lot26-seedvr7b-apollo30-20261017-v2/temporal.py')
builder=module('accepted_insect_encoder','pipeline/recipes/effects-lot58-install-20261017-v1/install.py')
OUT=ROOT/'effects/batches/insectes-continu-accepted-20261027-v1'
INSTALL=ROOT/'effects/installations/insectes-continu-reference060-20261027-v1'
DATE='2026-10-27'
DECISION="ok on valide. maj le suivi et committe"
load,save,rel=base.load,base.save,base.rel
sha=workflow.sha256_file
base.BATCH=OUT


def copy_exact(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert sha(target)==sha(source)
    else:
        try:os.link(source,target)
        except OSError:shutil.copy2(source,target)
    assert sha(source)==sha(target)


def derive():
    assert not (OUT/'production.json').exists()
    source=load(INSTALL/'derivation.json');assets=[];reports=[]
    for d in source['assets']:
        a=copy.deepcopy(d['asset']);ref=a['resref']
        a['parent_interpolation_run']=a['interpolation_run']
        a.update(interpolation_run=f'{ref.lower()}-continu060-apollo30-20261027-v1',
                 pack=f'effects/ressources/{ref}/packs/{ref.lower()}-7b-continu060-apollo30-20261027-v1')
        assets.append(a)
    save(OUT/'batch.json',{'assets':assets,'isocontour':0.60,'installation':workflow.file_evidence(ROOT,INSTALL/'installation.json')})
    for a in assets:
        ref=a['resref'];d=next(x for x in source['assets'] if x['resref']==ref)
        original=ROOT/d['manifest']['path'];assert sha(original)==d['manifest']['sha256']
        m=copy.deepcopy(load(original));plan=replace(base.make_plan(a),recipe_id='insect-continuous060-approved-ingame')
        assert not plan.run_root.exists();interpolation.reserve(plan);plan.run_root.mkdir(parents=True)
        snapshot=plan.run_root/'producer-source.py';shutil.copy2(Path(__file__),snapshot)
        carrier=plan.run_root/'runtime-carrier'/f'{ref}.bam'
        copy_exact(ROOT/m['runtime_carrier']['path'],carrier)
        m['runtime_carrier']['path']=rel(carrier)
        for f in m['frames']:
            for key,suffix in [('raw_rgba_x4',''),('straight_raw_rgba_x4','-straight')]:
                path=ROOT/f[key];target=plan.interpolation_root/'frames-rgba'/f'frame_{f["frame"]:03d}{suffix}.rgba'
                assert sha(path)==f[key+'_sha256'];copy_exact(path,target)
                f[key]='frames-rgba/'+target.name
        recipe={'schema':interpolation.RECIPE_SCHEMA,'recipe_id':plan.recipe_id,'pipeline_id':interpolation.PIPELINE_ID,
            'scale':4,'native_fps':[15,1],'target_fps':[30,1],'spatial_model':'seedvr2_7b_int8_convrot.safetensors',
            'interpolation_model_inherited':'apo-8','new_neural_inference':0,'isocontour':0.60,
            'alpha_policy':'continuous native field sigma0.25x1, SS4 coverage, then unchanged native temporal fractions',
            'selected_variant':'Reference appreciee','source_installed_manifest':interpolation.evidence(ROOT,'installed-derivation',original),
            'installation_receipt':interpolation.evidence(ROOT,'installation',INSTALL/'installation.json'),
            'tools':[interpolation.evidence(ROOT,'producer',snapshot)]}
        save(plan.recipe_path,recipe);m['visual_treatment']=recipe
        save(plan.interpolation_root/'manifest.json',m)
        descriptor=interpolation.descriptor(plan,recipe,status='completed',sealed=True,created_at=workflow.utc_now(),outputs=[
            interpolation.evidence(ROOT,'interpolation-manifest',plan.interpolation_root/'manifest.json'),
            interpolation.evidence(ROOT,'runtime-bam-carrier',carrier)])
        descriptor['pipeline']['version']='effect-insects-continuous060-accepted.v1'
        descriptor['provenance']['generator']=rel(Path(__file__))
        descriptor['inputs'].extend([recipe['source_installed_manifest'],recipe['installation_receipt']])
        save(plan.descriptor_path,descriptor)
        reports.append(base.finish(a,plan,load(plan.spatial_manifest)))
    save(OUT/'production.json',{'status':'completed','assets':reports,'count':3,'phases':392,'profiles':8,
        'native_geometry_and_durations_preserved':True,'selected_loop_phases_exact':196,
        'installed_bytes_unchanged':True,'release_changed':False})


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'acceptance.json').exists(),'Final acceptance is immutable'
    before_path=OUT/'processing-before.csv'
    if not before_path.exists():before_path.write_bytes((ROOT/'effects/index/processing.csv').read_bytes())
    before={r['asset_key']:r for r in workflow.read_csv(before_path,workflow.PROCESSING_FIELDS)}
    if not (OUT/'production.json').exists():derive()
    assets=load(OUT/'batch.json')['assets'];game=get_path('bg2ee_game_root',required=True)
    installed_path=game/'iee-assets/effects/manifest.json';installed=load(installed_path)
    receipt=load(INSTALL/'installation.json');assert sha(installed_path)==receipt['manifest_sha256']
    assert sha(game/'iee-assets/effects/EffectAnimations-X4.registry')==installed['registry_sha256']
    transaction=load(INSTALL/'transaction.json');assert transaction['status']=='installed'
    # Only the847files of this correction, no global asset reconstruction.
    for f in transaction['files']:
        assert not f.get('delete') and sha(game/f['name'])==f['sha256']
    members={r['resref']:r for r in installed['resources']};frames=defaultdict(list)
    for f in installed['frames']:frames[f['resref']].append(f)
    runtime=[]
    for a in assets:
        ref=a['resref'];stage=ROOT/'effects/ressources'/ref/'runs'/a['interpolation_run']/'02-interpolation'
        m=load(stage/'manifest.json');variants={'SPINSECT':['SPINSECT','XINSECTN'],
            'SPIPLAAI':['SPIPLAAI','SPIPLARI','X26PLAA'],'SPIPLAUI':['SPIPLAUI','XIPLAUIN']}[ref]
        for name in variants:
            member=members[name];straight=member['rgb_encoding']=='straight'
            _,built,new_frames,_,_,_=builder.build_resource(a,name,straight)
            assert built['timeline']==member['timeline'] and built['cycles']==member['cycles']
            expected={f['asset']:f for f in new_frames}
            assert set(expected)=={f['asset'] for f in frames[name]}
            for f in frames[name]:
                e=expected[f['asset']]
                for key in ['sha256','bytes','logical_size_x1','physical_size_x4','source_centre_x1']:
                    assert f[key]==e[key],(name,key)
            c=next(c for c in installed['runtime_bam_carriers'] if c['resref']==name)
            assert c['sha256']==m['runtime_carrier']['sha256'] and sha(game/c['asset'])==c['sha256']
            runtime.append({'runtime_resref':name,'production_bam':ref,'accepted_run':a['interpolation_run'],
                'installed_parent_run_label':member['interpolation_run'],'rgb_encoding':member['rgb_encoding'],
                'run':workflow.file_evidence(ROOT,stage.parent/'run.json'),
                'interpolation_manifest':workflow.file_evidence(ROOT,stage/'manifest.json'),
                'backings':len(frames[name]),'carrier':c,'exact_pixels_geometry_timelines_bound':True})
    accepted=[]
    for a in assets:
        accepted.append(workflow.accept_asset(ROOT,a['resref'],pack_path=a['pack'],decision=DECISION,decision_date=DATE,write=True))
        print('accepted',a['resref'],flush=True)
    proof=[];names={a['resref'] for a in assets}
    for row in workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS):
        previous=before[row['asset_key']];ref=row['asset_key'].rsplit(':',1)[-1]
        if ref not in names:assert row==previous,row['asset_key'];continue
        assert row['selected_run']==row['interpolation_run'] and row['qa_state']=='passed'
        assert row['spatial_state']==row['interpolation_state']=='verified'
        for key in ['installation_state','installation_receipt','release_state','release_candidate']:assert row[key]==previous[key]
        selection=ROOT/f'effects/index/selections/{ref}.json'
        proof.append({'resref':ref,'selection':workflow.file_evidence(ROOT,selection),
                      'qa_evidence':workflow.file_evidence(ROOT,ROOT/row['qa_evidence'])})
    save(OUT/'verification.json',{'passed':True,'accepted_count':3,'runtime_bindings':7,'checked_installed_files':len(transaction['files']),
        'other_rows_unchanged':True,'installation_and_release_unchanged':True,'assets':proof})
    clua=load(INSTALL/'clua.json');save(OUT/'clua.json',clua)
    (OUT/'CLUA.md').write_bytes((INSTALL/'CLUA.md').read_bytes())
    save(OUT/'acceptance.json',{'schema':'bg2-effects-batch-user-acceptance-v1','decision_date':DATE,'user_decision':DECISION,
        'status':'accepted','accepted_count':3,'accepted':accepted,'selected_variant':'Reference appreciee, continuous0.60',
        'final_assets':assets,'bound_runtime_variants':runtime,'source_aliases':{'SPIPLARI':{'canonical':'SPIPLAAI','runtime_reuse_bound':True}},
        'installation':workflow.file_evidence(ROOT,INSTALL/'installation.json'),'transaction':workflow.file_evidence(ROOT,INSTALL/'transaction.json'),
        'installed_manifest_sha256':sha(installed_path),'installed_registry_sha256':installed['registry_sha256'],
        'accepted_controller_bindings':clua,'individual_profile_tests_inferred':False,
        'native_owner_blend_or_measured_cadence_inferred':False,'new_inference':0,'installed_files_changed':False,
        'lot31_acceptance_inferred':False,'release_mutation':False})
    print('ACCEPTED insects0.60:3assets/7runtime bindings; other rows and installed files unchanged',flush=True)


if __name__=='__main__':main()
