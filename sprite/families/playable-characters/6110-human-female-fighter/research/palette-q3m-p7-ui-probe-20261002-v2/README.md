# P7 — sonde UI native CHFF1INV

- Demande utilisateur 2026-10-02 : installation pour tester le premier corps Q3m sans équipement. Support HD paperdoll encore absent ; étape installée = observation du rendu natif pour établir le contrat UI.
- Scope : resref exact `CHFF1INV`, deux morceaux du corps ; aucune substitution d'image, aucun nouvel asset installé, aucune entrée/sortie clavier/souris, aucune écriture d'objet ou d'état GL.
- Runtime : `pipeline/runtime/manifests/iee-sprite-p7-ui-probe-20261002-v2.json` ; DLL `A7099657…551E6B2A`, INI `92ECAF23…B4FB4FB28` ; baseline exacte P4 x2 BOX. Seuls DLL/INI remplacés ; catalogue `5F0596DD…5CDC6044` et trois shaders inchangés.
- INI : `[Shaders] EnablePaperdollUIProbe=true`, `EnableCreatureSpriteP4Probe=false`. Profils fpSprite/fpSELECT laissés désactivés ; CreatureSpriteFilter=Box, scope 0x6110, catalogue monde x2 conservés.
- Hooks réemployés : CVidPalette::Realize, CVidCell::Render (RVA 0x424780), common RenderTexture (0x425530) ; signatures existantes du manifeste BG2EE 2.7.3 vérifiées. Le probe dépend du hook palette Character validé et valide séparément les deux entrées CVidCell ; aucun besoin d'activer le style D7.
- Journal jeu : `config://bg2ee_game_root/InfinityEngine-Enhancer.log` (fichier rotatif). Balises `P7_UI_PROBE`, `P7_UI_PALETTE`, `P7_UI_DRAW` ; bornes 64 palettes / 128 géométries distinctes par thread de rendu. Native UI/corps HD encore à valider.
- Palette : 256 DWORD réalisés, format/type natifs, propriétaire, caller RVA, flags/transparence, type/source/ranges CVidPalette ; palette globale observée à nouveau à la soumission du draw (spéciaux éventuellement corrigés par le moteur).
- Géométrie : identité CVidCell, séquence/slot, x/y, taille logique, 4 i32 par rectangle source/render/clip, shader natif. Lectures `safe_read`, déduplication bornée, erreur diagnostique sans substitution du rendu.
- Vérifications : DLL compilée MSVC 2019 x64 ; test hôte `iee_tests` passé (parse opt-in/default off inclus). Install→Verify→Restore sur fixture, retour DLL/INI exact, refus des dérives à l'installation/restauration : `verification.json`. Installation réelle vérifiée : `installation-verification.json`. Aucune QA ingame déduite.

## Manipulation utilisateur

1. Lancer comme d'habitude via InfinityLoader, charger la guerrière humaine déjà utilisée.
2. Retirer son équipement ; ouvrir son inventaire, garder la silhouette visible environ 10 s.
3. Fiche personnage (`R`) → Personnaliser → Couleurs : couleur principale des vêtements rouge puis bleu ; après chaque modification, rouvrir l'inventaire environ 10 s. Si le menu Couleurs est indisponible, la mesure initiale reste exploitable.
4. Fermer le jeu et InfinityLoader ; prévenir l'agent pour lire la dernière session. Mode fenêtré conservé possible ; aucune sauvegarde nécessaire au protocole.

Suite après mesure : confronter palette réelle au profil Q3m Character réemployé par l'aperçu, établir alpha/geometry/filtre UI, adapter le runtime et produire un registre UI séparé pour CHFF1INV seul, installer le corps HD pour QA utilisateur. Réutiliser les deux plans déjà calculés si compatibles ; autres corps/équipements hors scope.

## Commandes

`install.ps1 -Mode Verify` : lecture seule du candidat et du contexte catalogue/shaders.

`install.ps1 -Mode Restore` : jeu/InfinityLoader fermés, fichiers live et sauvegardes contrôlés ; retour aux octets DLL/INI P4 x2 BOX. État local actif sous `ingame-installation/`, preuves historiques conservées.

`prepare.ps1` / `verify-install.ps1` : préparation d'un nouveau candidat et fixture locale ; pas de régénération des sprites monde ni d'inférence GPU.
