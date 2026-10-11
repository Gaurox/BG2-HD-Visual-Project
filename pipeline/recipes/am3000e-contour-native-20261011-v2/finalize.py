"""Seal the user's acceptance of the corrected AM3000E soft contour on AR3000."""
from build import ROOT,OUT,REF,ID,v,rel
import animation_workflow as workflow
import area_pack_state as state
from workspace_paths import get_path

def main():
    pack=ROOT/'animations/packs-par-zone'/ID;leaf=pack/'AR3000'
    game=get_path('bg2ee_game_root');live=game/'iee-assets/areas/AR3000'
    payload=lambda p:{f.name:v.sha256_file(f) for f in p.iterdir() if f.is_file() and f.name!='manifest.json'}
    assert payload(live)==payload(leaf)
    assert state.zone_signatures(live)==state.load_lock()['areas']['AR3000']['resources']
    source=ROOT/f'animations/ressources/{REF}/runs'/ID
    final=ROOT/f'animations/ressources/{REF}/runs/am3000e-contour-native-accepted-20261011-v1'
    final.mkdir(parents=True,exist_ok=False)
    recipe='ReboutCX x4/PLT_MAGE; Apollo8 30FPS; fondu doux RGBA prémultiplié sigma2x4/canvas2 ; dimensions/centres natifs exacts ; cycles48/36/20,1,6/1,2/0,666667s'
    v.write_json(final/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),
        resrefs=[REF],source_run=rel(source),source_run_manifest_sha256=v.sha256_file(source/'manifest.json'),
        source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
        output_split_root=rel(pack),output_manifest_sha256=v.sha256_file(pack/'manifest.json'),
        tested_areas=['AR3000'],selection_reason='Utilisateur : ok. validé. on passe a FLM2PUR.',recipe=recipe,
        installation_receipt=rel(OUT/'installation.json'),qa_status='accepted-ingame',release_status='not-selected'))
    decision='2026-10-11-accepted-am3000e-native-contour-v1'
    workflow.finalize(ROOT,REF,final,pack,['AR3000'],'accepted','2026-10-11',
        'Utilisateur : ok. validé. on passe a FLM2PUR. AM3000E dernière version corrigée acceptée ingame sur AR3000. '+recipe+'.',
        decision_id=decision,recipe_id=ID,correction_id=ID,
        notes='Lot5 AM3000E validé ingame explicitement : fondu doux corrigé, dimensions/centres natifs restaurés,5occurrences AR3000. '+recipe+'. Autres assets lot5 en attente ; aucune release.',apply=True)
    check=workflow.check_workspace(ROOT,REF);assert check['ok'],check
    v.write_json(ROOT/'pipeline/recipes/am3000e-contour-native-20261011-v2/acceptance.json',dict(
        schema='bg2-upscale-animation-batch-acceptance-v1',status='accepted-ingame',decision_date='2026-10-11',
        decision_origin='explicit-user-ingame-qa',resref=REF,tested_areas=['AR3000'],occurrences=5,final_run=rel(final),
        qa_decision=f'animations/index/qa-decisions/{REF}/{decision}.json',installed_payload_identical=True,
        native_geometry_preserved=True,game_payload_changed=False,release_status='not-selected'))
    print('ACCEPTED AM3000E corrected soft contour /AR3000 /5 occurrences',flush=True)

if __name__=='__main__':main()
