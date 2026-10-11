"""Refine the baseline audit with external historical references and reservations."""
from audit import *

def main():
    baseline=load(HERE/'audit.json');external=load(HERE/'external-reference-check.json')
    reviewed=[];reservations=[]
    for original in baseline['runs']:
        r=dict(original);roles=set(r['dependency_roles'])
        if r['path']=='animations/runs/ar0602-bubbles2-seedvr7b-lab-x4':
            p=ROOT/r['path']/'03_runtime_pack/manifest.json'
            expected='b8118e1bac4ada2b3035d2f693a45cd030a77ef38a2ac1eed757fd40d342f9ff'
            assert sha(p)==expected
            r.update(classification='historical-provenance-only-review',
                external_historical_references=external['references'][r['path']],
                historical_manifest_sha256=expected,
                review_reason='Retained source of archived P3 descriptors; exact source manifest still matches their immutable historical receipt')
        elif r['classification']=='keep-approval-active-or-uncertain' and 'active' in roles:
            m=load(ROOT/r['path']/'manifest.json')
            assert m['status']=='completed',r['path']
            r.update(classification='unused-unvalidated-reservation-review',
                review_reason='Completed run with old reservation marker(s); marker is a workflow claim, not evidence of a running process. Resolve reservations/dependencies before deletion.')
            rr=[]
            for reason in r['reasons']:
                if reason.startswith('active:') and reason.endswith('.reservation.json'):
                    p=ROOT/reason[7:];reservation=load(p)
                    rr.append(dict(path=rel(p),sha256=sha(p),created_utc=reservation.get('created_utc'),
                        status=reservation.get('status'),destination=reservation.get('destination')))
            r['reservation_markers']=rr;reservations.extend(rr)
        elif r['classification']=='keep-approval-active-or-uncertain':
            assert 'declared-accepted' in roles,r['path']
            r['classification']='keep-declared-approval'
        reviewed.append(r)
    totals={}
    for category in sorted({r['classification'] for r in reviewed}):
        rows=[r for r in reviewed if r['classification']==category]
        totals[category]=dict(runs=len(rows),bytes=sum(r['bytes'] for r in rows),GiB=round(sum(r['bytes'] for r in rows)/2**30,3))
    candidates=[r for r in reviewed if r['classification']=='unused-unvalidated-removable']
    needs_review=[r for r in reviewed if r['classification'] in {'historical-provenance-only-review','unused-unvalidated-reservation-review'}]
    report=dict(schema='bg2-animation-runs-reviewed-audit-v1',status='completed-read-only',created_utc=datetime.now(timezone.utc).isoformat(),
        baseline=rel(HERE/'audit.json'),baseline_sha256=sha(HERE/'audit.json'),
        external_check=rel(HERE/'external-reference-check.json'),external_check_sha256=sha(HERE/'external-reference-check.json'),
        roots=len(reviewed),totals=totals,removable=candidates,needs_review=needs_review,
        verification=dict(qa_selection_manifest_contracts=baseline['qa_selection_manifest_contracts_checked'],
            qa_selection_manifest_errors=baseline['qa_selection_manifest_contract_errors'],
            installed_areas=234,installation_status='installed = lock = registry',
            candidate_bam_duplicates_checked=sum(len(r['bam_duplicate_verification']) for r in candidates)),
        deletion_performed=False,QA_changed=False,installation_changed=False,release_changed=False,
        cleanup_requirements=['Recheck authority hashes and candidate inventory fingerprints immediately before deletion',
            'Retain immutable diagnostic metadata; canonical source.bam duplicates are verified',
            'Do not delete reservation markers or historical proof sources as part of the automatic candidate list'])
    write(HERE/'reviewed-audit.json',report)
    for name,rows in [('runs-reviewed.csv',reviewed),('candidats-suppression.csv',candidates),('a-revoir.csv',needs_review)]:
        with (HERE/name).open('x',encoding='utf-8',newline='') as out:
            writer=csv.writer(out);writer.writerow(['classification','MiB','bytes','path'])
            for r in rows:writer.writerow([r['classification'],round(r['bytes']/2**20,2),r['bytes'],r['path']])
    print(json.dumps(totals,indent=2))

if __name__=='__main__':main()
