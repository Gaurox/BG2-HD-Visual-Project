# Interface — ressources restantes, 2026-11-21

- Périmètre du suivi au lancement : 133 resrefs, 153 frames natives. `BIGLOGO` frame 0 reprise du PNG Topaz existant avec son alpha d'origine. Les autres frames reprennent l'alpha natif x4 nearest.
- ComfyUI local : SeedVR2 7B int8 convrot x4 LAB, seed 959948902156062, 1 step. 163 entrées, 42 prompts. Recouvrement et fusion pour `BGPADB`, `GU20BKMD`, `WORLDMAP`.
- `sources.json` : format, dimensions, centres, cycles, rectangles PVRZ et SHA256 natifs. `jobs/submitted.json` : IDs ComfyUI. `results.json` : PNG, SHA256 et statut de production. `review/index.html` : planches original/x4 et accès aux PNG.
- Reprise : `python -B interface/experiments/remaining-ui-seedvr7b-x4-20261121-v1/run.py monitor` ; `review` reconstruit les planches depuis les résultats locaux.
- Production de PNG. La QA en jeu et le routage des variantes restent séparés. Les 39 ressources V1 demandent un chemin d'intégration distinct des remplacements de pages PVRZ V2.
