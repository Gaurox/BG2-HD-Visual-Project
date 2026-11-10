"""27 scoped correction trials, all native palettes, synchronized comparison data."""
from prepare import ROOT,BASE,OUT,load,save
from masks import PAD,build as smooth_masks
import argparse,collections,hashlib,importlib.util,os,subprocess,time,traceback
from types import SimpleNamespace
from fractions import Fraction
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
import effect_workflow as workflow
import run_effect_interpolation as interpolation
from derive_animation_visual_treatment import apply_geometry_preserving_rgb_gaussian

spec=importlib.util.spec_from_file_location('original_temporal',ROOT/'pipeline/recipes/effects-lot31-projectiles-20261018-v1/temporal.py')
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)

def sha(data):return hashlib.sha256(data).hexdigest().upper()

def image(array):
    array=array.astype(np.uint8,copy=False);h,w=array.shape[:2];key=sha(array.tobytes()+str(array.shape).encode())
    folder=OUT/'review/images';folder.mkdir(parents=True,exist_ok=True);p=folder/(key+'.png')
    if not p.exists():Image.fromarray(array).save(p,compress_level=2)
    return 'images/'+p.name

def raw(array):
    data=array.tobytes();key=sha(data);folder=OUT/'rgba';folder.mkdir(exist_ok=True);p=folder/(key+'.rgba')
    if not p.exists():p.write_bytes(data)
    return {'path':p.relative_to(ROOT).as_posix(),'sha256':key,'bytes':len(data)}

def parent(a):
    stage=ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation'
    m=load(stage/'manifest.json');sp=load(ROOT/m['parent']['spatial_manifest'])
    anchor=[sp['frames'][0]['canvas_offset_x1'][i]+sp['frames'][0]['centre_x1'][i] for i in range(2)]
    return stage,m,sp,anchor

def before_frame(stage,f,sp,anchor):
    cw,ch=sp['aligned_canvas_size_x1'];out=np.zeros((ch*4+2*PAD,cw*4+2*PAD,4),np.uint8)
    w,h=f['physical_size_x4'];crop=np.fromfile(stage/f['straight_raw_rgba_x4'],np.uint8).reshape(h,w,4)
    x,y=[(anchor[i]-f['centre_x1'][i])*4+PAD for i in range(2)]
    out[y:y+h,x:x+w]=crop
    return out

def spatial_images(a,sp):
    if a['rebout']:
        folder=OUT/'reboutcx'/a['job_id'];manifest=folder/'manifest.json'
        while not manifest.exists():time.sleep(2)
        rows=load(manifest)['frames']
        images={}
        for f in rows:
            rgba=np.array(Image.open(ROOT/f['path']).convert('RGBA'))
            fg=rgba[:,:,3]>0
            if fg.any():
                near=ndi.distance_transform_edt(~fg,return_distances=False,return_indices=True)
                rgba[:,:,:3]=rgba[:,:,:3][tuple(near)]
            images[f['frame']]=rgba
        return images
    folder=ROOT/load((ROOT/'effects/ressources'/a['resref']/'runs'/a['interpolation_run']/'02-interpolation/manifest.json'))['parent']['spatial_manifest']
    return {f['frame']:np.array(Image.open(folder.parent/f['aligned_rgba_xn']).convert('RGBA')) for f in sp['frames']}

def native_apollo(a,v,images,keys):
    """2x at the true native15FPS clock; no endpoint stretching or blank trimming."""
    folder=OUT/'apollo'/a['job_id']/v['id'];inp=folder/'input';out=folder/'output'
    done=folder/'completed.json'
    if len(keys)==1:return []
    if not done.exists():
        inp.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True)
        h,w=images[keys[0]].shape[:2];pw=max(128,(w+31)//32*32);ph=max(128,(h+31)//32*32)
        extended=keys+(keys[:2] if v['loop_closed'] else [keys[-1]])
        for i,k in enumerate(extended):
            im=Image.new('RGB',(pw,ph));im.paste(Image.fromarray(images[k][:,:,:3]),(0,0));im.save(inp/f'in_{i:03d}.png')
        cmd=[str(interpolation.DEFAULT_TVAI_FFMPEG),'-hide_banner','-loglevel','error','-y','-framerate','15','-i',str(inp/'in_%03d.png'),
            '-vf','tvai_fi=model=apo-8:fps=30:rdt=-0.01:device=-2','-pix_fmt','rgb24',str(out/'out_%04d.png')]
        save(folder/'command.json',{'command':cmd,'native_fps':15,'target_fps':30,'keys':keys,'source_size':[w,h]})
        env=dict(os.environ,TVAI_MODEL_DIR=str(interpolation.DEFAULT_TVAI_MODEL_DIR),TVAI_MODEL_DATA_DIR=str(interpolation.DEFAULT_TVAI_MODEL_DIR))
        with (folder/'apollo.log').open('w',encoding='utf-8') as log:subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
        save(done,{'passed':True})
    return interpolation.parse_numbered_pngs(out)

def native_sources(a,v,identities):
    slots=v['native_slots'];closed=v['loop_closed'];keys=[]
    for k in slots:
        if not keys or identities[k]!=identities[keys[-1]]:keys.append(k)
    # Returns at a later time stay in sequence; source20/12 only have terminal holds.
    canonical={identities[k]:k for k in keys};rank={k:i for i,k in enumerate(keys)};specs=[]
    for phase in range(len(slots)*2):
        slot=phase//2;left=canonical[identities[slots[slot]]]
        nxt=(slot+1)%len(slots) if closed else min(slot+1,len(slots)-1)
        right=canonical[identities[slots[nxt]]];fraction=.5 if phase%2 and left!=right else 0.
        specs.append((left,right,fraction,2*rank[left]+1))
    return keys,specs

def black_neutral(candidate):
    old=candidate.copy();a=old[:,:,3].astype(np.float32);rgb=old[:,:,:3].astype(np.float32)
    energy=np.rint(rgb*a[:,:,None]/255).astype(np.uint8)
    intensity=rgb.max(2);alpha=np.rint(a*intensity/255).astype(np.uint8)
    normal=np.zeros_like(old);normal[:,:,3]=alpha
    covered=alpha>0
    normal[:,:,:3][covered]=np.clip(np.rint(energy[covered].astype(float)*255/alpha[covered,None]),0,255).astype(np.uint8)
    primary=normal.copy();primary[:,:,:3]=np.rint(normal[:,:,:3].astype(float)*alpha[:,:,None]/255).astype(np.uint8)
    error=int(np.abs(primary[:,:,:3].astype(np.int16)-energy.astype(np.int16)).max())
    assert error<=1,error
    assert not normal[intensity==0].any(),'black matte is not transparent'
    return normal,primary,error

def produce(a):
    result=OUT/'results'/f'{a["job_id"]}.json'
    if result.exists():return load(result)
    stage,m,sp,anchor=parent(a);cw,ch=sp['aligned_canvas_size_x1'];size=[cw*4+2*PAD,ch*4+2*PAD]
    fm=ROOT/'effects/ressources'/a['resref']/'runs'/a['spatial_run']/'00-frames-x1';fmanifest=load(fm/'manifest.json')
    native={};native_alpha={};identities={};native_paths={}
    for f in fmanifest['frames']:
        k=f['frame'];small=np.array(Image.open(fm/'rgba'/f['file']).convert('RGBA'))
        im=np.pad(small.repeat(4,0).repeat(4,1),((PAD,PAD),(PAD,PAD),(0,0)));im[im[:,:,3]==0]=0
        native[k]=im;native_alpha[k]=im[:,:,3];identities[k]=sha(im.tobytes());native_paths[k]=image(im)
    smoothed=smooth_masks(a,sp) if a['smooth'] else None
    sources=spatial_images(a,sp) if a['rebout'] or a['retime'] else None
    plan=SimpleNamespace(interpolation_root=OUT/'apollo'/a['job_id'],tvai_ffmpeg=interpolation.DEFAULT_TVAI_FFMPEG,tvai_model_dir=interpolation.DEFAULT_TVAI_MODEL_DIR)
    profiles=[];records=[];max_error=0;rgb_changes=0;blank_held=0
    for v in m['timing']['cycles']:
        old_frames=[m['frames'][i] for i in v['timeline_frame_indices']];specs=[]
        if a['retime']:
            assert base.native_rate(a)==15
            keys,specs=native_sources(a,v,identities);files=native_apollo(a,v,sources,keys)
            save(OUT/'timing-audits'/f'{a["job_id"]}-{v["id"]}.json',{'native_slots':v['native_slots'],
                'input_keys_adjacent_deduplicated':keys,'native_slots_count':len(v['native_slots']),
                'deduplicated_inputs':len(v['native_slots'])-len(keys),'all_nonadjacent_returns_preserved':True,
                'duration_rational':[len(v['native_slots']),15],'native_anchor_clock_preserved':True})
        elif a['rebout']:
            files=base.apollo(plan,v,sources)
        seq_before=[];seq_after=[];phase_reports=[]
        for phase,oldf in enumerate(old_frames):
            before=before_frame(stage,oldf,sp,anchor)
            left,right=oldf['temporal_source_frames'];fraction=oldf['temporal_fraction']
            if a['retime'] or a['rebout']:
                sample=phase
                if a['retime']:left,right,fraction,sample=specs[phase]
                if fraction==0:rgb=sources[left][:,:,:3].copy()
                else:
                    with Image.open(files[sample]) as im:rgb=np.array(im.convert('RGB'))[:ch*4,:cw*4].copy()
                alpha=np.rint(sources[left][:,:,3].astype(float)*(1-fraction)+sources[right][:,:,3].astype(float)*fraction).astype(np.uint8)
                rgba=np.dstack((rgb,alpha));rgba[alpha==0]=0
                if a['retime']:
                    prem=rgba.copy();prem[:,:,:3]=np.rint(rgb.astype(float)*alpha[:,:,None]/255).astype(np.uint8)
                    prem=apply_geometry_preserving_rgb_gaussian(prem,1.2)
                    covered=alpha>0;rgba[:,:,:3][covered]=np.clip(np.rint(prem[:,:,:3][covered].astype(float)*255/alpha[covered,None]),0,255).astype(np.uint8)
                candidate=np.pad(rgba,((PAD,PAD),(PAD,PAD),(0,0)))
            else:candidate=before.copy()
            if a['smooth']:
                dtype=float if a['rebout'] else np.float32
                expected=np.rint(native_alpha[left].astype(dtype)*(1-fraction)+native_alpha[right].astype(dtype)*fraction).astype(np.uint8)
                assert np.array_equal(candidate[:,:,3],expected),(a['job_id'],phase,'base alpha chronology mismatch')
                alpha=np.rint(smoothed[left].astype(float)*(1-fraction)+smoothed[right].astype(float)*fraction).astype(np.uint8)
                fg=candidate[:,:,3]>0;added=(alpha>0)&~fg
                if fg.any() and added.any():
                    near=ndi.distance_transform_edt(~fg,return_distances=False,return_indices=True)
                    candidate[:,:,:3][added]=candidate[:,:,:3][tuple(near)][added]
                candidate[:,:,3]=alpha;candidate[alpha==0]=0
                if not a['rebout'] and not a['retime']:
                    shared=(before[:,:,3]>0)&(alpha>0)
                    assert np.array_equal(candidate[:,:,:3][shared],before[:,:,:3][shared]),'mask-only RGB modified'
            if a['black_neutral']:
                candidate,primary,error=black_neutral(candidate);max_error=max(max_error,error)
            else:
                primary=candidate.copy();primary[:,:,:3]=np.rint(candidate[:,:,:3].astype(float)*candidate[:,:,3:4]/255).astype(np.uint8)
            candidate[candidate[:,:,3]==0]=0;primary[primary[:,:,3]==0]=0
            assert np.all(primary[:,:,:3]<=primary[:,:,3:4])
            assert not candidate[[0,-1],:,:].any() and not candidate[:,[0,-1],:].any()
            if not candidate.any():blank_held+=1
            bp=image(before);ap=image(candidate);seq_before.append(bp);seq_after.append(ap)
            rec={'frame':len(records),'profile':v['id'],'phase':phase,'temporal_source_frames':[left,right],
                'temporal_fraction':fraction,'before':bp,'after':ap,'straight':raw(candidate),'premultiplied':raw(primary)}
            records.append(rec)
        profiles.append({'id':v['id'],'cycle':v['cycle'],'loop':v['loop_closed'],'duration_rational':v['duration_rational'],
            'phases':len(seq_after),'phase_durations_rational':v['phase_durations_rational'],
            'before':seq_before,'after':seq_after,'native':[native_paths[k] for k in v['native_slots']]})
        assert sum(Fraction(*d) for d in v['phase_durations_rational'])==Fraction(*v['duration_rational'])
    r={'resref':a['resref'],'ordinal':a['ordinal'],'job_id':a['job_id'],'primary':a['primary'],'changed':a['changed'],
        'actions':{k:a[k] for k in ('rebout','smooth','retime','black_neutral')},'size_x4':size,
        'logical_size_x1':[size[0]//4,size[1]//4],'centre_x1':[anchor[0]+PAD//4,anchor[1]+PAD//4],
        'parent_interpolation':workflow.file_evidence(ROOT,stage/'manifest.json'),
        'palette_file':a['palette_file'],'consumers':a['consumers'],'profiles':profiles,'frames':records,
        'mask_only_existing_rgb_exact':not a['rebout'] and not a['retime'] and not a['black_neutral'],
        'black_premultiplied_flux_max_error':max_error,'native_blank_hold_phases':blank_held,
        'native_duration_preserved':True,'passed':True,'qa':'pending-user-preview','installed':False}
    save(result,r);print('PASS',a['job_id'],len(records),'phases',flush=True);return r

def main():
    from concurrent.futures import ThreadPoolExecutor,as_completed
    import threading
    p=argparse.ArgumentParser();p.add_argument('--job',action='append');args=p.parse_args()
    jobs=[a for a in load(OUT/'plan.json')['jobs'] if not args.job or a['job_id'] in args.job]
    # Source masks are shared across palettes; construct once before threaded phase work.
    seen=set()
    for a in jobs:
        if a['smooth'] and a['resref'] not in seen:
            _,_,sp,_=parent(a);smooth_masks(a,sp);seen.add(a['resref'])
    state={};lock=threading.Lock()
    def work(a):
        key=a['job_id']
        with lock:state[key]={'state':'running'};save(OUT/'progress.json',state)
        try:r=produce(a);value={'state':'completed'}
        except Exception as e:traceback.print_exc();value={'state':'failed','error':repr(e)}
        with lock:state[key]=value;save(OUT/'progress.json',state)
        return key,value
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=[f.result() for f in as_completed([pool.submit(work,a) for a in jobs])]
    errors={k:v for k,v in results if v['state']=='failed'}
    print('Correction failures:',errors,flush=True)
    return bool(errors)

if __name__=='__main__':raise SystemExit(main())
