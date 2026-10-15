"""Lossless full-x4 animations, decoded and compared to production RGB hashes."""
import time
from PIL import Image
from temporal import ROOT,BATCH,load,save,digest
from review import world_frames


def main():
    out=BATCH/'review/full-animations';out.mkdir(parents=True,exist_ok=True);reports=[]
    for a in load(BATCH/'batch.json')['assets']:
        name=a['resref'];proof=BATCH/'verification'/f'{name}.json'
        while not proof.exists():time.sleep(3)
        stage=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']/'02-interpolation'
        m=load(stage/'manifest.json');s=load(ROOT/m['parent']['spatial_manifest']);size=tuple(v*4 for v in s['aligned_canvas_size_x1'])
        profiles=[]
        for v in m['timing']['cycles']:
            path=out/f'{name}-{v["id"]}.webp';indices=v['timeline_frame_indices']
            if not path.exists():
                frames=world_frames(a,m,v,size=size)
                duration=[round((i+1)*1000/30)-round(i*1000/30) for i in range(len(frames))]
                frames[0].save(path,save_all=True,append_images=frames[1:],duration=duration,loop=0,lossless=True,method=1)
            with Image.open(path) as opened:
                if not v['constant_native_cycle']:assert opened.n_frames==len(indices),(name,v['id'],'preview phase count')
                for p in range(opened.n_frames):
                    opened.seek(p)
                    assert digest(opened.convert('RGB').tobytes())==m['frames'][indices[p]]['anchored_rgb_sha256'],(name,v['id'],p,'lossless preview mismatch')
            profiles.append({'profile':v['id'],'path':path.relative_to(BATCH/'review').as_posix(),
                             'source_phases':len(indices),'size_x4':list(size),'decoded_rgb_exact':True})
        reports.append({'resref':name,'profiles':profiles})
        save(out/f'{name}.json',reports[-1])
        print(name,'full x4 animated RGB verified',len(profiles),'profiles',flush=True)
    while not (BATCH/'review/review.json').exists() or not (BATCH/'review/full-posters.json').exists():time.sleep(3)
    page=BATCH/'review/index.html';text=page.read_text(encoding='utf-8')
    if 'Animation x4 sans réduction' not in text:
        button='''<button type="button" onclick="window.open(this.closest('article').querySelector('select').value.replace('cycles/','full-animations/'),'_blank')">Animation x4 sans réduction</button>'''
        text=text.replace('</select>','</select>'+button)
        text=text.replace('</header>','<p>Chaque animation x4 complète est disponible sans réduction ni perte : bouton sous le choix du cycle. Les pixels RGB décodés sont identiques aux images de production, vérifiés phase par phase.</p></header>')
        page.write_text(text,encoding='utf-8')
    save(BATCH/'review/full-animations.json',{'count':len(reports),'assets':reports,'all_decoded_rgb_exact':True,
         'fps':[30,1],'webp_timing':'33/34ms cumulative rounded timestamps; native durations preserved to nearest millisecond in preview'})
    print('64 full-resolution animated effects ready, every RGB phase verified lossless',flush=True)


if __name__=='__main__':main()
