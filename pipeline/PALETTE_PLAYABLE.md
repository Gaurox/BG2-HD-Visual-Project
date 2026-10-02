# Characters palettisés — entrée Q3m dédupliquée

- Guide de reprise du processus complet et extension monstres/PNJ : [SPRITES_PRODUCTION_Q3M_X2.md](SPRITES_PRODUCTION_Q3M_X2.md). Ce module reste limité à `engine_section=character`, même pour les PNJ.
- Entrée de production : `pipeline/scripts/palette_playable.py`.
- Plan source actif : `sprite/index/palette-work-plan.json` ; ne représente ni production, ni QA, ni installation, ni release.
- Analyse initiale : `docs/measurements/playable-palettized-frame-dedup-20261001-v1/` ; 78 modèles, 4 510 BAM, 563 969 tâches complètes uniques / 13 677 041 occurrences.
- Corps/armures, casques, boucliers, armes ; profil Character, Q3m K6, six fits, sans B/tramage. x2 et x4 séparés.
- **État 2026-10-02 : production x2 complète, assemblée et installée BOX pour les 78 IDs.** [Génération](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/current-generation.json), [installation/vérification](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/README.md) : 4 510 BAM / 1 564 054 frames natives, aucun manquant ; QA visuelle globale et release distinctes. Cache x2 déjà rempli : ne pas refaire les lots historiques.

## Commandes

Depuis la racine, Python `config://chainner_python` :

```powershell
$q3mPython = (Get-Content -LiteralPath 'config/workspace-paths.local.json' -Raw | ConvertFrom-Json).paths.chainner_python
# CPU seulement : contrôle du plan actif + décompte exact de la sélection.
& $q3mPython -B pipeline/scripts/palette_playable.py plan --scale 2
& $q3mPython -B pipeline/scripts/palette_playable.py plan --scale 2 --animation-id 0x6110

# À lancer seulement quand la production est demandée : GPU pour les tâches manquantes.
# Sans --animation-id : tous les modèles du plan ; option répétable pour une sélection.
& $q3mPython -u -B pipeline/scripts/palette_playable.py run --scale 2
# Sélection répétable ; mêmes résultats partagés, pas une production isolée par ID.
# & $q3mPython -u -B pipeline/scripts/palette_playable.py run --scale 2 --animation-id 0x6100 --animation-id 0x6110

# Assemblage expérimental, sans GPU : consomme exclusivement le cache déjà complet.
& $q3mPython -u -B pipeline/scripts/palette_playable.py pack --scale 2 --output sprite/.work/q3m-playable-x2-new-test-v1
```

`pack` crée un catalogue V6 expérimental dans un dossier neuf. Aucun remplacement de catalogue canonique, installation, DLL, QA ou release. Toute production GPU est annoncée avant lancement ; les commandes ci-dessus ne constituent pas une autorisation de produire maintenant.
`--scale 4` reste disponible avec namespace/sorties distincts ; x2 + BOX est le choix monde actuellement installé. `plan` indique les tâches sources de la sélection, pas automatiquement le nombre de tâches GPU encore manquantes : cette dernière décision utilise le cache validé et les bilans de sélection.

## Chemin effectif

1. `WorkPlan` vérifie SHA/taille/statut du SQLite, hashes des sources d'index et noyaux, scalepix et couverture des modèles/ressources. Un plan absent est reconstruit sur CPU vers un nouveau snapshot ; aucun chemin de production sans déduplication.
2. `run` adopte d'abord les résultats disponibles des essais Q3m natifs vérifiés `0x6110` x2 v3 / x4 v5 : metadata épinglée, source/échelle/fits/encodeur compatibles, SHA du shard V6, géométrie/representatives, I/F/dep comparés. Les NPZ seuls et anciens Q0 ne sont pas admissibles.
3. Queue unique globale → `SharedPixelProcessor`. Mathématiques `PixelProcessor.process/encode` inchangées ; clé = identité indexée/RGB utilisés du plan. Marqueurs/transparents sans GPU.
4. Cache persistant `sprite/.work/palette-q3m-shared/x<scale>/<namespace>/work/encoded/` ; recette figée et verrou OS exclusif. Hit seulement après validation des membres/tailles NPZ, dtypes, géométrie, guide, F/classes/spéciaux et `dep_mask`. Données invalides rejetées ; reprise relit les résultats terminés.
5. `pack` matérialise chaque ressource native une fois : source SHA, indices de frames, centres x1 signés, representatives et cycles d'origine. Un même BAM partagé réutilise un composant V6 dans les routes des différents modèles. Aucune fusion de palettes colorées par acteur/couche.

Le partage porte sur les résultats **I/F/dep** du même profil/échelle. L'option de partage séparé des cibles neurales décrite dans l'analyse n'est pas utilisée : queue complète de frames, 563 797 tâches coûteuses au maximum avant reprise des résultats existants.

## Assemblage parallèle effectivement utilisé

- `pack` ci-dessus est séquentiel ; son option CLI `--workers` n'y ajoute pas de parallélisme.
- [assemble.py](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/assemble.py) : variante x2, 8 processus CPU, reprise d'un dossier non scellé ; vérifie source SHA, tous centres/dimensions/transparences/cycles et feuilles V6 avant publication du catalogue. Réutilise les mêmes `WorkPlan.materialize`, `ResultCache.load`, `palette_registry.write/inspect`.
- Invocation de référence pour **un nouveau dossier**, si un nouvel assemblage est demandé :

```powershell
& $q3mPython -u -B docs/measurements/playable-q3m-x2-ingame-20261002-v1/assemble.py --output sprite/.work/q3m-playable-all-x2-new-pack-v1 --workers 8
```

- Ne pas relancer dans `q3m-playable-all-x2-pack-20261002-v1`, déjà scellé. Reprise uniquement si ni `pack.json` ni catalogue final n'existent. Sous-processus = lectures SQLite/cache + écritures de feuilles distinctes, pas plusieurs producteurs GPU concurrents.
- [verify.py](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/verify.py) contrôle le pack/installation **courants** (paths/78 IDs/4 510 BAM/1 564 054 frames codés). `verify.py --installed` est relisible sans réécrire une preuve finale identique. Pour un autre pack/profil, adapter le vérificateur dans un nouveau run.
- [install.ps1](../docs/measurements/playable-q3m-x2-ingame-20261002-v1/install.ps1) conserve la baseline historique de 2 IDs ; ce n'est pas l'installateur d'une prochaine extension. Détails de conservation des 78 IDs, scope BOX global, restauration et limitations des helpers : [guide de production](SPRITES_PRODUCTION_Q3M_X2.md#installation-vérification-restauration).

## Persistance / changement de sources

- SQLite de 550 MiB ignoré par Git ; scripts, pointeur SHA, contrat, bilan et preuves committés. Les BAM natifs et fixtures P1 restent des dépendances locales du domaine.
- Reconstruction explicite : `palette_playable.py restore-plan` ; nouveau dossier d'analyse, vérification CPU indépendante, puis remplacement du seul pointeur source actif.
- Autre snapshot déjà vérifié : `palette_playable.py activate --database <chemin-dans-le-depot>/processing-plan.sqlite`.
- Source/noyau/fits incompatibles : arrêt explicite ; produire un nouveau plan/profil compatible. Ne jamais modifier le snapshot initial ni les essais historiques pour contourner l'arrêt.
- `palette_complete.py` conserve le constructeur historique de l'essai `0x6110` et fournit le calcul pixel éprouvé. Le traitement de série Q3m passe par `palette_playable.py`.
- Une génération scellée sous `.work` ou un cache référencé reste à conserver ; présence hors Git ne signifie pas jetable. Un fichier installé absent se recopie depuis le pack acquis, sans refaire l'inférence.
- Hors Character : nouveau plan/contrat et comparaison avec ce cache ; ne pas étendre silencieusement `palette-work-plan.json` ni annoncer une réutilisation inter-profils sur le seul hash d'image. Aucun `--monster`/`--all-sprites` n'est implémenté.

## Vérification ciblée

Suites utiles lorsque les modules correspondants changent ; pas un préalable à la lecture du suivi ou à une nouvelle sélection compatible déjà vérifiée :

```powershell
& $q3mPython -B -m unittest pipeline.tests.test_playable_frame_dedup pipeline.tests.test_palette_playable pipeline.tests.test_palette_complete pipeline.tests.test_palette_frac_encode pipeline.tests.test_palette_registry pipeline.tests.test_test_changed
```

Tests de pipeline : réutilisation entre modèles et après reprise, pas d'initialisation GPU sur hits, namespaces x2/x4, source/centres/cycles/representatives, composant BAM commun, catalogue V6, rejet de plan/cache/NPZ invalides, verrou, ancien Q0 et NPZ non conformes au shard natif vérifié. Aucun résultat n'en déduit une QA globale ou ingame.
`test_changed.py` relie explicitement l'analyse et le module de plan partagé à ces suites ; une modification de ces modules ne sélectionne pas une liste vide de tests.
