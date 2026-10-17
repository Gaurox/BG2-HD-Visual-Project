# Test de retrait du SDF

- `python -B pipeline/recipes/effects-lot8-sdf-inset-preview-20261017-v1/preview.py`
- Lit les sources et la recette du test SDF Ankheg précédent ; décale le champ de0 /0,5 /1texel x2, donc retraits0 /1 /2pixels x4. Intégration8×8 identique, RGB/timings constants, aucune réinférence.
- Vérifie témoin0 SHA exact et A2≤A1≤A0 ; quantifie perte d’îlots/phases vides au lieu de protéger arbitrairement les traits fins. Sorties sous `effects/batches/lot8-sdf-inset-preview-20261017-v1/` uniquement ; aucun register-run ni pack installé.
