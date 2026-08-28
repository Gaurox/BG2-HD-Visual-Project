# Pipeline d'upscale des maps — méthode validée

> **Séquence, branches et critères de passage : [README.md](README.md).** Cette page ne décrit
> que la politique de résolution et le détail de l'upscale.

Cette page décrit uniquement la méthode retenue pour les prochaines zones. Les essais,
comparaisons et réglages rejetés sont archivés dans
[`archive/tests-upscale/AR0602/ARCHIVE_ESSAIS_AR0602.md`](../archive/tests-upscale/AR0602/ARCHIVE_ESSAIS_AR0602.md)
et les échecs de paramètres dans
[`archive/tests-upscale/AR0602/ECHECS_PARAMETRES_MODELES.md`](../archive/tests-upscale/AR0602/ECHECS_PARAMETRES_MODELES.md).

## Politique de résolution validée

- **Toute zone : SeedVR2 7B x4/LAB par défaut.** Le x4 est désormais la résolution de référence.
- **Découpage :** appliquer obligatoirement
  [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md) : direct jusqu'à environ 1 200×1 500 px
  (1,80 Mpx), puis 2, 4, 6, 8 ou 10 morceaux selon la surface. Les plus grandes maps (> 14,40 Mpx
  x1) utilisent une grille 2×5 à recouvrement, avec des coupes ajustées d'une tuile si nécessaire
  pour rester sur une frontière de 64 px.
- **x2 uniquement sur demande explicite de l'utilisateur**, notamment pour réduire le poids ou
  accélérer une itération.

Les deux variantes techniques (`tuiles-principales` et `tuiles-secondaires`) utilisent toujours
la même échelle pour une zone donnée.

### Portes WED secondaires

Une porte WED échange des tuiles complètes de 64×64 px. Produire donc le rendu SeedVR2 7B de la
variante secondaire en même temps que le principal, à la même échelle. Lorsqu'un masque CGI corrige
une zone qui apparaît dans les deux états, employer le même masque et la même largeur de fondu sur
les deux composites. Toute exception visuelle doit être décidée par l'utilisateur et documentée
dans le run.

## Zones avec eau

Avant de traiter une zone dont le WED contient une couche liquide, appliquer obligatoirement la
procédure dédiée : [WATER_MAP_PIPELINE.md](WATER_MAP_PIPELINE.md). Elle restaure les alphas des
deux variantes, réutilise l'overlay d'eau déjà upscalé sans refaire d'inférence, libère les
tuiles d'eau de base entièrement opaques et **adoucit le contour de rive**.

En pratique, une zone d'eau se construit avec `--transparent-full-water-base --soften-water-contours`
et reste en DXT5. Sans ces drapeaux, l'eau animée reste masquée par des aplats fixes et la rive
apparaît en marches de 64 px. Cette branche couvre aussi `WTSWAM`, `WTSEW` et `WTOIL`, dont les
overlays restent stock ; un build x1 DXT5 peut être utilisé uniquement pour réparer leurs alphas
de zone, sans relancer d'inférence.

## Référence finale AR0602

- **Base historique : SeedVR2 7B/LAB x4**, grille 2×5 de dix morceaux à recouvrement, validée
  par l'utilisateur. AR0602 fait 4 928×3 584 px (17,66 Mpx x1) : ce palier correspond aujourd'hui
  aux dix morceaux prescrits par [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md) — voir aussi
  AR0700, qui a confirmé sur le palier maximal (19,66 Mpx) qu'une grille 2×4 à huit morceaux peut
  se bloquer là où le 2×5 à dix morceaux termine sans incident.
- **Deux PNG distincts :** `tuiles-principales` et `tuiles-secondaires` sont inférés et assemblés
  séparément ; aucun masque CGI et aucun composite ne sont utilisés.
- **Zone opaque : DXT1 automatique.** Build : 2 200 tuiles upscalées, 0 rééchantillonnée,
  0 OOB, PSNR `39,59 dB`; coutures maximales `0,045 σ`.
- Le run de production est
  `maps/AR0602/runs/seedvr2-7b-int8-lab-grid-2x5-x4-png-review/`.
  Les anciens essais x2/CGI restent archivés comme points de comparaison, sans être actifs.

## Procédure de production

0. **Qualifier la zone avant toute inférence :**

   ```powershell
   python pipeline/scripts/audit_area_preflight.py ARxxxx <run>/00_preflight/ARxxxx-preflight.json
   ```

   Exiger `blockers: []`, puis lire les procédures listées dans `routes`. Cette gate détecte les
   masques alpha, les secondes variantes WED, l'eau et les paires jour/nuit. Voir
   [AREA_PREFLIGHT.md](AREA_PREFLIGHT.md).

1. **Contrôler l'intégrité des rendus maîtres x1 avant toute inférence :**

   ```powershell
   python pipeline/scripts/validate_x1_masters.py --area ARxxxx
   ```

   Exiger `OK` sur les deux variantes. Un maître corrompu se propage sans être détecté : SeedVR
    l'agrandit fidèlement, le build le découpe fidèlement, le moteur l'affiche fidèlement. C'est
    le seul point de contrôle possible. Le verdict AR0300 est conservé dans
    [`../docs/DECISIONS.md`](../docs/DECISIONS.md).

### Rendus maîtres et extraction

Les deux rendus x1 (`tuiles-principales` et `tuiles-secondaires`) sont extraits pour les
369 zones du catalogue dans `maps/ARxxxx/rendus-x1/tuiles-*/ARxxxx-tuiles-*-x1.png`.

Pour actualiser ou compléter les rendus manquants, lancer :

```powershell
python pipeline/scripts/batch_extract.py
python pipeline/scripts/batch_extract_secondary.py
```

`render_secondary.py` reste disponible pour traiter une zone individuelle.

2. Utiliser les deux rendus x1 de la zone lorsque le préflight route vers
   [SECONDARY_TILE_PIPELINE.md](SECONDARY_TILE_PIPELINE.md) ; sinon, la primaire suffit au build.
3. Choisir l'échelle selon la politique ci-dessus, puis produire les rendus SeedVR2 7B requis avec
   le workflow de référence : `euler`, `simple`, une étape, CFG `1`, denoise `1`, VAE FP16 et
   `color_correction_method: lab`.
4. Pour toute grande zone x4, employer le nombre de morceaux prescrit par
   [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md) : `--split-grid 2 4` (huit morceaux)
   jusqu'à 14,40 Mpx x1, `--split-grid 2 5` (dix morceaux) au-delà. Chaque morceau est coupé sur
   des frontières de tuile, garde `128 px` x1 de contexte interne, puis les marges de `512 px` x4
   sont retirées avant juxtaposition sans fondu.

   ```powershell
   python pipeline/scripts/run_seedvr_comfyui.py --area ARxxxx --run <run> --preflight <run>/00_preflight/ARxxxx-preflight.json --tile-kind tuiles-principales --split-grid 2 5 --scale 4 --expected-scale 4
   python pipeline/scripts/run_seedvr_comfyui.py --area ARxxxx --run <run> --preflight <run>/00_preflight/ARxxxx-preflight.json --tile-kind tuiles-secondaires --split-grid 2 5 --scale 4 --expected-scale 4 --append
   ```

   Adapter `--split-grid` au palier réellement applicable (`2 2`, `2 3`, `2 4` ou `2 5`) : ne pas
   reprendre `2 5` par défaut pour une zone plus petite.

    **Ne jamais raccorder deux inférences bord à bord.** L'ancien splitter sans recouvrement produit
    précisément des moitiés sans recouvrement : il ne doit pas être utilisé.

### Découpe à recouvrement : contrôle et cas manuel

Pour chaque zone découpée, vérifier que les dimensions sont des multiples de `128`, qu'il n'y a
pas de décalage, puis mesurer la discontinuité de couture :

```powershell
python pipeline/scripts/check_seam.py --area ARxxxx --run <run> [--tile-kind tuiles-secondaires] [--zoom]
```

L'outil lit la géométrie de découpe dans le `run.json` du run, mesure **chaque** couture interne
(grille comme coupe en lignes) et rapporte la plus forte. L'objectif est une couture `< 3 σ`.
Pour ne pas confondre un relief déjà discontinu dans le rendu maître avec un raccord artificiel,
il accepte aussi une couture qui n'amplifie pas de plus de `1,5×` le saut local mesuré au même
endroit dans le x1. Toute autre valeur reste à inspecter dans les zones détaillées traversées par
la jonction ; `--zoom` écrit un aperçu de chaque couture dans `06_qa/seam-checks/`.

> **La valeur en σ dépend de la méthode de mesure et n'est comparable qu'entre runs mesurés par
> cet outil.** Points de calibration relevés le 2026-08-19 : AR0601 (coupe en lignes, validée)
> `1,25 σ` ; AR0602 (grille 2×5, référence validée) `3,19 σ`. Les valeurs en σ inscrites dans les
> notes d'`areas.csv` avant cette date proviennent de mesures ponctuelles antérieures et ne sont
> pas reproductibles par cette commande : ne pas les comparer directement.

Le découpage est géré directement par `run_seedvr_comfyui.py --split-grid COLONNES LIGNES`. Il
répartit les parties aussi régulièrement que possible, sur des frontières de tuile, conserve
`128 px` x1 de contexte de chaque côté, puis retire `512 px` x4 aux bords internes avant
juxtaposition sans fondu ni correction de couleur supplémentaire. Le découpage manuel historique
ne doit pas être employé pour une nouvelle zone.

Pour une petite zone, un rendu x1 complet peut être soumis directement en x4, par exemple :

```powershell
python pipeline/scripts/run_seedvr_comfyui.py --area ARxxxx --run seedvr2-7b-direct-x4 --preflight <run>/00_preflight/ARxxxx-preflight.json --scale 4 --expected-scale 4
```

Les références suivantes sont des validations historiques x2, antérieures à la règle x4 actuelle :
AR0602 (`4928×3584`) a validé une coupe à `y=1792` : deux parties `4928×1920` sont devenues
`9856×3840`, puis l'ensemble a été assemblé en `9856×7168`; la couture est indécelable visuellement et mesure
`+1,76 σ`. AR0300 a aussi été validée (`5120×3840` vers deux parties `5120×2048`, puis
`10240×7680`). AR0500, assemblée en
`10240×7680`, ne présente aucun décalage et sa couture mesure `+2,5 σ`.

La résolution maximale qu'un SeedVR2-7B peut traiter en une image reste à déterminer afin de
ne découper que lorsque c'est nécessaire. Les exécutions et comparaisons antérieures sont dans
[`archive/tests-upscale/AR0602/ARCHIVE_ESSAIS_AR0602.md`](../archive/tests-upscale/AR0602/ARCHIVE_ESSAIS_AR0602.md).

### Correction colorimétrique conditionnelle

Les upscaleurs génératifs peuvent dériver en teinte, saturation et courbe de tonalité. Si une
dérive est mesurée, insérer la correction après l'upscale et l'assemblage, avant le build :

```powershell
python pipeline/scripts/color_match.py <original-x1.png> <upscale-xN.png> <sortie-xN.png> [table.npy]
```

`color_match.py` réalise une égalisation d'histogramme par canal, avec lissage sur trois niveaux
et monotonie forcée. L'upscale est ramené à la résolution de l'original pour la comparaison, puis
la table est appliquée à l'image pleine résolution. Le fond noir hors-zone est exclu du modèle et
reste noir.

Avec SeedVR2 7B et `color_correction_method: lab`, aucune retouche colorimétrique supplémentaire
n'est requise. Réserver ce script aux futures zones qui révèlent une dérive mesurée : les
paramètres sont propres à la zone et ne doivent pas être repris d'un essai historique.

5. Si l'utilisateur fournit un masque, générer l'équivalent CGI neutre de la variante à l'échelle
   retenue et composer : `composite = CGI × masque flouté + SeedVR × (1 − masque flouté)`.
6. Construire les assets avec :

   ```powershell
   python pipeline/scripts/build_upscaled_area.py ARxxxx <principale-xN.png> <build-dir> <secondaire-xN.png>
   ```

   Le build doit annoncer `0 resampled` pour les rendus fournis.
7. Vérifier obligatoirement :

   ```powershell
   python pipeline/scripts/verify_upscaled.py ARxxxx <build-dir> <principale-xN.png>
   ```

   Exiger `out-of-bounds tiles: 0` et un PSNR de reconstruction proche de `40 dB`.
8. Jeu fermé : sauvegarder les fichiers actifs de l'override, copier les fichiers du build,
   comparer leurs SHA-256, puis lancer exclusivement `InfinityLoader.exe` depuis la racine du jeu.
9. Faire quatre captures en jeu, les renommer et les classer dans `06_qa/screenshots/` du run.
10. **À la fin de chaque tâche, demander explicitement si les éléments validés doivent être
    intégrés au manifeste de release.** Poser : « La tâche `<nom>` est terminée. Veux-tu que
    j'intègre au manifeste de release les éléments validés par cette tâche ? » Aucune écriture de
    `$mapSpecs`, `content.json`, staging ou archive sans un oui explicite. Si aucun élément n'est
    `validated-installed`, le signaler et ne rien intégrer; les éléments `pending-qa` restent
    inéligibles. En cas de refus ou de report, le consigner dans le compte rendu.
11. **Proposer séparément la mise à jour du catalogue à l'utilisateur, qui confirme ou refuse.**
    Puis `python pipeline/scripts/refresh_area_catalog.py` et renseigner à la main
    `runs`/`build`/`status` (et leurs équivalents `_nuit`) dans `areas.csv`. Voir
    [`README.md`](README.md) étape 8.

## Références verrouillées

- Séquence complète et critères de passage : [`README.md`](README.md).
- Workflow SeedVR 7B : `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-7B.api.json`.
- Contrôle d'intégrité des sources : `pipeline/scripts/validate_x1_masters.py`.
- Découpe à recouvrement : `run_seedvr_comfyui.py --split-grid 2 4` ou `2 5` pour toute grande
  zone x4, selon le palier prescrit par [`MAP_SPLITTING_POLICY.md`](MAP_SPLITTING_POLICY.md).
- Format de build : atlas 2 048 px, 49 tuiles/page (7×7), bordure répliquée 4 px. Le mode
  `--wed-regions-1024` est obsolète et ne doit pas être employé.
- Paramètres Topaz CLI : `pipeline/TOPAZ_GIGAPIXEL_CLI_REFERENCE.md`.
- Règles de formats, d'injection et de vérification : [`README.md`](README.md).
