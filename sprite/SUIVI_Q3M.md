# Suivi sprites Q3m — 2026-10-03

## Portée / méthode

- Familles = `engine_section` des INI, autorité `index/family-groups.csv` ; 15 profils personnages/créatures. `effect` et IDs sans INI : hors queue, conservés dans l'inventaire source.
- Personnages jouables, compagnons, PNJ, monstres, animaux et figurants inclus ; un PNJ utilisant `character` appartient au même profil que les jouables.
- Méthode courante : Q3m K6, indices + fractions + dépendances, palette réalisée par le moteur. Classes/successeurs et owner propres au profil ; aucune transposition implicite des rampes Character aux monstres.
- Monde : x2 + BOX. Paperdolls : voie UI distincte ; acquis `6110` conservés.
- xBR final / ReboutCX première génération : **historique, exclus de l'avancement Q3m**. Sources, runs et QA historiques préservés ; aucun déplacement/suppression. xBR comme guide et ReboutCX comme producteur de cibles restent des briques de Q3m.
- Couleurs, 4 partenaires / 8 niveaux et 16 niveaux : diagnostics de six frames, format V6 incompatible ; candidats distincts, aucune couverture complète acquise. Référence : `../docs/measurements/q3m4partners-colour-comparison-x4-20261003-v1/README.md`.
- Intégration nouveau moteur sprite : **90 %**, estimation utilisateur du 2026-10-03 ; ne mesure ni couverture des assets ni QA.

## Inventaire des familles

`Stock` = IDs avec au moins un BAM / IDs définis ; `Q3m connu` = références de production disponibles, pas QA/installation/release. Les sous-types restent dans `index/q3m-work-items.csv` (`animation_type`, INI source).

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
| `monster_large` | 1/1 | — | Profil grands monstres BG1 ; ogre. |
| `monster_large16` | 3/5 | — | Profil grands monstres à 16 directions ; wyvernes, charognards rampants. |
| `ambient` | 18/21 | — | Animations ambiantes mobiles ; chats, rats, poules, écureuils, figurants. |
| `ambient_static` | 13/13 | — | Ambiants statiques et animaux ; vaches, chevaux, enfants/nobles/figurants. |
| `town_static` | 18/19 | — | PNJ assis/couchés ; poses fixes, humains/nains/elfes/halfelins endormis. |
| `flying` | 5/5 | — | Oiseaux en vol ; profil et placement distincts. Aigles, mouettes, vautours. |

## Queue / références

- `index/q3m-work-tracking.json` : décisions de méthode, estimation moteur, familles et références ; **plan**, aucune autorité supplémentaire sur les états métier.
- `index/q3m-work-items.csv` : 465 IDs, dont 335 avec BAM et 130 sans BAM. Une ligne par animation ; composants/équipement reliés par `family_ids`. `q3m-reference-available` / `to-produce-or-extend-profile` / `source-absent` = état de queue, pas validation.
- 81 IDs avec référence Q3m ; 254 IDs avec BAM sans référence Q3m inscrite dans cette queue. Pas de déduction d'un taux global à partir des frames ou de sommes de BAM partagés.
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
- Profil/couleur/alpha/fits non défini : travail source mesuré, coût GPU final `null` ; aucune adoption I/F ni transposition de profil. Quatre partenaires reste un contrat distinct à définir.
- Sélection CPU : `pipeline/scripts/analyze_sprite_frame_dedup.py plan --animation-id <ID> [...]`. Pas d'inférence indépendante par famille ni addition des compteurs partagés.
