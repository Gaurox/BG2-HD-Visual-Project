# Variantes xBR25 · lot50 · 2026-11-08

- Décision technique après inspection SeedVR :25micro-motifs en xBR4X /masque natifnearest4 /Apollo30. Détails symboliques inventés par7B dans petites flammes/fumées/particules ; variantes SeedVR conservées et comparables.
- Résultat : `production.json` ;25vérifications source/alpha/géométrie/temps et25reçus runtime registryv3 dans `verification/`, `runtime-verification/`. Aucun état QA/install/release acquis.
- Autorité50 : `../lot50-seedvr7b-apollo30-20261108-v1/production.json` ; [planche](http://127.0.0.1:8797/).
- LAVABUB2 temporelv2 : v1 échouée conservée, chargement de tous les records de slots malgré déduplication des seuls inputs d'inférence ; pause native préservée.
- Recette : `xbr_variants.py`, `extend_xbr.py`, `temporal_xbr.py`, `verify_xbr.py`, `runtime_profiles_xbr.py`, `repair_lavabub2.py` sous `pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/`.
- Manifestes spatiaux : géométries dérivées de l'export natif déjà vérifié ; `algorithm`, `parameters`, `recipe.json` et outils hashés décrivent xBR. Les champs hérités `job_signature`/`padding_x1` du gabarit SeedVR ne décrivent pas l'exécution xBR ; pas de reprise par le CLI SeedVR sur ces runs.
