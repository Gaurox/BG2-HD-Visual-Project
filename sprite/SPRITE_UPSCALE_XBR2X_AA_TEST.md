# Variante expérimentale xBR2X Antialias — corps Character CDMB1

Ce document, le job et les scripts cités sont spécifiques à `CDMB1`. Pour porter le test sur une
autre famille sans modifier cet essai, appliquer d'abord
[`SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md`](SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md), puis dériver un
chemin V4 isolé avec ses propres tests.

## Périmètre

Utiliser uniquement le job canonique :

```text
sprite/jobs/dwarf-male-fighter-cdmb1-aa-xbr2x.json
```

Cette variante traite le corps `CDMB1`, animation `0x6102`, code d'armure Character `1`.
Le test ingame exige : aucune armure, aucune arme, aucun objet en main gauche et aucun casque.
Tout overlay équipé rend le test visuel non interprétable et doit rester natif par fallback.

Le runner, le build et la transaction ingame sont séparés du pipeline V2/V3 :

```text
pipeline/scripts/run_creature_sprite_x2_aa.py
pipeline/scripts/xbr2x_antialias_batch.js
pipeline/scripts/Install-CreatureSprite-AA-Variant-Test.ps1
pipeline/scripts/Restore-CreatureSprite-AA-Variant-Test.ps1
sprite/dwarf-male-fighter-cdmb1-aa/runs/xbr2x-aa-x2/
```

Ne jamais écrire dans les dossiers de build du corps standard, du nain complet ou d'un autre
personnage. Ne jamais remplacer leur job, leur manifeste, leur registre ou leur sauvegarde.

## Contrat palette et registre

- méthode : `XBR/xbr2X`, x2, une passe, `antialias=true`, `xbr_blend=true` ;
- échantillonnage runtime : `NEAREST` ;
- registre : `IEECSXN`, version `4`, monolithe x2 ;
- payload : un indice de palette de base par pixel physique, suivi de recettes de mélange xBR
  ordonnées et clairsemées ;
- provenance : chaque opération conserve l'indice source exact, y compris lorsque plusieurs
  indices utilisés partagent le même RGBA ;
- réalisation : le runtime rejoue les recettes sur la palette réalisée courante ; aucune couleur
  RGBA finale n'est figée dans le registre ;
- alpha partiel : autorisé et compté pour ce test mono-calque ;
- registry-set V4 et équipement AA : hors périmètre, fail-closed.

Le builder doit reproduire exactement, octet pour octet, le RGBA Scalepix Antialias de chaque
frame avec les seules recettes de palette. Lire les totaux et hashes uniquement dans :

```text
sprite/dwarf-male-fighter-cdmb1-aa/runs/xbr2x-aa-x2/build/build-manifest.json
```

## Commandes

Depuis la racine du dépôt :

```powershell
$job = 'sprite/jobs/dwarf-male-fighter-cdmb1-aa-xbr2x.json'

python pipeline/scripts/run_creature_sprite_x2_aa.py plan --job $job
python pipeline/scripts/run_creature_sprite_x2_aa.py prepare --job $job --resume
python pipeline/scripts/run_creature_sprite_x2_aa.py verify --job $job
python pipeline/scripts/run_creature_sprite_x2_aa.py install --job $job
python pipeline/scripts/run_creature_sprite_x2_aa.py status --job $job
```

Le jeu n'est jamais lancé automatiquement.

## Transaction ingame

L'installation AA est un overlay transactionnel sur le test sprite déjà actif :

1. exiger `InfinityLoader`, `Baldur` et `BaldurReal` fermés ;
2. identifier au maximum un état sprite parent actif ;
3. sauvegarder octet pour octet la DLL, l'INI, les registres X2/XN, le set XN et tous ses shards ;
4. publier `status=installing` avant la première mutation ;
5. installer le monolithe V4 et la DLL testée ;
6. imposer `EnableCreatureSpriteLinearFiltering=false` dans l'INI de test ;
7. enregistrer les hashes installés et publier `status=installed-pending-qa`.

L'état canonique de la transaction est :

```text
sprite/dwarf-male-fighter-cdmb1-aa/runs/xbr2x-aa-x2/ingame-test/active-test.json
```

Vérifier sans mutation que tous les fichiers AA courants et toutes les sauvegardes nécessaires à
la restauration correspondent aux hashes enregistrés :

```powershell
python pipeline/scripts/run_creature_sprite_x2_aa.py verify-restore --job $job
```

Exiger `restore_preflight=verified` et `active_state.status=installed-pending-qa`.

Restaurer l'état ingame antérieur exact :

```powershell
python pipeline/scripts/run_creature_sprite_x2_aa.py restore --job $job
```

Récupérer une transaction interrompue après inspection de l'état et des sauvegardes :

```powershell
python pipeline/scripts/run_creature_sprite_x2_aa.py restore --job $job --recover-interrupted
```

La restauration vérifie les hashes AA courants, remet chaque fichier sauvegardé, supprime chaque
fichier ajouté par la variante, puis vérifie les hashes restaurés. Elle ne modifie pas les états,
builds ou sauvegardes du test parent.

## Gates

```powershell
python -m unittest `
  pipeline.tests.test_creature_sprite_x2_aa `
  pipeline.tests.test_creature_sprite_x2_pipeline `
  pipeline.tests.test_sprite_inventory
```

Exiger également :

- tests natifs `iee_tests.exe` passés dans le build CMake AA séparé ;
- `registry_version=4`, `registry_layout=monolith`, `sampling=NEAREST` ;
- nombre de frames reproduites exactement égal au nombre total de frames ;
- aucune collision `override` pour `CDMB1*` ;
- hashes build/runtime valides avant installation ;
- `status=installed-pending-qa` après installation ;
- log runtime sans erreur de registre, recette, palette, composition ou texture.

Cette variante reste `pending-qa` et n'est pas éligible au manifeste de release.

Résultat comparatif et réactivation :
[`CDMB1_UPSCALE_VARIANT_TRIALS.md`](CDMB1_UPSCALE_VARIANT_TRIALS.md).
