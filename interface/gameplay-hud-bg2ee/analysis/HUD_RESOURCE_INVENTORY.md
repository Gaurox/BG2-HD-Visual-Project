# Inventaire du HUD de jeu

## Portée observée

La capture de référence est une partie en cours en 2560×1440. Les éléments à améliorer sont :

- les colonnes décoratives gauche et droite ;
- le cadre du journal de dialogue et les cadres de la barre basse ;
- les séparateurs et bordures statiques de cette barre ;
- les cadres et boutons d'interface qui se superposent à ces panneaux.

La zone centrale de jeu est explicitement hors périmètre. Les portraits, icônes de sorts/objets, curseurs, jauges à contenu variable et texte seront traités dans une seconde liste, après identification dynamique.

## Pages statiques identifiées

Ces quatre pages PVRZ DXT5 constituent le support de fond du HUD. Elles sont le candidat principal pour une passe x4 : le mécanisme déjà validé pour les menus peut les remplacer à taille affichée constante.

| Page | Taille originale | Empreinte FNV-1a DXT5 | Éléments composés connus | Zone visible |
| --- | ---: | --- | --- | --- |
| `MOS0170.PVRZ` | 512×512 | `D044CFCD4C956C75` | `GUIW12_1`, `GUIVERB` | morceaux de cadre bas ; page partagée |
| `MOS0171.PVRZ` | 1024×1024 | `BA4FF5696C7DE14B` | `GUIW12_1` à `GUIW12_6` | dialogue et cadre inférieur |
| `MOS0172.PVRZ` | 1024×1024 | `8F3171282397778B` | `GUIW12_6` à `GUIW12_8` | dialogue et cadre inférieur |
| `MOS0176.PVRZ` | 1024×1024 | `8E777F27AEB3EA6D` | `GUIWLS20`, `GUIWRS20` | panneaux décoratifs latéraux |

Toutes ces pages viennent de `data/bgee.bif`. Les textures source et les compositions décodées sont disponibles dans `reference/decoded-mos/`.

`GUIW12_1` à `GUIW12_8` sont les huit compositions du panneau inférieur. `GUIWLS20` et `GUIWRS20` sont les deux colonnes verticales de 80×1536 ; elles correspondent visuellement aux bordures latérales de la capture.

## Colonne de boutons gauche — identifiée

Les boutons gris rectangulaires de la colonne gauche sont **entièrement portés par `GUILS10.BAM`**. Ce BAM V2 contient 68 cadres organisés en 17 cycles de 4 états (normal, survol, appuyé et désactivé). Sa géométrie est inchangée ; les pixels et les icônes sont prélevés dans les deux pages suivantes :

| Page | Taille originale | Empreinte FNV-1a DXT5 | Contenu |
| --- | ---: | --- | --- |
| `MOS0140.PVRZ` | 1024×1024 | `B28D170B09DC019E` | atlas principal : icônes crâne, étoile, œil, armure, silhouette, livre, parchemin, roue, carte, aide et leurs états |
| `MOS0141.PVRZ` | 512×512 | `BB32351E53E5DDF4` | compléments, état des boutons et extrémités de la colonne |

L’aperçu complet de l’atlas et l’extraction des deux pages sont dans `reference/identified-left-toolbar/`. Cette correspondance est confirmée visuellement avec la capture : les dix commandes visibles y apparaissent avec la même forme et les mêmes variantes gris/or/blanc.

La variante `GUILS20.BAM` utilise `MOS0141` à `MOS0143` pour une autre composition de l’interface ; elle reste hors du premier lot car elle n’est pas celle affichée dans la capture de référence.

## Éléments complémentaires à tracer

Les fichiers ci-dessous sont des BAM V1 ou V2. Ils portent les contrôles de premier plan (boutons, cadres de portraits et ornements), mais ne sont pas encore associés image par image à la capture. Des aperçus des BAM V1 ont été extraits dans `reference/bam-v1-previews/`.

| Ressources candidates | Format | Rôle probable | Limite actuelle |
| --- | --- | --- | --- |
| `GUICTRL`, `GUIWCTLC`, `GUIWSBR`, `GUIWSMB`, `GUIWPKPC` | BAM V1 paletté | boutons et petits contrôles de l'écran monde | ne passent pas par le remplacement PVRZ actuel |
| `GUPORTC`, `PORTL1A`, `PORTL1B`, `PORTL2A` | BAM V1 paletté | cadres/effets de portraits | à corréler avec le HUD en situation |
| `GUIWDB10`, `GUIJRNLC`, `GUIPFC` | BAM V2 | widgets modernes de l'UI | pages sous-jacentes à identifier avant export |

## Mémo HUD — ressources déjà repérées pour les passes futures

| Priorité | Élément visible | Ressources à reprendre | Statut |
| --- | --- | --- | --- |
| 1 | Cadres du journal de dialogue et barre basse | `GUIW12_1` à `GUIW12_8` → `MOS0170`, `MOS0171`, `MOS0172` | pages identifiées, non upscalées |
| 1 | Colonnes décoratives gauche/droite | `GUIWLS20`, `GUIWRS20` → `MOS0176` | page identifiée, non upscalée |
| 1 | Icônes d’actions du bas de l’écran | `GUIBTACT.BAM` → `MOS0112`, `MOS0113` | atlas et 76 cadres identifiés ; éviter de traiter `MOS0113` seul tant que les états de la colonne gauche x4 ne sont pas vérifiés |
| 2 | Cases vides de raccourcis/actions | `GUIWDB10.BAM`, `GUIWDBUT.BAM` → `MOS0173`, `MOS0174` | atlas et coordonnées identifiés ; non upscalés |
| 2 | Variante de colonne gauche utilisée par d’autres compositions | `GUILS20.BAM` → `MOS0141`, `MOS0142`, `MOS0143` | atlas identifiés ; non upscalés |
| 3 | Portraits, contours et petits contrôles | `GUPORTC`, `PORTL1A`, `PORTL1B`, `PORTL2A`, `GUICTRL`, `GUIWCTLC`, `GUIWSBR`, `GUIWSMB`, `GUIWPKPC` | BAM V1 palettés : demande une voie runtime distincte |

Cette table est volontairement limitée à des ressources déjà lues et visualisées. Elle évite de rechercher à nouveau les éléments lors d’une prochaine passe HUD.

## Faisabilité et méthode sûre

1. Produire séparément les six pages `MOS0140`, `MOS0141`, `MOS0170`, `MOS0171`, `MOS0172`, `MOS0176` en x4 avec le preset validé : Topaz Recovery v2, Detail 50, conservation des couleurs.
2. Recompresser en PVRZ DXT5, conserver les coordonnées et déclarer les six empreintes dans le registre de remplacement de l'Infinity Engine Enhancer.
3. Installer seulement ce lot avec un manifeste et une sauvegarde dédiée ; la désactivation restera un simple retour au DLL/manifeste précédent.
4. Vérifier en jeu le HUD 2560×1440 et les écrans qui partagent `MOS0170` (dont `GUIVERB`), puis seulement ensuite tracer les BAM.

La première étape est directement réutilisable depuis le pipeline des menus. Les BAM V1 nécessiteront une extension distincte du runtime : ils sont palettés et ne sont pas des pages PVRZ DXT5. Ils ne doivent donc pas être inclus dans une intégration PVRZ sans ce travail préalable.

## État de cette analyse

- Dossier créé et capture de référence archivée.
- Pages PVRZ et compositions de fond identifiées par lecture des BIF.
- Colonne de boutons gauche reliée à `GUILS10.BAM` et à ses deux atlas.
- Aperçus de référence générés.
- Installation actuelle et rendu du jeu laissés inchangés.
