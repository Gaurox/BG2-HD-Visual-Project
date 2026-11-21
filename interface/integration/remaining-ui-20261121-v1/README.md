# Installation locale — interface restante, 2026-11-21

- 133 resrefs, 153 frames, 73 atlas x4 isolés. Overrides sous les noms natifs. 34 MOS V1 et 5 BAM V1 convertis en V2. Dimensions, centres et ordre des cycles vérifiés. `LOADCNTR` conserve sa séquence non contiguë via des entrées V2 réutilisant les mêmes blocs.
- `pack.json` : fichiers, SHA256, pages, entrées de galerie, références statiques. `installed.json` : reçu actif et sauvegarde. `verify_pack.py` : géométrie, cycles, alpha, intégrité. Tests renderer : 73 empreintes DXT5 acceptées, rejet lorsque les octets changent.
- Démarrage BG2EE 2.7.3.0 vérifié : EEex charge la galerie de 153 entrées, le renderer prépare les 73 pages et les premiers chargements x4 apparaissent dans le log moteur. Régression renderer : 71 pages gameplay et 7 pages sélecteur vérifiées.
- [Parcours en jeu](TEST_INGAME.md). Validation utilisateur du lot installé : `qa-accepted-20261121-v1.json`. Release locale alpha.10 : composant 120, fichiers runtime épinglés dans `releases/BG2-HD-Upscale/manifests/ui-release-candidate.json`.
- Retour jeu et InfinityLoader fermés : `python -B interface/integration/remaining-ui-20261121-v1/install.py restore`.
