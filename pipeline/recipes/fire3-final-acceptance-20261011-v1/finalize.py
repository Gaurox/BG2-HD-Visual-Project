"""Seal final explicit all-map FIRE_3 QA; no game or release mutation."""
from pathlib import Path
import csv, io, json, sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import animation_workflow as w
import area_pack_state as state
import combine_area_pack_splits as combine
import run_animation_upscale_30fps_v2 as v

TAG='fire3-fade4-30fps-all-maps-accepted-20261011-v1'
PACK=ROOT/'animations/packs-par-zone'/TAG
RUN=ROOT/'animations/ressources/FIRE_3/runs'/TAG
REPORT=HERE/'acceptance.json'
DECISION='2026-10-11-accepted-fire3-fade4-30fps-all-maps-v1'

def rel(p):return p.resolve().relative_to(ROOT).as_posix()

def payload(p):
    return {f.name:v.sha256_file(f) for f in p.iterdir() if f.is_file() and f.name!='manifest.json'}

def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as out:
        json.dump(data,out,ensure_ascii=False,indent=2);out.write('\n')

def main():
    assert not REPORT.exists() and not RUN.exists() and not PACK.exists()
    source=ROOT/'animations/ressources/FIRE_3/runs/fire3-aura-fade4-all-areas-20261011-v1'
    roots=[ROOT/'animations/packs-par-zone/fire3-aura-fade4-30fps-20261011-v1',
           ROOT/'animations/packs-par-zone/fire3-aura-fade4-all-areas-20261011-v1']
    combine.combine(roots,PACK,False)
    row,_=w._registry_row(ROOT,'FIRE_3');areas=sorted(row['areas'].split(';'))
    lock_hash=v.sha256_file(state.LOCK_PATH)
    old_qa={rel(p):v.sha256_file(p) for p in (ROOT/'animations/index/qa-decisions/FIRE_3').glob('*.json')}
    old_qa.update({rel(p):v.sha256_file(p) for p in (ROOT/'animations/index/area-qa-decisions/FIRE_3').glob('*.json')})
    installed=[];reference=None
    for area in areas:
        live=state.game_areas_dir()/area;leaf=PACK/area
        assert payload(live)==payload(leaf),area+': installed differs from approved pack'
        assert state.zone_signatures(live)==state.load_lock()['areas'][area]['resources'],area
        _,resources=v.validate_v2_pack(leaf)
        r=next(r for r in resources if r['resref']=='FIRE_3')
        assert r['target_fps']==dict(numerator=30,denominator=1) and r['frame_count']==28
        assert len(set(r['cycles'][0]['timeline_frame_indices']))==28
        assert len(r['cycles'][0]['native_frame_indices'])/15==len(r['cycles'][0]['timeline_frame_indices'])/30
        normalized=w._resource_group(resources,'FIRE_3')
        if reference is None:reference=normalized
        assert normalized==reference,area+': FIRE_3 variant differs'
        installed.append(dict(area=area,installed_payload_identical=True,qa_treatment_uniform=True))
    write(RUN/'manifest.json',dict(schema='bg2-upscale-animation-final-selection-v1',status='completed',created_utc=v.utc_now(),
        resrefs=['FIRE_3'],source_run=rel(source),source_run_manifest_sha256=v.sha256_file(source/'manifest.json'),
        output_split_root=rel(PACK),output_manifest_sha256=v.sha256_file(PACK/'manifest.json'),
        qa_status='accepted-ingame-all-ten-maps',tested_areas=areas,
        user_statement="oui c'est bon je valide tout. MAJ le suivi si necessaire et committe.",
        recipe='Apollo8 30FPS;28 distinct phases;14/15s; aura-only fade4x4/sigma0; bright core/native geometry preserved',
        installation_receipts=['pipeline/recipes/fire3-aura-fade4-30fps-20261011-v1/installation.json',
                               'pipeline/recipes/fire3-aura-fade4-all-areas-20261011-v1/installation.json'],release_status='not-selected'))
    text=('Utilisateur : oui c’est bon je valide tout. QA FIRE_3 acceptée sur les neuf cartes propagées ; '
          'QA AR0202 antérieure conservée. Dix cartes/34 occurrences : Apollo8 30 FPS, 28 phases distinctes, '
          'durée 14/15 s, aura fondu seul4px x4 sans flou. Réserve temporelle clôturée sur toutes les zones. '
          'Fichiers et contrats installés vérifiés ; autres assets préservés. Aucune intégration release.')
    w.finalize(ROOT,'FIRE_3',RUN,PACK,areas,'accepted','2026-10-11',text,decision_id=DECISION,
        recipe_id=TAG,correction_id='fire3-aura-fade4-all-areas-20261011-v1',
        notes='QA ingame utilisateur finale 2026-10-11 acceptée sur10cartes/34occurrences. Apollo8 30FPS,28phases distinctes, '
            '0,933333s ; aura fondu seul4px x4/sigma0, cœur et géométrie natifs préservés. Réserve temporelle clôturée partout. '
            'Installation uniforme vérifiée, autres animations conservées. Décision : animations/index/qa-decisions/FIRE_3/'+DECISION+'.json. '
            'Détails : '+rel(REPORT)+'. Release non sélectionnée.',apply=True)
    # Append the final all-area scope; preserve earlier catalogue bytes verbatim.
    path=ROOT/'animations/index/animation_alpha_corrections.csv'
    fields=next(csv.reader(io.StringIO(path.read_text(encoding='utf-8'))))
    data=dict(resref='FIRE_3',areas=';'.join(areas),element='34 flammes',correction_id='fire3-aura-fade4-all-areas-20261011-v1',
        alpha_operations='aura-only-inner-fade;loop-wide-core-protection',inner_radius_x4='4',canvas_radius_x4='0',canvas_edges='none',
        rgb_policy='existing-premultiplied-RGBA-times-fade-once',status='validated-installed',validated_date='2026-10-11',prototype=rel(RUN),
        notes='QA finale explicite utilisateur acceptée sur les10cartes.28phases distinctes/30FPS,14/15s ; fondu seul4px x4/sigma0. '
              'Réserve temporelle clôturée partout ; anciennes décisions et installations conservées. '+rel(REPORT))
    out=io.StringIO(newline='');csv.DictWriter(out,fieldnames=fields,lineterminator='\n').writerow(data)
    with w._animation_authority_lock(ROOT):
        old=path.read_bytes();tmp=HERE/'alpha-catalogue.partial';tmp.write_bytes(old+out.getvalue().encode('utf-8'));tmp.replace(path)
    for path,digest in old_qa.items():assert v.sha256_file(ROOT/path)==digest,path
    assert v.sha256_file(state.LOCK_PATH)==lock_hash
    check=w.check_workspace(ROOT,'FIRE_3');assert check['ok'],check
    write(REPORT,dict(schema='bg2-upscale-animation-final-acceptance-v1',status='accepted-ingame',decision_date='2026-10-11',
        decision_origin='explicit-user-ingame-qa',user_statement="oui c'est bon je valide tout. MAJ le suivi si necessaire et committe.",
        resref='FIRE_3',areas=areas,occurrences=34,fps=30,distinct_phases=28,inner_fade_x4=4,gaussian_sigma_x4=0,
        temporal_reserve_closed_all_areas=True,final_run=rel(RUN),qa_pack=rel(PACK),
        qa_decision='animations/index/qa-decisions/FIRE_3/'+DECISION+'.json',installed_checks=installed,
        old_qa_hashes_preserved=old_qa,authority_check=check,game_payload_changed=False,release_status='not-selected'))
    print('ACCEPTED: FIRE_3 10 maps/34 occurrences; temporal reserve closed; current selection matches installed version')

if __name__=='__main__':main()
