# AR0300N — opacité appariée160, candidat v10

- Autorisation : utilisateur « ok go » après proposition128→160 sur centres ET secondaires.
- État : installé, QA ingame en attente ; tests refusés ; aucune intégration release.
- Reçu canonique : `pipeline/water/manifests/ar0300n-reflections-alpha160-installed-20260912-v10.json`
  (chemin relatif racine workspace). Run, hashes, snapshots source et rollback y sont référencés.
- Réparation native reste128. V10 est un renforcement artistique expérimental, pas une recette validée.

## Preuve ABI en lecture seule

- `BaldurReal.exe` BG2EE2.7.3, SHA256
  `B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57`.
- RVA `DrawColor=0x413200`, `DrawAlpha=0x413090` ; route GL vers `0x428120` / `0x427B60`.
- État couleur partagé RVA `0x756E08`. DrawColor échange R/B pour GL, conserve le byte alpha haut
  et retourne la couleur ARGB précédente ; DrawAlpha ne remplace que ce byte haut.
- Utilisation de `DrawColor` déjà résolu/validé par le manifeste ; aucun nouvel offset runtime.

## Contrat

- 892 primaires eau exclusives : BC3 alpha128→160, marges incluses ; RGB bit-exact.
- 374 secondaires exclusifs : source alpha inchangé ; DrawColor alpha128→160 avant DrawBegin,
  couleur antérieure restaurée après DrawEnd. Toute autre opacité native reste inchangée.
- Champ optionnel `local_art_opacity` du registre v3 : IDs triés/uniques, source/target1..255,
  égalité alpha primaire/dessin secondaire, WED override obligatoire et hashé. Champ absent = neutre.
- Gate : fichiers WED/TIS/PVRZ validés, WED actuel = snapshot, propriétaire TIS actif, taille/grille/
  slots conformes, rôle secondaire listé et page propre au TIS. Aucune modification ARE/sauvegarde.
- AR0300 jour et les18 autres entrées registre inchangés ; overlay WTLAKE x4/36 phases/15→30FPS,
  q0.70, INI, shaders et correctifs universels de teinte/transition conservés.
- Pages160 et DLL compatible indivisibles. Repli : transaction complète v9, jamais DLL seule.

## Reprise

- QA : phare, reflet du mur, raccords entre populations, animation, cycle jour→nuit→jour.
- Log borné : `WATER_ART_OPACITY secondary ... nativeAlpha=128 drawAlpha=160`.
- DLL compilée en Release/VS2019 avec BUILD_TESTING=OFF ; aucun lancement du jeu par l'agent.
- Tests ajoutés, non exécutés : `test_water_overlay_route2_policy` (C++) et
  `pipeline/tests/test_water_art_opacity_candidate.py` (générateur).
