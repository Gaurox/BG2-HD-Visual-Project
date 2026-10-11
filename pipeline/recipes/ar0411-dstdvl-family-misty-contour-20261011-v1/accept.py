"""Explicit user QA: all five dust clouds on AR0411, no other area inferred."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import animation_workflow as w
import run_animation_upscale_30fps_v2 as v
from workspace_paths import get_path

TAG='ar0411-dstdvl-family-misty-contour-20261011-v1'
RUN=ROOT/'animations/batches'/TAG
PACK=ROOT/'animations/packs-par-zone'/TAG
A_RUN=ROOT/'animations/ressources/DSTDVL1A/runs/dstdvl1a-misty-contour-native-geometry-20261011-v2'
A_PACK=ROOT/'animations/packs-par-zone/dstdvl1a-misty-contour-native-geometry-20261011-v2'
RECIPE=Path(__file__).resolve().parent

def accept():
    live=get_path('bg2ee_game_root')/'iee-assets/areas/AR0411'
    _,resources=v.validate_v2_pack(PACK/'AR0411')
    assert (live/v.REGISTRY_NAME).read_bytes()==v.registry_v2_from_resources(resources,3)
    for resource in resources:
        for asset in resource['assets']:
            assert hashlib.sha256((live/asset['name']).read_bytes()).hexdigest()==asset['sha256']
    for name in ['DSTDVL1A','DSTDVL1B','DSTDVL1C']:
        run,pack=(A_RUN,A_PACK) if name=='DSTDVL1A' else (RUN,PACK)
        artifact,manifest,manifest_path=w._artifact(ROOT,run)
        source=w._source_pack(ROOT,pack,name,['AR0411'])
        w._verify_embedded_pack(ROOT,manifest,manifest_path)
        w._verify_pack_binding(ROOT,manifest,manifest_path,source,name)
        # A's bytes are still exact in the newer full pack, despite sibling changes.
        _,selected=v.validate_v2_pack(run/'03_runtime_pack')
        assert w._resource_group(resources,name)==w._resource_group(selected,name)
        decision_id='2026-10-11-accepted-'+name.lower()+'-ar0411-misty-contour-v1'
        path=ROOT/'animations/index/area-qa-decisions'/name/(decision_id+'.json')
        decision=dict(schema_version=1,decision_id=decision_id,asset_id='animations:bam:'+name,resref=name,
            status='accepted',result_kind='x4',decision_origin='explicit-user-ingame-qa',decision_date='2026-10-11',
            recorded_at_utc=w.utc_now(),decision='Utilisateur : tous valides, maj le suivi et committe. '+name+
                ' accepte en jeu sur AR0411 : fondu20px x4 + Gaussian sigma4 en bordure, coeur conserve, dimensions/centres et cadence natives conserves. '
                'QA limitee a AR0411 ; autres9zones non modifiees et non validees pour ce correctif. Aucun changement installation ou release dans cette validation.',
            recipe_id=TAG,final_run=artifact,source_pack=source,lineage=w._collect_lineage(ROOT,manifest,manifest_path),tested_areas=['AR0411'])
        decision['$schema']=w.DECISION_SCHEMA_REF
        data,changed=w._prepare_immutable(path,decision,'recorded_at_utc')
        if changed:
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
        errors=[]
        w._validate_decision_record(ROOT,path,name,errors,validate_registry=False)
        assert not errors,errors
    for name in ['DSTDVL2B','DSTDVL2C']:
        w.finalize(ROOT,name,RUN,PACK,['AR0411'],'accepted','2026-10-11',
            'Utilisateur : tous valides, maj le suivi et committe. '+name+
            ' accepte en jeu sur AR0411 apres le meme fondu20px x4 / Gaussian sigma4 que DSTDVL1A. Rendu brumeux accepte ; coeur, dimensions/centres et cadence preserves.',
            decision_id='2026-10-11-accepted-'+name.lower()+'-ar0411-misty-contour-v1',recipe_id=TAG,
            notes='QA ingame AR0411 validee utilisateur 2026-10-11. Contour brumeux : fondu20px x4 + Gaussian sigma4, RGBA premultiplie, coeur preserve. '
                'Dimensions/centres, timeline et cadence conserves. Installation pipeline/recipes/'+TAG+'/installation.json. Aucune integration release.',apply=True)
    _,rows=w._registry_row(ROOT,'DSTDVL1A')
    for row in rows:
        if row['resref'] in ['DSTDVL1A','DSTDVL1B','DSTDVL1C']:
            name=row['resref']
            path='animations/index/area-qa-decisions/'+name+'/2026-10-11-accepted-'+name.lower()+'-ar0411-misty-contour-v1.json'
            assert row['status']=='à-valider'
            row['notes']='QA ingame AR0411 validee utilisateur 2026-10-11 ; decision '+path+'. Fondu20px x4 + Gaussian sigma4 en bordure sur RGBA premultiplie ; coeur, dimensions/centres et cadence conserves. '
            row['notes']+='Run '+(A_RUN if name=='DSTDVL1A' else RUN).relative_to(ROOT).as_posix()+'. '
            row['notes']+='Correctif installe AR0411 uniquement ; autres9zones a propager puis valider, donc statut global a-valider conserve. Aucune release.'
    (ROOT/w.REGISTRY_REL).write_bytes(w._render_registry(rows))
    print('Five AR0411 QA accepted; DSTDVL2B/2C globally complete; DSTDVL1A/B/C partial AR0411 only')

if __name__=='__main__': accept()
