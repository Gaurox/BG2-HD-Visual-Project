# Installateur d'essai d'animations par zone

Outil de QA ingame : installe/restaure exactement une zone sous
`iee-assets/areas/<AREA_ID>`. Il ne modifie ni DLL, ni INI, ni registre global, ni autorités
animation, QA ou release.

| Entrée stable | Cœur dédié |
|---|---|
| `../scripts/Install-AreaAnimation-AreaTest.ps1` | `area_animation_area_test.py install` |
| `../scripts/Restore-AreaAnimation-AreaTest.ps1` | `area_animation_area_test.py restore` |
| conception | `DESIGN.md` |

Le pack est l'état complet désiré de la zone, jamais un delta. Le dossier `areas` doit déjà exister ;
l'outil n'active pas le runtime par zone.

```powershell
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 -AreaPack <split-root\ARxxxx> -VerifyOnly
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 -AreaPack <split-root\ARxxxx>
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 -BackupPath <backup> -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 -BackupPath <backup>
```

Production : omettre `-GameRoot` pour utiliser `config://bg2ee_game_root`. Les tests utilisent une
fixture temporaire avec une surcharge explicite.
