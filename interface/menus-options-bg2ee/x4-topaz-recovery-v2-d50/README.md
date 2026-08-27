# Menu complet x4 — Topaz Gigapixel Recover v2, Detail 50

Variante validée du menu principal BG2EE. Elle remplace l'ensemble des éléments visuels de cette page via les atlas x4, sans modifier les archives du jeu.

- `topaz-input-x1/` : 34 PNG d'origine, un par élément visuel.
- `upscale-topaz-recovery-v2-d50/` : les 34 exports PNG x4.
- `sources/` et `sprite-manifest.json` : ressources natives et coordonnées de recomposition.
- `assets/` : huit atlas DXT5 x4 et leurs aperçus PNG, une fois la recomposition terminée.

Paramètres : Topaz Gigapixel 8.4.1, **Recover v2**, **Detail 50**, échelle **x4**, PNG RGBA et couleurs préservées. `Run-Topaz-RecoveryV2-D50-X4.ps1` permet de produire ou reprendre le lot sans écraser les sorties existantes.

`Install-Menu-X4-Topaz-RecoveryV2-D50-Test.ps1` installe cette variante et crée une sauvegarde horodatée. `Restore-Menu-X4-Topaz-RecoveryV2-D50-Test.ps1` restaure cet état antérieur, jeu fermé.

## Capture de test

`captures/menu-complet-x4-topaz-recovery-v2-d50-20260815-182421.png` est la capture en jeu retenue. La capture magenta sans rendu qui l'a précédée est conservée séparément dans `captures/rejected/` pour ne pas être confondue avec un rendu du menu.

## Vérification de complétude

La comparaison avec la référence vanilla et l'audit des fichiers confirment que les 34 sources attendues sont présentes en x4 et que les huit atlas sont installés : `MOS0017`, `MOS0181`, `MOS0257`, `MOS0258`, `MOS0261`, `MOS0262`, `MOS0265` et `MOS0266`.

Le grand fond et les bordures décoratives appartiennent à `START2EE.MOS`, exporté comme un élément Topaz x4 unique puis recomposé sur `MOS0257` et `MOS0258`. Leur changement est plus subtil que celui du médaillon ou des boutons : Recover v2 préserve les aplats sombres et les motifs peu détaillés. Les textes blancs restent rendus par les polices de l'interface ; ils ne peuvent donc pas être upscalés via ces atlas.
