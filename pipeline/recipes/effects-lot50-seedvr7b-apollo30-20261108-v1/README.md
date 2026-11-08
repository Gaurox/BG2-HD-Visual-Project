# Lot50 · SeedVR7B x4/Apollo30 · 2026-11-08

## Décision finale de production

- `finalize_current.py` :50résultats courants =25SeedVR+25xBR ;5164phases/150profils,10328contrats natifs. `finalize.py` archive uniquement la baseline50SeedVR dans `production-seedvr-baseline.json`.
- Après inspection, `xbr_variants.py` ajoute18variantes micro-motifs, puis `extend_xbr.py` ajoute7fumées/particules. Sources SeedVR conservées. `temporal_xbr.py`, `verify_xbr.py`, `runtime_profiles_xbr.py` = copies isolées pour ces variantes.
- `repair_lavabub2.py` : nouveaux runs temporelsv2 pour les deux méthodes, source/carrier inchangés ; charger tous les records référencés par les slots, dédupliquer seulement les inputs d'inférence. Les records transparents8..14 sont distincts même si visuellement identiques.
- `run_temporal.py` : journal atomique à temporaire unique +retry de renommage Windows ; reprise après WinError5 sans relancer les vérifiés. Ancien temporaire de journal sans autorité conservé.
- `merged_review.py --final` publie50cartes dont25boutons SeedVR/xBR, catalogue `review/current-cards.json` ; `contact_sheets.py` inspecte désormais les résultats courants. Ne pas republier `review.py` seul après cette fusion.
- Reçus finaux : `effects/batches/lot50-seedvr7b-apollo30-20261108-v1/{production,verification-current}.json`. QA/install/release indépendantes.

- Portée utilisateur : traiter50effets après analyse des recettes ; aucune installation/acceptation/release.
- Plan : `effects/batches/lot50-seedvr7b-apollo30-20261108-v1/batch.json` ; analyse : `effects/research/lot50-recipe-analysis-20261108-v1/`.
- `prepare.py` : une fois ; nouveaux runs parBAM, profils F12/T7/H15/D4/S3/P6/G3.
- `spatial.py` : producteur canonique7BINT8/LAB,1file ComfyUI8188 ; `spatial_one.py` dérive3masques par index vert exact connecté au bord avant inférence. Sources inchangées, hashes/manifeste d'export explicites.
- `run_temporal.py` :1worker Apollo apo-8, once+loop par cycle non vide ; code isolé `temporal.py` adapté du lot33 via `adapt_temporal.py`, `support.py` conserve ancres/holds/réapparitions, paddingRGB min128/multiples32 puis crop exact. Ancres15→30, pas de redistribution sur pauses. Délais/états reprenables par asset.
- Masques : source nearest4, feather0/2/12 par asset ; cap par composante `min(radius,(maxdistance-1)*0.5)`, composantes maxdistance≤4x4 inchangées. H : normal-neutre séparé, flux prémultiplié±1 ; alpha natif reste le témoin par défaut. Pas de contour0.60 appliqué sans comparatif.
- `verify.py` : redécode source/carrier ; indices/palette/cycles/centres, alpha source ou dérivation verte, durées, composants aux ancres, backings/encodages. Accepte répétitions temporelles correspondant aux holds natifs.
- `runtime_profiles.py --wait` : packs finaux **`*-native-profiles-20261108-v2` /registryv3** ; profils once+loop dans registre. Source/carrier gardent48cycles vides ; registre omet seulement ces queues inutilisables, sans renumérotation. Le lecteur moteur refuse les cycles0slot : ne pas employer les packs initiauxv1.
- Probe existant `build/iee-lot26-sdf-probe-20261017-v1/Release/lot26_effect_catalogue_probe.exe --catalogue-only <pack> <contracts>` : catalogue/chaque phase/mode/géométrie, zéro lectureRGBA ; aucun changement moteur/jeu.
- `review.py --wait` : PNG droits lossless dédupliqués,2canvas synchronisés/carte,cycles/modes/fond/phase/vitesse/pause ; LRU192Mio, lecture viewport. H : compagnon noir neutre optionnel. Natif original affiché même pour3sources vertes.
- `finalize.py` : résumé50 seulement ; autorité finale `production.json.assets[].pack`, pas `batch.json.assets[].pack` initial. QA/install/release indépendantes ;15FPS non mesuré.

```powershell
python -B pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/spatial.py
python -B pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/run_temporal.py
python -B pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/runtime_profiles.py --wait
python -B pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/review.py --wait
python -B pipeline/recipes/effects-lot50-seedvr7b-apollo30-20261108-v1/finalize.py
```

ComfyUI/Apollo : exécution hors sandbox réseau pour l'instance locale autorisée. Serveur de revue : `python -B -m http.server 8797 --bind 127.0.0.1 --directory effects/batches/lot50-seedvr7b-apollo30-20261108-v1/review`.
