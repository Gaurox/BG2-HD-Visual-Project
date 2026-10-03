# Suivi sprites Q3m — 2026-10-03

## Portée / méthode

- Familles = `engine_section` des INI, autorité `index/family-groups.csv` ; 15 profils personnages/créatures. `effect` et IDs sans INI : hors queue, conservés dans l'inventaire source.
- Personnages jouables, compagnons, PNJ, monstres, animaux et figurants inclus ; un PNJ utilisant `character` appartient au même profil que les jouables.
- Méthode courante : **Q3m K6, quatre partenaires / huit niveaux, V7 x2** ; indices + B/F + dépendances, palette native vivante. Classes et partenaires propres au profil fixe/rampes ; owner exact par famille.
- Monde : x2 + BOX. Paperdolls : voie UI distincte ; acquis `6110` conservés.
- xBR final / ReboutCX première génération : **historique, exclus de l'avancement Q3m**. Sources, runs et QA historiques préservés ; aucun déplacement/suppression. xBR comme guide et ReboutCX comme producteur de cibles restent des briques de Q3m.
- Pilote quatre partenaires : **15 témoins / 49 BAM / 11 586 frames**, actions retenues uniquement, tests hôte acquis ; historique du pilote préservé. Décisions QA des familles complètes ci-dessous. `../docs/measurements/q3m-families-engine-x2-20261003-v2/current-generation.json` ; contrat `../pipeline/PALETTE_Q3M_V7.md`.
- Première famille complète V7 : **`monster_large` / ogre `0x9000` / 7 BAM / 434 frames**, produite et installée ; **QA ingame en attente**. `../docs/measurements/q3m-monster-large-full-x2-20261003-v1/current-generation.json` ; faits d'installation `installation-verification.json` du même run.
- Deuxième famille complète V7 : **`flying` / 5 IDs / 4 BAM / 243 frames**, produite, installée et **famille validée par l'utilisateur**. `../docs/measurements/q3m-flying-full-x2-20261003-v1/current-generation.json` ; QA `index/qa-decisions/flying/2026-10-03-accepted-full-flying-q3m-v7-k6-x2-box-v1.json` ; le comparatif et les faits d'installation restent des états historiques distincts.
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
| `monster_ankheg` | 1/1 | — | Ankheg ; enfouissement/émergence et éléments de rendu propres au profil. |
| `monster_large` | 1/1 | — | Ogre ; **famille complète V7 x2 installée**, 7 BAM / 434 frames ; QA ingame en attente. |
| `monster_large16` | 3/5 | — | Profil grands monstres à 16 directions ; wyvernes, charognards rampants. |
| `ambient` | 18/21 | — | Animations ambiantes mobiles ; chats, rats, poules, écureuils, figurants. |
| `ambient_static` | 13/13 | — | Ambiants statiques et animaux ; vaches, chevaux, enfants/nobles/figurants. |
| `town_static` | 18/19 | — | PNJ assis/couchés ; poses fixes, humains/nains/elfes/halfelins endormis. |
| `flying` | 5/5 | — | Aigle, mouette, vautour, petit oiseau ; **famille complète V7 x2 installée et validée**, 4 BAM / 243 frames ; intérieur/extérieur partagent une ressource. |

## Queue / références

- `index/q3m-work-tracking.json` : décisions de méthode, estimation moteur, familles et références ; **plan**, aucune autorité supplémentaire sur les états métier.
- `index/q3m-work-items.csv` : 465 IDs, dont 335 avec BAM et 130 sans BAM. Une ligne par animation ; composants/équipement reliés par `family_ids`. `q3m-reference-available` / `to-produce-or-extend-profile` / `source-absent` = état de queue, pas validation.
- Historique V6 : 81 IDs avec référence Q3m ; 254 IDs avec BAM sans référence V6 inscrite. Nouveau V7 : **15 IDs témoins partiels, 6 IDs / 2 familles complètes installées ; 5 IDs / 1 famille validée (`flying`)** ; colonnes `q3m_v7_witness_*`, `q3m_v7_full_production_reference`, `q3m_v7_installation_reference` du CSV. Pas de taux global à partir des frames/BAM partagés.
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
- Coût du reste des 335 animations avec BAM : `null` tant que la sélection exacte et son union de clés finale ne sont pas calculées ; ne pas additionner les compteurs par famille.
- Sélection CPU : `pipeline/scripts/analyze_sprite_frame_dedup.py plan --animation-id <ID> [...]`. Pas d'inférence indépendante par famille ni addition des compteurs partagés.
