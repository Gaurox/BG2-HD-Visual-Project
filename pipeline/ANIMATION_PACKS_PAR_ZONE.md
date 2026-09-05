# Packs d'animations par zone

Le runtime brut est plafonné à 512 Mio. Le split rend chaque zone autonome et permet au moteur de
charger son pack après `LoadArea`.

## Découper

```powershell
python pipeline/scripts/split_animation_pack_by_area.py `
  --pack <pack-termine> --output animations/packs-par-zone/<lot>
```

Exiger dans `manifest.json` : aucune zone au-dessus du budget, aucune ressource sans zone, packs
relus et hashes valides. `--resume` revalide sans réécrire.

## Contrat de production des packs feuilles

Un pack utilisé par `Install-AreaAnimation-AreaTest.ps1` est produit uniquement par les scripts
courants de split/fusion. Son manifest de zone doit contenir
`runtime_budget_enforced: true` (booléen JSON exact), en plus du budget recalculé sous 512 Mio.

- champ absent/faux : pack legacy ou incompatible ; régénérer un nouveau split/fusion depuis le
  run terminé, jamais une édition manuelle du manifest ;
- une zone avec plusieurs ressources : fusionner les feuilles mono-ressource avec
  `merge_area_pack_resources.py` avant l'essai ciblé ;
- le résultat est l'état complet de la zone. Ajouter une ressource exige de régénérer la feuille
  avec les ressources déjà servies que l'on souhaite conserver.

## Combiner

L'installateur remplace tout `iee-assets/areas`; il ne fusionne pas avec l'état installé. Construire
donc un split-root représentant l'état complet désiré :

```powershell
python pipeline/scripts/combine_area_pack_splits.py `
  --input <lot-actif> --input <lot-neuf> `
  --output <lot-combine>
```

Une collision est refusée. `--replace-area ARxxxx` remplace la zone entière : il est sûr seulement
si le pack remplaçant contient l'union des resrefs déjà servis et nouveaux.

Pour fusionner des packs mono-ressource et éventuellement lier chaque variante à une occurrence :

```powershell
python pipeline/scripts/merge_area_pack_resources.py `
  --area ARxxxx `
  --pack <pack-1>::X,Y --pack <pack-2>::X,Y `
  --output <split-root-fusionne>
```

Pour étendre un pack v2/v3 multi-ressource avec un pack v1 sans collision :

```powershell
python pipeline/scripts/merge_v2_base_pack.py `
  --base-v2-pack <pack-actif> --new-v1-pack <pack-neuf> `
  --output <pack-fusionne>
```

Redécouper ensuite ce pack avec un index d'occurrences limité à la zone, puis combiner. Avant tout
`--replace-area`, comparer l'union des resrefs et les hashes des ressources préexistantes.

## Installer et restaurer

Jeu et InfinityLoader fermés :

Essai ciblé : le pack feuille est l'état complet désiré de la zone ; il remplace seulement cette
zone, sans fusion implicite. Ne pas l'utiliser pour une intégration complète.

```powershell
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 `
  -AreaPack <lot-complet\ARxxxx> -VerifyOnly
.\pipeline\scripts\Install-AreaAnimation-AreaTest.ps1 `
  -AreaPack <lot-complet\ARxxxx>

# Le chemin de sauvegarde est affiché par l'installation.
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 `
  -BackupPath <backup> -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimation-AreaTest.ps1 `
  -BackupPath <backup>
```

Le ciblé n'écrit ni DLL ni INI et n'active pas le mode par zone : `iee-assets\areas` doit déjà
exister. Omettre `-GameRoot` en production pour utiliser `config://bg2ee_game_root`.
Lancer systématiquement `-VerifyOnly` ; un refus `runtime_budget_enforced` se résout par
régénération du pack, pas par contournement de l'installateur.

Intégration complète :

```powershell
.\pipeline\scripts\Install-AreaAnimations-PerArea.ps1 `
  -SplitRoot <lot-complet> -VerifyOnly
.\pipeline\scripts\Install-AreaAnimations-PerArea.ps1 `
  -SplitRoot <lot-complet>

.\pipeline\scripts\Restore-AreaAnimations-PerArea.ps1 `
  -BackupPath <backup> -VerifyOnly
.\pipeline\scripts\Restore-AreaAnimations-PerArea.ps1 `
  -BackupPath <backup>
```

QA : zone servie, changement de zone et retour, zone sans pack, plusieurs allers-retours,
pause/reprise et sortie/retour dans le champ. Conserver le reçu ; ne modifier les autorités qu'après
décision explicite.
