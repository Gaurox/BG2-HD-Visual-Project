# Test isolé xBR4X — corps Character CDMB1

Ce document, le job et les scripts cités sont spécifiques à `CDMB1`. Pour reproduire un essai x4
sur une autre famille sans modifier ce run, appliquer
[`SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md`](SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md).

## Contrat

Portée ingame : corps `CDMB1`, animation `0x6102`, code d'armure Character `1`.
Exiger aucune armure, aucune arme, aucun objet en main gauche et aucun casque.

Méthode obligatoire :

```text
algorithm=XBR/xbr4X
scale=4
passes=1
antialias=false
xbr_blend=false
sampling=NEAREST
registry=IEECSXN version 3 scale 4
```

Le x4 est un appel direct à `xbr4X`. Ne jamais appliquer deux passes `xbr2X`.

## Sources et sorties

```text
job=sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/jobs/dwarf-male-fighter-cdmb1-xbr4x.json
source=sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/source
run=sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/runs/xbr4x-x4
engine_build=engine/InfinityEngine-Enhancer/source-patchee/cmake-build-character-x4-cdmb1-vs2019
```

Ne modifier ni réutiliser comme sortie :

```text
sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr2x-legacy/runs/xbr2x-x2
sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr2x-aa/runs/xbr2x-aa-x2
sprite/families/playable-characters/6102-dwarf-male-fighter/family-runs/complete-xn-xbr2x/runs/xbr2x-x2-xn
```

## Production

```powershell
$job = 'sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/jobs/dwarf-male-fighter-cdmb1-xbr4x.json'

python pipeline/scripts/run_creature_sprite_x2.py plan --job $job
python pipeline/scripts/run_creature_sprite_x2.py prepare --job $job --resume
python pipeline/scripts/run_creature_sprite_x2.py verify --job $job
```

Exiger 23 ressources, 10 323 frames, `registry_layout=monolith`, `registry_version=3`,
`registry_scale=4`, `dimensions_exact_x4=10323`, zéro couleur nouvelle et zéro alpha partiel.

## Overlay ingame imbriqué

Fermer `InfinityLoader`, `Baldur` et `BaldurReal`.

L'installateur dédié autorise au maximum un test sprite parent actif. Il sauvegarde la DLL, l'INI,
les registres X2/XN, le set XN et tous ses shards sans modifier l'état du parent. Il retire
temporairement ces layouts, installe le monolithe x4 et impose `NEAREST`.

Préflight sans mutation :

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $job `
  -VerifyOnly
```

Exiger `Status=install-preflight-verified` et `GameStateUnchanged=true`.

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $job
```

État canonique :

```text
sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/runs/xbr4x-x4/ingame-test/active-test.json
```

Vérifier sans mutation que la restauration exacte est possible :

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $job `
  -VerifyOnly
```

Restaurer le test parent exact :

```powershell
powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $job
```

Pour une transaction interrompue, remplacer `-VerifyOnly` par `-RecoverInterrupted` après
inspection de `active-test.json` et de `backup_root`.

## Gates

```powershell
python -m unittest `
  pipeline.tests.test_creature_sprite_x4_variant `
  pipeline.tests.test_creature_sprite_x2_pipeline `
  pipeline.tests.test_sprite_inventory
```

Exiger également les tests natifs `iee_tests.exe`, les hashes build/runtime/installés et le log
ingame contenant `scale=x4` et `filter=NEAREST`. Avant ce log, conserver
`status=installed-pending-qa`.

Résultat comparatif et réactivation :
[`CDMB1_UPSCALE_VARIANT_TRIALS.md`](CDMB1_UPSCALE_VARIANT_TRIALS.md).
