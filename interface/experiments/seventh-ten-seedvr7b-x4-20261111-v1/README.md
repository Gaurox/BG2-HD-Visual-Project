# Lot 7 — dix fonds/panneaux SeedVR2 7B x4

- Sélection : `../../analysis/seventh-ten-20261111-v1/proposal.json` ; dix resrefs du périmètre accepté, aucune sortie courante retenue remplacée.
- GMPCARBB, GMWMSGA0, GMWMSGA9, GMWMSGB0, GUICGPR, GUIAPBR, GUICHISE, GUICPORB, GUICUSTP, GUICUSTX.
- Recette : SeedVR2 7B int8 convrot, x4 LAB, seed959948902156062, steps1/cfg1, Euler/simple ; VAE fp16 tiled512/overlap128.
- Sources : KEY/BIF, compositions MOS V2 entières ; padding bord droit/bas multiple64, crop x4 exact, alpha natif nearest x4 remis séparément.
- `native-controls.json` : icônes intégrées de GMPCARBB et poignées GMWMSGA0/9 conservées en natif x4 exact, assertions des octets RGBA après restauration.
- `results.json` : dix PNG/dimensions/SHA256/rectangles ; `jobs/` : deux prompts5/5 et téléchargements ; `comparison/` : original gauche / 7B droite, vues complètes et zooms100% des ornements.
- Produit, attente de validation des planches ; non installé, release inchangée. Certaines variantes historiques : usage runtime non établi, aucune route ingame déduite du nom.
- Préparation/finalisation refusent l’écrasement des manifests.
