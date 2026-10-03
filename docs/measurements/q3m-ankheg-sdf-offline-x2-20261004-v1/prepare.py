"""Load sealed original and installed alpha planes; choose complete body poses."""
import json,struct,sys,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
import palette_partner_registry as leaves
from palette_work_plan import file_sha

def load(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sources():
    original_run=ROOT/'docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1'
    alpha_run=ROOT/'docs/measurements/q3m-ankheg-alpha-light-x2-20261004-v1'
    original=load(original_run/'production.json');alpha=load(alpha_run/'production.json')
    directory=ROOT/original['pack_directory'];palettes={};oracle=(directory/'witnesses.oracle').read_bytes();pos=12
    for _ in range(struct.unpack_from('<I',oracle,8)[0]):
        aid,owner,ref,nf,nc=struct.unpack_from('<II8sII',oracle,pos);pos+=24
        palettes[ref.split(b'\0')[0].decode()]=np.frombuffer(oracle,np.uint8,6*256*4,pos).reshape(6,256,4).copy();pos+=6*256*4+2052
        for __ in range(nc):count=struct.unpack_from('<I',oracle,pos)[0];pos+=4+count*4
        pos+=nf*(16+6*32)
    assert pos==len(oracle)
    resources={}
    alpha_dir=ROOT/'sprite/.work/q3m-ankheg-alpha-light-x2-20261004-v1/isolated'
    for info in original['pack']['leaves']:
        name='CreatureSprites-XN-'+info['sha256']+'.registry';path=directory/name
        assert file_sha(path).upper()==info['sha256']
        r=leaves.inspect(path,include_frames=True)['resources'][0];ref=r['resref']
        if ref not in ('MAKHG1','MAKHG1E','MAKHG3'):continue
        current=next(x for x in alpha['details'] if x['resref']==ref)
        new_path=alpha_dir/('CreatureSprites-XN-'+current['V8_sha256']+'.registry')
        assert file_sha(new_path).upper()==current['V8_sha256']
        a=leaves.inspect(new_path,include_frames=True)['resources'][0]
        resources[ref]=dict(original=r,current=a,palettes=palettes[ref],sha256=info['sha256'])
    return resources

if __name__=='__main__':
    resources=sources();work=ROOT/'sprite/.work/q3m-ankheg-sdf-offline-x2-20261004-v1';work.mkdir(exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',17)
    canvas=Image.new('RGB',(1600,960),(235,235,231));draw=ImageDraw.Draw(canvas)
    for rindex,(ref,bundle) in enumerate(resources.items()):
        r=bundle['original'];p=bundle['palettes'][0]
        for col,ordinal in enumerate((0,11,20,25,40,50,65,75)):
            if ordinal>=len(r['frames']):continue
            f=r['frames'][ordinal];raw=r['profile'].decode(f['I'],f['F'],p)
            im=Image.fromarray(raw,'RGBA');im.thumbnail((190,270),Image.Resampling.NEAREST)
            bg=Image.new('RGBA',(200,275),(112,115,112,255));bg.alpha_composite(im,((200-im.width)//2,(275-im.height)//2))
            x=col*200;y=rindex*320;canvas.paste(bg.convert('RGB'),(x,y+35));draw.text((x+6,y+6),ref+'/'+str(ordinal),font=font,fill=(35,38,43))
    canvas.save(work/'contact.png')
    print(work/'contact.png')
