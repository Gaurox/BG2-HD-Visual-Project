"""Verify final pixels/geometry; preserve siblings; transactional two-map install."""
from pathlib import Path
import argparse, sys, shutil
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
sys.path.insert(0,str(ROOT/'pipeline/area-animation-area-test'))
sys.path.insert(0,str(ROOT/'engine/InfinityEngine-Enhancer/source-patchee/tools'))
import run_animation_upscale_30fps_v2 as v2
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
import area_animation_area_test as installer
import install_renderer_candidate as renderer
from workspace_paths import get_path
TAG='portails-deux-correctif-20261010-v1'; BATCH=ROOT/'animations/batches'/TAG
PACK=ROOT/'animations/packs-par-zone'/(TAG+'-complete')
BASE=ROOT/'animations/packs-par-zone/portails-cinq-selection-20261010-v1-complete'
GAME=get_path('bg2ee_game_root')
def rel(p): return Path(p).resolve().relative_to(ROOT).as_posix()
def payload(leaf):
    _,resources=v2.validate_v2_pack(leaf)
    return {name:v2.sha256_file(leaf/name) for name in [v2.REGISTRY_NAME]+[a['name'] for r in resources for a in r['assets']]}
def raw(leaf,f):
    w,h=f['physical_size_x4']; return np.frombuffer((leaf/f['asset']).read_bytes(),np.uint8).reshape(h,w,4)
def composite(a):
    h,w=a.shape[:2]; yy,xx=np.indices((h,w)); bg=np.where(((yy//24+xx//24)%2)[...,None],np.array([38,42,49]),np.array([19,23,30]))
    return Image.fromarray(np.minimum(bg+a[:,:,:3],255).astype(np.uint8))
def verify():
    results=[]; jobs=[]; previews=BATCH/'previews'; previews.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
    for ref,area,selected in [('OHHPORT','AR0811',8),('BDFORCEW','OH8100',50)]:
        job=v2.load_json(BATCH/(ref+'-job.json')); jobs.append(job)
        final=ROOT/job['final_split']/area
        _,rs=v2.validate_v2_pack(final); r=rs[0]
        temporal=ROOT/job['temporal_run']/'03_runtime_pack'; prior=v2.validate_v2_pack(temporal)[1][0]
        old=BASE/area; oldr=next(q for q in v2.validate_v2_pack(old)[1] if q['resref']==ref)
        assert r['cycles']==oldr['cycles'] and r['frame_count']==oldr['frame_count']
        changed=[]; corners=[]
        for f,b,oldf in zip(r['frames'],prior['frames'],oldr['frames'],strict=True):
            assert all(f[k]==b[k]==oldf[k] for k in ['logical_size_x1','physical_size_x4','centre_x1'])
            a=raw(final,f); original=raw(temporal,b)
            assert np.all(a[:,:,3]<=original[:,:,3])
            assert np.array_equal(a[:,:,:3],np.rint(original[:,:,:3].astype(np.float32)*(a[:,:,3,None]/255.)).astype(np.uint8))
            assert not a[a[:,:,3]==0,:3].any()
            if f['sha256']!=oldf['sha256']: changed.append(f['frame'])
            if ref=='OHHPORT':
                for patch in [a[:8,:8],a[:8,-8:],a[-8:,:8],a[-8:,-8:]]: assert not patch.any()
                corners.append(f['frame'])
        if ref=='OHHPORT':
            assert not (set(changed)&{0,1,3,4,5}), 'unaffected native frames changed'
        f=r['frames'][selected]; a=raw(final,f); b=raw(old,oldr['frames'][selected])
        left,right=composite(b),composite(a)
        if left.height>550:
            left=left.resize((left.width//2,left.height//2),Image.Resampling.BOX); right=right.resize(left.size,Image.Resampling.BOX)
        board=Image.new('RGB',(left.width*2+16,left.height+66),(20,23,29)); board.paste(left,(0,66)); board.paste(right,(left.width+16,66))
        d=ImageDraw.Draw(board); d.text((12,8),f'{ref} — frame {selected}',font=font,fill='white'); d.text((12,36),'Avant',font=font,fill='white'); d.text((left.width+28,36),'Correctif',font=font,fill='white')
        board.save(previews/(ref+'-before-after.png'))
        results.append(dict(resref=ref,frames=r['frame_count'],changed_frames=changed,geometry_centres_cycles_identical=True,premultiplied_once=True,zero_rgb_under_zero_alpha=True,all_phase_background_corners_transparent=(len(corners)==12 if ref=='OHHPORT' else None),manifest=rel(final/'manifest.json'),manifest_sha256=v2.sha256_file(final/'manifest.json')))
    v2.write_json(BATCH/'local-checks.json',dict(status='passed',resources=results,ingame_QA='pending-user-verification'))
    return jobs
def prepare():
    jobs=verify(); checks=[]; roots=[]
    for job in jobs:
        ref=job['resref']; area='AR0811' if ref=='OHHPORT' else 'OH8100'
        before=payload(BASE/area)
        actual={p.name:v2.sha256_file(p) for p in (GAME/'iee-assets/areas'/area).iterdir() if p.is_file()}
        assert actual==before,f'{area}: installed baseline differs'
        _,rs=v2.validate_v2_pack(BASE/area)
        specs=[str(BASE/area)+'::'+r['resref'] for r in rs if r['resref']!=ref]
        specs.append(str(ROOT/job['final_split']/area)+'::'+ref)
        output=BATCH/'complete-area-packs'/area
        merge.merge(specs,area,output,output.exists())
        leaf=output/area; after=payload(leaf)
        kept={n:h for n,h in before.items() if n!=v2.REGISTRY_NAME and not n.startswith('AAX4-'+ref+'-')}
        assert all(after.get(n)==h for n,h in kept.items())
        plan=installer.install_area_pack(leaf,verify_only=True); assert not plan.dropped
        checks.append(dict(area_id=area,resref=ref,preserved_frames=len(kept),incoming_bytes=plan.incoming_bytes,before_payload=before)); roots.append(output)
    if not PACK.exists(): combine.combine(roots,PACK,False)
    candidate=BATCH/'renderer-candidate'; candidate.mkdir(exist_ok=True)
    shutil.copy2(BATCH/'.work/runtime-build/Release/InfinityEngine-Enhancer.dll',candidate/'InfinityEngine-Enhancer.dll')
    shutil.copy2(GAME/'InfinityEngine-Enhancer.ini',candidate/'InfinityEngine-Enhancer.ini')
    renderer.install_candidate(candidate,verify_only=True)
    v2.write_json(BATCH/'selection.json',dict(schema='bg2-two-animation-repair-install-v1',status='prepared',created_utc=v2.utc_now(),resources=jobs,area_checks=checks,complete_pack=rel(PACK),renderer_candidate=rel(candidate),renderer_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.dll'),ini_sha256=v2.sha256_file(candidate/'InfinityEngine-Enhancer.ini'),release='not-selected'))
    print('Prepared AR0811 + OH8100 and scoped renderer',flush=True)
def install():
    record=v2.load_json(BATCH/'selection.json'); tests=v2.load_json(BATCH/'renderer-tests.json')
    assert tests['passed']
    out=BATCH/'installation.json'; receipt=v2.load_json(out) if out.exists() else dict(status='installing',areas=[],renderer=None,ingame_QA='pending-user-verification',release='not-selected')
    if not receipt['renderer']:
        assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')=='70a2745b212babe378c6ccd8b1660110ad3aac5a9ef7523ecbbfcea776bb6d09'
        assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==record['ini_sha256']
        result=renderer.install_candidate(ROOT/record['renderer_candidate'])
        receipt['renderer']=dict(status=result.status,receipt=rel(result.receipt_path),dll_sha256=record['renderer_sha256'],ini_preserved=True)
        v2.write_json(out,receipt)
    for check in record['area_checks']:
        area=check['area_id']; leaf=PACK/area
        if any(a['area_id']==area for a in receipt['areas']):
            assert payload(leaf)=={p.name:v2.sha256_file(p) for p in (GAME/'iee-assets/areas'/area).iterdir() if p.is_file()}; continue
        assert {p.name:v2.sha256_file(p) for p in (GAME/'iee-assets/areas'/area).iterdir() if p.is_file()}==check['before_payload']
        result=installer.install_area_pack(leaf)
        installer.record_lock(area,leaf,GAME)
        receipt['areas'].append(dict(area_id=area,status=result.status,receipt=rel(result.receipt_path),preserved_frames=check['preserved_frames'],pack_manifest_sha256=v2.sha256_file(leaf/'manifest.json')))
        v2.write_json(out,receipt)
        print('INSTALLED '+area,flush=True)
    assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.dll')==record['renderer_sha256']
    assert v2.sha256_file(GAME/'InfinityEngine-Enhancer.ini')==record['ini_sha256']
    receipt['status']='installed'; v2.write_json(out,receipt)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--install',action='store_true');p.add_argument('--verify',action='store_true');a=p.parse_args()
    install() if a.install else verify() if a.verify else prepare()
