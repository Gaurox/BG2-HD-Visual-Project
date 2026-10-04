"""Hidden WGL: V9 range-palette equipment, empty body, native shadow; pinned shaders."""
from pathlib import Path
helper=Path(__file__).resolve().parent.parent/'q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/gpu_verify.py'
source=helper.read_text(encoding='utf-8')
exec(compile(source[:source.index('programs={};old={}')]+source[source.index('tex=U();output=U();fbo=U();'):source.index('production=json.loads')],str(helper),'exec'))
import struct,run_creature_sprite_x2 as registry
from palette_work_plan import file_sha
from sdf_trial import catmull
work=ROOT/'sprite/.work'/HERE.name
programs={name:program((work/'runtime-src/assets/override'/(name+'.glsl')).read_text()) for name in ['fpDraw','fpSprite','fpSELECT']}
production=json.loads((HERE/'production.json').read_text());details={d['resref']:d for d in production['details']};palettes={}
for n in range(8):
    raw=(HERE/f'work/physical-{n}.oracle').read_bytes();pos=12
    for _ in range(struct.unpack_from('<I',raw,8)[0]):
        _,_,ref,nf,nc=struct.unpack_from('<II8sII',raw,pos);pos+=24;ref=ref.rstrip(b'\0').decode();palettes[ref]=np.frombuffer(raw,np.uint8,1024,pos).reshape(256,4).copy();pos+=6144+2052
        for __ in range(nc):count=struct.unpack_from('<I',raw,pos)[0];pos+=4+count*4
        pos+=nf*208
cases=[]
refs=['MDGU1G1','CSHDG1']+[r for r in ['WPMMCG1','WPMD1G1','WPMH0G1'] if r in details]
assert len(refs)==5
for ref in refs:
    detail=details[ref];resource=leaves.inspect(work/'isolated'/registry.catalog_shard_filename(detail['V9_sha256']),include_frames=True)['resources'][0]
    for ordinal in [0,len(resource['frames'])//2]:
        f=resource['frames'][ordinal];i,s,m=(f[k] for k in ['I','S','M']);raw=resource['profile'].decode(i,f['F'],palettes[ref])
        encoded=np.zeros((*s.shape,4),np.uint8);valid=m!=0xffffffff;encoded[valid,:3]=raw.reshape(-1,4)[m[valid],:3];encoded[...,3]=s;encoded[6:-6,6:-6,3]|=(i==1).astype(np.uint8)*128
        field=(s.astype(np.float32)-64)/16
        for zoom in [0.75,1.0,1.5,3.0]:
            expected=render_reconstructed(raw,i,field,zoom) if np.any(i>=2) else catmull(np.pad(raw,((6,6),(6,6),(0,0))),zoom)
            gpu=render(programs['fpDraw'],encoded,zoom,1);delta=np.abs(gpu[...,3].astype(int)-np.clip(np.rint(expected[...,3]*255),0,255).astype(int))
            diff=np.abs(composite(gpu.astype(float)/255,(130,124,110)).astype(int)-composite(expected,(130,124,110)).astype(int))
            report=dict(resref=ref,frame=ordinal,zoom=zoom,mean_alpha_error=float(delta.mean()),mean_composited_error=float(diff.mean()))
            assert report['mean_alpha_error']<0.15 and report['mean_composited_error']<0.2,report
            assert np.array_equal(gpu,render(programs['fpSprite'],encoded,zoom,1));render(programs['fpSELECT'],encoded,zoom,1);cases.append(report)
write_json(HERE/'gpu-verification.json',dict(passed=True,renderer=renderer,compiled_shaders=list(programs),views=cases,harness=dict(path=helper.relative_to(ROOT).as_posix(),sha256=file_sha(helper)),shader_contract='unchanged installed stable V9',ingame_QA=False))
bind(gl,'wglMakeCurrent',I,[ptr,ptr])(None,None);bind(gl,'wglDeleteContext',I,[ptr])(ctx);bind(u,'ReleaseDC',I,[ptr,ptr])(hwnd,dc);bind(u,'DestroyWindow',I,[ptr])(hwnd)
print(json.dumps(dict(GPU=True,views=len(cases),renderer=renderer)))
