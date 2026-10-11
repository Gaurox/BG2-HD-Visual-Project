# Lots4/5 — traitement et installation, 2026-10-11

État courant : **lot4 accepté ingame et terminé**, AM0510A nouvel essai SeedVR7B seed20261011 retenu. **Lot5 seul en attente** :3assets/4variantes/20cartes/68occurrences, registre `à-valider`, release non sélectionnée. Lot3 accepté séparément (AM0902L SeedVR retenu). Détails QA/retrait : `../am0510a-seedvr7b-retest-20261011-v1/README.md` et `acceptance.json`. Ce document décrit aussi la production initiale historique.

Index courant lot5 : `animations/packs-par-zone/lot5-current-20261011-v1` ;20feuilles byte-identiques à l'installation. Aperçu et commandes : `animations/batches/lot5-current-20261011-v1/{preview-lot5.png,CLUA.md}`. Sorties/aperçus AM0510A écartés et ancien index complete21cartes supprimés ; confirmation explicite pour le dossier partagé : « Oui, supprimer ce pack partagé ». Les métadonnées historiques restent immuables. Les scripts historiques ne sont pas à rejouer sur ces IDs.

| Lot / asset | Recette finale | Durées / déduplication |
|---|---|---|
| 4 / AM0510A | Réutilisation SeedVR2 7B INT8/LAB x4 + Apollo8 existants ; masque authored `mask.py` : arche/aperture opaque, halo au sol pondéré par variation lumineuse native, fondu extérieur8px x4, fade canvas12 ; suppression du rectangle statique | 9poses distinctes →18phases ; 0,6s. RGB conservé sous alpha visible ; pixels alpha0 mis à RGB0. Masque opaque22,76%, visible31,23%, ouverture noire de la carte entièrement couverte |
| 5 / AM3000E | Palette BMP **PLT_MAGE réalisée sur indices x1 avant ReboutCX** ; canvas aligné selon centres ; Apollo8 ; prémultiplication RGB unique. Aucun inner fade : le sweep4/8/12/16 supprimait les petites poses d'apparition (core loss≥15%, petites composantes≥94%) | 24poses distinctes ; C0=24slots→48phases/1,6s ; C1=18→36/1,2s (**séquence des5occurrences**) ; C2=10→20/0,666667s. 76frames produites →61 stockées :15 sorties identiques entre cycles aliasées, **aucune phase supprimée** |
| 5 / FLM2PUR | ReboutCX x4 + Apollo8 sur2variantes distinctes : palette embarquée AR1008, BMP **PLT_PURP** OH4210 ; prémultiplication unique ; inner4 uniquement pour l'embarqué (core loss0,269%, énergie9,159%) ; aucun inner pour PLT_PURP (petites composantes perdues100%) | 16poses distinctes par palette ; cycle inversé natif15..0 conservé →32phases/1,066667s par variante |
| 5 / AMWRPGT1 | Réutilisation **byte-identique** de `amwrpgt1-timeline30-apo8-safe8x6-gauss3-20260906` : SeedVR2 7B/LAB, spline fit1 safe inner8/outer6, alpha gauss3, Apollo8 ; pas de régénération | 12poses distinctes →24phases/0,8s. Déjà présents AR3003/AR3011/AR3016/AR3017, packs identiques, installation `already-installed` ; ajout sur13 autres cartes. QA antérieures AR3011/AR3016/AR3017 conservées |

## Sources / preuves ciblées

- BAM natifs immuables `animations/ressources/{AM0510A,AM3000E,FLM2PUR,AMWRPGT1}/source.bam` ; décodage `bam_export.decode_bam`, cycles `export_bam_frames.cycle_metadata`.
- Palettes : BMP1×1/8bits, table256RGB depuis override prioritaire puis BIF ; copies extraites `animations/tmp/lot45-analysis-20261011-v1/{PLT_MAGE,PLT_PURP}.bmp`, copies conservées dans le batch `palettes/`. **196 couleurs utilisées diffèrent** de l'embarqué pour AM3000E ; **247** pour FLM2PUR. Réutiliser l'embarqué sur OH4210 serait faux.
- Analyse : `analyse.py`, `animations/tmp/lot45-analysis-20261011-v1/{analysis.json,native-overview.png}` ; aucun doublon RGBA source après réalisation de chacune des palettes.
- Batch : `animations/batches/lot45-final-20261011-v1/` : `spatial-*/manifest.json`, `base-*`, `temporal-*/03_runtime_pack`, `finishing-*.json`, `feather-*.json`, `mask-AM0510A/{mask.png,comparison.png,manifest.json}`, `final-*`, `verification.json`, `baseline.json`, `area-sources.json`, `installation.json`, `preview.png`.
- Wrappers SHA256 : `animations/ressources/<REF>/runs/<ref-minuscule>-lot45-final-20261011-v1/manifest.json` ; feuilles sources exactes par carte et index final. Packs : `animations/packs-par-zone/lot45-final-20261011-v1-complete/<AREA>`.
- Commandes exécutées (depuis racine, scripts dans ce répertoire) : `python analyse.py` → `config://chainner_python spatial.py` + `python baselines.py` → `python mask.py` → `common.temporal` sur AM3000E-PLT_MAGE / FLM2PUR-embedded / FLM2PUR-PLT_PURP → `python finish.py` → `python verify.py` → `python install.py`. Sorties historiques : ne pas relancer les producteurs sur ces mêmes chemins.

## Portée runtime / installation

- Palettes externes **fixes** réalisées hors ligne, feuilles dédiées par carte, contrôle des resrefs BMP et flags dans les ARE actuels. `run_animation_upscale.py`/splitter génériques gardent leur exclusion des palettes externes ; cette recette ne prétend pas prendre en charge une palette dynamique ni modifier DLL/ARE.
- AR0510 (839,397) : AM0510A ajouté, FLAME2S/FLAME2M/FLMS acquis byte-identiques. Aperçu masque sur référence de carte : fenêtre opaque et halo fondu ; QA ingame reste nécessaire.
- AR3000 : DoorMist03/04/05/02/01 aux (396,1169)/(640,1521)/(899,1853)/(447,2006)/(194,1670), sequence1/PLT_MAGE ; autres ressources de carte byte-identiques.
- AR1008 :12 FLM2PUR embarqués ; OH4210 :1 `Purple_Flame01` externe (1522,962), PLT_PURP ; FIREBRN/FIRE_3/FIRE_4/FIRE_4GS/AM5204C acquis conservés.
- AMWRPGT1 :50 occurrences sur AR3003–AR3017 (AR3018 absent), AR3019, AR3020. Mirroring/occlusion/hauteurs/activation conservés. AR3017 `ExitPortal` (2863,1404) nativement désactivé ; activation console temporaire seulement pour QA.
- AMWRPGT1/AR3003 : liseré cyan historique attribué au raster BC1/PVRZ de **la carte**, pas au BAM. Carte inchangée ; pas de nouveau traitement alpha prétendant corriger ce défaut.
- Transaction AreaTest :21/21 feuilles vérifiées par hashes, sauvegardes/récépissés `backups/animations/area-tests`, jeu/InfinityLoader arrêtés. DLL/INI/ARE et tous les frères préservés ; lot3 exact conservé. Aucun payload/staging/TP2/manifeste release modifié.
- `CLUA.md` :69occurrences ; **`CLUA-lots3-4-5.md` :79occurrences/31cartes**, coordonnées logiques x1 + portrait0 ; commande temporaire pour les deux effets désactivés (OH5120 Fiery_Boil du lot3, AR3017 ExitPortal). QA non déduite de l'installation.

## Lot4 terminé

- **AM0510A uniquement**, arche lumineuse et halo au sol sur AR0510 (839,397) ; 18phases/30FPS, boucle0,6s.
- Ancien aperçu `preview-lot4.png` retiré avec la variante écartée ; commandes `CLUA-lot4.md` conservées.
- `C:MoveToArea("AR0510")` puis `C:Eval('JumpToPoint([839.397])',0)` ; contrôler arche, halo, disparition du rectangle statique et raccord avec la carte.
- Activation nécessaire : le script AR0510 BCS désactive AM0510A après chargement ; une fois la zone initialisée, `C:Eval('AmbientActivate("AM0510A",1)')`, fermer la console/reprendre le jeu. Le flag ARE actif ne suffit pas à prédire l'état script/sauvegarde.
- **Sélection AM0510A acceptée le 2026-10-11** : nouveau SeedVR7B LAB seed20261011/Apollo8, même masque,18phases/0,6s ; `../am0510a-seedvr7b-retest-20261011-v1/README.md`. Reçu courant `animations/batches/am0510a-seedvr7b-retest-20261011-v1/installation.json` ; QA `2026-10-11-accepted-am0510a-lot4-final-v1`. Le batch lot45 initial reste historique, sorties de l'ancien portail retirées.
