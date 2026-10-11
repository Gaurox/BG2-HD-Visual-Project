"""Read-only audit of remaining animation runs: contracts, provenance, duplicate BAMs."""
from pathlib import Path
import collections,csv,hashlib,io,json,os,re,stat,sys
from datetime import datetime,timezone

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
REF=re.compile(r'animations/(?:runs|batches|packs-par-zone)/[A-Za-z0-9_.-]+(?:/[^\s"\'`<>\[\](),;{}]+)*|animations/ressources/[A-Za-z0-9_]+/runs/[A-Za-z0-9_.-]+(?:/[^\s"\'`<>\[\](),;{}]+)*',re.I)
REPARSE=getattr(stat,'FILE_ATTRIBUTE_REPARSE_POINT',1024)
CORE={'qa','selection','installation','registry','release','qa-migration'}
sha_cache={}

def rel(p):return p.relative_to(ROOT).as_posix()
def sha(p):
    if p not in sha_cache:
        h=hashlib.sha256()
        with p.open('rb') as f:
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
        sha_cache[p]=h.hexdigest()
    return sha_cache[p]
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def write(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write((json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode())

def main():
    assert not (HERE/'audit.json').exists(),'Immutable audit already exists'
    roots=sorted(p.resolve() for p in [*(ROOT/'animations/runs').glob('*'),*(ROOT/'animations/batches').glob('*'),*(ROOT/'animations/ressources').glob('*/runs/*')] if p.is_dir())
    root_map={rel(p).casefold():p for p in roots};records={};metadata={};authority={};contracts={}
    labels=collections.defaultdict(set);reasons=collections.defaultdict(set)
    queue=collections.deque();visited=set();cached_edges={};missing=set()
    def root_of(p):
        for q in [p,*p.parents]:
            try:k=rel(q).casefold()
            except ValueError:continue
            if k in root_map:return root_map[k]
        return None
    def protect(p,label,owner):
        reasons[p].add(label+':'+rel(owner))
        if label not in labels[p]:
            labels[p].add(label)
            queue.extend((m,label) for m in metadata[p])
    def parse(p):
        if p in cached_edges:return cached_edges[p]
        raw=p.read_text(encoding='utf-8-sig',errors='replace').replace('\\','/')
        edges={ROOT/m.group(0).split('::',1)[0].rstrip('.') for m in REF.finditer(re.sub('/+','/',raw))}
        if p.suffix.lower()=='.json':
            try:obj=load(p)
            except ValueError:obj={}
            def walk(x):
                if isinstance(x,dict):
                    for k,value in x.items():
                        if isinstance(value,str) and value.startswith(('./','../')):
                            q=(p.parent/value.split('::',1)[0]).resolve()
                            if q.is_relative_to(ROOT/'animations'):edges.add(q)
                        walk(value)
                elif isinstance(x,list):
                    for item in x:walk(item)
            walk(obj)
        cached_edges[p]=edges
        return edges
    for index,p in enumerate(roots,1):
        files=[];bams=[];metas=[];hazards=[]
        if p.lstat().st_file_attributes & REPARSE:hazards.append('root-reparse-point')
        for base,dirs,names in os.walk(p,followlinks=False):
            base=Path(base)
            for name in list(dirs):
                q=base/name
                if name=='.git' or q.lstat().st_file_attributes & REPARSE:
                    hazards.append('embedded-git-or-reparse-directory');dirs.remove(name)
            for name in names:
                q=base/name;s=q.lstat()
                if s.st_file_attributes & REPARSE:hazards.append('reparse-file');continue
                if name=='.git' or name.endswith('.reservation.json'):hazards.append('git-or-reservation')
                files.append((q.relative_to(p).as_posix(),s.st_size,s.st_mtime_ns))
                if q.suffix.lower()=='.bam':bams.append(q)
                if q.suffix.lower()=='.json' or (base==p and q.suffix.lower() in {'.md','.txt'}):metas.append(q)
        records[p]=dict(path=rel(p),bytes=sum(s for _,s,_ in files),files=len(files),
            latest_mtime_ns=max((t for _,_,t in files),default=0),
            inventory_sha256=hashlib.sha256(''.join(f'{n}\t{s}\t{t}\n' for n,s,t in sorted(files)).encode()).hexdigest(),
            bam_files=[rel(q) for q in bams],hazards=hazards)
        metadata[p]=metas
        for q in metas:
            if q.suffix.lower()!='.json':continue
            try:m=load(q)
            except ValueError:
                if q.name=='manifest.json':protect(p,'unreadable',q)
                continue
            if not isinstance(m,dict):continue
            status=m.get('status')
            if isinstance(status,str) and status in {'running','working','processing','in-progress'}:protect(p,'active',q)
            if ('approval' in q.name.lower() and status=='accepted') or (q==p/'manifest.json' and status=='accepted'):
                protect(p,'declared-accepted',q)
        if hazards:protect(p,'hazard',p)
        if index%150==0:print('INVENTORY',index,'/',len(roots),flush=True)
    def seed(p,label):
        if p.is_file():authority[rel(p)]=sha(p);queue.append((p.resolve(),label))
    for base,label in [('animations/index/qa-decisions','qa'),('animations/index/area-qa-decisions','qa'),('animations/index/selections','selection')]:
        for p in (ROOT/base).rglob('*.json'):
            seed(p,label)
            def contract_refs(x):
                if isinstance(x,dict):
                    if isinstance(x.get('manifest_path'),str) and isinstance(x.get('manifest_sha256'),str):
                        contracts[x['manifest_path']]=x['manifest_sha256'].lower()
                    for value in x.values():contract_refs(value)
                elif isinstance(x,list):
                    for value in x:contract_refs(value)
            contract_refs(load(p))
    for name,label in [('area-pack-lock.json','installation'),('animation_upscale_registry.csv','registry'),('animation_alpha_corrections.csv','registry'),('qa-evidence-migrations.json','qa-migration'),('path-migrations.json','qa-migration')]:seed(ROOT/'animations/index'/name,label)
    for base in ['releases/BG2-HD-Upscale/manifests','releases/BG2-HD-Upscale/bg2hd/manifests']:
        for p in (ROOT/base).rglob('*.json'):seed(p,'release')
    retention=ROOT/'animations/index/post-p3-pack-retention-20260902.json'
    seed(retention,'historical-retention')
    for record in load(retention).get('packs',[]):
        p=ROOT/'animations/packs-par-zone'/record['name']
        if p.is_dir():
            queue.append((p/'manifest.json','historical-retention'))
            queue.extend((q,'historical-retention') for q in p.glob('*/manifest.json'))
    for p in (ROOT/'animations/ressources').glob('*/.*.reservation.json'):seed(p,'active')
    while queue:
        p,label=queue.popleft();p=Path(os.path.normpath(p));key=(p,label)
        if key in visited or not p.is_file():continue
        visited.add(key)
        for q in parse(p):
            q=Path(os.path.normpath(q));run=root_of(q)
            if run:protect(run,label,p)
            if not q.exists():missing.add(rel(q));continue
            if q.is_file() and q.suffix.lower()=='.json':queue.append((q,label))
            elif q.is_dir() and run is None:
                if (q/'manifest.json').is_file():queue.append((q/'manifest.json',label))
                if q.parent==ROOT/'animations/packs-par-zone':queue.extend((m,label) for m in q.glob('*/manifest.json'))
        if len(visited)%1500==0:print('DEPENDENCY GRAPH',len(visited),'file/role pairs',flush=True)
    canonical_bams=collections.defaultdict(list)
    for p in (ROOT/'animations/ressources').glob('*/source.bam'):canonical_bams[sha(p)].append(rel(p))
    output=[]
    for p,r in records.items():
        roles=labels[p];matches=[]
        if roles & CORE:classification='keep-used-or-qa-contract'
        elif roles & {'declared-accepted','active','hazard','unreadable'}:classification='keep-approval-active-or-uncertain'
        elif roles:classification='historical-provenance-only-review'
        else:
            for name in r['bam_files']:
                q=ROOT/name;h=sha(q);matches.append(dict(path=name,sha256=h,identical_canonical_sources=canonical_bams.get(h,[])))
            classification='unused-unvalidated-removable' if all(x['identical_canonical_sources'] for x in matches) else 'unused-unvalidated-unique-BAM-preserve'
        output.append(dict(r,classification=classification,dependency_roles=sorted(roles),
            reasons=sorted(reasons[p]),bam_duplicate_verification=matches))
    errors=[]
    for name,h in contracts.items():
        p=ROOT/name
        if not p.is_file() or sha(p)!=h:errors.append(name)
    for name,h in authority.items():
        sha_cache.pop(ROOT/name,None)
        assert sha(ROOT/name)==h,name
    totals={}
    for category in sorted({x['classification'] for x in output}):
        rr=[x for x in output if x['classification']==category]
        totals[category]=dict(runs=len(rr),bytes=sum(x['bytes'] for x in rr),GiB=round(sum(x['bytes'] for x in rr)/2**30,3))
    report=dict(schema='bg2-upscale-remaining-animation-runs-audit-v1',created_utc=datetime.now(timezone.utc).isoformat(),
        scope=['animations/runs/*','animations/batches/*','animations/ressources/*/runs/*'],
        operation='read-only audit; no deletion, QA/selection/installation/release mutation',roots=len(roots),
        total_bytes=sum(x['bytes'] for x in output),totals=totals,authority_sha256=authority,
        qa_selection_manifest_contracts_checked=len(contracts),qa_selection_manifest_contract_errors=errors,
        metadata_files_parsed=len(cached_edges),preexisting_missing_provenance_paths=sorted(missing),
        policy='All actual QA/selection/installation/release/registry dependencies retained. A native BAM alone does not make a run used: exact canonical duplication checked for otherwise unreachable roots. Historical inventory dependencies and unique BAMs require separate review. Declared technical approval never inferred as ingame QA.',
        runs=sorted(output,key=lambda x:-x['bytes']))
    write(HERE/'audit.json',report)
    with (HERE/'runs.csv').open('x',encoding='utf-8',newline='') as f:
        writer=csv.writer(f);writer.writerow(['classification','GiB','bytes','files','path','dependency_roles'])
        for r in report['runs']:writer.writerow([r['classification'],round(r['bytes']/2**30,4),r['bytes'],r['files'],r['path'],';'.join(r['dependency_roles'])])
    assert not errors,errors
    print(json.dumps(dict(roots=len(roots),total_GiB=round(report['total_bytes']/2**30,3),totals=totals,contracts=len(contracts),errors=errors),indent=2),flush=True)

if __name__=='__main__':main()
