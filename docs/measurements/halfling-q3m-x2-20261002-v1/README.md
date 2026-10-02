# Halfelins — Q3m K6 x2

- Portée monde : 12 IDs Character (6 normaux, 6 LOW) ; prêtre, guerrier, voleur ; hommes/femmes. Aucun ID mage halfelin dans l'inventaire actuel.
- Dernier lot Character confirmé : SQLite = inventaire = 78 modèles ; bilans humains/demi-orcs 26 + nains/gnomes 24 + elfes/demi-elfes 16 = 66 IDs distincts ; différence exacte = les 12 halfelins sélectionnés. QA/installation/release non déduites de cette couverture de production.
- Registre réutilisé : `sprite/index/palette-work-plan.json` ; SQLite existant ouvert en lecture seule. Aucun nouveau scan des pixels sources ni audit global des résultats précédents.
- `selection.json` : IDs/profils/ressources, alias exacts, compteurs/cache avant lancement, exclusions, comparaison des IDs aux trois bilans de production compatibles avec le même SHA source/namespace/échelle.
- Liste exhaustive : `sprite/.work/q3m-halfling-x2-20261002-v1/work-list.csv` (ignorée), SHA dans la sélection ; work_id/key → consommateurs, cache/GPU/spécial, partage avec chacun des trois lots précédents. Correspondances resref/frame/palette/centres/cycles dans le SQLite existant.
- 978 BAM ; 2 040 492 occurrences → 123 751 traitements uniques : 104 575 résultats en cache, 19 176 nouveaux GPU, zéro nouveau spécial.
- Commun avec les humains/demi-orcs : 963 tâches ; nains/gnomes : 104 574 ; elfes/demi-elfes : 580 ; union 104 575, compteurs non additifs. Les gnomes féminins utilisent déjà beaucoup de corps `CIF*`, les équipements `WQS*` sont largement communs.
- Femmes : 100 % des tâches déjà en cache pour les 6 IDs féminins ; nouveaux calculs uniquement sur les modèles masculins. Nouveau par modèle normal/LOW : prêtre 9 388, guerrier 9 396, voleur 9 788 ; union globale 19 176, pas la somme de ces compteurs.
- 6 alias LOW/normaux exacts ; 917 093 répétitions de tâches entre modèles évitées. Aucun doublon recalculé ; classes/sexes/armures/équipements gardent leurs routes et différences.
- Clé : dimensions + transparence + pixels indexés + RGB des indices utilisés ; aucune fusion visuelle, recadrage, miroir ou rotation. Centres/cycles conservés par occurrence pour l'assemblage ultérieur.
- Hors profil : `0x4800 SLEEPING_MAN_HALFLING`, format `town_static`. Paperdolls/inventaire exclus, pipeline UI séparé.
- `run.py` appelle le producteur existant sans modifier les maths ; cache Q3m x2 partagé, namespace épinglé, verrou exclusif, hits/nouveaux résultats validés par ses invariants intégrés. Toute clé commune aux lots précédents manquante arrête l'analyse.
- `production.json` : production terminée, 123 751 résultats uniques ; 104 575 réutilisés, 19 176 nouveaux GPU, zéro nouveau spécial, 115 056 cibles neurales. Sortie producteur 0 ; couverture/cache/géométrie/index/classes/F/dep vérifiés par ses invariants intégrés.
- Couverture finale des IDs source Character : 78/78, aucun ID restant ; constat issu de ce lot + les trois bilans précédents compatibles, sans audit global relancé. Aucun registre global de QA/installation/release créé.
- État `encoded-not-native-or-ingame-verified` ; assemblage natif/installation/QA/release séparés.
- Run achevé : relancement refusé pour préserver le bilan ; nouvelle version pour une nouvelle production, cache partagé conservé.

```powershell
$halflingPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
& $halflingPython -u -B docs/measurements/halfling-q3m-x2-20261002-v1/run.py
```
