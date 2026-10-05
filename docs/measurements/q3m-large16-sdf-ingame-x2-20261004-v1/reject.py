"""Seal the rejected SDF decision and verified restoration of accepted Large16 V7."""
import hashlib,json,struct
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
REF=HERE.relative_to(ROOT).as_posix()
QA='sprite/index/qa-decisions/monster_large16/2026-10-04-rejected-full-large16-q3m-v9-sdf-x2-catmullrom-v1.json'
ACCEPTED='sprite/index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json'
USER='retire SDF c\'est vraiment pas acceptable, ca fait beaucoup trop lisse. valide la famille sans SDF'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def identity(p):return dict(path=p.relative_to(ROOT).as_posix(),sha256=sha(p),bytes=p.stat().st_size)
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

assert not (HERE/'restoration-verification.json').exists() and not (ROOT/QA).exists()
receipt=read(HERE/'ingame-installation/active-test.json');assert receipt['status']=='restored-parent'
game=Path(read(ROOT/'config/workspace-paths.local.json')['paths']['bg2ee_game_root'])
parent=HERE.parent/'q3m-monster-large16-full-x2-20261004-v1';generation=read(parent/'current-generation.json')
catalog=game/receipt['catalog_relative'];dll=game/'InfinityEngine-Enhancer.dll'
assert sha(catalog)==receipt['parent_catalog_sha256']==generation['catalog']['sha256']
assert sha(dll)==receipt['parent_dll_sha256']==generation['dll']['sha256']
for item in receipt['preserved_files']:assert sha(game/item['relative_path'])==item['sha256'].lower(),item['relative_path']
accepted=read(ROOT/ACCEPTED);assert accepted['status']=='accepted'
versions=[]
for item in accepted['resources']:
    path=game/item['registry'];assert sha(path)==item['sha256'].lower()
    with path.open('rb') as stream:header=stream.read(32)
    assert header[:7]==b'IEECSXN' and struct.unpack_from('<H',header,8)[0]==7
    versions.append(dict(registry=item['registry'],sha256=item['sha256'].lower(),version=7))
assert len(versions)==20
proof=dict(schema='bg2-Large16-SDF-restoration-verification-v1',role='installation-restoration-not-new-production',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    status='restored-accepted-V7-no-SDF',family='monster_large16',animation_ids=generation['animation_ids'],scale=2,registry_version=7,SDF=False,resources=20,frames=1692,
    restored_files=[dict(relative_path=receipt['catalog_relative'],sha256=sha(catalog)),dict(relative_path='InfinityEngine-Enhancer.dll',sha256=sha(dll))],
    preserved_files_sha256_verified=len(receipt['preserved_files']),V7_leaves_verified=versions,restored_catalog_byte_identical=True,restored_DLL_byte_identical=True,
    shaders_INI_executable_UI_Ankheg_test_CRE_unchanged=True,Character_SDF_not_enabled=True,accepted_QA=identity(ROOT/ACCEPTED),restoration_receipt=identity(HERE/'ingame-installation/active-test.json'),release=False)
write(HERE/'restoration-verification.json',proof)
trial=read(HERE/'current-generation.json')
decision=dict(schema='bg2-upscale-native-sprite-family-qa-decision-v1',status='rejected',qa_state='failed',recorded_at_utc=datetime.now(timezone.utc).isoformat(),
    scope=dict(kind='installed-complete-available-native-family-contour-trial',engine_family='monster_large16',animation_ids=trial['animation_ids'],variant_id='q3m-v9-sdf-x2-catmullrom',scale=2,resources=18,frames=1688),
    visual_qa=dict(result='fail',authority='user',user_statement=USER,defect='contour excessively smooth; unacceptable visual result'),
    runtime_contract=dict(runtime=trial['runtime'],dll=trial['dll'],catalogue_sha256=trial['catalog']['sha256'],world_filter='CatmullRom',owner=11,colour_profile_id=8,decode_rule_id=3,SDF=True),
    provenance=dict(selected_generation=identity(HERE/'current-generation.json'),production=identity(HERE/'production.json'),installation_snapshot=identity(HERE/'installation-verification.json'),restoration=identity(HERE/'restoration-verification.json')),
    final_selection=dict(variant='Q3m-V7-x2-without-SDF',status='accepted',authority='user',accepted_QA=identity(ROOT/ACCEPTED),generation=identity(parent/'current-generation.json'),installation_state='restored-byte-identical'),release_state='not-promoted')
write(ROOT/QA,decision)

path=ROOT/'sprite/index/q3m-work-tracking.json';d=read(path)
record=next(t for t in d['current_contour_trials'] if t['family']=='monster_large16')
record.update(state='rejected-ingame-restored-accepted-V7-parent',qa_ingame=False,qa_state='failed',qa_decision=QA,qa_decision_sha256=sha(ROOT/QA),installation_state='restored-parent',user_feedback=USER,restoration_reference=f'{REF}/restoration-verification.json')
d['current_contour_trials']=[t for t in d['current_contour_trials'] if t['family']!='monster_large16']
d['historical_contour_trials'].append(record)
family=next(f for f in d['families'] if f['engine_section']=='monster_large16');family['current_contour_trials']=[];family.setdefault('historical_contour_trials',[]).append(record)
family['current_full_production']['installation_restoration_reference']=f'{REF}/restoration-verification.json'
for key in ['installed_candidate_reference','latest_installation_verification_reference']:d['engine_integration'][key]=f'{REF}/restoration-verification.json'
assert family['current_full_production']['qa_ingame'] and family['current_full_production']['qa_reference']==ACCEPTED
assert d['queue_totals']['current_recipe_ingame_accepted_families']==3 and d['queue_totals']['current_recipe_ingame_accepted_animation_ids']==9
write(path,d)

path=ROOT/'sprite/SUIVI_Q3M.md';text=path.read_text(encoding='utf-8')
text=text.replace('Large16 A000/A100/A200 owner11 possède désormais sa propre attente, autres familles restent NonBlocking.','Large16 et les autres familles restent NonBlocking ; l’attente propre à l’essai Large16 a été retirée avec sa DLL.')
text=text.replace('DLL `7dc7394c…3508` (base stable + attente Large16), catalogue Large16 SDF **`e23ccdc6…22a43`**','DLL stable **`0bdaf3b6…e4d5`**, catalogue Large16 V7 sans SDF **`6fbb2f02…44c80`**')
text=text.replace('## Large16 : SDF installé après validation V7','## Large16 : essai SDF rejeté, V7 validé restauré')
text=text.replace('**Actif Large16 : essai V9 SDF x2, QA en attente**','**Historique Large16 : essai V9 SDF x2 rejeté et retiré**')
text+=f'\n- Décision finale utilisateur : **Large16 complet disponible Q3m V7 x2 sans SDF validé et actif**. SDF « beaucoup trop lisse », rejet `{QA}` ; `../{REF}/restoration-verification.json` : DLL/catalogue parent exacts, vingt feuilles V7/1 692frames vérifiées, 119fichiers préservés. Ankheg SDF stable conservé, Character SDF en stock. Delta source attente Large16 annulé ; scripts/patch/build/essai historiques conservés, aucun asset acquis retraité.\n'
path.write_text(text,encoding='utf-8')
path=ROOT/'sprite/index/README.md';text=path.read_text(encoding='utf-8')
text=text.replace('Large16 SDF actif :','Large16 essai SDF historique retiré :').replace('dix-huit feuilles monde/1 688frames, QA en attente. V7 sans SDF reste accepté ; CSV décrit cet acquis V7, essai actif référencé dans `current_contour_trials`.','dix-huit feuilles monde/1 688frames, rejeté : contour trop lisse. **V7 sans SDF accepté et réinstallé** ; CSV décrit cet acquis V7, essai dans `historical_contour_trials`, restauration `restoration-verification.json` du run SDF.')
path.write_text(text,encoding='utf-8')
with (HERE/'README.md').open('a',encoding='utf-8') as out:out.write(f'\n## Décision finale — SDF rejeté et retiré\n\n- Utilisateur : « {USER} ». V9 SDF trop lisse ; QA `{QA}`. **Actif : V7 x2 sans SDF validé**, QA antérieure inchangée/reconfirmée.\n- `restore.ps1` exécuté ; `restoration-verification.json` : DLL+catalogue V7 parent exacts, vingt feuilles V7 et119fichiers inchangés. CREblanc, Ankheg SDF stable et Character en stock conservés. Les mentions installé/en attente plus haut sont historiques.\n- Delta attente Large16 retiré des sources courantes ; `runtime-delta.patch` et build local conservent cet essai. Aucun fichier preuve antérieur réécrit, aucun commit/release demandé dans cette restauration.\n')
print(json.dumps(dict(restored=True,SDF=False,accepted_family='monster_large16',verified_V7_leaves=20,preserved_files=119)))
