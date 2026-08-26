# Upscale de sprites pixel art — XBR2x

Date : 2026-08-24  
Statut : **méthode de prétraitement x2 validée visuellement par l'utilisateur**.

Point d'entrée agent : [`sprite/README.md`](../../README.md).
Pipeline complet automatisé : [`SPRITE_UPSCALE_PIPELINE.md`](SPRITE_UPSCALE_PIPELINE.md).  
Inventaire des familles et contraintes : [`sprite/index/README.md`](../../index/README.md).

Ce document définit uniquement la transformation raster d'une frame. Il ne qualifie ni l'identité
du sprite, ni les suffixes BAM, ni le profil moteur, ni l'éligibilité d'un registre. Résoudre ces
éléments dans l'inventaire avant d'appliquer XBR2x.

## Méthode unique retenue

Pour les sprites pixel art BG2 à produire en x2, appliquer **XBR / xbr2X**,
sans anti-alias, en une seule passe.

| Paramètre | Valeur obligatoire |
|---|---|
| Algorithme | `XBR` / `xbr2X` |
| Échelle | `2x`, en une seule passe |
| Anti-alias | Désactivé |
| Entrée | Une frame PNG RGBA native |
| Sortie | PNG RGBA, largeur et hauteur exactement doublées |

Les pixels RGB mémorisés sous alpha zéro font partie de la donnée source.
Conserver l'alpha PNG : ne pas aplatir l'image sur un fond vert, noir ou autre
avant le traitement.

## Utilisation graphique

1. Ouvrir [`Lancer MMPX.cmd`](G:\AI\MMPX\Lancer%20MMPX.cmd).
2. Déposer une seule frame PNG native dans la page scalepix.
3. Dans la rangée **2X**, sélectionner le résultat **XBR**.
4. Vérifier que la case **Antialias** associée à XBR est décochée.
5. Exporter le PNG dans un dossier de travail distinct, avec une copie de la
   frame source.
6. Vérifier que les deux dimensions de sortie valent exactement le double de
   celles de la frame native.

## Utilisation reproductible en ligne de commande

Le script local force `xbr_blend = false` et génère une unique sortie XBR.

```powershell
node 'G:\AI\MMPX\tools\generate-scalepix-variants.js' `
  'G:\chemin\frame.png' `
  'G:\chemin\sortie-xbr' `
  --xbr-only
```

Le fichier écrit est `<nom-frame>_2x-xbr.png`. Le script requiert FFmpeg et
FFprobe ; leurs chemins par défaut sont `C:\ffmpeg\bin\ffmpeg.exe` et
`C:\ffmpeg\bin\ffprobe.exe`. Ils peuvent être remplacés par les variables
d'environnement `FFMPEG_PATH` et `FFPROBE_PATH`.

## Contrôles avant reconstruction

- Conserver le `family_id` sélectionné dans `sprite/index/sprite_families.csv`.
- Exiger `pipeline_ready=yes` pour une production ; pour une évolution du pipeline, traiter
  explicitement chaque `blocker` avant toute installation.
- Traiter les frames individuellement, jamais une planche concaténée.
- Vérifier plusieurs directions, armes, animations et silhouettes.
- Contrôler les contours, la transparence, les pixels de palette et le
  scintillement entre les frames.
- Préserver l'ordre des frames BAM, les cycles, les dimensions, les centres,
  les offsets et les transformations de palette dynamiques.

Cette décision valide le prétraitement des images seulement. Toute
reconstruction BAM ou installation en jeu reste une étape séparée, à valider.
