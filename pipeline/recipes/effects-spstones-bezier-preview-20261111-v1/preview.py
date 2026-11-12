"""SPSTONES standalone comparison; never writes production or installed files."""
from pathlib import Path
import base64
import hashlib
import io
import json
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
sys.path.append(str(ROOT / '.tools/potracer'))
from build_spatial_spline_alpha import potrace_alpha
from workspace_paths import get_path

ASSET = ROOT / 'effects/ressources/SPSTONES'
SPATIAL = ASSET / 'runs/spstones-seedvr7b-x4-20261017-v1'
STAGE = ASSET / 'runs/spstones-apollo30-retimed-strict-20261017-v2/02-interpolation'
OUT = ROOT / 'effects/batches/spstones-bezier-preview-20261111-v1'
PAD = 16  # x4 pixels, preview only; anchors remain common to all versions.
load = lambda p: json.loads(p.read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    assert not OUT.exists(), 'Use a new version; preserve existing previews'
    manifest = load(STAGE / 'manifest.json')
    spatial = load(SPATIAL / '01-spatial-x4/manifest.json')
    width, height = [v * 4 for v in spatial['aligned_canvas_size_x1']]
    game = get_path('bg2ee_game_root', required=True)
    watched = [ASSET / 'source.bam', STAGE / 'manifest.json',
               game / 'iee-assets/effects/manifest.json', game / 'override/SPSTONES.bam']
    before = {str(p): sha(p) for p in watched if p.is_file()}
    ids = sorted({i for f in manifest['frames'] for i in f['temporal_source_frames']})
    native, curves, soft = {}, {}, {}
    component_checks = []
    for i in ids:
        f = spatial['frames'][i]
        alpha = np.array(Image.open(SPATIAL / '00-frames-x1/alpha' / f['source_alpha']).convert('L'))
        canvas = alpha.repeat(4, 0).repeat(4, 1)
        assert canvas.shape == (height, width)
        a = np.pad(canvas, PAD)
        curve, _ = potrace_alpha(a, threshold=0, alphamax=1.334,
                                opttolerance=.1, supersample=8, band=10000)
        # Same thickness-aware recipe as lot31, capped at sigma1 x4 for a light edge.
        d = ndi.distance_transform_edt(a > 0)
        ridge = (d > 0) & (d >= ndi.maximum_filter(d, size=3))
        nearest = ndi.distance_transform_edt(~ridge, return_distances=False, return_indices=True)
        sigma = np.clip(d[tuple(nearest)] / 4, .5, 1.)
        t = (sigma - .5) / .5
        blur = (ndi.gaussian_filter(curve.astype(float), .5, mode='constant') * (1-t)
                + ndi.gaussian_filter(curve.astype(float), 1., mode='constant') * t)
        edge = ndi.distance_transform_edt(curve > 0)
        u = np.clip((edge - 2*sigma)/(2*sigma), 0, 1)
        weight = 1 - u*u*(3-2*u)
        softened = np.rint(curve*(1-weight)+blur*weight).clip(0,255).astype(np.uint8)
        labels, count = ndi.label(a > 0, np.ones((3,3)))
        for variant in (curve, softened):
            mass = np.bincount(labels.ravel(), weights=variant.ravel(), minlength=count+1)
            assert np.all(mass[1:] > 0), (i, 'component lost')
        native[i], curves[i], soft[i] = a, curve, softened
        component_checks.append({'native_frame': i, 'components': count, 'lost': 0})
    OUT.mkdir(parents=True)
    labels = ['Actuelle', 'Bezier seul', 'Bezier + fondu leger']
    urls, animations, posters, reports = [], [], [], []
    for f in manifest['frames']:
        n = f['frame']
        w, h = f['physical_size_x4']
        raw = np.frombuffer((STAGE/f['straight_raw_rgba_x4']).read_bytes(), np.uint8).reshape(h,w,4)
        source = np.zeros((height+2*PAD, width+2*PAD, 4), np.uint8)
        x, y, _, _ = f['runtime_crop_box_x4']
        source[y+PAD:y+PAD+h, x+PAD:x+PAD+w] = raw
        left, right = f['temporal_source_frames']; t = f['temporal_fraction']
        def mix(masks):
            return np.rint(masks[left].astype(float)*(1-t)+masks[right].astype(float)*t).astype(np.uint8)
        assert np.array_equal(mix(native), source[:,:,3]), (n, 'source alpha differs')
        fg = source[:,:,3] > 0
        near = ndi.distance_transform_edt(~fg, return_distances=False, return_indices=True)
        variants = [source]
        for masks in (curves, soft):
            v = source.copy(); v[:,:,3] = mix(masks)
            added = (v[:,:,3] > 0) & ~fg
            v[:,:,:3][added] = source[near[0][added],near[1][added],:3]
            visible = fg & (v[:,:,3] > 0)
            assert np.array_equal(v[:,:,:3][visible], source[:,:,:3][visible])
            v[v[:,:,3] == 0] = 0
            assert not v[[0,-1],:,:].any() and not v[:,[0,-1],:].any()
            variants.append(v)
        row_urls = []
        sheet = Image.new('RGB', ((width+2*PAD)*3, height+2*PAD+32), (92,82,66))
        draw = ImageDraw.Draw(sheet)
        for j, v in enumerate(variants):
            im = Image.fromarray(v)
            bio = io.BytesIO(); im.save(bio, format='PNG')
            row_urls.append('data:image/png;base64,'+base64.b64encode(bio.getvalue()).decode())
            bg = Image.new('RGBA', im.size, (92,82,66,255))
            sheet.paste(Image.alpha_composite(bg, im).convert('RGB'), (j*im.width,32))
            draw.text((j*im.width+12,10),labels[j],fill='white')
        urls.append(row_urls); animations.append(sheet)
        if n in (6,24,42,60): posters.append(sheet)
        reports.append({'phase':n,'native_alpha_reconstructed_exactly':True,'existing_visible_rgb_preserved':True})
    animations[0].save(OUT/'comparison.webp',save_all=True,append_images=animations[1:],
                       duration=[round((i+1)*1000/30)-round(i*1000/30) for i in range(len(animations))],loop=0,quality=90,method=4)
    contact = Image.new('RGB',(posters[0].width,posters[0].height*len(posters)))
    for i, im in enumerate(posters): contact.paste(im,(0,i*im.height))
    contact.save(OUT/'contact-sheet.jpg',quality=93)
    html = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>SPSTONES — comparatif</title>
<style>body{background:#171b22;color:#eee;font:16px system-ui;margin:24px}button,input,select{margin:8px}main{display:flex;gap:12px}figure{margin:0;flex:1;min-width:0}canvas{width:100%;height:auto;image-rendering:pixelated}figcaption{padding:10px}#stage{overflow:auto}p{color:#bac4d1}</style>
<h1>SPSTONES — contours</h1><p>70 phases · 30 FPS · 2,333 s · aperçu autonome</p>
<button id="play">Pause</button><input id="seek" type="range" min="0" max="69" value="0"><span id="phase"></span>
<label>Fond <input id="bg" type="color" value="#5c5242"></label><label><input id="alpha" type="checkbox">Alpha seul</label>
<label>Zoom <select id="zoom"><option value="1">100 %</option><option value="2">200 %</option><option value="3">300 %</option></select></label>
<div id="stage"><main>'''
    for label in labels: html += '<figure><figcaption>'+label+'</figcaption><canvas></canvas></figure>'
    html += '''</main></div><p>Bézier : Potrace 1.334 / tolérance 0.1 / SS8. Fondu : sigma 0.5–1 pixel x4, adapté à l’épaisseur. Texture et chronologie conservées.</p><script>
const urls=DATA, canv=[...document.querySelectorAll('canvas')], imgs=[];
const seek=document.querySelector('#seek'), phase=document.querySelector('#phase'), bg=document.querySelector('#bg'), alpha=document.querySelector('#alpha');
let playing=true, current=0, epoch=performance.now();
Promise.all(urls.map(row=>Promise.all(row.map(src=>new Promise(resolve=>{let im=new Image();im.onload=()=>resolve(im);im.src=src}))))).then(all=>{imgs.push(...all);requestAnimationFrame(tick)});
function draw(){phase.textContent=`Phase ${current+1}/70`;seek.value=current;canv.forEach((c,j)=>{let im=imgs[current][j];c.width=im.width;c.height=im.height;let ctx=c.getContext('2d');ctx.drawImage(im,0,0);if(alpha.checked){let d=ctx.getImageData(0,0,c.width,c.height);for(let k=0;k<d.data.length;k+=4){d.data[k]=d.data[k+1]=d.data[k+2]=d.data[k+3];d.data[k+3]=255}ctx.putImageData(d,0,0)}else{ctx.globalCompositeOperation='destination-over';ctx.fillStyle=bg.value;ctx.fillRect(0,0,c.width,c.height)}})}
function tick(t){if(playing)current=Math.floor((t-epoch)*30/1000)%70;draw();requestAnimationFrame(tick)}
document.querySelector('#play').onclick=e=>{playing=!playing;epoch=performance.now()-current*1000/30;e.target.textContent=playing?'Pause':'Lecture'};
seek.oninput=()=>{current=+seek.value;epoch=performance.now()-current*1000/30};
document.querySelector('#zoom').onchange=e=>{document.querySelector('main').style.minWidth=(3*WIDTH*+e.target.value)+'px'};
</script></html>'''.replace('DATA',json.dumps(urls)).replace('WIDTH',str(width+2*PAD))
    (OUT/'index.html').write_text(html,encoding='utf-8')
    assert all(sha(Path(p)) == digest for p,digest in before.items()), 'protected input changed'
    result={'asset':'SPSTONES','frames':70,'fps':30,'duration_seconds':70/30,
            'installed':False,'source_hashes_unchanged':before,'native_component_checks':component_checks,
            'checks':reports,'curve':{'alphamax':1.334,'opttolerance':.1,'supersample':8,'nearest_clamp':False},
            'soft_edge':{'sigma_x4':[.5,1.],'thickness_adaptive':True},'preview_padding_x4':PAD}
    (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'output':str(OUT),'frames':70,'components_lost':0,'protected_inputs_unchanged':True}))

if __name__ == '__main__': main()
