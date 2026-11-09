# Finalisation projectiles — analyse 2026-11-09

- Périmètre : 243 PRO stock + overrides actifs, contrôleurs VVC/VEF récursifs, enfants PRO ; 78 IDs sans PRO suivis, dont 34 référencés SPL/ITM/PRO. Analyse seule ; aucun GPU, jeu, build, installation ou release.
- Conclusion : **3 BAM sans production confirmés**, **1 réemploi sprites à raccorder**, contrats moteur résiduels à résoudre. `effects=494/494 clôturés` ne ferme pas ces usages hors inventaire effets.
- Autorités conservées : QA images ≠ QA propriétaire ; 29 PRO acceptés pour composants observés, 3 accords historiques ; aucune nouvelle décision QA/intégration/installation/release.

## Images hors effets

| BAM | Chemin utilisateur → moteur | Source / production | Action minimale |
|---|---|---|---|
| BGLRYU | SPPR612.SPL → BGLRY.PRO → fumée ANIMATE0101 | 20 frames / 1 cycle ; aucune sortie trouvée | Produire une fois, pack et raccord cellule secondaire |
| SPCL236U | SPCL236.SPL, 5 capacités → SPCL236.PRO → fumée ANIMATE0102 | 10 frames / 1 cycle ; aucune sortie trouvée | Même travail ; vol SPCL236 déjà produit |
| SPGLYPHI | SPPR304.SPL, 14 capacités → TRAPGLYP.PRO → fragments ANIMATE0410 ; partagé avec TRAPGLPN | 60 frames / 5 cycles ; aucune sortie trouvée | Une production commune, pas deux ; TRAPGLPN sans référence directe SPL/ITM trouvée |
| ACOWG1 | PROJECTL188 / missile189 COW → constructeur BAM `0x227600`, chaîne littérale à `0x22e220` | Q3m ambient_static x2 déjà produit/accepté ; absent catalogue effets, aucun override BAM | Réemployer le sprite ; vérifier/adopter la route projectile et sa compatibilité d'échelle, sans nouvelle inférence |

- Trois premières sources : `sprite/index/sprite_resources.csv`, familles `effect`, absentes de `effects/index/work-items.csv` et du registre animations. Pas des sprites multipart ni des équipements superposés. Planche : [new-source-candidates.png](new-source-candidates.png).
- Le champ historique sprite `runtime_relevant=no` n'exclut pas l'appel par un projectile : les références PRO/constructeur ci-dessus sont distinctes du pilote créature.
- Déduplication des 3 nouvelles sources : BAM canonique + palette ; 20/10/60 poses natives uniques, 0 correspondance exacte avec les productions recensées. Pas de second job sur BGLRYT, SPCL236, SPGLYPTI ou GLPHWRDT déjà produits.
- Raccord secondaire : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/core/effect_secondary_scope.h` ne contient pas BGLRYU/SPCL236U/SPGLYPHI ; prévoir cet ajout avec les packs, pas une simple copie de textures.
- COW : `sprite/index/q3m-work-items.csv:0xB000`, `sprite/index/q3m-work-tracking.json:ambient_static.current_full_production`, `docs/measurements/q3m-ambient-static-full-x2-20261004-v1/selection.json`. La QA créature n'accorde aucune QA projectile ; le catalogue `CreatureSprites-XN` ne prouve pas la substitution d'un CVidCell projectile.

## Liens actifs vérifiés

| Contrôle | Résultat | Preuve |
|---|---|---|
| PRO actifs vs stock + patchs documentés lot31/nuées | 243 conformes ; 0 delta inexpliqué | `link-summary.json:PRO_byte_issues`, `audit_links.py` |
| Routes lot31 par propriétaire/palette/encodage | 134/134 conformes | `palette-routes.csv` |
| Catalogue / registre | 736 ressources, SHA registre conforme ; manifeste stable pendant lecture | `link-summary.json` |
| Ressources runtime touchées par les composants PRO | 169 ; 21 207 backings présents et de taille conforme ; 0 écart | `selection-links.csv`, `link-summary.json` |
| Contextes source + palette | 175 = 164 réutilisables + 8 masques natifs + 3 sans sortie | `analysis.json`, `visual-contexts.csv` |
| Métadonnées source/QA/run/pack des sélections | 0 échec | `analysis.json:selection_metadata_failures` |
| Composants secondaires produits | 85/85 avec preuve partagée rôle/asset ; 37 groupes historiques conservés | `components.csv:shared_route_evidence` |
| DLL active | SHA `393820D32FFC94E20E50D0DD27B6511C19EA1994B64AF3444BE75AA434987912`, identique V14 acceptée | `renderer-observation.json`, acceptation finale V14 |

- Contrôle des backings = existence/taille et comparaison des hashes déclarés dans les métadonnées ; **pas de rehash des octets des 21 207 textures**, ni de nouveaux draws ingame.
- L'ancien découpage structurel reste 100 raccordés statiques / 124 routes secondaires prudentes / 13 natifs / 4 PRO avec image manquante / LIGHTCHA / LIGHTSTO. **Les 124 ne sont pas 124 liens cassés** : ce classement conservateur ne réconcilie pas la campagne V3–V14. Les 85 composants produits qui déclenchent sa réserve secondaire ont tous une preuve partagée, sans acceptation automatique de chaque propriétaire/palette/cycle.
- 85/169 ressources ont des métadonnées de frames exactement identiques à la sélection canonique effets. Les 84 différences sont séparées dans `selection-links.csv` : 76 ressources avec `palette_job`, 5 canoniques de compatibilité (BDWOFOGA/SPCLOUDK/SPCLOUDS/SPDFOGA/SPSKULLT), 3 alias normaux de nuées. **Différence de sélection ≠ rupture** : les palettes, compagnons alpha/straight et alias ont leurs propres preuves/versions ; conserver leur provenance lors de la finalisation.
- Alias moteur alpha : `core/effect_texture_alias.h` → SPCLOUDK/X58CLK, SPCLOUDS/X58CLS, SPDFOGA/X58DFOG, BDWOFOGA/X58WFOG en normal, WRITHING/X28WRTH en normal. Réemplois et acceptations déjà documentés ; ne pas réinstaller les anciennes sélections canoniques par-dessus ces corrections.

## Contrats restant ouverts

| Sujet | Constat | Suite ciblée |
|---|---|---|
| LIGHTCHA | Mot natif de traînée3 = 9 ; SPCHLGT3 ne déclare pas ce cycle. Phases/séquences5/7 observées et acceptées en V13 | Résoudre la sémantique/branche native du mot9 ; conserver la QA des éclairs observés, ne pas fabriquer un cycle9 |
| LIGHTSTO | MAGMIS absent KEY/BIF/catalogue ; 0 référence directe SPL/ITM trouvée, fermeture CHROMORB | Identifier un appel réel/branche avant traitement ; pas de substitution arbitraire par SPMAGMIS |
| COW188 | ACOWG1 déjà produit x2 côté sprites, pas de ressource au catalogue effets | Pont de rendu/pack à étudier avec conservation du contrat sprite ; pas de double IA |
| IDs natifs | 34 référencés / 78 suivis ; voir complément binaire ci-dessous | Compléter la fermeture des constructeurs/enfants et leurs liens, au lieu d'inventer 78 nouveaux jobs |
| TSKULLNP | Pas de SPL direct ; **BOLT07.ITM** capacité0 utilise projectile239 / missile240 | Pilote objet possible si un contrôle propriétaire devient nécessaire ; SKLH déjà observé via TRAPSKUL |
| SHAREA202 | BAM/palette SHAREA2 identifiés ; propriétaire/palette non exercé indépendamment | Statique/dispatch ciblé ; préserver les cinq palettes déjà validées |
| FIREBALL | 21 modes implicites d'explosion ; enum ≠ BAM | Résoudre les branches utiles/enfants ; ne pas compter 21 images nouvelles |
| Déplacement | PROJ-MOTION-001 reporté par utilisateur | Hors de cette passe ; animation des images et positions restent distinctes |

## Complément : IDs sans PRO

- Lecture de l'exécutable courant, branches factory des 34 IDs référencés : `native-used-dispatch.txt`, SHA EXE dans `native-used-strings.json`. Chaînes littérales croisées avec types KEY, y compris casse mixte ; résultats `native-raster-links.csv`.
- **10 BAM nommés identifiés dans ces branches** : ACOWG1, HLYMITE, SHAIR, SHAREA, SHEARTH, SPFDEATH, SPGENHLA, SPHOLYMT, SPMAGMIS, SPSCORIC. **9 présents au catalogue effets ; ACOWG1 seul hors catalogue**, déjà produit côté sprites.
- 7 BMP de palette identifiés, pas des images supplémentaires : SHAIR4, SHEARTH6, SHAREA2/3/4/5/6.
- ID65/194 → HLYMITE ; 67..73/76 → SPMAGMIS ; 118/130 → SHAIR ; 119/137 → SHEARTH ; 188 → ACOWG1 ; 190 → SPSCORIC ; 197..202 → SHAREA et palettes ; 207 → SPFDEATH ; 241 → SPHOLYMT ; 254 → SPGENHLA.
- ID80..84 : prototype SPMAGMIS rencontré mais chaîne résout aussi un enfant par factory et efface une référence ; **ne pas assimiler ce prototype au visuel final des éclairs**. Même prudence pour invisible78. Les ID13/38 passent par une branche générique dans la table ; les normalisations amont/lookup demandent encore analyse.
- Limite : extraction des littéraux de branches, pas fermeture des ressources calculées/constructeurs/enfants. Les 3 nouvelles images sont les manques confirmés dans le graphe résolu ; pas une preuve qu'aucun autre manque n'existe derrière les branches non résolues.

## Ordre de reprise proposé

1. Produire les 3 BAM hors effets avec leur contrat natif ; raccorder la cellule secondaire et conserver une production commune pour SPGLYPHI.
2. Raccorder COW188 depuis ACOWG1 existant ; terminer le mapping des IDs moteur, leurs palettes/enfants et modes FIREBALL utiles.
3. Résoudre LIGHTCHA9/LIGHTSTO et consigner les contrats/provenances propriétaires utiles. Aucun retest des composants déjà acceptés sans changement d'octets ou de contrat.
4. Décider ensuite du périmètre d'acceptation/finalisation des projectiles. Aucun taux global « projectiles100% » déduit du taux effets ou des seuls liens statiques.

## Reproduction et fichiers

- `python -B pipeline/scripts/projectile_tracking.py status` : snapshot actuel à jour, aucune entrée changeante ; `refresh` exige un nouveau nom.
- Correctif nécessaire à cette lecture : `pipeline/scripts/projectile_tracking.py` ignore les sélections `mode=native` lors de la recherche de pack HD. Avant correction, tentative d'ouvrir le dépôt comme fichier sur SHAREAB ; aucune donnée historique altérée.
- `audit_links.py` : recette de lecture PRO/controllers/catalogue/palettes/contrats déclarés ; copie dans un nouveau dossier requise pour relancer après scellement. `projectiles-243.csv` conserve le verdict structurel prudent ; `components.csv` ajoute les preuves partagées séparément.
- `analysis.json` / `contexts.json` / `usage.csv` : sources, palettes, dépendances, usages et SHA. `link-summary.json` : résultat des liens actifs. `native-raster-links.csv` : complément moteur hors PRO. QA52 et toutes les décisions historiques conservées.
