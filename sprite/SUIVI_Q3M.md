# Suivi sprites Q3m — 2026-10-04

## Portée / méthode

- Familles = `engine_section` des INI, autorité `index/family-groups.csv` ; 15 profils personnages/créatures. `effect` et IDs sans INI : hors queue, conservés dans l'inventaire source.
- Personnages jouables, compagnons, PNJ, monstres, animaux et figurants inclus ; un PNJ utilisant `character` appartient au même profil que les jouables.
- Nouvelle méthode créatures : **Q3m K6, quatre partenaires / huit niveaux, V7 x2** ; indices + B/F + dépendances, palette native vivante. Classes et partenaires propres au profil fixe/rampes ; owner exact par famille. Character acquis : V6 profile1/rule1 ; l'essai contour V10 conserve ses couleurs, sans conversion V7.
- Monde installé : **x2 + CatmullRom global**, réactivé à la demande utilisateur. BOX = contrat initial des lots Ogre/Flying ; QA Flying conservée avec ce contrat historique. Paperdolls : voie UI distincte ; acquis `6110` conservés.
- xBR final / ReboutCX première génération : **historique, exclus de l'avancement Q3m**. Sources, runs et QA historiques préservés ; aucun déplacement/suppression. xBR comme guide et ReboutCX comme producteur de cibles restent des briques de Q3m.
- Pilote quatre partenaires : **15 témoins / 49 BAM / 11 586 frames**, actions retenues uniquement, tests hôte acquis ; historique du pilote préservé. Décisions QA des familles complètes ci-dessous. `../docs/measurements/q3m-families-engine-x2-20261003-v2/current-generation.json` ; contrat `../pipeline/PALETTE_Q3M_V7.md`.
- Première famille complète V7 : **`monster_large` / ogre `0x9000` / 7 BAM / 434 frames**, produite et installée ; **QA ingame en attente**. `../docs/measurements/q3m-monster-large-full-x2-20261003-v1/current-generation.json` ; faits d'installation `installation-verification.json` du même run.
- Deuxième famille complète V7 : **`flying` / 5 IDs / 4 BAM / 243 frames**, produite, installée et **famille validée par l'utilisateur**. `../docs/measurements/q3m-flying-full-x2-20261003-v1/current-generation.json` ; QA `index/qa-decisions/flying/2026-10-03-accepted-full-flying-q3m-v7-k6-x2-box-v1.json` ; le comparatif et les faits d'installation restent des états historiques distincts.
- Troisième famille complète : **`monster_ankheg` / `0x3000` / 12 BAM / 516 frames** ; couleurs V7 acquises, corps/terre, toutes actions/directions et enfouissement/émergence. Variante actuellement installée et **validée ingame : V9 SDF + attente des métadonnées HD**, `../docs/measurements/q3m-ankheg-sdf-stable-ingame-x2-20261004-v1/current-generation.json`. QA immuable `index/qa-decisions/monster_ankheg/2026-10-04-accepted-full-ankheg-q3m-v9-sdf-stable-x2-catmullrom-v1.json`. Le lot V7 sans contour garde sa QA distincte, en attente.
- Quatrième famille complète disponible : **`monster_large16` / trois IDs A000/A100/A200 / deux modèles, trois contrats couleur / V7 x2 sans SDF**, produite, installée et **validée ingame par l'utilisateur**. Source native : 12 BAM monde + un INV auxiliaire / 1 114 frames originales ; 20 feuilles / 1 692 frames avec palette blanche native `MWYV_WS`. A201/A202 sans BAM déclarés ; douze BAM partagés Quadrant hors appels Large16 exclus. `../docs/measurements/q3m-monster-large16-full-x2-20261004-v1/README.md`.
- Cinquième famille complète : **`ambient_static` / 13 IDs / 13 modèles / 26 BAM / 1 144 frames / V7 x2 couleurs améliorées sans SDF**, installée et **validée ingame**, cheval corrigé v3 inclus. QA immuable `index/qa-decisions/ambient_static/2026-10-04-accepted-full-ambient-static-horse-eye-v3-q3m-v7-x2-catmullrom-v1.json` ; production initiale +remplacement cheval requis, catalogue actif `211edfd2…d2c55`.
- Essai Spline Fit 1 Ankheg **rejeté ingame** : pixels flottants isolés sur le contour ; catalogue/DLL parent restaurés avant nouvel essai. Décision immuable `index/qa-decisions/monster_ankheg/2026-10-04-rejected-spline-fit1-q3m-x2-catmullrom-v1.json` ; preuves de production/test spline conservées.
- Essai **historique, remplacé par SDF** : alpha léger gaussien σ 0,65 px x2 / intensité 0,8 / minimum 176 sur 255 / V8 alpha8, bande intérieure 2 px ; escaliers encore trop visibles selon le retour utilisateur. Couleurs V7 conservées ; 431 masques uniques / 85 réutilisations / 494 frames modifiées / 22 identiques / 0 pixel effacé. `../docs/measurements/q3m-ankheg-alpha-light-x2-20261004-v1/current-generation.json` ; aucun verdict QA accepté déduit.
- **En stock, non installé** : guerrière humaine sans équipement `0x6110 CHFB1`, même contour SDF, V10 dérivé du V6 Character ; 23 BAM / 10 323 frames / 2 388 masques uniques / 7 935 réutilisations / 0 inférence / 0 encodage Q3m. Décision explicite utilisateur, **QA visuelle en attente** : `../docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/stock-decision.json`. Code, assets locaux, comparaison PNG et preuves gardés ; DLL/catalogue/trois shaders Ankheg stable restaurés et vérifiés (`restoration-verification.json`). Aucun équipement/paperdoll ni autre avatar modifié.
- Comparaison initiale et 16 niveaux : diagnostics préservés, sans promotion du candidat 16 niveaux. `../docs/measurements/q3m4partners-colour-comparison-x4-20261003-v1/README.md`.
- Intégration nouveau moteur sprite : **90 %**, estimation utilisateur du 2026-10-03 ; ne mesure ni couverture des assets ni QA.

- Gros sprites divisés en tuiles : **méthode contextuelle systématique**, assemblage avant RGB-fill/inférence K6, correction limitée aux bandes4px natifs ; [pipeline/cache/commandes](../pipeline/SPRITES_Q3M_MULTIPART.md).

## Inventaire des familles

`Stock` = IDs avec au moins un BAM / IDs définis ; `Q3m connu` = références **V6 antérieures**, pas couverture du nouveau contrat V7. Les sous-types restent dans `index/q3m-work-items.csv` (`animation_type`, INI source). Chaque famille a un témoin V7, listé dans `index/q3m-family-witnesses.json` ; les témoins restent partiels. Le lot complet Ogre possède une référence distincte.

| Profil | Stock | Q3m connu | Intégration / exemples |
|---|---:|---:|---|
| `character` | 78/78 | 78 | Corps/armures + armes/casques/boucliers ; palettes par couche. Variantes LOW `5000` et standard `6000`. Jouables, compagnons, PNJ partageant ces avatars. |
| `character_old` | 7/8 | 7 | **Famille disponible complète validée**, Q3m x2 palette améliorée/CatmullRom ; cinq IDs V7 sans SDF +gardes6405/6406 V9 SDF. 1 066 BAM natifs/2 018 feuilles variantes installées ; corps des gardes natifs transparents, XHFF6621 absent. |
| `monster` | 77/102 | 3 | Monstres BG2, BAM éventuellement divisés ; palette fixe/false-color à résoudre par ID. Spectateurs, Bodhi, golems, trolls. |
| `monster_old` | 46/54 | — | **Famille disponible complète installée, QA en attente**, Q3m V7 K6 x2 amélioré sans SDF ;18 modèles/46 variantes natives,79 BAM/217 feuilles/17 752 frames physiques (218 liaisons/17 754 frames liées). Huit IDs sans source. |
| `monster_icewind` | 44/132 | — | Séquences de style IWD ; contrat palette propre à l'animation. Orcs, gobelins, ettins, liches. |
| `monster_quadrant` | 7/9 | — | **Famille disponible complète Q3m V7 x2 contextuel palette améliorée sans SDF installée et validée ingame** ; deux modèles/sept palettes, 36 BAM natifs/132 feuilles/12 928 frames ; quadrants vides préservés, MWDR1101/1105 sans source. |
| `multi_new` | 10/10 | — | **Complète installée, QA en attente** : neuf dragons (trois modèles, sept palettes MDR1) et Démogorgon ; Q3m K6 x2 amélioré, raccords contextuels quatre/neuf parties, sans SDF. |
| `monster_layered` | 7/7 | — | **Famille complète Q3m V7 x2 palette améliorée sans SDF installée et validée ingame** ; 65 BAM utiles/6 422 frames, sept modèles, corps/armes, deux chemins natifs. MSIRG2BE orphelin exclu. |
| `monster_ankheg` | 1/1 | — | Ankheg ; **famille complète V9 SDF x2 + attente HD installée et validée**, 12 BAM / 516 frames ; couleurs V7, corps/terre et enfouissement/émergence. |
| `monster_large` | 1/1 | — | Ogre ; **famille complète V7 x2 installée**, 7 BAM / 434 frames ; QA ingame en attente. |
| `monster_large16` | 3/5 | — | Wyverne, charognard rampant, wyverne blanche ; **famille disponible complète V7 x2 sans SDF installée**, 20 feuilles / 1 692 frames, palette blanche native ; **validée ingame**. Deux IDs sans BAM. |
| `ambient` | 18/21 | — | **Famille disponible complète Q3m V7 x2 améliorée sans SDF installée et validée**, 18 IDs/16 modèles/34 BAM/2 580 frames. KEG1/2/3 sans BAM. |
| `ambient_static` | 13/13 | — | **Famille complète V7 x2 couleurs améliorées sans SDF installée et validée**, cheval œil v3 inclus ; 13 modèles/26 BAM/1 144 frames. |
| `town_static` | 18/19 | — | **Famille disponible complète Q3m V7 x2 améliorée sans SDF installée et validée**, 18 modèles/18 BAM/1 543 frames. NULL_ANIMATION/SNONE sans BAM. |
| `flying` | 5/5 | — | Aigle, mouette, vautour, petit oiseau ; **famille complète V7 x2 installée et validée**, 4 BAM / 243 frames ; intérieur/extérieur partagent une ressource. |

## Queue / références

- `index/q3m-work-tracking.json` : décisions de méthode, estimation moteur, familles et références ; **plan**, aucune autorité supplémentaire sur les états métier.
- `index/q3m-work-items.csv` : 465 IDs, dont 335 avec BAM et 130 sans BAM. Une ligne par animation ; composants/équipement reliés par `family_ids`. `q3m-reference-available` / `to-produce-or-extend-profile` / `source-absent` = état de queue, pas validation.
- Historique V6 : 81 IDs avec référence Q3m ; 254 IDs avec BAM sans référence V6 inscrite. Nouvelle recette : **15 IDs témoins partiels, 136 IDs /12 familles disponibles complètes installées ; 79 IDs /9 familles validées (`flying`, `monster_ankheg` V9 stable, `monster_large16` V7 sans SDF, `ambient_static` V7 sans SDF +cheval œil v3, `town_static` V7 sans SDF, `ambient` V7 sans SDF, `character_old` V7/V9 SDF gardes seulement, `monster_layered` V7 sans SDF, `monster_quadrant` V7 contextuel sans SDF)** ; colonnes `q3m_v7_witness_*`, `q3m_v7_full_production_reference`, `q3m_v7_installation_reference` du CSV. QA propre à chaque variante/runtime. Ogre reste QA en attente ; V10 Character en stock exclu de l'installation et des validations. Pas de taux global à partir des frames/BAM partagés.
- Character : `../docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json` ; 78 IDs / 4 510 BAM.
- Monster `0x7F02`, `0x7F07`, `0x7F30` : `../docs/measurements/q3m-monster-integration-x2-20261003-v1/current-generation.json` ; delta 39 BAM / 20 925 frames, catalogue mixte prêt à installer selon son pointeur. Cela ne prouve pas l'installation actuelle.
- QA = `index/qa-decisions/` ; installation = reçu actif du run concerné ; release = candidats puis `content.json`. Références indépendantes, aucun état réconcilié dans cette queue.
- Paperdolls `6110` : 81 BAM / 163 frames acceptés ; autres avatars UI non couverts par cet acquis. Suivi UI séparé dans le JSON.
- Mise à jour : modifier uniquement la queue et ses références pour le lot demandé ; nouvelle référence pour un nouveau contrat couleur. Ne pas transformer une ancienne QA en QA du nouveau contrat.

## Travail réel / doublons exacts

- Plan source global : `index/q3m-source-work-plan.json` → `../docs/measurements/all-creature-source-dedup-20261003-v1/README.md` ; Character acquis lu sans reconstruction, 14 autres profils analysés.
- Hors Character : **699 374 frames / 4 014 BAM → 194 573 travaux source**, 504 801 répétitions physiques évitées. 5 travaux source communs avec Character ; contrat couleur distinct ≠ hit Q3m.
- Queue CSV enrichie : `dedup_unique_source_work`, `dedup_unique_model_candidate_work`, `dedup_source_work_shared_with_character`, `dedup_source_plan`. Compteurs par ID non additifs ; sélectionner l'union des clés pour connaître un lot réel.
- Q3m Monster connu : reprise vérifiée **3 190/3 190 hits**, aucun processeur/GPU/Torch, payloads inchangés. Character/Monster et leurs producteurs acquis inchangés.
- Garantie locale : produire une seule fois chaque clé finale compatible ; namespace profil/recette/échelle + clé pixel, cache persistant validé et verrouillé. Centres/cycles/calques restent hors clé pixel, stockés par occurrence.
- Contrat quatre partenaires défini et testé : V7 fixe/rampes ; **2 730 sources → 2 731 encodages compatibles** pour le pilote. Une source spéciale a deux contrats ; 54 variantes de métadonnées inutiles partagent les mêmes octets. Reprise 2 731/2 731 hits sans import Torch. Centres/cycles restent par occurrence.
- Ogre complet : **434 clés compatibles = 136 hits du témoin + 298 nouveaux encodages** ; 1 788 nouvelles cibles K6. Reprise 434/434 hits sans import Torch ; les 22 CRE partagent cette production, sans traitement par individu. `../docs/measurements/q3m-monster-large-full-x2-20261003-v1/production.json`.
- Flying complet : **243 clés compatibles = 39 hits acquis + 204 nouveaux encodages** ; 1 224 nouvelles cibles K6. Reprise 243/243 hits sans import Torch ; `D300/D400` partagent le composant `ABIRG1`, les frames et la feuille physique ; quatre échantillons acceptés inchangés. `../docs/measurements/q3m-flying-full-x2-20261003-v1/production.json`.
- Ankheg complet : **516 frames → 431 sources / 432 contrats compatibles = 143 hits du témoin + 288 nouveaux encodages + 1 encodage spécial sans GPU** ; 1 728 nouvelles cibles K6. Reprise 432/432 hits sans import Torch ; 143 encodages acquis inchangés. Deux CRE, un seul modèle : `C:CreateCreature("ANKHEG01")`. `../docs/measurements/q3m-monster-ankheg-full-x2-20261003-v1/production.json`.
- Large16 complet disponible : **1 114 frames BAM originales → 1 053 sources**, avec palette blanche native **1 567 sources couleur / 1 570 contrats = 176 hits acquis + 1 388 nouveaux encodages + six spéciaux sans GPU** ; 8 328 nouvelles cibles. Reprise 1 570/1 570 hits sans Torch. Douze BAM Quadrant partagés exclus ; `../docs/measurements/q3m-monster-large16-full-x2-20261004-v1/production.json`.
- Coût du reste des 335 animations avec BAM : `null` tant que la sélection exacte et son union de clés finale ne sont pas calculées ; ne pas additionner les compteurs par famille.
- Sélection CPU : `pipeline/scripts/analyze_sprite_frame_dedup.py plan --animation-id <ID> [...]`. Pas d'inférence indépendante par famille ni addition des compteurs partagés.

## Mémoire du chat : décisions / preuves

Préfixe des runs ci-dessous : `../docs/measurements/`. Les instantanés scellés restent historiques ; les décisions QA et reçus actifs font autorité séparément.

| Étape | Résultat / référence | Commit déjà acquis |
|---|---|---|
| Nouvelle queue | 15 familles natives ; xBR/ReboutCX première version exclus des compteurs ; moteur 90 % = estimation utilisateur | `221a708d` |
| Doublons globaux | `all-creature-source-dedup-20261003-v1/summary.json` ; 212 BAM identiques décodés une fois ; hors Character 194 573 travaux source / 194 158 candidats modèle ; total source avec Character 758 537 uniques / 2 263 428 frames physiques | `753be430` |
| Un témoin par famille + moteur | `q3m-families-engine-x2-20261003-v2/current-generation.json` ; 15 profils, 49 BAM, 11 586 frames, 2 731 encodages compatibles ; scopes/owners natifs, palettes live, composites, géométrie/cycles ; pilote ≠ famille entièrement traitée | `1fbb3574` |
| Ogre complet | `q3m-monster-large-full-x2-20261003-v1/` ; unique profil `monster_large`, modèle partagé par 22 CRE ; 7 BAM / 434 frames ; installé, QA en attente ; `CLUA.txt` recense les consommateurs | `4442c265` |
| Flying x2/x4 puis complet | `q3m-flying-frame-x2-x4-20261003-v1/comparatif-oiseaux-q3m-x2-x4.png` : une frame par modèle, PNG sans perte ; x2 choisi, famille complète ensuite validée ; 4 modèles pour 5 IDs, `D300/D400` partagent `ABIRG1` | `b8c21595` |
| Ankheg + Spline Fit 1 + alpha léger | `q3m-monster-ankheg-full-x2-20261003-v1/`, `q3m-ankheg-spline-fit1-x2-20261003-v1/`, `q3m-ankheg-alpha-light-x2-20261004-v1/` ; famille complète 1 ID, CatmullRom réactivé ; spline rejetée (pixels flottants), alpha léger insuffisant (escaliers) | `552254c3` |
| Simulation SDF hors jeu | `q3m-ankheg-sdf-offline-x2-20261004-v1/` ; comparaison de poses, zooms, détails, séquences ; PDF 5 pages `../output/pdf/ankheg-contour-sdf-comparatif-20261004-v1.pdf`, identité dans `pdf.json` | `552254c3` |
| SDF V9 ingame | `q3m-ankheg-sdf-ingame-x2-20261004-v1/` ; 12 BAM / 516 frames ; couleurs inchangées, 431 masques / 85 hits, 0 nouveau Q3m ; rendu apprécié, retours temporaires x1 constatés | `a46a319a` |
| Diagnostic + stabilité validée | `q3m-ankheg-sdf-stability-analysis-20261004-v1/` → `q3m-ankheg-sdf-stable-ingame-x2-20261004-v1/` ; retard du chargement initial confirmé ; attente HD owner9/id3000 ; DLL seule remplacée ; utilisateur « validé, committe » | `16b01e52` |
| Large16 complet sans SDF | `q3m-monster-large16-full-x2-20261004-v1/` ; natif owner11, trois IDs disponibles, 20 feuilles / 1 692 frames ; palette blanche réelle, installé, validé ingame | commit du lot Large16 |
| Character CHFB1 SDF en réserve | `q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/` ; V10 + ombres Character128, palette V6 intacte ; preuves natives/GPU et comparaison ; essai installé puis retiré à la demande utilisateur ; **en stock, QA en attente** | présent commit |

`Famille` = profil d'intégration native ; `modèle` = ensemble de BAM physiques ; `CRE` = consommateur. Tester une fois chaque modèle ; variantes de CRE appelant les mêmes ressources ne créent aucun travail sprite supplémentaire. Choix CLUA vérifiés :

```lua
C:CreateCreature("OGRE01")
C:CreateCreature("EAGLE")
C:CreateCreature("SEAGUL")
C:CreateCreature("VULTURE")
C:CreateCreature("BIRD")
C:CreateCreature("ANKHEG01")
C:CreateCreature("WYVBAB01")
C:CreateCreature("CARCRA01")
C:CreateCreature("QMWYVW01") -- témoin blanc ajouté, même CRE source sauf ID animation A200
```

Flying : alias intérieur `BIRD_IN` = même ressource ; listes `CLUA-generiques.txt` / `CLUA.txt` dans le run complet. Ankheg : deux CRE, un modèle. Ogre : 22 CRE, un modèle. Character : sélectionner la guerrière humaine existante, corps `CHFB1` sans armure/arme/bouclier/casque ; aucun changement automatique de sauvegarde.

## Contour SDF : contrat conservé

- Recette retenue Ankheg : distance signée lissée et bornée, σ=2 px x2, biais ≤1 px x2 ; noyau fin rayon2/voisinage3 ; topologie foreground8/background4 conservée ; pad6 ; distance quantifiée 1/16 px x2 ; couverture **8×8 échantillons par pixel écran**, couleur CatmullRom 16 taps prémultipliée. Ombres natives séparées ; palette live. Références : `q3m-ankheg-sdf-offline-x2-20261004-v1/sdf_trial.py`, `pipeline/scripts/sprite_sdf_registry.py`, shaders monde.
- V9 : V7 + plans S (distance) / M (référence au matériau natif) ; pas de raster couleur figé ni de nouveau modèle neural. Contrat Ankheg profile8/rule3 ; ombre127. Assemblage corps/terre conserve les deux draws natifs.
- Instabilité : session 2026-10-04 01:32:17–01:33:02 ; `MAKHDG1E` non résolu à 01:32:30.894, terre prête +9 ms / corps +39 ms, deux draws HD à 01:32:31.031. Aucune preuve d'éviction ; avertissement émis une seule fois/processus, pas de comptage exhaustif des frames x1. Cause confirmée : lecture NonBlocking au premier resref ; logs complets/extrait et sonde dans le run d'analyse.
- Correctif installé/validé : lecteur commun capture/draw `WaitForAnkhegMetadata`, catalogue V2 / owner9 / ID3000 ; attente existante ≤5 s, worker/payloads paresseux/authentification/quarantaine/fallback sur erreur conservés. Sonde finale : **12/12 premiers accès HD, 0 miss, attente max69,013 ms**, 516 frames / 1 485 slots / 48 compositions vérifiés. Mesure hôte, pas promesse de latence. Character owner1 possède déjà son attente ; Large16 et les autres familles restent NonBlocking ; l’attente propre à l’essai Large16 a été retirée avec sa DLL. Généralisation par contrat natif, jamais par seule présence d'un contour.
- Extension **Character V10 en stock** : V6 x2 profile1/rule1 + S/M ; I/F compressés, deps, représentants, géométrie/cycles conservés ; retirer les seules données SDF restitue les 23 feuilles V6 octet pour octet. `pipeline/scripts/character_sdf_registry.py` ; parser/plafonds/authentification natifs conservés.
- CHFB1 partagé par six IDs : ajout de 23 composants/feuilles, remplacement des seules routes `0x6110.CHFB1` ; **50 230 routes hors périmètre identiques**. 23 BAM / 10 323 frames / 24 868 slots. Armour `CHFB2/3`, `CHFF4`, équipements/paperdolls et cinq autres avatars restent sur leurs acquis.
- Métadonnée SDF `0=ordinaire / 1=ombre127 / 2=Character ombre128` ; uniforme `uIeeCreatureSdfCharacter` requis pour mode2 et remis à zéro sur les autres draws. Composite SDF uniquement si toutes les couches ont SDF et le même mode ; équipement sans SDF + corps SDF revient au fallback natif. Ce test couvre le corps sans équipement.
- Preuves Character : 23/23 chargements HD à froid, 0 miss, attente max84,8784 ms ; toutes frames/cycles ×6 palettes ×3 formats ; suite core/mode2 ; trois registres malformés rejetés. GPU : 24 vues/four zooms, trois shaders compilés ; **18 draws ordinaires et neuf draws Ankheg V9 identiques** au moteur `16b01e52`. `verification.json`, `gpu-verification.json`, `comparatif-chfb1-sdf.png` ; aucune QA ingame déduite.

## État installé / réserve après ce chat

- **Actif : Ankheg SDF stable validé**, DLL stable **`0bdaf3b6…e4d5`**, catalogue Ambient_static V7 sans SDF validé **`211edfd2…d2c55`**, trois shaders du runtime validé. Reçu stable conservé ; vérification de restauration du test Character : `../docs/measurements/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/restoration-verification.json` (**5 fichiers restaurés +95 préservés**, INI/exécutable/81 packs UI/12 feuilles Ankheg inchangés). Catalogue parent de la restauration Character historiquement exact ; routes Character préservées dans le nouveau catalogue Large16 ⇒ CHFB1 V6 actif ; feuilles V10 résiduelles non référencées.
- **Réserve : Character SDF V10**, DLL `3636ba3a…67e2`, catalogue `a13177c3…0eb`, 23 nouvelles feuilles + trois shaders ; code/protocole/scripts/preuves versionnés, build et pack locaux conservés. Identités complètes : `stock-decision.json`, `runtime.json`, `current-generation.json`. Assets locaux : `sprite/.work/q3m-6110-chfb1-sdf-ingame-x2-20261004-v1/{isolated,combined}` ; DLL : `engine/InfinityEngine-Enhancer/source-patchee/build-q3m-character-sdf-20261004-v1/Release/InfinityEngine-Enhancer.dll`. `.work` reste un cache ; solution reproductible par sources/recette, vérifier sa présence et ses SHA avant réemploi.
- Retrait déjà effectué par `restore.ps1` du test Character ; `stock.py` a scellé la décision et vérifié la restauration/les 23 feuilles conservées. `installation-verification.json` historique garde l'installation d'essai initiale ; le reçu local porte `restored-parent`. **Ne pas rejouer `install.ps1`, `track.py`, `produce.py`, `verify.py` dans ce run scellé** ; futur réemploi = demande explicite + nouveau run/reçu, jeu/InfinityLoader fermés.
- Source du dépôt contient V10 ; installation active reste le runtime stable antérieur. Ne pas inférer l'installation depuis HEAD ni la QA depuis les tests natifs/GPU. Release/payload/staging/TP2/content/manifeste inchangés.

- Installation Large16 actuelle : `../docs/measurements/q3m-monster-large16-full-x2-20261004-v1/installation-verification.json` ; 20 nouvelles feuilles V7 sans SDF + CRE témoin blanc, **99 fichiers préservés**, 88 IDs/50 253 routes hérités identiques ; catalogue actif 91 IDs/4 592 ressources. QA V7 Large16 acceptée : `index/qa-decisions/monster_large16/2026-10-04-accepted-full-available-large16-q3m-v7-x2-catmullrom-v1.json` ; un essai SDF conserve une QA distincte.

## Large16 : essai SDF rejeté, V7 validé restauré

- **V7 sans SDF accepté, commit `9856d78d`** ; QA conservée, trois familles/neuf IDs acceptés.
- **Historique Large16 : essai V9 SDF x2 rejeté et retiré**, `../docs/measurements/q3m-large16-sdf-ingame-x2-20261004-v1/README.md` ; trois IDs, 18 BAM monde/1 688 frames, deux INV/four frames V7 conservés. Couleurs I/F/deps/profil restaurables V7 byte-identiques.
- 1 508 masques uniques /180 hits /zéro inférence ou encodage Q3m ; sonde native complète/GPU24vues ; 18/18 premiers accès HD sans miss, attente max96,0796ms.
- DLL base `16b01e52` + attente Large16 owner11/IDs exacts≤5s ; Character V10 en stock non activé. Shaders/INI/exe/UI/Ankheg/CREblanc/V7 acquis :119fichiers identiques ; toutes50 273routes conservées. Installation et QA restent distinctes.
- Restore de cet essai → V7 validé, même CREblanc. Mêmes CLUA WYVBAB01/CARCRA01/QMWYVW01 ; gameplay/rotations/mort à tester ingame.

- Décision finale utilisateur : **Large16 complet disponible Q3m V7 x2 sans SDF validé et actif**. SDF « beaucoup trop lisse », rejet `sprite/index/qa-decisions/monster_large16/2026-10-04-rejected-full-large16-q3m-v9-sdf-x2-catmullrom-v1.json` ; `../docs/measurements/q3m-large16-sdf-ingame-x2-20261004-v1/restoration-verification.json` : DLL/catalogue parent exacts, vingt feuilles V7/1 692frames vérifiées, 119fichiers préservés. Ankheg SDF stable conservé, Character SDF en stock. Delta source attente Large16 annulé ; scripts/patch/build/essai historiques conservés, aucun asset acquis retraité.

## Ambient_static complet installé — 2026-10-04

- Cinquième famille complète : 13 IDs/13 modèles/26 BAM/1 144 frames ; Q3m V7 K6 x2 couleurs améliorées, sans SDF ; palettes fixes/rampes natives live, CatmullRom conservé. Aucun BAM absent.
- 1 064 encodages compatibles = 44 hits acquis + 1 020 nouveaux ; 6 120 cibles ; 80 doublons partiels mendiant/esclave, aucun modèle entièrement identique. Reprise 1 064 hits sans Torch.
- Native isolé/combiné K6 ×3 formats accepté ; 91 IDs/50 273 routes hérités et 120 fichiers préservés. Actif 104 IDs/4 618 ressources/50 299 routes. Cinq CRE témoins pour les IDs sans consommateur stock ; liste 13 modèles : `../docs/measurements/q3m-ambient-static-full-x2-20261004-v1/CLUA-generiques.txt`.
- Production/installation : `../docs/measurements/q3m-ambient-static-full-x2-20261004-v1/current-generation.json`, `installation-verification.json` ; QA ingame en attente, aucune release. Totaux recette : cinq familles/23 IDs complets installés ; QA acquises inchangées, trois familles/neuf IDs.

## Ambient_static : 12 modèles validés, œil du cheval corrigé — 2026-10-04

- Validation explicite utilisateur des 12 modèles hors B100 : 24 BAM/1 100 frames ; QA immuable `index/qa-decisions/ambient_static/2026-10-04-accepted-12-models-except-horse-q3m-v7-x2-catmullrom-v1.json`. Trois familles entièrement validées/21 IDs validés au total ; ambient_static reste partielle en QA.
- Cheval B100 : œil natif sombre atténué ; correction locale sans SDF I natif/F0 sur 48 pixels x2/dix frames, 34 frames inchangées ; zéro nouvelle inférence. Deux nouvelles feuilles installées ; 24 feuilles acceptées et 4 616 autres feuilles/composants préservés ; 149 fichiers SHA identiques, mêmes DLL/shaders/INI/CRE.
- Nouveau run `../docs/measurements/q3m-horse-eye-x2-20261004-v1/current-generation.json` ; `installation-verification.json`, `comparison.png`, restore dédié ; QA du cheval corrigé en attente. Aucun ancien asset/cache/run/QA final réécrit ; aucune release.

## Cheval : pose non couverte / candidat œil local v3 — 2026-10-04

- Retour utilisateur : œil toujours atténué sur la capture `20261004131339_1.jpg`. Pose AHRSG1 frames0–3, absente du premier correctif (frames11–15). Cible neurale : contraste39,939→26,809 sur f0/K0, avant encodage Q3m.
- Analyse/candidat : `../docs/measurements/q3m-horse-eye-directions-20261004-v3/README.md` ; 44 frames examinées, 16 frames de repos/32 présentations direct-miroir ; ellipse locale suivant l'iris natif sur AHRSG1 frames0–4, 134 pixels x2 I/F ; 39 frames inchangées, premier correctif de profil conservé.
- Q3m V7 K6 x2 amélioré sans SDF ; 1 440 cas filtrés sur la zone corrigée, aucun contraste inférieur à l'original ; native deux BAM/44 frames/878 slots accepté ; 3 072 comparaisons miroir égales. Aucun changement des 12 modèles acceptés, aucune nouvelle inférence.
- **Candidat non installé, QA ingame en attente** : `sprite/.work/q3m-horse-eye-directions-20261004-v3/candidate/` ; installation précédente/catalogue actif et 149 fichiers vérifiés inchangés. `candidate.json`, `verification.json`, comparatif `capture-pose-comparison.png`. Aucune release ; état production/installation actif conservé.

## Cheval : candidat œil v3 installé — 2026-10-04

- Utilisateur approuve le comparatif et demande l'installation ; **QA ingame en attente**. Nouveau run `../docs/measurements/q3m-horse-eye-ingame-x2-20261004-v1/README.md` ; candidat d'analyse v3 conservé immuable.
- Une nouvelle feuille AHRSG1 publiée +catalogue `211edfd2…d2c55` ; AHRSG1E déjà identique ; cinq frames/134 pixels x2 corrigés, premier correctif de profil conservé. Q3m V7 x2 amélioré sans SDF ; aucun nouvel upscale, DLL/shaders/INI/CRE inchangés.
- `installation-verification.json` : 150 fichiers préservés SHA ; 104 IDs/50 299 routes et 4 617 autres composants/feuilles identiques ; native deux BAM/44 frames/878 slots accepté. 12 modèles acceptés hors cheval conservés.
- Reçu `ingame-installation/active-test.json`, restore dédié vers le correctif précédent ; `C:CreateCreature("HORSE")`. Aucune release.

## Ambient_static : famille complète validée — 2026-10-04

- Utilisateur : « parfait famille validée ! » ; **13 IDs/13 modèles/26 BAM/1 144 frames acceptés ingame**, Q3m V7 K6 x2 amélioré sans SDF, CatmullRom, cheval v3 inclus.
- QA immuable `index/qa-decisions/ambient_static/2026-10-04-accepted-full-ambient-static-horse-eye-v3-q3m-v7-x2-catmullrom-v1.json` : exactes 26 feuilles installées et contrat runtime/DLL/INI/shaders ; 24 feuilles précédemment acceptées conservées. Production initiale **avec remplacement cheval requis**, aucune validation rétroactive du cheval initial/premier correctif.
- Installation active : `../docs/measurements/q3m-horse-eye-ingame-x2-20261004-v1/current-generation.json`, catalogue `211edfd2…d2c55` ; preuve d'installation historique non réécrite. Les mentions QA en attente des essais ci-dessus restent historiques.
- Totaux recette : cinq familles/23 IDs installés, quatre familles/22 IDs validés ; Ogre installé, QA encore en attente. Aucune release.
- Prochain lot proposé seulement : `town_static`, 18 modèles/18 BAM/1 543 frames →1 542 travaux uniques, huit hits compatibles →1 534 nouveaux encodages ; aucun traitement/installation. `../docs/measurements/q3m-town-static-selection-x2-20261004-v1/README.md`.

## Town_static : famille complète disponible installée — 2026-10-04

- Demande utilisateur : tout traiter Q3m avec palette améliorée et installer ingame. **18 IDs/18 modèles/18 BAM/1 543 frames**, V7 K6 x2/quatre partenaires/huit niveaux, sans SDF ; owner14, profils8/9 règle3, palettes natives live/CatmullRom. NULL_ANIMATION4001/SNONE sans source, exclu.
- Production `../docs/measurements/q3m-town-static-full-x2-20261004-v1/current-generation.json` ; 1 542 travaux uniques =huit hits acquis +1 534 nouveaux ; 9 204 cibles, reprise 1 542 hits sans Torch. Doublon exact SNOMM0/4 partagé ; aucune autre variante fusionnée.
- Native isolé/combiné : 18 BAM/1 543 frames/24 573 slots, K6 ×trois formats ; géométrie/cycles/représentants/profils conservés ; comparatif18poses inspecté. **QA ingame en attente**, aucun ancien verdict réécrit.
- Installation `installation-verification.json` : 18 feuilles +catalogue +sept CRE témoins QTST ; 151 fichiers acquis préservés SHA ; **104 IDs/50 299 routes et 4 618 composants/feuilles hérités identiques**, Ambient_static/cheval v3 et autres familles validées conservés. Actif122IDs/4 636ressources/50 317routes ; DLL/shaders/INI inchangés.
- 57 CRE consommateurs ; 18 commandes `CLUA-generiques.txt` ; sept témoins sans CRE d'origine, seuls offsets animation0x28 modifiés. Restore dédié vers le parent cheval v3 validé.
- Totaux recette : six familles/41 IDs installés, quatre familles/22 IDs validés ; aucune release ni commit à cette étape.

## Town_static : famille complète disponible validée — 2026-10-04

- Utilisateur : « tout est validé » après installation ; **18 IDs/18 modèles/18 BAM/1 543 frames acceptés ingame**, Q3m V7 K6 x2 amélioré, CatmullRom, sans SDF. NULL_ANIMATION4001/SNONE sans source reste exclu.
- QA immuable `index/qa-decisions/town_static/2026-10-04-accepted-full-available-town-static-q3m-v7-x2-catmullrom-v1.json` : exactes 18 feuilles installées, contrat runtime/DLL/INI/shaders, production et snapshot d'installation. Les mentions en attente du run de production restent historiques ; aucune preuve réécrite.
- Totaux recette : six familles/41 IDs installés, **cinq familles/40 IDs validés** ; Ogre QA en attente ; aucune release.
- Prochain lot proposé seulement : **ambient**, 18 IDs/16 modèles/34 BAM/2 580 frames physiques distinctes →2 406 travaux uniques, **1 024 hits compatibles →1 382 nouveaux encodages**. Chauve-souris et rat intérieur/extérieur partagent leurs BAM ; 174 répétitions entre BAM distincts, dont160 mendiant/esclave. KEG1/2/3 sans BAM. `../docs/measurements/q3m-ambient-selection-x2-20261004-v1/README.md` ; aucun traitement/installation.

## Ambient : famille complète disponible installée — 2026-10-04

- Demande utilisateur « ok go » : **18 IDs/16 modèles/34 BAM/2 580 frames physiques distinctes**, Q3m V7 K6 x2/quatre partenaires/huit niveaux, palettes améliorées live, CatmullRom, **sans SDF** ; owner12, profils8/9 règle3. KEG1/2/3 (CC00/CC01/CC02) sans BAM, exclus. `../docs/measurements/q3m-ambient-full-x2-20261004-v1/current-generation.json`.
- Travail réel : 2 406 encodages uniques =1 024 hits acquis SHA identiques +1381 nouveaux encodages +1 frame spéciale ; 8286 cibles ; reprise 2 406 hits sans Torch. Chauve-souris C000/C500 et rat C300/CC04 partagent cinq feuilles : 39 bindings/2 734 frames liées, aucune duplication physique ; 174 répétitions entre BAM distincts.
- Tests natifs isolé/combiné : 39 bindings/2 734 frames/14970 slots, K6 ×trois formats ; cycles/centres/profils/représentants source préservés, alias exacts, plans S/M/A absents ; comparatif16modèles inspecté, aucune QA ingame déduite.
- Installation `../docs/measurements/q3m-ambient-full-x2-20261004-v1/installation-verification.json` : 34 feuilles +catalogue +un CRE témoin QAMBCC04 ; **176 fichiers acquis préservés SHA**, 122 IDs/50 317 routes/4 636 composants hérités identiques ; Town_static accepté, cheval v3, Ankheg/Large16/Flying conservés. DLL/shaders/INI inchangés ; actif140IDs/4 670ressources/1 593 131frames/50 356routes, SHA catalogue `58e785769464a5471e056446f5e2b48ff6c9df07606454e1aa61f3c3c69afc2d`.
- 571 CRE consommateurs ; 18 commandes `../docs/measurements/q3m-ambient-full-x2-20261004-v1/CLUA-generiques.txt`, témoins/census `creatures.json` ; restauration dédiée vers le parent Town_static accepté. **QA utilisateur en attente** ; sept familles/59 IDs installés, cinq familles/40 IDs acceptés ; aucune release ni commit à cette étape.

## Ambient : famille complète disponible validée — 2026-10-04

- Utilisateur : « tout validé » ; **18 IDs/16 modèles/34 BAM/2 580 frames physiques acceptés ingame**, Q3m V7 K6 x2 palette améliorée/CatmullRom, sans SDF ; cinq bindings alias chauve-souris/rat conservés. KEG1/2/3 sans BAM exclus.
- QA immuable `index/qa-decisions/ambient/2026-10-04-accepted-full-available-ambient-q3m-v7-x2-catmullrom-v1.json` : exactes34feuilles/39bindings et runtime/DLL/INI/shaders installés, provenance production/vérification/snapshot ; catalogue `58e78576…afc2d`. Preuves historiques de production/installation non réécrites ; aucune modification ingame à cette étape.
- Totaux recette : sept familles/59 IDs installés, **six familles/58 IDs validés** ; Ogre QA en attente, aucune release.
- Prochain lot proposé seulement : **character_old**, sept IDs avec BAM sur8, six ensembles de sprites (cinq corps visibles +un transparent), 99 BAM/4 725 frames physiques →3 771 travaux uniques, **288 hits compatibles →3 483 nouveaux travaux dont41transparents**. Drizzt/Elminster/moine/squelette/Sarevok ; gardes funestes6405/6406 partagent22BAM entièrement transparents natifs ; XHFF6621 sans BAM. `../docs/measurements/q3m-character-old-selection-x2-20261004-v1/README.md` ; aucun traitement/installation.

## Character_old : famille complète disponible installée — 2026-10-04

- Demande utilisateur « go et installe » : **sept IDs/six ensembles/99 BAM/4 725 frames physiques**, Q3m V7 K6 x2/quatre partenaires/huit niveaux, palette améliorée live/CatmullRom, **sans SDF** ; owner6, profils8/9 règle3. Drizzt/Elminster/moine/squelette/Sarevok ; gardes funestes6405/6406 partagent22BAM/936frames transparents source ; 6621/XHFF sans BAM exclu. `../docs/measurements/q3m-character-old-full-x2-20261004-v1/current-generation.json`.
- 3 771 travaux uniques =288 hits acquis SHA identiques +3442 encodages nouveaux +41 travaux spéciaux ; 20385 cibles nouvelles/0 hits cibles ; reprise3 771 hits sans Torch. 954 répétitions entre BAM distincts ; alias gardes22feuilles partagé, 121bindings/5 661frames liées.
- Native monde isolé/combiné :120bindings/5 659frames/21143slots, K6 ×trois formats ; CMNKINV auxiliaire/deuxframes/cycle source vide vérifié directement feuille/cache ; couverture totale99BAM/4 725frames physiques, 121bindings/5 661frames liées. Géométries/cycles/profils/représentants conservés, alias exacts, gardes I/F zéro, aucun plan S/M/A. Comparatif six ensembles inspecté ; **QA utilisateur en attente**.
- Installation `../docs/measurements/q3m-character-old-full-x2-20261004-v1/installation-verification.json` :99feuilles +catalogue +deux témoins QCOL6405/QCOL6406 ; **211 fichiers acquis SHA identiques**, 140IDs/50 356routes/4 670composants hérités identiques ; Ambient accepté/chevalv3/Town_static/Ankheg/Large16/Flying préservés. DLL/shaders/INI inchangés ; actif147IDs/4 769ressources/1 597 856frames/50 477routes, catalogue `27f150c54f849cd495938d0cd2a3ade12a5632f64254a3e5545b0904ff62cd6f`.
- 160CRE consommateurs ; sept CLUA `../docs/measurements/q3m-character-old-full-x2-20261004-v1/CLUA-generiques.txt`, deux témoins dérivés ARNMAN01, animation0x28 modifiée et cinq scripts/dialogue vidés ; autres octets conservés. Restore dédié vers le parent Ambient accepté. Huit familles/66 IDs installés, six familles/58 IDs acceptés ; aucune release ni commit à cette étape.

## Character_old : correction des dépendances natives — 2026-10-04

- Symptôme confirmé : session 16:19:52–16:20:23, `CSHDG1` absent → composition incomplète → vanilla pour 6400/6401/6403. Première installation non validée ; corps acquis conservés.
- Delta : 33 CSHD +15 SSHD +919 WPM =967 BAM/44 669 frames/18 576 travaux encodés uniques, Q3m V7 K6 x2, sans SDF ; 4 775 liaisons ajoutées aux seuls sept IDs. Corps 99 BAM/4 725 frames inchangés. Famille : 1 066 BAM/49 394 frames physiques.
- [Production/installation corrective](../docs/measurements/q3m-character-old-runtime-fix-x2-20261004-v1/README.md), `verification.json` : oracle natif toutes frames nouvelles + compositions corps/ombre/arme/bouclier/casque, séquence16/slot31 et voisins. DLL/INI/shaders/autres familles conservés. QA ingame en attente ; compte accepted inchangé ; release inchangée.

## Gardes 6405/6406 : SDF ciblé — 2026-10-04

- Demande SDF sur QCOL6405/QCOL6406 ; **974 BAM/44 736 frames physiques partagés** : 22 MDGU +33 CSHD +919 WPM. V9 profiles8/9 règle3, x2/CatmullRom ; I/F/couleurs/géométries/cycles acquis identiques, zéro nouvelle inférence. Corps natifs936frames entièrement transparents ; SDF ne crée aucun corps.
- 33 routes CSHD ajoutées par ID : INI `shadow=` vide utilise néanmoins CSHD en jeu ; parent manque deux liaisons CSHDG1, nouveau complet. 952 feuilles partagées clonées pour seuls deux IDs ; cinq autres Character_old et145IDs/routes héritées conservés. Actif6 688ressources/1 686 325frames/55 318routes.
- [Run/installation](../docs/measurements/q3m-doom-guard-sdf-ingame-x2-20261004-v1/README.md) ; DLL stable16b01e52 +seul support V9 native-kind1 ; hooks/shaders/INI/CRE inchangés. Oracle natif K6×3 toutes frames/slots, compositions avec/sans équipement et40vues GPU passés ; Ankheg V9 préservé. QA utilisateur en attente, aucun nouvel accepted ni release.

## Character_old : famille complète validée — 2026-10-04

- Validation explicite utilisateur : « bien on valide toute la famille » ; **sept IDs/six ensembles**, cinq corps visibles +gardes6405/6406 transparents natifs. Q3m x2/CatmullRom/palette améliorée ; V7 sans SDF pour6400–6404, V9 SDF pour6405/6406. XHFF6621 sans source exclu.
- QA immuable `sprite/index/qa-decisions/character_old/2026-10-04-accepted-full-character-old-q3m-v7-v9-guards-sdf-x2-catmullrom-v1.json` : **2 018 feuilles variantes/93 194frames physiques installées**, 1 066 BAM natifs distincts, 4 962bindings/228124frames liées ;952 dépendances clonées pour isoler SDF. SHA2018feuilles +DLL/INI/trois shaders +deuxCREtémoin vérifiés, aucune production/installation historique réécrite.
- [Décision/suivi](../docs/measurements/q3m-character-old-accepted-x2-20261004-v1/README.md) ; totaux **sept familles/65 IDs acceptés**, huit familles/66 IDs installés. Ogre reste QA en attente ; aucune modification ingame/release.

- Monster_layered **complet installé, QA ingame en attente** : `../docs/measurements/q3m-monster-layered-full-x2-20261004-v1/README.md`, sept IDs/modèles, 65 BAM/6 422 frames ; 5 757 encodages uniques, 276 hits acquis, 5 479 nouveaux +deux spéciaux. Quatre feuilles Volo identiques au pilote local acquis ; 65 feuilles ajoutées au catalogue installé, où le pilote était absent. MSIRG2BE orphelin conservé hors runtime, aucun BAM source modifié. Hook ajouté au type2000 (`5aa840/32f3b0`), type8000 (`5aa650/32ee90`) déjà couvert ; association de la proposition corrigée par fabrique native. Neuf familles/73 IDs complets installés ; sept familles/65 IDs acceptés conservés.

## Monster_layered : famille complète validée — 2026-10-04

- Utilisateur « tout validé » : **sept IDs/sept modèles/65 BAM/6 422 frames**, Q3m V7 K6 x2 palette améliorée/CatmullRom sans SDF. MSIRG2BE orphelin exclu ; source inchangée.
- QA immuable `sprite/index/qa-decisions/monster_layered/2026-10-04-accepted-full-layered-q3m-v7-x2-catmullrom-v1.json` : 65 feuilles et DLL/INI/trois shaders installés SHA vérifiés ; provenance production/native/installation et diagnostic visibilité conservée. Volo : `C:CreateCreature("SARVOLO")`; QLYR2100 hérite du masquage finaliste ENDVOLO/opcode271 et ne convient pas au test visible. Ogre mage : invisibilité native MAGE01/opcode20, rendu HD confirmé.
- [Décision](../docs/measurements/q3m-monster-layered-accepted-x2-20261004-v1/README.md) ; **neuf familles/73 IDs installés, huit familles/72 IDs acceptés** ; Ogre reste QA en attente. Aucune installation/release modifiée.

- Prochain lot **proposé seulement** : `monster_quadrant`, deux modèles/sept variantes disponibles (grandes wyvernes normale/blanche/albinos, tanar’ri normal/bleu/vert/rouge). 36 BAM natifs/3 552 frames ; palettes propres →12 476 encodages uniques,200 hits acquis,12 276 nouveaux dont29 spéciaux sans GPU. 1101/1105 MWDR sans BAM ;33 hits de préfixe hors Quadrant exclus ;21 déclarations0×0 natives à préserver. [Sélection/doublons](../docs/measurements/q3m-monster-quadrant-selection-x2-20261004-v1/README.md). Aucun traitement ni installation.

## Monster_quadrant : famille complète disponible installée — 2026-10-04

- Demande utilisateur : lot complet Q3m amélioré +installation. **Sept IDs/deux modèles/sept palettes**, 36 BAM natifs/3 552 frames source ;132 feuilles variantes/12 928 frames. Q3m V7 K6 x2/CatmullRom sans SDF ;33 BAM hors appels natifs exclus ;1101/1105 MWDR sans source.
- Travail :12 476 identités ;200 hits acquis SHA inchangés +12238 nouveaux encodages +38 spéciaux ;73418 nouvelles cibles K6. Reprise12 476 hits sans Torch.
- **65 déclarations0×0 natives (21 physiques) conservées**, plans vides, centres/cycles/représentants exacts ; lecteur V7 limité à quatre resrefs fixes, native per-cell owner4 saute leurs dessins sans pixels inventés. DLL basée exactement sur le parent Layered accepté ; V10 Character en stock non activé, shaders/INI inchangés.
- 6916 assemblages offline quatre parties/136 cas avec quadrants vides, tous12928frames K6×3formats isolé/combiné, Ankheg V9 hérité. Catalogue parent154IDs/6753ressources/55383routes préservé ; actif161IDs/6885ressources/55515routes.
- [Run/CLUA](../docs/measurements/q3m-monster-quadrant-full-x2-20261004-v1/README.md) ;132 feuilles +DLL +catalogue +sept CRE neutres sans effets/inventaire/scripts. SHA2318 fichiers acquis conservés. **Dix familles/80 IDs installés ; huit familles/72 IDs acceptés inchangés**, QA ingame en attente ; aucune release.

## Monster_quadrant : raccords contextuels installés — 2026-10-04

- Sept palettes/132 feuilles/12 928 frames Q3m V7 x2 amélioré sans SDF ; reconstruction native des quatre parties sous K6 avant inférence, réparation limitée aux bandes4px natifs ;6010622 pixels I/F modifiés, **zéro hors bande**, masques/classes/centres/cycles/palettes inchangés.
- 3 144 contextes dédupliqués ;18552 nouvelles cibles ;encodeur ROI uniquement. **272 frames non référencées** conservées (rectifie l'estimation352 du rapport de prototype) ;65 déclarations0×0 inchangées.
- DLL/shaders/INI/sept CLUA acquis inchangés ;6753 autres composants +55515 routes inchangés. [Run/CLUA](../docs/measurements/q3m-monster-quadrant-seam-fixed-x2-20261004-v1/README.md). Catalogue actif161IDs/6885ressources/1705675frames. **Validation ingame en attente**, compteurs dix familles/80IDs installés et huit familles/72IDs acceptés inchangés.

## Monster_quadrant : famille corrigée validée — 2026-10-04

- Validation utilisateur explicite : deux modèles/sept palettes, 36 BAM natifs/132 feuilles/12 928 frames, Q3m V7 K6 x2 amélioré/CatmullRom sans SDF. QA immuable `index/qa-decisions/monster_quadrant/2026-10-04-accepted-full-quadrant-contextual-q3m-v7-x2-catmullrom-v1.json`.
- [Décision](../docs/measurements/q3m-monster-quadrant-accepted-x2-20261004-v1/README.md) ; 3 144 contextes, 18 552 cibles ; zéro pixel hors bande ; dimensions/cycles/classes/acquis runtime préservés. MWDR1101/1105 restent absents.
- Dix familles/80 IDs installés ; **neuf familles/79 IDs acceptés** ; Ogre reste QA en attente. Les mentions QA en attente précédentes sont les états historiques avant cette décision.
- Méthode incorporée aux commandes `q3m_family_witnesses.py plan/run/pack` via `q3m_multipart_seams.py` ; groupes natifs et clés de voisinage, checkpoint SHA, encodeur ROI, aucun GPU sur reprise complète/pack. [Contrat](../pipeline/SPRITES_Q3M_MULTIPART.md). Aucun payload/release modifié.

## Monster_old : complet disponible installé — 2026-10-05

- 46 IDs/18 modèles,79 BAM natifs/6 917 frames originales ;217 feuilles/17 752 frames physiques (218 liaisons/17 754 frames liées) Q3m V7 K6 x2 palette améliorée sans SDF. 16 785 encodages uniques ;100644 cibles neuves, aucune répétition physique retraitée. Trente palettes BMP natives authentifiées, sept INV auxiliaires conservés.
- Huit IDs7D01–7D08 sans BAM exclus. DLL/INI/shaders/acquis conservés ;46 CRE tests QOLD neutres sans scripts/effets/équipement. [Run/CLUA](../docs/measurements/q3m-monster-old-full-x2-20261004-v1/README.md).
- Onze familles/126 IDs installés ;neuf familles/79 IDs acceptés inchangés. **QA ingame en attente**, aucune release/validation déduite.

## MultiNew : complet installé — 2026-10-05

- 10 IDs/4 modèles : MDR1 rouge/vert/aqua/bleu/brun/multicolore/violet ; MDR2 noir, MDR3 argent, MDEM Démogorgon. 1 753 BAM/191 817 frames natives ; 5155 feuilles/519867 frames physiques, 5 155 liaisons/519 867 frames liées.
- 17 103 sources originales -> 42 772 travaux compatibles, 30 palettes BMP natives par banque ; 5 411 assemblages contextuels, zéro changement hors bande. Q3m V7 K6 x2 amélioré/CatmullRom sans SDF.
- DLL/INI/shaders acquis inchangés ; 10 CRE tests QMUL neutres. Douze familles/136 IDs installés ; neuf familles/79 IDs acceptés inchangés. **Monster_old et MultiNew : QA en attente** ; aucune release déduite.
- [Run et CLUA](../docs/measurements/q3m-multi-new-full-x2-20261005-v1/README.md).

## MultiNew : chargement stabilisé — 2026-10-05

- [Correctif runtime installé](../docs/measurements/q3m-multi-new-frame-stability-20261005-v1/README.md) : métadonnées du groupe courant 4/9 parties prêtes avant le rendu HD ; fini le repli vanilla dû au chargement asynchrone. Repli natif conservé pour les ressources réellement invalides.
- Régression : ancien mode 20/20 groupes en repli temporaire ; corrigé 0/580 groupes, 5 155 ressources. DLL seule remplacée ; assets/palettes Q3m K6 x2 sans SDF inchangés. QA ingame toujours en attente ; compteurs et décisions acquis inchangés.
