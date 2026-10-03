"""Prepare lossless comparative scenes and acquired-mask provenance; no game writes."""
import sys,json,hashlib
from pathlib import Path
import numpy as np
from scipy import ndimage
from PIL import Image,ImageDraw,ImageFont
from prepare import sources,ROOT,HERE,load
from sdf_trial import RECIPE,reconstruct,catmull,render_reconstructed,composite,material_layers
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from sprite_alpha_coverage import apply

WORK=ROOT/'sprite/.work/q3m-ankheg-sdf-offline-x2-20261004-v1'
ASSETS=HERE/'images';ASSETS.mkdir(exist_ok=True);WORK.mkdir(exist_ok=True)
font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',22)
bold=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf',25)
LABELS=('Alpha actuel','Contour reconstruit')
views=[('face','MAKHG1',11),('profil','MAKHG1',25),('attaque','MAKHG3',20),('miroir','MAKHG1E',25)]
resources=sources();cache={};records={};renders={}
recipe_key=json.dumps(RECIPE,sort_keys=True).encode()+bytes.fromhex(file_sha(HERE/'sdf_trial.py'))

def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=file_sha(p),bytes=p.stat().st_size)

def stone(w,h):
    # Deliberately synthetic, repeatable floor, identical for compared variants.
    rng=np.random.default_rng(42004);im=Image.new('RGB',(w,h),(83,82,76));d=ImageDraw.Draw(im)
    for row,y in enumerate(range(-35,h+35,35)):
        for x in range(-72,w+72,72):
            shift=36 if row%2 else 0;shade=int(rng.integers(119,146))
            d.rounded_rectangle((x+shift+2,y+2,x+shift+69,y+32),radius=4,
                fill=(shade+8,shade+5,shade-5),outline=(175,172,160),width=1)
    a=np.asarray(im).astype(np.int16);noise=rng.integers(-3,4,(h,w,1),dtype=np.int16)
    return np.clip(a+noise,0,255).astype(np.uint8)

def get_pose(ref,ordinal):
    b=resources[ref];r=b['original'];f=r['frames'][ordinal];c=b['current']['frames'][ordinal]
    assert np.array_equal(f['I'],c['I']) and np.array_equal(f['F'],c['F'])
    assert f['geometry']==c['geometry']
    key=hashlib.sha256(recipe_key+np.array(f['I'].shape,dtype='<u4').tobytes()+np.minimum(f['I'],3).tobytes()).hexdigest()
    if key not in cache:
        field,report=reconstruct(f['I']);cache[key]=(field,report)
        np.savez_compressed(WORK/(key+'.npz'),SDF=field)
    field,report=cache[key]
    assert report['maximum_field_change_x2']<=1.000001
    assert report['solid_components_before']==report['solid_components_after'],(ref,ordinal,report)
    assert report['maximum_added_solid_distance_x2']<=1.0 and report['maximum_removed_solid_distance_x2']<=1.0
    raw=r['profile'].decode(f['I'],f['F'],b['palettes'][0]);current=apply(raw,c['A'])
    records[(ref,ordinal)]=dict(resref=ref,frame=ordinal,mask_key=key,source_leaf_sha256=b['sha256'],
        geometry=list(f['geometry']),**report)
    return raw,current,f['I'],field

def render_pose(ref,ordinal,zoom):
    key=(ref,ordinal,zoom)
    if key in renders:return renders[key]
    raw,current,i,field=get_pose(ref,ordinal)
    before=catmull(np.pad(current,((6,6),(6,6),(0,0))),zoom)
    after=render_reconstructed(raw,i,field,zoom)
    renders[key]=(before,after)
    return before,after

def save_scene(name,rgba,bg):
    image=Image.fromarray(composite(rgba,bg),'RGB');image.save(ASSETS/name)
    return image

for name,ref,ordinal in views:
    raw,current,i,field=get_pose(ref,ordinal)
    # Validate original mathematical sampler at exact texel centres.
    expected=np.pad(current,((6,6),(6,6),(0,0))).astype(float)/255
    expected[expected[...,3]==0,:3]=0
    sampled=catmull(np.pad(current,((6,6),(6,6),(0,0))),1.0)
    assert np.allclose(sampled,expected,atol=1e-12)
    # Source material colours and deep body/shadow pixels are retained.
    extended,shadow=material_layers(raw,i);padded=np.pad(raw,((6,6),(6,6),(0,0)))
    mask=np.pad(i>=2,6)
    assert np.array_equal(extended[mask,:3],padded[mask,:3])
    reconstructed=render_reconstructed(raw,i,field,1.0)
    core=ndimage.distance_transform_edt(mask)>=3.0
    assert np.allclose(reconstructed[core,:3],padded[core,:3]/255,atol=1e-12)
    far_shadow=np.pad(i==1,6)&(ndimage.distance_transform_edt(~mask)>=3.0)
    assert np.allclose(reconstructed[far_shadow],padded[far_shadow]/255,atol=1e-12)
    for zoom in (1.0,1.5,3.0):
        for label,rgba in zip(('actuel','sdf'),render_pose(ref,ordinal,zoom)):
            suffix=str(zoom).replace('.','p')
            save_scene(name+'-'+label+'-'+suffix+'-gris.png',rgba,(119,122,123))
            if zoom==3.0:save_scene(name+'-'+label+'-'+suffix+'-pierre.png',rgba,stone(rgba.shape[1],rgba.shape[0]))
    # Show native opaque mask, current alpha, and reconstructed body alpha at zoom 3.
    before,after=render_pose(ref,ordinal,3.0)
    for label,rgba in (('actuel',before),('sdf',after)):
        alpha_rgb=np.repeat((np.rint(rgba[...,3]*255).astype(np.uint8))[...,None],3,axis=2)
        Image.fromarray(alpha_rgb).save(ASSETS/(name+'-'+label+'-alpha.png'))
    print(json.dumps(dict(view=name,frame=ordinal,report=records[(ref,ordinal)])),flush=True)

# Three adjacent frames per orientation; duplicate masks reuse one field.
for name,ref,ordinal in views:
    for n in (ordinal-1,ordinal,ordinal+1):
        pair=render_pose(ref,n,1.0)
        for label,rgba in zip(('actuel','sdf'),pair):
            save_scene('sequence-'+name+'-'+str(n)+'-'+label+'.png',rgba,(119,122,123))

# Overview PNG is an additional inspectable lossless raster, no screenshot alteration.
overview=Image.new('RGB',(1500,660),(244,242,235));draw=ImageDraw.Draw(overview)
draw.text((32,18),'ANKHEG / ALPHA ACTUEL ET CONTOUR SDF',font=bold,fill=(28,35,43))
draw.text((32,58),'Simulation CPU - Catmull-Rom - 1 texel Q3m x2 = 3 pixels ecran',font=font,fill=(72,81,89))
for col,(label,variant) in enumerate(zip(LABELS,('actuel','sdf'))):
    x=32+col*745;draw.text((x,102),label,font=bold,fill=(48,58,66) if col==0 else (0,109,104))
    im=Image.open(ASSETS/('profil-'+variant+'-3p0-pierre.png'))
    overview.paste(im,(x+(710-im.width)//2,150+(470-im.height)//2))
overview.save(HERE/'comparatif.png')
shader=ROOT/'engine/InfinityEngine-Enhancer/source-patchee/assets/shader-suite/creature-hd-common.glsl'
write_json(HERE/'trial.json',dict(schema='bg2-ankheg-SDF-offline-visual-trial-v1',recipe=RECIPE,
    role='offline-simulation-not-installation-or-ingame-QA',views=[dict(name=n,resref=r,frame=f) for n,r,f in views],
    selected_frames=len(records),unique_mask_work=len(cache),rendered_mask_reuses=len(records)-len(cache),
    original_generation=identity(ROOT/'docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1/current-generation.json'),
    installed_alpha_generation=identity(ROOT/'docs/measurements/q3m-ankheg-alpha-light-x2-20261004-v1/current-generation.json'),
    processor=identity(HERE/'sdf_trial.py'),shader_mathematical_reference=identity(shader),
    records=list(records.values()),checks=dict(native_centre_sampler_identity=True,
        body_RGB_at_centres_byte_identical=True,far_native_shadow_pixels_byte_identical=True,
        solid_components_preserved=True,bounded_field_bias=True),
    simulation=dict(palette='K6 palette 0, native reference green',zooms=[1,1.5,3],
        coordinates='pixel-centre aligned; one Q3m x2 texel = zoom screen pixels',
        backgrounds=['neutral gray RGB119/122/123','synthetic stone, seeded42004'],
        exclusions=['GPU precision','native sprite blur and selection outline','game lighting/tints','complete in-game compositor'],
        proposed_coverage='8x8 screen subpixel integration of continuous bilinear smoothed signed distance',
        RGB='Catmull-Rom 16 taps; premultiplied; alpha clamp/unpremultiply as current shader',
        native_shadow='original shadow plane sampled separately and kept beneath reconstructed foreground'),
    game_files_modified=False,neural_inferences=0,QA='pending-offline-visual-review'))
print(json.dumps(dict(complete=True,selected_frames=len(records),unique_masks=len(cache))),flush=True)
