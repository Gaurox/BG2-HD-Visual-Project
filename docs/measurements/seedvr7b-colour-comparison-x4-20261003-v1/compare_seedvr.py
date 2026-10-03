"""Six native frames through existing ComfyUI SeedVR2 7B x4; offline PNG comparison."""
from pathlib import Path
import argparse,copy,hashlib,json,sys,time
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_oracle import read_bam_p8
from palette_monster_contract import get_profile,CONTRACT
from reboutcx_batch import prepare_inference_rgb
from run_creature_sprite_x2 import SourceFrame
from run_seedvr_comfyui import ComfyClient,apply_runtime_overrides,validate_approved_7b_settings,sha256_file

args=argparse.ArgumentParser();args.add_argument('--server',required=True);a=args.parse_args()
OUT=Path(__file__).parent
PREVIOUS=ROOT/'sprite/.work/q3m-colour-comparison-20261003-v1'
X4=ROOT/'sprite/.work/q3m-colour-comparison-x4-20261003-v1'
comparison=json.loads((X4/'comparison.json').read_text(encoding='utf-8'))
old_comparison=json.loads((PREVIOUS/'comparison.json').read_text(encoding='utf-8'))
resources={r['resref']:r for r in json.loads(CONTRACT.read_text())['resources']}
workflow_path=ROOT/'pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json'
assert sha256_file(workflow_path)=='30dec619a4c1a3ecde076c0926a5ed8ee29d5f2ca8b4eb89a75d3b5f7811b61e'
template=json.loads(workflow_path.read_text());template.pop('65',None) # UI comparison node only.
summary=apply_runtime_overrides(template,scale=4,color_correction_method=None)
validate_approved_7b_settings(summary)
client=ComfyClient(a.server,poll_seconds=2,timeout_seconds=1800)
system=client.preflight()
def write_json(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def colours(rgba):return len(np.unique(rgba[rgba[:,:,3]==255,:3],axis=0))

recipe=dict(role='offline-image-test-not-Q3m-not-runtime',model=summary['model'],workflow_sha256=sha256_file(workflow_path),
            workflow=summary,scale=4,input='same native indexed BAM frame; nearest nontransparent RGB fill; native alpha',
            inference='SeedVR2 7B INT8 convrot, Euler one step, fixed workflow seed, LAB colour correction',
            display_alpha='same xBR4 guide/live neutral palette alpha as Q3m x4; exact special shadow RGB restored',
            source_comparison_sha256=sha256_file(X4/'comparison.json'),system=system)
write_json(OUT/'recipe.json',recipe)
report=dict(recipe=recipe,installation_changed=False,registries_changed=False,QA_changed=False,
            colour_count='distinct RGB on opaque sprite pixels; raw SeedVR RGB is not palette/Q3m constrained',families=[])
frames=[]
for fam in comparison['families']:
    slug=Path(fam['comparison_png']).name.split('-avant-q3m')[0]
    for sample in fam['samples']:
        key=f"{slug}-{sample['resref']}-{sample['frame']}";r=resources[sample['resref']]
        native=read_bam_p8((ROOT/r['source']).read_bytes());src=native['frames'][sample['frame']]
        assert hashlib.sha256(native['canonical']).hexdigest()==sample['source_sha256']
        profile=get_profile(sample['profile_id'])
        palette=profile.fitting[0];indices=src['indices'];rgb=palette[indices,:3]
        transport=np.dstack((rgb,np.where(indices==0,0,255).astype(np.uint8)))
        fr=SourceFrame(sample['resref'],sample['frame'],src['width'],src['height'],src['center_x'],src['center_y'],0,indices,palette[:,:3],transport.tobytes())
        filled=prepare_inference_rgb(fr,palette[:,:3])
        input_rgba=np.dstack((filled,palette[indices,3]))
        source=OUT/(key+'-native-filled-rgba.png');Image.fromarray(input_rgba,'RGBA').save(source)
        frames.append(dict(key=key,slug=slug,family=fam,sample=sample,frame=fr,profile=profile,source=source))

# Independent images, not a temporal sequence: each pose is a separate test.
# Start with the smallest input; remaining order is deterministic.
for d in sorted(frames,key=lambda d:d['frame'].width*d['frame'].height):
    key=d['key'];fr=d['frame'];receipt_path=OUT/(key+'-job.json');raw=OUT/(key+'-seedvr7b-x4-raw.png')
    if receipt_path.exists():
        receipt=json.loads(receipt_path.read_text());assert receipt['source_sha256']==sha256_file(d['source'])
    else:
        # Queue the requested frame only; never clear or interrupt the service queue.
        uploaded=client.upload(d['source'],'bg2-sprite-seedvr7b-x4-20261003-v1')
        prompt=copy.deepcopy(template);prompt['1']['inputs']['image']=uploaded
        prompt['9']['inputs']['filename_prefix']='bg2_sprite_seedvr7b_x4_20261003_v1/'+key
        write_json(OUT/(key+'-prompt.json'),prompt)
        prompt_id=client.queue(prompt)
        receipt=dict(key=key,prompt_id=prompt_id,source_sha256=sha256_file(d['source']),status='queued',workflow_summary=summary)
        write_json(receipt_path,receipt)
    if not raw.exists():
        print(json.dumps(dict(stage='seedvr-running',frame=key,prompt_id=receipt['prompt_id'])),flush=True)
        started=time.perf_counter();history=client.wait_history(receipt['prompt_id'])
        output=history['outputs']['9']['images'];assert len(output)==1
        client.download(output[0],raw)
        receipt.update(status='completed',history_status=history['status'],output=output[0],raw_sha256=sha256_file(raw),wait_seconds=time.perf_counter()-started)
        write_json(receipt_path,receipt)
    assert sha256_file(raw)==receipt['raw_sha256']
    with Image.open(raw) as img:
        assert img.size==(fr.width*4,fr.height*4),('not exact x4',key,img.size)
        rgb=np.asarray(img.convert('RGB')).copy()
    encoded_path=ROOT/d['sample']['encoded_cache']
    with np.load(encoded_path,allow_pickle=False) as data:guide=data['guide'].copy()
    assert guide.shape==rgb.shape[:2]
    palette=d['profile'].fitting[0]
    # Model compares material RGB. Restore exact special indices/shadow and alpha
    # from the same semantic guide to avoid judging edge/matte differences.
    special=guide<3;rgb[special]=palette[guide[special],:3]
    rgba=np.dstack((rgb,palette[guide,3]))
    q3m=np.asarray(Image.open(ROOT/d['sample']['png']).convert('RGBA'))
    assert np.array_equal(rgba[:,:,3],q3m[:,:,3]),'common x4 alpha mismatch'
    png=OUT/(key+'-seedvr7b-x4-rgba.png');Image.fromarray(rgba,'RGBA').save(png)
    d['rgba']=rgba
    d['metrics']=dict(resref=fr.resref,frame=fr.index,cycle=d['sample']['cycle'],
                     source_sha256=d['sample']['source_sha256'],source_geometry=d['sample']['source_geometry'],
                     old_colours=d['sample']['before_colours'],q3m_x2_colours=d['sample']['q3m_x2_colours'],
                     q3m_x4_colours=d['sample']['q3m_x4_colours'],seedvr7b_x4_colours=colours(rgba),
                     seedvr7b_raw_png=str(raw.relative_to(ROOT)),comparison_rgba_png=str(png.relative_to(ROOT)),
                     prompt_id=receipt['prompt_id'],png_sha256=sha256_file(png),alpha_identical_to_Q3m_x4=True)
    print(json.dumps(dict(stage='seedvr-completed',frame=key,size=[fr.width*4,fr.height*4],colours=colours(rgba))),flush=True)

FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
def checker(w,h):
    y,x=np.indices((h,w));dark=(x//16+y//16)%2
    rgb=np.where(dark[:,:,None],np.array([53,56,61]),np.array([42,45,50])).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,np.full((h,w),255,np.uint8))),'RGBA')
for fam in comparison['families']:
    selected=[d for d in frames if d['family'] is fam];slug=selected[0]['slug']
    prior=Image.open(ROOT/fam['comparison_png']).convert('RGB');assert prior.width%3==0
    tw=prior.width//3;canvas=Image.new('RGB',(tw*4,prior.height),(25,27,31));canvas.paste(prior,(0,0))
    draw=ImageDraw.Draw(canvas);draw.text((3*tw+20,47),'SeedVR2 7B x4 — RGB / LAB',font=FONT,fill='white')
    row_y=138
    oldfam=next(f for f in old_comparison['families'] if f['target']==fam['target'])
    for d in selected:
        fr=d['frame'];rgba=d['rgba'];img=Image.fromarray(rgba,'RGBA');full_h=fr.height*8+64;x=tw*3
        tile=checker(tw,full_h);full=img.resize((fr.width*8,fr.height*8),Image.Resampling.NEAREST)
        tile.alpha_composite(full,((tw-full.width)//2,48));canvas.paste(tile.convert('RGB'),(x,row_y))
        draw.text((x+16,row_y+8),f"{fr.resref} / frame {fr.index} / cycle {d['sample']['cycle']} — {d['metrics']['seedvr7b_x4_colours']} couleurs",font=SMALL,fill='white')
        osample=next(s for s in oldfam['samples'] if s['resref']==fr.resref and s['frame']==fr.index)
        detail=img.crop(tuple(v*2 for v in osample['crop']));detail=detail.resize((detail.width*4,detail.height*4),Image.Resampling.NEAREST)
        dt=checker(tw,detail.height+40);dt.alpha_composite(detail,((tw-detail.width)//2,30));canvas.paste(dt.convert('RGB'),(x,row_y+full_h+8))
        draw.text((x+16,row_y+full_h+12),'Même région — détail à taille égale',font=SMALL,fill='white')
        row_y+=fr.height*8+420
    png=OUT/(slug+'-comparatif-4-traitements.png');canvas.save(png)
    report['families'].append(dict(target=fam['target'],old_method=fam['old_method'],comparison_png=str(png.relative_to(ROOT)),samples=[d['metrics'] for d in selected]))
    print(json.dumps(dict(stage='comparison-ready',path=str(png))),flush=True)
write_json(OUT/'comparison.json',report)
