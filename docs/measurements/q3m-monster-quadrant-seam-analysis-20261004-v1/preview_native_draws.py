"""Replay per-part draw of seam-only encoded prototype, with unchanged shader."""
import ast,json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
HERE=Path(__file__).resolve().parent
namespace=dict(np=np);tree=ast.parse((HERE/'analyze.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('sample','weights','background')],type_ignores=[]),str(HERE/'analyze.py'),'exec'),namespace)
sample=namespace['sample'];background=namespace['background'];data=json.loads((HERE/'context-probe.json').read_text());reports=[]
for record in data['cases']:
    aid=record['animation_id'];seq=record['seq'];slot=record['slot'];label=aid[2:]+'-s'+str(seq)+'-t'+str(slot);g=record['geometry'];nonempty=[a for a in g if a[0]*a[1]]
    left=min(-a[2] for a in nonempty);top=min(-a[3] for a in nonempty)
    images=[np.array(Image.open(HERE/'work'/(label+'-v'+str(i)+'.png')).convert('RGBA')) for i in (0,2)]
    H,W=images[0].shape[:2];zoom=5;yy,xx=np.mgrid[:H*zoom//2,:W*zoom//2];wx=(xx+.5)/zoom;wy=(yy+.5)/zoom;out=[]
    for canvas in images:
        result=np.empty((*wx.shape,4));result[:,:,:3]=.26;result[:,:,3]=1
        for a in g:
            if not a[0]*a[1]:continue
            x=-a[2]-left;y=-a[3]-top;w,h=a[0],a[1];im=canvas[y*2:(y+h)*2,x*2:(x+w)*2]
            # Source quadrants are disjoint, so crops are the exact per-part pixels.
            m=(wx>=x)&(wx<x+w)&(wy>=y)&(wy<y+h);s=sample(im,(wx-x)*2-.5,(wy-y)*2-.5)
            result[m,:3]=s[m,:3]*s[m,3:4]+result[m,:3]*(1-s[m,3:4])
        out.append(background(result))
    assembled=background(sample(images[1],wx*2-.5,wy*2-.5));out.append(assembled)
    seam_x=-left;seam_y=-40-top;band=(abs(wx-seam_x)<1.5)|(abs(wy-seam_y)<1.5)
    changed=np.max(abs(out[0].astype(int)-out[1].astype(int)),axis=2)
    residual=np.max(abs(out[1].astype(int)-out[2].astype(int)),axis=2)
    rec=dict(animation_id=aid,seq=seq,slot=slot,prototype_render='unchanged four native draws / CLAMP_TO_EDGE / neutral CatmullRom / native outline not simulated',native_seam_pixels_changed_gt8=int(((changed>8)&band).sum()),separate_vs_assembled_max_RGB_error_after_repair=int(residual.max()),installed_files_changed=False)
    reports.append(rec);print(json.dumps(rec),flush=True)
    if aid=='0x1000' and seq==0 and slot==2:
        # Face/head raccord crop, with the native split at its centre.
        x0=int((seam_x-18)*zoom);y0=int((seam_y-20)*zoom);w=36*zoom;h=40*zoom
        sheet=Image.new('RGB',(1080,430),(32,32,32));draw=ImageDraw.Draw(sheet)
        for i,(title,im) in enumerate(zip(['Actuel / 4 dessins natifs','Essai raccord / 4 dessins natifs','Essai raccord / filtrage assemble'],out)):
            crop=Image.fromarray(im[y0:y0+h,x0:x0+w]).resize((360,400),Image.Resampling.NEAREST)
            sheet.paste(crop,(i*360,30));draw.text((i*360+5,8),title,fill='white')
        sheet.save(HERE/'seam-closeup.png')
        sheet=Image.new('RGB',(out[0].shape[1]*2,out[0].shape[0]+26),(32,32,32));draw=ImageDraw.Draw(sheet)
        for i,(title,im) in enumerate(zip(['Actuel / 4 dessins natifs','Essai raccord / 4 dessins natifs'],out[:2])):
            sheet.paste(Image.fromarray(im),(i*im.shape[1],26));draw.text((i*im.shape[1]+5,7),title,fill='white')
        sheet.save(HERE/'native-draw-comparison.png')
(HERE/'native-draw-analysis.json').write_text(json.dumps(dict(role='offline prototype not ingame QA',cases=reports),indent=2)+'\n')
