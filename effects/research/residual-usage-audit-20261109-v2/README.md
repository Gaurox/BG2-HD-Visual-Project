# Reliquat effets — audit des usages

- Audit2026-11-09 : 67entrées résiduelles examinées ; 0nouveau job d’effet du monde confirmé dans le graphe courant. 3cas dormants AM307TT2/3/MSOLG1 conservés ; 2BAM absents derrière contrôleurs sans appelant ; SPWI124B actif = icône, renvoi icons. Exclusions de production uniquement, aucune QA inventée.
- `scan-summary.json` : 22392 ressources natives/overrides, 64931181octets, métadonnées + scripts + contrôleurs + EXE ; index ARE/sprites croisés.
- `native-residual-contact-sheet.png` : inspection CPU des65sources présentes ; `sources.json` : SHA, géométrie, cycles, stats.
- `references.json` = candidats bruts, **pas preuve de rendu**. `typed-areas.json` et `followup-references.json` séparent WAV, noms, icônes, faux suffixes et contrôleurs sans appelants.
- Guillotines : appels272 réels dans GUILLOT1/2 mais scripts orphelins dans le graphe actuel ; AR0329 emploie action301 sonore. Aucun lien vers ces scripts dans les ARE/CRE/BCS/DLG/2DA/INI natives/overrides. Ne pas lancer un job sur la seule présence du script.
- Solar : ANISND MSOL historique ; INI actif7F3B utilise **MSOG**, pas MSOLG1. VVC MSOLG1 orphelin ; aucun second job du Solar.
- SP_DEMGT : alias installé identique AMDEMGT accepté ; pas de nouvelle production, QA propre à l’alias non inférée.
- SHGLYPH/SHSKULL : ombres PRO natives ; préserver. SPAURAFD/SPENTAXL restent bloqués source absente ; ne pas supprimer leurs contrôleurs.
- **Limite** : audit statique de cette installation, pas preuve universelle d’inutilisation ni QA ingame. Toute nouvelle invocation/mod réouvre la ressource correspondante.
- `classification.json` : usage excluded appliqué au périmètre effects ; processing/QA/install/release intacts. Les2sources manquantes restent blocked dans la queue.
- Formats primaires : [ARE](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/are_v1.htm), [SPL](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/spl_v1.htm), [actions272/301](https://gibberlings3.github.io/iesdp/scripting/actions/bgeeactions.htm).

| Catégorie | Entrées |
|---|---:|
|substring-false-hit|1|
|unreferenced-bam-current-graph|45|
|sound-homonym|6|
|ambient-name-homonym|4|
|dormant-effect-script|2|
|legacy-solar-orphan-vvc|1|
|native-projectile-shadow|2|
|missing-source-orphan-controller|2|
|ui-variant-no-direct-caller|1|
|active-ui-icon|1|
|already-produced-alias|1|
|door-name-homonym|1|

## Décisions par ressource

| BAM | Décision | Motif |
|---|---|---|
|0202A|substring-false-hit|Les occurrences texte sont des suffixes de AM0202A, pas un champ BAM 0202A. Animation active AR0202 = AM0202A déjà acceptée ; BAM différent, sans nouvel appel identifié.|
|AM0021A|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0202AT|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0404A|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0404B|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0411A|sound-homonym|Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.|
|AM0411B|sound-homonym|Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.|
|AM0411B1|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0411B2|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0603D4|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM0902L1|ambient-name-homonym|AR0902.BCS emploie le nom comme objet sonore pour action301 AmbientActivate. La vraie animation placée est AM0902L, déjà acceptée côté animations ; aucun BAM suffixé appelé.|
|AM0902L2|ambient-name-homonym|AR0902.BCS emploie le nom comme objet sonore pour action301 AmbientActivate. La vraie animation placée est AM0902L, déjà acceptée côté animations ; aucun BAM suffixé appelé.|
|AM0902L3|ambient-name-homonym|AR0902.BCS emploie le nom comme objet sonore pour action301 AmbientActivate. La vraie animation placée est AM0902L, déjà acceptée côté animations ; aucun BAM suffixé appelé.|
|AM0902L4|ambient-name-homonym|AR0902.BCS emploie le nom comme objet sonore pour action301 AmbientActivate. La vraie animation placée est AM0902L, déjà acceptée côté animations ; aucun BAM suffixé appelé.|
|AM2000A1|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM2000A2|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM2000A3|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM2000A4|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|AM2000B1|sound-homonym|Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.|
|AM2000B2|sound-homonym|Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.|
|AM2000B3|sound-homonym|Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.|
|AM2000B4|sound-homonym|Les références ARE sont dans des champs de sons ambiants (record+0x30..0x78), pas dans animation.resref. Le BAM homonyme n’est pas l’asset sonore appelé.|
|AM307TT2|dormant-effect-script|GUILLOT1.BCS contient action272 CreateVisualEffect(AM307TT2), mais aucun appelant de GUILLOT1 trouvé. Références AR0329.BCS = action301 AmbientActivate, pas création graphique. ARE0307/0329 utilisent AM307TT1 déjà accepté ; aucun nouveau job confirmé.|
|AM307TT3|dormant-effect-script|GUILLOT2.BCS contient action272 CreateVisualEffect(AM307TT3), mais aucun appelant de GUILLOT2 trouvé. Références AR0329.BCS = action301 AmbientActivate, pas création graphique. ARE0307/0329 utilisent AM307TT1 déjà accepté ; aucun nouveau job confirmé.|
|AM60406B|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|DEMB1A1|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A2|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A3|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A4|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A5|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A6|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A7|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille. DEMB1A7/DEMB1A9 = doublon canonique strict.|
|DEMB1A8|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1A9|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille. DEMB1A7/DEMB1A9 = doublon canonique strict.|
|DEMB1CA|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|DEMB1G1|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré. Image de démonstration de personnage inspectée ; les correspondances DEMB* dans les CRE sont des scripts/variables dembal*, pas un préfixe d’animation de cette famille.|
|FISH4SA|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|FISH4SB|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|FISH4SC|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|FISH5SA|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|FISH5SB|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|FISH5SC|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|JDPROP|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|MSOLG1|legacy-solar-orphan-vvc|Sprite Solar historique ; VVC MSOLG1 sans appelant trouvé. ANISND mentionne MSOL, mais le profil actif 7F3B.INI utilise resref=MSOG, confirmé par sprite/index/sprite_animations.csv. Pas de second traitement du Solar.|
|SETTRAP|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|SHGLYPH|native-projectile-shadow|Champ PRO shadow-animation 0x10C ; masque natif native-mask-no-ai déjà identifié dans projectiles/index/visual-assets.csv. Conserver natif ; aucune nouvelle QA déduite.|
|SHSKULL|native-projectile-shadow|Champ PRO shadow-animation 0x10C ; masque natif native-mask-no-ai déjà identifié dans projectiles/index/visual-assets.csv. Conserver natif ; aucune nouvelle QA déduite.|
|SPAURAFD|missing-source-orphan-controller|VVC SPAURAFD référence un BAM absent de KEY/override/source local ; aucun appelant du contrôleur trouvé. Conserver blocked, ne pas fabriquer une image.|
|SPELLTIN|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|SPENTAXL|missing-source-orphan-controller|VVC ENTTEST1 référence un BAM absent de KEY/override/source local ; aucun appelant du contrôleur trouvé. Conserver blocked, ne pas fabriquer une image.|
|SPWI124A|ui-variant-no-direct-caller|Variante graphique d’icône/parchemin, sans appelant exact trouvé. SPWI124 utilise icône de livre C et icône mémorisée B ; conserver A comme variante à qualifier côté icons.|
|SPWI124B|active-ui-icon|Six SPL actifs référencent SPWI124B dans extended-header+0x04 (icône mémorisée), dont SPWI124. Travail éventuel à suivre dans icons, pas comme effet du monde ; aucune QA/production UI déduite.|
|SP_DEMGT|already-produced-alias|Alias exact AMDEMGT accepté ; images, géométrie et timeline installées identiques. Aucune nouvelle inférence ; QA indépendante de cet alias non inventée.|
|TREE01|door-name-homonym|Références dans noms/IDs de portes ARE/WED et opérations de porte BCS ; aucune animation BAM TREE01 placée. Le BAM d’arbre n’est pas le dessin des tuiles de cette porte.|
|TREE02|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE03|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE04|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE05|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE06|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE07|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE08|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE09|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|TREE10|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|WBRAZR1|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|WBRAZR2|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|WBRAZR3|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
|WBRAZR4|unreferenced-bam-current-graph|BAM présent, sans appel graphique exact trouvé dans les ressources natives/overrides ni dans les index ARE/sprites. Pas de production requise dans le graphe audité ; réouvrir si nouvel usage démontré.|
