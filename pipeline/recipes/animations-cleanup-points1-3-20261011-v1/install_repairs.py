"""Transactional installs; exact-payload lock repairs without rewriting the game."""
from common import *
from prepare_repairs import INSTALL,LOCK_ONLY
import importlib.util
spec=importlib.util.spec_from_file_location('cleanup_area_installer',ROOT/'pipeline/area-animation-area-test/area_animation_area_test.py')
installer=importlib.util.module_from_spec(spec);sys.modules[spec.name]=installer;spec.loader.exec_module(installer)

def main():
    assert not (HERE/'repair-installation.json').exists()
    baseline=load(HERE/'repair-baseline.json');qa_hashes={rel(p):digest(p) for p in (ROOT/'animations/index/qa-decisions').glob('*/*.json')}
    installer.ensure_game_stopped(installer.running_game_processes)
    for area in INSTALL+LOCK_ONLY:
        assert fresh_payload(state.game_areas_dir()/area)==baseline['areas'][area]['before'],area
    for area in INSTALL:installer.install_area_pack(REPAIR/area,verify_only=True)
    if '--verify-only' in sys.argv:print('VERIFIED: two installations ready; four lock-only snapshots match game');return
    receipts=[]
    for area in INSTALL:
        result=installer.install_area_pack(REPAIR/area);assert result.status=='installed'
        # Store exact leaf paths, never stringify a multi-area root's source metadata.
        state.record_zone(area,state.game_areas_dir(),leaf=REPAIR/area)
        assert fresh_payload(state.game_areas_dir()/area)==baseline['areas'][area]['after'],area
        item=dict(area=area,status=result.status,receipt=rel(result.receipt_path),receipt_sha256=digest(result.receipt_path))
        write(HERE/'repair-receipts'/(area+'.json'),item);receipts.append(item)
        print('INSTALLED',area,'exact approved assets; backed up',flush=True)
    for area in LOCK_ONLY:
        assert fresh_payload(state.game_areas_dir()/area)==baseline['areas'][area]['before'],area
        state.record_zone(area,state.game_areas_dir(),leaf=REPAIR/area)
        assert fresh_payload(state.game_areas_dir()/area)==baseline['areas'][area]['before'],area
        print('LOCK FIXED',area,'game unchanged',flush=True)
    for name,expected in qa_hashes.items():assert v.sha256_file(ROOT/name)==expected,name
    with workflow._animation_authority_lock(ROOT):
        rr,_=workflow._read_registry(ROOT)
        for r in rr:
            if r['resref'] in ['FISH1L','FISH2L','FISH2S','FISH3S']:
                r['notes']+=' Installation AR5000 de la version déjà acceptée réalisée et vérifiée le2026-10-11 ; QA acquise inchangée. Reçu '+rel(HERE/'repair-installation.json')+'.'
            elif r['resref'] in ['AM3021D','AM3021E','AM3021F']:
                r['notes']+=' Version exacte déjà acceptée réinstallée AR3021 le2026-10-11 ; QA acquise inchangée. Reçu '+rel(HERE/'repair-installation.json')+'.'
        workflow._write_transaction(ROOT,{ROOT/workflow.REGISTRY_REL:workflow._render_registry(rr)})
    write(HERE/'repair-installation.json',dict(schema='bg2-upscale-animation-cleanup-installation-v1',status='completed',
        created_utc=v.utc_now(),installed_areas=INSTALL,lock_only_areas=LOCK_ONLY,receipts=receipts,
        game_root='config://bg2ee_game_root',new_qa_inferred=False,prior_qa_hashes_preserved=qa_hashes,release_mutation=False))

if __name__=='__main__':main()
