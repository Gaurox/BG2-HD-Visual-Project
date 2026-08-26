# Essais comparatifs CDMB1 — x2, LINEAR, AA et x4

## Périmètre

```text
animation_id=0x6102
ids_symbol=FIGHTER_MALE_DWARF
bam_prefix=CDMB1
layer=body
armor_code=1
équipement ingame=aucun
zone observée=AR0411
créature=PLAYER1
```

Comparer uniquement le nain. Les builds d'équipement et du personnage complet restent hors de la
décision visuelle de ce test corporel.

Pour répéter ce protocole sur un autre sprite, appliquer
[`SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md`](SPRITE_UPSCALE_VARIANT_TEST_RUNBOOK.md).

## Sources canoniques

| Variante | Job | Build, runtime et état |
|---|---|---|
| x2 NEAREST sans AA | [`dwarf complete job`](../../families/playable-characters/6102-dwarf-male-fighter/family-runs/complete-xn-xbr2x/jobs/dwarf-male-fighter-complete-xn-xbr2x.json) | `sprite/families/playable-characters/6102-dwarf-male-fighter/family-runs/complete-xn-xbr2x/runs/xbr2x-x2-xn` |
| x2 LINEAR sans AA | même pack x2 | `sprite/families/playable-characters/6102-dwarf-male-fighter/family-runs/complete-xn-xbr2x/runs/xbr2x-x2-xn/ingame-test/linear-filter-test-20260825-2358/test-manifest.json` |
| x2 NEAREST AA | [`CDMB1 AA job`](../../families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr2x-aa/jobs/dwarf-male-fighter-cdmb1-aa-xbr2x.json) | `sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr2x-aa/runs/xbr2x-aa-x2` |
| x4 NEAREST sans AA | [`CDMB1 x4 job`](../../families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/jobs/dwarf-male-fighter-cdmb1-xbr4x.json) | `sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/runs/xbr4x-x4` |

Lire les nombres de ressources, frames, tailles, hashes et états courants dans les manifestes et
`ingame-test/active-test.json` de chaque run. Ne pas prendre ce document comme source d'état live.

## Preuves visuelles

Le raccourci `screenshots - Raccourci.lnk` à la racine du projet résout le dossier Steam des
captures. Fichiers retenus :

| Variante | Capture | Objet de la comparaison |
|---|---|---|
| x2 NEAREST AA | `20260826004444_1.jpg` | contour et conservation des petits détails |
| x2 NEAREST sans AA | `20260826005010_1.jpg` | baseline nette |
| x4 NEAREST sans AA | `20260826010816_1.jpg` | gain x4 sur tête, épaule, avant-bras, main, botte et diagonales |
| x2 LINEAR sans AA | aucune capture canonique | observation locale utilisateur ; ne pas utiliser comme preuve de QA |

Résoudre les captures sans coder le chemin Steam en dur :

```powershell
$shortcut = Get-ChildItem -LiteralPath . -Filter 'screenshots*.lnk' | Select-Object -First 1
$shell = New-Object -ComObject WScript.Shell
$screens = $shell.CreateShortcut($shortcut.FullName).TargetPath

Get-Item -LiteralPath `
  (Join-Path $screens '20260826004444_1.jpg'), `
  (Join-Path $screens '20260826005010_1.jpg'), `
  (Join-Path $screens '20260826010816_1.jpg')
```

Les recadrages présents sous `.tmp` sont diagnostiques. Ne pas les utiliser comme source canonique
et ne pas les intégrer au manifeste de release.

## Résultats retenus

| Variante | Observation | Décision |
|---|---|---|
| x4 NEAREST sans AA | meilleur rendu statique ; diagonales plus fines, détail conservé, aucun halo ni défaut visible de palette/transparence ; gain subtil à la taille de jeu | candidat visuel préféré ; conserver séparé ; valider les animations avant extension |
| x2 NEAREST sans AA | rendu net et stable ; légèrement plus crénelé que x4 | baseline et meilleur compromis qualité/coût |
| x2 NEAREST AA | rendu plus doux ; perte de petits détails ; palette et alpha visuellement corrects pendant l'essai | conserver comme prototype expérimental inactif |
| x2 LINEAR sans AA | lissage acceptable sans reconstruction d'asset | conserver comme option de comparaison ; exclure de la QA et de la release |

Classement visuel convenu pour les captures comparables :

```text
1. x4 NEAREST sans AA
2. x2 NEAREST sans AA
3. x2 NEAREST AA
```

Ne pas attribuer un rang formel à `LINEAR` sans capture comparable au même cadrage. Le x4 doit
encore être observé en attente, marche, attaque, impact et mort pour détecter une instabilité
temporelle. Ne pas étendre automatiquement x4 à tous les sprites depuis le seul résultat statique
`CDMB1` ; tenir compte du coût registre x4 lu dans les projections canoniques.

## Réactiver x2 NEAREST sans AA

Si l'overlay x4 est l'état supérieur, vérifier puis restaurer la transaction x4. Cette restauration
réactive exactement les fichiers sauvegardés du test parent x2 sans modifier son état :

```powershell
$jobX4 = 'sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/jobs/dwarf-male-fighter-cdmb1-xbr4x.json'

powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $jobX4 `
  -VerifyOnly

powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Restore-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $jobX4
```

Exiger ensuite `EnableCreatureSpriteLinearFiltering=false` et `filter=NEAREST` dans une nouvelle
session de log.

## Réactiver x4 NEAREST sans AA

Précondition : x2 parent actif, aucun autre overlay imbriqué actif, jeu fermé.

```powershell
$jobX4 = 'sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr4-direct/jobs/dwarf-male-fighter-cdmb1-xbr4x.json'

powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $jobX4 `
  -VerifyOnly

powershell -ExecutionPolicy Bypass -File `
  pipeline/scripts/Install-CreatureSprite-X4-Variant-Test.ps1 `
  -JobFile $jobX4
```

Exiger `status=installed-pending-qa`, `scale=x4` et `filter=NEAREST`.

## Réactiver x2 NEAREST AA

Restaurer d'abord tout overlay x4. Précondition : x2 parent actif, jeu fermé.

```powershell
$jobAA = 'sprite/families/playable-characters/6102-dwarf-male-fighter/cdmb1/variants/xbr2x-aa/jobs/dwarf-male-fighter-cdmb1-aa-xbr2x.json'

python pipeline/scripts/run_creature_sprite_x2_aa.py verify --job $jobAA
python pipeline/scripts/run_creature_sprite_x2_aa.py install --job $jobAA
python pipeline/scripts/run_creature_sprite_x2_aa.py verify-restore --job $jobAA
```

Restaurer le parent x2 :

```powershell
python pipeline/scripts/run_creature_sprite_x2_aa.py restore --job $jobAA
```

## Réactiver LINEAR sur le pack x2

Restaurer d'abord tout overlay x4 ou AA. Exiger le pack x2 comme état supérieur et une DLL qui
supporte `EnableCreatureSpriteLinearFiltering`. Lire le hash attendu et les fichiers conservés dans
le manifeste LINEAR ; ne pas remplacer manuellement une DLL si le hash courant ne correspond pas à
une variante consignée.

Fermer le jeu. Sous `[Shaders]` dans `<GameRoot>\InfinityEngine-Enhancer.ini` :

```ini
EnableCreatureSpriteLinearFiltering = true
```

Relancer via `InfinityLoader.exe` et exiger `filter=LINEAR`. Pour revenir à la baseline :

```ini
EnableCreatureSpriteLinearFiltering = false
```

Relancer et exiger `filter=NEAREST`. Toute QA formelle doit utiliser cette seconde session.

## Statut d'intégration

Ces essais sont comparatifs. Ils ne constituent pas une validation complète du Character nain et
ne rendent aucun élément `pending-qa`, `LINEAR` ou corporel isolé éligible au manifeste de release.
