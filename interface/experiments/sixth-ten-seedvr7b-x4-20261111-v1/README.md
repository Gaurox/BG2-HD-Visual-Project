# Lot 6 — dix fonds généraux et multijoueurs SeedVR2 7B x4

- GMPCARBD, GUWPKPC0, GUIINVHB, GUICONNB, GUICONN1, GUIDCX, GUIDLC, GUIMOVB, GUISMBM, START.
- Sélection : `interface/analysis/sixth-ten-20261111-v1/proposal.json` ; références statiques de l’UI, resrefs non encore produits dans le suivi actif.
- Recette : SeedVR2 7B int8 convrot x4 LAB, seed959948902156062, steps1/cfg1, Euler/simple, VAE fp16 tiled512 overlap128.
- MOS V2 décodés depuis KEY/BIF ; composition entière par resref, jamais atlas inféré ; pas de nouveaux contrôles/portraits/logos superposés.
- Padding bord droit/bas multiple64, crop exact, alpha natif nearest x4 remis séparément.
- `sources/`, `inputs/`, `sources.json`, `workflows/`, `jobs/` : sources/identités/prompts/rectangles/sorties par nœud.
- `outputs/<resref>/` : PNG x4 exact ; `results.json` : dimensions/SHA256 ; `comparison/` : planches numérotées et zooms avant/après.
- État : produit pour comparaison, non installé ; aucune QA ingame ni intégration release déduite.
- Préparation/finalisation refusent l’écrasement de manifests existants.
