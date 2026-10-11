"""Seal the user's final lot2 choices; retain historical production/install evidence."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import animation_workflow as workflow
import run_animation_upscale_30fps_v2 as v
import area_pack_state as state
from workspace_paths import get_path

TAG = 'lot2-five-effects-accepted-20261011-v1'
GAME = get_path('bg2ee_game_root')
JOBS = {
    'AM4000Z': ('AR4000', 'lot2-seedvr-selected-20261011-v1-complete',
                'am4000z-lot2-seedvr-selected-20261011-v1', 'lot2-seedvr-selected-20261011-v1',
                'SeedVR2 7B INT8/LAB x4 seed20261011; Apollo8 30fps; premultiply once; sans fondu', 10),
    'EYESRED1': ('AR0329', 'lot2-seedvr-selected-20261011-v1-complete',
                 'eyesred1-lot2-seedvr-selected-20261011-v1', 'lot2-seedvr-selected-20261011-v1',
                 'SeedVR2 7B INT8/LAB x4 seed20261011; cadence native; premultiply once; sans fondu', 1),
    'BUBBLEA': ('AR2903', 'lot2-small-effects-20261011-v1-complete',
                'bubblea-lot2-small-effects-20261011-v1', 'lot2-small-effects-20261011-v1',
                'xBR2 blend puis nearest2; Apollo8 30fps preserve-segmented-holds; pauses exactes; premultiply once', 3),
    'WTRBODY1': ('AR0502', 'wtrbody1-xbr-apo8-collapse-20261011-v1',
                 'wtrbody1-xbr-apo8-collapse-20261011-v1', 'wtrbody1-xbr-apo8-collapse-20261011-v1',
                 'xBR2 puis nearest2; 20frames -> 10poses uniques; Apollo8 7.5->30fps; 40frames distinctes; boucle20/15s; 10ancres conservees', 1),
}


def rel(path):
    return path.relative_to(ROOT).as_posix()


def payload(path):
    return {p.name: v.sha256_file(p) for p in path.iterdir()
            if p.is_file() and p.name != 'manifest.json'}


def main():
    lock = state.load_lock()
    checks = []
    # AM0504SB already accepted explicitly; do not replace that immutable decision.
    purple = ROOT/'animations/packs-par-zone/lot2-small-effects-20261011-v1-complete/AR0504'
    assert payload(purple) == payload(GAME/'iee-assets/areas/AR0504')
    assert workflow.check_workspace(ROOT, 'AM0504SB')['ok']
    for ref, (area, pack_id, source_id, installation_id, recipe, count) in JOBS.items():
        pack = ROOT/'animations/packs-par-zone'/pack_id
        leaf = pack/area
        assert payload(leaf) == payload(GAME/'iee-assets/areas'/area)
        assert state.zone_signatures(GAME/'iee-assets/areas'/area) == lock['areas'][area]['resources']
        historical = ROOT/'animations/ressources'/ref/'runs'/source_id
        seed = ref in ('AM4000Z', 'EYESRED1')
        # Original SeedVR preview wrappers omitted a lineage hash. Bind the immutable
        # spatial run directly; preserve those wrappers and the unaccepted first attempt.
        source = ROOT/'animations/batches/lot2-seedvr7b-lab-x4-20261011-v1' if seed else historical
        suffix = 'v2' if seed else 'v1'
        final = ROOT/'animations/ressources'/ref/'runs'/(ref.lower()+'-lot2-selection-accepted-20261011-'+suffix)
        if not final.exists():
            final.mkdir(parents=True)
            v.write_json(final/'manifest.json', dict(
                schema='bg2-upscale-animation-final-selection-v1', status='completed', created_utc=v.utc_now(),
                resrefs=[ref], source_run=rel(source), source_run_manifest_sha256=v.sha256_file(source/'manifest.json'),
                historical_selection=rel(historical), historical_selection_manifest_sha256=v.sha256_file(historical/'manifest.json'),
                source_pack=rel(leaf), source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
                output_split_root=rel(pack), output_manifest_sha256=v.sha256_file(pack/'manifest.json'),
                selection_reason='Utilisateur : ok lot 2 validé. MAJ le suivi et committe', tested_areas=[area],
                recipe=recipe, installation_receipt='animations/batches/'+installation_id+'/installation.json'))
        decision_id='2026-10-11-accepted-'+ref.lower()+'-lot2-final-v1'
        workflow.finalize(ROOT, ref, final, pack, [area], 'accepted', '2026-10-11',
            'Utilisateur : ok lot 2 validé. MAJ le suivi et committe. '+ref+' accepte en jeu sur '+area+
            ' ('+str(count)+' occurrences); recette finale : '+recipe+'.',
            decision_id=decision_id, recipe_id=ref.lower()+'-lot2-final-20261011-v1',
            correction_id=installation_id,
            notes='Lot2 QA utilisateur acceptee 2026-10-11 sur '+area+' ('+str(count)+' occurrences). '+recipe+
                  '. Recu animations/batches/'+installation_id+'/installation.json; siblings conserves; aucune integration release.',
            apply=True)
        result=workflow.check_workspace(ROOT, ref)
        assert result['ok'], result
        checks.append(dict(resref=ref, area=area, occurrences=count, recipe=recipe,
            final_run=rel(final), pack=rel(leaf), installed_payload_matches=True,
            qa_decision='animations/index/qa-decisions/'+ref+'/'+decision_id+'.json'))
        print('ACCEPTED', ref, area, flush=True)
    checks.insert(0, dict(resref='AM0504SB', area='AR0504', occurrences=6,
        recipe='ReboutCX x4; Apollo8 30fps; inner12; premultiply once',
        installed_payload_matches=True,
        qa_decision='animations/index/qa-decisions/AM0504SB/2026-10-11-accepted-am0504sb-lot2-reboutcx-v1.json'))
    batch=ROOT/'animations/batches'/TAG
    batch.mkdir(parents=True, exist_ok=False)
    v.write_json(batch/'manifest.json', dict(schema='bg2-upscale-animation-batch-final-qa-v1',
        status='accepted', recorded_utc=v.utc_now(), decision_origin='explicit-user-ingame-qa',
        decision='Utilisateur : ok lot 2 validé. MAJ le suivi et committe',
        asset_count=5, area_count=5, occurrences=21, resources=checks, release_status='not-selected'))
    print('DONE: lot2 accepted, 5 assets / 5 maps / 21 occurrences; release unchanged')


if __name__ == '__main__':
    main()
