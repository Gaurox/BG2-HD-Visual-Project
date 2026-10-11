"""Accept the installed lot5 variants; retain AM3000E's already acquired decision."""
from pathlib import Path
import sys,csv
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/recipes/lot45-final-20261011-v1'))
from common import v,rel,payload,AREAS,GAME
import animation_workflow as workflow
import area_pack_state as state

TAG='lot5-accepted-20261011-v1'
REPORT=Path(__file__).resolve().parent/'acceptance.json'
JOBS={
    'FLM2PUR':dict(pack='flm2pur-palette-selection-soft2-20261011-v1',source='flm2pur-palette-selection-soft2-20261011-v1',
        receipt='animations/batches/flm2pur-oh4210-contour-20261011-v1/installation.json',
        recipe='ReboutCX x4/Apollo8; AR1008 palette embarquée inner4, OH4210 PLT_PURP sigma2x4/étincelles sigma0,8/canvas1 ; dimensions natives exactes,32phases/1,066667s'),
    'AMWRPGT1':dict(pack='lot5-current-20261011-v1',source='amwrpgt1-lot5-current-20261011-v1',
        receipt='animations/batches/lot45-final-20261011-v1/installation.json',
        recipe='SeedVR2 7B LAB x4 réutilisé byte-identique; spline fit1 safe inner8/outer6/alpha gauss3, Apollo8;24phases/0,8s sur17cartes'),
}

def main():
    assert not REPORT.exists(),'acceptance already sealed'
    lock=state.load_lock();checks=[];all_areas=set()
    for ref,job in JOBS.items():
        areas=AREAS[ref];all_areas.update(areas)
        pack=ROOT/'animations/packs-par-zone'/job['pack']
        for area in areas:
            leaf=pack/area;live=GAME/'iee-assets/areas'/area
            assert payload(live)==payload(leaf),area+': installed bytes differ'
            assert state.zone_signatures(live)==lock['areas'][area]['resources']
            assert state.recipe_signatures(lock['areas'][area])=={key:data['sig'] for key,data in lock['areas'][area]['resources'].items()}
            resources=[r for r in v.validate_v2_pack(leaf)[1] if r['resref']==ref];assert len(resources)==1
            r=resources[0];assert r['target_fps']==dict(numerator=30,denominator=1)
            assert all(len(c['native_frame_indices'])/15==len(c['timeline_frame_indices'])/30 for c in r['cycles'])
        source=ROOT/f'animations/ressources/{ref}/runs'/job['source']
        final=ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-{TAG}'
        final.mkdir(parents=True,exist_ok=False);leaf=pack/areas[0]
        v.write_json(final/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),
            resrefs=[ref],source_run=rel(source),source_run_manifest_sha256=v.sha256_file(source/'manifest.json'),
            source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
            output_split_root=rel(pack),output_manifest_sha256=v.sha256_file(pack/'manifest.json'),
            tested_areas=areas,selection_reason='Utilisateur : ok je valide tout le lot. maj le suivi et committe.',
            recipe=job['recipe'],installation_receipt=job['receipt'],qa_status='accepted-ingame',release_status='not-selected'))
        decision=f'2026-10-11-accepted-{ref.lower()}-lot5-final-v1'
        workflow.finalize(ROOT,ref,final,pack,areas,'accepted','2026-10-11',
            'Utilisateur : ok je valide tout le lot. '+ref+' accepté ingame sur '+','.join(areas)+'. '+job['recipe']+'.',
            decision_id=decision,recipe_id=TAG,correction_id=TAG,
            notes='Lot5 terminé, QA ingame utilisateur acceptée sur toutes les occurrences. '+job['recipe']+'. Reçu '+job['receipt']+'. Release non sélectionnée.',apply=True)
        check=workflow.check_workspace(ROOT,ref);assert check['ok'],check
        checks.append(dict(resref=ref,areas=areas,final_run=rel(final),qa_decision=f'animations/index/qa-decisions/{ref}/{decision}.json',
            recipe=job['recipe'],installed_payload_identical=True,qa_lineage_valid=True))
        print('ACCEPTED',ref,len(areas),'areas',flush=True)
    # This immutable decision already covers all five AM3000E occurrences; no new decision is needed.
    ref='AM3000E';selection=v.load_json(ROOT/'animations/index/selections'/f'{ref}.json')
    check=workflow.check_workspace(ROOT,ref);assert check['ok'],check
    pack=ROOT/'animations/packs-par-zone/am3000e-contour-native-20261011-v2';area='AR3000';all_areas.add(area)
    assert payload(GAME/'iee-assets/areas'/area)==payload(pack/area)
    assert state.zone_signatures(GAME/'iee-assets/areas'/area)==lock['areas'][area]['resources']
    checks.insert(0,dict(resref=ref,areas=[area],qa_decision='animations/index/qa-decisions/AM3000E/2026-10-11-accepted-am3000e-native-contour-v1.json',
        existing_accepted_decision_retained=True,installed_payload_identical=True,qa_lineage_valid=True,
        recipe='ReboutCX PLT_MAGE/Apollo8; fondu doux sigma2/canvas2; dimensions/centres natifs restaurés,61frames/48-36-20phases'))
    assert len(all_areas)==20
    rows=list(csv.DictReader((ROOT/'animations/index/animation_upscale_registry.csv').open(encoding='utf-8')))
    assert all(next(r for r in rows if r['resref']==ref)['status']=='validé-x4' for ref in ['AM3000E','FLM2PUR','AMWRPGT1'])
    v.write_json(REPORT,dict(schema='bg2-upscale-animation-batch-acceptance-v1',status='accepted-ingame',decision_date='2026-10-11',
        decision_origin='explicit-user-ingame-qa',decision='ok je valide tout le lot. maj le suivi et committe.',lot=5,
        asset_count=3,palette_variant_count=4,area_count=20,occurrences=68,resources=checks,
        AMWRPGT1_prior_QA_retained=['AR3011','AR3016','AR3017'],game_payload_changed=False,release_status='not-selected'))
    print('LOT5 ACCEPTED: 3 assets /4 variants /20 areas /68 occurrences',flush=True)

if __name__=='__main__':main()
