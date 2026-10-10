"""Record explicit final ingame acceptance; historical runs/receipts stay immutable."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
import animation_workflow as workflow
import run_animation_upscale_30fps_v2 as v2
HERE = Path(__file__).resolve().parent
selected = v2.load_json(ROOT/'animations/batches/portails-cinq-selection-20261010-v1/selection.json')
repaired = v2.load_json(ROOT/'animations/batches/portails-deux-correctif-20261010-v1/selection.json')
repair_by_resref = {r['resref']: r for r in repaired['resources']}
renderer = v2.load_json(ROOT/'animations/batches/bdforcew-shift-right-20261010-v3/installation.json')
assert renderer['status'] == 'installed'
old_ohh = ROOT/'animations/index/qa-decisions/OHHPORT/2026-10-10-accepted-ohhport-xbr-apo8-backgroundfix-v1.json'
old_ohh_sha = v2.sha256_file(old_ohh)
areas = {'BDFORCEW':['OH8100'], 'OHDLPORT':['OH5400','OH5500'], 'OHHPORT':['AR0811'],
         'OHRSGATE':['OH4220','OH4230'], 'SPDIMNDR':['AR6108']}
recipes = {'BDFORCEW':'reboutcx-apo8-splinefit1-inner16-wed16-shift6',
           'OHDLPORT':'xbr2-blend-nearest2-apo8-premul',
           'OHHPORT':'xbr2-blend-nearest2-apo8-backgroundfix-premul',
           'OHRSGATE':'seedvr7b-lab-apo8-inner16-premul',
           'SPDIMNDR':'seedvr7b-lab-apo8-linear-inner2-premul'}
corrections = {'BDFORCEW':'splinefit1-inner16-native-wed-guard4-fade16-postmask-dx6',
               'OHDLPORT':'premultiply-once',
               'OHHPORT':'native-frame2-opaque-black-background-transparent',
               'OHRSGATE':'innerfeather16-premultiply',
               'SPDIMNDR':'linear-cycles-0-2-3-4-innerfeather2-premultiply'}
results = []
for chosen in selected['resources']:
    resref = chosen['resref']; current = repair_by_resref.get(resref, chosen)
    pack = ('animations/packs-par-zone/portails-deux-correctif-20261010-v1-complete'
            if resref in repair_by_resref else selected['complete_pack'])
    source_run = current.get('spline_run') or current.get('final_run') or current['temporal_run']
    run = f'animations/ressources/{resref}/runs/{resref.lower()}-portails-accepted-20261010-v1'
    manifest = dict(schema='bg2-upscale-animation-final-selection-v1', status='completed',
        created_utc=v2.utc_now(), resrefs=[resref], source_run=source_run,
        source_run_manifest_sha256=v2.sha256_file(ROOT/source_run/'manifest.json'),
        source_pack=current['final_split'],
        source_pack_manifest_sha256=v2.sha256_file(ROOT/current['final_split']/'manifest.json'),
        output_split_root=pack, output_manifest_sha256=v2.sha256_file(ROOT/pack/'manifest.json'),
        recipe=current['recipe'], selection_reason='Utilisateur : « ok le lot est validé. MAJ le suivi et committe en l’état ».',
        runtime_contract=dict(scale=4, fps=30, native_frame_centres_preserved=True,
                              area_coordinates_preserved=True))
    if resref == 'BDFORCEW':
        manifest['runtime_contract'].update(non_vanilla_visual_placement=True,
            occurrences=[[2286,820],[2350,866]], post_mask_dx_x1=6, post_mask_dy_x1=0,
            native_wed_guard_x4=4, native_wed_feather_x4=16,
            renderer_dll_sha256=renderer['dll_sha256'],
            renderer_receipt=renderer['renderer_receipt'],
            renderer_installation='animations/batches/bdforcew-shift-right-20261010-v3/installation.json')
    path = ROOT/run/'manifest.json'; path.parent.mkdir(parents=True, exist_ok=True)
    assert not path.exists(), 'Accepted descriptors are immutable: '+str(path)
    v2.write_json(path, manifest)
    decision = ('Validation ingame explicite utilisateur du lot final de cinq animations. '+
                ('BDFORCEW/OH8100 : premier rendu lissé restauré ; spline Fit1/inner16, '+
                 'WED guard4/fade16 x4 ; deux dessins déplacés +6 x1 à droite après masque WED, '+
                 'état visuel non vanilla explicitement demandé ; DLL '+renderer['dll_sha256']+'. '
                 if resref == 'BDFORCEW' else '')+
                'Recette retenue : '+recipes[resref]+'. Aucun changement release.')
    kwargs = dict(decision_id=f'2026-10-10-accepted-{resref.lower()}-portails-final-v1',
                  recipe_id=recipes[resref], correction_id=corrections[resref], notes=decision)
    workflow.finalize(ROOT, resref, run, pack, areas[resref], 'accepted', '2026-10-10', decision, **kwargs)
    result = workflow.finalize(ROOT, resref, run, pack, areas[resref], 'accepted', '2026-10-10',
                               decision, apply=True, **kwargs)
    results.append(dict(resref=resref, areas=areas[resref], final_run=run,
                        decision_id=result['decision_id'], recipe_id=recipes[resref]))
    print(resref+' accepted / selection and registry updated', flush=True)
assert v2.sha256_file(old_ohh) == old_ohh_sha
v2.write_json(HERE/'acceptance.json', dict(schema='bg2-upscale-animation-batch-acceptance-v1',
    status='accepted-ingame', decision_date='2026-10-10', recorded_at_utc=v2.utc_now(),
    decision_origin='explicit-user-ingame-qa', resources=results,
    renderer_dll_sha256=renderer['dll_sha256'], renderer_receipt=renderer['renderer_receipt'],
    renderer_installation='animations/batches/bdforcew-shift-right-20261010-v3/installation.json',
    renderer_installation_sha256=v2.sha256_file(ROOT/'animations/batches/bdforcew-shift-right-20261010-v3/installation.json'),
    historical_OHHPORT_approval_preserved=True, release='not-selected'))
