# P7 — premier rendu CHFF1INV, Q3m K6 x2

- Demande 2026-10-02 : guerrière humaine sans équipement ; corps `CHFF1INV` seul, tenue native conservée ; aucune couche arme/bouclier/casque, aucun autre corps.
- État : `working`, aperçu hors jeu ; ni QA utilisateur acquise ni installation. Catalogue, DLL, configuration et release inchangés.
- Résultat : `paperdoll-default-q3m-x2.png` RGBA 256×320 ; `preview.png` sur fond sombre ; `comparison.png` natif nearest x2 / Q3m, palette et placement identiques.
- Plans réutilisables : `part-{0,1}-q3m-x2.npz` = guide xBR2 sans mélange + I/F/dep_mask + géométrie native ; pas de catalogue UI produit.
- Source figée : `sprite/Etudes_Sprite_codex_claude/CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/vanilla_inventory/CHFF1INV.BAM` ; SHA `7362904c…da86d8a`, identique à la ressource KEY `data/GUIIcon.bif`, locator `0x004006FB`.
- Source : 2 morceaux, haut 66×64 / centres −24,−16 ; bas 65×75 / centres −25,0 ; cycle `[0,0,1,1]`. Placement aperçu x1 `(24,16)` puis `(25,80)`.
- Recette : reboutcx P12 fixed86/q32 fp16 → cible x4 float → BOX x2 → Q3m K6, poids égaux, sans tramage ; ajustement REF/DEFAULT/LATIN1–4. 12 cibles nouvelles, ≈9,38 s total ; cibles et index ignorés sous `work/`.
- Vérification locale : dimensions et centres conservés ; fuite de classe 0 ; spéciaux modifiés 0 ; masques exacts ; 36 décodages RGBA (2 morceaux × 18 palettes) identiques à l'oracle scalaire ; répétition cible GPU delta 0 ; relecture NPZ/PNG passée. Détails/hashes : `result.json`.

## Contrat UI encore à établir

- Palette affichée = DEFAULT `[30,91,93,12,23,93,2]` du banc Character P1 ; réemploi préparatoire du profil `character-bg2ee-2.7.3.0`. Ce rendu ne prouve pas la réalisation des palettes du paperdoll par BG2EE.
- Alpha = convention diagnostique P1 (index0 0, index1 128, autres 255) ; alpha/effets natifs UI non mesurés.
- Assemblage +80 px du second morceau : référence moteur compatible [GemRB, CharAnimations::GetPaperdollImage](https://raw.githubusercontent.com/gemrb/gemrb/master/gemrb/core/CharAnimations.cpp), centres du BAM conservés. Position BG2EE à vérifier ; la palette GemRB n'est pas utilisée comme oracle BG2EE.
- BOX ici = réduction des cibles neuronales avant encodage. Filtre, taille et raccords effectifs dans l'UI BG2EE restent à vérifier. Aucun routage paperdoll dans le DLL n'est revendiqué.

## Reproduction limitée

Copier `render.py` dans un nouveau dossier frère de recherche, puis lancer ce script avec le Python chaiNNer configuré. Les imports locaux utilisent `pipeline/scripts`, modèle et scalepix passent par `config://reboutcx_model` / `config://mmpx_scalepix`. Le script refuse d'écraser un rendu existant ; aucune régénération des sprites monde.
