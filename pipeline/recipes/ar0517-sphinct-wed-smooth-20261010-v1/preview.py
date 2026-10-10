"""WED-derived arch fixture and actual GPU comparison; simulation, never ingame QA."""
from pathlib import Path
import sys,json,subprocess,re,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
OUT=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1'
LEAF=ROOT/'animations/packs-par-zone/combined-20260917-active-plus-visual-regression-fix/AR0517'
report=json.loads((OUT/'diagnosis.json').read_text())
arch=next(p for p in report['polygons'] if p['index']==3)
# Use the unchanged hidden-WGL harness, with the exact new bridge shader.
hp=ROOT/'pipeline/recipes/portails-deux-correctif-20261010-v1/test_gl_mask.py'
prefix=hp.read_text(encoding='utf-8').split('# Exercise the unchanged path:',1)[0]
prefix=prefix.replace("BATCH=ROOT/'animations/batches/portails-deux-correctif-20261010-v1'",
                      "BATCH=ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1'")
scope={'__file__':str(hp),'__name__':'ar0517_gpu_preview'};exec(prefix,scope)
render=scope['render']
new_program=scope['program']
baseline_cpp=(ROOT/'animations/batches/bdforcew-shift-right-20261010-v3/.work/runtime-src/src/iee/native_occlusion_bridge.cpp').read_text()
old_program=scope['create_program']()
for kind,text in zip([0x8B31,0x8B30],re.findall(r'k(?:Vertex|Fragment)Source = R"glsl\((.*?)\)glsl";',baseline_cpp,re.S)):
 shader=scope['create_shader'](kind);s=scope['c'].c_char_p(text.encode())
 scope['source_shader'](shader,1,scope['c'].byref(s),None);scope['compile_shader'](shader)
 ok=scope['ii']();scope['get_shader'](shader,0x8B81,scope['c'].byref(ok));assert ok.value
 scope['attach'](old_program,shader)
scope['link'](old_program);ok=scope['ii']();scope['get_program'](old_program,0x8B82,scope['c'].byref(ok));assert ok.value
mask=np.zeros((12,16,4),np.uint8);mask[:,:,0]=255;mask[:,:,3]=255
mask[:,:4,0]=0;mask[:,5,2]=255;mask[:,9,1]=79;mask[:,12,0]=127
rep=np.random.default_rng(517).integers(0,256,(48,64,4),dtype=np.uint8)
for mode,premul in [(False,False),(False,True),(True,False),(True,True)]:
 scope['program']=old_program;old=render(mask,rep,mode,premul)
 scope['program']=new_program;new=render(mask,rep,mode,premul)
 assert np.array_equal(old,new),'existing shader path changed'
resource=v2.validate_v2_pack(LEAF)[1][0];frame=resource['frames'][29]
lw,lh=frame['logical_size_x1'];cx,cy=frame['centre_x1'];x,y=497,452
bitmap=Image.new('L',(832,960));ImageDraw.Draw(bitmap).polygon([tuple(p) for p in arch['points']],fill=255)
cut=np.asarray(bitmap.crop((x-cx,y-cy,x-cx+lw,y-cy+lh)))>0
transfer=np.zeros((lh,lw,4),np.uint8);transfer[:,:,0]=np.where(cut,0,255);transfer[:,:,3]=255
transfer.tofile(OUT/'arch-transfer.rgba')
exe=OUT/'.work/runtime-build/Release/iee_native_occlusion_feather_tests.exe'
subprocess.run([str(exe),str(lw),str(lh),str(OUT/'arch-transfer.rgba'),str(OUT/'arch-coverage.rgba')],check=True)
covered=np.fromfile(OUT/'arch-coverage.rgba',np.uint8).reshape(lh,lw,4)
assert np.array_equal(covered[:,:,:3],transfer[:,:,:3])
assert not covered[cut,3].any()
outside=cut.repeat(4,0).repeat(4,1)
frames=[]
for f in resource['frames']:
 w,h=f['physical_size_x4'];raw=np.frombuffer((LEAF/f['asset']).read_bytes(),np.uint8).reshape(h,w,4).copy()
 before=render(transfer,raw);after=render(covered,raw,2)
 assert not after[outside].any(),'occluded pixels revealed'
 assert np.array_equal(after[~outside,:3],raw[~outside,:3]),'straight RGB attenuated twice'
 assert np.all(after[:,:,3]<=before[:,:,3]),'coverage expanded past native mask'
 # Accepted additive BDFORCEW mode 1 still has the same alpha, with RGB attenuated once.
 mode1=render(covered,raw,True)
 assert np.array_equal(mode1[:,:,3],after[:,:,3])
 frames.append(dict(frame=f['frame'],cleared_pixels_stay_zero=True,straight_RGB_preserved=True))
 if f['frame']==29:selected=(before,after)
bg=Image.open(ROOT/'maps/AR0517/runs/seedvr2-7b-int8-lab-direct-x4/tuiles-principales/01_upscale/AR0517-tuiles-principales-x4-seedvr2-7b-int8-lab.png').convert('RGB')
assert bg.size==(3328,3840)
def panel(a):
 box=((x-cx)*4,(y-cy)*4,(x-cx+lw)*4,(y-cy+lh)*4)
 scene=bg.copy();back=np.asarray(scene.crop(box)).astype(float)
 alpha=a[:,:,3,None].astype(float)/255
 merged=np.rint(back*(1-alpha)+a[:,:,:3]*alpha).clip(0,255).astype(np.uint8)
 scene.paste(Image.fromarray(merged),(box[0],box[1]))
 return scene.crop((370*4,350*4,620*4,565*4)).resize((750,645),Image.Resampling.BOX)
board=Image.new('RGB',(1520,710),(20,23,29));d=ImageDraw.Draw(board);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',21)
for offset,title,pixels in [(0,'Avant : masque natif x1 agrandi',selected[0]),(770,'Correctif : bord WED lisse / alpha seul',selected[1])]:
 d.text((offset+10,10),title,font=font,fill='white');board.paste(panel(pixels),(offset,55))
board.save(OUT/'SPHINCT-AR0517-before-after.png')
v2.write_json(OUT/'gpu-tests.json',dict(passed=True,actual_new_shader_compiled_linked_drawn=True,
 gpu=scope['gpu'],frames=frames,straight_RGB_preserved=True,no_occluded_pixel_revealed=True,
 preview='WED polygon3 raster fixture on processed AR0517 background; simulation, not actual engine capture',
 native_transfer_RGB_preserved=True,existing_shader_modes_0_1_byte_identical=True,ingame_QA='pending'))
scope['make'](None,None)
scope['api'](scope['O'],'wglDeleteContext',scope['w'].BOOL,scope['c'].c_void_p)(scope['context'])
scope['api'](scope['U'],'ReleaseDC',scope['ii'],scope['w'].HWND,scope['w'].HDC)(scope['hwnd'],scope['dc'])
scope['api'](scope['U'],'DestroyWindow',scope['w'].BOOL,scope['w'].HWND)(scope['hwnd'])
print('49 frames / straight RGB / no leak / GPU preview: passed',flush=True)
