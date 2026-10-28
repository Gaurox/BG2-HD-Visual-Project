from pathlib import Path
import hashlib
import json
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
GAME=get_path('bg2ee_game_root',required=True)
RESULT=ROOT/'projectiles/analysis/validation-v13-20261028-v1'
OUT=ROOT/'projectiles/analysis/masque-capture-v14-20261028-v1'
REF='projectiles/analysis/validation-v13-20261028-v1/evidence.json'
def js(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def save(p,d):
    with p.open('x',encoding='utf-8') as f:json.dump(d,f,ensure_ascii=False,indent=2);f.write('\n')

proof=js(RESULT/'evidence.json')
save(RESULT/'acceptance.json',dict(user_feedback=proof['user_feedback'],scope='Three observed effects accepted visually in V13; technical conclusions remain separate',
    technical={'LIGHTCHA':'All three trails HD+mask+odd phases confirmed','BOLT2':'Flight HD+mask confirmed; only phases0/2 in3draws, no odd phase/cadence claim','MAGICMIS':'Visually accepted native rendering; zero final HD bindings due to64x88 contract mismatch. V14 correction awaits ingame check.'},
    no_global_QA_or_release=True))
progress=js(ROOT/'projectiles/analysis/validations-manuelles-consolidees-20261028-v1/secondary-progress.json')
for row in progress['remaining']:
    row.update(current_state='observed-component-accepted-with-HD-mask-and-odd-phase-evidence',current_evidence=REF)
    progress['prior_shared_evidence'].append(row)
progress['remaining']=[]
progress['limits']='37 role/asset groups with shared runtime evidence; not37 complete PROs, not every palette/cycle/owner. LIGHTCHA static word9 is not an observed runtime sequence.'
assert len(progress['prior_shared_evidence'])==37
save(RESULT/'secondary-progress.json',progress)
path=ROOT/'projectiles/index/work-tracking.json';tracking=js(path)
before={n:{k:v for k,v in x.items() if k in ('integration','installation','release')} for n,x in tracking['projectiles'].items()}
for owner in ['LIGHTCHA','BOLT2','MAGICMIS']:
    row=tracking['projectiles'][owner]
    if REF not in row.setdefault('historical_evidence',[]):row['historical_evidence'].append(REF)
    row['qa']['evidence'].append(REF)
    row['qa']['latest_manual_feedback']=dict(text=proof['user_feedback'],renderer='V13',evidence=REF)
tracking['projectiles']['LIGHTCHA']['qa']['scope']=['SPCHLGT1','SPCHLGT2','SPCHLGT3']
tracking['projectiles']['LIGHTCHA']['notes']='V13 visuellement accepté : SPCHLGT1/2/3,93dessinsHD dont89masqués et50phases impaires ;3missCPU initiaux suivis de succès,0rejetmasque. Séquences5/7 observées, pasdecycle9 fabriqué ; pasQAcomplète duPRO.'
tracking['projectiles']['BOLT2']['notes']='Vol Semence accepté visuellement ; V13 SPFIRSE2 troisdessinsHD dont2masqués, séquence4,phases0/2. LiaisonHD/masque duvol confirmée ; pasdephase impaire/cadence mesurée dansces3dessins. Explosion/dispersion/fumée déjàacceptées conservées.'
tracking['projectiles']['MAGICMIS']['notes']='Aspect V13 accepté maisdessin restaitnatif : canevasréel64x88,pack64x78. V14installée : sourceutile64x64 extraiteenmémoire depuisy7dupack,positionnativeetmasque parpasse ;5suitesdontGPU64x78/88passantes. QAHD/masqueV14enattente ; accordasset7septembre conservé, aucuneimageretraitée.'
for n,x in before.items():assert {k:v for k,v in tracking['projectiles'][n].items() if k in ('integration','installation','release')}==x
path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
raw=(GAME/'InfinityEngine-Enhancer.log').read_bytes()
v14=js(ROOT/'engine/InfinityEngine-Enhancer/installations/projectiles-mask-canvas-20261028-v14/installation.json')
save(OUT/'log-baseline.json',dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest().upper(),last_line=raw.decode('utf-8',errors='replace').splitlines()[-1],dll=v14['dll'],temporary_trace=True))
save(OUT/'next-test.json',dict(resource='SPMAGMIS',command='C:Eval(\'ForceSpellRES("SPWI112","XQTARG")\',0)',
    setup='Reload test save, partyAI off, open space east of Player1; create one passive target',
    target_command='C:Eval(\'CreateCreatureObjectOffset("XQTARG",Player1,[384.0])\',0)',
    after='Wait15seconds unpaused then quit normally, no save',
    expected='Real HD draws, successful native masking where needed, odd animation phases and no persistent geometry/mask fallback',
    no_retest=['SPWI615/LIGHTCHA','FIRESEED/BOLT2'],cleanup='After capture and game/loader stop, disable only EnableEffectStreamingTrace; preserve V14 and manual approvals'))

p=ROOT/'projectiles/SUIVI_MANUEL.md';text=p.read_text(encoding='utf-8-sig')
start=text.index('## Suite utile')
text=text[:start]+'''## Suite utile

- **Éclairs acquis en V13** : SPCHLGT1/2/3,93dessinsHD dont89masqués,50phases impaires ;3chargementsCPU initiaux suivis de succès,0rejetmasque. Séquences5/7 réelles. Plus de test des éclairs demandé.
- **Vol de Semence acquis HD+masque en V13** :3dessinsHD dont2masqués,phases0/2 ; aucune phase impaire/cadence mesurée dans ce court échantillon. Autres composants déjà acquis conservés. Plus de test de Semence demandé.
- Matrice secondaire : [37/37 groupes rôle/asset ont désormais une preuve technique partagée](analysis/validation-v13-20261028-v1/secondary-progress.json) ; cela n'accepte pas tous les PRO/palettes/cycles ni leur fermeture complète.
- **Un seul contrôle reste préparé** : [Projectile magique V14](analysis/masque-capture-v14-20261028-v1/README.md). L'aspect V13 était accepté, mais le pack64×78 ne correspondait pas au canevas natif64×88. V14 réutilise sa zone utile64×64 en mémoire et la place sur le canevas natif réel ;5suitespassantes, dont lecture de chaque pixelGPU64×78/88,0imageretraitée. Pas d'acceptationHDV14 avant logs.
- Contrats non exercés : valeur9 déclarée LIGHTCHA, TSKULLNP et enfantSHAREA202 restent distincts. Aucune propagation automatique des validations aux propriétaires non testés.
- Hors campagne : nouvelles images BGLRYU/SPCL236U/SPGLYPHI, dépendanceMAGMIS absente ; déplacement reporté [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001).
- Trace temporaireV14 active pour le dernier tir : après capture, jeu/loader arrêtés, désactiver seulement la trace et garderV14.
'''
lines=text.splitlines()
for idx,line in enumerate(lines):
    if line.startswith('| LIGHTCHA |'):
        cells=line.split('|');cells[5]=' V13 : trois traînéesHD+masque+phasesimpaires confirmées, pasQAcomplète de touslescycles. ';lines[idx]='|'.join(cells)
    if line.startswith('| BOLT2 |'):
        cells=line.split('|');cells[5]=' V13 : volHD+masque confirmé ;3dessins/phases0,2 seulement, pasdephaseimpaire mesurée. Effets déjàacquis conservés. ';lines[idx]='|'.join(cells)
    if line.startswith('| MAGICMIS |'):
        cells=line.split('|');cells[5]=' AspectV13 accepté maisrendu natif64×88 ; V14corrige leplacementvariable, contrôleHD/masqueencoreattendu. QAasset historiqueconservée. ';lines[idx]='|'.join(cells)
text='\n'.join(lines)+'\n'
text=text.replace('Matrice secondaire : 35/37 groupes avec preuve technique partagée antérieure ; les deux groupes d’éclair restants ont un retour visuel positif mais pas encore de confirmation technique V11 suffisante. Ne pas afficher «37/37 HD validés».','Matrice secondaire :37/37groupes avec preuve technique partagée aprèsV13, sansacceptationglobale de tousleurspropriétaires ; SPMAGMIS resteencontrôleV14 séparé.')
p.write_text(text,encoding='utf-8')
print('Saved V13 acceptance;37shared groups; flight/trails confirmed. Only V14 magic-missile capture pending.')
