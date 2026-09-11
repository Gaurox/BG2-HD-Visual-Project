# Catalogue créatures x2 NEAREST

Ce dossier reçoit uniquement les nouveaux descripteurs d'append :

```text
jobs/append-<family>-vN.json
```

Le `job_id` et le `run_dir` du catalogue actif restent inchangés pendant toute la chaîne de
restauration. Ne pas déplacer les générations, backups ou états actifs hérités ; le prochain job
peut être rangé ici tout en réutilisant le `run_dir` actif.

## Vérification incrémentale

- Preuve : `<run_dir>/verification-cache/<generation-id>/sealed-verification.json`.
- Cache jetable : `<run_dir>/verification-cache/hash-cache-v1.json` ; écriture atomique.
- `plan`, `verify`, `prepare --resume` : SHA/CRC réutilisés si l'identité fichier est inchangée ;
  invalidation par branche.
- `install` : job, pointeur, manifests et sorties scellées ; aucun job leaf consulté.
- `--full-verify` : validation exhaustive sans réutilisation.
- Preuve/cache absent ou invalide : rehash ou full scan ; jamais accepté.
- `pipeline/catalog-builder-contract.json` change seulement avec le constructeur binaire, pas avec
  le vérificateur.
