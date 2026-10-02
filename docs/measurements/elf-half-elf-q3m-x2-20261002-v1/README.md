# Elfes / demi-elfes — Q3m K6 x2

- Portée monde : 16 IDs Character (8 normaux, 8 LOW) ; prêtre/druide, guerrier/rôdeur/paladin, mage/ensorceleur, voleur/barde ; hommes/femmes. Même découpage que les lots humains et nains/gnomes.
- Demi-elfes : pas d'IDs `HALF_ELF` distincts dans l'inventaire actuel ; préfixe monde `E` commun elfes/demi-elfes, selon [IESDP, Character](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/ini_anim.htm). Lecture ciblée du jeu stock : `RACE.IDS` = `3 HALF_ELF` ; `JAHEIR11/JAHEIR12.CRE` (`data/Creature.bif`) = race 3, sexe 2, animation `0x6111`. Aucun second calcul pour la race demi-elfe.
- Registre réutilisé : `sprite/index/palette-work-plan.json` ; SQLite existant en lecture seule. Aucun nouveau scan des pixels sources.
- `selection.json` : IDs/profils/ressources, alias exacts, scope demi-elfe, compteurs/cache avant lancement, exclusions.
- Liste exhaustive : `sprite/.work/q3m-elf-half-elf-x2-20261002-v1/work-list.csv` (ignorée), SHA dans la sélection ; work_id/key → consommateurs, cache/GPU/spécial, partage humains/demi-orcs et nains/gnomes. Géométrie/cycles/palettes et correspondances par occurrence dans le SQLite existant.
- 1 162 BAM ; 2 887 904 occurrences → 148 100 traitements uniques : 1 203 résultats déjà en cache, 146 875 nouveaux GPU, 22 spéciaux sans GPU.
- Commun avec les humains/demi-orcs : 987 tâches ; nains/gnomes : 579 ; union 1 203 (363 communes aux deux lots, compteurs non additifs).
- 8 alias LOW/normaux exacts ; 1 411 476 répétitions de tâches entre modèles évitées. Classes/sexes/armures/équipements conservent leurs routes et différences ; chaque clé globale est calculée une seule fois.
- Clé : dimensions + transparence + pixels indexés + RGB des indices utilisés ; aucune fusion visuelle, recadrage, miroir ou rotation. Centres/cycles conservés par occurrence pour l'assemblage ultérieur.
- Hors profil : `0x4700 SLEEPING_MAN_ELF`, `0x4710 SLEEPING_WOMAN_ELF`, format `town_static`. Paperdolls/inventaire exclus, pipeline UI séparé.
- `run.py` appelle le producteur existant sans modifier les maths ; cache Q3m x2 partagé, namespace épinglé, verrou exclusif, hits et nouveaux résultats validés par ses invariants intégrés. Source/profil des deux bilans précédents comparés à la sélection ; toute clé commune manquante arrête l'analyse.
- `production.json` : production terminée, 148 100 résultats uniques ; 1 203 réutilisés, 146 875 nouveaux GPU, 22 spéciaux sans GPU, 881 250 cibles neurales. Sortie producteur 0 ; couverture/cache/géométrie/index/classes/F/dep vérifiés par ses invariants intégrés.
- État `encoded-not-native-or-ingame-verified` ; assemblage natif/installation/QA/release non déduits.
- Run achevé : relancement refusé pour préserver le bilan ; nouvelle version pour une nouvelle production, cache partagé conservé.

```powershell
$elfPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
& $elfPython -u -B docs/measurements/elf-half-elf-q3m-x2-20261002-v1/run.py
```
