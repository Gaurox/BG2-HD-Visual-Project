"""Publish a new comparison revision; keep all previous candidate/gallery files."""
from common import *
import copy,os,re,subprocess,shutil

def main():
    assert not (OUT/'result.json').exists(),'Delivered revision exists: create a new version instead.'
    verification=load(OUT/'verification.json');assert verification['status']=='passed' and verification['contexts']==39
    plan=load(OUT/'plan.json')
    if 'jobs' in plan:plan['parent_jobs']=plan.pop('jobs');save(OUT/'plan.json',plan)
    changed={a['job_id']:a for a in jobs()};catalog=copy.deepcopy(load(WEB/'catalog.json'));review=OUT/'review';profiles=0
    for asset in catalog['assets']:
        latest=asset['ordinal'] in {1,2,3,4,5,6,22,27}
        if latest:
            asset['actions']='xBR x4 · masque natif' if asset['ordinal']<=6 else 'Contour doux · noir transparent'
            asset['history']=['Vanilla · 15 fps','SeedVR · 30 fps','ReboutCX · 30 fps' if asset['ordinal']<=6 else 'Masque lissé · 30 fps','xBR · 30 fps' if asset['ordinal']<=6 else 'Noir transparent · 30 fps']
        for ctx in asset['contexts']:
            key=Path(ctx['data']).stem
            if key in changed:
                r=load(OUT/'results'/f'{key}.json');data={k:r[k] for k in ('resref','ordinal','job_id','size_x4','profiles')}
                data.update(actions=asset['actions'],black_neutral=asset['ordinal'] in (22,27))
                initial=load(PREVIOUS/'results'/f'{key}.json')
                for profile,parent in zip(data['profiles'],initial['profiles'],strict=True):profile['initial']=[old_image(path) for path in parent['before']]
            else:
                data=copy.deepcopy(load(WEB/ctx['data']))
                for profile in data['profiles']:
                    for version in ('native','before','after'):profile[version]=[old_image(p) for p in profile[version]]
            profiles+=len(data['profiles']);save(review/ctx['data'],data)
            for profile in data['profiles']:
                assert len(profile['before'])==len(profile['after'])==profile['phases']
                assert all(media(path).exists() for field in ('native','before','after','initial') if field in profile for path in profile[field])
    assert profiles==658
    catalog['latest_revision']={'assets':8,'contexts':39,'xbr_native_mask':[1,2,3,4,5,6],'black_neutral':[22,27]};save(review/'catalog.json',catalog)
    (review/'board-bounds.json').write_bytes((WEB/'board-bounds.json').read_bytes())
    template=Path(__file__).parent/'board.html'
    page=template.read_text(encoding='utf-8').replace('27 effets corrigés · 99 palettes disponibles · choisir la palette et le cycle sur chaque carte. Les pauses natives sont conservées.',
        '01–06 : xBR et masques natifs · 22 et 27 : noir transparent · 99 palettes disponibles. Choisir palette et cycle sur chaque carte.')
    (review/'index.html').write_text(page,encoding='utf-8');(review/'detail.html').write_bytes((WEB/'detail.html').read_bytes())
    (review/'.gitignore').write_text('/images/\n',encoding='utf-8')
    js=re.search(r'<script>(.*?)</script>',page,re.S)[1];check=subprocess.run(['node','--check'],input=js.encode(),capture_output=True);assert check.returncode==0,check.stderr
    # Expose candidate media through the existing8794 origin; hard links avoid duplicate pixels.
    for path in review.rglob('*'):
        if not path.is_file():continue
        dst=EXPOSED/path.relative_to(review);dst.parent.mkdir(parents=True,exist_ok=True)
        if not dst.exists():
            try:os.link(path,dst)
            except PermissionError:shutil.copyfile(path,dst)
        else:assert dst.read_bytes()==path.read_bytes(),'Published revision already differs: '+str(dst)
    entry=WEB/'index.html';old_entry=evidence(entry)
    redirect=f'<!doctype html><meta charset="utf-8"><meta http-equiv="refresh" content="0;url={REVISION}/index.html?v=xbr-native1"><title>Planche effets actualisée</title><a href="{REVISION}/index.html?v=xbr-native1">Ouvrir la planche animée actualisée</a>\n'
    entry.write_text(redirect,encoding='utf-8')
    result={'schema':'bg2-effects-correction-preview-v2','date':'2026-10-19','assets_updated':8,'contexts_updated':39,
        'xbr_assets':6,'xbr_contexts':37,'black_assets':[22,27],'gallery_assets':31,'gallery_contexts':99,'gallery_profiles':profiles,
        'phases_updated':verification['phases'],'parent':evidence(PREVIOUS/'result.json'),'verification':evidence(OUT/'verification.json'),
        'native_probe':evidence(OUT/'native/probe.json'),'preview':'http://127.0.0.1:8794/'+REVISION+'/index.html?v=xbr-native1',
        'previous_entry':old_entry,'current_entry':evidence(entry),'gallery':evidence(review/'catalog.json'),'template':evidence(template),
        'unchanged_other_contexts':60,'plan':evidence(OUT/'plan.json'),
        'recipe':[evidence(path) for path in sorted(Path(__file__).parent.glob('*.py'))],
        'qa':'pending-user-preview','installed':False,'production_registry_changed':False,'release_changed':False}
    save(OUT/'result.json',result);print('Published31/99 board,8effects/39contexts updated; all658profiles available.',flush=True)

if __name__=='__main__':main()
