"""Before/after final packed resources, replay unchanged separate native draws."""
from common import *
import ast
from PIL import Image,ImageDraw
import run_creature_sprite_x2 as registry,palette_partner_registry as leaves
ns=dict(np=np);tree=ast.parse((HERE.parent/'q3m-monster-quadrant-seam-analysis-20261004-v1/analyze.py').read_text())
exec(compile(ast.Module(body=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('sample','weights','background')],type_ignores=[]),'sampling','exec'),ns)
sample=ns['sample'];background=ns['background'];gen=load(HERE/'current-generation.json')
roots=[ROOT/GEN['generation_dir']/'iee-assets/creature-sprites',ROOT/gen['generation_dir']/'iee-assets/creature-sprites']
cats=[registry.read_sealed_catalog_index(p/'CreatureSprites-XN.catalog',g['catalog']['sha256']) for p,g in zip(roots,(GEN,gen))]
routes=[{(r['animation_id'],r['resref']):r for r in cat['directory']} for cat in cats]
resources,works,summary,contexts,bindings=plan();src={(r['witness']['animation_id'],r['resref']):r for r in resources}
sheet=Image.new('RGB',(1040,7*360),(50,50,50));draw=ImageDraw.Draw(sheet)
for n,witness in enumerate(load(HERE/'selection.json')['witnesses']):
    aid=witness['animation_id'];refs=next(g for g in witness['multipart_groups'] if g[0].endswith('G21'));rs=[src[(aid,ref)] for ref in refs];seq=0;slot=2
    rows=[r['frames'][r['cycles'][seq][slot]] for r in rs];g=[row['geometry'] for row in rows];positive=[a for a in g if a[0]*a[1]]
    L=min(-a[2] for a in positive);T=min(-a[3] for a in positive);R=max(a[0]-a[2] for a in positive);B=max(a[1]-a[3] for a in positive);W=R-L;H=B-T;zoom=5
    yy,xx=np.mgrid[:H*zoom,:W*zoom];wx=(xx+.5)/zoom;wy=(yy+.5)/zoom;out=[]
    for root,cat,route in zip(roots,cats,routes):
        canvas=np.zeros((H*zoom,W*zoom,4));canvas[:,:,:3]=.26;canvas[:,:,3]=1
        for ref,r,row,a in zip(refs,rs,rows,g):
            shard=cat['shards'][route[(aid,ref)]['shard_index']];f=leaves.inspect(root/Path(shard['registry']).name,include_frames=True)['resources'][0]['frames'][row['frame_index']]
            if not f['I'].size:continue
            pal=np.column_stack((r['profile'].fitting[0],np.full(256,255,np.uint8)));pal[0]=0;pal[1,3]=127;im=r['profile'].decode(f['I'],f['F'],pal)
            x=-a[2]-L;y=-a[3]-T;mask=(wx>=x)&(wx<x+a[0])&(wy>=y)&(wy<y+a[1]);s=sample(im,(wx-x)*2-.5,(wy-y)*2-.5)
            canvas[mask,:3]=s[mask,:3]*s[mask,3:4]+canvas[mask,:3]*(1-s[mask,3:4])
        out.append(background(canvas))
    draw.text((10,n*360+4),aid+' '+witness['name'],fill='white')
    for k,im in enumerate(out):
        image=Image.fromarray(im);image.thumbnail((500,305),Image.Resampling.LANCZOS);draw.text((k*520+10,n*360+24),'Avant' if k==0 else 'Raccords corriges / memes dessins natifs',fill='white');sheet.paste(image,(k*520+10,n*360+44))
    if aid=='0x1000':
        x0=int((-L-18)*zoom);y0=int((-40-T-20)*zoom);close=Image.new('RGB',(720,430),(32,32,32));dd=ImageDraw.Draw(close)
        for k,im in enumerate(out):close.paste(Image.fromarray(im[y0:y0+200,x0:x0+180]).resize((360,400),Image.Resampling.NEAREST),(k*360,30));dd.text((k*360+5,8),'Avant' if k==0 else 'Correction finale empaquetee',fill='white')
        close.save(HERE/'seam-closeup.png')
sheet.save(HERE/'comparison.png');print('Final packed before/after: all seven palettes, unchanged native per-part filter.')
