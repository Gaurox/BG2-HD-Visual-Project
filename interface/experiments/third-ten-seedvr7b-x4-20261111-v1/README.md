# Troisième lot — dix compositions SeedVR2 7B x4

- Sélection et accès ingame : `interface/analysis/third-ten-20261111-v1/proposal.json` ; `TEST_INGAME.md`.
- `GUISTBSC`, `GUISTDOB`, `GUISTIDB`, `GUISTROB`, `GUIMAPWB`, `GUICREDT`, `GUISAVEB`, `GUICGB`, `GUIHSB`, `GMPWMSG0`.
- Sources : MOS natifs complets ; pas d’atlas traité par inférence, pas de boutons superposés.
- Recette retenue : SeedVR2 7B int8 convrot x4, LAB, seed959948902156062, steps1/cfg1, Euler/simple.
- Padding droit/bas par réplication de bord au multiple64 ; crop exact ; alpha natif nearest x4 séparé.
- `sources/`, `inputs/`, `workflows/`, `jobs/submissions.json` : entrées et prompts exacts.
- `outputs/<resref>/<resref>-seedvr-7b-x4.png` : PNG finaux ; `raw/` : sortie avant retrait padding.
- `results.json` : tailles/SHA256 ; 10/10 dimensions et alpha vérifiés.
- `comparison/` : vues entières et zooms natif/7B, numéros identiques au guide de test.
- Installé pour test via `interface/integration/third-ten-seedvr7b-x4-20261111-v1/` ; résultat ingame en attente.
- Les illustrations superposées du temple et des chambres restent des ressources séparées, pas traitées dans ces dix fonds.
- `prepare.py` et `finalize.py` refusent d’écraser leurs manifests existants.
