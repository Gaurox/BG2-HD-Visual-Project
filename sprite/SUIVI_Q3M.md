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

## Inventaire des familles

`Stock` = IDs avec au moins un BAM / IDs définis ; `Q3m connu` = références **V6 antérieures**, pas couverture du nouveau contrat V7. Les sous-types restent dans `index/q3m-work-items.csv` (`animation_type`, INI source). Chaque famille a un témoin V7, listé dans `index/q3m-family-witnesses.json` ; les témoins restent partiels. Le lot complet Ogre possède une référence distincte.

| Profil | Stock | Q3m connu | Intégration / exemples |
|---|---:|---:|---|
| `character` | 78/78 | 78 | Corps/armures + armes/casques/boucliers ; palettes par couche. Variantes LOW `5000` et standard `6000`. Jouables, compagnons, PNJ partageant ces avatars. |
| `character_old` | 7/8 | — | Avatars anciens/spéciaux, contrat distinct de Character ; Drizzt, Elminster, Sarevok. |
| `monster` | 77/102 | 3 | Monstres BG2, BAM éventuellement divisés ; palette fixe/false-color à résoudre par ID. Spectateurs, Bodhi, golems, trolls. |
| `monster_old` | 46/54 | — | Anciennes animations BG1, séquences/directions et palettes propres ; ours, loups, basilics, demi-ogres. |
| `monster_icewind` | 44/132 | — | Séquences de style IWD ; contrat palette propre à l'animation. Orcs, gobelins, ettins, liches. |
| `monster_quadrant` | 7/9 | — | Assemblage de plusieurs quadrants ; centres et ordre de dessin conservés. Grandes wyvernes, tanar'ri. |
| `multi_new` | 10/10 | — | Grands composites, quadrants et BAM divisés selon l'INI ; dragons, Démogorgon. |
| `monster_layered` | 7/7 | — | Corps et armes superposées ; sous-types `2000` et `8000` à conserver séparément. Sirines, ogres mages, gnolls, hobgobelins, kobolds. |
| `monster_ankheg` | 1/1 | — | Ankheg ; **famille complète V9 SDF x2 + attente HD installée et validée**, 12 BAM / 516 frames ; couleurs V7, corps/terre et enfouissement/émergence. |
| `monster_large` | 1/1 | — | Ogre ; **famille complète V7 x2 installée**, 7 BAM / 434 frames ; QA ingame en attente. |
| `monster_large16` | 3/5 | — | Wyverne, charognard rampant, wyverne blanche ; **famille disponible complète V7 x2 sans SDF installée**, 20 feuilles / 1 692 frames, palette blanche native ; **validée ingame**. Deux IDs sans BAM. |
| `ambient` | 18/21 | — | Animations ambiantes mobiles ; chats, rats, poules, écureuils, figurants. |
| `ambient_static` | 13/13 | — | **Famille complète V7 x2 couleurs améliorées sans SDF installée et validée**, cheval œil v3 inclus ; 13 modèles/26 BAM/1 144 frames. |
| `town_static` | 18/19 | — | PNJ assis/couchés ; poses fixes, humains/nains/elfes/halfelins endormis. |
| `flying` | 5/5 | — | Aigle, mouette, vautour, petit oiseau ; **famille complète V7 x2 installée et validée**, 4 BAM / 243 frames ; intérieur/extérieur partagent une ressource. |

## Queue / références

- `index/q3m-work-tracking.json` : décisions de méthode, estimation moteur, familles et références ; **plan**, aucune autorité supplémentaire sur les états métier.
- `index/q3m-work-items.csv` : 465 IDs, dont 335 avec BAM et 130 sans BAM. Une ligne par animation ; composants/équipement reliés par `family_ids`. `q3m-reference-available` / `to-produce-or-extend-profile` / `source-absent` = état de queue, pas validation.
- Historique V6 : 81 IDs avec référence Q3m ; 254 IDs avec BAM sans référence V6 inscrite. Nouvelle recette : **15 IDs témoins partiels, 23 IDs /5 familles disponibles complètes installées ; 22 IDs /4 familles validées (`flying`, `monster_ankheg` V9 stable, `monster_large16` V7 sans SDF, `ambient_static` V7 sans SDF +cheval œil v3)** ; colonnes `q3m_v7_witness_*`, `q3m_v7_full_production_reference`, `q3m_v7_installation_reference` du CSV. QA propre à chaque variante/runtime. Ogre reste QA en attente ; V10 Character en stock exclu de l'installation et des validations. Pas de taux global à partir des frames/BAM partagés.
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
- Correctif installé/validé : lecteur commun capture/draw `WaitForAnkhegMetadata`, catalogue V2 / owner9 / ID3000 ; attente existante ≤5 s, worker/payloads paresseux/authentification/quarantaine/fallback sur erreur conservés. Sonde finale : **12/12 premiers accès HD, 0 miss, attente max69,013 ms**, 516 frames / 1 485 slots / 48 compositions vérifiés. Mesure hôte, pas promesse de latence. Character owner1 possède déjà son attente ; autres familles restent NonBlocking. Généralisation par contrat natif, jamais par seule présence d'un contour.
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
