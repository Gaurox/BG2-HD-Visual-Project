"""SPDEATH3 only: unchanged RGB/timing, validated Ankheg SDF mask preview."""
from pathlib import Path
import importlib.util
import json
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'pipeline/scripts'))
import effect_workflow as workflow
from workspace_paths import get_path

RECIPE = ROOT / 'pipeline/recipes/effects-lot8-sdf-ankheg-preview-20261017-v1/preview.py'
spec = importlib.util.spec_from_file_location('effects_validated_sdf', RECIPE)
sdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sdf)
OUT = ROOT / 'effects/batches/spdeath3-sdf-ankheg-preview-20261018-v1'
REVIEW = OUT / 'review'
STAGE = ROOT / 'effects/ressources/SPDEATH3/runs/spdeath3-apollo30-native-retimed-20261017-v1/02-interpolation'
QA = ROOT / 'sprite/index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json'
load, save, digest, evidence = sdf.load, sdf.save, sdf.digest, sdf.evidence


def gallery(data):
    page = '''<!doctype html><html lang="fr"><meta charset="utf-8"><title>SPDEATH3 — masque SDF Ankheg</title>
<style>body{margin:22px;background:#111821;color:#e9eef5;font:15px system-ui}h1{font-size:24px}p{max-width:950px;line-height:1.5}button,select,input{padding:7px;background:#29374b;color:#fff;border:1px solid #71849c}button{cursor:pointer}.row{display:flex;gap:22px;flex-wrap:wrap}figure{margin:15px 0}figcaption{margin-bottom:10px}canvas{display:block;image-rendering:pixelated;background-color:var(--bg,#6e5e46);background-image:var(--pattern,none);background-size:24px 24px}#detail{margin-top:20px;max-width:100%}.tools{position:sticky;top:0;background:#111821ed;padding:10px 0;z-index:1}#phase{width:300px}a{color:#a7ceff}.note{color:#aebed1}</style>
<h1>33 · SPDEATH3 — lissage du masque SDF Ankheg</h1>
<p>Avant / après synchronisés, RGB existants réutilisés. SDF borné : sigma4, correction du champ ±2 pixels x4, couverture8×8, sans retrait systématique. Durée et30FPS conservés. Aperçu uniquement ; version ingame inchangée.</p>
<div class="tools"><button id="play">Lecture</button> <select id="profile"></select> <label>Phase <input id="phase" type="range" min="0" value="0"><span id="counter"></span></label><br>
<label>Fond <select id="bg"><option value="brown">Terrain brun</option><option value="check">Damier</option><option value="black">Noir</option><option value="light">Clair</option></select></label> <label><input id="alpha" type="checkbox"> Masques seuls</label> <span id="status">Chargement…</span></div>
<div class="row"><figure><figcaption>Masque installé actuel</figcaption><canvas id="before"></canvas></figure><figure><figcaption>SDF Ankheg proposé</figcaption><canvas id="after"></canvas></figure></div>
<p class="note">Les deux vues sont à taille réelle x4. Clique sur une vue pour déplacer le gros plan du contour. La marge transparente de4pixels sert à montrer les bords reconstruits sans les couper ; mêmes coordonnées et marge sur les deux vues.</p>
<canvas id="detail" width="800" height="450"></canvas>
<script>
const D=DATA, pics=new Map();let current=0,playing=false,ready=false,epoch=0,profile=D.profiles[0],focus=D.detail_focus;
const $=id=>document.getElementById(id), names=['before','after'];
for(const p of D.profiles){const o=document.createElement('option');o.value=p.id;o.textContent=p.id+' · '+p.frames.length+' phases · '+p.duration.toFixed(3)+' s';$('profile').append(o)}
async function get(mode,n){const key=mode+n;if(!pics.has(key)){const i=new Image();i.src='frames/'+mode+'_'+String(n).padStart(3,'0')+'.png';pics.set(key,i.decode().then(()=>i))}return pics.get(key)}
function drawable(im){if(!$('alpha').checked)return im;const c=document.createElement('canvas');c.width=im.width;c.height=im.height;const x=c.getContext('2d');x.drawImage(im,0,0);const a=x.getImageData(0,0,c.width,c.height);for(let k=0;k<a.data.length;k+=4){a.data[k]=a.data[k+1]=a.data[k+2]=a.data[k+3];a.data[k+3]=255}x.putImageData(a,0,0);return c}
async function draw(){if(!ready)return;const n=profile.frames[current];const ims=await Promise.all(names.map(k=>get(k,n)));const detail=$('detail'),q=detail.getContext('2d');q.clearRect(0,0,800,450);q.imageSmoothingEnabled=false;
for(let j=0;j<2;j++){const c=$(names[j]),x=c.getContext('2d'),im=drawable(ims[j]);c.width=D.size[0];c.height=D.size[1];x.drawImage(im,0,0);q.fillStyle='#e9eef5';q.font='16px system-ui';q.fillText(j?'SDF Ankheg':'Actuel',j*400+8,23);q.drawImage(im,focus[0]-24,focus[1]-24,48,48,j*400+8,35,384,384)}
$('phase').value=current;$('counter').textContent=(current+1)+' / '+profile.frames.length}
async function choose(){playing=false;ready=false;$('play').textContent='Lecture';$('status').textContent='Chargement…';profile=D.profiles.find(p=>p.id===$('profile').value);current=0;$('phase').max=profile.frames.length-1;await Promise.all(profile.frames.flatMap(n=>names.map(k=>get(k,n))));ready=true;$('status').textContent='Prêt · vues synchronisées';draw()}
function tick(now){if(playing&&ready){let t=((now-epoch)/1000)%profile.duration,k=0;while(k<profile.durations.length-1&&t>=profile.durations[k]){t-=profile.durations[k];k++}if(k!==current){current=k;draw()}}requestAnimationFrame(tick)}
$('play').onclick=()=>{if(!ready)return;playing=!playing;epoch=performance.now()-profile.durations.slice(0,current).reduce((a,b)=>a+b,0)*1000;$('play').textContent=playing?'Pause':'Lecture'};
$('profile').onchange=choose;$('phase').oninput=()=>{playing=false;$('play').textContent='Lecture';current=+$('phase').value;draw()};$('alpha').onchange=draw;
$('bg').onchange=()=>{const v=$('bg').value;document.body.style.setProperty('--bg',({brown:'#6e5e46',black:'#000',light:'#ddd',check:'#ddd'})[v]);document.body.style.setProperty('--pattern',v==='check'?'conic-gradient(#777 25%,transparent 0 50%,#777 0 75%,transparent 0)':'none')};
for(const k of names)$(k).onclick=e=>{const r=e.currentTarget.getBoundingClientRect();focus=[(e.clientX-r.left)*D.size[0]/r.width,(e.clientY-r.top)*D.size[1]/r.height];draw()};
choose();requestAnimationFrame(tick);
</script></html>'''
    (REVIEW / 'index.html').write_text(page.replace('DATA', json.dumps(data, ensure_ascii=False)), encoding='utf-8')


def main():
    assert not OUT.exists(), 'Preserve previous completed/partial preview; use a new version'
    (REVIEW / 'frames').mkdir(parents=True)
    game_manifest = get_path('bg2ee_game_root', required=True) / 'iee-assets/effects/manifest.json'
    installed_sha = workflow.sha256_file(game_manifest)
    manifest_evidence = evidence(STAGE / 'manifest.json')
    m = load(STAGE / 'manifest.json')
    spatial = load(ROOT / m['parent']['spatial_manifest'])
    cw, ch = spatial['aligned_canvas_size_x1']
    pad = 4  # one native pixel, even x2-grid phase; display-only global margin
    width, height = cw*4+2*pad, ch*4+2*pad
    cache, records, samples = {}, [], {}
    best_score, sample_id = -1, None
    for f in m['frames']:
        original = sdf.frame(STAGE, f)
        source = np.zeros((height, width, 4), np.uint8)
        l,t,r,b = f['runtime_crop_box_x4']
        source[t+pad:b+pad,l+pad:r+pad] = original
        candidate, checks = sdf.smooth_rgba(source, cache)
        visible = (source[:,:,3] > 0) & (candidate[:,:,3] > 0)
        assert np.array_equal(candidate[:,:,:3][visible], source[:,:,:3][visible])
        candidate[candidate[:,:,3] == 0] = 0
        assert not candidate[candidate[:,:,3] == 0].any()
        assert not candidate[[0,-1],:,:].any() and not candidate[:,[0,-1],:].any(), 'preview border too tight'
        primary = candidate.copy()
        primary[:,:,:3] = np.rint(candidate[:,:,:3].astype(np.float32)*candidate[:,:,3:4]/255).astype(np.uint8)
        assert np.all(primary[:,:,:3] <= primary[:,:,3:4])
        n = f['frame'];stem = f'{n:03d}'
        for mode, pixels in [('before',source),('after',candidate)]:
            Image.fromarray(pixels).save(REVIEW/'frames'/f'{mode}_{stem}.png',compress_level=3)
        straight = REVIEW/'frames'/f'after_{stem}-straight.rgba'
        premult = REVIEW/'frames'/f'after_{stem}-premultiplied.rgba'
        straight.write_bytes(candidate.tobytes());premult.write_bytes(primary.tobytes())
        delta = np.abs(candidate[:,:,3].astype(np.int16)-source[:,:,3].astype(np.int16))
        if delta.sum() > best_score:
            best_score = int(delta.sum());sample_id=n
            samples={'before':source.copy(),'after':candidate.copy()}
        records.append({'frame':n,'cycle':f['cycle'],'mode':f['mode'],
                        'source_sha256':f['straight_raw_rgba_x4_sha256'],
                        'preview_straight':evidence(straight),'preview_premultiplied':evidence(premult),
                        'source_crop_x4':f['runtime_crop_box_x4'],'source_centre_x1':f['centre_x1'],
                        'source_temporal_frames':f['temporal_source_frames'],
                        'no_new_empty_frame':bool(not source[:,:,3].any() or candidate[:,:,3].any()),
                        'fractional_alpha_pixels':int(((candidate[:,:,3]>0)&(candidate[:,:,3]<255)).sum()),**checks})
        assert records[-1]['no_new_empty_frame']
        if n%20==0:print('SPDEATH3 SDF',n,'/',len(m['frames']),flush=True)
    profiles=[]
    for p in m['timing']['cycles']:
        profiles.append({'id':p['id'],'frames':p['timeline_frame_indices'],
                         'durations':[a/b for a,b in p['phase_durations_rational']],
                         'duration':p['duration_seconds']})
        assert abs(sum(profiles[-1]['durations'])-p['duration_seconds'])<1e-10
    before,after=samples['before'],samples['after']
    delta=ndimage.gaussian_filter(np.abs(after[:,:,3].astype(float)-before[:,:,3]),3)
    cy,cx=np.unravel_index(delta.argmax(),delta.shape)
    sheet=Image.new('RGB',(820,510),(25,32,42));draw=ImageDraw.Draw(sheet)
    for col,(mode,title) in enumerate([('before','Actuel'),('after','SDF Ankheg')]):
        im=Image.fromarray(samples[mode]);im.save(REVIEW/f'{mode}-poster.png')
        detail=im.crop((cx-24,cy-24,cx+24,cy+24)).resize((384,384),Image.Resampling.NEAREST)
        bg=Image.new('RGBA',detail.size,(110,94,70,255))
        sheet.paste(Image.alpha_composite(bg,detail).convert('RGB'),(col*410+8,35))
        sheet.paste(detail.getchannel('A').resize((76,76),Image.Resampling.NEAREST).convert('RGB'),(col*410+8,426))
        draw.text((col*410+8,10),title,fill='white')
        draw.text((col*410+92,442),f'Alpha / phase {sample_id}',fill='white')
    sheet.save(REVIEW/'detail.png')
    gallery({'profiles':profiles,'size':[width,height],'detail_focus':[int(cx),int(cy)]})
    assert workflow.sha256_file(game_manifest)==installed_sha
    assert evidence(STAGE/'manifest.json')==manifest_evidence
    result={'schema':'effects-spdeath3-sdf-preview-v1','resref':'SPDEATH3','phases':len(records),
            'profiles':profiles,'frames':records,'source':manifest_evidence,
            'reference':evidence(sdf.REFERENCE),'adapter':evidence(RECIPE),'producer':evidence(Path(__file__)),
            'accepted_ankheg_qa':evidence(QA),
            'method':{'sigma_x4':4,'field_bias_limit_x4':2,'inset_x4':0,'quantization_x2':1/16,
                      'area_supersampling':8,'topology':'FG8/BG4 preserved on x2 field',
                      'rgb':'existing covered RGB exact; nearest foreground extrusion on newly covered edge',
                      'temporal_alpha':'existing nearest foreground opacity envelope'},
            'preview_margin_x4':pad,'preview_size_x4':[width,height],
            'preview_margin_only':'same display origin/margin for both; runtime geometry/carrier unchanged',
            'sdf_masks_computed':len(cache),'existing_visible_rgb_identical':True,
            'native_timing_and_phase_selection_unchanged':True,'new_neural_inference':0,
            'installed_manifest_unchanged_sha256':installed_sha,'production_authorities_changed':False,
            'installed':False,'qa':'pending-user-preview','preview':'review/index.html'}
    save(OUT/'result.json',result)
    save(OUT/'summary.json',{'resref':'SPDEATH3','phases':len(records),'sdf_masks':len(cache),
         'changed_alpha_pixels':sum(r.get('changed_alpha_pixels',0) for r in records),
         'fractional_alpha_pixels':sum(r['fractional_alpha_pixels'] for r in records),
         'alpha_mass_ratio_range':[min(r.get('alpha_mass_ratio',1) for r in records),max(r.get('alpha_mass_ratio',1) for r in records)],
         'max_added_distance_x4':max(r.get('max_added_distance_x4',0) for r in records),
         'sdf_inset_x4':0,'sample_frame':sample_id,'installed':False,'production_authorities_changed':False})
    print('READY',len(records),'phases;',len(cache),'SDF masks; preview only',flush=True)


if __name__=='__main__':main()
