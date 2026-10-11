# Lots4/5 — traitement et installation, 2026-10-11

État courant : **lots4/5 acceptés ingame et terminés**. Lot4 : AM0510A nouvel essai SeedVR7B seed20261011 retenu. Lot5 : **3assets/4variantes/20cartes/68occurrences**, acceptation utilisateur « ok je valide tout le lot. maj le suivi et committe. ». Rapport courant `../lot5-acceptance-20261011-v1/acceptance.json` ; sélections `animations/index/selections/{AM3000E,FLM2PUR,AMWRPGT1}.json`, CSV `validé-x4`. Release non sélectionnée. Lot3 accepté séparément (AM0902L SeedVR retenu). Détails lot4/retrait : `../am0510a-seedvr7b-retest-20261011-v1/README.md` et `acceptance.json`.

Index initial lot5 : `animations/packs-par-zone/lot5-current-20261011-v1` ;17feuilles AMWRPGT1 toujours courantes, AR1008 embarqué conservé à l'identique ; AR3000/OH4210 historiques depuis les corrections de contour. Aperçu initial et commandes : `animations/batches/lot5-current-20261011-v1/{preview-lot5.png,CLUA.md}`. Sorties/aperçus AM0510A écartés et ancien index complete21cartes supprimés ; confirmation explicite pour le dossier partagé : « Oui, supprimer ce pack partagé ». Métadonnées historiques immuables ; ne pas rejouer les producteurs sur ces IDs.

AM3000E retenu : pack `animations/packs-par-zone/am3000e-contour-native-20261011-v2/AR3000`, lissage sigma2x4 + fade canvas2px, dimensions/centres natifs exacts,5occurrences ; `../am3000e-contour-native-20261011-v2/README.md`. QA immuable `2026-10-11-accepted-am3000e-native-contour-v1` conservée. Essai soft2 v1 avec padding incompatible écarté après fallback vanilla ; reçus historiques conservés.

FLM2PUR retenu : famille `animations/packs-par-zone/flm2pur-palette-selection-soft2-20261011-v1`, AR1008 embarqué/inner4 inchangé, OH4210 PLT_PURP **soft2 de droite**, sigma2x4/étincelles protégées/canvas1px ;32phases/1,066667s par variante. QA `2026-10-11-accepted-flm2pur-lot5-final-v1`, reçu batch `flm2pur-oh4210-contour-20261011-v1/installation.json` ; `../flm2pur-oh4210-contour-20261011-v1/README.md`.

AMWRPGT1 retenu : SeedVR2 7B/LAB + Apollo8, safe inner8/outer6/gauss3 existant byte-identique,17cartes/50occurrences ; QA `2026-10-11-accepted-amwrpgt1-lot5-final-v1`, QA antérieures AR3011/AR3016/AR3017 conservées. Contrôle final :20payloads installés/signatures de verrou conformes, lineage des3sélections conforme, durées natives conservées.

Les rubriques de production/installation ci-dessous décrivent aussi l'état initial historique ; certains chemins AM0510A et l'ancien index complete ont été retirés. Les sélections et recettes finales ci-dessus font autorité.

| Lot / asset | Recette finale | Durées / déduplication |
|---|---|---|
| 4 / AM0510A | Nouvel essai SeedVR2 7B INT8/LAB x4 seed20261011 + Apollo8 ; masque retenu : arche/aperture opaque, halo au sol pondéré par variation lumineuse native, fondu extérieur8px x4, fade canvas12 | 9poses distinctes →18phases ; 0,6s ; rectangle statique retiré |
| 5 / AM3000E | Palette BMP **PLT_MAGE réalisée avant ReboutCX** ; Apollo8 ; contour RGBA prémultiplié sigma2x4/cœur préservé + fade canvas2px, géométrie native exacte. Aucun inner érosif | 24poses distinctes ; C0=24slots→48phases/1,6s ; C1=18→36/1,2s (**séquence des5occurrences**) ; C2=10→20/0,666667s. 76frames produites →61 stockées :15 sorties identiques entre cycles aliasées, **aucune phase supprimée** |
| 5 / FLM2PUR | ReboutCX x4 + Apollo8 ; embarqué AR1008/inner4 conservé ; BMP **PLT_PURP** OH4210/contour sigma2x4, étincelles≤48px filtrées séparément sigma0,8/flux préservé, canvas1px ; prémultiplication unique, géométrie native exacte | 16poses distinctes par palette ; cycle inversé natif15..0 conservé →32phases/1,066667s par variante |
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
- AR0510 (839,397) : AM0510A ajouté, FLAME2S/FLAME2M/FLMS acquis byte-identiques. Version SeedVR seed20261011 acceptée ingame ; fenêtre opaque et halo fondu.
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
