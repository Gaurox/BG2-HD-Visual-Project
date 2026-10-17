# Proposition lot26 — matière / apparitions / objets

- État : proposition uniquement ; aucun run, index, QA, fichier installé ou release modifié.
- Contrat détaillé : `batch.json` ; comparaison native : `preview/native.png` ; doublons natifs : `native-duplicate-audit.json`.
- 26 productions distinctes /27RESREF : SPIPLARI = alias canonique de SPIPLAAI ; réunir leurs consommateurs, une seule inférence.
- 1258 enregistrements source ;47cycles ;1088slots natifs (cycles alternatifs, pas une durée globale) ;518746560octets RGBA x4 avant interpolation.
- Sélection :51candidats connus +98autres sources inspectées visuellement. Sources disponibles/hashées, propriétaires connus, production non commencée ; exclusions des productions existantes, animations acceptées, doublons, personnages, ombres/masques noirs, projectiles à palette runtime. Plus grand ensemble retenu dans ce périmètre visible/palette fixe ; sous-groupes apparentés, contrats alpha/lecture distincts.
- Matières/brumes/essaims11 : OHBENVLP SPHEART SPINSECT SPIPLAAI SPIPLAUI SPMELBD1 TRGOOYAA TRGOOYBB TRVENTAA TRVENTBB WRITHING.
- Apparitions/conjurations6 : OHRFEAR SPANISUM SPHANDAT SPPROIMG SPRAISED SPSUMGTE.
- Objets/pièges/éclats9 : GLPHWRDT SKLT SPBLBBTM SPBLBTOP SPGLBBLD SPSTONES SPTRAPBB TRAPGR TRSPEART.
- Recette proposée : SeedVR7B x4 RGB, Apollo30 par cycle ; silhouette/détails fins insectes/lames/ancrages conservés ; contours selon groupe ; alpha droit ou prémultiplié selon owner. SPIPLAAI/SPIPLARI : consommateurs normaux et Blended à router séparément.
- Doublons :122slots répétés sur6BAM (SPMELBD1,TRVENTBB,WRITHING,SPPROIMG,SPSUMGTE,TRSPEART). Dédupliquer les poses puis réétaler sur la durée native ; garder les cycles constants. TRAPGR :1image statique, aucun mouvement à inventer.
- VVC :15FPS source ; cadence PRO à établir/confirmer séparément. Source50images de SPSUMGTE ≠ durée50slots : sa table native possède100slots.
- Reproduction : `python -B pipeline/recipes/effects-next-lot-proposal-20261017-v1/native_review.py`, puis `propose.py`. Feuilles comparatives : `effects/batches/next-lot-inspection-20261017-v1/`.
