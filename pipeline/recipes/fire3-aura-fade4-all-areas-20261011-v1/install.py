"""Use the standard transactional area installer; seal propagation separately from QA."""
from prepare import *
import importlib.util
import animation_workflow as w

module_name='fire3_area_installer'
spec=importlib.util.spec_from_file_location(module_name,ROOT/'pipeline/area-animation-area-test/area_animation_area_test.py')
installer=importlib.util.module_from_spec(spec);sys.modules[module_name]=installer;spec.loader.exec_module(installer)

def main():
    assert not (HERE/'installation.json').exists(),'Final installation receipt exists'
    baseline=v.load_json(HERE/'baseline.json')
    installer.ensure_game_stopped(installer.running_game_processes)
    qa_paths=[ROOT/'animations/index/selections/FIRE_3.json',
              ROOT/'animations/index/qa-decisions/FIRE_3/2026-10-11-accepted-fire3-ar0202-fade4-composite-v1.json',
              ROOT/'animations/index/area-qa-decisions/FIRE_3/2026-10-11-accepted-fire3-ar0202-fade4-30fps-v1.json']
    qa_hashes={rel(p):v.sha256_file(p) for p in qa_paths}
    reference=payload(state.game_areas_dir()/'AR0202')
    assert reference==baseline['reference_ar0202_payload'],'Reference AR0202 changed'
    for area in AREAS:
        assert payload(state.game_areas_dir()/area)==baseline['areas'][area]['before'],area+': changed since preparation'
        result=installer.install_area_pack(PACK/area,verify_only=True)
        assert result.status=='verified-only',result
    if '--verify-only' in sys.argv:
        print('VERIFY ONLY: nine complete-area packs ready; game stopped; other resources preserved')
        return
    receipts=[]
    for area in AREAS:
        result=installer.install_area_pack(PACK/area)
        assert result.status=='installed',result
        installer.record_lock(area,PACK/area,installer.DEFAULT_GAME_ROOT)
        assert payload(state.game_areas_dir()/area)==baseline['areas'][area]['after'],area
        assert state.zone_signatures(state.game_areas_dir()/area)==state.load_lock()['areas'][area]['resources'],area
        receipt=dict(area=area,status=result.status,receipt=rel(result.receipt_path),
                     receipt_sha256=v.sha256_file(result.receipt_path),installed_payload_matches=True,
                     sibling_assets_and_runtime_unchanged=True)
        write(HERE/'receipts'/(area+'.json'),receipt);receipts.append(receipt)
        print('INSTALLED',area,'verified; backup',receipt['receipt'],flush=True)
    assert payload(state.game_areas_dir()/'AR0202')==reference,'Reference AR0202 changed'
    for path,digest in qa_hashes.items():assert v.sha256_file(ROOT/path)==digest,path
    # Production/installation update only. Existing immutable map QA decisions are retained.
    with w._animation_authority_lock(ROOT):
        row,rows=w._registry_row(ROOT,'FIRE_3')
        row['notes']=('QA utilisateur AR0202 2026-10-11 acceptée : Apollo8 30 FPS, 28 phases distinctes, durée0,933333s, '
            'fondu seul4px x4/sigma0, cœur et géométrie natifs conservés. Recette byte-identique propagée et installation '
            'vérifiée le 2026-10-11 sur les neuf autres cartes ; FIRE_3 uniforme sur les10cartes/34occurrences. '
            'Autres animations et contrats runtime conservés. Production : '+rel(RUN)+'. Installation : '+rel(HERE/'installation.json')+'. '
            'QA : AR0202 acquis ; aucune nouvelle visite ingame déduite sur les neuf cartes propagées. '
            'La sélection composite conserve les références QA historiques des anciennes versions horsAR0202 ; '
            'leurs réserves temporelles historiques ne décrivent plus la production installée. Release non sélectionnée.')
        w._write_transaction(ROOT,{ROOT/w.REGISTRY_REL:w._render_registry([row if r['resref']=='FIRE_3' else r for r in rows])})
    check=w.check_workspace(ROOT,'FIRE_3');assert check['ok'],check
    write(HERE/'installation.json',dict(schema='bg2-upscale-animation-propagation-install-v1',status='installed-verified',
        created_utc=v.utc_now(),resref='FIRE_3',areas_updated=AREAS,reference_area='AR0202',total_areas=10,total_occurrences=34,
        fps=30,distinct_phases=28,duration_seconds=14/15,inner_fade_x4=4,gaussian_sigma_x4=0,
        run=rel(RUN),pack=rel(PACK),game_root='config://bg2ee_game_root',receipts=receipts,
        source_asset_byte_identical=True,siblings_assets_and_runtime_preserved=True,reference_ar0202_unchanged=True,
        qa_reference=rel(qa_paths[-1]),qa_hashes_preserved=qa_hashes,new_ingame_visits_inferred=False,
        current_installed_version_uniform=True,qa_selection_retains_historical_versions=True,
        authority_check=check,release_status='not-selected'))
    print('DONE: FIRE_3 uniform on 10 maps /34 occurrences; nine installations backed up and verified')

if __name__=='__main__':main()
