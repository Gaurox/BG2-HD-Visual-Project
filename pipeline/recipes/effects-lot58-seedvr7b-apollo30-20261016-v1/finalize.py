"""Summarize this production only; no selection, installation or release."""
from fractions import Fraction
from temporal import ROOT, BATCH, load, save, digest


def main():
    batch=load(BATCH/'batch.json');assets=batch['assets'];reports=[]
    for a in assets:
        name=a['resref'];v=load(BATCH/'verification'/f'{name}.json')
        assert v['passed'] and v['native_input_keys_unique_before_apollo']
        assert v['native_pixels_palette_world_geometry_preserved']
        assert v['straight_alpha_companions_verified']
        run=ROOT/'effects/ressources'/name/'runs'/a['interpolation_run']
        descriptor=load(run/'run.json');assert descriptor['result']['sealed']
        m=load(run/'02-interpolation/manifest.json')
        for c in m['timing']['cycles']:
            assert sum(Fraction(*d) for d in c['phase_durations_rational'])==Fraction(*c['duration_rational'])
            if not c['constant_native_cycle']:
                assert not c['adjacent_rgb_duplicates'] and not c['loop_seam_duplicate']
                assert c['unique_rgb']==c['unique_rgba']==c['phase_count']
        reports.append({'resref':name,'spatial_run':a['spatial_run'],'interpolation_run':a['interpolation_run'],
                        'pack':a['pack'],'verification':f'verification/{name}.json',
                        'pack_manifest_sha256':v['pack_manifest_sha256'],'phases':v['phases'],
                        'profiles':v['cycle_mode_variants'],'raw_bytes':v['raw_bytes']})
    review=load(BATCH/'review/review.json');assert review['count']==len(assets)==58
    assert [a['resref'] for a in review['assets']]==[a['resref'] for a in assets]
    videos=load(BATCH/'review/videos.json');assert len(videos['videos'])==4
    assert all(v['fps']==[30,1] and v['pts_checked'] for v in videos['videos'])
    gallery=BATCH/'review/index.html';page=gallery.read_text(encoding='utf-8')
    if 'Vue d’ensemble' not in page:
        links=' · '.join(f'<a href="{v["path"]}">Vidéo {i}</a>' for i,v in enumerate(videos['videos'],1))
        page=page.replace('</header>',f'<p>Vue d’ensemble à 30 FPS : {links}</p></header>')
        page=page.replace('</style>','@media(max-width:600px){body{margin:12px}main{display:block}article{margin-bottom:14px}.compare{flex-wrap:wrap}}</style>')
        page=page.replace('</html>','''<script>
function freezeImage(i){if(!i.complete||!i.naturalWidth)return;let c=document.createElement('canvas');c.width=i.naturalWidth;c.height=i.naturalHeight;c.getContext('2d').drawImage(i,0,0);i.src=c.toDataURL('image/png')}
function selectCycle(s){let a=s.closest('article'),o=s.selectedOptions[0],r=a.querySelector('.result'),n=a.querySelector('.native');r.src=playing?o.value:r.dataset.poster;n.onload=()=>{if(!playing&&!n.src.startsWith('data:'))freezeImage(n)};n.src=o.dataset.native;a.querySelector('.full').href=o.dataset.full;a.querySelector('.timing').textContent=o.dataset.phases+' phases · '+Number(o.dataset.duration).toFixed(3)+' s · '+o.dataset.removed+' slots natifs retirés'}
function togglePlay(){playing=!playing;if(playing)document.querySelectorAll('select').forEach(selectCycle);else document.querySelectorAll('.compare img').forEach(freezeImage);document.getElementById('toggle').textContent=playing?'Pause':'Lecture'}
</script></html>''')
        gallery.write_text(page,encoding='utf-8')
    audit=load(BATCH/'native-duplicate-audit.json')
    result={'schema':'bg2-effects-batch-production-result-v1','status':'completed','assets_count':58,
            'source_frames':sum(a['source_frames'] for a in assets),'native_cycles':sum(len(a['native_cycles']) for a in assets),
            'spatial_model':'seedvr2_7b_int8_convrot.safetensors','scale':4,'interpolation_model':'apo-8',
            'target_fps':[30,1],'filter':'NEAREST','native_duplicate_audit':audit['summary'],
            'output_phases_all_independent_profiles':sum(r['phases'] for r in reports),
            'output_profiles':sum(r['profiles'] for r in reports),'runtime_pack_raw_bytes':sum(r['raw_bytes'] for r in reports),
            'native_duration_rationals_preserved':True,'unexpected_visible_duplicates':0,
            'constant_native_cycles_policy':'No invented motion; native constant/transparent content and duration retained; shared backings allowed.',
            'eight_fps_exception':{'resref':'SPFLAST1','duration_seconds':[9,8],'phases':34,'last_phase_seconds':[1,40]},
            'native_timing_basis':{'vvc':'Exact source VVC FPS field','projectiles':'15 FPS compatibility default; not an ingame cadence measurement','sources':['https://github.com/gemrb/gemrb/blob/master/gemrb/core/Animation.h','https://github.com/gemrb/gemrb/blob/master/gemrb/core/Projectile.cpp']},
            'integration_limits':['PRO per-occurrence playback/rate and draw-owner coverage require runtime confirmation.',
                                  'Per-cycle once/loop alternatives and straight-alpha companions retained; default mono-BAM pack is premultiplied and is not an approval of every consumer render mode.'],
            'review':'review/index.html','review_sha256':digest((BATCH/'review/index.html').read_bytes()),
            'overview_videos':'review/videos.json',
            'qa':'pending-user-review','installed':False,'release_changed':False,'assets':reports}
    save(BATCH/'production.json',result)
    progress=load(BATCH/'temporal-progress.json')
    for a in assets:
        progress.setdefault(a['resref'],{}).update(state='completed',error=None,verified=True)
    save(BATCH/'temporal-progress.json',progress)
    print('58/58 produced and independently verified;',result['output_phases_all_independent_profiles'],'phases;',result['output_profiles'],'profiles')


if __name__=='__main__':main()
