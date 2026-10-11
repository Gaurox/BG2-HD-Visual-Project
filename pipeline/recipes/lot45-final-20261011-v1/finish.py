from common import *
import hashlib,shutil
from scipy.ndimage import label
from build_alpha_feather import inner_feather_ramp
import merge_area_pack_resources as merge
import combine_area_pack_splits as combine
from PIL import Image,ImageDraw

def sweep(pack,r,tag):
    tests=[]
    radii=[4,8,12,16] if r['resref']=='AM3000E' else [2,4,6,8]
    for radius in radii:
        cores=[];losses=[];sparks=[]
        for f in r['frames']:
            p=pixels(pack,f);a=p[...,3];lum=p[...,:3].astype(float)@np.array([.2126,.7152,.0722])
            energy=lum*a/255;visible=a>0;ramp=inner_feather_ramp(a,radius)
            core=visible&(lum>=np.percentile(lum[visible],90))
            cores.append(1-(energy*ramp)[core].sum()/max(energy[core].sum(),1))
            losses.append(1-(energy*ramp).sum()/max(energy.sum(),1))
            ids,_=label(visible,np.ones((3,3)));counts=np.bincount(ids.ravel());small=(counts>0)&(counts<=48);small[0]=False
            tiny=small[ids]&(lum>20)
            if tiny.any():sparks.append(1-(energy*ramp)[tiny].sum()/max(energy[tiny].sum(),1))
        tests.append(dict(radius_x4=radius,max_core_loss_pct=100*max(cores),mean_energy_loss_pct=100*float(np.mean(losses)),
                          max_tiny_component_loss_pct=100*max(sparks,default=0)))
    eligible=[t for t in tests if t['max_core_loss_pct']<=5 and t['mean_energy_loss_pct']<=10 and t['max_tiny_component_loss_pct']<=20]
    selected=max([t['radius_x4'] for t in eligible],default=0)
    v.write_json(BATCH/('feather-'+tag+'.json'),dict(tests=tests,selected_radius_x4=selected,
        rule='largest radius with max core loss <=5%, mean energy <=10%, tiny luminous components <=20%'))
    return selected

def deduplicate(r,arrays):
    before=r['frame_count'];keys={};mapping={};frames=[];new={};duplicates=[]
    native_count=max(i for c in r['cycles'] for i in c['native_frame_indices'])+1
    for f in r['frames']:
        old=f['frame'];p=arrays[(r['resref'],old)]
        key=(tuple(f['logical_size_x1']),tuple(f['centre_x1']),hashlib.sha256(p.tobytes()).hexdigest())
        if key in keys:
            assert old>=native_count,'native input duplicates should have been collapsed before interpolation'
            mapping[old]=keys[key];duplicates.append([old,keys[key]]);continue
        index=len(frames);keys[key]=index;mapping[old]=index;nf=copy.deepcopy(f);nf['frame']=index
        frames.append(nf);new[(r['resref'],index)]=p
    assert all(mapping[i]==i for i in range(native_count))
    for c in r['cycles']:c['timeline_frame_indices']=[mapping[i] for i in c['timeline_frame_indices']]
    r.update(frames=frames,frame_count=len(frames))
    return new,dict(stored_before=before,stored_after=len(frames),aliased_duplicate_outputs=duplicates,
        target_phase_counts_preserved=True)

def finish_effect(tag):
    source=BATCH/('temporal-'+tag+'/03_runtime_pack');_,rs=v.validate_v2_pack(source);r=copy.deepcopy(rs[0])
    radius=sweep(source,r,tag);arrays={}
    for f in r['frames']:
        p=pixels(source,f)
        if radius:p[...,3]=np.rint(p[...,3]*inner_feather_ramp(p[...,3],radius)).astype(np.uint8)
        p[...,:3]=np.rint(p[...,:3].astype(float)*p[...,3,None]/255).astype(np.uint8)
        p[p[...,3]==0,:3]=0;arrays[(r['resref'],f['frame'])]=p
    arrays,report=deduplicate(r,arrays)
    dest=write_pack(BATCH/('final-'+tag),[r],arrays)
    v.write_json(BATCH/('finishing-'+tag+'.json'),dict(status='completed',source_pack=rel(source),
        source_pack_manifest_sha256=v.sha256_file(source/'manifest.json'),final_pack=rel(dest),
        final_pack_manifest_sha256=v.sha256_file(dest/'manifest.json'),inner_feather_x4=radius,
        rgb='premultiply exactly once, RGB zero under alpha0',deduplication=report))
    return dest

def main():
    jobs={tag:finish_effect(tag) for tag in ['AM3000E-PLT_MAGE','FLM2PUR-embedded','FLM2PUR-PLT_PURP']}
    jobs['AM0510A']=BATCH/'final-AM0510A';jobs['AMWRPGT1']=AMWRP
    palettes=BATCH/'palettes';palettes.mkdir()
    for name in ['PLT_MAGE','PLT_PURP']:
        shutil.copyfile(ROOT/f'animations/tmp/lot45-analysis-20261011-v1/{name}.bmp',palettes/(name+'.bmp'))
    before=v.load_json(BATCH/'baselines-source.json');baselines={};roots=[];chosen={}
    for ref,areas in AREAS.items():
        for area in areas:
            base=before[area];specs=[]
            preserved=ROOT/base['preserved_pack'] if base['preserved_pack'] else None
            if preserved:
                old=v.validate_v2_pack(preserved)[1]
                # Preserve all original sibling resources and already acquired AMWRPGT1 bytes.
                if ref=='AMWRPGT1' and base.get('AMWRPGT1_same_as_selected'):
                    specs.append(str(preserved));target_pack=preserved
                else:
                    specs.extend(str(preserved)+'::'+name for name in sorted({r['resref'] for r in old if r['resref']!=ref}))
                    target_pack=None
            else:target_pack=None
            if target_pack is None:
                tag='AM3000E-PLT_MAGE' if ref=='AM3000E' else 'FLM2PUR-PLT_PURP' if ref=='FLM2PUR' and area=='OH4210' else 'FLM2PUR-embedded' if ref=='FLM2PUR' else ref
                target_pack=jobs[tag]
                specs.append(str(target_pack)+'::'+ref)
            # Fixed external palettes are baked before inference and are specific to this area leaf.
            actual=[r for r in OCCURRENCES if r['area_id']==area and r['resource_resref']==ref]
            if ref=='AM3000E':assert all(r['palette_mode']=='external' and r['palette_resref']=='PLT_MAGE' for r in actual)
            if ref=='FLM2PUR':assert all((r['palette_mode'],r['palette_resref'])==('external','PLT_PURP') if area=='OH4210' else (r['palette_mode'],r['palette_resref'])==('embedded','') for r in actual)
            out=PACKS/(TAG+'-merged-'+area);merge.merge(specs,area,out,False);roots.append(out)
            after=payload(out/area)
            for name,digest in (base['payload'] or {}).items():
                if name!=v.REGISTRY_NAME and not name.startswith('AAX4-'+ref+'-'):assert after[name]==digest,area+': changed sibling '+name
            if ref=='AMWRPGT1' and base.get('AMWRPGT1_same_as_selected'):
                assert after==base['payload'],area+': acquired pack changed'
            baselines[area]=dict(present=base['present'],payload=base['payload'],output_payload=after)
            chosen[area]=dict(resref=ref,source_pack=rel(target_pack),source_pack_manifest_sha256=v.sha256_file(target_pack/'manifest.json'),
                existing_bytes_preserved=ref=='AMWRPGT1' and bool(base.get('AMWRPGT1_same_as_selected')),
                palette='PLT_MAGE' if ref=='AM3000E' else 'PLT_PURP' if ref=='FLM2PUR' and area=='OH4210' else 'embedded')
            print('MERGED',area,ref,flush=True)
    complete=PACKS/(TAG+'-complete');combine.combine(roots,complete,False)
    v.write_json(BATCH/'baseline.json',baselines);v.write_json(BATCH/'area-sources.json',chosen)
    for ref,areas in AREAS.items():
        wrapper=ROOT/f'animations/ressources/{ref}/runs/{ref.lower()}-{TAG}';wrapper.mkdir(parents=True,exist_ok=False)
        leaf=complete/areas[0]
        if ref in ['AM0510A','AMWRPGT1']:
            source=AM0510.parent if ref=='AM0510A' else AMWRP.parent
        else:source=BATCH/('spatial-'+('AM3000E-PLT_MAGE' if ref=='AM3000E' else 'FLM2PUR-embedded'))
        v.write_json(wrapper/'manifest.json',dict(schema='bg2-upscale-animation-visual-treatment-v1',status='completed',created_utc=v.utc_now(),
            resref=ref,resrefs=[ref],source_run=rel(source),source_run_manifest_sha256=v.sha256_file(source/'manifest.json'),
            source_pack=rel(leaf),source_pack_manifest_sha256=v.sha256_file(leaf/'manifest.json'),output_split_root=rel(complete),
            output_manifest_sha256=v.sha256_file(complete/'manifest.json'),area_sources={a:chosen[a] for a in areas},
            recipe=dict(spatial='SeedVR7B LAB reused' if ref in ['AM0510A','AMWRPGT1'] else 'ReboutCX x4 fp16 on realized palette',
                temporal='Apollo8',target_fps=30,contour='authored arch + measured halo' if ref=='AM0510A' else 'existing safe8x6 spline-fit1 gauss3 preserved' if ref=='AMWRPGT1' else 'swept inner feather; premultiply once',
                palette='BMP realized before inference, dedicated area leaves' if ref in ['AM3000E','FLM2PUR'] else 'embedded',
                occlusion='native bridge retained, no static WED clipping'),qa_status='pending-ingame',release_status='not-selected'))
    v.write_json(BATCH/'manifest.json',dict(schema='bg2-upscale-animation-batch-production-v1',status='completed',created_utc=v.utc_now(),resrefs=REFS,
        lots=[4,5],complete_pack=rel(complete),recipe_script=rel(Path(__file__)),occurrence_count=69,area_count=21,qa_status='pending-ingame',release_status='not-selected'))
    preview(jobs)
    print('COMPLETE: 4 assets / 21 maps / 69 occurrences',flush=True)

def preview(jobs):
    sheet=Image.new('RGB',(1250,700),(32,32,32));draw=ImageDraw.Draw(sheet)
    for i,tag in enumerate(['AM0510A','AM3000E-PLT_MAGE','FLM2PUR-embedded','FLM2PUR-PLT_PURP','AMWRPGT1']):
        pack=jobs[tag];r=v.validate_v2_pack(pack)[1][0];cycle=r['cycles'][0]
        index=cycle['timeline_frame_indices'][len(cycle['timeline_frame_indices'])//2];p=pixels(pack,r['frames'][index])
        if tag=='AM0510A':image=Image.alpha_composite(Image.new('RGBA',(512,512),(32,32,32,255)),Image.fromarray(p)).convert('RGB')
        elif tag=='AMWRPGT1':image=Image.alpha_composite(Image.new('RGBA',(p.shape[1],p.shape[0]),(32,32,32,255)),Image.fromarray(p)).convert('RGB')
        else:image=Image.fromarray(np.minimum(p[...,:3].astype(np.uint16)+32,255).astype(np.uint8))
        image.thumbnail((380,290),Image.Resampling.LANCZOS);x=(i%3)*416;y=(i//3)*350
        sheet.paste(image,(x+(416-image.width)//2,y+40));draw.text((x+12,y+12),tag,fill='white')
    sheet.save(BATCH/'preview.png')

if __name__=='__main__':main()
