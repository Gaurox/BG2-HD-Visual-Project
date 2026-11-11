# Lot 5 — création/personnalisation, dix fonds SeedVR2 7B x4

- Ressources : GUIGDB, GUIAPB, GUISMF, GUISMDB, GUILUPB, GUISMS, GUIHSBS, GUIMPB, GU3MPB, GUISMDA.
- Sélection : `interface/analysis/fifth-ten-20261111-v1/proposal.json` ; seuls resrefs encore non produits dans le suivi actif.
- Recette : SeedVR2 7B int8 convrot x4 LAB, seed959948902156062, steps1/cfg1, Euler/simple, VAE fp16 tiled512 overlap128.
- MOS V2 décodés depuis KEY/BIF ; compositions complètes, pas d’atlas inféré ni de portraits/contrôles superposés.
- Padding bord droit/bas au multiple64 ; crop exact ; alpha natif nearest x4 réappliqué séparément.
- `sources.json`, `sources/`, `inputs/`, `workflows/`, `jobs/` : sources, rectangles, identités et prompts exacts.
- `outputs/<resref>/` : PNG x4 ; `raw-*` : sortie Comfy avant crop et alpha.
- `results.json` : dimensions et SHA256 ; `comparison/` : deux planches de résultats + originaux/zooms individuels.
- État : produit pour comparaison, pas installé ; aucun statut QA ingame ou release déduit.
- `prepare.py` et `finalize.py` refusent l’écrasement de manifests existants.

## Validation et installation

- Images validées : `preview-accepted-20261111-v1.json` ; QA ingame non déduite.
- Installé : `interface/integration/fifth-ten-seedvr7b-x4-20261111-v1/installed-20261111-v1.json` ; guide : `TEST_INGAME.md`.
