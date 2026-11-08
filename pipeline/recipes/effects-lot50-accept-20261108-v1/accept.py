"""Bind explicit user QA to current installed50, including seven alpha revisions."""
from collections import defaultdict
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

SOURCE=ROOT/'effects/batches/lot50-black-transparent-20261108-v1'
INSTALL=ROOT/'effects/installations/lot50-current-20261108-v1'
OUT=ROOT/'effects/batches/lot50-accepted-20261108-v1'
DECISION='bien tout est validé. maj le suivi et committe'
DATE='2026-11-08'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def evidence(p):return workflow.file_evidence(ROOT,p)
def save(name,value):
    p=OUT/name;assert not p.exists(),'Final acceptance evidence is immutable'
    p.write_bytes(workflow.json_bytes(value))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'acceptance.json').exists()
    production=load(SOURCE/'production.json');jobs=production['assets'];assert len(jobs)==50
    game=get_path('bg2ee_game_root',required=True);mp=game/'iee-assets/effects/manifest.json';installed=load(mp)
    installation=load(INSTALL/'installation.json')
    assert workflow.sha256_file(mp)==installation['manifest_sha256']
    assert workflow.sha256_file(game/'iee-assets/effects/EffectAnimations-X4.registry')==installed['registry_sha256']
    assert (installed['resource_count'],installed['frame_count'])==(638,66392)
    members={r['resref']:r for r in installed['resources']};frames=defaultdict(list)
    for f in installed['frames']:frames[f['resref']].append(f)
    clua={r['bam']:r for r in load(INSTALL/'clua.json')};bindings=[];controls={}
    for a in jobs:
        n=a['resref'];stage=ROOT/'effects/ressources'/n/'runs'/a['interpolation_run']/'02-interpolation';m=load(stage/'manifest.json')
        assert workflow.sha256_file(ROOT/a['pack']/'manifest.json')==a['pack_manifest_sha256']
        assert load(stage.parent/'run.json')['result']['sealed']
        for runtime_ref in (n,f'X50N{a["ordinal"]:02d}'):
            r=members[runtime_ref];assert r['production_bam']==n and r['interpolation_run']==a['interpolation_run']
            key='straight_raw_rgba_x4' if r['rgb_encoding']=='straight' else 'raw_rgba_x4'
            sources={(stage/f[key]).resolve().as_posix():f for f in m['frames']}
            assert len(frames[runtime_ref])==r['frame_count']
            for f in frames[runtime_ref]:
                source=sources[(ROOT/f['source']).resolve().as_posix()]
                assert f['sha256']==source[key+'_sha256'] and f['physical_size_x4']==source['physical_size_x4']
                assert f['source_centre_x1']==source['centre_x1']
            carrier=next(c for c in installed['runtime_bam_carriers'] if c['resref']==runtime_ref)
            assert carrier['sha256']==m['runtime_carrier']['sha256'] and workflow.sha256_file(game/carrier['asset'])==carrier['sha256']
            bindings.append(dict(runtime_resref=runtime_ref,production_bam=n,interpolation_run=a['interpolation_run'],rgb_encoding=r['rgb_encoding'],
                                 backings=len(frames[runtime_ref]),run=evidence(stage.parent/'run.json'),manifest=evidence(stage/'manifest.json'),
                                 carrier=carrier,primary_test_binding=runtime_ref==clua[n]['runtime_bam']))
        control=next(c for c in installed['runtime_vvc_controllers'] if c['asset']=='override/'+clua[n]['vvc']+'.vvc')
        assert control['bam']==clua[n]['runtime_bam'] and workflow.sha256_file(game/control['asset'])==control['sha256']
        controls[clua[n]['vvc']]=control
    assert len(bindings)==100 and len(controls)==50
    before_file=OUT/'processing-before.csv'
    if not before_file.exists():before_file.write_bytes((ROOT/'effects/index/processing.csv').read_bytes())
    before={r['asset_key']:r for r in workflow.read_csv(before_file,workflow.PROCESSING_FIELDS)}
    accepted=[]
    for a in jobs:
        # Resumable only when an identical explicit QA was already committed by this script.
        selection=ROOT/f'effects/index/selections/{a["resref"]}.json'
        if selection.exists() and load(selection).get('selected_run')==a['interpolation_run']:
            q=load(ROOT/load(selection)['qa_evidence']['path']);assert q['decision']==DECISION and q['decision_date']==DATE
            accepted.append(dict(resref=a['resref'],selected_run=a['interpolation_run'],selection=str(selection.relative_to(ROOT))))
        else:accepted.append(workflow.accept_asset(ROOT,a['resref'],pack_path=a['pack'],decision=DECISION,decision_date=DATE,write=True))
        print('accepted',a['resref'],flush=True)
    names={a['resref'] for a in jobs};proof=[]
    for row in workflow.read_csv(ROOT/'effects/index/processing.csv',workflow.PROCESSING_FIELDS):
        n=row['asset_key'].rsplit(':',1)[-1];old=before[row['asset_key']]
        if n not in names:assert row==old;continue
        assert row['qa_state']=='passed' and row['spatial_state']==row['interpolation_state']=='verified'
        assert row['selected_run']==row['interpolation_run']
        assert all(row[k]==old[k] for k in ('installation_state','installation_receipt','release_state','release_candidate'))
        selection=ROOT/f'effects/index/selections/{n}.json';s=load(selection)
        assert s['selected_run']==row['selected_run'] and s['qa_evidence']['path']==row['qa_evidence']
        assert workflow.sha256_file(ROOT/row['qa_evidence'])==s['qa_evidence']['sha256']
        proof.append(dict(resref=n,selection=evidence(selection),qa_evidence=evidence(ROOT/row['qa_evidence'])))
    assert len(proof)==50
    save('verification.json',dict(passed=True,accepted_count=50,runtime_bindings=100,primary_controllers=50,assets=proof,
                                 other_rows_unchanged=True,installation_and_release_states_unchanged=True))
    save('acceptance.json',dict(schema='bg2-effects-batch-user-acceptance-v1',status='accepted',decision_date=DATE,user_decision=DECISION,
                              accepted_count=50,accepted=accepted,final_assets=jobs,bound_runtime_variants=bindings,accepted_primary_controllers=controls,
                              production=evidence(SOURCE/'production.json'),installation=evidence(INSTALL/'installation.json'),
                              installed_manifest_sha256=workflow.sha256_file(mp),installed_registry_sha256=installed['registry_sha256'],
                              models=production['model_counts'],phases=5164,profiles=150,black_transparent=installation['black_transparent'],
                              installed_files_changed=False,release_mutation=False,
                              ingame_qa='Explicit user validation of installed50, including final seven black-transparent revisions.',
                              individual_all_profiles_or_blend_modes_tested_inferred=False,
                              instrumented_presentation_cadence_or_native_owner_coverage_inferred=False))
    save('clua.json',load(INSTALL/'clua.json'))
    (OUT/'CLUA.md').write_bytes((INSTALL/'CLUA.md').read_bytes())
    print('ACCEPTED50;100runtime bindings; installation/release unchanged',flush=True)

if __name__=='__main__':main()
