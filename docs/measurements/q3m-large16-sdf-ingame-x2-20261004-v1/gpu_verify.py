"""Reuse the pinned hidden WGL harness; test real Large16 V9 fields against CPU math."""
from pathlib import Path
helper=Path(__file__).resolve().parent.parent/'q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/gpu_verify.py'
text=helper.read_text(encoding='utf-8')
# Setup and raster helper only; no Character trials, asset writes or production.
exec(compile(text[:text.index('programs={};old={}')]+text[text.index('tex=U();output=U();fbo=U();'):text.index('production=json.loads')],str(helper),'exec'))
import run_creature_sprite_x2 as registry
from palette_work_plan import file_sha
work=ROOT/'sprite/.work/q3m-large16-sdf-ingame-x2-20261004-v1'
programs={name:program((work/'runtime-src/assets/override'/(name+'.glsl')).read_text()) for name in ['fpDraw','fpSprite','fpSELECT']}
production=json.loads((HERE/'production.json').read_text());cases=[]
for aid in production['animation_ids']:
    detail=next(d for d in production['details'] if d['animation_id']==aid and d['resref'].endswith('G1'))
    resource=leaves.inspect(work/'isolated'/registry.catalog_shard_filename(detail['V9_sha256']),include_frames=True)['resources'][0]
    for ordinal in [0,len(resource['frames'])//2]:
        frame=resource['frames'][ordinal];i,s,m=(frame[k] for k in ['I','S','M'])
        palette=resource['profile'].source[:,[2,1,0,3]].copy();palette[:,3]=255;palette[0]=0;palette[1,3]=127
        raw=resource['profile'].decode(i,frame['F'],palette)
        encoded=np.zeros((*s.shape,4),np.uint8);valid=m!=0xffffffff
        encoded[valid,:3]=raw.reshape(-1,4)[m[valid],:3];encoded[...,3]=s;encoded[6:-6,6:-6,3]|=(i==1).astype(np.uint8)*128
        field=(s.astype(np.float32)-64)/16
        for zoom in [0.75,1.0,1.5,3.0]:
            expected=render_reconstructed(raw,i,field,zoom);gpu=render(programs['fpDraw'],encoded,zoom,1)
            delta=np.abs(gpu[...,3].astype(int)-np.clip(np.rint(expected[...,3]*255),0,255).astype(int))
            diff=np.abs(composite(gpu.astype(float)/255,(130,124,110)).astype(int)-composite(expected,(130,124,110)).astype(int))
            report=dict(animation_id=aid,resref=detail['resref'],frame=ordinal,zoom=zoom,mean_alpha_error=float(delta.mean()),mean_composited_error=float(diff.mean()))
            assert report['mean_alpha_error']<0.15 and report['mean_composited_error']<0.2,report
            assert np.array_equal(gpu,render(programs['fpSprite'],encoded,zoom,1))
            render(programs['fpSELECT'],encoded,zoom,1);cases.append(report)
write_json(HERE/'gpu-verification.json',dict(passed=True,renderer=renderer,compiled_shaders=list(programs),Large16_views=cases,harness=dict(path=helper.relative_to(ROOT).as_posix(),sha256=file_sha(helper)),shader_contract='byte-identical installed stable V9; no shader changes',ingame_QA=False))
bind(gl,'wglMakeCurrent',I,[ptr,ptr])(None,None);bind(gl,'wglDeleteContext',I,[ptr])(ctx);bind(u,'ReleaseDC',I,[ptr,ptr])(hwnd,dc);bind(u,'DestroyWindow',I,[ptr])(hwnd)
print(json.dumps(dict(GPU=True,views=len(cases),renderer=renderer)))
