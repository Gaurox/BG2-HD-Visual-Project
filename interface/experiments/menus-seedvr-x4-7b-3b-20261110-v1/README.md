# Quatre menus — comparaison SeedVR x4 7B / 3B

- Demande : maximum quatre menus accessibles en jeu ; comparaison seulement.
- `INVENTOR` inventaire ; `QUESTBAK` journal ; `GUIREC2` personnage ; `STONEOPT` options.
- Sources : compositions MOS natives complètes, pas des atlas PVRZ ni des captures avec contrôles superposés.
- `sources/` = x1 ; `inputs/` = padding droit/bas par réplication de bord, multiple64.
- `seedvr-7b-x4/<resref>/` / `seedvr-3b-x4/<resref>/` : PNG x4 exact + sortie Comfy brute dans `raw/`.
- `comparison/` : original agrandi nearest x4 / 7B / 3B ; vue entière réduite + deux détails à 1 pixel sortie = 1 pixel PNG.
- `workflows/` : huit prompts exécutés ; `jobs/submissions.json` : identifiants ComfyUI.
- `results.json` : tailles/SHA256/chemins ; `finalize.py` : recadrage exact et planches régénérables.

## Réglages communs

- Modèles : `seedvr2_7b_int8_convrot.safetensors` / `seedvr2_3b_int8_convrot.safetensors`.
- VAE `seedvr2_ema_vae_fp16.safetensors`, encode/decode tiled512 overlap128.
- Facteur4 ; seed959948902156062 ; 1step ; cfg1 ; Euler/simple ; denoise1 ; correction couleurLAB.
- Workflows dérivés de `pipeline/comfyui/workflows/SeedVR-Image-BG2-Pipeline-{7B,3B}.api.json` ; modification locale x4, entrées/sorties ; nœud de comparaison retiré.
- Après inférence : recadrage au x4 natif, alpha source nearest x4 réappliqué séparément ; RGB inféré conservé.
- 8/8 sorties : dimensions vérifiées ; comparaison utilisateur en attente.

Essais autonomes, hors variante Topaz retenue. Aucun remplacement de QA, installation ou release.

## Décision 2026-11-11

- 7B retenu pour les quatre fonds ; `selection-20261111.json` = choix hors jeu, pas QA ingame.
- 3B local + sorties Comfy correspondantes + workflows supprimés ; `cleanup-3b-20261111.json` : 168 418 512 octets libérés.
- Planches communes conservées ; paramètres, hashes et identifiants jobs 3B conservés comme métadonnées.
- `finalize.py` désactivé après nettoyage ; ne pas régénérer/écraser les PNG 7B sélectionnés.
- Installation réversible : `interface/integration/four-menus-seedvr7b-20261111-v1/`.
