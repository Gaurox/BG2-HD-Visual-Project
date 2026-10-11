"""Migrate acquired QA with exact historical bytes/contract; never accept changed live versions."""
from legacy_plan import *
import io

def archive_evidence(items):
    result=[]
    for e in items:
        p=path(e['path']);suffix=p.suffix;dest=HERE/'historical-evidence'/(e['sha256']+suffix)
        if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
        assert digest(dest)==e['sha256']
        result.append(dict(e,archived_path=rel(dest)))
    return result

def main():
    baseline=HERE/'historical-registry-rows.json'
    if not baseline.exists():
        original=[r for r in rows() if r['resref'] in PLAN]
        assert len(original)==43 and all(not r['qa_decision'] for r in original)
        write(baseline,dict(schema='bg2-upscale-historical-qa-registry-snapshot-v1',created_utc=v.utc_now(),
            registry_path=workflow.REGISTRY_REL.as_posix(),registry_sha256=digest(ROOT/workflow.REGISTRY_REL),rows=original))
    original=load(baseline)['rows'];outcomes=[]
    old_qa=load(HERE/'repair-installation.json')['prior_qa_hashes_preserved']
    for row in original:
        ref=row['resref'];areas=row['areas'].split(';');tag=ref.lower()+'-historical-qa-bound-20261011-v1'
        qa_root=PACKS/tag;run=ROOT/'animations/ressources'/ref/'runs'/tag;decision_id='2026-10-11-preserved-historical-'+ref.lower()+'-v1'
        evidence=[];installed=[];contracts=[]
        for area in areas:
            rr,sources,source,ee=legacy_resources(ref,area);evidence+=archive_evidence(ee)
            leaf=qa_root/area
            if not leaf.exists():write_leaf(leaf,area,rr,sources,3,dict(kind='exact historical acquired QA snapshot',
                source_manifest=rel(source/'manifest.json'),source_manifest_sha256=digest(source/'manifest.json'),
                texture_change=False,timing_change=False,legacy_v1_encoding_only=ref.startswith('AM0205'),
                installation_forbidden='QA snapshot is scoped to one resref; compose a complete area before installing'))
            assert workflow._resource_group(resources(leaf),ref)==workflow._resource_group(rr,ref)
            if same_live(leaf,rr,area):installed.append(area)
            contracts.append(dict(area=area,resources=[dict(frame_count=r['frame_count'],playback_mode=r['playback_mode'],
                native_fps=r['native_fps'],target_fps=r['target_fps'],variant_index=r.get('variant_index',0),
                position=r.get('position'),texture_hashes=[a['sha256'] for a in r['assets']]) for r in rr]))
        if not (qa_root/'manifest.json').exists():write_index(qa_root,areas,'asset-scoped QA snapshot; historical approval migration only; never an area installation')
        discrepancy=sorted(set(areas)-set(installed));clarification=''
        if ref.startswith('AM0205') and ref!='AM0205E':
            clarification=' QA acquise conservée uniquement sur Native 27 phases à 15 FPS (2026-08-21). Installation actuelle : TimedTimeline 54 phases à 30 FPS, approbation ingame exacte non retrouvée ; choix de version/QA ciblée requis.'
        if ref=='AM0604A':
            clarification=' QA acquise conservée uniquement sur ar0604-apo8-x4-30fps-v2 sans correction alpha. Installation actuelle issue de ar0604-spline-fit2-alpha-30fps-v2 ; notes historiques rejettent les essais alpha, aucune approbation exacte retrouvée ; choix de version/QA ciblée requis.'
        if ref=='AM0602F':
            clarification=' Note 18 phases/30 FPS antérieure conservée comme historique ; sélection 9 phases Native confirmée par la QA AR0602 du 2026-09-05, octets et contrat identiques, aucun nouveau test déduit.'
        if not (run/'manifest.json').exists():
            write(run/'manifest.json',dict(schema='bg2-upscale-historical-qa-binding-run-v1',status='completed',created_utc=v.utc_now(),
                resrefs=[ref],operation='formalize existing user ingame approvals without graphical reprocessing',
                output_split_root=rel(qa_root),output_manifest_sha256=digest(qa_root/'manifest.json'),
                registry_evidence=dict(path=rel(baseline),sha256=digest(baseline),resref=ref,notes=row['notes']),
                historical_evidence=evidence,acquired_qa_date=PLAN[ref]['date'],new_ingame_qa=False,
                installation_matches_accepted_areas=installed,installation_discrepancy_areas=discrepancy,clarification=clarification,
                runtime_contracts=contracts,release_mutation=False))
        text='Formalisation le 2026-10-11 de la validation utilisateur historique déjà acquise ; aucune nouvelle visite ingame. Octets, géométrie, cycles, cadence et variantes conservés dans le snapshot QA ; propagation de la même ressource aux zones inventoriées par identité, sans déduire de visites exhaustives. Source : '+rel(baseline)+'.'+clarification+' Notes acquises : '+row['notes']
        decision=ROOT/'animations/index/qa-decisions'/ref/(decision_id+'.json')
        if not decision.exists():
            workflow.finalize(ROOT,ref,run,qa_root,areas,'accepted',PLAN[ref]['date'],text,decision_id=decision_id,
                recipe_id=TAG,notes=row['notes']+' Formalisation historique 2026-10-11 : '+rel(run/'manifest.json')+'.'+clarification,apply=True)
        checked=workflow.check_workspace(ROOT,ref);assert not checked['errors'],checked
        outcomes.append(dict(resref=ref,decision=rel(decision),decision_sha256=digest(decision),acquired_qa_date=PLAN[ref]['date'],
            selected_run=rel(run),qa_pack=rel(qa_root),accepted_contracts=contracts,
            installed_identical_areas=installed,installed_different_areas=discrepancy,clarification=clarification,
            check_errors=checked['errors']))
        print('BOUND',ref,'exact historic QA; live matches' if not discrepancy else 'historic QA retained; live discrepancy '+','.join(discrepancy),flush=True)
    for name,h in old_qa.items():assert v.sha256_file(ROOT/name)==h,name
    alpha=ROOT/'animations/index/animation_alpha_corrections.csv';lines=alpha.read_bytes().decode('utf8').splitlines(keepends=True)
    fields=next(csv.reader([lines[0]]));changed=[]
    for line in lines:
        if line.split(',',1)[0] in ['AM0205A','AM0205B','AM0205C','AM0205D']:
            r=dict(zip(fields,next(csv.reader([line]))))
            r['notes']+=' Suivi 2026-10-11 : QA alpha/cadence acquise sur 27 phases Native conservée ; installation actuelle 54 phases TimedTimeline30 distincte, QA ingame exacte non retrouvée. Voir docs/validation/animations-cleanup-status-20261011-v2.json.'
            buf=io.StringIO();writer=csv.DictWriter(buf,fieldnames=fields,lineterminator='\n');writer.writerow(r);line=buf.getvalue()
        changed.append(line)
    alpha.write_bytes(''.join(changed).encode('utf8'))
    write(HERE/'historical-qa-migration.json',dict(schema='bg2-upscale-historical-qa-migration-v1',status='completed',created_utc=v.utc_now(),
        resources=43,new_ingame_qa=False,all_prior_qa_hashes_preserved=True,release_mutation=False,
        installed_identical_resources=sum(not x['installed_different_areas'] for x in outcomes),
        ambiguous_current_versions=[x['resref'] for x in outcomes if x['installed_different_areas']],results=outcomes))

if __name__=='__main__':main()
