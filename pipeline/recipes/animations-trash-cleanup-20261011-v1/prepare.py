"""Recheck the authorized 43 deletions and 29 reversible quarantines."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,shutil,stat

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
AUDIT=ROOT/'pipeline/recipes/animations-remaining-runs-audit-20261011-v1'
TRASH=ROOT/'corbeille/animations-20261011-v1'
REPARSE=getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)
def rel(p):return p.relative_to(ROOT).as_posix()
def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())
def inventory(p,full_hash=False):
    assert p.resolve().is_relative_to((ROOT/'animations').resolve())
    assert not p.lstat().st_file_attributes & REPARSE,p
    files=[];payload={}
    for folder,dirs,names in os.walk(p,followlinks=False):
        base=Path(folder)
        for name in dirs:
            q=base/name
            assert name!='.git' and not q.lstat().st_file_attributes & REPARSE,q
        for name in names:
            q=base/name;s=q.lstat()
            assert name!='.git' and not s.st_file_attributes & REPARSE,q
            n=q.relative_to(p).as_posix();files.append((n,s.st_size,s.st_mtime_ns))
            if full_hash:payload[n]=sha(q)
    fingerprint=hashlib.sha256(''.join(f'{n}\t{s}\t{t}\n' for n,s,t in sorted(files)).encode()).hexdigest()
    return dict(bytes=sum(s for _,s,_ in files),files=len(files),inventory_sha256=fingerprint),payload
def main():
    assert not (HERE/'operation-plan.json').exists()
    review=load(AUDIT/'reviewed-audit.json');baseline=load(AUDIT/'audit.json')
    assert sha(AUDIT/'audit.json')==review['baseline_sha256']
    assert sha(AUDIT/'reviewed-audit.json')==load(AUDIT/'verification.json')['reviewed_audit_sha256']
    for name,h in baseline['authority_sha256'].items():assert sha(ROOT/name)==h,name
    deletes=[];moves=[];markers=[];archive_bytes=0
    for item in review['removable']:
        p=ROOT/item['path'];actual,_=inventory(p)
        assert all(actual[k]==item[k] for k in actual),p
        for bam in item['bam_duplicate_verification']:
            assert sha(ROOT/bam['path'])==bam['sha256']
            assert any(sha(ROOT/name)==bam['sha256'] for name in bam['identical_canonical_sources'])
        copies=[]
        for q in p.rglob('*'):
            if q.is_file() and q.suffix.lower() in {'.json','.md','.py','.ps1','.txt','.log'}:
                dest=HERE/'discarded-run-records'/hashlib.sha256(item['path'].encode()).hexdigest()[:16]/q.relative_to(p)
                dest.parent.mkdir(parents=True,exist_ok=True)
                if not dest.exists():shutil.copyfile(q,dest)
                assert sha(q)==sha(dest)
                copies.append(dict(source=rel(q),archive=rel(dest),sha256=sha(dest),bytes=dest.stat().st_size))
                archive_bytes+=dest.stat().st_size
        deletes.append(dict(path=item['path'],absolute_path=str(p.resolve()),**actual,diagnostics=copies))
    for index,item in enumerate(review['needs_review'],1):
        p=ROOT/item['path'];actual,hashes=inventory(p,True)
        assert all(actual[k]==item[k] for k in actual),p
        dest=TRASH/item['path'];assert not dest.exists()
        moves.append(dict(source=item['path'],destination=rel(dest),absolute_source=str(p.resolve()),
            absolute_destination=str(dest.resolve()),classification=item['classification'],**actual,payload_sha256=hashes))
        for marker in item.get('reservation_markers',[]):
            q=ROOT/marker['path'];assert sha(q)==marker['sha256']
            assert load(q)['destination']==item['path'],q
            d=TRASH/marker['path'];assert not d.exists()
            markers.append(dict(source=marker['path'],destination=rel(d),absolute_source=str(q.resolve()),
                absolute_destination=str(d.resolve()),sha256=marker['sha256'],bytes=q.stat().st_size))
        if index%10==0:print('HASHED QUARANTINE',index,'/',len(review['needs_review']),flush=True)
    assert len(deletes)==43 and len(moves)==29 and len(markers)==22
    retained=[r['path'] for r in baseline['runs'] if r['classification']=='keep-used-or-qa-contract' or
        (r['classification']=='keep-approval-active-or-uncertain' and 'active' not in r['dependency_roles'])]
    assert len(retained)==665
    plan=dict(schema='bg2-animation-runs-trash-operation-plan-v1',status='verified',created_utc=datetime.now(timezone.utc).isoformat(),
        user_authorization='supprime les 43. crée une dossier corbeille a la racine du projet et déplace ceux dont on est pas sur',
        reviewed_audit=rel(AUDIT/'reviewed-audit.json'),reviewed_audit_sha256=sha(AUDIT/'reviewed-audit.json'),
        trash_root=rel(TRASH),deletes=deletes,moves=moves,reservation_moves=markers,
        retained_roots=retained,authority_sha256=baseline['authority_sha256'],
        gross_deleted_bytes=sum(r['bytes'] for r in deletes),diagnostics_archived_bytes=archive_bytes,
        estimated_net_freed_bytes=sum(r['bytes'] for r in deletes)-archive_bytes,
        quarantined_bytes=sum(r['bytes'] for r in moves)+sum(r['bytes'] for r in markers),
        game_mutation=False,QA_mutation=False,release_mutation=False)
    write(HERE/'operation-plan.json',plan)
    print('VERIFIED: delete43; quarantine29 +22 reservations; 665 retained; estimated net GiB',round(plan['estimated_net_freed_bytes']/2**30,3))
if __name__=='__main__':main()
