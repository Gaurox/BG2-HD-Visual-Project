# BDFORCEW / OH8100 — rendu lissé et translation finale

- QA finale utilisateur2026-10-10 : lot de cinq assets validé ; autorité `animations/index/selections/BDFORCEW.json`.
- Pixels : pack correctifv1 inchangé, ReboutCX/Apollo8/Spline Fit1/inner16 prémultiplié ;340 frames.
- Runtime : restaurer WED garde4/fondu16 x4 ; décaler le dessin masqué de+6 x1 horizontal après le pont natif, occurrences2286,820 /2350,866 uniquement. Filtre owner/resref/zone/occurrence/replacement/mask/dither ; débordement entier refusé. État visuel non vanilla autorisé ; ARE, BAM, centres, collisions et sauvegardes inchangés.
- DLL acceptée : `748fe476d24ffa32007d33d34f5c6e506b56147570772ee40b810556ad317c56` ; reçu `backups/renderer/20261010T150141567331Z-182aac70/renderer-install-receipt.json`.
- Données locales : `animations/batches/bdforcew-shift-right-20261010-v3/{plan,source,tests,installation}.json`, `renderer-delta.patch`, `selected-placement.png` (simulation), `.work/runtime-src`, `.work/runtime-build`, `candidate/`.
- Ordre de reproduction : `preview.py` → `build_renderer.py` → `install.py` ; scripts bornés au baseline installé WED4 `66f6a4f051597f02e84cd9902cb98851954d677b30fcf72385a5e01a250dd896`. Installation transactionnelle, jeu/InfinityLoader fermés, INI et393 frames AR0811/OH8100 préservés.
- Les reçus/instantanés pré-QA restent immuables ; acceptation finale séparée : `pipeline/recipes/portails-cinq-validation-20261010-v1/acceptance.json`. Aucune intégration release.
