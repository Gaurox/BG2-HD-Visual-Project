# Characters palettisés — entrée Q3m dédupliquée

- Entrée de production : `pipeline/scripts/palette_playable.py`.
- Plan source actif : `sprite/index/palette-work-plan.json` ; ne représente ni production, ni QA, ni installation, ni release.
- Analyse initiale : `docs/measurements/playable-palettized-frame-dedup-20261001-v1/` ; 78 modèles, 4 510 BAM, 563 969 tâches complètes uniques / 13 677 041 occurrences.
- Corps/armures, casques, boucliers, armes ; profil Character, Q3m K6, six fits, sans B/tramage. x2 et x4 séparés.

## Commandes

Depuis la racine, Python `config://chainner_python` :

```powershell
$q3mPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
# CPU seulement : contrôle du plan actif + décompte exact de la sélection.
& $q3mPython -B pipeline/scripts/palette_playable.py plan --scale 4
& $q3mPython -B pipeline/scripts/palette_playable.py plan --scale 4 --animation-id 0x6110

# À lancer seulement quand la production est demandée : GPU pour les tâches manquantes.
# Sans --animation-id : tous les modèles du plan ; option répétable pour une sélection.
& $q3mPython -u -B pipeline/scripts/palette_playable.py run --scale 4

# Assemblage expérimental, sans GPU : consomme exclusivement le cache déjà complet.
& $q3mPython -u -B pipeline/scripts/palette_playable.py pack --scale 4 --output sprite/.work/q3m-playable-x4-test-v1
```

`pack` crée un catalogue V6 expérimental dans un dossier neuf. Aucun remplacement de catalogue canonique, installation, DLL, QA ou release. Toute production GPU est annoncée avant lancement ; les commandes ci-dessus ne constituent pas une autorisation de produire maintenant.

## Chemin effectif

1. `WorkPlan` vérifie SHA/taille/statut du SQLite, hashes des sources d'index et noyaux, scalepix et couverture des modèles/ressources. Un plan absent est reconstruit sur CPU vers un nouveau snapshot ; aucun chemin de production sans déduplication.
2. `run` adopte d'abord les résultats disponibles des essais Q3m natifs vérifiés `0x6110` x2 v3 / x4 v5 : metadata épinglée, source/échelle/fits/encodeur compatibles, SHA du shard V6, géométrie/representatives, I/F/dep comparés. Les NPZ seuls et anciens Q0 ne sont pas admissibles.
3. Queue unique globale → `SharedPixelProcessor`. Mathématiques `PixelProcessor.process/encode` inchangées ; clé = identité indexée/RGB utilisés du plan. Marqueurs/transparents sans GPU.
4. Cache persistant `sprite/.work/palette-q3m-shared/x<scale>/<namespace>/work/encoded/` ; recette figée et verrou OS exclusif. Hit seulement après validation des membres/tailles NPZ, dtypes, géométrie, guide, F/classes/spéciaux et `dep_mask`. Données invalides rejetées ; reprise relit les résultats terminés.
5. `pack` matérialise chaque ressource native une fois : source SHA, indices de frames, centres x1 signés, representatives et cycles d'origine. Un même BAM partagé réutilise un composant V6 dans les routes des différents modèles. Aucune fusion de palettes colorées par acteur/couche.

Le partage porte sur les résultats **I/F/dep** du même profil/échelle. L'option de partage séparé des cibles neurales décrite dans l'analyse n'est pas utilisée : queue complète de frames, 563 797 tâches coûteuses au maximum avant reprise des résultats existants.

## Persistance / changement de sources

- SQLite de 550 MiB ignoré par Git ; scripts, pointeur SHA, contrat, bilan et preuves committés. Les BAM natifs et fixtures P1 restent des dépendances locales du domaine.
- Reconstruction explicite : `palette_playable.py restore-plan` ; nouveau dossier d'analyse, vérification CPU indépendante, puis remplacement du seul pointeur source actif.
- Autre snapshot déjà vérifié : `palette_playable.py activate --database <chemin-dans-le-depot>/processing-plan.sqlite`.
- Source/noyau/fits incompatibles : arrêt explicite ; produire un nouveau plan/profil compatible. Ne jamais modifier le snapshot initial ni les essais historiques pour contourner l'arrêt.
- `palette_complete.py` conserve le constructeur historique de l'essai `0x6110` et fournit le calcul pixel éprouvé. Le traitement de série Q3m passe par `palette_playable.py`.

## Vérification ciblée

```powershell
& $q3mPython -B -m unittest pipeline.tests.test_playable_frame_dedup pipeline.tests.test_palette_playable pipeline.tests.test_palette_complete pipeline.tests.test_palette_frac_encode pipeline.tests.test_palette_registry pipeline.tests.test_test_changed
```

Tests de pipeline : réutilisation entre modèles et après reprise, pas d'initialisation GPU sur hits, namespaces x2/x4, source/centres/cycles/representatives, composant BAM commun, catalogue V6, rejet de plan/cache/NPZ invalides, verrou, ancien Q0 et NPZ non conformes au shard natif vérifié. Aucun résultat n'en déduit une QA globale ou ingame.
`test_changed.py` relie explicitement l'analyse et le module de plan partagé à ces suites ; une modification de ces modules ne sélectionne pas une liste vide de tests.
