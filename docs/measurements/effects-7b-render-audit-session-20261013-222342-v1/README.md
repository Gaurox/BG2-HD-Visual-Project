# Effects 7B — audit rendu, session 2026-10-13 22:23:42

- Source figée : `session.log`, lignes globales 32026–33062 ; `audit.json` = SHA, assets, stages, limites.
- 10 packs 7B x4/30 : 548 backings installés relus (545 modifiés lors du passage 3B→7B), tous SHA conformes ; manifeste et DLL conformes au reçu d’installation.
- Observés `timeline-resolved` + `x4-bound` : BDETHER, BDSPCLAR, EXALTAH, SPNWCHRM, SPPLANAR, ABJURH, SPCCMDSI.
- Non observés cette session : GLDUSTH, SPGFLSH1, COLDH. Installation prouvée, rendu cette session non établi.
- Dernier diagnostic : x4Bound=1081, registryFallback=0, bindFallback=0 ; compteurs cumulés au diagnostic, pas bilan exhaustif de fin.
- Personnages 6000/6010/6100/6110/6200/6210 : composites HD x2 ; aucune alerte de fallback.
- Seule alerte : prologue RenderTexture detour EEex, pattern récupéré ; aucune alerte shader/texture/occlusion.

| Traitement | État / preuve |
|---|---|
| Compression textures effects | Aucune dans ce chemin : RGBA8, glTexImage2D RGBA/UNSIGNED_BYTE ; `effect_animation_x4_registry.cpp:228` |
| Échantillonnage | LINEAR min/mag, niveau 0 seul ; même sortie masquée (`native_occlusion_bridge.cpp:517`) |
| CatmullRom / sharpen personnalisés | Profils fpSprite/fpSELECT désactivés ; effets sans ownership CreatureHD, uniforms remis neutres (`shader_probe.cpp:1445–1542`) |
| FXAA / SSAA plein écran | false / false dans INI inchangé |
| Shader visibilité décor | Actif observé BDETHER/BDSPCLAR/SPPLANAR ; texelFetch x4, transfert masque natif x1, multiplication RGB et alpha ; aucune convolution RGB globale |
| Shader natif fpDraw | Échantillonnage + modulation couleur/ton natifs si style inactif |
| Shader natif fpSprite | Halo 5×5 toujours présent quand style inactif (`override/fpSprite.glsl:587–624`) ; route/valeur uSpriteBlurAmount par effet non enregistrées, impact non démontré |
| Traitement intégré aux fichiers | Gaussian RGB sigma=1.2 px x4 ; fade intérieur 12 px x4 = 3 px natifs ; RGB prémultiplié |
| Alpha production | Masque binaire natif agrandi nearest x4, phases intermédiaires alpha native-left ; fade intérieur ensuite |

- Hypothèses de perte perçue : traitement intégré, alpha conservant la grille native, rendu/réduction à la taille native, halo natif si route fpSprite. Les logs ne permettent pas d’attribuer la perception à une cause unique.
- Étape discriminante : comparer RGB brut 7B / Apollo avant traitement / résultat installé ; puis capturer route shader, uniforms et sortie écran du même frame. Aucun réglage ni asset modifié pour cet audit.
