"""Restore broad smooth coverage; compare post-mask horizontal translations on map crop."""
from pathlib import Path
import sys,numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3]
old=ROOT/'pipeline/recipes/bdforcew-wed-edge-20261010-v2/compare_edge.py'
scope={'__file__':str(old),'__name__':'placement_preview'}
exec(old.read_text(encoding='utf-8').split('for number,(x,y) in enumerate',1)[0],scope)
v2=scope['v2'];render=scope['render'];r=scope['r'];rgba=scope['rgba'];transfer_for=scope['transfer_for'];distance=scope['distance'];covered=scope['covered'];leaf=scope['leaf']
OUT=ROOT/'animations/batches/bdforcew-shift-right-20261010-v3';OUT.mkdir(parents=True,exist_ok=True)
bg=Image.open(ROOT/'animations/batches/portails-deux-diagnostic-20261010-v1/OH8100-native-local.png').convert('RGB')
assert bg.size==(1080,1320)
bg=np.asarray(bg.resize((1440,1760),Image.Resampling.NEAREST)).astype(np.uint16)
frame=r['frames'][50];occurrences=[(2286,820),(2350,866)]
raw=rgba(leaf,frame);fitted=[];narrow=[]
for number,(x,y) in enumerate(occurrences,1):
    mask=transfer_for(frame,x,y);d=distance(mask);m=covered(mask,d,1,4)
    mask.tofile(OUT/f'instance-{number}-transfer.rgba');m.tofile(OUT/f'instance-{number}-expected-coverage.rgba')
    fitted.append(render(m,raw,True));narrow.append(render(covered(mask,d,1,1),raw,True))
def panel(images,dx):
    result=bg.copy();cx,cy=frame['centre_x1']
    for image,(x,y) in zip(images,occurrences):
        px=(x-cx+dx-2120)*4;py=(y-cy-580)*4;h,w=image.shape[:2]
        assert 0<=px and 0<=py and px+w<=result.shape[1] and py+h<=result.shape[0]
        result[py:py+h,px:px+w]+=image[:,:,:3]
    # Focus on doorway/black edge, retaining both occurrences and left contact.
    return Image.fromarray(np.minimum(result,255).astype(np.uint8)).crop((200,280,1380,1420)).resize((590,570),Image.Resampling.BOX)
font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
choices=[('Actuel WED4 / position vanilla',narrow,0),('Ancien WED16 / +4 x1',fitted,4),('Ancien WED16 / +6 x1',fitted,6),('Ancien WED16 / +8 x1',fitted,8)]
board=Image.new('RGB',(1200,1280),(22,25,31));draw=ImageDraw.Draw(board)
for i,(label,images,dx) in enumerate(choices):
    image=panel(images,dx);xx=(i%2)*600;yy=(i//2)*640
    draw.text((xx+10,yy+12),label,font=font,fill='white');board.paste(image,(xx,yy+52))
board.save(OUT/'placement-comparison.png')
# First-correctif bytes are unchanged; only the final draw X is translated.
delta=6
before=panel(narrow,0);after=panel(fitted,delta)
board=Image.new('RGB',(1200,640),(22,25,31));draw=ImageDraw.Draw(board)
for xx,label,img in [(0,'Actuel : coupe WED4',(before)),(600,'Rendu lisse WED16 + decale a droite',(after))]:
    draw.text((xx+10,12),label,font=font,fill='white');board.paste(img,(xx,52))
board.save(OUT/'selected-placement.png')
v2.write_json(OUT/'plan.json',dict(schema='bg2-bdforcew-non-vanilla-placement-v1',requested_treatment='first corrective smooth version',area='OH8100',resref='BDFORCEW',occurrences=[list(p) for p in occurrences],post_mask_dx_x1=delta,post_mask_dy_x1=0,wed_feather_x4=16,native_frame_centres_unchanged=True,area_coordinates_unchanged=True,asset_bytes_unchanged=True,non_vanilla_visual_placement=True,scope='both BDFORCEW draws at exact OH8100 positions, only with successful replacement/mask',ingame_QA=False,preview_background='native area crop; actual GLSL coverage; simulation'))
scope['scope']['make'](None,None)
print('Placement preview +6 x1 ready',flush=True)
