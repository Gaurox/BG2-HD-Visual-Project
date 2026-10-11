"""AM0510A: authored arch + soft measured halo; remove the static rectangular repaint."""
from common import *
from PIL import Image,ImageDraw
from scipy.ndimage import distance_transform_edt,gaussian_filter,label,binary_fill_holes,binary_dilation
from build_animated_zone_mask import smoothstep

def bezier(points,count=80):
    t=np.linspace(0,1,count)[:,None];a,b,c,d=np.asarray(points,float)
    return ((1-t)**3*a+3*(1-t)**2*t*b+3*(1-t)*t*t*c+t**3*d).tolist()

def main():
    out=BATCH/'mask-AM0510A';out.mkdir(parents=True,exist_ok=False)
    points=[(46,64),(46,24)]+bezier([(46,24),(46,8),(61,3),(77,4)])+bezier([(77,4),(94,4),(106,10),(106,22)])+[(106,59),(98,65)]
    canvas=Image.new('1',(512,512));ImageDraw.Draw(canvas).polygon([(x*4,y*4) for x,y in points],fill=1)
    core=np.asarray(canvas).astype(bool)
    reference=ROOT/'animations/ressources/AM0510A/paint-ready-am0510a/background-x4-512.png'
    bg=np.asarray(Image.open(reference).convert('RGB'))
    # Preserve the map's genuine black window aperture, without retaining floor cracks elsewhere.
    roi=np.zeros((512,512),bool);roi[:260,170:440]=True
    ids,count=label((bg.max(2)<6)&roi)
    sizes=np.bincount(ids.ravel());sizes[0]=0
    aperture=ids==int(np.argmax(sizes));assert aperture.sum()>15000
    core|=binary_dilation(binary_fill_holes(aperture),iterations=3)
    outside=distance_transform_edt(~core)
    window=smoothstep(1-outside/8)
    spatial=ROOT/'animations/ressources/AM0510A/runs/am0510a-seedvr7b-lab-x4-20260919/resources/AM0510A/01_frames_x1/rgba'
    frames=np.stack([np.asarray(Image.open(p).convert('RGBA')) for p in sorted(spatial.glob('*.png'))])
    assert frames.shape==(9,128,128,4)
    luma=frames[...,:3].astype(float)@np.array([.299,.587,.114])
    deviation=np.stack([gaussian_filter(f,2) for f in luma]).std(0)
    # Author a floor-only support around the animated halo; derive its opacity from actual motion.
    support=Image.new('1',(128,128));ImageDraw.Draw(support).polygon([(45,56),(106,54),(125,68),(111,84),(82,89),(53,76)],fill=1)
    gate=gaussian_filter(np.asarray(support).astype(float),2.5)
    halo=gaussian_filter(np.clip((deviation-1.5)/4,0,1)*gate,2)
    halo4=np.asarray(Image.fromarray(halo.astype(np.float32),'F').resize((512,512),Image.Resampling.BICUBIC))
    yy,xx=np.indices(core.shape);edge=smoothstep(np.minimum.reduce([xx,yy,511-xx,511-yy])/12)
    mask=np.rint(np.clip(np.maximum(window,halo4)*edge,0,1)*255).astype(np.uint8)
    assert mask[aperture].min()>=250
    assert np.max(np.concatenate([mask[0],mask[-1],mask[:,0],mask[:,-1]]))==0
    Image.fromarray(np.dstack([mask]*3)).save(out/'mask.png')
    resources=v.validate_v2_pack(AM0510)[1];r=copy.deepcopy(resources[0]);arrays={}
    for f in r['frames']:
        p=pixels(AM0510,f);p[...,3]=np.rint(p[...,3].astype(float)*mask/255).astype(np.uint8)
        p[p[...,3]==0,:3]=0;arrays[('AM0510A',f['frame'])]=p
    pack=write_pack(BATCH/'final-AM0510A',[r],arrays)
    before=Image.fromarray(pixels(AM0510,r['frames'][0]));after=Image.fromarray(arrays[('AM0510A',0)])
    background=Image.fromarray(bg).convert('RGBA')
    compare=Image.new('RGB',(1536,512))
    compare.paste(Image.alpha_composite(background,before).convert('RGB'),(0,0))
    compare.paste(Image.alpha_composite(background,after).convert('RGB'),(512,0))
    compare.paste(Image.fromarray(mask).convert('RGB'),(1024,0));compare.save(out/'comparison.png')
    v.write_json(out/'manifest.json',dict(status='completed',recipe='authored arch/aperture core + motion-weighted floor halo, outward feather8, canvas edge fade12',
        source_pack=rel(AM0510),source_pack_manifest_sha256=v.sha256_file(AM0510/'manifest.json'),
        background_reference=rel(reference),background_sha256=v.sha256_file(reference),mask=rel(out/'mask.png'),mask_sha256=v.sha256_file(out/'mask.png'),
        window_control_points=points,floor_polygon_x1=[(45,56),(106,54),(125,68),(111,84),(82,89),(53,76)],
        aperture_pixels=int(aperture.sum()),opaque_share=float((mask>=250).mean()),visible_share=float((mask>0).mean()),
        original_duration_seconds=.6,output_phases=18,final_pack=rel(pack),final_pack_manifest_sha256=v.sha256_file(pack/'manifest.json'),qa_status='pending-ingame'))
    print('MASK completed; opacity',float((mask>=250).mean()),'visible',float((mask>0).mean()))

if __name__=='__main__':main()
