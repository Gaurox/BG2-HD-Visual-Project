# BAM V1, BAM V2 et PVRZ - notions indispensables

> **Statut :** Documentation communautaire de référence - IESDP  
> **Dernière vérification :** 2026-08-27

## BAM V1

Format d’animation à palette. Il contient notamment :

- un en-tête ;
- les entrées de frames ;
- les cycles ;
- une palette ;
- une table de correspondance vers les frames ;
- les pixels, compressés ou non.

Chaque entrée de frame stocke largeur, hauteur et coordonnées de centre X/Y. Les cycles peuvent partager des frames au moyen d’une table d’indirection. La transparence dépend d’un index de palette ; le format peut employer un encodage RLE.

Pour BGEE, l’alpha de palette n’est pris en compte que dans certains contextes d’interface. Le comportement historique est conservé pour les anciennes ressources.

## BAM V2

Format Enhanced Edition dans lequel les données d’image sont réparties en blocs pointant vers des pages PVRZ. Une frame conserve largeur, hauteur et centre, mais référence un ou plusieurs blocs de texture.

Chaque bloc précise notamment :

- page PVRZ ;
- coordonnées source ;
- largeur/hauteur ;
- coordonnées de destination dans la frame.

Une frame peut donc être assemblée à partir de plusieurs rectangles.

## PVRZ

Les PVRZ sont des PVR compressés par zlib. Ils servent aux BAM V2, MOS V2 et TIS Enhanced Edition. L’IESDP indique des textures généralement en puissances de deux, jusqu’à 1024 pixels, avec compression de texture de bureau limitée à BC1/DXT1 ou BC3/DXT5.

## Conséquences pour un upscale

- multiplier seulement l’image ne suffit pas : centres et coordonnées de blocs doivent suivre la même transformation ;
- une frame répartie sur plusieurs blocs doit être recomposée puis redécoupée sans trou ni chevauchement ;
- les cycles et la table de frames doivent rester identiques sauf migration intentionnelle ;
- le choix V1/V2 influence palette, alpha, compression, taille et coût de reconstruction.

## Ne pas confondre

Le format autorise certaines grandes dimensions, mais le moteur peut imposer des limites d’affichage dépendant de la version. L’IESDP ne donne pas une valeur certaine pour BGEE au-delà d’une indication « 1024x1024 ou plus » pour BAM V1. Toute taille cible doit donc être testée réellement dans BG2:EE.

## Sources
- IESDP BAM V1: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm
- IESDP BAM V2: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v2.htm
- IESDP PVRZ: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/pvrz.htm
