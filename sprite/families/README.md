# Familles de sprites

Traitement : [`../PROCESSING.md`](../PROCESSING.md). Ne pas improviser une chaîne depuis un
workspace existant.

`../index/family-groups.csv` décide le macro-groupe et le dossier de chaque `engine_section`.
`pipeline/scripts/sprite_layout.py` résout le chemin exact depuis les lignes normalisées des index.

- Ne pas classer depuis un nom de PNJ, un nom d'item ou une resref supposée.
- Ne pas précréer les milliers de workspaces : matérialiser une famille au premier job.
- Ne jamais déplacer un run scellé. Les chemins existants sous `playable-characters/` et
  `monster-icewind/` restent valides.
- Une famille contient jobs, runs et recherches ; les BAM natifs partagés appartiennent au magasin
  `../ressources/`.
- Les chemins historiques restent résolus exclusivement par `../index/path-migrations.json`.

Macro-groupes : `characters`, `monsters`, `composite-monsters`, `ambient-static`, `large-flying`
et `effects`. Les animations sans `engine_section` restent dans l'index sans workspace de
production.
