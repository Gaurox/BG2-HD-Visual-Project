"""Scoped lot3 finishing, interpolation, native tile recut, sibling-safe area packs."""
from common import *
import json
from PIL import Image,ImageDraw
from scipy.ndimage import label, distance_transform_edt
from build_alpha_feather import inner_feather_ramp
from build_spatial_spline_alpha import potrace_alpha
import split_animation_pack_by_area as split
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
from workspace_paths import get_path

def payload(p):
    return {f.name:v.sha256_file(f) for f in sorted(p.iterdir()) if f.is_file() and f.name!='manifest.json'} if p.exists() else None

def prepare():
    records=[]
    for run,ref,radius in [(SEED,'AM1001A',4),(SEED,'AM1512PA',4),(REB,'AM2008A',0)]:
        _,rs,_=v.load_base_pack(run/'03_runtime_pack'); r=next(r for r in rs if r['resref']==ref)
        arrays={}; masks=[]
        for f in r['frames']:
            p=pixels(run/'03_runtime_pack',f)
            if radius:
                source=p[...,3].copy()
                alpha,report=potrace_alpha(source,threshold=127,alphamax=.8,opttolerance=.2,supersample=8,band=6)
                alpha=np.rint(alpha*inner_feather_ramp(alpha,radius)).astype(np.uint8)
                # New anti-aliased edge pixels inherit nearest visible material, without blurring the jet.
                grown=(alpha>0)&(source==0)
                nearest=distance_transform_edt(source==0,return_distances=False,return_indices=True)
                p[...,:3][grown]=p[...,:3][tuple(nearest)][grown]
                p[...,3]=alpha; masks.append(dict(frame=f['frame'],**report))
            p[p[...,3]==0,:3]=0
            arrays[(ref,f['frame'])]=p
        hashes=[__import__('hashlib').sha256(p.tobytes()).hexdigest() for p in arrays.values()]
        assert len(set(hashes))==len(hashes),ref+': duplicate spatial poses require explicit hold treatment'
        base=write_pack(BATCH/('base-'+ref),[r],arrays)
        records.append(dict(resref=ref,stored_poses=len(hashes),duplicate_stored_poses=0,
            native_lookup=r['cycles'],collapse_uniform_duplicate_holds=ref=='AM1512PA',mask_reports=masks,
            radius_x4=radius,source_pack=rel(run/'03_runtime_pack'),source_pack_manifest_sha256=v.sha256_file(run/'03_runtime_pack/manifest.json')))
        temporal(base,ref,ref=='AM1512PA')
    v.write_json(BATCH/'preparation.json',records)

def recut():
    whole=temporal(BATCH/'context-base','AM0902L')
    _,wr=v.validate_v2_pack(whole); complete=wr[0]
    whole_cycle=complete['cycles'][0]['timeline_frame_indices']
    assert len(whole_cycle)==16
    _,rs,_=v.load_base_pack(REB/'03_runtime_pack'); r=copy.deepcopy(next(r for r in rs if r['resref']=='AM0902L'))
    r.update(playback_mode='TimedTimeline',native_fps=dict(numerator=15,denominator=1),
             target_fps=dict(numerator=30,denominator=1))
    # Field names match the temporal writer, copied directly from its resource.
    r['native_fps']=complete['native_fps']; r['target_fps']=complete['target_fps']
    frames=copy.deepcopy(r['frames']); arrays={}
    for tile,c in enumerate(r['cycles']):
        timeline=[]
        for slot,native in enumerate(c['native_frame_indices']):
            for parity in (0,1):
                index=native if parity==0 else 32+tile*8+slot
                f=copy.deepcopy(r['frames'][native]); f['frame']=index
                if parity: frames.append(f)
                p=pixels(whole,complete['frames'][whole_cycle[slot*2+parity]])
                cx,cy=f['centre_x1']; w,h=f['physical_size_x4']; x,y=(129-cx)*4,(158-cy)*4
                arrays[('AM0902L',index)]=p[y:y+h,x:x+w].copy()
                timeline.append(index)
        c['timeline_frame_indices']=timeline
    r['frames']=sorted(frames,key=lambda f:f['frame']);r['frame_count']=64
    write_pack(BATCH/'recut-AM0902L',[r],arrays)

def sweep(r,pack):
    tests=[]
    for radius in [4,8,12,16]:
        losses=[]; cores=[]; sparks=[]
        for f in r['frames']:
            p=pixels(pack,f); a=p[...,3]; ramp=inner_feather_ramp(a,radius)
            lum=p[...,:3].astype(float)@np.array([.2126,.7152,.0722]); energy=lum*a/255
            mask=a>0; core=mask&(lum>=np.percentile(lum[mask],90))
            cores.append(1-(energy*ramp)[core].sum()/max(energy[core].sum(),1))
            losses.append(1-(energy*ramp).sum()/max(energy.sum(),1))
            ids,_=label(mask,np.ones((3,3))); counts=np.bincount(ids.ravel());small=(counts>0)&(counts<=48);small[0]=False
            tiny=small[ids]&(lum>20)
            if tiny.any(): sparks.append(1-(energy*ramp)[tiny].sum()/max(energy[tiny].sum(),1))
        tests.append(dict(radius_x4=radius,max_core_loss_pct=100*max(cores),mean_energy_loss_pct=100*float(np.mean(losses)),
                          max_tiny_component_loss_pct=100*max(sparks,default=0)))
    eligible=[t for t in tests if t['max_core_loss_pct']<=5 and t['mean_energy_loss_pct']<=35 and t['max_tiny_component_loss_pct']<=20]
    selected=max([t['radius_x4'] for t in eligible],default=0)
    v.write_json(BATCH/'feather-sweep.json',dict(tests=tests,selected_radius_x4=selected,
                 rule='largest radius with core loss <=5%, mean energy loss <=35%, tiny bright components loss <=20%; otherwise keep alpha'))
    return selected

def finish():
    resources=[];arrays={};checks=[];radius=0
    for ref in AREAS:
        pack=BATCH/('recut-AM0902L' if ref=='AM0902L' else 'temporal-'+ref+'/03_runtime_pack')
        _,rs=v.validate_v2_pack(pack);r=copy.deepcopy(next(r for r in rs if r['resref']==ref))
        if ref=='AM2008A':radius=sweep(r,pack)
        for f in r['frames']:
            p=pixels(pack,f)
            if ref=='AM2008A':
                if radius:p[...,3]=np.rint(p[...,3]*inner_feather_ramp(p[...,3],radius)).astype(np.uint8)
                p[...,:3]=np.rint(p[...,:3].astype(float)*p[...,3,None]/255).astype(np.uint8)
            p[p[...,3]==0,:3]=0
            arrays[(ref,f['frame'])]=p
        if ref=='AM0902L':
            # Feather the complete silhouette before recutting; internal tile edges never see padding.
            whole=BATCH/'temporal-AM0902L/03_runtime_pack'
            full_r=v.validate_v2_pack(whole)[1][0]
            for phase,full_index in enumerate(full_r['cycles'][0]['timeline_frame_indices']):
                p=pixels(whole,full_r['frames'][full_index])
                p[...,3]=np.rint(p[...,3]*inner_feather_ramp(p[...,3],2)).astype(np.uint8)
                p[p[...,3]==0,:3]=0
                for c in r['cycles']:
                    index=c['timeline_frame_indices'][phase];f=r['frames'][index]
                    cx,cy=f['centre_x1'];w,h=f['physical_size_x4'];x,y=(129-cx)*4,(158-cy)*4
                    arrays[(ref,index)]=p[y:y+h,x:x+w].copy()
        native=v.load_base_pack((REB if ref in ['AM0902L','AM2008A'] else SEED)/'03_runtime_pack')[1]
        original=next(x for x in native if x['resref']==ref)
        durations=[]
        for c,old in zip(r['cycles'],original['cycles']):
            assert c['native_frame_indices']==old['native_frame_indices']
            assert len(c['timeline_frame_indices'])==2*len(old['native_frame_indices'])
            durations.append(len(c['timeline_frame_indices'])/30)
        for old in original['frames']:
            new=r['frames'][old['frame']]
            assert (old['logical_size_x1'],old['physical_size_x4'],old['centre_x1'])==(new['logical_size_x1'],new['physical_size_x4'],new['centre_x1'])
        resources.append(r)
        checks.append(dict(resref=ref,frame_count=r['frame_count'],cycle_durations_seconds=durations,
            input_duplicate_holds_removed=ref=='AM1512PA',native_geometry_and_lookups_preserved=True,
            temporal_pack=rel(pack),temporal_pack_manifest_sha256=v.sha256_file(pack/'manifest.json')))
    final=write_pack(BATCH/'final-assets',resources,arrays)
    splitroot=ROOT/'animations/packs-par-zone'/(TAG+'-assets')
    split.split(final,splitroot,ROOT/'animations/index/occurrences.csv',False)
    game=get_path('bg2ee_game_root');lock=v.load_json(ROOT/'animations/index/area-pack-lock.json')
    baseline={};selected=[]
    for ref,areas in AREAS.items():
        for area in areas:
            live=game/'iee-assets/areas'/area;before=payload(live);specs=[]
            baseline[area]=dict(present=live.exists(),payload=before)
            if live.exists():
                build=lock['areas'][area]['build'];inputs=build.get('merged_from') or [build['leaf']]
                root=ROOT/'animations/packs-par-zone'/(TAG+'-baseline-'+area)
                merge.merge([str(ROOT/p) for p in inputs],area,root,False)
                preserved=root/area;assert payload(preserved)==before,area+': installed baseline differs'
                specs.append(str(preserved))
            specs.append(str(splitroot/area)+'::'+ref)
            dest=ROOT/'animations/packs-par-zone'/(TAG+'-merged-'+area)
            merge.merge(specs,area,dest,False);selected.append(dest)
            after=payload(dest/area)
            for name,digest in (before or {}).items():
                if name!=v.REGISTRY_NAME:assert after[name]==digest,area+'/'+name
            baseline[area]['output_payload']=after
    complete=ROOT/'animations/packs-par-zone'/(TAG+'-complete');combine.combine(selected,complete,False)
    v.write_json(BATCH/'baseline.json',baseline)
    v.write_json(BATCH/'checks.json',dict(status='completed',resources=checks,siblings_preserved=True,
        shared_tiles_interpolated_together=True,unchanged_cycle_durations=True,qa_status='pending-ingame'))
    for ref in AREAS:
        run=REB if ref in ['AM0902L','AM2008A'] else SEED
        wrapper=ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-{TAG}'
        wrapper.mkdir(parents=True,exist_ok=False)
        leaf=splitroot/AREAS[ref][0]
        check=next(c for c in checks if c['resref']==ref)
        v.write_json(wrapper/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),
            resrefs=[ref],resref=ref,source_run=rel(run),source_run_manifest_sha256=v.sha256_file(run/'manifest.json'),
            temporal_pack=check['temporal_pack'],temporal_pack_manifest_sha256=check['temporal_pack_manifest_sha256'],
            source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),
            output_split_root=rel(splitroot),output_manifest_sha256=v.sha256_file(splitroot/'manifest.json'),
            recipe=dict(spatial='ReboutCX context seam-only' if ref=='AM0902L' else 'ReboutCX' if ref=='AM2008A' else 'SeedVR2 7B INT8 LAB',
                        scale=4,temporal='Apollo8',target_fps=30,duplicate_holds='collapse uniform x2, input 7.5 fps' if ref=='AM1512PA' else 'none',
                        contour='native union, outer silhouette only; no internal fading' if ref=='AM0902L' else 'inner feather' if ref=='AM2008A' else 'Potrace sharp corners, band6',
                        inner_feather_x4=radius if ref=='AM2008A' else 2 if ref=='AM0902L' else 4,
                        rgb='premultiply once' if ref=='AM2008A' else 'straight alpha; RGB zero under alpha0',
                        occlusion='installed native occlusion bridge; no static WED clipping'),
            qa_status='pending-ingame',release_status='not-selected'))
    v.write_json(BATCH/'manifest.json',dict(schema='bg2-upscale-animation-batch-production-v1',status='completed',created_utc=v.utc_now(),
        resrefs=list(AREAS),complete_pack=rel(complete),asset_pack=rel(splitroot),recipe_script=rel(Path(__file__)),
        qa_status='pending-ingame',release_status='not-selected'))
    preview(resources,arrays)
    print('COMPLETE',rel(complete),flush=True)

def preview(resources,arrays):
    sheet=Image.new('RGB',(1200,700),(34,34,34));draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(resources):
        if r['resref']=='AM0902L':
            p=np.zeros((1268,1024,4),np.uint8)
            for c in r['cycles']:
                f=r['frames'][c['timeline_frame_indices'][0]];part=arrays[(r['resref'],f['frame'])]
                cx,cy=f['centre_x1'];h,w=part.shape[:2];x,y=(129-cx)*4,(158-cy)*4
                p[y:y+h,x:x+w]=part
        else:p=arrays[(r['resref'],0)]
        image=Image.fromarray(p);bg=Image.new('RGBA',image.size,(34,34,34,255))
        if r['resref']=='AM2008A':image=Image.fromarray(np.minimum(p[...,:3].astype(np.uint16)+34,255).astype(np.uint8))
        else:image=Image.alpha_composite(bg,image).convert('RGB')
        image.thumbnail((570,290),Image.Resampling.LANCZOS)
        x=(i%2)*600;y=(i//2)*350
        sheet.paste(image,(x+(600-image.width)//2,y+40))
        draw.text((x+16,y+12),r['resref']+' x4 / 30fps',fill='white')
    sheet.save(BATCH/'preview.png')

if __name__=='__main__':
    mode=sys.argv[1]
    {'prepare':prepare,'recut':recut,'finish':finish}[mode]()
