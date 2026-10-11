# AM0602F — test de fondu alpha x4

Test isolé et réversible. Le run SeedVR x4 canonique et son `03_runtime_pack` ne sont pas modifiés.

- source : les 9 PNG RGBA x4 de `AM0602F` ;
- RGB : inchangé ;
- alpha : fondu intérieur par distance, rayon 8 pixels physiques x4 = 2 pixels logiques x1 ;
- bord du masque source : transparent ;
- intérieur : retour progressif à l'alpha source avec une courbe smoothstep ;
- extérieur : toujours transparent, sans aucun débordement ;
- lumière et sol restent présents à l'intérieur du masque.

Le script d'installation ne remplace que les neuf fichiers
`iee-assets/AAX4-AM0602F-frameXXX.rgba`. Il ne modifie ni DLL, ni INI, ni registre.

Installation, jeu fermé :

```powershell
.\Install-AM0602F-AlphaFeather-X4-Test.ps1
```

Restauration exacte, jeu fermé :

```powershell
.\Restore-AM0602F-AlphaFeather-X4-Test.ps1 -BackupPath .\install-backups\alpha-feather-x4-8px-backup-YYYYMMDD-HHMMSS
```
