"""Finalize only this production batch: native probes, preserved install, tracking."""
import argparse
import collections
import csv
import io
import json
import subprocess
import time

from temporal import ROOT,BATCH,load,save,digest,rel
from workspace_paths import get_path


def main():
    p=argparse.ArgumentParser();p.add_argument('--wait',action='store_true');args=p.parse_args()
    batch=load(BATCH/'batch.json');assets=batch['assets'];reports=[];checks=[]
    for a in assets:
        path=BATCH/'verification'/f'{a["resref"]}.json'
        if args.wait:
            while not path.exists():time.sleep(3)
        reports.append(load(path));checks.append(load(BATCH/'checks'/f'{a["resref"]}.json'))
    assert len(reports)==64 and all(r['passed'] for r in reports)
    probe=ROOT/'build/iee-map-first-frame-refresh-20261014-v1/Release/iee_effect_animation_x4_registry_tests.exe'
    native=[]
    for a in assets:
        result=subprocess.run([str(probe),str(ROOT/a['pack']),str(BATCH/'contracts'/f'{a["resref"]}.tsv')],capture_output=True,text=True)
        assert result.returncode==0,(a['resref'],result.stdout,result.stderr)
        rows=len((BATCH/'contracts'/f'{a["resref"]}.tsv').read_text(encoding='ascii').splitlines())
        native.append({'resref':a['resref'],'passed':True,'contracts':rows,'probe_output':result.stdout.strip()})
        print(a['resref'],'native probe PASS',rows,flush=True)
    save(BATCH/'native-verification.json',{'passed':64,'contracts':sum(r['contracts'] for r in native),
        'probe':rel(probe),'probe_sha256':digest(probe.read_bytes()),'assets':native})
    reference=load(BATCH/'installation-preserved-reference.json');game=get_path('bg2ee_game_root')
    current={n:digest((game/n).read_bytes()) for n in reference['files']}
    assert current==reference['files']
    save(BATCH/'installation-preserved-final.json',{'passed':True,'files':current,'character_profile':'NearestRGB-SilhouetteAlphaAA',
        'renderer_and_installed_effects_unchanged':True,'no_game_control':True,'new_effects_installed':False})
    before={r['asset_key']:r for r in csv.DictReader(io.StringIO(subprocess.check_output(['git','show','HEAD:effects/index/processing.csv']).decode('utf-8-sig')))}
    after={r['asset_key']:r for r in csv.DictReader((ROOT/'effects/index/processing.csv').open(encoding='utf-8-sig',newline=''))}
    keys={f'effects:bam:{a["resref"]}' for a in assets};assert set(before)==set(after)
    assert all(before[k]==r for k,r in after.items() if k not in keys)
    fields=('qa_state','qa_evidence','selected_run','installation_state','installation_receipt','release_state','release_candidate')
    for a in assets:
        k=f'effects:bam:{a["resref"]}';r=after[k]
        assert r['spatial_run']==a['spatial_run'] and r['interpolation_run']==a['interpolation_run']
        assert r['spatial_state']=='produced' and r['interpolation_state']=='produced'
        assert all(r[f]==before[k][f] for f in fields)
    result={'schema':'bg2-effects-lot64-production-final-v1','status':'completed-awaiting-user-review','count':64,
        'model':'seedvr2_7b_int8_convrot.safetensors','scale':4,'filter':'NEAREST','target_fps':[30,1],
        'native_cycles':sum(r['native_cycles'] for r in reports),'cycle_mode_profiles':sum(r['cycle_mode_variants'] for r in reports),
        'phases':sum(r['phases'] for r in reports),'raw_bytes':sum(r['raw_bytes'] for r in reports),
        'visible_adjacent_duplicates':sum(c['visible_adjacent_duplicates'] for r in reports for c in r['cycles']),
        'loop_seam_duplicates':sum(c['loop_seam_duplicate'] for r in reports for c in r['cycles']),
        'nonconsecutive_pose_revisits':sum(c['nonconsecutive_pose_revisits'] for r in reports for c in r['cycles']),
        'constant_native_profiles':[{'resref':r['resref'],**c} for r in reports for c in r['cycles'] if c['constant_native_cycle']],
        'alternate_playback_profiles':{c['resref']:c['alternate_playback_profiles'] for c in checks if c['alternate_playback_profiles']},
        'native_contracts':sum(r['contracts'] for r in native),'native_durations_and_world_geometry_preserved':True,
        'character_profile_unchanged':True,'installed':False,'qa':'awaiting-user-review','release_changed':False,'assets':checks}
    assert result['visible_adjacent_duplicates']==result['loop_seam_duplicates']==0
    save(BATCH/'production.json',result)
    # Wait for all review derivatives to finish before publishing completion.
    if args.wait:
        while not (BATCH/'review/review.json').exists():time.sleep(3)
    review=load(BATCH/'review/review.json');assert review['count']==64
    assert all((BATCH/f'review/lot64-animated-{i}.mp4').is_file() for i in range(1,5))
    (BATCH/'README.md').write_text(f'''# Lot64 — production terminée, contrôle utilisateur attendu

- 64 effets SeedVR2 7B/LAB x4, NEAREST, Apollo30 ; {result['native_cycles']} cycles natifs, {result['cycle_mode_profiles']} profils cycle/mode, {result['phases']} phases produites. `production.json` lie les64 packs/runs/checks.
- Durées rationnelles et géométrie monde natives conservées ; maintien de poses supprimé avant interpolation sur durée native ; aucun doublon visible adjacent ni endpoint de boucle émis deux fois.
- `verification/*.json` : vérification indépendante, phase par phase ; `native-verification.json` : {result['native_contracts']} contrats séquence/slot/phase/backing/casse dans le chargeur C++ réel.
- Profils constants/invisibles natifs et retours non consécutifs sur une pose explicitement recensés dans `production.json` ; aucune animation fabriquée pour un cycle technique transparent.
- `review/index.html` : 64 effets animés et tous les cycles/profils sélectionnables ; WebP lossless. `review/lot64-animated-{{1,2,3,4}}.mp4` : quatre planches de16,30FPS exact,12s, dérivés de contrôle.
- `installation-preserved-final.json` : renderer, effets déjà installés et profil personnages NearestRGB-SilhouetteAlphaAA identiques ; aucun contrôle du jeu ni installation de ce lot.
- Production=produced dans `effects/index/processing.csv` ; aucune décision QA/selection/installation/release déduite. Recette : `pipeline/recipes/effects-lot64-seedvr7b-apollo30-20261015-v1/README.md`.
''',encoding='utf-8')
    readme=ROOT/'effects/README.md';text=readme.read_text(encoding='utf-8')
    marker='## Quotidien — minimum utile'
    addition='Lot64 produit en **7B x4 / NEAREST / Apollo30 par cycle**, contrôle animé en attente :\n[`production et vérifications`](batches/lot64-seedvr7b-apollo30-20261015-v1/production.json),\n[`planche animée et choix des cycles`](batches/lot64-seedvr7b-apollo30-20261015-v1/review/index.html).\nAucune installation ni QA acquise ; profil personnages préservé.\n\n'
    if 'Lot64 produit en **7B x4' not in text:readme.write_text(text.replace(marker,addition+marker),encoding='utf-8')
    save(BATCH/'completed.json',{'status':'completed-awaiting-user-review','assets':64,'review':'review/index.html',
        'preserved_installation':True,'installed':False,'completed_utc':__import__('effect_workflow').utc_now()})
    print(json.dumps({k:v for k,v in result.items() if k not in {'assets','constant_native_profiles'}},ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
