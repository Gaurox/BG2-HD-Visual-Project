# Lot26 — huit masques SplineFit1 / v3

- Demande : SPHEART SPHANDAT SPRAISED GLPHWRDT SKLT SPTRAPBB TRAPGR TRSPEART seulement. 8nouveaux runs/packs, 404phases ; 18productions v2 conservées.
- Recette SplineFit1 : spline cubique périodique, tolérance1pixel x4, espacement1.5, supersampling4, padding32, sans fondu intérieur. Ajustement vers l’intérieur ; trous/transparence conservés, îlots isolés protégés.
- RGB droit identique octet pour octet ; prémultiplication adaptée une fois au nouvel alpha. Dimensions, centres, carrier, cycles, phases et durées inchangés ; aucun nouvel appel SeedVR/Apollo.
- `production.json`, `spline-verification.json`, `verification.json`, `scope-verification.json`. Galerie `review/index.html` : natif /avant /après sur les8 ; 26cartes, accents corrigés. Serveur127.0.0.1:8786.
- QA utilisateur en attente ; aucune installation/release/acceptation déduite.

- `alpha-contracts.json` hérite des contrats natifs/owners v2 ; les8 surcharges SplineFit1 sont décrites par `batch.json`, `spline-verification.json` et les recettes scellées des nouveaux runs.
