# Lot33 — correction temporelle et reconnaissance runtime

- Demande2026-10-14 : 33effets 7B x4/NEAREST/30FPS, sans doublons ; supprimer les poses natives doublées et répartir les poses distinctes sur la durée initiale. Jeu lancé/contrôlé exclusivement par l'utilisateur.
- Entrées : `effects/batches/lot33-seedvr7b-apollo30-20261014-v1/batch.json` ; 33parents SeedVR7B scellés conservés, aucune nouvelle inférence spatiale.
- Sorties : `effects/batches/lot33-retimed-20261014-v2/` ; nouveaux runs/packs mono-BAM ; anciens runs/preuves inchangés.
- Apollo8 : poses natives consécutives identiques retirées par empreinte RGBA native ancrée ; cadence entrée `(K-1)*30/(2*S-1)` ; `2*S` phases à30FPS ; première/dernière pose aux première/dernière phases ; aucune copie de fin. Durée `S/15 = 2*S/30` conservée.
- `SPIMPFR` : retirer aussi le préambule vide (24records natifs), sinon la quantification du début produit deux images noires malgré des alphas distincts. 34poses entrantes/118sorties sur59slots natifs.
- `SPSUMP` : 64slots natifs →32poses distinctes →128images RGB/RGBA distinctes, durée64/15s ; aucun maintien conservé.
- Alpha : couverture native x4 alignée, interpolation temporelle linéaire déterministe ; aucun masque généré par le modèle, aucune mise à l'échelle spatiale supplémentaire. GaussianRGB1.2 et fondu intérieur12x4 conservés ; RGB prémultiplié exactement une fois. Sampling GPU reste NEAREST.
- BAM runtime : padding transparent minimal par frame, union des rectangles de la pose native et des phases retimées qui utilisent ce slot. Palette, indices natifs, cycles/lookup, nombre de records et coordonnées monde des pixels inchangés ; centres compensés par le padding. Permet le remplacement HD pendant les anciens slots1x1 vides sans modifier le dessin natif ou le renderer des personnages.
- Renderer : comparaison RESREF insensible à la casse dans tout le registre ; lecture CVidCell normalisée ; diagnostic `owner-observed` par resref pour distinguer présence du contrôleur et substitution effective. `SPSPAINI` vérifié hors jeu aussi sur son nom complet de8caractères ; validation de sa route réellement dessinée à confirmer dans la prochaine session utilisateur.
- Installation transactionnelle : DLL+INI identique, pack97 (64précédents byte-identiques +33remplacés), 33BAM runtime liés par SHA256 au manifeste du candidat. Sauvegarde/restauration commune ; profils personnages INI/shaders/catalogue identiques. Barrière de démarrage/cartes et cache GPU64 conservés ; plafond CPU4Gio inchangé.

```powershell
python -B pipeline/recipes/effects-lot33-retimed-20261014-v2/produce.py
python -B pipeline/recipes/effects-lot33-retimed-20261014-v2/verify.py
python -B pipeline/recipes/effects-lot33-retimed-20261014-v2/install.py prepare
python -B pipeline/recipes/effects-lot33-retimed-20261014-v2/install.py install
python -B pipeline/recipes/effects-lot33-retimed-20261014-v2/review.py
```

- `verify.py` : décodage indépendant BAM natif/carrier, pixels/palette/ancrage/cycles ; SHA256 de **toutes** les images RGB visibles et RGBA ancrées (aucune exemption de maintien ou fin), différence entre phases >0, couverture alpha bornée par sources temporelles, géométrie x4 et durée exactes.
- `runtime-contracts.tsv` : chaque phase/slot testé par le parseur C++ réellement compilé, noms natifs VVC + variantes minuscules/majuscules ; index de backing vérifié exactement. Test sur candidat puis sur pack installé ; ne constitue pas une preuve de dessin ingame.
- Réinstallation : `effects/installations/lot33-retimed-7b-x4-nearest-20261014-v2/installation.json` ; QA visuelle en attente de l'utilisateur ; aucune sélection QA/release créée.
