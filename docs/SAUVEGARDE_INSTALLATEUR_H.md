# Sauvegarde du futur installateur H: — 2026-11-10

Autorité : demande utilisateur 2026-11-10 ; remplace la copie complète automatique du projet.

| Rôle | Contrat |
|---|---|
| Git | Code, documentation, index, manifestes ; preuves historiques suivies conservées |
| H: | Fichiers sélectionnés du futur installateur ; aucun cache/essai/source GPU |
| Destination | `config://installer_backup_root` + `installateur/<version>/<run>/` |
| Identité | Commit Git, version, SHA-256 de `content.json`, inventaire par fichier |
| Réussite | `<snapshot>/completed.json`, `status=complete`, SHA-256 source/destination vérifiés |

```powershell
python -B pipeline/scripts/backup_installer.py --plan
python -B pipeline/scripts/backup_installer.py
```

- Payload : `content.json` → `bg2hd/payload-allvalidated/<payload_group>/<basename(source)>`.
- Autres entrées : fichiers Git actifs sous `bg2hd/`, `manifests/`, `tools/`, `bootstrap/`,
  `schemas/`, `docs/`, documents racine de release ; WeiDU binaire/source, licences du projet.
- Arborescence relative au dépôt conservée sous `<snapshot>/files/` ; code/manifeste complémentaires
  présents sur Git. Copie de sauvegarde d'inputs, pas un nouvel installateur compilé/public.
- Snapshot neuf, création exclusive ; aucune purge, aucun remplacement, aucun lien vers G:.
  Snapshots incomplets conservés avec `running.json`/`failed.json` ; ne valent pas sauvegarde réussie.
- SHA-256 calculé pendant copie et relu sur H: ; hashes payload comparés à `content.json`.
  Sources modifiées pendant l'opération → échec, pas de reçu réussi.
- `inventory.jsonl` : chemin, octets, SHA-256 de chaque fichier effectivement vérifié.
- Aucun parcours des millions de fichiers du projet ; aucun changement QA, staging, release ou jeu.
- Aucun hook de sauvegarde sur push ; `pre-push` conserve Git LFS. Sauvegarde complète historique
  laissée intacte, outil `sync_full_project_backup.py` uniquement sur demande explicite.
- Restauration : checkout du commit indiqué puis copie de `files/` dans un autre dossier ; vérifier
  les SHA-256 de `inventory.jsonl` avant tout remplacement de production.
