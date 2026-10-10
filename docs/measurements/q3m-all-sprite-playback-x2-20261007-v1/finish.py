"""Record installed shared runtime independently of unchanged family production/QA."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from palette_work_plan import file_sha,write_json
from workspace_paths import get_path
load=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
g=load(HERE/'current-generation.json');receipt=load(HERE/'ingame-installation/active-test.json')
v=load(HERE/'runtime-verification.json');a=load(HERE/'analysis.json')
assert receipt['status']=='installed-common-playback-corrected-pending-ingame-confirmation' and v['passed']
game=get_path('bg2ee_game_root',required=True)
assert file_sha(game/'InfinityEngine-Enhancer.dll')==g['dll']['sha256']
assert file_sha(game/'iee-assets/creature-sprites/CreatureSprites-XN.catalog')==g['catalog_sha256']
prefix=HERE.relative_to(ROOT).as_posix();path=ROOT/'sprite/index/q3m-work-tracking.json';t=load(path)
before=json.dumps(t['families'],sort_keys=True)
t['engine_integration'].update(installed_candidate_reference=prefix+'/current-generation.json',
    latest_installation_verification_reference=prefix+'/installation-verification.json')
t['current_shared_runtime_correction']=dict(state='installed-native-verified-pending-ingame-confirmation',
    scope='all15 installed creature/character families;331 IDs',issue='cold metadata and signed native CVidCell cycle slots',
    observed_animation_id='0x6110',observed_resref='CHFF4G1',observed_sequence=15,observed_slot=12,
    generation_reference=prefix+'/current-generation.json',verification_reference=prefix+'/runtime-verification.json',
    installation_reference=prefix+'/installation-verification.json',dll_sha256=g['dll']['sha256'],
    sprites_recalculated=0,assets_unchanged=True,existing_QA_decisions_immutable=True,new_runtime_ingame_QA=False,
    previously_pending_G2_asset_QA_ids=['0x7312','0x7313'],release=False)
assert before==json.dumps(t['families'],sort_keys=True)
write_json(path,t)
for path,marker,entry in (
    (ROOT/'sprite/SUIVI_Q3M.md','## Portée / méthode',
     '- **Correctif runtime commun installé (2026-10-07)** : 331 IDs/15 familles ; attente métadonnées exactes +Loop/Clamp natifs pour tous corps/équipements/parties. Cas Character6110/CHFF4G1/seq15/slot12 reproduit puis corrigé ; 0 sprite recalculé, catalogue/14330 feuilles inchangés. Tests natifs acquis ; confirmation ingame du nouveau runtime encore requise, QA historiques et deux G2 Monster en attente conservées. [Diagnostic/tests/installation](../docs/measurements/q3m-all-sprite-playback-x2-20261007-v1/README.md).'),
    (ROOT/'sprite/index/README.md','# Index sprites',
     '- **Runtime commun installé 2026-10-07** : 331 IDs/15 familles, attente à froid +Loop/Clamp CVidCell généralisés ; Character6110 seq15 slot12 corrigé. 0 recalcul, mêmes assets ; confirmation ingame requise. [Preuves](../../docs/measurements/q3m-all-sprite-playback-x2-20261007-v1/README.md).')):
    text=path.read_text(encoding='utf-8')
    if entry not in text:
        if marker in text:text=text.replace(marker,marker+'\n\n'+entry,1)
        else:
            lines=text.splitlines(True);text=lines[0]+'\n'+entry+'\n'+''.join(lines[1:])
        path.write_text(text,encoding='utf-8',newline='\n')
path=ROOT/'.gitattributes';text=path.read_text(encoding='utf-8');entry=prefix+'/** -text -whitespace'
if entry not in text:path.write_text(text+'\n'+entry+'\n',encoding='utf-8',newline='\n')
write_json(HERE/'summary.json',dict(installed=True,native_verification_passed=True,animation_ids=331,families=15,
    changed_files=['InfinityEngine-Enhancer.dll'],sprites_recalculated=0,physical_leaves_preserved=14330,
    observed_6110_failure_corrected=True,all_playback=v['all_playback'],production_unchanged=True,
    family_QA_unchanged=True,new_runtime_ingame_QA=False,release=False))
print(json.dumps(dict(installed=True,tracking_updated=True,ids=331,sprites_recalculated=0)),flush=True)
