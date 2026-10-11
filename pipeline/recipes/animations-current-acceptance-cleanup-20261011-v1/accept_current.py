"""Seal the five explicitly accepted installed versions without replacing game files."""
from pathlib import Path
import sys,copy,csv,io
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/recipes/animations-cleanup-points1-3-20261011-v1'))
from common import *
HERE=Path(__file__).resolve().parent
TAG='animations-current-acceptance-cleanup-20261011-v1'
PACK=ROOT/'animations/packs-par-zone/animations-five-current-accepted-20261011-v1'
BASE=ROOT/'animations/packs-par-zone/combined-20260904-fpit1s-contour-fondu-J'
TARGETS={'AM0205A':'AR0205','AM0205B':'AR0205','AM0205C':'AR0205','AM0205D':'AR0205','AM0604A':'AR0604'}

def main():
    assert not (HERE/'acceptance.json').exists()
    oldqa={rel(p):digest(p) for p in (ROOT/'animations/index/qa-decisions').glob('*/*.json')}
    oldrows={r['resref']:r for r in rows()};snapshots={}
    for area in sorted(set(TARGETS.values())):
        leaf=BASE/area;rr=resources(leaf);verify_assets(leaf,rr)
        assert same_live(leaf,rr,area),area+': installed version changed since user QA'
        live=state.game_areas_dir()/area;before=fresh_payload(live);version=registry_version(live)
        write_leaf(PACK/area,area,rr,source_assets(leaf,rr),version,dict(kind='exact installed user-accepted version',
            source_manifest=rel(leaf/'manifest.json'),source_manifest_sha256=digest(leaf/'manifest.json'),
            user_decision='tout ce que je viens de voir ingame est ok. a valider proprement et garder.',game_mutation=False))
        assert fresh_payload(PACK/area)==before,area
        snapshots[area]=dict(payload_sha256=before,registry_version=version,pack=rel(PACK/area))
    write_index(PACK,sorted(snapshots),'complete area snapshots of the explicitly accepted installed versions; game unchanged')
    decisions=[]
    for ref,area in TARGETS.items():
        tag=ref.lower()+'-current-ingame-accepted-20261011-v1';run=ROOT/'animations/ressources'/ref/'runs'/tag
        rr=resources(PACK/area,ref);old=oldrows[ref]
        if ref.startswith('AM0205'):
            assert rr[0]['frame_count']==54 and rr[0]['playback_mode']=='TimedTimeline'
            description='Pod x4, canvas feather32 x4, Apollo8 TimedTimeline30 FPS, 54 phases, boucle1.8s. Version actuellement installée vue et acceptée explicitement le2026-10-11 ; ancienne QA Native27/15 FPS conservée comme historique.'
            correction=ref.lower()+'-canvas32-apo8-30fps-accepted-20261011-v1'
        else:
            assert rr[0]['frame_count']==14 and rr[0]['playback_mode']=='TimedTimeline'
            description='Fontaine x4 Apollo8 TimedTimeline30 FPS, 14 phases ; masque manuel spline-fit2 multiplié dans alpha, RGB inchangé. Version actuellement installée vue et acceptée explicitement le2026-10-11. Les refus alpha de2026-08-23 restent historiques et ne décrivent pas cette nouvelle décision.'
            correction='am0604a-spline-fit2-alpha-30fps-accepted-20261011-v1'
        write(run/'manifest.json',dict(schema='bg2-upscale-installed-animation-acceptance-run-v1',status='completed',created_utc=v.utc_now(),
            resrefs=[ref],output_split_root=rel(PACK),output_manifest_sha256=digest(PACK/'manifest.json'),
            operation='seal exact installed version explicitly accepted ingame by user',
            prior_qa_decision=old['qa_decision'],prior_qa_sha256=digest(path(old['qa_decision'])),
            resources=copy.deepcopy(rr),description=description,new_ingame_qa=True,game_mutation=False,release_mutation=False))
        decision_id='2026-10-11-accepted-current-'+ref.lower()+'-v1'
        workflow.finalize(ROOT,ref,run,PACK,[area],'accepted','2026-10-11',
            'Utilisateur : tout ce que je viens de voir ingame est ok. a valider proprement et garder. '+description,
            decision_id=decision_id,recipe_id=TAG,correction_id=correction,
            notes=description+' Écart version/installé fermé. Historique avant confirmation : '+old['notes'],apply=True)
        checked=workflow.check_workspace(ROOT,ref);assert not checked['errors'],checked
        decisions.append(dict(resref=ref,area=area,run=rel(run),decision=rel(ROOT/'animations/index/qa-decisions'/ref/(decision_id+'.json')),
            check_errors=checked['errors'],frame_count=rr[0]['frame_count'],fps=30))
    for area,record in snapshots.items():
        assert fresh_payload(state.game_areas_dir()/area)==record['payload_sha256']
        state.record_zone(area,state.game_areas_dir(),leaf=PACK/area)
    for p,h in oldqa.items():assert v.sha256_file(path(p))==h,p
    alpha=ROOT/'animations/index/animation_alpha_corrections.csv';lines=alpha.read_bytes().decode('utf8').splitlines(keepends=True)
    fields=next(csv.reader([lines[0]]));new=[]
    for line in lines:
        ref=line.split(',',1)[0]
        if ref in TARGETS:
            r=dict(zip(fields,next(csv.reader([line]))));r.update(correction_id=ref.lower()+'-canvas32-apo8-30fps-accepted-20261011-v1',
                status='validated-installed',validated_date='2026-10-11',prototype=next(x['run'] for x in decisions if x['resref']==ref),
                notes='Version installée acceptée ingame le2026-10-11 : 54 phases/30 FPS, canvas32 x4, RGB inchangé. Écart temporel fermé ; ancienne QA27/15 FPS conservée sous qa-decisions comme historique.')
            b=io.StringIO();csv.DictWriter(b,fieldnames=fields,lineterminator='\n').writerow(r);line=b.getvalue()
        new.append(line)
    r=dict.fromkeys(fields,'');r.update(resref='AM0604A',areas='AR0604',element='fontaine',
        correction_id='am0604a-spline-fit2-alpha-30fps-accepted-20261011-v1',alpha_operations='manual-grayscale-spline-fit2-mask',
        inner_radius_x4='0',canvas_radius_x4='0',canvas_edges='none',rgb_policy='byte-identical',status='validated-installed',
        validated_date='2026-10-11',prototype=next(x['run'] for x in decisions if x['resref']=='AM0604A'),
        notes='Masque484x408 x4, SHA5933f08c6ba0fd752219bef9068d019c65c984cc4bffb986e2c56ea03233a977 ; alpha_final=alpha_source*masque/255 sur14 phases/30 FPS. Acceptation explicite de la version installée le2026-10-11 ; anciens refus alpha conservés comme historique.')
    b=io.StringIO();csv.DictWriter(b,fieldnames=fields,lineterminator='\n').writerow(r);new.append(b.getvalue());alpha.write_bytes(''.join(new).encode('utf8'))
    write(HERE/'acceptance.json',dict(schema='bg2-upscale-five-current-animation-acceptance-v1',status='accepted',created_utc=v.utc_now(),
        user_decision='tout ce que je viens de voir ingame est ok. a valider proprement et garder. supprimer toutes run non utilisées. mettre au propre le suivi',
        decisions=decisions,areas=snapshots,all_prior_qa_hashes_preserved=oldqa,game_mutation=False,release_mutation=False,remaining_ambiguities=[]))
    print('ACCEPTED: AM0205A/B/C/D and AM0604A; exact installed versions; game files unchanged; five ambiguities closed')

if __name__=='__main__':main()
