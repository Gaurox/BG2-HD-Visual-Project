"""Lossless animated review sheet; production RGBA is never changed."""
from produce import ROOT,BATCH,ORIGINAL,load
from PIL import Image
import numpy as np


def main():
    out=BATCH/'review';out.mkdir(exist_ok=True);cards=[]
    for a in load(ORIGINAL)['assets']:
        ref=a['resref'];r=load(BATCH/'checks'/(ref+'.json'))
        base=ROOT/'effects/ressources'/ref/'runs'/r['interpolation_run']/'02-interpolation'
        m=load(base/'manifest.json');s=load(ROOT/m['parent']['spatial_manifest']);cw,ch=s['aligned_canvas_size_x1']
        anchor=[s['frames'][0]['canvas_offset_x1'][i]+s['frames'][0]['centre_x1'][i] for i in range(2)]
        target=(max(1,round(cw*min(1,208/cw,208/ch))),max(1,round(ch*min(1,208/cw,208/ch))))
        frames=[]
        for f in m['frames']:
            p=np.frombuffer((base/f['raw_rgba_x4']).read_bytes(),np.uint8).reshape(f['physical_size_x4'][1],f['physical_size_x4'][0],4)
            image=Image.new('RGB',(cw*4,ch*4),(0,0,0))
            image.paste(Image.fromarray(p[:,:,:3]),tuple((anchor[i]-f['centre_x1'][i])*4 for i in range(2)))
            frames.append(image.resize(target,Image.Resampling.LANCZOS))
        duration=[round((i+1)*1000/30)-round(i*1000/30) for i in range(len(frames))]
        frames[0].save(out/f'{ref}.webp',save_all=True,append_images=frames[1:],duration=duration,loop=0,lossless=True,method=3)
        cards.append(f'<article><h2>{ref}</h2><div><img src="{ref}.webp"></div><p>{len(frames)} phases distinctes · {len(frames)/30:.3f} s</p></article>')
        print(ref,'preview ready',flush=True)
    html='''<!doctype html><meta charset="utf-8"><title>33 effets — 7B x4 nearest / 30 FPS corrigés</title>
<style>body{background:#111;color:#eee;font:15px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}article{background:#1c1c1c;border:1px solid #333;padding:12px}h1{font-size:24px}h2{font-size:16px;margin:0 0 8px}article div{background:#000;display:flex;align-items:center;justify-content:center;height:220px}p{color:#bbb;font-size:13px}img{max-width:100%;max-height:208px}</style>
<h1>33 effets corrigés — SeedVR 7B x4 / nearest / 30 FPS</h1><p>Prévisualisations animées sans compression destructive, sur fond noir. Les vignettes sont ajustées à leur case ; en jeu, taille et ancrage natifs conservés. Doublons retirés avant Apollo, durée globale conservée.</p><main>'''+''.join(cards)+'</main>'
    (out/'index.html').write_text(html,encoding='utf-8')


if __name__=='__main__':main()
