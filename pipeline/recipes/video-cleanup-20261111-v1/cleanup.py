"""Apply only the 141 approved BG2 video cleanup candidates; no GPU or media decode."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,stat,subprocess,sys

ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).resolve().parent
ANALYSIS=ROOT/'video/research/cleanup-analysis-20261111-v1'
PLAN=ANALYSIS/'plan.json'
SUMMARY=ROOT/'docs/validation/video-cleanup-analysis-20261111-v1.json'
VERIFY=HERE/'verification.json'
RECEIPT=HERE/'cleanup.json'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def absolute(s):return ROOT/s if s.startswith('video/') else Path(s)
def key(p):return str(p.resolve()).casefold()
def snapshot(p):
    s=p.stat();return dict(bytes=s.st_size,mtime_ns=s.st_mtime_ns)
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def context():
    summary=load(SUMMARY);assert sha(PLAN)==summary['plan_sha256'],'Analysis plan changed'
    d=load(PLAN);entries=d['candidates']+d['external_candidates']+d['external_input_candidates']
    assert len(entries)==141 and sum(e['bytes'] for e in entries)==14631402684
    assert len({key(absolute(e['path'])) for e in entries})==141
    comfy=get_path('comfyui_root',required=True).resolve()
    roots=[(ROOT/'video').resolve(),comfy/'output/BG2_video_upscale',comfy/'input']
    protected={key(ROOT/p):p for p in d['protected']}
    tracked={key(ROOT/p) for p in subprocess.check_output(['git','ls-files','video'],cwd=ROOT,text=True).splitlines()}
    return d,entries,roots,protected,tracked

def safe(p,roots):
    resolved=p.resolve(strict=True);assert p.is_file() and resolved==p.absolute(),p
    allowed=next((r.resolve() for r in roots if resolved.is_relative_to(r.resolve())),None)
    assert allowed and resolved!=allowed,p
    for ancestor in (p,*p.parents):
        s=ancestor.lstat()
        assert not stat.S_ISLNK(s.st_mode) and not getattr(s,'st_file_attributes',0)&0x400,ancestor
        if ancestor==allowed:break
    assert p.stat().st_nlink==1,p

def verify():
    assert not VERIFY.exists() and not RECEIPT.exists(),'Use a new cleanup version'
    d,entries,roots,protected,tracked=context();checks=[];hashes={};packet_hashes={}
    def digest(p):
        k=key(p)
        if k not in hashes:hashes[k]=sha(p)
        return hashes[k]
    def packets(p):
        k=key(p)
        if k not in packet_hashes:
            # Stream copy only: no decoder/filter/model and hardware acceleration explicitly off.
            args=['ffmpeg','-v','error','-nostdin','-hwaccel','none','-threads','1','-i',str(p),
                '-map','0:v:0','-an','-c:v','copy','-f','hash','-hash','sha256','-']
            packet_hashes[k]=subprocess.check_output(args,text=True).strip()
        return packet_hashes[k]
    def same(a,b):
        if digest(a)==digest(b):method='full-file-SHA256'
        else:
            assert packets(a)==packets(b),(a,b)
            method='encoded-video-packets-SHA256-no-decode'
        checks.append(dict(discard=str(a),reference=str(b),method=method))
    for e in entries:
        p=absolute(e['path']);safe(p,roots)
        assert key(p) not in protected and key(p) not in tracked,p
        assert snapshot(p)==dict(bytes=e['bytes'],mtime_ns=e['mtime_ns']),p
        for target in e.get('canonical_final_copy',[]):
            q=ROOT/target;expected=d['final_files'][target]['sha256']
            assert digest(q)==expected and digest(p)==expected,(p,q)
            checks.append(dict(discard=str(p),reference=str(q),method='full-file-SHA256-canonical-final'))
    inventory=load(ANALYSIS/'inventory.json')['files']
    for e in d['external_candidates']:
        p=absolute(e['path']);parent=p.parent.name
        if p.suffix=='.mov' and parent.startswith(('intro-','intro15f-')):
            matches=[ROOT/f['path'] for f in inventory if f['path'].endswith('.mov') and f['bytes']==e['bytes']]
            assert len(matches)==1,(p,matches);same(p,matches[0])
        elif p.suffix=='.mp4':
            asset=next(a for a in ['deathand','flythr03','restinn','rest'] if p.name.lower().startswith(a))
            if asset=='deathand':q=ROOT/'video/deathand/runs/deathand-upscale-seedvr2-lab-1080p-v1/02_upscale/DEATHAND-1080p-seedvr2-3b-int8-lab.mp4'
            elif asset=='flythr03':q=ROOT/'video/flythr03/runs/flythr03-upscale-seedvr2-lab-prototype-v1/02_upscale/FLYTHR03-1080p-seedvr2-3b-int8-lab.mp4'
            else:q=ROOT/f'video/{asset}/runs/{asset}-seedvr-apollo-20261109-v1/{asset.upper()}-SeedVR2-3B-FP16-LAB-1080p15.mp4'
            same(p,q)
    for e in d['external_input_candidates']:
        p=absolute(e['path'])
        if '__ouverture_contexte__' in p.name or 'H3-01604-corrected' in p.name:
            matches=[ROOT/f['path'] for f in inventory if Path(f['path']).name==p.name and f['bytes']==e['bytes']]
            assert len(matches)==1,(p,matches);same(p,matches[0])
        elif p.suffix=='.webm':
            lower=p.name.lower()
            asset=next(a for a in ['deathand','flythr03','restdung','restinn','daynite'] if a in lower)
            same(p,ROOT/f'video/{asset}/{asset}.wbm')
    keep_snapshot={s:snapshot(ROOT/s) for s in d['protected']}
    save(VERIFY,dict(state='verified',plan_sha256=sha(PLAN),candidate_count=len(entries),
        candidate_bytes=sum(e['bytes'] for e in entries),duplicate_checks=checks,
        protected_snapshot=keep_snapshot,protected_files=len(keep_snapshot),gpu_tasks_started=0,
        media_decodes=0,cpu_hash_files=len(hashes),cpu_packet_hash_files=len(packet_hashes)))
    print('VERIFIED',len(entries),'candidates;',len(checks),'duplicate checks;',len(keep_snapshot),'protected files',flush=True)

def apply():
    assert not RECEIPT.exists(),'Receipt already exists; do not replay'
    v=load(VERIFY);d,entries,roots,protected,tracked=context()
    assert v['state']=='verified' and v['plan_sha256']==sha(PLAN)
    # Check every absolute target and all protected paths before the first unlink.
    for e in entries:
        p=absolute(e['path']);safe(p,roots)
        assert key(p) not in protected and key(p) not in tracked,p
        assert snapshot(p)==dict(bytes=e['bytes'],mtime_ns=e['mtime_ns']),p
    for s,expected in v['protected_snapshot'].items():assert snapshot(ROOT/s)==expected,s
    receipt=dict(schema='video-cleanup-receipt-v1',state='deleting',started_utc=datetime.now(timezone.utc).isoformat(),
        plan=PLAN.relative_to(ROOT).as_posix(),plan_sha256=sha(PLAN),user_authorization='ok go pour la passe de ménage sans utiliser le gpu',
        gpu_tasks_started=0,media_decodes=0,deleted=[],errors=[],protected_files=len(v['protected_snapshot']))
    save(RECEIPT,receipt)
    for e in entries:
        p=absolute(e['path'])
        try:
            safe(p,roots);assert snapshot(p)==dict(bytes=e['bytes'],mtime_ns=e['mtime_ns'])
            p.unlink()
            receipt['deleted'].append(dict(path=e['path'],bytes=e['bytes'],category=e['category']))
        except Exception as exc:
            receipt['errors'].append(dict(path=e['path'],error=repr(exc)))
            receipt['state']='stopped-on-error';save(RECEIPT,receipt);raise
        save(RECEIPT,receipt)
    for s,expected in v['protected_snapshot'].items():assert snapshot(ROOT/s)==expected,s
    assert all(not absolute(e['path']).exists() for e in entries)
    receipt.update(state='complete',finished_utc=datetime.now(timezone.utc).isoformat(),
        deleted_files=len(receipt['deleted']),deleted_bytes=sum(e['bytes'] for e in receipt['deleted']),
        protected_files_unchanged=True,game_modified=False,release_modified=False)
    save(RECEIPT,receipt)
    print('COMPLETE',receipt['deleted_files'],'files;',receipt['deleted_bytes'],'bytes;',receipt['deleted_bytes']/2**30,'GiB; GPU tasks=0',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['verify','apply']);args=parser.parse_args()
    {'verify':verify,'apply':apply}[args.action]()
