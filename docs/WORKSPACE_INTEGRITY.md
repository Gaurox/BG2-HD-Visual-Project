# Intégrité physique du workspace

Ce contrôle relie le registre global, les autorités métier, les sources extraites et les runs sans
créer une nouvelle source de vérité. Ses trois sorties sont des projections jetables :

- `asset-tracking/workspace-integrity.json` : bilan et anomalies physiques ;
- `asset-tracking/runs.json` : index normalisé des runs connus ;
- `asset-tracking/runs.csv` : vue humaine du même index.

Elles peuvent être supprimées puis recréées. Aucun pipeline ne doit les éditer ni les lire comme
une décision de sélection, de QA, d'installation ou de release.

## Contrôle

Le point d'entrée global recommandé est `python pipeline/scripts/workspace.py check`. Pour ce seul
audit :

```powershell
python pipeline/scripts/audit_workspace_integrity.py --verify-determinism
python pipeline/scripts/audit_workspace_integrity.py --check
```

Le générateur vérifie les 18 353 entrées du registre et ses inputs, les sources extraites des
animations et des inventaires graphiques, les 3 321 portraits logiques, les maîtres x1 des maps,
les runs sélectionnés, les preuves QA animation, les manifests de builds sprite et leurs chaînes
de restauration, les destinations du nettoyage contrôlé et les chemins machine actifs. Le mode
`--check` n'écrit rien et échoue si une projection manque, est périmée ou si une erreur
d'intégrité est détectée.

L'index de runs ne change pas les autorités existantes : `areas.csv` sélectionne toujours les
maps, les manifests et `qa-approval.json` décrivent toujours les animations, et
`current-generation.json` avec l'`active-test.json` canonique sélectionnent toujours les sprites.
L'index se contente de rendre ces relations filtrables et de distinguer les runs sélectionnés,
approuvés, historiques ou incomplets.

## Convention pour les nouveaux runs

Les organisations solides conservent leur contrat natif :

- maps : `<AREA>/runs/<run-id>/run.json`, puis `05_build/` ;
- animations : `runs/<run-id>/request.json`, `manifest.json`, pack et `qa-approval.json` séparé ;
- sprites : job mutable, génération adressée par contenu, `build-manifest.json`, snapshot de job
  immuable pour toute nouvelle génération et pointeur courant externe.

Un nouveau domaine qui ne possède pas encore de contrat plus précis utilise
`docs/workspace-run.schema.json`. Son run doit conserver :

1. un `run_id` stable et les `asset_ids` du registre concernés ;
2. l'identité de la pipeline et une recette hashée ;
3. les inputs et outputs par chemins relatifs, tailles et SHA-256 ;
4. le générateur, la date UTC et les parents éventuels ;
5. un résultat explicite et le caractère scellé du descriptor.

La sélection n'est jamais inscrite comme vérité mutable dans le run scellé. Elle reste dans une
autorité externe : catalogue métier, pointeur `current-*`, candidat approuvé ou manifeste de
release. Les sources sont placées hors du run et restent immuables ; les copies de travail et
outputs restent sous le run ; les backups et archives ne deviennent jamais une autorité.

## Compatibilité historique conservée

- Les anciens chemins `maps/maps-principales/<AREA>/` et `maps/maps-secondaires/<AREA>/` sont
  résolus en lecture vers `maps/<AREA>/`. Les `run.json` scellés ne sont pas réécrits.
- Les 64 anciens répertoires animation et sept fichiers d'atelier déplacés depuis `proto/` sont
  résolus par `animations/index/path-migrations.json`. Les contenus historiques restent inchangés,
  et leur rôle de migration ne leur confère aucun statut QA, installation ou release.
- `maps/AR0413/runs/wtoil-family-definitive` reste documenté par son README : lui ajouter
  rétroactivement un faux `run.json` détruirait la distinction entre preuve ancienne et contrat
  actuel.
- Les anciens chemins sprites restent résolus par `sprite/index/path-migrations.json`. Seul
  l'`active-test.json` du catalogue courant décrit l'installation active ; les sept autres sont
  des états historiques utiles à la restauration.
- Cinq anciens builds catalogue citent un job mutable qui a depuis évolué. Ils restent scellés et
  signalés. Les nouvelles générations ont l'obligation d'embarquer
  `build/provenance/job.json` avec son hash, déjà imposée par la pipeline sprite.
- Les 146 jobs/manifests sprite historiques contenant des chemins machine restent inchangés et
  bornés par `config/historical-absolute-paths.json`. Le runner accepte ces anciennes valeurs,
  mais les générateurs produisent désormais des références `config://`.

## Nettoyage contrôlé du 31 août 2026

La preuve non autoritative est `docs/workspace-cleanup-manifest.json`. Elle enregistre les nombres
de fichiers, octets et empreintes agrégées vérifiés pendant le déplacement :

- les neuf essais AR0410 sont sous
  `maps/AR0410/runs/legacy-upscale-tests-20260818/`, hors des maîtres x1 ;
- les 314 dérivés vidéo sont répartis dans quatre runs sous `video/runs/` et reliés aux assets
  concernés sans décision QA ;
- les 122 fichiers de `temp/` sont conservés sous
  `archive/workspace-cleanup-20260831/temp-20260827-20260828/` ;
- `animations/runs/am0900dm-seedvr7b-lab-x4` a été supprimé après preuve qu'il ne contenait aucun
  fichier et n'était référencé par aucune autorité.

Le contrôle courant vérifie 445 fichiers préservés et l'absence de retour dans les zones actives.
Les deux outputs intermédiaires absents AR0016/AR0017 restent volontairement non régénérés : leurs
builds sélectionnés existent et aucune validation actuelle ne nécessite ces intermédiaires.

## Configuration portable

Les clés machine sont déclarées dans `config/workspace-paths.json`. Copier
`config/workspace-paths.example.json` vers le fichier ignoré
`config/workspace-paths.local.json`, ou définir les variables d'environnement indiquées :

- `BG2EE_GAME_ROOT` : installation BG2EE ;
- `BG2EE_MMPX_SCALEPIX` : page `scalepix.html` de MMPX ;
- `BG2EE_TOPAZ_EXE` : Gigapixel ;
- `BG2EE_TOPAZ_VIDEO_FFMPEG` et `BG2EE_TOPAZ_VIDEO_MODELS` : Topaz Video AI ;
- `BG2EE_COMFYUI_URL` : service ComfyUI, avec défaut local.

`workspace_paths.py` résout la configuration pour Python et les références des nouveaux jobs ;
`WorkspacePaths.ps1` fournit le même accès aux scripts PowerShell. Les scripts PowerShell
historiques acceptent aussi les variables directement. Aucune valeur locale n'est versionnée.
