# Essai item-description — SeedVR2 7B x4

- Décision 2026-11-12 : conserver les quatre essais ; généralisation aux 976 illustrations différée.
- `four-items.api.json` : workflow ComfyUI exact ; `run.json` : copie des métadonnées de l'essai.
- Base des chemins relatifs internes au run :
  `icons/batches/item-description-seedvr7b-x4-20261112-v1/`.
- Sources décodées : `icons/batches/item-description-preview-20261112-v1/assets/<RESREF>/source-frame-000.png`.
- Entrées : composition RGBA native sur beige RGB `(234,221,190)` ; padding beige droite/bas
  au multiple de 64. Charger les quatre PNG `inputs/` dans ComfyUI avant exécution du workflow.
- Sorties brutes : ordre du téléchargement `CHELM01`, `CSW1H01`, `CPOTN02`, `CAMUL01`.
  Crop depuis `(0,0)` aux dimensions natives x4 ; PNG RGB, puis variante alpha natif nearest x4.
- Comparaisons : source nearest x4 contre inférence RGB sur beige, sans alpha réappliqué.
- Conservation locale des médias ignorés Git ; recette et métadonnées suivies Git.
- La décision conserve une piste de traitement ; `qa=pending` dans le run ne vaut aucune
  acceptation runtime. Aucune installation ni intégration release.
