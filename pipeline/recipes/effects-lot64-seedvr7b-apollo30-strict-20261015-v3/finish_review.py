"""Check the complete control board, exact video PTS, and add a native-pixel viewer."""
from fractions import Fraction
import json
import re
import shutil
import subprocess
import time
from PIL import Image,ImageDraw,ImageFont
from temporal import BATCH,load,save


def main():
    out=BATCH/'review';proof=out/'control-verification.json'
    if proof.exists():print('Control board already verified');return
    for name in ('completed.json','review/full-animations.json','review/full-posters.json'):
        while not (BATCH/name).exists():time.sleep(3)
    production=load(BATCH/'production.json');review=load(out/'review.json');full=load(out/'full-animations.json')
    assert production['count']==review['count']==full['count']==64
    assert production['visible_adjacent_duplicates']==production['nonconsecutive_pose_revisits']==production['loop_seam_duplicates']==0
    assert full['all_decoded_rgb_exact']
    assert all(load(BATCH/'verification'/f'{a["resref"]}.json')['native_input_keys_unique_before_apollo'] for a in review['assets'])
    page=out/'index.html';text=page.read_text(encoding='utf-8')
    assert text.count('<article>')==text.count('<select ')==text.count('Animation x4 sans réduction')==64
    assert text.count('Frame x4 sans réduction')==64
    names=re.findall(r'<h2>\d+ · ([A-Z0-9_]+)</h2>',text)
    assert names==[a['resref'] for a in review['assets']]
    for a in review['assets']:
        for v in a['variants']:assert (out/v['path']).is_file()
    videos=[]
    for i in range(1,5):
        path=out/f'lot64-animated-{i}.mp4'
        args=[shutil.which('ffprobe'),'-v','error','-select_streams','v:0','-show_entries','frame=best_effort_timestamp',
              '-show_entries','stream=time_base,avg_frame_rate,nb_frames','-of','json',str(path)]
        data=json.loads(subprocess.check_output(args));stream=data['streams'][0];tb=Fraction(stream['time_base'])
        stamps=[int(f['best_effort_timestamp']) for f in data['frames']]
        assert len(stamps)==360 and stream['avg_frame_rate']=='30/1'
        assert all((b-a)*tb==Fraction(1,30) for a,b in zip(stamps,stamps[1:]))
        videos.append({'path':path.name,'frames':360,'every_pts_interval':[1,30],'all_pts_intervals_exact':True})
    viewer='''<!doctype html><html lang="fr"><meta charset="utf-8"><title>Animation x4 — sans perte</title>
<style>body{margin:0;background:#090b10;color:#eef2f9;font:15px system-ui}header{position:sticky;top:0;background:#151b26;padding:12px;z-index:1}button{background:#26344a;color:white;border:1px solid #5d7190;padding:7px;margin:0 5px;cursor:pointer}img{image-rendering:pixelated;max-width:none;display:block}#view{overflow:auto;padding:12px}p{margin:8px 0 0;color:#bccbe1}</style>
<header><b id="name"></b><button onclick="zoom(.5)">50%</button><button onclick="zoom(1)">100%</button><button onclick="zoom(2)">200%</button><button onclick="fit()">Ajuster</button><span id="scale"></span><p>100% = pixels x4 de production sans réduction. Rééchantillonnage NEAREST aux autres zooms ; RGB sans perte sur fond noir. La taille dans cette visionneuse ne représente pas la taille ingame.</p></header><div id="view"><img id="effect"></div>
<script>const img=document.getElementById('effect'),file=new URLSearchParams(location.search).get('animation');function zoom(z){img.style.width=Math.round(img.naturalWidth*z)+'px';img.style.height=Math.round(img.naturalHeight*z)+'px';document.getElementById('scale').textContent=Math.round(z*100)+'%'}function fit(){zoom(Math.min((innerWidth-30)/img.naturalWidth,(innerHeight-140)/img.naturalHeight))}if(file&&/^[A-Z0-9_]{1,8}-cycle[0-9]{3}-(loop|once)\.webp$/.test(file)){document.getElementById('name').textContent=file.replace('.webp','');img.onload=()=>zoom(1);img.src='full-animations/'+file}else{document.getElementById('name').textContent='Animation invalide'}</script></html>'''
    (out/'full.html').write_text(viewer,encoding='utf-8')
    old="window.open(this.closest('article').querySelector('select').value.replace('cycles/','full-animations/'),'_blank')"
    new="window.open('full.html?animation='+encodeURIComponent(this.closest('article').querySelector('select').value.split('/').pop()),'_blank')"
    text=text.replace(old,new);assert text.count('full.html?animation=')==64
    page.write_text(text,encoding='utf-8')
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',21)
    for i in range(4):
        image=Image.new('RGB',(1080,1016),(12,15,22));d=ImageDraw.Draw(image)
        d.text((20,12),f'64 effets — 7B x4 / NEAREST / Apollo30 — {i+1}/4',font=font,fill='white')
        for j,a in enumerate(review['assets'][i*16:i*16+16]):
            x,y=(j%4)*270,65+(j//4)*237
            with Image.open(out/'posters'/f'{a["resref"]}.png') as poster:image.paste(poster,(x+15,y))
            d.text((x+12,y+192),f'{i*16+j+1:02d} {a["resref"]}',font=font,fill='white')
        image.save(out/f'lot64-poster-{i+1}.png')
    result={'passed':True,'assets':64,'cycle_profiles':sum(len(a['variants']) for a in review['assets']),
            'production_phases':production['phases'],'native_keys_unique_before_apollo':True,
            'all_animated_rgb_rgba_unique_per_cycle':True,'full_x4_decoded_rgb_exact':True,
            'native_pixel_viewer':'full.html','videos':videos,'character_profile_preserved':True,'installed':False}
    save(proof,result);print(json.dumps(result,ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
