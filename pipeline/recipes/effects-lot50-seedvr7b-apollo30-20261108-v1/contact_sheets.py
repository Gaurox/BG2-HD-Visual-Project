"""Native and produced anchor samples for visual inspection; no acceptance implied."""
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from temporal import BATCH,load

def main():
    review=BATCH/'review';font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',14)
    cards=[]
    current={a['resref']:a for a in load(review/'current-cards.json')['assets']} if (review/'current-cards.json').exists() else {}
    for a in load(BATCH/'batch.json')['assets']:
        path=review/'data'/(a['resref']+'.json')
        if not path.exists():continue
        r=current.get(a['resref'],load(path));p=r['profiles'][0];scores=[]
        for phase in range(0,len(p['frames']),2):
            f=r['frames'][p['frames'][phase]];arr=np.array(Image.open(review/f['image']))
            scores.append((int((arr[:,:,:3].astype(np.int64)*arr[:,:,3:4]).sum()),phase))
        phase=max(scores)[1];f=r['frames'][p['frames'][phase]];n=r['native'];idx=p['native'][phase//2]
        atlas=Image.open(review/n['image']);w,h=n['width'],n['height'];x,y=(idx%n['cols'])*w,(idx//n['cols'])*h
        native=atlas.crop((x,y,x+w,y+h)).resize((r['width'],r['height']),Image.Resampling.NEAREST)
        produced=Image.new('RGBA',(r['width'],r['height']));produced.paste(Image.open(review/f['image']),(f['x'],f['y']))
        tile=Image.new('RGB',(400,225),(38,45,57));d=ImageDraw.Draw(tile)
        d.text((8,5),f"{a['ordinal']:02} {a['resref']} {r.get('method','SeedVR')} p{phase}",font=font,fill='white')
        for col,im in enumerate([native,produced]):
            im=im.copy();im.thumbnail((185,172),Image.Resampling.NEAREST)
            tile.paste(im,(col*200+(200-im.width)//2,45+(172-im.height)//2),im)
            d.text((col*200+8,25),'Natif' if col==0 else 'Traite alpha natif',font=font,fill='#b8c9df')
        cards.append(tile)
    for page in range((len(cards)+19)//20):
        sheet=Image.new('RGB',(1600,1160),(15,20,28));d=ImageDraw.Draw(sheet)
        d.text((12,10),f'Lot50 : ancres natives / traitees - {page+1}/3 - inspection agent, QA utilisateur en attente',font=font,fill='white')
        for i,im in enumerate(cards[page*20:(page+1)*20]):sheet.paste(im,((i%4)*400,35+(i//4)*225))
        sheet.save(BATCH/f'contact-{page+1}.png')
    print('Contact sheets:',len(cards),'assets')

if __name__=='__main__':main()
