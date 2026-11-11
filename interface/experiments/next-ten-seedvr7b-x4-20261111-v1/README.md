# Dix panneaux — SeedVR2 7B x4

- Demande utilisateur : tous les dix assets de `interface/analysis/next-ten-20261111-v1/proposal.json`.
- Modèle `seedvr2_7b_int8_convrot.safetensors` ; VAE `seedvr2_ema_vae_fp16.safetensors`.
- Même recette que les menus retenus : x4, LAB, seed959948902156062, steps1, cfg1, Euler/simple, denoise1.
- Compositions MOS natives complètes, pas des atlas ; aucun contrôle superposé traité.
- Padding droit/bas par réplication de bord, multiple64 ; recadrage exact ; alpha natif nearest x4 réappliqué séparément.
- État : produit, comparaison utilisateur en attente ; aucune installation ni QA ingame/release.

| Nº | Ressource | Usage |
|---|---|---|
| 1 | INVSTATS | Statistiques inventaire |
| 2 | GUIINVHI | Description objets |
| 3 | GUIMGX | Capacités objets |
| 4 | GUIMGB | Livre de sorts mage |
| 5 | GUIPRB | Livre de sorts prêtre |
| 6 | GUIMGCP | Contingences |
| 7 | GUICUSTB | Personnalisation / biographie |
| 8 | GUICHISD | Graphismes, raccourcis, scripts |
| 9 | GUITUTB | Options audio/gameplay/retours |
| 10 | GUILOAD | Chargement |

## Fichiers

- `outputs/<resref>/<resref>-seedvr-7b-x4.png` : résultat exact aux dimensions natives ×4.
- `outputs/<resref>/raw/` : sortie Comfy avant retrait du padding / remise de l’alpha.
- `sources/`, `inputs/`, `sources.json` : sources x1, entrées adaptées et identités.
- `workflows/`, `jobs/submissions.json` : prompts exécutés et identifiants.
- `results.json` : dimensions, SHA256, état, coordonnées des zooms.
- `comparison/overview-01-05.png`, `overview-06-10.png` : vues entières réduites des résultats.
- `comparison/zooms-01-05.png`, `zooms-06-10.png` : original nearest x4 à gauche, 7B à droite ; pixels des extraits sans rééchantillonnage.
- `comparison/<numéro>-<resref>-original-7b-zooms.png` : comparaison individuelle entière + deux zooms identiques.
- L’affichage du chat peut réduire les planches : ouvrir le PNG pour examiner ses pixels réels.
- `prepare.py` / `finalize.py` : préparation et finalisation ; créer un nouveau run pour remplacer des résultats.

## Planches individuelles : vue entière et deux zooms

- [1. Panneau statistiques inventaire](comparison/01-INVSTATS-original-7b-zooms.png)
- [2. Description des objets](comparison/02-GUIINVHI-original-7b-zooms.png)
- [3. Capacités des objets](comparison/03-GUIMGX-original-7b-zooms.png)
- [4. Livre de sorts mage](comparison/04-GUIMGB-original-7b-zooms.png)
- [5. Livre de sorts prêtre](comparison/05-GUIPRB-original-7b-zooms.png)
- [6. Contingences](comparison/06-GUIMGCP-original-7b-zooms.png)
- [7. Personnalisation et biographie](comparison/07-GUICUSTB-original-7b-zooms.png)
- [8. Options graphiques, raccourcis, scripts](comparison/08-GUICHISD-original-7b-zooms.png)
- [9. Options audio, gameplay, retours](comparison/09-GUITUTB-original-7b-zooms.png)
- [10. Chargement de partie](comparison/10-GUILOAD-original-7b-zooms.png)

## Installation retenue — 2026-11-11

- Dix sorties retenues par l’utilisateur pour installation : `selected-20261111-v1.json`.
- Installées, QA ingame en attente ; état généré initial conservé dans `results.json`.
- Reçu/restauration : `interface/integration/next-ten-seedvr7b-x4-20261111-v1/README.md`.
