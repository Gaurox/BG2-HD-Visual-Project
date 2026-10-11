"""Only versions supported by acquired QA; current installations are checked separately."""
from common import *
PACKS=ROOT/'animations/packs-par-zone'
BASE=PACKS/'combined-20260904-fpit1s-contour-fondu-J'
PLAN={}
def add(refs,root,date):
    for ref in refs.split():PLAN[ref]=dict(root=PACKS/root,date=date)
add('AM0033AB','combined-20260904-fpit1s-contour-fondu-J','2026-08-27')
add('AM0205A AM0205B AM0205C AM0205D AM0205E','combined-20260904-fpit1s-contour-fondu-J','2026-08-21')
add('AM0602AA AM0602AB AM0602AC AM0602B AM0602C AM0602D AM0602E AM0602F AM0602G PORTL1A PORTL1B','bubbles2-xbr2x-blend-3areas-premultiply-budget-20260905','2026-09-05')
add('AM0602J AM0602K1 AM0602K2 AM0602L1 AM0602L2 AM0602M','combined-20260904-fpit1s-contour-fondu-J','2026-08-23')
PLAN['AM0602J']['date']='2026-09-02'
add('AM0604A','combined-20260904-fpit1s-contour-fondu-J','2026-08-23')
add('AM0700A AM0700B AM0700C AM0700D FIRE_1','combined-20260827-plus-flame2s-ar0602-radialA','2026-08-27')
add('AM0900DM','combined-20260827-ar0900-two-manual-masks-v3','2026-08-27')
add('AM1400N','combined-20260828-plus-ar1400-fountains-only','2026-08-28')
add('AM2100PA AM2100PB AM2100PC','combined-20260901-ar2100-portals-30fps-v2','2026-09-01')
add('AM2201A AM2201B','combined-20260901-active-plus-am2201ab-spline-fit1-feather1-30fps-v2','2026-09-01')
add('AM307TT1 AM307UR1 AM307UR2 AM307UR3','combined-20260831-ar0307-ar0329-six-bam-30fps-v2','2026-08-31')
add('BUTRFLY','combined-20260901-chimsmk-dstdvl-butterfly-xbr2x-nearest2-30fps-v3-opaque-rgb-dilate-blend-safe-zero-candidate','2026-09-01')
add('CHIMSMK','combined-20260901-chimsmk-oval-dstdvl1a-b-c-activefade7-20-7-candidate','2026-09-01')
add('PORTL2A','combined-20260828-ar0603-portal-spline-feather8','2026-08-28')

def legacy_resources(ref,area):
    leaf=PLAN[ref]['root']/area;evidence=[]
    if ref=='FIRE_1':leaf=PLAN[ref]['root']/'AR0700'
    if ref=='CHIMSMK' and area in ['AR1100','AR2000']:leaf=PLAN['BUTRFLY']['root']/area
    if ref=='AM0604A':leaf=ROOT/'animations/runs/ar0604-apo8-x4-30fps-v2/03_runtime_pack'
    if ref.startswith('AM0205'):leaf=ROOT/'animations/runs/ar0602-eau-seedvr3b-lab-x4/04_ingame_test/03_am0205_recovered_pack'
    rr=copy.deepcopy(resources(leaf,ref));assert rr,(ref,area,leaf)
    verify_assets(leaf,rr);sources=source_assets(leaf,rr)
    evidence.append(dict(path=rel(leaf/'manifest.json'),sha256=digest(leaf/'manifest.json')))
    if ref.startswith('AM0205'):
        assert v.runtime_v1.registry_from_resources(resources(leaf))==(leaf/v.REGISTRY_NAME).read_bytes()
        rr=[v.normalise_v1_resource(r) for r in rr]
    if ref in ['AM0205A','AM0205B','AM0205C','AM0205D']:
        # Original V1 assets and slot map, preserved in a later recovery pack.
        # V2 Native encoding is equivalent; no later timed interpolation is accepted here.
        r=rr[0];assert len(rr)==1 and r['frame_count']==27
        old=ROOT/'animations/runs'/f'{ref}-pod-canvas-feather-x4';m=load(old/'manifest.json')
        assert m['frame_count']==27 and m['alpha_operation']['canvas_edge_radius_physical_x4']==32
        for f,a in zip(m['frames'],r['assets'][:27]):
            assert Path(f['runtime_asset']).name==a['name'] and f['runtime_sha256']==a['sha256'] and f['runtime_bytes']==a['bytes']
            assert digest(old/f['runtime_asset'])==a['sha256']
        assert r['cycles'][0]['native_frame_indices']==list(range(27))
        proof=leaf/v.REGISTRY_NAME
        sources=source_assets(leaf,rr)
        evidence+= [dict(path=rel(old/'manifest.json'),sha256=digest(old/'manifest.json')),
                    dict(path=rel(proof),sha256=digest(proof))]
    if area=='AR0602':
        approval=ROOT/'releases/BG2-HD-Upscale/manifests/animation-qa-approvals/AR0602/qa-v3-ef4ac04675374e8a.json'
        qa=load(approval);assert qa['status']=='accepted' and digest(leaf/'manifest.json')==qa['pack_manifest_sha256'].lower()
        match=next(e for e in qa['evidence'] if ref in e.get('accepted_resrefs',[]))
        assert digest(path(match['path']))==match['sha256'].lower()
        assert digest(path(match['source_pack'])/'manifest.json')==match['pack_manifest_sha256'].lower()
        current_group=workflow._resource_group(resources(leaf),ref)
        old_group=workflow._resource_group(resources(path(match['source_pack'])),ref)
        assert current_group==old_group,ref+': later area QA carry-forward is not identical'
        evidence.append(dict(path=rel(approval),sha256=digest(approval),decision_date=qa['decision_date'],kind=qa['decision_origin']))
    return rr,sources,leaf,evidence

if __name__=='__main__':
    rr=[r for r in rows() if r['resref'] in PLAN];assert len(rr)==43
    for r in rr:
        ref=r['resref']
        for area in r['areas'].split(';'):
            target,_,leaf,_=legacy_resources(ref,area)
            print(ref,area,[(x['frame_count'],x['playback_mode']) for x in target], 'installed-identical='+str(same_live(leaf,target,area)),flush=True)
