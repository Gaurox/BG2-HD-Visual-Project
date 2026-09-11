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
- Checkpoint : `<run_dir>/verification-cache/<generation-id>/verification-checkpoint.json`.
- Cache jetable : `<run_dir>/verification-cache/hash-cache-v1.json` ; écriture atomique.
- Lot Character : `prepare-data --resume --defer-full-verify` ; état
  `data-prepared-unverified`, sans gate exhaustive finale.
- Catalogue : `prepare --resume --defer-full-verify` ; état `built-unverified`, non installable.
- Gate unique : `verify --full-verify --keep-going` ; conserve les preuves des scopes réussis et
  liste toutes les erreurs indépendantes.
- Après correction : `verify --resume --keep-going` ; revérifie les scopes échoués/modifiés et leurs
  agrégats, puis scelle atomiquement si aucune erreur ne reste.
- Nouvelle génération dérivée : si `prepare` retourne `full_verification_started=true`, la même
  reprise cible uniquement les branches changées ; sinon la première gate doit être complète.
- `plan`, `prepare --resume`, `verify` scellé : SHA/CRC réutilisés si l'identité fichier est stable.
- `install` sans `--full-verify` exige `sealed-verification.json` ; aucun job leaf consulté.
- `--full-verify` force volontairement tous les scopes et ignore leurs preuves sémantiques.
- Preuve/cache absent ou invalide : rehash ou full scan ; jamais accepté.
- Résumé : `scope_proofs_reused`, `files_hashed`, `elements_invalidated`,
  `verification_seconds`.
- Changer la sémantique d'un validateur exige d'incrémenter son identifiant `*-vN`.
- `pipeline/catalog-builder-contract.json` change seulement avec le constructeur binaire, pas avec
  le vérificateur.

```powershell
python pipeline/scripts/run_creature_sprite_x2.py prepare-data --resume --defer-full-verify --job <agregat-character>
python pipeline/scripts/run_creature_sprite_x2.py prepare --resume --defer-full-verify --job <catalogue>
python pipeline/scripts/run_creature_sprite_x2.py verify --full-verify --keep-going --job <catalogue>
# Corriger les scopes listés, puis :
python pipeline/scripts/run_creature_sprite_x2.py verify --resume --keep-going --job <catalogue>
python pipeline/scripts/run_creature_sprite_x2.py install --job <catalogue> --creature-sprite-filter Nearest
```
