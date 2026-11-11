# Lot 4 — dix ressources UI, dix-huit images SeedVR2 7B x4

- `DONATE` 2 frames, `INNROOMS` 8 frames ; `GUIERR`, `GUIERR6`, `GUIERR7`, `GUISRRQB`, `GUIWLSP`, `GUIWRSP`, `PAPERSEP`, `PCHAPTER`.
- Recette : `seedvr2_7b_int8_convrot.safetensors`, x4/LAB, seed959948902156062, steps1/cfg1, Euler/simple ; VAE fp16 tiled512 overlap128.
- Sources natives : MOS/BAM V2 décodés depuis KEY/BIF ; composition complète par frame, jamais atlas inféré.
- Modèle et VAE partagés dans deux graphes, branches indépendantes par image ; même recette que les précédents lots.
- `sources.json` : dimensions, frames, rectangles atlas et identités ; `workflows/`, `jobs/` : prompts, sorties par nœud et identifiants.
- `outputs/<resref>/<job>-seedvr-7b-x4.png` : résultat exact ; `raw-*` : sorties Comfy avant crop et alpha natif.
- `results.json` : 18 PNG/SHA256 ; crop exact ; alpha natif nearest x4 séparé, fondu DONATE conservé.
- `comparison/` : original / 7B, zoom identique par image ; `TEST_INGAME.md` : accès par numéro.
- Installé pour test ; aucune QA ingame ni release déduite. `prepare.py` et `finalize.py` refusent l’écrasement d’un run finalisé.
