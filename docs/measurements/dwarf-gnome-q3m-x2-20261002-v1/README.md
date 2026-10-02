# Nains / gnomes — Q3m K6 x2

- Portée monde : 16 nains (8 normaux, 8 LOW) + 8 gnomes ; prêtre, guerrier, mage, voleur ; hommes/femmes.
- Registre réutilisé : `sprite/index/palette-work-plan.json` ; SQLite existant ouvert en lecture seule ; aucun nouveau scan des frames sources.
- `selection.json` : 24 IDs, ressources/profils, alias exacts, compteurs/cache avant lancement, exclusions.
- Liste exhaustive : `sprite/.work/q3m-dwarf-gnome-x2-20261002-v1/work-list.csv` (ignorée), SHA dans la sélection ; work_id/key → consommateurs, cache/GPU/spécial, partage avec les humains. Géométrie/cycles/palettes et correspondances par occurrence dans le SQLite existant.
- 1 369 BAM ; 4 147 512 occurrences → 166 078 traitements uniques : 962 résultats humains déjà en cache, 165 083 nouveaux GPU, 33 spéciaux sans GPU.
- 155 710 tâches partagées entre modèles sélectionnés ; 1 981 849 répétitions de tâches entre modèles évitées.
- 8 alias LOW/nains normaux exacts. Gnomes : `height_code_shield=WQH` contre code vide des nains ; ressources monde différentes, même lorsque le corps est commun. Gnomes féminins prêtre/guerrier : `CIFB` ; voleur : `CIFT` ; mage : `CDFW`. Aucune assimilation globale gnome/nain ; partage seulement par clé exacte du registre.
- Clé : dimensions + transparence + pixels indexés + RGB des indices utilisés ; pas de rapprochement visuel, recadrage, miroir ou rotation. Centres/cycles conservés par occurrence pour l'assemblage ultérieur.
- Hors profil : `0x4600 SLEEPING_DWARF`, format `town_static`. Paperdolls/inventaire exclus, pipeline UI séparé.
- `run.py` appelle le producteur existant sans modifier les maths ; cache Q3m x2 partagé, namespace épinglé, verrou exclusif, hits et nouveaux résultats validés par le producteur. Aucun humain commun recalculé.
- `production.json` : production terminée, 166 078 résultats uniques ; 962 réutilisés, 165 083 nouveaux GPU, 33 spéciaux sans GPU, 990 498 cibles neurales. Sortie producteur 0 ; couverture/cache/géométrie/index/classes/F/dep vérifiés par ses invariants intégrés.
- État `encoded-not-native-or-ingame-verified` ; assemblage natif/installation/QA/release non déduits.
- Run achevé : relancement refusé pour préserver le bilan ; nouvelle version pour une nouvelle production, cache partagé conservé.

```powershell
$dwarfPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
& $dwarfPython -u -B docs/measurements/dwarf-gnome-q3m-x2-20261002-v1/run.py
```
