# P4 — filtres x4, candidat 2026-10-01 v1

- Demande : implémenter §10.2 du guide après mesure du zoom ; P3 acceptée par l'utilisateur.
- Runtime : `pipeline/runtime/manifests/iee-sprite-p4-filters-20261001-v1.json` ; DLL + trois shaders épinglés par SHA256. État : candidat expérimental ; aucune décision QA P4/release.
- Catalogue x4 Q3m K6 existant conservé : `637DBC809EAD7A9AD2A771BB760F5C0042109C5A4B6A19BE68A75CC41D50E0B8`.
- Périmètre installé : `CreatureSpriteFilterAnimation=0x6110`. Autres animations : Nearest, masques LINEAR historiques. Aucun I/F, BAM, géométrie, palette, sauvegarde, asset de famille ou payload release changé.

| Mode INI | Stockage / MIN / MAG | Masque natif |
|---|---|---|
| Nearest | RGBA droit ; NEAREST / NEAREST ; MAX_LEVEL=0 | LINEAR / LINEAR historique |
| Box | RGBA droit ; sampler NEAREST / NEAREST ; intégrale d'aire explicite au shader | même intégrale après application du masque x1 |
| Mipmaps | RGBA8 prémultiplié CPU ; MIN=LINEAR_MIPMAP_LINEAR / MAG=NEAREST ; chaîne complète GPU | visibilité multiplie RGB prémultiplié et alpha ; nouvelle chaîne après masque |

- BOX : surface écran via dérivées UV, recouvrement exact de texels, accumulation RGB×alpha, déprémultiplication ; agrandissement nearest. Borne 16 texels/axe (17×17 maximum) ; au-delà, nearest sans troncature d'intégrale. Zoom min mesuré : 4.86 texels/axe ; zoom joué initial : 1.49.
- Mips : dimensions NPOT divisées par deux jusqu'à 1×1 ; validation GL de chaque niveau ; aucune publication de chaîne incomplète. Échec ⇒ MAX_LEVEL=0, texture native conservée. Comptabilité cache inclut les niveaux ; scratch masque ≤64 MiB chaîne comprise.
- Shader : `IEE_CREATURE_MINIFICATION_CONTRACT_V1`, uniforme résolu avant substitution ; modes 3=Box, 4=Mipmaps. Déprémultiplication avant teinte/blur/sélection/blending natifs. Stockage sRGB8 ; effets de quantification aux faibles alpha à juger en jeu.
- Implémentation : `src/iee/core/sprite_minification.h`, `creature_sprite_minification.h`, `creature_sprite_filter.*`, `creature_sprite_x2.cpp`, `native_occlusion_bridge.cpp`, `shader_probe.cpp`, `hooks.cpp`, `assets/shader-suite/{creature-hd-common.glsl,templates/*}` ; préfixe moteur `engine/InfinityEngine-Enhancer/source-patchee/`.

## Mesure / vérification

- `verification.json` : hashes sources/candidat, CTest, tests Python, transaction locale ; `gpu-tests.json` : compilation effective fpDraw/fpSprite/fpSELECT/masque et 12 oracles RGBA sur RTX 5090, GL 4.6, préambule de test GLSL 130.
- Contexte WGL caché jamais affiché/activé ; aucune entrée bureau, aucun lancement/contrôle du jeu. Test synthétique ≠ QA en jeu.
- Sonde : premier draw HD **0x6110** par frame ; append `filter_mode,max_mip_level,provenance,animation_id,mask_calls,mask_successes,mask_cpu_ms,mask_cpu_max_ms` au CSV. Analyseur compatible ancien CSV ; BOX séparé de Nearest malgré MIN/MAG identiques.
- CPU upload inclut prémultiplication + commande de génération mips ; CPU masque inclut passe GL + génération masquée. Timings CPU/driver, pas temps GPU. Pixels/upload imbriqués dans composition ; masque mesuré séparément. FPS global ; mémoire processus global ; octets uploadés = base RGBA transférée, pas VRAM ni octets générés par GPU.
- Références antérieures immuables : `../palette-q3m-p4-probe-20261001-v1/`, `../palette-q3m-p4-measurement-20261001-v1/`.

## Installation et bascule (jeu + InfinityLoader fermés)

```powershell
pipeline/scripts/Set-Sprite-P4-Filter.ps1 -Mode Install -Filter Box
pipeline/scripts/Set-Sprite-P4-Filter.ps1 -Mode Verify
pipeline/scripts/Set-Sprite-P4-Filter.ps1 -Mode Select -Filter Mipmaps
pipeline/scripts/Set-Sprite-P4-Filter.ps1 -Mode Select -Filter Nearest
pipeline/scripts/Set-Sprite-P4-Filter.ps1 -Mode Restore
```

- Baseline exigée : sonde v1 + INI + trois shaders + reçu + catalogue attendus ; backups dans `ingame-filter/`. Restore exact DLL/INI/shaders/reçu ; catalogue conservé. Dérive utilisateur ⇒ refus avant remplacement.
- Captures : `captures/{box,mipmaps,nearest}/p4-*.csv`, session unique par lancement. Pas d'analyse de session sans signal utilisateur.
- Analyse explicite : Python `config://chainner_python`, `-B pipeline/scripts/palette_p4_probe.py --input <CSV> --output <nouveau-JSON>`.

## Essai manuel suivant

1. Même sauvegarde/scène/guerrière que P3 ; fenêtre conservée à sa taille actuelle ; attendre 10 s après affichage du monde.
2. Zoom maximal en butée : immobile 20 s.
3. Depuis ce maximum, choisir le zoom joué en comptant les crans arrière ; noter ce nombre N. Immobile 20 s.
4. Zoom minimal en butée : immobile 20 s.
5. Retour au maximum puis exactement N crans arrière : marcher 20 s ; avatar immobile, déplacer doucement la caméra 20 s en gardant l'avatar visible.
6. Quitter jeu et InfinityLoader ; donner avis sur détails/contours/scintillement, puis autoriser la mesure. Même N, scène et taille pour mipmaps/nearest suivants.

P4 reste ouverte : comparaison x2 Nearest/CatmullRom à organiser ensuite ; catalogue commun x2/x4 de deux animations à traiter explicitement pour conserver le périmètre. Décision datée échelle + filtre seulement après mesures et choix visuel utilisateur.
