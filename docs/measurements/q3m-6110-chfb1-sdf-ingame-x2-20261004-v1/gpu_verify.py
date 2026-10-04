"""Hidden WGL context: compile live shaders and compare raster output to PDF math."""
import ctypes as c, json, sys, subprocess, hashlib
from pathlib import Path
import numpy as np
from PIL import Image
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2];E=ROOT/'engine/InfinityEngine-Enhancer/source-patchee'
sys.path.insert(0,str(ROOT/'pipeline/scripts'));sys.path.insert(0,str(HERE.parent/'q3m-ankheg-sdf-offline-x2-20261004-v1'))
import palette_partner_registry as leaves
from sdf_trial import render_reconstructed,composite,RECIPE
from sprite_sdf_registry import planes
from palette_work_plan import write_json

u=c.WinDLL('user32');g=c.WinDLL('gdi32');gl=c.WinDLL('opengl32')
def bind(lib,name,rest,args):
    f=getattr(lib,name);f.restype=rest;f.argtypes=args;return f
ptr=c.c_void_p;U=c.c_uint;I=c.c_int;F=c.c_float
create=bind(u,'CreateWindowExW',ptr,[U,c.c_wchar_p,c.c_wchar_p,U,I,I,I,I,ptr,ptr,ptr,ptr])
hwnd=create(0,'STATIC','SDF hidden verifier',0x80000000,0,0,16,16,None,None,None,None)
assert hwnd
dc=bind(u,'GetDC',ptr,[ptr])(hwnd)
class PFD(c.Structure):
    _fields_=[('size',c.c_ushort),('version',c.c_ushort),('flags',U),('pixel',c.c_byte),('color',c.c_byte),('r',c.c_byte),('rs',c.c_byte),('g',c.c_byte),('gs',c.c_byte),('b',c.c_byte),('bs',c.c_byte),('a',c.c_byte),('ashift',c.c_byte),('accum',c.c_byte),('ar',c.c_byte),('ag',c.c_byte),('ab',c.c_byte),('aa',c.c_byte),('depth',c.c_byte),('stencil',c.c_byte),('aux',c.c_byte),('layer',c.c_byte),('reserved',c.c_byte),('layerMask',U),('visibleMask',U),('damageMask',U)]
pfd=PFD();pfd.size=c.sizeof(PFD);pfd.version=1;pfd.flags=0x24;pfd.color=32;pfd.a=8
fmt=bind(g,'ChoosePixelFormat',I,[ptr,c.POINTER(PFD)])(dc,c.byref(pfd));assert fmt
assert bind(g,'SetPixelFormat',I,[ptr,I,c.POINTER(PFD)])(dc,fmt,c.byref(pfd))
ctx=bind(gl,'wglCreateContext',ptr,[ptr])(dc);assert ctx
assert bind(gl,'wglMakeCurrent',I,[ptr,ptr])(dc,ctx)
address=bind(gl,'wglGetProcAddress',ptr,[c.c_char_p])
def fun(name,rest,args):
    try:return bind(gl,name,rest,args)
    except AttributeError:
        a=address(name.encode());assert a and a not in (1,2,3,0xffffffffffffffff),name
        return c.WINFUNCTYPE(rest,*args)(a)
getString=fun('glGetString',c.c_char_p,[U]);renderer=getString(0x1f01).decode()
createShader=fun('glCreateShader',U,[U]);shaderSource=fun('glShaderSource',None,[U,I,c.POINTER(c.c_char_p),ptr]);compileShader=fun('glCompileShader',None,[U])
getShader=fun('glGetShaderiv',None,[U,U,c.POINTER(I)]);shaderLog=fun('glGetShaderInfoLog',None,[U,I,ptr,ptr])
createProgram=fun('glCreateProgram',U,[]);attach=fun('glAttachShader',None,[U,U]);link=fun('glLinkProgram',None,[U]);getProgram=fun('glGetProgramiv',None,[U,U,c.POINTER(I)]);programLog=fun('glGetProgramInfoLog',None,[U,I,ptr,ptr]);use=fun('glUseProgram',None,[U])
getLoc=fun('glGetUniformLocation',I,[U,c.c_char_p]);uniform1=fun('glUniform1f',None,[I,F]);uniform2=fun('glUniform2f',None,[I,F,F])
genTex=fun('glGenTextures',None,[I,c.POINTER(U)]);bindTex=fun('glBindTexture',None,[U,U]);texImage=fun('glTexImage2D',None,[U,I,I,I,I,I,U,U,ptr]);param=fun('glTexParameteri',None,[U,U,I])
genFbo=fun('glGenFramebuffers',None,[I,c.POINTER(U)]);bindFbo=fun('glBindFramebuffer',None,[U,U]);attachFbo=fun('glFramebufferTexture2D',None,[U,U,U,U,I]);status=fun('glCheckFramebufferStatus',U,[U])
viewport=fun('glViewport',None,[I,I,I,I]);begin=fun('glBegin',None,[U]);end=fun('glEnd',None,[]);texcoord=fun('glTexCoord2f',None,[F,F]);vertex=fun('glVertex2f',None,[F,F]);read=fun('glReadPixels',None,[I,I,I,I,U,U,ptr]);finish=fun('glFinish',None,[]);error=fun('glGetError',U,[]);pixelStore=fun('glPixelStorei',None,[U,I])
head='#version 120\n#define lowp\n#define mediump\n#define highp\n'
vs='varying vec2 vTc; varying vec4 vColor; void main(){gl_Position=gl_Vertex;vTc=gl_MultiTexCoord0.xy;vColor=vec4(1.0);}'
def shader(kind,source):
    handle=createShader(kind);encoded=(head+source).encode();p=c.c_char_p(encoded);shaderSource(handle,1,c.byref(p),None);compileShader(handle);ok=I();getShader(handle,0x8b81,c.byref(ok))
    if not ok.value:
        log=c.create_string_buffer(65536);shaderLog(handle,len(log),None,log);raise ValueError(log.value.decode())
    return handle
vsid=shader(0x8b31,vs)
def program(source):
    p=createProgram();attach(p,vsid);attach(p,shader(0x8b30,source));link(p);ok=I();getProgram(p,0x8b82,c.byref(ok))
    if not ok.value:
        log=c.create_string_buffer(65536);programLog(p,len(log),None,log);raise ValueError(log.value.decode())
    return p
programs={};old={}
for name in ('fpDraw','fpSprite','fpSELECT'):
    path=E/'assets/override'/ (name+'.glsl');programs[name]=program(path.read_text())
    original=subprocess.run(['git','show','16b01e52:'+path.relative_to(ROOT).as_posix()],cwd=ROOT,capture_output=True,check=True).stdout.decode()
    old[name]=program(original)
tex=U();output=U();fbo=U();genTex(1,c.byref(tex));genTex(1,c.byref(output));genFbo(1,c.byref(fbo))
def render(p,rgba,zoom,sdf):
    h,w=rgba.shape[:2];ow,oh=int(np.ceil(w*zoom)),int(np.ceil(h*zoom))
    bindTex(0x0de1,output);texImage(0x0de1,0,0x8058,ow,oh,0,0x1908,0x1401,None)
    bindFbo(0x8d40,fbo);attachFbo(0x8d40,0x8ce0,0x0de1,output,0);assert status(0x8d40)==0x8cd5
    bindTex(0x0de1,tex);pixelStore(0x0cf5,1);texImage(0x0de1,0,0x8058,w,h,0,0x1908,0x1401,rgba.ctypes.data)
    for pname,value in ((0x2801,0x2600),(0x2800,0x2600),(0x2802,0x812f),(0x2803,0x812f)):param(0x0de1,pname,value)
    use(p)
    for name,value in (('uIeeCreatureFilterMode',2),('uIeeCreatureSdfEncoded',int(sdf)),('uIeeCreatureSdfCharacter',int(sdf==2)),('uSpriteBlurAmount',1)):
        location=getLoc(p,name.encode())
        if location>=0:uniform1(location,value)
    for name in ('uIeeCreatureTexelSize','uTcScale'):
        location=getLoc(p,name.encode())
        if location>=0:uniform2(location,1/w,1/h)
    viewport(0,0,ow,oh);begin(7)
    # Align screen-pixel footprint to the CPU's specified zoom, including ceil.
    for x,y,tx,ty in ((-1,-1,0,0),(1,-1,ow/(w*zoom),0),(1,1,ow/(w*zoom),oh/(h*zoom)),(-1,1,0,oh/(h*zoom))):
        texcoord(tx,ty);vertex(x,y)
    end();finish();result=np.empty((oh,ow,4),np.uint8);read(0,0,ow,oh,0x1908,0x1401,result.ctypes.data);assert error()==0
    return result

production=json.loads((HERE/'production.json').read_text());work=ROOT/production['work_dir'];assets=HERE/'gpu';assets.mkdir(exist_ok=True)
cases=[];neutral=[];ankheg=[]
for witness in production['witnesses']:
    z=np.load(ROOT/witness['path']);i,f,s,m,raw=(z[k] for k in ('I','F','S','M','raw'))
    encoded=np.zeros((*s.shape,4),np.uint8);valid=m!=0xffffffff
    encoded[valid,:3]=raw.reshape(-1,4)[m[valid],:3];encoded[...,3]=s
    encoded[6:-6,6:-6,3]|=(i==1).astype(np.uint8)*128
    field=(s.astype(np.float32)-64)/16
    for zoom in (0.75,1.0,1.5,3.0):
        expected=render_reconstructed(raw,i,field,zoom)
        gpu=render(programs['fpDraw'],encoded,zoom,2)
        delta=np.abs(gpu[...,3].astype(int)-np.clip(np.rint(expected[...,3]*255),0,255).astype(int))
        diff=np.abs(composite(gpu.astype(float)/255,(130,124,110)).astype(int)-composite(expected,(130,124,110)).astype(int))
        report=dict(witness=Path(witness['path']).stem,zoom=zoom,mean_alpha_error=float(delta.mean()),mean_composited_error=float(diff.mean()))
        assert report['mean_alpha_error']<0.15 and report['mean_composited_error']<0.2,report
        sprite=render(programs['fpSprite'],encoded,zoom,2);assert np.array_equal(gpu,sprite),'sprite blur changed SDF'
        render(programs['fpSELECT'],encoded,zoom,2)
        if zoom==3:
            Image.fromarray(composite(gpu.astype(float)/255,(130,124,110))).save(assets/(Path(witness['path']).stem+'-sdf.png'))
            ordinary=np.pad(raw,((6,6),(6,6),(0,0)))
            before=render(old['fpDraw'],ordinary,zoom,0)
            Image.fromarray(composite(before.astype(float)/255,(130,124,110))).save(assets/(Path(witness['path']).stem+'-before.png'))
        cases.append(report)
    ordinary=np.pad(raw,((6,6),(6,6),(0,0)))
    for name in programs:
        assert np.array_equal(render(old[name],ordinary,1.5,0),render(programs[name],ordinary,1.5,0)),(name,'ordinary draw changed')
        neutral.append(dict(witness=Path(witness['path']).stem,shader=name,byte_identical=True))
# V9 Ankheg shader mode1 retains exactly its original shadow127 and colour result.
directory=ROOT/'sprite/.work/q3m-ankheg-sdf-ingame-x2-20261004-v1/isolated'
for file in sorted(directory.glob('CreatureSprites-XN-*.registry'))[:3]:
    resource=leaves.inspect(file,include_frames=True)['resources'][0];frame=resource['frames'][0];i,s,m=(frame[k] for k in ('I','S','M'))
    palette=resource['profile'].source[:,[2,1,0,3]].copy();palette[:,3]=255;palette[0]=0;palette[1]=[0,0,0,127]
    raw=resource['profile'].decode(i,frame['F'],palette)
    encoded=np.zeros((*s.shape,4),np.uint8);valid=m!=0xffffffff
    encoded[valid,:3]=raw.reshape(-1,4)[m[valid],:3];encoded[...,3]=s;encoded[6:-6,6:-6,3]|=(i==1).astype(np.uint8)*128
    for name in programs:
        assert np.array_equal(render(old[name],encoded,1.5,1),render(programs[name],encoded,1.5,1)),(name,'Ankheg changed')
        ankheg.append(dict(resref=resource['resref'],shader=name,byte_identical=True))
write_json(HERE/'gpu-verification.json',dict(passed=True,renderer=renderer,compiled_shaders=list(programs),Character_SDF_views=cases,neutral_draws=neutral,Ankheg_unchanged=ankheg,ingame_QA=False))
bind(gl,'wglMakeCurrent',I,[ptr,ptr])(None,None);bind(gl,'wglDeleteContext',I,[ptr])(ctx);bind(u,'ReleaseDC',I,[ptr,ptr])(hwnd,dc);bind(u,'DestroyWindow',I,[ptr])(hwnd)

