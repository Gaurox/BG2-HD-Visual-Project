# Essai SeedVR2 3B — titre *Shadows of Amn* — sans correction couleur

- Source : `source/TITLE-frame-00-original.png`, PNG RGBA extrait du jeu.
- Workflow : `SeedVR-Image-BG2-Pipeline-3B.api.json`.
- Seed : `959948902156062`, identique à la passe 3B de référence.
- Paramètre modifié : `SeedVR2PostProcessing.color_correction_method = none` ; le reste du workflow est inchangé.

| Facteur | Pixels rouge-dominants | Référence 3B avec LAB | Verdict |
| --- | ---: | ---: | --- |
| x2 | 0,554 % | 0,942 % | amélioration, mais moins forte que `adain` (0,349 %) |
| x4 | 2,635 % | 1,133 % | régression ; ne pas intégrer |

Les deux PNG gardent leur alpha et leurs dimensions attendues. Aucun atlas de jeu n'est modifié par cet essai.
