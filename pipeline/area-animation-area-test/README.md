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

## Contrat du pack entrant

Le manifest de zone doit déclarer `runtime_budget_enforced: true` (booléen JSON). Ce champ est
produit par `split_animation_pack_by_area.py` et `merge_area_pack_resources.py` ; il prouve que
le pack a été construit pour le budget runtime par zone.

Absence ou valeur `false` : refus volontaire. Repartir du run x4 terminé, créer un nouveau split
et, si nécessaire, une nouvelle fusion de zone. Ne jamais ajouter ou modifier ce champ à la main
dans un manifest scellé.

Chaîne : run x4 terminé → split → fusion des ressources de la zone si nécessaire → `-VerifyOnly`
→ installation explicite. La feuille finale contient toutes les ressources à servir dans cette zone.

```powershell
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 -AreaPack <split-root\ARxxxx> -VerifyOnly
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 -AreaPack <split-root\ARxxxx>
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 -BackupPath <backup> -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 -BackupPath <backup>
```

Production : omettre `-GameRoot` pour utiliser `config://bg2ee_game_root`. Les tests utilisent une
fixture temporaire avec une surcharge explicite.
