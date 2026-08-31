# Pipeline d'upscale des animations de zone BAM

## Périmètre

Ce pipeline automatise la production des assets **et** du pack consommé par le runtime générique :

```text
BAM canonique -> frames x1 alignées -> SeedVR x4 -> alpha source x4
-> frames natives x4 -> buffers RGBA bruts -> registre resref/cycles/frames
-> 03_runtime_pack validé
```

Il ne modifie jamais le jeu, la DLL, l'INI, `override` ou les catalogues. Le dossier
`03_runtime_pack` est une sortie hors ligne ; son installation réversible suit ensuite
[`../animations/UPSCALE_ANIMATIONS_ZONE.md`](../animations/UPSCALE_ANIMATIONS_ZONE.md).

Il s'agit du pipeline spatial **V1**, conservé comme autorité des ancres x4. Pour produire à côté
un pack temporel 15 -> 30 fps avec le registre v2 `TimedTimeline`, suivre
[`ANIMATION_UPSCALE_30FPS_V2.md`](ANIMATION_UPSCALE_30FPS_V2.md). La V2 consomme un run V1 terminé ;
elle ne le remplace et ne le réécrit jamais.

Référence validée en jeu le 2026-08-20 : les 13 BAM et 219 frames de `AR0602`, y compris les
géométries variables, via `AreaAnimations-X4.registry` et `EnableAreaAnimationX4=true` dans la
section `[Shaders]`.

Si le run est techniquement valide mais qu'une QA révèle un liseré ou le rectangle d'une frame,
ne pas modifier le run canonique : créer un prototype alpha isolé suivant
[`ANIMATION_ALPHA_CORRECTIONS.md`](ANIMATION_ALPHA_CORRECTIONS.md), puis l'installer de façon
réversible pour la QA.

Contrôler d'abord le flag ARE bit 1 (`0x0002`, « Blended ») de la ressource : s'il est mis, un
fond ou un halo ne vient pas de l'alpha et aucune correction alpha ne le retirera. Suivre
[`ANIMATION_BLENDED_RGB_NEUTRALISATION.md`](ANIMATION_BLENDED_RGB_NEUTRALISATION.md).

Si l'objectif est de remplacer les répétitions du cycle par de vraies images
intermédiaires, suivre [`ANIMATION_INTERPOLATION_PIPELINE.md`](ANIMATION_INTERPOLATION_PIPELINE.md).
L'agent doit proposer le nombre de frames, les FPS et la durée avant de demander l'export.

Si l'objectif est au contraire d'ajouter de vraies présentations entre toutes les positions
natives et de lire à 30 fps sans accélérer la boucle, employer la V2
[`ANIMATION_UPSCALE_30FPS_V2.md`](ANIMATION_UPSCALE_30FPS_V2.md).

Après chaque QA, renseigner le statut du BAM dans
[`../animations/ANIMATION_UPSCALE_REGISTRY.md`](../animations/ANIMATION_UPSCALE_REGISTRY.md).

## Commande principale

Script : `pipeline/scripts/run_animation_upscale.py`.

Prévisualiser un BAM sans écrire :

```powershell
python pipeline/scripts/run_animation_upscale.py --resref AM0205E --scale 4 --plan
```

Prévisualiser tous les BAM utilisés par une zone :

```powershell
python pipeline/scripts/run_animation_upscale.py --area AR0205 --scale 4 --plan
```

Préparer les sources et extraire les frames sans contacter ComfyUI :

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --resref AM0205E `
  --run am0205e-seedvr7b-lab-x4 `
  --scale 4 `
  --prepare-only
```

Lancer le traitement complet, ComfyUI/SeedVR déjà démarré :

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --resref AM0205E `
  --run am0205e-seedvr7b-lab-x4 `
  --scale 4
```

Pour un run x4 terminé, cette commande construit automatiquement
`animations/runs/<run>/03_runtime_pack`. Il ne faut plus lancer manuellement une étape de renommage
des `.rgba`.

## Composer le registre runtime global

Le runtime ne lit qu'un seul `AreaAnimations-X4.registry`. Avant un nouveau test en jeu, composer
le pack du lot avec les packs déjà actifs : ne jamais installer le seul `03_runtime_pack` d'un
nouveau lot si un autre pack x4 doit rester actif.

La composition ne relance pas SeedVR : elle relit les manifests, vérifie les SHA-256 et tailles de
tous les assets sources, reconstruit le registre puis écrit un nouveau pack immuable. Les resrefs
dupliqués entre deux packs sont refusés.

Exemple AR0205 A–D avec le pack AR0602 déjà validé et le correctif alpha de la lanterne conservé :

```powershell
python pipeline/scripts/build_animation_runtime_pack.py `
  animations/runs/ar0205-a-d-seedvr7b-lab-x4 `
  animations/runs/ar0205-a-d-seedvr7b-lab-x4/04_ingame_test/03_runtime_pack `
  --include-pack animations/runs/ar0602-all-bam-seedvr7b-lab-x4/03_runtime_pack `
  --alpha-override-manifest animations/runs/AM0602F-lanterne-canvas-feather-x4/manifest.json
```

`--alpha-override-manifest` accepte uniquement un manifeste de correction alpha validé : le resref,
le nombre de frames, les dimensions physiques, les noms, tailles et SHA-256 sont contrôlés avant
de remplacer les buffers correspondants dans le nouveau pack. Le manifeste de composition inscrit
la provenance et les empreintes de chaque pack et correctif source. Rejouer la même commande avec
`--resume` vérifie l'immuabilité sans réécrire le pack.

### Prototype x4 historique AM0205E

La migration ponctuelle d'AM0205E est terminée : son pack runtime matérialisé reste dans le run
historique et son ancien chemin `proto/` est résolu par `animations/index/path-migrations.json`.
Le migrateur one-shot est archivé et ne doit plus servir de point d'entrée. Pour une nouvelle
production, créer un nouveau run avec le pipeline V1 courant ; ne jamais réécrire ce pack ancien.

## Installation réversible du pack composé

Jeu et `InfinityLoader` fermés, utiliser les scripts génériques :

```powershell
.\pipeline\scripts\Install-AreaAnimations-X4-Pack.ps1 `
  -PackRoot .\animations\runs\ar0205-a-d-seedvr7b-lab-x4\04_ingame_test\03_runtime_pack
```

L'installateur vérifie chaque asset, crée une sauvegarde avec SHA-256, protège les assets existants
différents (seul le registre global est remplacé), active une seule clé
`EnableAreaAnimationX4=true` sous `[Shaders]` et ne lance jamais le jeu. Pour un comparatif A/B :

```powershell
.\pipeline\scripts\Set-AreaAnimations-X4-State.ps1 -Mode x1
.\pipeline\scripts\Set-AreaAnimations-X4-State.ps1 -Mode x4
```

Restaurer exactement le test, jeu fermé :

```powershell
.\pipeline\scripts\Restore-AreaAnimations-X4-Pack.ps1 `
  -BackupPath <dossier-x4-animation-backup>
```

Après une interruption, reprendre exactement le même run :

```powershell
python pipeline/scripts/run_animation_upscale.py `
  --resref AM0205E `
  --run am0205e-seedvr7b-lab-x4 `
  --scale 4 `
  --resume
```

Pour reprendre un run créé avec `--prepare-only`, employer la même commande avec `--resume`, sans
`--prepare-only`. Sur un run déjà terminé, `--resume` revalide les frames et le pack runtime sans
réécrire les manifests ni rappeler le GPU.

## Sélecteurs

- `--resref <BAM>` : traite une ressource BAM éligible ; option répétable.
- `--area <ARxxxx>` : développe les occurrences BAM à palette intégrée présentes dans
  `animations/index/occurrences.csv` ; option répétable. Les ressources WBM/PVRZ et les BAM à
  palette ARE externe sont exclues du plan avec un motif explicite.
- Les deux peuvent être combinés ; les doublons sont supprimés.
- Le pack final contient l'union de cette sélection. Comme le runtime ne charge qu'un seul registre,
  sélectionner ensemble toutes les zones/resrefs qui doivent coexister dans une installation.
- Un BAM partagé sélectionné par une zone sera upscalé partout où ce même resref est rendu.
- `--scale 4` est la valeur par défaut et la référence validée en jeu.
- `--scale 2` utilise le même protocole, mais demande une validation runtime séparée.

Toujours exécuter `--plan` avant une sélection par zone : une zone peut contenir plusieurs BAM et
des occurrences non éligibles au pipeline BAM.

## Arborescence d'un run

```text
animations/runs/<run>/
  manifest.json
  resources/<RESREF>/
    00_source/<RESREF>.bam
    01_frames_x1/
      manifest.json
      rgb/frame_XXX.png
      alpha/frame_XXX.png
      rgba/frame_XXX.png
    02_upscale_xN/
      manifest.json
      00_padded_x1/
      01_comfy_padded_xN/
      aligned_rgba/
      rgb/
      alpha/
      rgba/
      raw_rgba/frame_XXX.rgba
      preview/animation-xN-contact-sheet.png
  03_runtime_pack/                 # présent automatiquement pour un run x4 terminé
    manifest.json
    AreaAnimations-X4.registry
    AAX4-<RESREF>-frameXXX.rgba
```

Sémantique :

- `01_frames_x1/*` : canvas commun aligné sur les centres BAM ; sources du modèle.
- `aligned_rgba/` : résultat xN conservé sur ce canvas commun ; diagnostic temporel.
- `rgb/`, `alpha/`, `rgba/` : résultat recadré aux dimensions natives de chaque frame.
- `raw_rgba/` : asset runtime natif, RGBA8 compact, lignes haut vers bas.
- `03_runtime_pack/AreaAnimations-X4.registry` : resrefs, dimensions logiques natives et tables
  `cycles[].frame_indices` de toutes les ressources du run.
- `03_runtime_pack/AAX4-*.rgba` : copies déterministes vérifiées des buffers physiques x4.

Le moteur doit déclarer chaque texture avec `logical_size_x1` et téléverser le buffer avec
`physical_size_xn`. Ne pas employer les dimensions du canvas aligné comme dimensions logiques.

## Gates automatiques

### P0 — sélection

- resref de 1 à 8 caractères ;
- zone présente dans l'index ;
- BAM présent dans `animations/ressources/` ;
- SHA-256 du BAM identique à `animations/index/ressources.csv` ;
- workflow SeedVR2 7B identique au hash approuvé.

### P1 — extraction x1

- copie source immuable et vérifiée ;
- export dans un dossier `.partial`, renommé seulement après validation ;
- frames contiguës `frame_000.png` à `frame_NNN.png` ;
- RGB, alpha et RGBA présents, de même canvas ;
- SHA-256 enregistré pour chaque fichier ;
- dimensions natives, centre, offset de canvas et cycles conservés ;
- géométrie classée `uniform` ou `per-frame`.

### P2 — upscale

- RGB seul envoyé à SeedVR2 7B ;
- preset verrouillé : LAB, Euler/simple, 1 étape, CFG 1, denoise 1 ;
- marge x1 de 32 px par défaut ;
- sortie ComfyUI exigée aux dimensions exactes ;
- alpha x1 agrandi par nearest-neighbour, jamais généré ;
- canvas xN recadré avec `canvas_offset * scale` et `source_size * scale` ;
- PNG et RGBA brut vérifiés par dimensions, taille et SHA-256.

### P3 — fin du run

Exiger dans `animations/runs/<run>/manifest.json` :

```json
{
  "schema": "bg2-upscale-area-animation-run-v1",
  "status": "completed"
}
```

Chaque ressource doit aussi porter `status: completed`. Un run `prepared` n'a pas encore effectué
l'inférence. Un run `failed` se reprend avec `--resume` après correction de la cause.

### P4 — pack runtime x4

Pour tout run x4 `completed`, exiger dans `03_runtime_pack/manifest.json` :

```json
{
  "schema": "bg2-upscale-area-animation-runtime-pack-v1",
  "status": "completed",
  "scale": 4
}
```

Gates bloquantes :

- le SHA-256 du manifeste source correspond au run terminé et immuable ;
- le registre binaire est reproductible depuis les manifests x1/x4 ;
- tous les resrefs font 1 à 8 caractères ASCII et sont uniques ;
- les frames et cycles sont contigus ; chaque index de cycle pointe vers une frame valide ;
- chaque taille physique vaut exactement `logical_size_x1 * 4` ;
- chaque `.rgba` a la taille `physical_width * physical_height * 4` et le SHA-256 attendu ;
- aucun fichier ou sous-dossier supplémentaire n'est accepté lors d'une reprise.

## Reprise et immutabilité

- Un dossier non vide est refusé sans `--resume`.
- La reprise exige la même sélection, les mêmes sources, le même workflow, la même échelle et le
  même padding.
- Chaque frame terminée est revalidée par SHA-256, dimensions PNG et taille RGBA brute.
- Une sortie terminée modifiée provoque un arrêt ; elle n'est pas écrasée silencieusement.
- Seules les frames absentes sont renvoyées à ComfyUI.
- Un run déjà terminé est validé sans nouvel appel GPU et sans réécriture de son manifeste.
- `03_runtime_pack` est également immuable : `--resume` le recompile en mémoire, compare registre,
  inventaire, tailles et SHA-256, puis le réutilise sans écriture.
- Un dossier d'extraction `.partial` abandonné est supprimé uniquement sous la ressource du run,
  puis recréé lors de `--resume`.

## Géométries variables

Le pipeline prend en charge la préparation des frames dont dimensions ou centres diffèrent :

1. SeedVR travaille sur le canvas aligné commun.
2. Le résultat xN est recadré par frame vers son rectangle BAM natif.
3. Le manifeste conserve `logical_size_x1`, `centre_x1`, `canvas_offset_x1`,
   `runtime_crop_box_xn` et `physical_size_xn`.

Le registre runtime consomme les dimensions logiques de chaque frame. Les géométries
`per-frame` sont donc prises en charge ; `AR0602` constitue la validation en jeu de ce chemin.

## Construction ou validation manuelle du pack

La commande principale l'exécute automatiquement. Pour auditer un run déjà terminé :

```powershell
python pipeline/scripts/build_animation_runtime_pack.py animations/runs/<run> --resume
```

Sans `--resume`, le constructeur refuse un `03_runtime_pack` non vide. Il n'écrase jamais un pack
ambigu ou modifié.

## Commande bas niveau

Pour un dossier de frames déjà extrait :

```powershell
python pipeline/scripts/upscale_animation_frames.py `
  <frames-x1>/rgb `
  <frames-x1>/alpha `
  <sortie-x4> `
  --frame-manifest <frames-x1>/manifest.json `
  --scale 4
```

L'ancien wrapper `upscale_sprite_frames_x4.py` a été supprimé. Utiliser directement
`upscale_animation_frames.py`.

## Validation du pipeline

Test hors GPU, avec serveur ComfyUI simulé :

```powershell
python -m unittest discover -s pipeline/tests -p "test_animation*.py" -v
```

Les tests couvrent géométrie variable, recadrage natif, dimensions x2, taille RGBA brute, reprise
sans nouvel appel GPU, génération du registre x4, tables de cycles, immutabilité du pack et rejet
d'un asset runtime modifié.
