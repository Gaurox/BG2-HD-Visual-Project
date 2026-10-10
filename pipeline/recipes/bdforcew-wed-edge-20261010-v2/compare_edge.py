"""Actual GLSL comparison: installed broad fade versus narrow inward AA, both occurrences."""
from pathlib import Path
import sys, numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import run_animation_upscale_30fps_v2 as v2
OLD=ROOT/'animations/batches/portails-deux-correctif-20261010-v1'
OUT=ROOT/'animations/batches/bdforcew-wed-edge-20261010-v2';OUT.mkdir(parents=True,exist_ok=True)
# Reuse the verified shader/context harness, stopping before its old test body.
harness=ROOT/'pipeline/recipes/portails-deux-correctif-20261010-v1/test_gl_mask.py'
scope={'__file__':str(harness),'__name__':'edge_comparison'}
exec(harness.read_text(encoding='utf-8').split('# Exercise the unchanged path:',1)[0],scope)
render=scope['render']
leaf=ROOT/'animations/packs-par-zone/portails-deux-correctif-20261010-v1-complete/OH8100'
r=next(q for q in v2.validate_v2_pack(leaf)[1] if q['resref']=='BDFORCEW')
base=ROOT/'animations/packs-par-zone/portails-cinq-selection-20261010-v1-complete/OH8100'
oldr=next(q for q in v2.validate_v2_pack(base)[1] if q['resref']=='BDFORCEW')
def rgba(pack,frame):
    w,h=frame['physical_size_x4'];return np.frombuffer((pack/frame['asset']).read_bytes(),np.uint8).reshape(h,w,4).copy()
def transfer_for(frame,x,y):
    w,h=frame['logical_size_x1'];cx,cy=frame['centre_x1'];yy,xx=np.indices((h,w))
    inside=y-cy+yy+.5>1011-(303/431)*(x-cx+xx+.5-2129)
    mask=np.zeros((h,w,4),np.uint8);mask[:,:,0]=np.where(inside,0,255);mask[:,:,3]=255
    return mask
def distance(mask):
    h,w=mask.shape[:2];d=np.where((mask[:,:,0]==0)|(mask[:,:,2]!=0),0.,5.).astype(np.float32)
    for y in range(h):
        for x in range(w):
            for dx,dy,cost in [(-1,0,1),(0,-1,1),(-1,-1,2**.5),(1,-1,2**.5)]:
                if 0<=x+dx<w and 0<=y+dy<h:d[y,x]=min(d[y,x],d[y+dy,x+dx]+cost)
    for y in range(h-1,-1,-1):
        for x in range(w-1,-1,-1):
            for dx,dy,cost in [(1,0,1),(0,1,1),(-1,1,2**.5),(1,1,2**.5)]:
                if 0<=x+dx<w and 0<=y+dy<h:d[y,x]=min(d[y,x],d[y+dy,x+dx]+cost)
    return d
def covered(mask,d,guard,band):
    t=np.clip((d-guard)/band,0,1);result=mask.copy();result[:,:,3]=np.floor(255*t*t*(3-2*t)+.5).astype(np.uint8);return result
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20);reports=[]
for number,(x,y) in enumerate([(2286,820),(2350,866)],1):
    frame=r['frames'][50];a=rgba(leaf,frame);before=rgba(base,oldr['frames'][50]);mask=transfer_for(frame,x,y);d=distance(mask)
    oldmask=covered(mask,d,1,4);newmask=covered(mask,d,1,1)
    unfeathered=render(mask,a);old=render(oldmask,a,True);new=render(newmask,a,True)
    assert np.all(new>=old) and np.all(new<=unfeathered)
    outside=(mask[:,:,0]==0).repeat(4,0).repeat(4,1);assert not new[outside].any()
    images=[render(mask,before),old,new];w,h=a.shape[1],a.shape[0]
    board=Image.new('RGB',(w*3+24,h+74),(24,27,33));draw=ImageDraw.Draw(board)
    draw.text((12,8),f'BDFORCEW — instance {number} — centres identiques',font=font,fill='white')
    for i,(label,img) in enumerate(zip(['Avant correctif','Installe : fade WED16 + garde4','Propose : WED4 + garde4'],images)):
        xx=i*(w+12);draw.text((xx+12,42),label,font=font,fill='white');board.paste(Image.fromarray(np.minimum(img[:,:,:3].astype(np.uint16)+np.array([24,27,33]),255).astype(np.uint8)),(xx,74))
    board.save(OUT/f'BDFORCEW-instance-{number}-coverage-comparison.png')
    mask.tofile(OUT/f'instance-{number}-transfer.rgba');newmask.tofile(OUT/f'instance-{number}-expected-coverage.rgba')
    energy=unfeathered[:,:,:3].astype(float).sum();weights=np.array([.2126,.7152,.0722]);luma=unfeathered[:,:,:3]@weights;core=luma>=np.percentile(luma[luma>0],95)
    reports.append(dict(occurrence=number,position=[x,y],geometry_and_centres_identical=True,old_visibility_loss_pct=100*(1-old[:,:,:3].sum()/energy),new_visibility_loss_pct=100*(1-new[:,:,:3].sum()/energy),old_bright_core_loss_pct=100*(1-(old[:,:,:3]@weights)[core].sum()/luma[core].sum()),new_bright_core_loss_pct=100*(1-(new[:,:,:3]@weights)[core].sum()/luma[core].sum()),no_native_occluded_pixels_revealed=True,frame=50,logical_size=frame['logical_size_x1']))
v2.write_json(OUT/'edge-diagnosis.json',dict(cause='installed WED coverage deliberately erodes one x1 cell then fades over four x1 pixels; too much interior loss near bright endpoint',old=dict(guard_x4=4,fade_x4=16),proposed=dict(guard_x4=4,fade_x4=4),occurrences=reports,gpu=scope['gpu'],installed_files_modified=False,simulation_only=True,OHHPORT='accepted by user; bytes unchanged'))
scope['make'](None,None);scope['api'](scope['O'],'wglDeleteContext',scope['w'].BOOL,scope['c'].c_void_p)(scope['context']);scope['api'](scope['U'],'ReleaseDC',scope['ii'],scope['w'].HWND,scope['w'].HDC)(scope['hwnd'],scope['dc']);scope['api'](scope['U'],'DestroyWindow',scope['w'].BOOL,scope['w'].HWND)(scope['hwnd'])
print(reports,flush=True)
