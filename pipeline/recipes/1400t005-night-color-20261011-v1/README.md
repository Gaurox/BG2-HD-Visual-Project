# 1400T005 — couleur nocturne personnalisée

- Demande : 2026-10-11, quatre autres arbres signalés OK ; T005 encore trop clair. Screenshot `E:/Steam/userdata/5536307/760/remote/257350/screenshots/20261011182133_1.jpg` ; arbre central, ancre native `(3695,611)` dans AR1400/AR1404. Défaut vanilla soupçonné ; origine exacte non démontrée.
- Après transfert RGB natif propriétaire `CVidPalette::Realize` : R×0.60, G×0.55, B×0.85, arrondi entier. Alpha/géométrie/cycles/RGB source SeedVR inchangés.
- Gate stricte état WED vivant : AR1400+AR1400N ou AR1404+AR1404. AR1400 jour, zone inconnue, WED inconnu, autres resrefs : transfert original exact. Cache utilise l'empreinte LUT corrigée ; retour jour retrouve l'empreinte native.
- Parent exact : `animations/batches/trees-native-lighting-20261011-v1/.work/runtime-src`, DLL `27b600b3398a121a1369272c11656ef40cb28164e6cddd70ea206d33ab6472ac`. Delta trois fichiers seulement ; registre eau généré identique.
- Reproduction : `python pipeline/recipes/1400t005-night-color-20261011-v1/build_renderer.py` ; installation `python pipeline/recipes/1400t005-night-color-20261011-v1/install.py --run`. Jeu et InfinityLoader fermés requis ; reçu renderer permet restauration.
- Autorités : `runtime.json`, `installation.json`, `runtime-delta.patch`, `build.log`. Installation renderer seule ; INI identique, fichiers AR1400/AR1404/AR3000 et verrou de packs vérifiés sans changement. Aucune release.
- Tests hôte : gate jour/nuit, exclusion autre arbre, LUT/cache, alpha, encodage palette. Rendu T005 personnalisé à valider ingame ; retour utilisateur quatre autres OK conservé sans déduire visite de chaque occurrence.

