# AR0900 nuit — v5 validé installé

- QA utilisateur : « nuit validé sur AR0900 » ; sélection `manifests/ar0900-night-validated-20260912-v5.json`.
- Installation historique : `manifests/ar0900-night-installed-20260912-v5.json`, conservée inchangée.
- Rejet v3 : `manifests/ar0900-night-rejected-20260912-v3.json`, capture/log archivés et hashés.
- Run : `maps/water-batches/runs/ar0900-night-seams-runtime-20260912-v5/`.
- Requête reproductible : `requests/ar0900-night-seams-runtime-20260912-v5.json`.

| Écart jour/nuit | Correction |
|---|---|
| Transition nuit sans nouveau CGameArea ; cache WED jour, route2 rejet3 | `hooks.cpp::publish_view_state` compare aussi le resref WED live ; rafraîchit snapshot/masque et caches tuiles ; animation de zone inchangée |
| 3 primaires2378/4662/4663 ignorés par la sélection alpha0 | Alpha128 natif sur775primaires stock DXT1 exclusivement eau, padding4 compris ; RGB inchangé à cette étape |
| Raccords nuit non traités | Recette jour : donneur secondaire nuit x4 même coordonnée ; bande8/poids1,1,1,1,.75,.5,.25,0 ; garde rive1x1 ;285primaires/358secondaires ;92317blocsRGB/97794blocsalpha |
| Registre précédent réduit à14entrées WTLAKE | Rétablissement exact des5entrées égouts/marais de l'autorité v4 ; registre final19entrées |

- Base et overlay étaient déjà x4 : TIS256px,5752tuiles base ; maître nuit SeedVR7B/LAB2×5 conservé.
- WTLAKE jour/nuit identique :36phases/15Hz, blend30FPS, matériau1, q0.70 ; aucun nouveau SeedVR.
- Installation :26pagesPVRZ nuit +DLL ;698fichiers registre vérifiés ;18entrées non ciblées inchangées.
- WED/TIS nuit, assets jour, INI et shaders inchangés. Jeu/loader fermés ; jeu non lancé.
- Build Release VS2019 `build/iee-ar0900-night-seams-runtime-20260912-v4/`, registre assetsv5.
- Sources modifiées copiées/hashées dans `build/ar0900-night-runtime-source-20260912-v5/`.
- Essai assetsv4 interrompu sur prérequis alpha128, non installé ; conservé, non sélectionnable.
- Aucun test exécuté (choix utilisateur). Plan ciblé préparé. Aucune projection/release modifiée.

QA : démarrage frais via InfinityLoader, `C:MoveToArea("AR0900")`, jour→nuit→jour ; profondeur,
animation, raccords, zoom/pan. Trace attendue : `Loaded WED AR0900N`, identité q0.7 et
`temporal=true frames=36`. Rendu nuit validé ; cycle jour→nuit→jour et météo non explicitement
attestés par ce retour. Aucune propagation aux autres variantes ; aucun rebuild/réinstallation requis.

Reçu global : `backups/water-map-repair/20260912T140501010610Z/installation.json`.
Rollback jeu/loader fermés : transaction renderer référencée, puis sauvegarde assets référencée.
Ne pas relancer une ancienne restauration de carte jour ni modifier les preuves historiques.
