"""CPU diagnostic: decode existing payloads only; no inference, registry or install writes."""
from pathlib import Path
import sys, json, struct, hashlib
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_oracle import read_bam_p8
from palette_monster_contract import get_profile
import palette_registry as v6
import run_creature_sprite_x2 as registry

OUT=Path(__file__).parent
CONTRACT=json.loads((ROOT/'docs/measurements/q3m-monster-contract-x2-20261002-v1/contract.json').read_text())
RESOURCES={r['resref']:r for r in CONTRACT['resources']}
GAME=Path("G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition")
FONT=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22)
SMALL=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def old_frames(path, wanted):
    result={}
    with path.open('rb') as s:
        header=s.read(24)
        version,scale,count,animation=struct.unpack_from('<4I',header,8)
        assert header[:8]==b'IEECSXN\0' and version==3 and scale==2
        for _ in range(count):
            r=s.read(48);ref=r[:8].split(b'\0')[0].decode();nf,nc=struct.unpack_from('<II',r,40)
            frames={}
            for n in range(nf):
                h=s.read(528);w,ht,cx,cy,tr,length=struct.unpack_from('<HHhhB3xI',h)
                assert h[9:12]==b'\0\0\0' and length==4*w*ht
                if ref in wanted and n in wanted[ref]:
                    frames[n]=(np.frombuffer(s.read(length),np.uint8).reshape(2*ht,2*w), (w,ht,cx,cy,tr))
                else: s.seek(length,1)
            for _ in range(nc):
                slots=struct.unpack('<I',s.read(4))[0];s.seek(slots*4,1)
            if frames: result[ref]=(r[8:40].hex(),frames)
    return result

def colours(rgba):
    return {tuple(map(int,p)) for p in rgba[rgba[:,:,3]==255,:3]}

def checker(w,h):
    y,x=np.indices((h,w));dark=(x//16+y//16)%2
    rgb=np.where(dark[:,:,None],np.array([53,56,61]),np.array([42,45,50])).astype(np.uint8)
    return Image.fromarray(np.dstack((rgb,np.full((h,w),255,np.uint8))), 'RGBA')

families=[('spectateur','Spectateur','0x7F02','7f02-mbeh-beholder','reboutcx-p2-mbeh-v2'),
          ('bodhi','Bodhi','0x7F30','7f30-nboh-bodhi','reboutcx-p2-sample-v1'),
          ('golem','Golem geôlier','0x7F07','7f07-mglc-golem-clay',None)]
report=dict(role='diagnostic-comparison-not-QA',palette='native neutral; same palette/alpha for both decoders',
            colours='distinct RGB on opaque sprite pixels, before background compositing; excludes transparency and shadow',
            sampling='first existing phase-5 G1 sample and first G2 sample; those previews selected high-F frames within representative cycles',
            display='PNG lossless; full sprite nearest-neighbour x3 of x2 pixels, detail nearest-neighbour x8; no added colours',families=[])
for slug,title,animation,family,run in families:
    base=ROOT/'sprite/families/monsters/7fxx'/family
    preview=json.loads((ROOT/'sprite/.work/q3m-monster-complete-x2-pack-20261003-v1/previews'/animation/'preview.json').read_text())
    selected=[next(s for s in preview['samples'] if s['resref'].endswith(suffix)) for suffix in ('G1','G2')]
    wanted={s['resref']:{s['frame']} for s in selected}
    paths=[base/'runs'/run/'components'/(ref+'.registry') for ref in wanted] if run else [base/'runs/x2-nearest-v1/build/iee-assets/creature-sprites/CreatureSprites-XN.registry']
    old={}
    for p in paths: old.update(old_frames(p,wanted))
    samples=[]
    for sample in selected:
        ref,n=sample['resref'],sample['frame'];resource=RESOURCES[ref]
        native=read_bam_p8((ROOT/resource['source']).read_bytes());src=native['frames'][n]
        leaf=ROOT/'sprite/.work/q3m-monster-complete-x2-leaves-20261003-v1'/(ref+'.registry')
        info=v6.inspect(leaf,include_resource_records=True,include_frames=True)
        installed=GAME/'iee-assets/creature-sprites'/registry.catalog_shard_filename(info['sha256'])
        assert sha(installed)==sha(leaf), 'installed payload differs'
        encoded=info['frame_data'][0]['frames'][n]
        geometry=(src['width'],src['height'],src['center_x'],src['center_y'],native['transparent'])
        oi,og=old[ref][1][n]
        assert encoded['geometry']==og==geometry
        source_sha=hashlib.sha256(native['canonical']).hexdigest()
        bamc=(ROOT/resource['source']).with_suffix('.bamc')
        assert source_sha==resource['canonical_sha256_registered'].lower()
        assert old[ref][0] in (source_sha,sha(bamc)), (ref,old[ref][0],source_sha)
        assert read_bam_p8(bamc.read_bytes())['canonical']==native['canonical']
        assert n in native['cycles'][sample['cycle']]['frame_indices']
        shape=oi.shape;i=np.frombuffer(encoded['I'],np.uint8).reshape(shape)
        f=np.frombuffer(encoded['F'],np.uint8).reshape(shape) if encoded['F'] else np.zeros_like(i)
        profile=get_profile(resource['palette_profile_id']);pal=profile.fitting[0]
        # Same live neutral source palette and shadow alpha on both sides.
        before=profile.decode(oi,np.zeros_like(oi),pal);after=profile.decode(i,f,pal)
        assert np.array_equal(before[:,:,3],after[:,:,3]), 'silhouette alpha differs'
        native_colours={tuple(map(int,p)) for p in pal[3:,:3]}
        bc,ac=colours(before),colours(after)
        ys,xs=np.nonzero(after[:,:,3]==255)
        # Geometrical centroid of opaque pixels, independent of colour differences.
        cx,cy=int(round(xs.mean())),int(round(ys.mean()))
        x0=max(0,min(shape[1]-32,cx-16));y0=max(0,min(shape[0]-32,cy-16))
        crop=(x0,y0,min(x0+32,shape[1]),min(y0+32,shape[0]))
        metrics=dict(resref=ref,frame=n,cycle=sample['cycle'],source_sha256=source_sha,
                     native_geometry=list(geometry),before_colours=len(bc),q3m_colours=len(ac),
                     q3m_colours_absent_from_source_palette=len(ac-native_colours),
                     q3m_fractional_opaque_pixels=int(np.count_nonzero((f>0)&(after[:,:,3]==255))),
                     opaque_pixels=int(len(xs)),crop=list(crop),installed_leaf_sha256=info['sha256'],
                     old_registry_paths=[p.relative_to(ROOT).as_posix() for p in paths])
        for name,rgba in [('avant',before),('q3m',after)]:
            Image.fromarray(rgba,'RGBA').save(OUT/f'{slug}-{ref}-{n}-{name}-rgba.png')
        samples.append((metrics,before,after))
    tw=max(470,max(a.shape[1]*3+48 for _,a,_ in samples))
    row_heights=[a.shape[0]*3+420 for _,a,_ in samples]
    canvas=Image.new('RGB',(tw*2,100+sum(row_heights)),(25,27,31));draw=ImageDraw.Draw(canvas)
    old_label='ReboutCX classique x2' if run else 'Ancien xBR x2 (pas ReboutCX)'
    draw.text((20,12),title+' — palette neutre, PNG sans perte',font=FONT,fill='white')
    draw.text((20,48),'Avant : '+old_label,font=FONT,fill='white')
    draw.text((tw+20,48),'Après : Q3m K6 x2',font=FONT,fill='white')
    row_y=100
    for metrics,before,after in samples:
        h,w=before.shape[:2];full_h=3*h+64
        for col,(rgba,num) in enumerate([(before,metrics['before_colours']),(after,metrics['q3m_colours'])]):
            x=col*tw;tile=checker(tw,full_h)
            enlarged=Image.fromarray(rgba,'RGBA').resize((3*w,3*h),Image.Resampling.NEAREST)
            tile.alpha_composite(enlarged,((tw-3*w)//2,48))
            canvas.paste(tile.convert('RGB'),(x,row_y))
            draw.text((x+16,row_y+8),f"{metrics['resref']} / frame {metrics['frame']} / cycle {metrics['cycle']} — {num} couleurs",font=SMALL,fill='white')
            detail=Image.fromarray(rgba,'RGBA').crop(tuple(metrics['crop']));detail=detail.resize((detail.width*8,detail.height*8),Image.Resampling.NEAREST)
            dt=checker(tw,detail.height+40);dt.alpha_composite(detail,((tw-detail.width)//2,30))
            canvas.paste(dt.convert('RGB'),(x,row_y+full_h+8))
            draw.text((x+16,row_y+full_h+12),'Même détail — zoom x8 sans lissage',font=SMALL,fill='white')
        row_y+=h*3+420
    image_path=OUT/(slug+'-avant-apres.png');canvas.save(image_path)
    record=dict(target=title,old_method=old_label,old_run=run,comparison_png=image_path.relative_to(ROOT).as_posix(),samples=[s[0] for s in samples])
    report['families'].append(record)
    print(json.dumps(record,ensure_ascii=False),flush=True)
(OUT/'comparison.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
