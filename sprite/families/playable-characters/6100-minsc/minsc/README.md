# Sprite de Minsc — extraction historique non canonique

Ne pas utiliser cette extraction pour créer un job ou identifier les BAM de Minsc. Le manifeste
historique associe `0x6100 FIGHTER_MALE_HUMAN` à `CHMM1*`; l'inventaire stock prouve que cette
association est fausse : `0x6100` résout le corps `CHMB*`, tandis que `CHMM1` appartient à
`0x6500 MONK_MALE_HUMAN`.

Conserver ce dossier uniquement comme provenance d'un essai raster ancien. Pour tout nouveau
travail, résoudre l'ID exact du CRE ou de la sauvegarde dans
[`../../../../README.md`](../../../../README.md), puis utiliser
`../../../../index/sprite_animations.csv` et `../../../../index/sprite_families.csv`.

Le contenu historique comprend 24 BAM `CHMM1*`, soit 10 334 cadres PNG avec transparence native.
Les données ont été sorties de l'arbre actif le 2026-08-27 vers
`G:\AI\BG2_Upscale-data\archive-pre-cleanup-20260827\sprite\6100-minsc-historical\`.
Le manifeste reste ici comme index de provenance ; ses chemins de données sont donc historiques.

- `gameplay-animation-0x6100/` : nom de dossier historique erroné ; son contenu `CHMM1*` est une
  famille de moine humain masculin, pas la famille `0x6100`.
- `MMINSC` et `MMINSCE` sont volontairement exclus : ils concernent la forme minotaure
  de Minsc et ne font pas partie de l'essai du sprite humanoïde.
- `portraits/` : portraits Minsc/NMinsc, distincts des sprites de combat.
- Chaque BAM possède `source.bamc` (l'octet original du BIF), `source.bam`
  décompressé, les cadres RGBA dans `frames/`, une planche RGB + son alpha, un GIF
  d'aperçu et une planche de contact.
- `manifest.json` conserve l'ordre des cadres, les cycles BAM et les points d'ancrage
  (`center_x`, `center_y`). Ces coordonnées doivent être conservées à l'identique
  lors d'une reconstruction, sinon le personnage sautera à l'écran.

L'extraction n'a modifié aucun fichier du jeu et n'est pas une installation dans `override`. Ne
pas la convertir en job par simple renommage. La méthode raster actuelle reste
[`../../../../XBR2X_RASTER_CONTRACT.md`](../../../../XBR2X_RASTER_CONTRACT.md), après
résolution canonique de la famille.
