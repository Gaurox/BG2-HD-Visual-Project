"""Exercise the actual bridge GLSL in a hidden WGL context, without launching BG2."""
from pathlib import Path
import ctypes as c
from ctypes import wintypes as w
import re, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
BATCH=ROOT/'animations/batches/portails-deux-correctif-20261010-v1'
BUILD=BATCH/'.work/runtime-build/Release'
U=c.WinDLL('user32'); G=c.WinDLL('gdi32'); O=c.WinDLL('opengl32')
def api(lib,name,restype,*args):
    f=getattr(lib,name);f.restype=restype;f.argtypes=args;return f
create=api(U,'CreateWindowExW',w.HWND,w.DWORD,w.LPCWSTR,w.LPCWSTR,w.DWORD,c.c_int,c.c_int,c.c_int,c.c_int,w.HWND,w.HMENU,w.HINSTANCE,c.c_void_p)
getdc=api(U,'GetDC',w.HDC,w.HWND)
class PFD(c.Structure):
    _fields_=[('size',w.WORD),('version',w.WORD),('flags',w.DWORD)]+[(n,c.c_ubyte) for n in ['type','colour','red','redShift','green','greenShift','blue','blueShift','alpha','alphaShift','accum','accumRed','accumGreen','accumBlue','accumAlpha','depth','stencil','aux','layer','reserved']]+[(n,w.DWORD) for n in ['layerMask','visibleMask','damageMask']]
p=PFD();p.size=c.sizeof(PFD);p.version=1;p.flags=0x25;p.colour=32;p.alpha=8
hwnd=create(0,'STATIC','BG2 occlusion shader test',0x80000000,0,0,64,64,None,None,None,None)
assert hwnd
dc=getdc(hwnd)
choose=api(G,'ChoosePixelFormat',c.c_int,w.HDC,c.POINTER(PFD));setpf=api(G,'SetPixelFormat',w.BOOL,w.HDC,c.c_int,c.POINTER(PFD))
assert setpf(dc,choose(dc,c.byref(p)),c.byref(p))
make=api(O,'wglMakeCurrent',w.BOOL,w.HDC,c.c_void_p);createctx=api(O,'wglCreateContext',c.c_void_p,w.HDC)
context=createctx(dc);assert context and make(dc,context)
getproc=api(O,'wglGetProcAddress',c.c_void_p,c.c_char_p)
def gl(name,result,*args):
    addr=getproc(name.encode())
    if addr and addr not in (1,2,3,c.c_void_p(-1).value): return c.WINFUNCTYPE(result,*args)(addr)
    return api(O,name,result,*args)
ui=c.c_uint; ii=c.c_int; ptr=c.c_void_p
getstring=gl('glGetString',c.c_char_p,ui)
gpu=getstring(0x1F01).decode();version=getstring(0x1F02).decode()
create_shader=gl('glCreateShader',ui,ui);source_shader=gl('glShaderSource',None,ui,ii,c.POINTER(c.c_char_p),c.POINTER(ii));compile_shader=gl('glCompileShader',None,ui)
get_shader=gl('glGetShaderiv',None,ui,ui,c.POINTER(ii));get_shader_log=gl('glGetShaderInfoLog',None,ui,ii,c.POINTER(ii),c.c_char_p)
create_program=gl('glCreateProgram',ui);attach=gl('glAttachShader',None,ui,ui);link=gl('glLinkProgram',None,ui);get_program=gl('glGetProgramiv',None,ui,ui,c.POINTER(ii));use=gl('glUseProgram',None,ui)
getuniform=gl('glGetUniformLocation',ii,ui,c.c_char_p);uniform=gl('glUniform1i',None,ii,ii)
gen_tex=gl('glGenTextures',None,ii,c.POINTER(ui));bind_tex=gl('glBindTexture',None,ui,ui);active=gl('glActiveTexture',None,ui);teximage=gl('glTexImage2D',None,ui,ii,ii,ii,ii,ii,ui,ui,ptr);parameter=gl('glTexParameteri',None,ui,ui,ii)
gen_fbo=gl('glGenFramebuffers',None,ii,c.POINTER(ui));bind_fbo=gl('glBindFramebuffer',None,ui,ui);attach_tex=gl('glFramebufferTexture2D',None,ui,ui,ui,ui,ii);status=gl('glCheckFramebufferStatus',ui,ui)
gen_vao=gl('glGenVertexArrays',None,ii,c.POINTER(ui));bind_vao=gl('glBindVertexArray',None,ui);viewport=gl('glViewport',None,ii,ii,ii,ii);draw=gl('glDrawArrays',None,ui,ii,ii);read=gl('glReadPixels',None,ii,ii,ii,ii,ui,ui,ptr)
error=gl('glGetError',ui);disable=gl('glDisable',None,ui)
cpp=(BATCH/'.work/runtime-src/src/iee/native_occlusion_bridge.cpp').read_text()
sources=re.findall(r'k(?:Vertex|Fragment)Source = R"glsl\((.*?)\)glsl";',cpp,re.S);assert len(sources)==2
program=create_program()
for kind,text in zip([0x8B31,0x8B30],sources):
    shader=create_shader(kind);s=c.c_char_p(text.encode());source_shader(shader,1,c.byref(s),None);compile_shader(shader)
    ok=ii();get_shader(shader,0x8B81,c.byref(ok));log=c.create_string_buffer(8192);get_shader_log(shader,8192,None,log)
    assert ok.value,log.value.decode();attach(program,shader)
link(program);ok=ii();get_program(program,0x8B82,c.byref(ok));assert ok.value
tex=(ui*3)();gen_tex(3,tex);fbo=ui();gen_fbo(1,c.byref(fbo));vao=ui();gen_vao(1,c.byref(vao));bind_vao(vao)
for cap in [0x0BE2,0x0B44,0x0B71,0x0C11,0x0B90,0x8DB9,0x0BD0]: disable(cap)
def texture(unit,id,pixels):
    h,width=pixels.shape[:2];active(0x84C0+unit);bind_tex(0x0DE1,id)
    teximage(0x0DE1,0,0x8058,width,h,0,0x1908,0x1401,pixels.ctypes.data)
    for key,value in [(0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812F),(0x2803,0x812F)]: parameter(0x0DE1,key,value)
def render(mask,replacement,feather=False,premul=False):
    h,width=replacement.shape[:2];scale=width//mask.shape[1]
    texture(0,tex[0],replacement);texture(1,tex[1],mask);texture(2,tex[2],np.zeros_like(replacement))
    bind_fbo(0x8D40,fbo);attach_tex(0x8D40,0x8CE0,0x0DE1,tex[2],0);assert status(0x8D40)==0x8CD5
    use(program)
    for name,value in [('uReplacement',0),('uVisibility',1),('uScale',scale),('uPremultiplied',int(premul)),('uInwardFeather',int(feather))]:
        loc=getuniform(program,name.encode());assert loc>=0;uniform(loc,value)
    viewport(0,0,width,h);draw(4,0,3);out=np.zeros_like(replacement);read(0,0,width,h,0x1908,0x1401,out.ctypes.data);assert error()==0
    return out

# Exercise the unchanged path: complete clears, neighbour B and fixed black dither.
mask=np.zeros((12,16,4),np.uint8);mask[:,:,0]=255;mask[:,:,3]=255;mask[:,:4,0]=0;mask[:,5,2]=255;mask[:,9,1]=79;mask[:,12,0]=127
rep=np.zeros((48,64,4),np.uint8);rep[:]=[160,100,220,255]
control=render(mask,rep);m=mask.repeat(4,0).repeat(4,1);expected=rep.copy()
expected[(m[:,:,0]==0)|(m[:,:,2]>0)]=0;expected[m[:,:,1]>0]=[0,0,0,79]
expected[(m[:,:,0]==127)&(m[:,:,1]==0),3]=127
assert np.array_equal(control,expected),'ordinary mask/dither shader regression'
premul_control=render(mask,rep,premul=True)
premul_expected=np.rint(rep.astype(np.float32)*(m[:,:,0,None]/255.)).astype(np.uint8)
premul_expected[m[:,:,2]>0]=0;premul_expected[m[:,:,1]>0]=[0,0,0,79]
assert np.array_equal(premul_control,premul_expected),'creature fractional/mask/dither shader regression'

# A native-size diagonal mask matched to the OH8100 WED180 boundary and BDF frame50.
leaf=ROOT/'animations/batches/portails-deux-correctif-20261010-v1/artifacts/BDFORCEW-final-split/OH8100'
r=v2.validate_v2_pack(leaf)[1][0];frame=r['frames'][50];lw,lh=frame['logical_size_x1'];cx,cy=frame['centre_x1']
yy,xx=np.indices((lh,lw));worldx=2286-cx+xx+0.5;worldy=820-cy+yy+0.5
inside=worldy>1011-(303/431)*(worldx-2129)
mask=np.zeros((lh,lw,4),np.uint8);mask[:,:,0]=np.where(inside,0,255);mask[:,:,3]=255
fixture=BATCH/'.work/WED180-native-transfer.rgba';fixture.write_bytes(mask.tobytes());fitted=BATCH/'.work/WED180-covered-transfer.rgba'
subprocess.run([str(BUILD/'iee_native_occlusion_feather_tests.exe'),str(lw),str(lh),str(fixture),str(fitted)],check=True)
coverage=np.frombuffer(fitted.read_bytes(),np.uint8).reshape(lh,lw,4).copy()
assert np.array_equal(coverage[:,:,:3],mask[:,:,:3])
rep=np.frombuffer((leaf/frame['asset']).read_bytes(),np.uint8).reshape(lh*4,lw*4,4).copy()
oldleaf=ROOT/'animations/packs-par-zone/portails-cinq-selection-20261010-v1-complete/OH8100';oldr=next(q for q in v2.validate_v2_pack(oldleaf)[1] if q['resref']=='BDFORCEW');oldframe=oldr['frames'][50]
oldrep=np.frombuffer((oldleaf/oldframe['asset']).read_bytes(),np.uint8).reshape(rep.shape).copy()
old=render(mask,oldrep);new=render(coverage,rep,True)
outside=(mask[:,:,0]==0).repeat(4,0).repeat(4,1);assert not new[outside].any()
baseline=render(mask,rep);assert np.all(new<=baseline),'inward smoothing revealed/gained pixels'
assert np.count_nonzero(new[:,:,:3]!=baseline[:,:,:3])>0,'coverage did not affect BDF'
# Confirm continuous coverage actually attenuates additive RGB, even with premul flag off.
solid=np.empty_like(rep);solid[:]=[160,100,220,255]
smooth=render(coverage,solid,True);assert len(np.unique(smooth[:,:,0]))>12
assert not smooth[outside].any()
for name,image in [('WED180-before',old),('WED180-corrected',new)]:
    bg=np.full(image[:,:,:3].shape,[24,27,33],np.uint16)
    Image.fromarray(np.minimum(bg+image[:,:,:3],255).astype(np.uint8)).save(BATCH/'previews'/(name+'.png'))
board=Image.new('RGB',(lw*8+16,lh*4+66),(24,27,33));font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',22);d=ImageDraw.Draw(board)
d.text((12,8),'BDFORCEW — alpha et occlusion WED180 (simulation GPU)',font=font,fill='white');d.text((12,36),'Avant',font=font,fill='white');d.text((lw*4+28,36),'SplineFit1 + coverage WED',font=font,fill='white')
for image,x in [(old,0),(new,lw*4+16)]: board.paste(Image.fromarray(np.minimum(image[:,:,:3].astype(np.uint16)+np.array([24,27,33]),255).astype(np.uint8)),(x,66))
board.save(BATCH/'previews/BDFORCEW-WED-before-after.png')
v2.write_json(BATCH/'renderer-gl-tests.json',dict(passed=True,gpu=gpu,opengl=version,actual_shader_compiled_linked_drawn=True,ordinary_and_dither_shader_exact=True,creature_fractional_and_dither_shader_exact=True,native_transfer_rgb_preserved=True,no_occluded_pixel_revealed=True,additive_rgb_coverage_applied=True,coverage_levels=len(np.unique(smooth[:,:,0])),fixture='OH8100 WED180 diagonal, BDFORCEW frame50 at first occurrence',ingame_QA=False))
make(None,None);api(O,'wglDeleteContext',w.BOOL,c.c_void_p)(context);api(U,'ReleaseDC',ii,w.HWND,w.HDC)(hwnd,dc);api(U,'DestroyWindow',w.BOOL,w.HWND)(hwnd)
print('actual GLSL mask test: passed — '+gpu,flush=True)
