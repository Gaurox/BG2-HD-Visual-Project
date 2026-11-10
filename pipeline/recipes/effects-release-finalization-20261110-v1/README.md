# Release alpha.8 — effets/raccords acquis, 2026-11-10

- Autorisation : intégrer tout le travail terminé à la release ; estimer le futur installeur.
- `build.py` → 424 sélections x4, 733 ressources runtime / 71 971 backings ; 783 BAM/VVC/PRO natifs. Sources conservées uniquement ; jeu inchangé.
- `integration.json` : sélections/QA exactes, variantes runtime, exclusions, COW, routes PRO. 6 masques natifs + 67 exclusions conservés ; aucune QA globale gameplay déduite.
- SPCSPRAI : identité release canonique → SeedVR accepté sous M3SPCS ; pixels/géométrie/timeline conservés. Comparatif xBR et contrôleurs isolés exclus.
- `renderer.py` → renderer alpha.10, DLL exacte `ED9A5E4E…9132A844`, shaders acquis, budgets streaming ; trace désactivée. Source retenue : `renderer-source-inventory.json` ; aucune nouvelle reproductibilité binaire revendiquée.
- `map_continuity.py` → `map-runtime-continuity.json` : registre eau 188 inchangé, empreinte embarquée vérifiée ; assemblages/QA historiques inchangés. Tests moteur et fingerprint liés ; qualification combinée sur jeu propre toujours ouverte.
- Compilation : `hash_sources.py` vérifie 115 633 sources physiques en parallèle ; cache local ignoré, invalidé par taille/date. `Compile-BG2HD-Release.ps1 -PhysicalHashIndexPath pipeline/recipes/effects-release-finalization-20261110-v1/physical-hash-index.json` ; contrôle : `Test-BG2HD-Phase2.ps1`. Sans index, SHA calculés directement et mémorisés dans le processus.
- Staging : `stage.py` ; ancien staging conservé sous `releases/BG2-HD-Upscale/archive/payload-alpha7-before-effects-20261110-v1/`.
- Taille : `estimate_size.py` → `size-estimate.json` ; échantillons pondérés par octets, DEFLATE niveau6 ; estimation de compression, aucune archive nouvelle fabriquée.
- Hors release : icônes QA en attente ; vidéos livraison/QA jeu non finalisées ; déplacement interpolé reporté.
- Statut public : `blocked` conservé ; ni installation jeu ni publication ni commit demandés.
