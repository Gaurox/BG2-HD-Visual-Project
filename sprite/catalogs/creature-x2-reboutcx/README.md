# Catalogue ReboutCX dérivé de xBR

- Production ReboutCX : chaque manifeste de run scellé ; QA, installation et release restent des
  états séparés.
- Suivi personnages jouables : `jobs/playable-characters-reboutcx-progress-p9-v1.json`.
  Instantané non installable : 23/78 familles, 1 471 composants vérifiés ; composants → manifeste
  ReboutCX + SHA-256 exacts.
- Un catalogue unique de ces sorties est volontairement **non construit** : plusieurs familles
  partagent un RESREF xBR alors que leurs sorties ReboutCX diffèrent. Résoudre la sélection du
  composant partagé avant de créer un job `bg2-upscale-reboutcx-derived-catalog-job-v1`.
- Reprise : produire un nouvel instantané, jamais modifier le précédent.

```powershell
python pipeline/scripts/reboutcx_playable_catalog_progress.py write-status --snapshot-id p9-v2
```
