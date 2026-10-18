# Production des33impacts natifs

```powershell
python -B pipeline/recipes/effects-lot33-native-impacts-20261017-v1/prepare.py
python -B pipeline/recipes/effects-lot33-native-impacts-20261017-v1/spatial.py
python -B pipeline/recipes/effects-lot33-native-impacts-20261017-v1/run_temporal.py
python -B pipeline/recipes/effects-lot33-native-impacts-20261017-v1/verify.py --wait
python -B pipeline/recipes/effects-lot33-native-impacts-20261017-v1/review.py --wait
python -B pipeline/recipes/effects-lot33-native-impacts-20261017-v1/finalize.py
```

- Préparation initiale unique ; ne pas réécrire les sources/propositions/runs scellés. Spatial/temporal/verify/review reprenables par asset.
- Spatial : producteur canonique x4,7B INT8/LAB, ComfyUI8188. L’accès local requiert l’exécution hors sandbox réseau ; aucune nouvelle permission utilisateur nécessaire, serveur explicitement fourni.
- `temporal.py` : copie isolée de la recette lot26v2 acceptée, modes adaptés aux owners natifs non décrits : once+loop par cycle,15FPS de compatibilité. Poses exactes ancrées retirées avant Apollo, durées rationnelles conservées ; source/centres/palette intacts dans carrier. Les deux workers temporels restent bornés.
- `temporal_padded.py` : même traitement avec padding RGB temporaire min128 et multiples32, puis crop exact ; évite le crash Apollo OpenCV ROI sur SPBURN40×220 /SPCHUNKS48×48. `retry.py --resref <BAM>` crée un nouveau runv2 et conserve plan initial/ancien run échoué. Ne pas relancer sur un retry déjà produit. Les deux reprises sont vérifiées ; aucun changement d’alpha/géométrie/durée.
- `verify.py` : redécode source/carrier et tous les pixels/timings/alpha/backs ; cache les succès par BAM. Après reprises, réexécuter sans filtre pour réconcilier le résumé33.
- `review.py` : WebP lossless RGBA droits, choix cycle/mode, original x4NEAREST, fonds réglables ; palette source, tint natif non simulé. Seuls les assets vérifiés entrent dans la galerie.
- `finalize.py` : résumé final33 seulement, QA/installation/release indépendantes. Production à `effects/batches/lot33-native-impacts-7b-apollo30-20261017-v1/`.
- Résultat :33/33,5244phases/182profils,3179553984octets de packs. `run_temporal.py` et `verify.py` relancés après reprises :zéro échec, progrès réconcilié ;33cartes de comparaison. SPCHUNKS spatial relancé à l’identique après contention du verrou métier.
