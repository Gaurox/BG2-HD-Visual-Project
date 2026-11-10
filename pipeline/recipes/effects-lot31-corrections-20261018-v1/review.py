"""Native/previous/corrected comparison on one shared clock, all31/99 contexts."""
from prepare import ROOT,OUT,load,save
import html,json,time
import numpy as np
from PIL import Image

def label(a):
    if not a['changed']:return 'Conservé'
    return ' + '.join(s for yes,s in [(a['rebout'],'ReboutCX'),(a['smooth'],'Bézier / contour doux'),(a['retime'],'Chronologie native'),(a['black_neutral'],'Noir transparent')] if yes)

DETAIL='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Comparatif effets corrigés</title>
<style>body{background:#141a23;color:#edf3fc;font:15px system-ui;margin:20px}a{color:#8bc2ff}button,select,input{margin:4px;padding:8px;background:#26384d;color:white;border:1px solid #65788d}header{position:sticky;top:0;background:#141a23;z-index:2;padding-bottom:8px}.row{display:flex;gap:16px;align-items:flex-start;flex-wrap:wrap}figure{margin:0;max-width:31vw;max-height:75vh;overflow:auto}canvas{display:block;height:auto;image-rendering:pixelated;border:1px solid #47556a}figcaption{margin:8px 0}#info{font-variant-numeric:tabular-nums}</style>
<header><a href="index.html">← Les31 effets</a><h1 id="title"></h1><select id="palette"></select><select id="profile"></select><br><button id="play">Pause</button><label>Phase <input id="seek" type="range" min="0" value="0"></label><label><input id="mask" type="checkbox">Alpha texture seul</label><select id="blend"><option value="source-over">Alpha normal</option><option value="lighter">Lumineux/additif</option></select><label>Zoom<select id="zoom"><option value="fit">Ajuster</option><option>1</option><option>2</option><option>4</option><option>8</option></select></label><input id="bg" type="color" value="#6e5e46"><p id="info"></p></header>
<div class="row"><figure><figcaption>Vanilla · palette native · 15fps</figcaption><canvas id="native"></canvas></figure><figure><figcaption>Version précédente</figcaption><canvas id="before"></canvas></figure><figure><figcaption>Correction proposée</figcaption><canvas id="after"></canvas></figure></div>
<p>Les trois vues partagent la même horloge et le même cadrage. Le mode lumineux restitue le mélange des effets dont le noir est neutre. Le mode alpha normal permet aussi d’inspecter le fond transparent de la correction. Les versions en jeu restent inchangées.</p>
<script>
let catalog,asset,data,profile,playing=true,epoch=performance.now(),offset=0,cache=new Map(),generation=0,lastPhase=-1;
const $=id=>document.getElementById(id),names=['native','before','after'];
function pic(path){if(!cache.has(path))cache.set(path,new Promise((ok,bad)=>{let i=new Image();i.onload=()=>ok(i);i.onerror=bad;i.src=path}));return cache.get(path)}
async function paint(time){if(!profile)return;let dur=profile.duration_rational[0]/profile.duration_rational[1],t=((time%dur)+dur)%dur,p=Math.min(profile.phases-1,Math.floor(t*30+1e-7)),n=Math.min(profile.native.length-1,Math.floor(t*15+1e-7));if(p===lastPhase)return;lastPhase=p;let token=++generation;let paths=[profile.native[n],profile.before[p],profile.after[p]],images=await Promise.all(paths.map(pic));if(token!==generation)return;$('seek').value=p;$('info').textContent=p+' / '+(profile.phases-1)+' · '+t.toFixed(3)+' / '+dur.toFixed(3)+' s · '+data.actions;
for(let j=0;j<3;j++){let c=$(names[j]),ctx=c.getContext('2d');ctx.globalCompositeOperation='source-over';ctx.fillStyle=$('bg').value;ctx.fillRect(0,0,c.width,c.height);ctx.imageSmoothingEnabled=false;if($('mask').checked){let off=document.createElement('canvas');off.width=c.width;off.height=c.height;let q=off.getContext('2d');q.drawImage(images[j],0,0);let a=q.getImageData(0,0,c.width,c.height);for(let i=0;i<a.data.length;i+=4){a.data[i]=a.data[i+1]=a.data[i+2]=a.data[i+3];a.data[i+3]=255}q.putImageData(a,0,0);ctx.drawImage(off,0,0)}else{ctx.globalCompositeOperation=$('blend').value;ctx.drawImage(images[j],0,0)}}}
async function choosePalette(){data=await(await fetch($('palette').value)).json();cache.clear();for(let n of names){$(n).width=data.size_x4[0];$(n).height=data.size_x4[1]}$('profile').innerHTML=data.profiles.map((p,i)=>'<option value="'+i+'">'+p.id+'</option>').join('');if(data.ordinal===30||data.ordinal===31)$('profile').value=data.profiles.findIndex(p=>p.loop);$('blend').value=data.black_neutral?'lighter':'source-over';chooseProfile()}
function chooseProfile(){profile=data.profiles[Number($('profile').value)];offset=0;epoch=performance.now();lastPhase=-1;$('seek').max=profile.phases-1;zoom();paint(0)}
function zoom(){if(data)for(let n of names)$(n).style.width=($('zoom').value==='fit'?Math.min(data.size_x4[0],innerWidth*.30):data.size_x4[0]*Number($('zoom').value))+'px'}$('zoom').onchange=zoom;addEventListener('resize',zoom);
$('palette').onchange=choosePalette;$('profile').onchange=chooseProfile;$('play').onclick=()=>{if(playing)offset+=(performance.now()-epoch)/1000;else epoch=performance.now();playing=!playing;$('play').textContent=playing?'Pause':'Lecture'};
$('seek').oninput=()=>{playing=false;$('play').textContent='Lecture';offset=Number($('seek').value)/30;epoch=performance.now();lastPhase=-1;paint(offset)};for(let id of ['mask','blend','bg'])$(id).oninput=()=>{lastPhase=-1;paint(offset+(playing?(performance.now()-epoch)/1000:0))};
function tick(){paint(offset+(playing?(performance.now()-epoch)/1000:0));requestAnimationFrame(tick)}
(async()=>{catalog=await(await fetch('catalog.json')).json();let id=Number(new URLSearchParams(location.search).get('asset')||1);asset=catalog.assets.find(a=>a.ordinal===id);$('title').textContent=String(id).padStart(2,'0')+' · '+asset.resref+' · '+asset.actions;$('palette').innerHTML=asset.contexts.map(c=>'<option value="'+c.data+'">'+c.label+'</option>').join('');await choosePalette();requestAnimationFrame(tick)})();
</script></html>'''

def main():
    plan=load(OUT/'plan.json');jobs=plan['jobs'];records=[]
    for a in jobs:
        p=OUT/'results'/f'{a["job_id"]}.json'
        while not p.exists():
            state=load(OUT/'progress.json') if (OUT/'progress.json').exists() else {}
            if state.get(a['job_id'],{}).get('state')=='failed':raise RuntimeError('Correction failed '+a['job_id'])
            time.sleep(2)
        r=load(p);data=OUT/'review/data'/f'{a["job_id"]}.json'
        save(data,{'resref':a['resref'],'ordinal':a['ordinal'],'job_id':a['job_id'],'actions':label(a),
            'black_neutral':a['black_neutral'],'size_x4':r['size_x4'],'profiles':r['profiles']})
        records.append((a,r,'data/'+data.name))
    assets=[];cards=[]
    for a in plan['assets']:
        group=[(j,r,path) for j,r,path in records if j['resref']==a['resref']]
        primary=next((j,r,path) for j,r,path in group if j['primary']);j,r,_=primary
        # A visible phase avoids blank terminal reserves in12/20.
        best=max(r['frames'],key=lambda f:int(np.fromfile(ROOT/f['premultiplied']['path'],np.uint8).reshape(-1,4)[:,:3].sum(dtype=np.uint64)))
        ctx=[]
        for q,_,path in sorted(group,key=lambda g:g[0]['job_id']):
            owners=', '.join(c['consumer_key'].rsplit(':',1)[-1] for c in q['consumers']) or 'palette BAM'
            ctx.append({'data':path,'label':q['job_id']+' / '+owners})
        assets.append({'ordinal':a['ordinal'],'resref':a['resref'],'actions':label(j),'contexts':ctx})
        title=f'{a["ordinal"]:02d} · {a["resref"]}'
        cards.append(f'<article><h2>{title}</h2><p>{html.escape(label(j))}</p><a href="detail.html?asset={a["ordinal"]}"><div class="pair"><figure><figcaption>Avant</figcaption><img src="{best["before"]}"></figure><figure><figcaption>Correction</figcaption><img src="{best["after"]}"></figure></div></a><p><a href="detail.html?asset={a["ordinal"]}">Comparer en animation · {len(group)} palette(s)</a></p></article>')
    save(OUT/'review/catalog.json',{'assets':assets,'contexts':len(records),'corrected_assets':27,'corrected_contexts':95})
    (OUT/'review/detail.html').write_text(DETAIL,encoding='utf-8')
    page='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Lot31 — corrections ReboutCX, masques et chronologie</title><style>body{margin:22px;background:#111822;color:#edf3fc;font:15px system-ui}a{color:#91c6ff}main{display:grid;grid-template-columns:repeat(auto-fit,minmax(620px,1fr));gap:16px}article{background:#1b2635;padding:15px;border-radius:9px}.pair{display:flex;gap:10px}figure{margin:0;width:48%}img{width:100%;height:200px;object-fit:contain;image-rendering:pixelated;background:#6e5e46}h2{font-size:19px}figcaption{font-size:12px}</style><h1>31 effets · correctifs proposés</h1><p>27effets corrigés /95contextes de palettes.10effets ReboutCX ;24masques reconstruits Bézier et fondus avec protection des traits fins.12/20 : pauses invisibles natives rétablies ;30 : interpolation à positions temporelles natives.12/14/20 : noir transparent, énergie lumineuse préservée.</p><p>Cliquer sur un effet pour comparer vanilla / version précédente / correction, sur une horloge commune.24,25,28,29 conservés. Aperçu de travail ; aucune installation ou validation ingame déduite.</p><main>CARDS</main></html>'''
    (OUT/'review/index.html').write_text(page.replace('CARDS',''.join(cards)),encoding='utf-8')
    print('Review ready:31 assets,99 contexts,27 corrected /95 context corrections',flush=True)

if __name__=='__main__':main()
