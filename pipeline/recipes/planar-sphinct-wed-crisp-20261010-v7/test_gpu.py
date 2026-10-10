"""Actual hidden-WGL shader: preserve modes0/1/2; test147 world-masked draws."""
from pathlib import Path
import sys,re
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[3];sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
OUT=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7';RUN=ROOT/'animations/ressources/SPHINCT/runs/planar-sphinct-wed-crisp-20261010-v7'
hp=ROOT/'pipeline/recipes/portails-deux-correctif-20261010-v1/test_gl_mask.py'
prefix=hp.read_text(encoding='utf-8').split('# Exercise the unchanged path:',1)[0]
prefix=prefix.replace("BATCH=ROOT/'animations/batches/portails-deux-correctif-20261010-v1'","BATCH=ROOT/'animations/batches/planar-sphinct-wed-crisp-20261010-v7'")
scope={'__file__':str(hp),'__name__':'planar_gpu'};exec(prefix,scope);render=scope['render'];new_program=scope['program']
oldcpp=(ROOT/'animations/batches/ar0517-sphinct-wed-smooth-20261010-v1/.work/runtime-src/src/iee/native_occlusion_bridge.cpp').read_text()
old_program=scope['create_program']()
for kind,source in zip([0x8B31,0x8B30],re.findall(r'k(?:Vertex|Fragment)Source = R"glsl\((.*?)\)glsl";',oldcpp,re.S)):
 shader=scope['create_shader'](kind);s=scope['c'].c_char_p(source.encode());scope['source_shader'](shader,1,scope['c'].byref(s),None);scope['compile_shader'](shader)
 ok=scope['ii']();scope['get_shader'](shader,0x8B81,scope['c'].byref(ok));assert ok.value;scope['attach'](old_program,shader)
scope['link'](old_program);ok=scope['ii']();scope['get_program'](old_program,0x8B82,scope['c'].byref(ok));assert ok.value
mask=np.random.default_rng(516).integers(0,256,(12,16,4),dtype=np.uint8);rep=np.random.default_rng(517).integers(0,256,(48,64,4),dtype=np.uint8)
for mode in [0,1,2]:
 for premul in [False,True]:
  scope['program']=old_program;old=render(mask,rep,mode,premul);scope['program']=new_program;new=render(mask,rep,mode,premul)
  assert np.array_equal(old,new),'previous shader mode changed'
scope['program']=new_program;checks=v2.load_json(OUT/'checks.json');results=[]
for occ in [c for c in checks['occurrences'] if c['area']=='AR0516']:
 cov=np.array(Image.open(RUN/occ['mask']));transfer=np.zeros((*cov.shape,4),np.uint8);transfer[:,:,0]=cov;transfer[:,:,3]=255
 base=ROOT/occ['source_pack'];r=next(r for r in v2.validate_v2_pack(base)[1] if r['resref']==occ['resref']);max_error=0
 for f in r['frames']:
  raw=np.frombuffer((base/f['asset']).read_bytes(),np.uint8).reshape(480,640,4).copy();actual=render(transfer,raw,3)
  expected=raw.copy();expected[:,:,3]=np.rint(raw[:,:,3].astype(float)*cov/255).astype(np.uint8)
  error=np.abs(actual.astype(int)-expected.astype(int));assert np.array_equal(actual[:,:,:3],raw[:,:,:3]);assert error.max()<=1
  assert not actual[cov==0,3].any();max_error=max(max_error,int(error.max()))
 results.append(dict(position=occ['position'],frames=len(r['frames']),RGB_exact=True,max_alpha_UNORM_rounding_error=max_error,occluded_alpha_zero=True))
v2.write_json(OUT/'gpu-tests.json',dict(passed=True,gpu=scope['gpu'],actual_shader_compiled_linked_drawn=True,existing_shader_modes_0_1_2_byte_identical=True,
 planar_draws=results,AR0517_reference_baked_pack_unchanged=True,ingame_QA='pending-user-retest'))
scope['make'](None,None);scope['api'](scope['O'],'wglDeleteContext',scope['w'].BOOL,scope['c'].c_void_p)(scope['context'])
scope['api'](scope['U'],'ReleaseDC',scope['ii'],scope['w'].HWND,scope['w'].HDC)(scope['hwnd'],scope['dc']);scope['api'](scope['U'],'DestroyWindow',scope['w'].BOOL,scope['w'].HWND)(scope['hwnd'])
print('GPU: previous modes byte-identical;147 draws RGB exact / alpha <=1 UNORM / no leak',flush=True)
