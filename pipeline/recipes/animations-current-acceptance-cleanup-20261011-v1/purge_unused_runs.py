"""Reachability-based run cleanup. Python audits only; PowerShell performs scoped deletions."""
from accept_current import *
import os,re,json,hashlib,argparse,collections,stat

REF=re.compile(r'animations/(?:runs|batches|packs-par-zone)/[A-Za-z0-9_.-]+(?:/[^\s"\'`<>\[\](),;{}]+)*|animations/ressources/[A-Za-z0-9_]+/runs/[A-Za-z0-9_.-]+(?:/[^\s"\'`<>\[\](),;{}]+)*',re.I)
REPARSE=getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)

def candidates():
    paths=list((ROOT/'animations/runs').glob('*'))+list((ROOT/'animations/batches').glob('*'))+list((ROOT/'animations/ressources').glob('*/runs/*'))
    return sorted(p for p in paths if p.is_dir())

def inventory(folder):
    folder=folder.resolve();assert folder.is_relative_to((ROOT/'animations').resolve())
    files=[];hazards=[];total=0;latest=0
    if folder.lstat().st_file_attributes & REPARSE:hazards.append('root-reparse-point')
    for base,dirs,names in os.walk(folder,followlinks=False):
        base=Path(base)
        for name in list(dirs):
            p=base/name
            if p.lstat().st_file_attributes & REPARSE:hazards.append('reparse-point:'+str(p));dirs.remove(name)
            if name=='.git':hazards.append('embedded-git-repository');dirs.remove(name)
        for name in names:
            p=base/name;s=p.lstat()
            if s.st_file_attributes & REPARSE:hazards.append('reparse-file:'+str(p));continue
            if name=='.git':hazards.append('embedded-git-repository')
            if p.suffix.lower()=='.bam':hazards.append('BAM-source-or-runtime-contract')
            if name.endswith('.reservation.json'):hazards.append('active-run-reservation')
            n=p.relative_to(folder).as_posix();files.append((n,s.st_size,s.st_mtime_ns));total+=s.st_size;latest=max(latest,s.st_mtime_ns)
    encoded=''.join(f'{n}\t{s}\t{t}\n' for n,s,t in sorted(files)).encode('utf8')
    return dict(file_count=len(files),bytes=total,latest_mtime_ns=latest,inventory_fingerprint=hashlib.sha256(encoded).hexdigest()),sorted(set(hazards))

def plan():
    roots=candidates();by_path={rel(p).casefold():p for p in roots};kept=collections.defaultdict(set)
    queue=collections.deque();seen=set();authority={};observed_missing=set()
    def protect(p,reason):
        key=rel(p).casefold()
        if key not in kept:
            queue.extend(p.rglob('manifest.json'));queue.extend(p.glob('*.json'))
        kept[key].add(reason)
    def reference(value,owner):
        value=re.sub('/+','/',value.replace('\\','/'))
        for match in REF.finditer(value):
            relative=match.group(0).split('::',1)[0].rstrip('.');p=ROOT/relative
            candidate=None
            for parent in [p,*p.parents]:
                try:key=rel(parent).casefold()
                except ValueError:continue
                if key in by_path:candidate=by_path[key];break
            if candidate is not None:protect(candidate,'reference:'+rel(owner))
            elif relative.casefold().startswith('animations/packs-par-zone/'):
                if p.is_file() and p.suffix=='.json':queue.append(p)
                elif p.is_dir():
                    if (p/'manifest.json').is_file():queue.append(p/'manifest.json')
                    # An area index references its complete leaves by relative directories.
                    if p.parent.name=='packs-par-zone':queue.extend(p.glob('*/manifest.json'))
            if not p.exists() and candidate is None:observed_missing.add(relative)
    def read_reference_file(p,is_authority=False):
        if not p.is_file():return
        text=p.read_text(encoding='utf-8-sig',errors='replace')
        if is_authority:authority[rel(p)]=digest(p)
        # Text extraction also covers immutable prose decisions and CSV prototype fields.
        reference(text,p)
        if p.suffix=='.json':
            try:data=json.loads(text)
            except ValueError:return
            def relative_references(obj):
                if isinstance(obj,dict):
                    for key,value in obj.items():
                        if isinstance(value,str) and key in {'source_run','source_temporal_run','source_pack','base_pack','pack','path','manifest_path','output_split_root'}:
                            value=value.split('::',1)[0]
                            if value.startswith(('../','./')):
                                resolved=(p.parent/value).resolve()
                                if resolved.is_relative_to(ROOT):reference(rel(resolved),p)
                        relative_references(value)
                elif isinstance(obj,list):
                    for value in obj:relative_references(value)
            relative_references(data)
    for base in ['animations/index/qa-decisions','animations/index/area-qa-decisions','animations/index/selections']:
        for p in (ROOT/base).rglob('*.json'):queue.append(p);authority[rel(p)]=digest(p)
    for name in ['animation_upscale_registry.csv','animation_alpha_corrections.csv','area-pack-lock.json','post-p3-pack-retention-20260902.json','qa-evidence-migrations.json']:
        read_reference_file(ROOT/'animations/index'/name,True)
    # Retention records use root names rather than full paths.
    retention=load(ROOT/'animations/index/post-p3-pack-retention-20260902.json')
    for record in retention.get('packs',[]):
        if record.get('classification') in {'release-source','qa-lineage','retained-qa-evidence','pending-qa-processing-evidence'}:
            p=ROOT/'animations/packs-par-zone'/record['name']
            if (p/'manifest.json').is_file():queue.append(p/'manifest.json');queue.extend(p.glob('*/manifest.json'))
    for base in ['releases/BG2-HD-Upscale/manifests','releases/BG2-HD-Upscale/bg2hd/manifests']:
        for p in (ROOT/base).rglob('*.json'):queue.append(p);authority[rel(p)]=digest(p)
    inv={}
    for index,p in enumerate(roots,1):
        key=rel(p).casefold();record,hazards=inventory(p);inv[key]=record
        for reason in hazards:protect(p,reason)
        manifest=p/'manifest.json'
        if manifest.is_file():
            try:m=load(manifest)
            except ValueError:protect(p,'unreadable-manifest');continue
            if m.get('status') in {'accepted','running','working','processing','in-progress'}:protect(p,'accepted-or-active-status')
        for proof in p.glob('*approval*.json'):
            try:
                if load(proof).get('status')=='accepted':protect(p,'accepted-approval-evidence')
            except ValueError:protect(p,'unreadable-approval-evidence')
        if index%100==0:print('INVENTORIED',index,'/',len(roots),flush=True)
    # Producer reservations sit beside their future run directory.
    for p in (ROOT/'animations/ressources').glob('*/.*.reservation.json'):read_reference_file(p,True)
    count=0
    while queue:
        p=queue.popleft().resolve()
        if p in seen or not p.is_file():continue
        seen.add(p);read_reference_file(p);count+=1
        if count%300==0:print('DEPENDENCY METADATA',count,'protected runs',len(kept),flush=True)
    removable=[];preserved=[]
    for p in roots:
        key=rel(p).casefold();item=dict(path=rel(p),absolute_path=str(p.resolve()),**inv[key])
        if key in kept:preserved.append(dict(item,reasons=sorted(kept[key])))
        else:removable.append(item)
    assert all(not (set(e['path'].casefold() for e in removable)&set(kept)) for _ in [0])
    result=dict(schema='bg2-upscale-unused-animation-runs-cleanup-plan-v1',status='planned',created_utc=v.utc_now(),
        scope=['animations/runs/*','animations/batches/*','animations/ressources/*/runs/*'],
        policy='Delete only unreachable run/batch roots. Preserve immutable QA, selected runs, installed/release dependencies, accepted approvals, native BAMs, reservations and reparse points. Packs, sources, game and release are outside deletion scope.',
        authority_sha256=authority,dependency_metadata_files=len(seen),roots=len(roots),preserved=preserved,remove=removable,
        deletion_count=len(removable),deletion_bytes=sum(x['bytes'] for x in removable),
        preexisting_missing_references=sorted(observed_missing))
    write(HERE/'purge-plan.json',result)
    print('PLAN:',len(roots),'runs/batches;',len(preserved),'protected;',len(removable),'unused to delete;',round(result['deletion_bytes']/2**30,2),'GiB',flush=True)

def verify_before_delete():
    plan=load(HERE/'purge-plan.json')
    for p,h in plan['authority_sha256'].items():assert v.sha256_file(path(p))==h,p+': authority changed; replan required'
    records=[];allowed=set(candidates())
    for index,item in enumerate(plan['remove'],1):
        p=path(item['path']);assert str(p.resolve())==item['absolute_path']
        assert p in allowed,p
        actual,hazards=inventory(p);assert not hazards and all(actual[k]==item[k] for k in actual),p
        # Diagnostic recipes/conclusions remain available after unused media are removed.
        archive=HERE/'discarded-run-records'/hashlib.sha256(item['path'].encode()).hexdigest()[:16]
        copied=[]
        for meta in p.iterdir():
            if meta.is_file() and meta.suffix.lower() in {'.json','.md','.py','.ps1','.txt','.log'}:
                dest=archive/meta.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(meta,dest)
                copied.append(dict(path=rel(dest),source=rel(meta),sha256=digest(dest)))
        records.append(dict(item,diagnostic_metadata_preserved=copied))
        if index%25==0:print('DELETE PRECHECK',index,'/',len(plan['remove']),flush=True)
    write(HERE/'delete-verified.json',dict(schema='bg2-upscale-unused-animation-runs-delete-verification-v1',status='verified',created_utc=v.utc_now(),
        plan_sha256=digest(HERE/'purge-plan.json'),records=records))
    print('VERIFIED',len(records),'exact contained paths; dependency authorities unchanged',flush=True)

def after_delete():
    plan=load(HERE/'purge-plan.json');verified=load(HERE/'delete-verified.json')
    assert verified['plan_sha256']==digest(HERE/'purge-plan.json')
    for r in verified['records']:assert not path(r['path']).exists(),r['path']
    for r in plan['preserved']:assert path(r['path']).is_dir(),r['path']
    for p,h in plan['authority_sha256'].items():assert v.sha256_file(path(p))==h,p
    for r in verified['records']:
        for meta in r['diagnostic_metadata_preserved']:assert digest(path(meta['path']))==meta['sha256']
    receipt=dict(schema='bg2-upscale-unused-animation-runs-cleanup-receipt-v1',status='completed',created_utc=v.utc_now(),
        plan=rel(HERE/'purge-plan.json'),plan_sha256=digest(HERE/'purge-plan.json'),
        deleted_runs=plan['deletion_count'],deleted_files=sum(r['file_count'] for r in plan['remove']),
        freed_bytes=plan['deletion_bytes'],preserved_runs=len(plan['preserved']),
        all_authority_sha256_preserved=True,diagnostic_recipes_preserved=True,game_mutation=False,release_mutation=False,
        records=[dict(path=r['path'],bytes=r['bytes'],file_count=r['file_count']) for r in plan['remove']])
    write(HERE/'purge-receipt.json',receipt)
    print('DELETED',receipt['deleted_runs'],'unused runs;',round(receipt['freed_bytes']/2**30,2),'GiB freed; dependencies and QA preserved')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['plan','verify-before-delete','after-delete']);args=parser.parse_args()
    {'plan':plan,'verify-before-delete':verify_before_delete,'after-delete':after_delete}[args.mode]()
