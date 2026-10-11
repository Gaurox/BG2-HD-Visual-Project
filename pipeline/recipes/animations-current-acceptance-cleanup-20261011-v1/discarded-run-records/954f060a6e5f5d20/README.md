# AR1300 — transition du pont-levis

Overlay vidéo bidirectionnel pour la porte `BRIDGE01` d'`AR1300`.

**Runtime validé en jeu le 2026-08-23** : ouverture, fermeture, inversion à la
frame courante, endpoints sans flash et couche strictement carte < animation < HUD.
La vidéo actuelle est un agrandissement Lanczos ; l'upscale SeedVR2 7B x4 reste
à produire et à valider.

Le livrable est volontairement composé de vidéos compactes, pas d'une suite de
textures : 124 frames RGBA 2048² résidentes représenteraient environ 1,9 Gio en
mémoire GPU. Le lecteur runtime décode une courte fenêtre de frames, compose
l'image sur le carré monde x1 documenté par le manifeste, puis libère le cache à
la dernière image.

## État actuel

- `01_classic-preview/BRIDGE01-classic-2048-audio.mp4` : ouverture, 124 frames
  Lanczos 2048² à 24 i/s.
- `01_classic-preview/BRIDGE01-classic-2048-reverse.mp4` : fermeture, exactement
  les mêmes frames en ordre inverse, encodées tout-intra pour une reprise précise.
- `01_classic-preview/BRIDGE01-classic-audio.wav` et
  `BRIDGE01-classic-audio-reverse.wav` : audio avant/arrière utilisé par le runtime.
- `BRIDGE01-classic-2048-closed.bgra` et `BRIDGE01-classic-2048-open.bgra` :
  endpoints lossless gardés en mémoire et affichés immédiatement pendant
  l'amorçage du décodeur, afin de masquer la bascule instantanée des tuiles WED.
- `01_classic-preview/asset-manifest.json` : contrat de lecture et de placement.
- La source MiniMax reste dans `../MiniMax_H3_00161__frames/` et n'est jamais
  modifiée.
- Procédure LLM de reproduction :
  `engine/InfinityEngine-Enhancer/source-patchee/docs/event-video-overlay-assets.md`.

InfinityEngine-Enhancer observe la variante de tuile réellement envoyée au rendu
par l'objet WED `BRIDGE01` : les 34 tuiles primaires représentent le pont ouvert
et les tuiles secondaires `4840–4873` le pont fermé. Une transition
fermé→ouvert lit le flux avant ; une transition ouvert→fermé lit le flux arrière.
La cellule primaire `3006`, dont la variante secondaire vaut `-1`, est ignorée :
elle est rendue dans les deux états et ne constitue donc pas un signal de porte.
Si l'état change pendant la lecture, l'image affichée reste figée pendant le seek,
puis la lecture repart dans l'autre sens depuis la même frame logique. Le premier
état observé au chargement ne joue rien afin de respecter une sauvegarde chargée
porte ouverte ou fermée.

L'overlay est composé à la sortie de `CGameArea::Render`, dans la cible de rendu
carte encore active. Le renderer GL différant ses commandes, sa file est d'abord
exécutée par `DrawFlush_GL`; l'overlay est alors ajouté sur la carte complète.
`DrawEndScaled` finalise ensuite la carte et l'animation avant que l'écran
propriétaire ne dessine son interface. Toutes les interfaces (dialogue,
inventaire, statistiques, menus système, etc.) restent donc dessinées par le
moteur au-dessus. Aucun masque dépendant de la forme ou de la résolution du HUD
n'est utilisé. La cible observée pendant la validation utilisait le framebuffer
par défaut (`0`) ; le code n'impose aucune valeur de framebuffer.

La version SeedVR2 7B x4 est le seul travail restant sur cet ajout. Elle doit
respecter exactement le rectangle, la cadence, les 124 frames, les deux sens,
les endpoints et le contrat de couche validés. Remplacer les médias et recalibrer
la colorimétrie si nécessaire, sans modifier le runtime, puis refaire la QA complète.
