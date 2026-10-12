# Sauvegarde complète H: — 2026-10-12

Autorité : utilisateur, fichiers directement accessibles ; toutes productions, caches et archives.
Git ne transporte pas les données ignorées. Ni le commit courant ni le remote `local` ne prouvent
une sauvegarde des assets. Dépendances externes via jonctions : références enregistrées ; octets
hors du projet exclus. Aucun calcul GPU ni changement de QA/installation/release.

## Emplacements et commandes

| Rôle | Chemin |
|---|---|
| Source canonique | `config://full_project_backup_source` |
| Destination | `config://full_project_backup_root` |
| Copie complète accessible | `<destination>/projet/` |
| Ancienne copie et fichiers remplacés | `<destination>/historique/` |
| Reçus / verrou / SHA-256 par fichier | `<destination>/.backup-state/` |
| Initialisation en cours / reprise | `<destination>/.backup-state/incoming-project/` |

```powershell
python -B pipeline/scripts/sync_full_project_backup.py
# Relecture des fichiers déjà vérifiés :
python -B pipeline/scripts/sync_full_project_backup.py --full-verify
# Installation locale des hooks versionnés (Git LFS conservé) :
git config core.hooksPath pipeline/git-hooks
# Cette commande déclenche aussi la sauvegarde complète, même sans nouveau commit :
git push local main:main
```

## Contrat

- Tous les fichiers, cachés et ignorés, `.git` inclus ; aucune sélection depuis `.gitignore`.
- Première copie séparée ; ancienne copie H: renommée seulement après réussite. Pas de suppression.
- Nouvelles copies : SHA-256 source calculé pendant transfert, destination relue et comparée.
- Liens physiques source reproduits sur H: ; jamais de lien entre G: et H:.
- Copie atomique par fichier ; anciennes versions déplacées sous `historique/changed-<run>/`.
- Fichiers absents de G: conservés sur H:. Le ledger du dernier run définit le périmètre courant.
- Reprise : copies vérifiées réutilisées si identité/taille/mtime source et taille/mtime destination
  correspondent au ledger ; `--full-verify` relit les SHA-256 même si les métadonnées sont inchangées.
- Arbre source réénuméré avant réussite ; ajout/retrait/modification pendant copie => reçu
  `incomplete`, pas de promotion initiale. Relancer après stabilisation ; aucun faux succès.
- Verrou exclusif ; pas de sauvegardes simultanées. Les `.git/**/*.lock` transitoires sont exclus.
- Hook `pre-push` sur la source canonique uniquement, remote `local` uniquement ; autres hooks LFS
  conservés. Copie échouée => push refusé. Les autres machines doivent configurer les deux clés.

## Vérifier / restaurer

1. Lire `.backup-state/completed.json` : `status=complete`, commit source, fichiers, octets,
   chemins historiques et jonctions externes. Un reçu `running`/`incomplete` ne vaut pas sauvegarde.
2. Ledger SQLite `files` : `relative,size,mtime,identity,sha256,dest_mtime,run_id`.
   Filtrer `run_id` du reçu pour retrouver exactement les fichiers du snapshot courant.
3. Restaurer vers un autre dossier ; vérifier SHA-256 depuis le ledger avant de remplacer une
   source. Ne jamais éditer les preuves/productions dans la sauvegarde en place.
4. Conserver `historique/` et les reçus tant que la rétention n'a pas été décidée explicitement.

Périmètre : dossier du projet complet ; installations du jeu et outils/modèles externes référencés
par `config://` hors du dossier ne sont pas inclus.
