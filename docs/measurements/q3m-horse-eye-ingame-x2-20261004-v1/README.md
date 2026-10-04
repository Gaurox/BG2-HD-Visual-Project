# Cheval B100 — candidat œil v3 installé, 2026-10-04

- Autorisation utilisateur : « ca a l'air nickel. installe le ingame » ; appréciation du comparatif local, **QA ingame encore en attente**.
- Analyse/candidat immuables : `../q3m-horse-eye-directions-20261004-v3/README.md`, `candidate.json`, `verification.json` ; recette `horse-front-native-eye-elliptical-K6-40percent-v3`.
- Actif : Q3m V7 K6 x2 couleurs améliorées, sans SDF, palette native live/CatmullRom conservés. Delta sur le précédent correctif : cinq frames AHRSG1 (0–4), 134 pixels x2 I/F ; 39 frames inchangées ; correction des dix frames de profil conservée.
- `prepare.py` reprend les deux feuilles exactes du candidat ; AHRSG1E déjà identique au parent. Publication : **une nouvelle feuille AHRSG1 +catalogue** ; aucun nouvel upscale/encodage, aucune DLL/shader/INI/CRE modifiée.
- Pack : `sprite/.work/q3m-horse-eye-ingame-x2-20261004-v1/combined/` ; production `current-generation.json` ; parent `../q3m-horse-eye-x2-20261004-v1/current-generation.json`.
- Catalogue actifSHA256 `211edfd214af0eefee3be1f8a4f62cb04b9a98406eedf3dbd8c50b8e6cfd2c55` ; AHRSG1SHA256 `b221818737cc7eae2144bf85fca77dda242c661f546902a9df493b3d5e4b36e9`.
- Preuve catalogue `catalog-proof.json` : 104 IDs/50 299 routes identiques ; 4 617 autres composants/feuilles identiques, dont AHRSG1E ; 4 618 ressources/1 589 008 frames actives. 24 BAM des 12 modèles ambient_static acceptés conservés.
- Native combiné `native-combined.log` : deux BAM/44 frames/878 slots ; K6 ×trois formats ; 18 572 760 pixels décodés, accepté. Argument correct : `combined/iee-assets/creature-sprites` ; tentative avec la racine du pack conservée dans `native-path-attempt.log`.
- Installation `install.ps1` : jeu/InfinityLoader fermés, SHA parent/QA/fichiers acquis contrôlés ; backup catalogue puis feuille et publication atomique du catalogue ; retour parent automatique si erreur.
- Reçu courant `ingame-installation/active-test.json` ; preuve immuable `installation-verification.json` : une feuille nouvelle et **150 fichiers préservés** vérifiés SHA256, backup parent authentifié. Release/payload/staging/content/TP2 inchangés.
- Test : `C:CreateCreature("HORSE")` ; promenade `C:MoveToArea("AR0700")` ; observer pose de la capture, phases voisines, profils/rotation et zoom usuel.
- Retour arrière dédié, jeu/InfinityLoader fermés : `& ./docs/measurements/q3m-horse-eye-ingame-x2-20261004-v1/restore.ps1` ; revient au catalogue `336514d6625b9380129d18aa187646b49e37aaac2a8404b3f19bbac8ea146d17`, conserve les feuilles non référencées. Ne pas rejouer l'ancien restore contre le nouveau catalogue.
