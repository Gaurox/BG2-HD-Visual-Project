"""Cross-check candidate50 against completed effects, projectile masks and selected animations."""
import csv
import hashlib
import json
import struct
import sys
from collections import defaultdict,Counter
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from bam_export import decode_bam,native_palette_alpha
from export_bam_frames import read_bam,cycle_metadata

PROPOSAL=ROOT/'effects/batches/lot50-magic-water-proposal-20261108-v1/batch.json'
OUT=ROOT/'effects/research/next50-reuse-audit-20261108-v1'
CACHE=ROOT/'.tmp/effects-next50-reuse-20261108/cache'
def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def rows(p):return list(csv.DictReader((ROOT/p).open(encoding='utf-8-sig',newline='')))
def sha(b):return hashlib.sha256(b).hexdigest().upper()
def save(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def signatures(path):
    raw=read_bam(path);key=sha(raw);cache=CACHE/(key+'.json')
    if cache.exists():return load(cache)
    fs,pal,tr=decode_bam(raw);alpha=native_palette_alpha(raw,tr);records=[]
    for i,(idx,cx,cy,_) in enumerate(fs):
        rgba=np.dstack((pal[idx],alpha[idx]));visible=rgba[:,:,3]>0
        rgba[~visible]=0
        if not visible.any() or not rgba[:,:,:3].any():
            # Whole black shadows still need alpha comparison; transparent records carry no new image.
            rgb_black=not rgba[:,:,:3].any()
        else:rgb_black=False
        if not visible.any():records.append(dict(frame=i,blank=True));continue
        yy,xx=np.where(visible);x0,x1=int(xx.min()),int(xx.max()+1);y0,y1=int(yy.min()),int(yy.max()+1)
        crop=rgba[y0:y1,x0:x1].copy();shape=struct.pack('<II',x1-x0,y1-y0)
        intrinsic=sha(shape+crop.tobytes());anchored=sha(struct.pack('<ii',x0-cx,y0-cy)+bytes.fromhex(intrinsic))
        mask=crop[:,:,3];mask_key=sha(shape+mask.tobytes()) if len(np.unique(mask))>1 and mask.size>=16 else None
        # A palette-independent indexed pattern is only a recoloring clue, never RGB equivalence.
        flat=idx[y0:y1,x0:x1].ravel();_,first,inverse=np.unique(flat,return_index=True,return_inverse=True)
        ranks=np.empty(len(first),np.uint16);ranks[np.argsort(first)]=np.arange(len(first),dtype=np.uint16)
        pattern=sha(shape+ranks[inverse].tobytes()+mask.tobytes())
        records.append(dict(frame=i,blank=False,black_rgb=rgb_black,intrinsic=intrinsic,anchored=anchored,
                            mask=mask_key,pattern=pattern,origin=[x0-cx,y0-cy],size=[x1-x0,y1-y0]))
    cycles=cycle_metadata(raw,len(fs));used={k for c in cycles for k in c['frame_indices']}
    result=dict(canonical_sha256=key,frames=records,cycles=cycles,used=sorted(used))
    save(cache,result);return result

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    assert not (OUT/'audit.json').exists(),'New audit version required'
    authority=[ROOT/'effects/index/processing.csv',ROOT/'projectiles/index/work-tracking.json',ROOT/'animations/index/animation_upscale_registry.csv']
    before={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in authority}
    state={r['asset_key'].rsplit(':',1)[-1]:r for r in rows('effects/index/processing.csv')}
    proposal=load(PROPOSAL);targets=proposal['assets']
    projectiles=rows('projectiles/index/visual-assets.csv');contexts=rows('projectiles/index/visual-contexts.csv')
    projected=load(ROOT/'projectiles/index/work-analysis-current.json')
    context_details=load(ROOT/projected['snapshot']/'contexts.json')
    candidates=[]
    for n,s in state.items():
        if s['spatial_state'] in {'not-started','blocked'}:continue
        p=ROOT/'effects/ressources'/n/'source.bam'
        if p.exists():candidates.append(dict(domain='effects',resref=n,source=str(p.relative_to(ROOT)),spatial_state=s['spatial_state'],spatial_run=s['spatial_run'],interpolation_run=s['interpolation_run'],qa_state=s['qa_state'],selected_run=s['selected_run']))
    for row in rows('animations/index/animation_upscale_registry.csv'):
        if not row['selected_run']:continue
        n=row['resref'];p=ROOT/'animations/ressources'/n/'source.bam'
        if p.exists():candidates.append(dict(domain='animations',resref=n,source=str(p.relative_to(ROOT)),selected_run=row['selected_run'],qa_decision=row.get('qa_decision'),status=row['status']))
    indexes={kind:defaultdict(set) for kind in ('anchored','intrinsic','mask','pattern')}
    full=defaultdict(list);decoded={};skipped=[]
    for number,a in enumerate(candidates,1):
        ident=a['domain']+':'+a['resref']
        try:sig=signatures(ROOT/a['source'])
        except Exception as exc:skipped.append(dict(source=a,error=repr(exc)));continue
        decoded[ident]=sig;full[sig['canonical_sha256']].append(ident)
        for i in sig['used']:
            f=sig['frames'][i]
            if f.get('blank'):continue
            for kind in indexes:
                if f.get(kind):indexes[kind][f[kind]].add(ident)
        if number%100==0:print('indexed',number,'/',len(candidates),flush=True)
    details={a['domain']+':'+a['resref']:a for a in candidates}
    results=[]
    for a in targets:
        n=a['resref'];sig=signatures(ROOT/a['source']);usable=[f for f in sig['frames'] if f['frame'] in sig['used'] and not f.get('blank')]
        hit_counts={kind:Counter() for kind in indexes};unique={kind:set(f[kind] for f in usable if f.get(kind)) for kind in indexes}
        for kind in indexes:
            for key in unique[kind]:
                for ident in indexes[kind].get(key,()):hit_counts[kind][ident]+=1
        matches=[]
        for kind in ('anchored','intrinsic','pattern','mask'):
            for ident,count in hit_counts[kind].most_common(8):
                if kind in {'mask','pattern'} and count<max(2,len(unique[kind])*.75):continue
                matches.append(dict(kind=kind,target_unique_poses=len(unique[kind]),covered_unique_poses=count,
                                    full_target_coverage=count==len(unique[kind]),candidate=details[ident]))
        native_masks=[p for p in projectiles if n in {p['canonical_bam'],*p['projectile_bams'].split(';'),*p['exact_source_aliases'].split(';')} and 'native-mask-no-ai' in p['actions']]
        native_contexts=[v for v in context_details.values() if n in v.get('bams',[]) and v.get('action')=='native-mask-no-ai']
        local=[]
        for p in sorted((ROOT/'effects/ressources'/n/'runs').glob('*/run.json')):
            d=load(p);local.append(dict(path=str(p.relative_to(ROOT)),pipeline=d.get('pipeline',{}).get('id'),result=d.get('result')))
        strict=full.get(sig['canonical_sha256'],[])
        reusable=[m for m in matches if m['kind']=='anchored' and m['full_target_coverage']]
        decision='reuse-existing-images-adapt-contract' if strict or reusable else 'native-projectile-mask-no-ai' if native_masks else 'new-distinct-visual'
        if n=='WTRBODY2':decision='related-WTRBODY1-not-exact-duplicate'
        results.append(dict(ordinal=a['ordinal'],resref=n,decision=decision,source_sha256=a['source_sha256'],source_frames=len(sig['frames']),
                            used_frames=len(sig['used']),unique_used_rgba_poses=len(unique['anchored']),canonical_matches=[details[i] for i in strict],
                            pose_matches=matches,projectile_native_masks=native_masks,
                            projectile_contexts=[{k:v.get(k) for k in ['bams','action','coverage_level','uses','projectiles','runtime_tint_blend']} for v in native_contexts],
                            local_run_descriptors=local))
    assert all(sha(p.read_bytes())==before[str(p.relative_to(ROOT))] for p in authority)
    summary=dict(targets=50,indexed_existing_sources=len(decoded),skipped=len(skipped),decisions=dict(Counter(r['decision'] for r in results)))
    save(OUT/'audit.json',dict(date='2026-11-08',summary=summary,assets=results,indexed_sources=candidates,skipped=skipped,
                             unchanged_authorities=before,projectiles_snapshot=projected,
                             limits=['Pose equality does not grant same timing/palette/owner/route.','Mask/pattern matches are reuse clues only, not accepted RGB equivalence.','No inference, installation, QA or cross-domain tracking changes.']))
    with (OUT/'audit.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['ordinal','resref','decision','unique_used_rgba_poses','anchored_full_matches','intrinsic_full_matches','projectile_mask'])
        w.writeheader()
        for r in results:w.writerow(dict(ordinal=r['ordinal'],resref=r['resref'],decision=r['decision'],unique_used_rgba_poses=r['unique_used_rgba_poses'],
            anchored_full_matches=';'.join(m['candidate']['domain']+':'+m['candidate']['resref'] for m in r['pose_matches'] if m['kind']=='anchored' and m['full_target_coverage']),
            intrinsic_full_matches=';'.join(m['candidate']['domain']+':'+m['candidate']['resref'] for m in r['pose_matches'] if m['kind']=='intrinsic' and m['full_target_coverage']),projectile_mask=bool(r['projectile_native_masks'])))
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    for r in results:
        if r['decision']!='new-distinct-visual' or r['pose_matches']:print(r['resref'],r['decision'],[(m['kind'],m['candidate']['resref'],m['covered_unique_poses'],m['target_unique_poses']) for m in r['pose_matches'][:4]])

if __name__=='__main__':main()
