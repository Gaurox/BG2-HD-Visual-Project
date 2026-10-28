"""Publish current manual-followup entry points without rewriting old evidence."""
from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'projectiles/analysis/validations-manuelles-consolidees-20261028-v1'
REF=OUT.relative_to(ROOT).as_posix()
assert (OUT/'decisions.json').is_file() and (OUT/'trace-disabled.json').is_file()

tracking_path=ROOT/'projectiles/index/work-tracking.json'
t=json.loads(tracking_path.read_text(encoding='utf-8-sig'))
for name,note in {
    'LIGHTCHA':'V11 : validation visuelle des éclairs explicitement confirmée par utilisateur pour le dernier essai. Dernière trace : SPCHLGT2 un seul dessin CpuNotReady, aucun SPCHLGT1/3 ; confirmation technique HD/masques/phases reste ouverte. Ne pas redemander le même essai visuel. Scope1/3 raccordé, 824contrats passants ; pas de cycle9 inventé.',
    'BOLT2':'Vol de Semence de feu accepté visuellement explicitement, confirmation utilisateur que les deux derniers essais ont été faits. Effets FSEEDX/FSEEDA/SPSMPUFF HD+masque confirmés antérieurement ; aucune ligne SPFIRSE2 dans la dernière capture, preuve finale du vol/phases/masque encore ouverte. Ne pas transformer une lacune de capture en refus visuel.',
    'MAGICMIS':'QA asset SPMAGMIS du7septembre conservée. Dernière session V11 : 128 dessins natifs MaskRejected, 36 HD sans masque ; repli de protection constaté, corrélation/propriétaire à examiner. Aucun retrait d’accord historique, aucune validation HD+masque de tous les dessins courants déduite.'
}.items():
    t['projectiles'][name]['notes']=note
    evidence=t['projectiles'][name].setdefault('historical_evidence',[])
    if REF+'/latest-feedback.json' not in evidence:evidence.append(REF+'/latest-feedback.json')
tracking_path.write_text(json.dumps(t,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

p=json.loads((ROOT/'projectiles/analysis/feu-vert-valide-20261028-v1/secondary-progress.json').read_text(encoding='utf-8-sig'))
for row in p['remaining']:
    row.update(current_state='visual-accepted-technical-evidence-incomplete',
               manual_visual_evidence=REF+'/latest-feedback.json',
               technical_evidence='Latest V11 trace does not confirm these resources; historical generic-HD evidence retained separately')
with (OUT/'secondary-progress.json').open('x',encoding='utf-8') as f:json.dump(p,f,ensure_ascii=False,indent=2);f.write('\n')

intro='''# Projectiles — source, production réutilisable, travail restant

- **Suivi courant : [validations manuelles](SUIVI_MANUEL.md)**. 28 PRO avec acceptation visuelle limitée aux composants observés ; 4 décisions historiques conservées séparément. États explicites `index/work-tracking.json:projectiles.<PRO>.qa` ; [32 décisions et sources figées](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json). Pas de QA intégrale des243PRO déduite.
- **Installation V11 conservée**, SPCHLGT1/3 raccordés au pontFX/masque ; 824contrats/27cycles et3suites passants. [Trace temporaire désactivée](analysis/validations-manuelles-consolidees-20261028-v1/trace-disabled.json) après capture, jeu/loader arrêtés ; autres octets INI et DLL conservés, aucune image retraitée.
- **Derniers essais acceptés visuellement** : éclairs en chaîne et vol de Semence, confirmation utilisateur «Oui, les deux essais». [Logs](analysis/validations-manuelles-consolidees-20261028-v1/latest-feedback.json) insuffisants pour les confirmer techniquement : un dessinSPCHLGT2 en chargement, aucun SPCHLGT1/3 ni SPFIRSE2 ; ne pas invalider le retour visuel ni afficher «37/37 HD».
- **Suite technique** : masque SPMAGMIS (128dessins natifs MaskRejected/36HD non masqués dans la dernière capture), puis protocole utile pour traces vol/éclair. 35/37 groupes secondaires avec preuve partagée antérieure ; les deux restants ont un accord visuel mais une confirmation technique encore ouverte. Aucun nouvel essai visuel identique demandé à ce stade.
- **100chaînes vérifiées statiquement** conservées séparément. [Audit243](analysis/audit-complet-243-20261028-v1/README.md) :100complètes,124partielles,13natives,4avec images manquantes,LIGHTCHAcontrat à examiner,LIGHTSTOdépendance absente. Cet audit historique ne constitue pas une QAingame générale.
- **Déplacement reporté** : [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001), [étude](analysis/deplacement-generalise-etude-20261028-v1/README.md). Animation des images ≠ interpolation des coordonnées ; aucune position intermédiaire ajoutée.
- Preuves/anciennes corrections : [répertoire de reprise](REPRISE_LIAISONS124.md). Ne pas redemander les validations acquises ; conserver les limites de propriétaire/palette/cycle et les états production/QA/installation/release distincts.

'''
readme=ROOT/'projectiles/README.md'
old=readme.read_text(encoding='utf-8-sig')
assert '- Entrée : [SUIVI.md]' in old
readme.write_text(intro+old[old.index('- Entrée : [SUIVI.md]'):],encoding='utf-8')

reprise='''# Reprise — projectiles déjà produits, 2026-10-28

## État courant

- Autorité : [suivi manuel](SUIVI_MANUEL.md), `index/work-tracking.json:qa` ; [32 décisions figées](analysis/validations-manuelles-consolidees-20261028-v1/decisions.json). 28acceptations visuelles de composants observés,3accords antérieurs à un correctif de rendu,1QAasset historique. Aucun PRO complet/ensemble243/release promu depuis ces décisions.
- 100chaînes `integration=verified-static` conservées ; images non produites BGLRYU/SPCL236U/SPGLYPHI et dépendance MAGMIS exclues de la campagne actuelle.
- V11 active : DLL SHA09EEE20EC52546C12BEDDCB61E5365AF0B968C2D27A96313A3575E5B7FB0D850 ; [reçu installation](../engine/InfinityEngine-Enhancer/installations/projectiles-lightning-trails-20261028-v11/installation.json), scopeFXSPCHLGT1/3 ajouté. 538ressources/62500backings,0image retraitée,0PRO modifié,0release.
- [Trace détaillée désactivée](analysis/validations-manuelles-consolidees-20261028-v1/trace-disabled.json) après sauvegarde de la session17:11:46–17:12:37 ; seule cléINI `EnableEffectStreamingTrace=true→false`, autres octets etDLL inchangés, jeu/loader arrêtés. Ne pas restaurer toute l'INI V10/V11 depuis un ancien reçu.
- Dernier retour : validation manuelle de SPWI615 et FIRESEED confirmée explicitement par utilisateur. [État technique séparé](analysis/validations-manuelles-consolidees-20261028-v1/latest-feedback.json) : SPCHLGT2 un dessinCpuNotReady, SPCHLGT1/3 etSPFIRSE2 absents de cette capture,0traceDropped. Les validations visuelles sont acquises ; confirmation finale HD/masques/phases encore ouverte, aucun nouveau jugement visuel identique à réclamer.
- Matrice rôle/asset :35/37groupes avec preuve partagée antérieure ; deux groupes d'éclair visuellement acceptés mais pas confirmés techniquement dansV11. Pas de compteur automatique de PRO complets validés.

## Suite utile

1. SPMAGMIS :128dessins natifs `MaskRejected`,36HD non masqués dans la dernière session ; masque absent à17:12:20, déjà observé16:45:47. Examiner capture/corrélation du propriétaire, passages composés et conditions de clipping ; conserver le repli natif de protection. QAasset7septembre conservée, pas de preuve «toutHD» sur le contrat courant.
2. Préparer une capture utile des éclairs/vol SPFIRSE2 (trajet assez long, cibles vivantes, occurrences et fin de session). Les tentatives géométrie24×16 ne prouvent pas un dessin final natif ; source native et métadonnées concordent. Ne pas retraiter les images pour une lacune de logs.
3. Contrats non exercés : LIGHTCHA valeur9/9cycles0..8, TSKULLNP sans pilote SPL direct, enfantSHAREA202 sans pilote direct. Aucun faux cycle/alias/QA propriétaire à inventer ; réutilisation d'une preuve commune limitée à son contrat.
- Interpolation du déplacement **reportée par utilisateur** : [PROJ-MOTION-001](../pipeline/PROBLEMES_A_RESOUDRE.md#proj-motion-001), [étude](analysis/deplacement-generalise-etude-20261028-v1/README.md). Aucun prototype installé ; ne pas la rouvrir au cours de la validation d'images.

## Preuves acquises et corrections conservées

| Périmètre | Preuve / limite |
|---|---|
| Feu vert | [FIREBGRT/X/R HD+masque, aspect accepté](analysis/feu-vert-valide-20261028-v1/README.md) ; XPGREEN pilote isolé, pasQA propriétaireFBFLAMGR |
| Piège / zone sauvage | [SPSETSCD/SPSETSH/SPFLAMES/SPGRWHRL acceptés](analysis/piege-zone-sauvage-valides-20261028-v1/README.md) ; condition ennemi requise pour piège |
| Mur brouillard / rouge | [V10 acceptée](analysis/mur-brouillard-v10-valide-20261028-v1/README.md), [correspondance alias](analysis/mur-brouillard-alpha-20261028-v1/alias-correspondence.json) ;0image retraitée,2683backingsSHA/2168accès sémantiques vérifiés |
| V8/V9 palettes/vols | [cinq essais acceptés](analysis/sharea-palettes-validees-20261028-v1/README.md), [phases TRAVEL confirmées](analysis/vol-animation-mouvement-20261028-v1/README.md) ;5palettes distinctes, preuve de cadence commune limitée |
| Variantes / cônes / souffles | [SPWI953/SPCL239/SPDD03](analysis/validation-variantes-20261028-v1/README.md), [SPCL239 isolé](analysis/validation-spcl239-isole-20261028-v1/README.md), [quatre cônes/souffles](analysis/validation-suite-cones-souffles-20261028-v1/README.md) ; décisions finales dans suivi manuel |
| Nuages | [CLOUDKIL V4](analysis/nuage-valide-v4-20261028-v1/acceptance.json), [CLOUD/1PDEATHF V6](analysis/nuages-v6-valides-20261028-v1/README.md), [WRITHING V7](analysis/writhing-v7-valide-20261028-v1/README.md) ; transparences acceptées |
| Crâne/orbe / Boule de feu | [V5 technique](analysis/composition-retest-v5-20261028-v1/README.md), [FIREBAT V3 technique](analysis/boule-de-feu-retest-v3-20261028-v1/README.md) ; accords visuels avant correctif gardés comme historiques, pas de nouvel accord déduit |
| Lot124 initial | [recette](../pipeline/recipes/projectiles-secondary-links-20261028-v1/README.md), [124candidats](analysis/liaisons124-20261028-v1/124-candidate-routes.csv) ; correctifs partiels, pas124QAglobales |

- XPGREEN.SPL reste un pilote de test installé ; aucun original remplacé. Nettoyage futur uniquement jeu/loader arrêtés etSHA conforme à [son reçu](analysis/validation-feu-vert-20261028-v1/installation.json).
- Ancienne demande d'arrêtPC : après coordination avec chat `Documenter les bâtiments du triangle` (`01a17feb-6c66-7c10-88cc-68d79706d5d5`) ; un seul arrêt à coordonner, pas d'arrêt pendant les essais actifs.
'''
(ROOT/'projectiles/REPRISE_LIAISONS124.md').write_text(reprise,encoding='utf-8')
manual=ROOT/'projectiles/SUIVI_MANUEL.md'
text=manual.read_text(encoding='utf-8')
text=text.replace('- Trace détaillée V11 : désactivation après cette capture, jeu/loader arrêtés ; reçu de fermeture dans le dossier de consolidation. Aucun nouvel essai demandé à ce stade.',
    '- [Trace détaillée V11 désactivée](analysis/validations-manuelles-consolidees-20261028-v1/trace-disabled.json) après capture, jeu/loader arrêtés ; DLL et autres octets INI conservés. Aucun nouvel essai demandé à ce stade.')
manual.write_text(text,encoding='utf-8')
print('Published current manual followup, QA states, open technical items, trace-off receipt')
