# WTSWAM — reprise météo v3, 2026-09-12

**V3 rejetée ingame.** Le lien fpTone→pluie n'expliquait pas le défaut : la variante TIS
WTSWAMR était restée palette6frames. Diagnostic/correctif courant :
[ressource pluie v4](WTSWAM_RAIN_RESOURCE_REPAIR_20260912.md). Historique v3 ci-dessous.

## Cause et périmètre

- Retour utilisateur : AR1607 correct avant pluie, tuiles répétées après déclenchement ; AR1800
  toujours répétée. Captures `20260912143310_1.jpg` / `20260912143319_1.jpg`.
- Défaut code confirmé : `prepare_water_overlay_draw` acceptait seulement `vpDraw/fpSEAM`.
  `fpTone` ne contenait ni timeline ni procédural ; changement de passe → retour overlay natif.
- Logs avant correction : `WATER_ROUTE2 draw wed=AR1607 program=24 ... q=0.7 temporal=true`
  à14:31:42 ; identité WSWAM00 AR1607 glName28 à14:33:02.338 ; draw `vpDraw/fpTone`
  program6 texture28 à14:33:04.560. Le simple compteur d'identités ne prouvait pas toutes les passes.
- Sources conservées : `build/wtswam-weather-20260912-v3/evidence/`.
  `.1.log` SHA256 `24F3E924C1C6BB3E5947A2DA5B9A09472955E02B975F4CEFEFB15281452F11D5` ;
  `.2.log` SHA256 `DBDC90C615CE2D5753AC3AD60B5457FF07AC6B80A2E79474C02BBA40B55393AB`.

## Correction

- `shader_probe.cpp` : ajoute `vpDraw/fpTone` au routage par draw ; chemin météo limité aux
  identités exactes du registre avec `materialId=5`. Aujourd'hui : AR1607/AR1800 seulement.
- `fpTone.glsl` : adaptation générée depuis `fpSEAM` ; mêmes timeline/matériau/coordonnées monde,
  échantillonnage simple natif fpTone, puis couleur sommet et tone météo natifs ; alpha conservé.
- Fallback explicite : route2 OFF, effet OFF, diagnostic ou q0 → fonction native fpTone inchangée.
  Aucun effet procédural sur les bases, secondaires, pluie, UI ou identités non approuvées.
- Générateur : `engine/InfinityEngine-Enhancer/source-patchee/tools/build_water_tone_shader.py`
  (plan-only ; `--run` régénère fpTone). Après évolution fpSEAM, préparer cette régénération.
- Diagnostics plafonnés séparément fpSEAM/fpTone par WED : la première passe ne consomme plus
  le budget de la seconde. Pas de reset à chaque alternance de programme.
- Assets/WED/registre v2 précédent inchangés ; q0.70, 36phases/15Hz/blend30FPS,
  alpha100 AR1607 /128 AR1800 et raccords RGB conservés. Autres familles : chemin météo natif.

## Livraison et QA

- Build neuf : `build/iee-wtswam-weather-20260912-v3`, Release x64, `BUILD_TESTING=OFF`.
- Candidat : `build/wtswam-weather-20260912-v3` ; reçus et hashes dans
  `manifests/wtswam-weather-installed-20260912-v3.json` après installation.
- Tests préparés : `pipeline/tests/test_water_tone_shader.py` et groupe moteur ; aucun exécuté.
- QA utilisateur requise : relancer via InfinityLoader ; visiter AR1607/AR1800 avant/pendant pluie,
  attendre la transition, vérifier mouvement, raccords, transparence, ombres et teinte météo.
  Rechercher les draws positifs `wed=... program=6 ... q=0.7 temporal=true` (ID programme variable).
- Pas de validation ingame déduite, pas de commit ni intégration release.
