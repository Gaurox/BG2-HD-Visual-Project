# Rollback — pipeline creature-sprite xN

Cette sauvegarde contient les fichiers d'origine avant la généralisation x2/x4 du
pipeline Character, le 2026-08-25. Le workspace n'est pas un dépôt Git : cette
copie est la source de rollback.

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

Le script ne supprime aucun nouveau fichier ajouté par la généralisation. Leur
liste sera consignée dans le compte rendu final ; ils peuvent rester présents
sans être utilisés par le chemin x2 restauré.
