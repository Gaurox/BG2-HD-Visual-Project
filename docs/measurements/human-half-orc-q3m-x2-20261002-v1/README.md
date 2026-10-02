# Humains / demi-orcs — Q3m K6 x2

- Portée monde : 18 humains (10 normaux, 8 LOW) + 8 demi-orcs ; guerrier, prêtre, mage, voleur, moine ; hommes/femmes.
- Registre réutilisé : `sprite/index/palette-work-plan.json` ; `processing-plan.sqlite` ouvert en lecture seule. Aucun nouveau scan source ni audit exhaustif.
- `selection.json` : sélection exacte, équivalences de ressources/profils, compteurs et état du cache avant lancement.
- Liste exhaustive des traitements uniques : `sprite/.work/q3m-human-half-orc-x2-20261002-v1/work-list.csv` (ignorée), SHA dans `selection.json` ; work_id/key → consommateurs et action. Correspondances resref/frame/centres/cycles dans le `frame_map` SQLite existant.
- 4 601 133 occurrences → 232 780 traitements uniques ; 190 532 en cache, 2 671 réutilisables du run guerrière, 39 577 nouveaux calculs.
- 16 alias LOW/demi-orcs : mêmes ressources monde, zéro calcul supplémentaire. Les paperdolls demi-orcs sont distincts et exclus de ce lot.
- Hors profil : cinq humains legacy/statiques listés dans `selection.json` ; monstres orcs `MOR1`–`MOR5` distincts ; inventaire via pipeline UI séparé.
- `run.py` reprend uniquement les clés/ressources historiques manquantes, puis appelle `palette_playable.produce` sans modifier ses maths, sa validation des hits ou son cache partagé.
- `production.json` : calcul terminé, 232 780 résultats ; 193 203 réutilisés, 39 577 nouveaux, 237 462 cibles neurales. État encodé ; assemblage natif/installation/QA/release non déduits.
- Run achevé : relancement refusé pour préserver le bilan. Nouvelle production dans une nouvelle version ; cache partagé conservé.

```powershell
$humanPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
& $humanPython -u -B docs/measurements/human-half-orc-q3m-x2-20261002-v1/run.py
```
