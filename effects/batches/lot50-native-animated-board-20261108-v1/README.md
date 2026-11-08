# Lot50 — planche native animée · 2026-11-08

- Sélection reprise : `../lot50-fire-smoke-proposal-20261028-v1/batch.json` ; 50BAM distincts, états actuels `not-started`, aucune sélection ; SHA256 sources vérifiés lors de l'export.
- Consultation : http://127.0.0.1:8796/ ; fichier autonome avec médias relatifs : `index.html` + `images/`.
- 23flammes /15explosions-jets /9fumées-nuages /3bulles-éruptions. 990images /1291slots natifs ; 123entrées de cycle dont75animables et48vides exclues du sélecteur. Aucun cycle concaténé, aucune pose répétée supprimée.
- Canvas nearest, ancrage commun par BAM, alpha palette natif ; lecture viewport, pause globale/locale, phase, vitesse, cycles manuels/automatiques, filtre, fonds et simulation lumineuse. 15FPS = hypothèse d'aperçu ; usage/blend/cadence ingame non établis.
- Recette : `pipeline/recipes/effects-lot50-animated-board-20261108-v1/{build.py,board.html}` ; génération vers ce dossier uniquement. Nouveau dossier/version pour remplacer la sélection.
- Vérifié : 50PNG RGBA décodés, dimensions atlas, indices des1291slots,75cycles lisibles, JavaScript compilé, HTTP200. Contrôle visuel navigateur non effectué.
- Aucun traitement HD, aucune modification production/QA/installation/release.
