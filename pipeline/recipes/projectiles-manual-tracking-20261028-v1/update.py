"""Consolidate explicit visual decisions; never infer complete-PRO/runtime QA."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import csv
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'pipeline/scripts'))
from workspace_paths import get_path
from projectile_tracking import validate_tracking

OUT = ROOT/'projectiles/analysis/validations-manuelles-consolidees-20261028-v1'
REF = OUT.relative_to(ROOT).as_posix()
GAME = get_path('bg2ee_game_root', required=True)
ENTRIES = []


def evidence(folder, name='acceptance.json'):
    return f'projectiles/analysis/{folder}/{name}'


def add(owner, label, driver, assets, proofs, technical, state='accepted-observed-components', limits='Composants observés seulement ; pas de QA complète du PRO ni de tous ses propriétaires.'):
    ENTRIES.append(dict(owner=owner, label=label, driver=driver, observed_components=assets.split(';'),
                        visual_state=state, evidence=proofs, technical=technical, limits=limits))


def save(path, data):
    with path.open('x', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write('\n')


def main():
    assert not OUT.exists(), 'Immutable consolidation already exists'
    OUT.mkdir()
    raw = (GAME/'InfinityEngine-Enhancer.log').read_bytes()
    lines = raw.decode('utf-8', errors='replace').splitlines()
    start = max(i for i, s in enumerate(lines) if 'Infinity Engine Enhancer initializing...' in s)
    session = lines[start:]
    snapshot = ('\n'.join(session)+'\n').encode('utf-8')
    (OUT/'runtime-session.log').write_bytes(snapshot)
    rows = [dict(re.findall(r'(\w+)=([^ ]+)', s)) for s in session if 'EFX_STREAM_ROW' in s]
    observed = {}
    for name in ['SPCHLGT1', 'SPCHLGT2', 'SPCHLGT3', 'SPFIRSE2', 'SPMAGMIS']:
        subset = [r for r in rows if r.get('resref') == name]
        observed[name] = dict(rows=len(subset), HD=sum(r.get('hd') == 'true' for r in subset),
                              masked=sum(r.get('masked') == 'true' for r in subset),
                              outcomes=dict(Counter(r.get('outcome') for r in subset)),
                              sequences=sorted({r.get('sequence') for r in subset}))
    drops = [int(v) for s in session for v in re.findall(r'traceDropped=(\d+)', s)]
    save(OUT/'latest-feedback.json', dict(
        user_statement='validé. MAJ le suivi projectile avec tout ce qui a été validé manuellement et donne la suite',
        clarification_question='Les deux essais : Éclairs en chaîne et Semence de feu lancée comme arme ?',
        clarification_answer='Oui, les deux essais',
        visual_accepted=['LIGHTCHA observed lightning', 'BOLT2 observed fire-seed flight'],
        runtime_status='incomplete-for-these-tests; visual decision preserved independently',
        log_start_line=start+1, first_line=session[0], last_line=session[-1],
        snapshot_sha256=hashlib.sha256(snapshot).hexdigest().upper(),
        resources=observed, maximum_trace_dropped=max(drops, default=0),
        warnings=[s for s in session if 'EFX_MASK_FALLBACK' in s or 'EFX_COMPOSITE_REJECT' in s],
        limits='No SPFIRSE2/SPCHLGT1/3 row in this snapshot; one SPCHLGT2 CPU-not-ready draw. No inferred HD/mask/interpolation confirmation.'))

    v1 = evidence('validation-vague1-clouds-20261028-v1', 'accepted-components.json')
    v2 = evidence('validation-vague2-writhing-20261028-v1', 'evidence.json')
    variants = evidence('validation-variantes-20261028-v1', 'evidence.json')
    palette = evidence('sharea-palettes-validees-20261028-v1', 'evidence.json')
    motion = evidence('vol-animation-mouvement-20261028-v1', 'evidence.json')
    cones = evidence('mur-brouillard-alpha-20261028-v1', 'feedback.json')
    wall = evidence('mur-brouillard-v10-valide-20261028-v1')
    trap = evidence('piege-zone-sauvage-valides-20261028-v1')
    six = evidence('six-tests-cloud-alpha-20261028-v1', 'evidence.json')
    latest = REF+'/latest-feedback.json'
    add('CLOUDKIL', 'Nuage mortel', 'SPWI502', 'SPCLOUDK→X58CLK', [evidence('nuage-valide-v4-20261028-v1')], 'HD/masque et phases impaires confirmés ; transparence acceptée.')
    for owner, label, driver, assets in [('CLOUD','Nuage puant','SPWI213','SPCLOUDS→X58CLS'), ('1PDEATHF','Brume mortelle','SPWI614','SPDFOGA→X58DFOG')]:
        add(owner,label,driver,assets,[evidence('nuages-v6-valides-20261028-v1')],'HD/masque et phases impaires confirmés ; transparence acceptée.')
    for owner,label,driver,assets in [('1PINCIND','Nuage incendiaire','SPWI810','SPINCINA'),('PWILT','Flétrissure','SPWI812','SPHORWIL;SPHORWIA')]:
        add(owner,label,driver,assets,[v1],'HD/masque observés ; pas de cadence complète mesurée.')
    add('WRITHING','Brouillard putride','SPPR250','WRITHING→X28WRTH',[evidence('writhing-v7-valide-20261028-v1')],'HD/masque et phases intermédiaires confirmés ; profil normal accepté.')
    for owner,label,driver,assets in [('BDSPFIRE','Feu spirituel','SPPR450','BDSFIRET;BDSFIREH;BDSFIREA'),('FDAWN','Aube illusoire','SPPR609','FDAWNX;FDAWNA'),('COMET','Comète','SPWI925','SPCOMTRV;SPCOMEXP')]:
        add(owner,label,driver,assets,[v2],'Textures HD liées ; masques selon les événements disponibles, pas de mesure par phase complète.')
    add('FIREBLIC','Malédiction de Séluné','SPWI953','FIREBICT;FIREBICX;FIREBICR',[variants],'HD/masque observés ; tentatives de lookup 24×16 du vol conservées comme limite.')
    add('SPCL239','Faisceau de la Conscience Solaire','SPCL239','SPCL239X;SPCL239R',[variants,evidence('validation-spcl239-isole-20261028-v1','evidence.json')],'HD/masque confirmés par essai isolé ; retour visuel positif antérieur conservé.')
    add('DDBREAT','Souffle','SPDD03','HDFBRER',[variants],'Anneau HD/masque observé ; pas de validation globale des sous-projectiles.')
    for t in json.loads((ROOT/'projectiles/analysis/sharea-palettes-preparation-20261028-v1/tests.json').read_text(encoding='utf-8-sig')):
        labels={'SPARBLNP':'Ralentissement','SLEEP':'Sommeil','SPARGRNP':'Délivrance de la magie','SPARMANP':'Manteau de terreur','SPARPUPA':'Bénédiction'}
        add(t['pro'],labels[t['pro']],t['spell'],'Anneau SHAREA avec palette native;vol observé',[palette,motion],'Cinq palettes liées HD ; preuve des phases de vol commune TRAVEL, pas cinq mesures de cadence. Déplacement non interpolé.')
    add('BURNHAND','Mains ardentes','SPWI103','SPBHANDI',[cones],'HD/masque confirmés sur le cône observé.')
    add('BDWOFOG','Mur de brouillard','OHBWFOG','BDWOFOGA→X58WFOG',[wall],'HD/masque et phases impaires confirmés ; transparence corrigée acceptée.')
    add('GREEHIT','Souffle de dragon noir','SPIN691','SPBDIMSP;SPBDRAE2',[cones],'HD/masque confirmés sur impact/dispersion observés.')
    add('REDHIT','Impact rouge','SPIN693','SPRDRAIM;SPRDRAE2',[wall],'HD/masque confirmés ; manque de preuve antérieur levé.')
    add('TRAPBOOM','Explosion de piège','SPCL911B sur ennemi','SPSETSCD;SPSETSH;SPFLAMES',[trap],'HD/masque confirmés ; condition ennemi satisfaite.')
    add('WILDZONE','Zone de magie sauvage','OHNROBE3','SPGRWHRL',[trap],'HD/masque confirmés sur l’effet observé.')
    add('FIREBLGR','Feu vert','XPGREEN','FIREBGRT;FIREBGRX;FIREBGRR',[evidence('feu-vert-valide-20261028-v1')],'HD/masque confirmés ; ne valide pas le propriétaire FBFLAMGR.')
    add('INSEC2','Fléau d’insectes','SPPR517','X26PLAA;XIPLAUIN',[six],'HD/masque observés ; pas de mesure finale par phase.')
    add('ICESTORM','Tempête de glace','SPWI404','Y31P067;COLDH',[six],'HD observée et masque COLDH ; tous les enfants/fragments non identifiés.')
    add('LIGHTCHA','Éclairs en chaîne','SPWI615','Éclairs/branches observés',[six,latest],'Visuel accepté explicitement ; dernière session V11 insuffisante : 1 dessin SPCHLGT2 en chargement, 0 SPCHLGT1/3. Confirmation HD/masques/phases à compléter.')
    add('BOLT2','Semence de feu','FIRESEED.ITM','Vol SPFIRSE2;explosion FSEEDX;dispersion FSEEDA;fumée SPSMPUFF',[evidence('piege-semence-resultats-20261028-v1','verification.json'),latest],'Visuel vol accepté explicitement ; effets HD/masque confirmés antérieurement. Aucun vol SPFIRSE2 dans la dernière session : preuve finale vol/phases/masque encore ouverte.')

    hist='historical-visual-acceptance-runtime-changed'
    add('PFIRE2','Boule de feu','SPWI304','FIREBAT et effet de Boule de feu observé',[evidence('boule-de-feu-retest-v3-20261028-v1','summary.json')],'Aspect positif signalé avant correctif du vol ; V3 HD/masque/phases confirmés techniquement, sans nouvel accord visuel V3 explicite.',hist,'Conserver « boule de feu testée ca a l’air ok » comme retour historique ; pas de nouvelle QA visuelle après changement de contrat V3.')
    for owner,label,driver,assets in [('TRAPSKUL','Piège à crâne','SPWI313','Vol SKLT observé'),('CHROMORB','Orbe chromatique','SPWI118','SPCHRORB observé')]:
        add(owner,label,driver,assets,[six,evidence('composition-retest-v5-20261028-v1','verification.json')],'Aspect positif V3 ; rendu V5 corrigé confirmé techniquement, sans nouvel accord visuel V5 explicite.',hist,'Fragments SKLH : preuve technique distincte, aucune acceptation manuelle globale déduite.')
    add('MAGICMIS','Projectile magique','QA asset SPMAGMIS du 2026-09-07','SPMAGMIS',['effects/index/qa-decisions/SPMAGMIS/2026-09-07-accepted-spmagmis-final-fx-r8.json',latest],'QA historique explicite conservée. Session récente : 128 dessins natifs MaskRejected, 36 HD sans masque ; contrat actuel à examiner.','accepted-historical-asset','Ne valide ni chaque compte de missiles ni le contrat actuel de masque depuis le seul ancien accord.')

    assert len({x['owner'] for x in ENTRIES}) == len(ENTRIES)
    source_hashes={}
    for row in ENTRIES:
        for source in row['evidence']:
            p=ROOT/source
            assert p.is_file(), source
            source_hashes[source]=hashlib.sha256(p.read_bytes()).hexdigest().upper()
    counts=dict(Counter(x['visual_state'] for x in ENTRIES))
    save(OUT/'decisions.json',dict(schema='bg2-projectile-manual-decisions-v1',recorded_utc=datetime.now(timezone.utc).isoformat(),
        decision_origin='explicit user visual feedback; historical scope and runtime evidence retained independently',
        source_sha256=source_hashes,counts=counts,decisions=ENTRIES,
        no_complete_PRO_or_release_QA=True,no_new_image_production=True))
    path=ROOT/'projectiles/index/work-tracking.json'
    tracking=json.loads(path.read_text(encoding='utf-8-sig'))
    before={n:{k:v for k,v in item.items() if k!='qa'} for n,item in tracking['projectiles'].items()}
    for row in ENTRIES:
        item=tracking['projectiles'].setdefault(row['owner'],{})
        item['qa']=dict(state=row['visual_state'],evidence=[REF+'/decisions.json']+row['evidence'],
                        scope=row['observed_components'],limits=row['limits'],reviewed_on='2026-10-28')
    for n,item in before.items():assert {k:v for k,v in tracking['projectiles'][n].items() if k!='qa'}==item
    with (ROOT/'projectiles/analysis/audit-complet-243-20261028-v1/projectiles-243.csv').open(encoding='utf-8-sig',newline='') as f:
        names={x['pro'] for x in csv.DictReader(f)}
    validate_tracking(tracking,names)
    path.write_text(json.dumps(tracking,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    table=['# Validations manuelles des projectiles — 2026-10-28','',
        '- Autorité par PRO : [`index/work-tracking.json:qa`](index/work-tracking.json). [Décisions figées](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json), [derniers logs/retour confirmé](analysis/validations-manuelles-consolidees-20261028-v1/latest-feedback.json).',
        f'- {counts.get("accepted-observed-components",0)} PRO avec acceptation visuelle des composants observés ; {len(ENTRIES)-counts.get("accepted-observed-components",0)} décisions historiques conservées séparément. Ces nombres ne sont pas des chaînes intégrales acceptées.',
        '- 100 chaînes `integration=verified-static` conservées : validation technique distincte, pas 100 essais visuels ajoutés. Production/installation/release inchangées par cette consolidation.',
        '- États : `accepted-observed-components` = accord utilisateur limité aux effets vus ; `historical-visual-acceptance-runtime-changed` = accord antérieur au correctif de rendu ; `accepted-historical-asset` = ancien accord asset, contrat courant à examiner.',
        '- Matrice secondaire : 35/37 groupes avec preuve technique partagée antérieure ; les deux groupes d’éclair restants ont un retour visuel positif mais pas encore de confirmation technique V11 suffisante. Ne pas afficher «37/37 HD validés».','',
        '| PRO | Essai | Composants acceptés visuellement | État visuel | Preuve technique / limite |','|---|---|---|---|---|']
    for row in ENTRIES:
        status={'accepted-observed-components':'Accepté, portée observée',hist:'Historique avant correctif','accepted-historical-asset':'Historique asset'}[row['visual_state']]
        table.append('| '+ ' | '.join([row['owner'],row['label']+' / '+row['driver'],', '.join(row['observed_components']),status,row['technical']])+' |')
    table+=['','## Suite utile','',
        '1. **Technique : masque SPMAGMIS** — 128 dessins natifs `MaskRejected` et 36 HD non masqués dans la dernière session ; préserver le repli natif clippé, examiner corrélation/propriétaire et composition. Ancienne QA visuelle conservée, pas de «tout HD» actuel.',
        '2. **Technique : couverture des traces d’éclair et de vol SPFIRSE2** — dernière capture sans SPCHLGT1/3 ni SPFIRSE2 ; un seul SPCHLGT2 en chargement. Les deux essais sont explicitement acceptés visuellement ; ne pas redemander le même contrôle visuel avant d’avoir un protocole de capture utile (trajet assez long/instances et fin de session).',
        '3. **Contrats non exercés** — cycle9 déclaré LIGHTCHA, TSKULLNP et enfant SHAREA202 restent distincts ; aucune propagation automatique des validations aux propriétaires non testés.',
        '- Hors campagne : nouvelles images BGLRYU/SPCL236U/SPGLYPHI, dépendance MAGMIS absente. Déplacement interpolé reporté [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001).',
        '- Trace détaillée V11 : désactivation après cette capture, jeu/loader arrêtés ; reçu de fermeture dans le dossier de consolidation. Aucun nouvel essai demandé à ce stade.','']
    (ROOT/'projectiles/SUIVI_MANUEL.md').write_text('\n'.join(table),encoding='utf-8')
    print(json.dumps(dict(counts=counts,total=len(ENTRIES),latest=observed),ensure_ascii=True))


if __name__=='__main__':
    main()
