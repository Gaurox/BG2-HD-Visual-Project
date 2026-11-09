# Réconciliation des propriétaires — 2026-11-10

- Autorité technique : `../../index/owner-reconciliation-current.json`. Détails : `owners.json`/`owners.csv`, `components.json`, `resources.json`, `engine-owners.json`, `opcode-references.csv`. QA utilisateur conservée dans `../../index/work-tracking.json` ; aucune nouvelle acceptation visuelle déduite.
- **320 propriétaires examinés : 243 PRO + 77 IDs moteur. 299 contrats compatibles réconciliés (242 PRO + 57 IDs), 13 IDs avec exceptions actives regroupées en 4 familles, 8 écarts natifs sans pilote statique conservés séparément.** Ces états concernent les composants/contrats recensés, pas toutes les chaînes gameplay des SPL/ITM.
- 468 occurrences, contrôleurs VVC/VEF développés, enfants corrigés 0x214/0x21a, alias de palettes/alpha et cycles complets. 0 modification PRO inexpliquée ; palettes natives, orientations, blend/alpha et périodes d'émission conservés.
- 1 400 références de lancement op140/op141 ajoutées aux capacités SPL/ITM et enfants PRO : **60 IDs moteur avec pilotes statiques**, au lieu de33. Les IDs109/120..147 ne peuvent pas être déclarés inutilisés à partir des seules capacités. Sources/offsets/SHA dans le CSV ; conventions [IESDP op140/op141](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op141). Scripts/opcodes dynamiques hors scan : aucune preuve universelle d'inutilisation.
- **31 668 contrats natifs du registre passants** : cycles, slots, phases, profils boucle/once, dimensions/centres ; probe du chargeur actuel, 0lectureRGBA. Cas SPMAGMIS : règle V14 explicite64×64→lookup64×78→placement FX variable, preuve finale conservée ; aucune exemption générique de géométrie.
- **25 017 backings / 13 080 150 976 octets couverts SHA, 0écart**, 195ressources installées concernées. `physical-baseline/` conserve le contrôle SHA initial borné ; `physical.json` réutilise ses24 991backings avec même manifeste + existence/taille actuelles et26nouveaux backings rehashés. Carriers natifs vérifiés SHA. Aucun rehash release/global.
- DLL installée `5A1559B5…3106612B`, EXE `B51093A4…4E04D57`, registre/manifeste inchangés ; sources du pont comparées aux SHA du reçu final-four. Aucune installation, trace, compilation, inférence ou release modifiée.

## Exceptions actives uniquement

| Famille | Propriétaires moteur | Écart vérifié | Travail restant |
|---|---|---|---|
| SHWATER |120/123/126/129/132/135/138/141 ;680références op141 | Pack accepté installé, cellule absente du scope secondaire ;transfert de palettes SHWATER1..7 absent | Raccorder SpellHit et ajouter la palette réalisée par cellule, comme SHAIR/SHEARTH. Réutiliser les images. |
| FLMSTRK |145 ;2références op141(type35) ;66 partage la même famille sans pilote scanné | Pack accepté installé, scope secondaire absent sur SkyStrike | Raccorder/qualifier cette route ;0production image. |
| SPDIMDR1 + SPDIMDR2 |109 ;17références op141(type38) | Factory `SPDimDr`+`2`, Update suffixes`1`/`2`, Render235a10→FX29e260 ;2packs acceptés installés, scope absent | Raccorder les2phases et qualifier le cycle de vie2→1→2. Les suffixes sont prouvés par code natif, pas déduits d'une ressemblance de nom. |
| SPBOOM recoloré |142/143/144 ;40références op141(types32/33/34) | Constructeur appelé227b10→SPBOOM ;range0 changée par235d80 vers MPALETTE67/65/69 ;pont actuel sans transfert de ces palettes | Qualifier/transférer ces3couleurs dans la copie d'upload GPU. La QA du SPBOOM neutre/Fireball récemment accepté reste acquise. |

- Preuve machine : `exceptions.json`. Exceptions de raccord/palette ;**aucune nouvelle inférence identifiée**, aucun CLUA ni nouveau test manuel préparé. Une nouvelle observation éventuelle se limitera aux différences visuelles après correction.
- Contrôle couleur ciblé : `palette-exception-check.json`. SHWATER1..7 :tables217entrées,tous les indices réellement utilisés couverts,213entrées utilisées changées par variante ;SPBOOM67/65/69 :les12indices de range0 sont utilisés et changent. Ce sont des différences RGB natives effectives ;qualifier aussi les queues des tables BMP courtes avant d'étendre le transfert.
- La qualification des neutres/variantes déjà couverts n'impose aucun retest. Les10omissions du lot précédent restent corrigées ;ces4familles viennent du scan élargi aux opcodes/constructeurs auxiliaires.

## Écarts sans pilote dans le scan courant

- `LIGHTSTO/MAGMIS` (source manquante), IDs21/24/25→`SPBRNHND`,44→`SPSMKJET`,96→`COLRSPRY` (BAM stock présent, absent du catalogue),241→`SPHOLYMT` : **8propriétaires /5familles**. Conservation native ;pas de substitution ni de production spéculative. Identifiants conservés dans `owners.json`, pas dans la liste active.
- Faux positifs écartés : SPSHADOW reste un masque natif, VVC SHAREAW possède son propre scope Render et n'a pas besoin d'une entrée secondary_scope. LIGHTCHA5/7/9 sont des périodes ;opcodes141/140 sont de vrais lanceurs, contrairement au champ de provenance d'un EFF.
- Le repli natif pour composition/palette/opacité non supportée reste intentionnel. Absence de drawHD enregistré pour un alias ≠nouveau défaut ou obligation de test. SPSCORIC conserve sa qualification9cycles et QA antérieure ;aucun drawlive inventé.

## Reproduction

```powershell
python -B pipeline/recipes/projectiles-owner-reconciliation-20261110-v1/reconcile.py --output projectiles/analysis/<nouvelle-version>
python -B pipeline/recipes/projectiles-owner-reconciliation-20261110-v1/status.py
```

- `--metadata-only` réservé au diagnostic, publication refusée ;réutilisation SHA optionnelle bornée au manifeste/ressources de la preuve citée. Ne jamais réécrire ce résultat final.
- `publication.json` contrôle la conservation QA/installation/release et lie320propriétaires au résultat. Déplacement PROJ-MOTION-001 reporté ;release distincte.
