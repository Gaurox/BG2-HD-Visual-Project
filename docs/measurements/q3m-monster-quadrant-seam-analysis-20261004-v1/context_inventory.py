"""Read-only native frame/context aliases needed for full contextual repair."""
import json,sys
from collections import defaultdict
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from q3m_family_witnesses import source_plan
from palette_work_plan import write_json
prior=HERE.parent/'q3m-monster-quadrant-full-x2-20261004-v1';selection=json.loads((prior/'selection.json').read_text())
rr,works,_=source_plan(prior/'selection.json','monster_quadrant');source={(r['witness']['animation_id'],r['resref']):r for r in rr}
records=[]
for witness in selection['witnesses']:
    aid=witness['animation_id'];contexts=set();pairs=defaultdict(set);slots=0;relevant=defaultdict(set);seen=set()
    for group in witness['multipart_groups']:
        rs=[source[(aid,ref)] for ref in group]
        for seq in range(min(len(r['cycles']) for r in rs)):
            for slot in range(min(len(r['cycles'][seq]) for r in rs)):
                fi=[r['cycles'][seq][slot] for r in rs]
                if any(f>=len(r['frames']) for r,f in zip(rs,fi)):continue
                rows=[r['frames'][f] for r,f in zip(rs,fi)]
                seen.update((r['resref'],f) for r,f in zip(rs,fi))
                sig=tuple((row['key'],tuple(row['geometry'])) for row in rows);contexts.add(sig);slots+=1
                for n,(r,f,row) in enumerate(zip(rs,fi,rows)):
                    if not row['geometry'][0]*row['geometry'][1]:continue
                    pairs[(r['resref'],f)].add(sig)
                    # Only neighboring RGB/index input within eight source pixels
                    # of this part, excluding its own entry. Includes holes/material.
                    a=row['geometry'];L=-a[2];T=-a[3];R=L+a[0];B=T+a[1];near=[]
                    for j,(other,otherrow) in enumerate(zip(rs,rows)):
                        if j==n:continue
                        b=otherrow['geometry'];l=-b[2];t=-b[3];right=l+b[0];bottom=t+b[1]
                        if not b[0]*b[1] or right<L-8 or l>R+8 or bottom<T-8 or t>B+8:continue
                        native=works[otherrow['key']]['frame'].indices
                        x0=max(0,L-8-l);x1=min(b[0],R+8-l);y0=max(0,T-8-t);y1=min(b[1],B+8-t)
                        near.append((l+x0,t+y0,native[y0:y1,x0:x1].shape,native[y0:y1,x0:x1].tobytes(),other['profile'].metadata()))
                    relevant[(r['resref'],f)].add(tuple(near))
    conflicts=[dict(resref=r,frame_index=f,contexts=len(c),near_edge_contexts=len(relevant[(r,f)])) for (r,f),c in pairs.items() if len(c)>1]
    declared={(ref,f) for ref in witness['refs'] for f in range(len(source[(aid,ref)]['frames']))}
    rec=dict(animation_id=aid,native_synchronized_slots=slots,unique_palette_geometry_contexts=len(contexts),declared_native_frames=len(declared),referenced_native_frames=len(seen),unreferenced_native_frames=len(declared-seen),native_frames_reused_across_contexts=len(conflicts),native_frames_with_different_near_edge_neighbors=sum(len(c)>1 for c in relevant.values()),examples=conflicts[:8])
    records.append(rec);print(json.dumps(rec),flush=True)
write_json(HERE/'context-inventory.json',dict(role='read-only-repair-planning',records=records,global_cache_modified=False,installed_files_changed=False))
