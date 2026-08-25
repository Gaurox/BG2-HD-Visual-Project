# Rollback — pipeline creature-sprite xN

Cette sauvegarde contient les fichiers d'origine avant la généralisation x2/x4 du
pipeline Character, le 2026-08-25. La baseline Git de référence est le commit
`84e17b6` et le développement xN est porté par la branche
`feature/creature-sprite-xn`. Cette copie fichier par fichier reste le rollback
local lorsque le worktree contient d'autres changements à conserver.

Ne pas exécuter la restauration pendant que le jeu, un build, un test ou un outil
du pipeline utilise ces fichiers.

Prévisualiser les remplacements :

```powershell
powershell -ExecutionPolicy Bypass -File `
  G:\AI\BG2_Upscale\_rollback\creature-sprite-xn-pre-20260825\Restore-CreatureSprite-XN-PreChange.ps1 `
  -ProjectRoot G:\AI\BG2_Upscale -WhatIf
```

Restaurer les fichiers d'origine :

```powershell
powershell -ExecutionPolicy Bypass -File `
  G:\AI\BG2_Upscale\_rollback\creature-sprite-xn-pre-20260825\Restore-CreatureSprite-XN-PreChange.ps1 `
  -ProjectRoot G:\AI\BG2_Upscale -Confirm
```

Le script ne supprime aucun nouveau fichier ajouté par la généralisation. Les
fichiers suivants peuvent rester présents sans être utilisés par le chemin x2
restauré :

- `pipeline/scripts/Install-CreatureSprite-XN-Test.ps1` ;
- `pipeline/scripts/Restore-CreatureSprite-XN-Test.ps1` ;
- `sprite/SPRITE_UPSCALE_XN_FOUNDATION.md`.
