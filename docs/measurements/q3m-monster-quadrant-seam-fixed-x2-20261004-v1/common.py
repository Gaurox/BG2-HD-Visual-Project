"""Contextual seam repair: exact source plan and four-native-pixel feather band."""
import os
os.environ.setdefault('OPENBLAS_NUM_THREADS','4');os.environ.setdefault('OMP_NUM_THREADS','4')
import hashlib,json,sys
from functools import lru_cache
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent;WORK=ROOT/'sprite/.work'/HERE.name
PARENT=HERE.parent/'q3m-monster-quadrant-full-x2-20261004-v1'
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan,validate_encoded,save,pack,load_model
from palette_work_plan import file_sha,write_json
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
digest=lambda obj:hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()
relative=lambda p:p.relative_to(ROOT).as_posix()
identity=lambda p:dict(path=relative(p),sha256=file_sha(p),bytes=p.stat().st_size)
PROD=load(PARENT/'production.json');GEN=load(PARENT/'current-generation.json')
CACHE=ROOT/'sprite/.work/q3m-family-witnesses-x2-20261003-v1';ENCODED=CACHE/'encoded'/PROD['encoder_namespace']
BACKEND=load(CACHE/'backend.json');BACKEND_KEY=bytes.fromhex(digest(BACKEND))

def plan():
    resources,works,summary=source_plan(PARENT/'selection.json','monster_quadrant')
    assert summary==PROD['plan']
    source={(r['witness']['animation_id'],r['resref']):r for r in resources};contexts={};bindings={}
    for w in load(PARENT/'selection.json')['witnesses']:
        for refs in w['multipart_groups']:
            rs=[source[(w['animation_id'],ref)] for ref in refs]
            for seq in range(min(len(r['cycles']) for r in rs)):
                for slot in range(min(len(r['cycles'][seq]) for r in rs)):
                    fi=[r['cycles'][seq][slot] for r in rs]
                    if any(f>=len(r['frames']) for r,f in zip(rs,fi)):continue
                    rows=[r['frames'][f] for r,f in zip(rs,fi)]
                    signature=[(row['key'],row['geometry']) for row in rows];key=digest(signature)
                    contexts.setdefault(key,dict(key=key,nodes=list(zip(rs,rows)),geometry=[row['geometry'] for row in rows],representative=dict(animation_id=w['animation_id'],refs=refs,seq=seq,slot=slot)))
                    for n,(r,row) in enumerate(zip(rs,rows)):
                        bind=(w['animation_id'],r['resref'],row['frame_index'])
                        assert bind not in bindings or bindings[bind]==(key,n),'frame aliases incompatible context'
                        bindings[bind]=(key,n)
    assert len(contexts)==3144 and len(bindings)==12656,(len(contexts),len(bindings))
    return resources,works,summary,contexts,bindings

def strength(a,geometry):
    h,w=a[1]*2,a[0]*2
    yy,xx=np.mgrid[:h,:w];wx=-a[2]+(xx+.5)/2;wy=-a[3]+(yy+.5)/2;distance=np.full((h,w),np.inf)
    for b in geometry:
        if b is a or not b[0]*b[1]:continue
        bx=-b[2];by=-b[3];br=bx+b[0];bt=by+b[1]
        if -a[2]+a[0]==bx or br==-a[2]:
            cut=bx if -a[2]+a[0]==bx else br;overlap=(wy>=max(-a[3],by))&(wy<min(-a[3]+a[1],bt))
            distance=np.minimum(distance,np.where(overlap,abs(wx-cut),np.inf))
        if -a[3]+a[1]==by or bt==-a[3]:
            cut=by if -a[3]+a[1]==by else bt;overlap=(wx>=max(-a[2],bx))&(wx<min(-a[2]+a[0],br))
            distance=np.minimum(distance,np.where(overlap,abs(wy-cut),np.inf))
    return np.clip((4-distance)/3,0,1)

@lru_cache(maxsize=128)
def old_arrays(key):
    with np.load(ENCODED/(key+'.npz'),allow_pickle=False) as z:return {n:z[n].copy() for n in z.files}

def old_targets(work,roi):
    used=np.unique(work['frame'].indices[work['frame'].indices!=0]);arrays=[]
    for pal in work['profile'].fitting:
        key=hashlib.sha256(BACKEND_KEY+bytes.fromhex(work['input_key'])+used.tobytes()+pal[used].tobytes()).hexdigest()
        with np.load(CACHE/'targets'/key[:2]/(key+'.npz'),allow_pickle=False) as z:arrays.append(z['target'][roi].copy())
    return np.stack(arrays)

def bound_plan(resources,works,contexts,bindings):
    """Map only the corrected frame bindings; all orphan/empty planes remain acquired."""
    for key,w in works.items():w['encoded_path']=ENCODED/(key+'.npz')
    original_keys={};patched={}
    for r in resources:
        for row in r['frames']:
            bind=(r['witness']['animation_id'],r['resref'],row['frame_index']);old=row['key'];original_keys[bind]=old
            if bind not in bindings:continue
            ck,n=bindings[bind];record=load(WORK/'contexts'/(ck+'.json'))['nodes'][n];new=record['encoded_key']
            if new==old:continue
            w=dict(works[old],encoded_path=WORK/'encoded'/(new+'.npz'));works.setdefault(new,w)
            row['key']=new;patched[bind]=record
    return original_keys,patched
