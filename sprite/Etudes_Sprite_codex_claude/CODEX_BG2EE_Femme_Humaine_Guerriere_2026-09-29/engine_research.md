# CODEX — recherche moteur/palettes indépendante — 2026-09-29

Périmètre : sources primaires publiques + exécutable local + code EEex livré. Aucun audit tiers lu; aucun `.claude` consulté; aucun fichier du jeu écrit; aucune validation ingame revendiquée. Les recommandations ci-dessous sont des conclusions de conception, pas une installation.

## Résultats décisifs

- **12 nuances = contrat de recoloration du moteur, pas limite générale de BAM.** BAM V1 transporte 256 indices; le chemin false-color répartit les indices comme ci-dessous.
- **88..255 ne sont pas libres** : 21 paires de canaux × 8 mélanges; remplacer les RGB embarqués dans ces positions ne crée pas 168 couleurs fixes.
- **BG2EE local 2.7.3.0 : mélanges = moyenne entière RGB des nuances 2..9 de deux canaux.** Vérification indépendante des instructions machine; Near Infinity et GemRB diffèrent sur ce point.
- **Le moteur charge MPALETTE.BMP.** RANGES12.BMP sert notamment à Near Infinity; modifier RANGES12 seul n'améliore pas le rendu BG2EE. Les deux extractions vanilla de cette étude sont identiques, ce qui masque facilement cette distinction.
- **EEex autorise des hooks**, mais l'existence d'EEex n'équivaut pas à un shader de recoloration HD prêt à l'emploi. Une extension ciblée doit utiliser les couleurs effectivement réalisées par le moteur, et préserver effets, ombres, couches, cache et compositing.

## Preuve locale reproductible

Fichier lu : `G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition/BaldurReal.exe`.

```
FileVersion  2.7.3.0
SHA256       b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57
ImageBase    0x140000000
```

`Baldur.exe` local = petit loader; ne pas le confondre avec le moteur. Outil : `inspect_engine_codex.py`, dependencies confinées à `research_deps/` (`capstone 5.0.9`, `pefile 2024.8.26`), sortie `engine_disassembly_codex.txt`.

```
& 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe' 'G:/AI/BG2_Upscale/output/codex_palette_study_20260929/inspect_engine_codex.py'
```

RVA = adresse relative à l'ImageBase; ne pas réutiliser ces offsets sur une autre version sans retrouver les fonctions et vérifier les octets.

| Région vérifiée | Lecture indépendante |
|---|---|
| `0x4221C0..0x42224E` | `SetRange` : destination `palette + 4*(4+12*location)`; lecture bitmap `(x=0..11,y=gradient)`; boucle comparée à `0xC`; invalide état de sous-gammes à `this+0x24` |
| `0x421F7B..0x42201E` | génération des 21 mélanges; première source `palette+0x18` donc index 6 = canal0 nuance2; suivante +`0x30` = 12 entrées; 8 répétitions; trois additions RGB suivies de `shr 1` |
| `0x421EE0..0x421F76` | possibilité de recopier 168 sous-couleurs déjà calculées lorsque conditions de cache remplies; ne pas modifier un pointeur partagé en place |
| `0x422250..0x42232D` | construction palette de type1, 256 entrées; index0 vert transparent; indices1,2,3 initialisés noirs |
| `0x26BA53` | xref chaîne `MPALETTE` située RVA `0x59F758`; ressource placée dans objet bitmap à `game+0x63D8` |
| `0x1E8BC4`, `0x1E8BEF`, autres | appels `SetRange` passant `game+0x63D8` comme bitmap en `r9`, confirmant la ressource réellement consommée |
| `0x3F9275` | xref `MPAL256` (RVA chaîne `0x5BEB08`), autre chemin lié aux images à gradients longs; non-utilisé par la boucle12 ci-dessus |

`RANGES12`, `CLRGRAD`, `CLOWNCLR` absents des chaînes ASCII du moteur inspecté. L'absence seule ne serait pas une preuve; les xrefs positifs MPALETTE→SetRange ferment ici la question. Les petits contextes de xrefs du dump peuvent commencer au milieu d'une instruction; ne citer que les lignes décodées cohérentes mentionnées ci-dessus. Noms `SetRange`/`RealizeRange` issus de symboles publics/conventions, algorithme reconfirmé à partir des octets, sans lire d'ancien audit.

## Contrat des indices et des couches

Canaux 0..6 : métal/boucle, minor, major, peau, cuir/sangles, armure, cheveux. Les noms décrivent l'emploi vanilla; le pixel encode un canal, pas une reconnaissance de matériau par teinte. Les couleurs « clown » ne sont qu'un affichage de travail. [IESDP opcode7](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op7).

| Canal | Indices BAM | Emploi body |
|---|---:|---|
| 0 | 4..15 | métal, boucle |
| 1 | 16..27 | minor |
| 2 | 28..39 | major |
| 3 | 40..51 | peau |
| 4 | 52..63 | cuir |
| 5 | 64..75 | armure |
| 6 | 76..87 | cheveux |

Indices0..3 spéciaux : transparence, ombre, noirs réservés. La transparence BAM V1 vient de la première entrée RGB(0,255,0), sinon0; garder les conventions exactes du pipeline. Les octets alpha V1 ont des règles spécifiques à l'interface; ce ne sont pas une solution d'alpha partiel pour les créatures. [BAM V1](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm).

Les 21 paires sont ordonnées lexicographiquement : `(0,1),(0,2),...,(0,6),(1,2),...,(5,6)`. Pour paire `(a,b)` de rang `k`, nuance `j∈[0,7]` :

```
i = 88 + 8*k + j
P[i].rgb = floor((P[4 + 12*a + (j+2)].rgb + P[4 + 12*b + (j+2)].rgb)/2)
```

Moyenne faite séparément sur les entiers des composantes; **pas moyenne en lumière linéaire, pas interpolation perceptuelle**. La routine réalise d'abord les canaux puis les sous-couleurs; tenir compte de l'ordre des effets avant de prétendre reproduire nuit, teintes et magie.

Chaque couche possède sept canaux. Locations d'effets : body0..6, arme16..22, bouclier32..38, casque48..54; le décalage sélectionne la couche, il n'agrandit pas la palette BAM. L'IESDP affiche encore «32–40» dans son ancien résumé mais affirme sept canaux et sa règle +32 : les valeurs32..38 sont la déduction cohérente; ne pas employer39/40. La seconde arme doit garder sa sémantique d'arme malgré son placement dans la couche off-hand. [Opcode7](https://gibberlings3.github.io/iesdp/opcodes/bgee.htm#op7), [NI SpriteDecoder lignes1520–1540](https://github.com/NearInfinityBrowser/NearInfinity/blob/50021b834e0360c6400a6a818626b50edabdd868/src/org/infinity/resource/cre/decoder/SpriteDecoder.java#L1520).

Conséquence : classer les pixels **par indices et rôle de couche**; ne jamais attribuer peau/armure depuis le RGB d'un aperçu recoloré. Un pixel de peau quantifié vers une nuance de vêtement visuellement proche devient faux dès changement de major/minor.

## Fichiers couleur et périmètre de leurs modifications

| Ressource | Fonction / décision |
|---|---|
| `MPALETTE.BMP` | bitmap gradients courts consommé par SetRange; modifier RGB de ses lignes améliore tous les utilisateurs de ces lignes; changement global, pas réservé CHF |
| `RANGES12.BMP` | choix prioritaire de NI pour la prévisualisation; synchroniser avec MPALETTE si nouvelle variante globale; jamais livrer seul |
| `MPAL256.BMP` | gradients longs, notamment format PLT; ne change pas12→256 dans sprites BAM false-color |
| `CLOWNCLR.IDS` | noms→numéros de gradients; ce n'est ni une table RGB ni une 2DA; attention identifiants qui sont aussi random aliases selon contexte |
| `RANDCOLR.2DA` | résout des sélections de gradients aléatoires; conserver la résolution native, particulièrement indices200+; ne pas supposer qu'un CRE200 cible toujours littéralement ligne200 |
| `RACECOLR.2DA` | défauts cheveux/peau par race; humaine exemple IESDP cheveux2, peau12 |
| `CLASCOLR.2DA` | défauts par classe/kit; guerrier exemple métal30, minor91, major93, cuir23, armure93 |
| `CLRGRAD` | aucune ressource canonique pertinente démontrée ici; ne pas inventer un fichier à modifier |

Sources : [RACECOLR](https://gibberlings3.github.io/iesdp/files/2da/2da_bgee/racecolr.htm), [CLASCOLR](https://gibberlings3.github.io/iesdp/files/2da/2da_bgee/clascolr.htm), [RANDCOLR](https://gibberlings3.github.io/iesdp/files/2da/2da_bgee/randcolr.htm), [CLOWNCLR](https://gibberlings3.github.io/iesdp/files/ids/bgee/clownclr.htm), [PLT](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/plt_v1.htm). Utiliser l'extraction locale pour valeurs effectives; documentation = repère.

## BAM versus moteur

- V1 : image à indices8bits; palette commune aux frames d'un BAM; frames uint16, cycles uint8; dimensions uint16, centres int16. La limite12 est introduite par le moteur false-color. Écrire un BAM V1 RGB libre ne retire pas cette recoloration lorsque l'animation est false-color.
- V2 : références à blocs de textures PVRZ, aucune palette d'indices 256 dans ce format. Conversion directe V1→V2 ne conserve donc pas le contrat des sept zones personnalisables. Il faut tester/réaliser une voie de rendu différente; ne pas présenter V2 comme remplacement transparent des personnages. [BAM V2](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v2.htm).
- x2/x4 augmente dimensions et centres; dimensions visuelles ingame dépendent du contrat de mise à l'échelle du runtime HD. Changer seulement les centres ne réduit pas la taille du dessin. Budget pixels : x2≈4×, x4≈16×. Limites historiques BG2 256×256 ne prouvent pas une limite BG2EE2.7; mesurer avec le chemin réel du projet.
- Toutes les informations topologiques restent : nombres/ordre des frames, cycles, timing, centres, miroirs, composition, direction et ordre devant/derrière. Ni les palettes ni un upscale ne recréent à eux seuls une animation manquante.

## Comparaison des implémentations disponibles

| Source vérifiée | Résultat | Usage fiable |
|---|---|---|
| BG2EE2.7.3.0 local | paires nuances2..9, moyenne RGB entière | référence pour cette version, à recouper ingame |
| Near Infinity `50021b834e0360c6400a6a818626b50edabdd868` | `srcIdx=floor(j*12/8)` =0,1,3,4,6,7,9,10, RGB/2 | excellent inventaire/frames/cycles/équipement; aperçu mélanges non-identique |
| GemRB `5552ade1d360fc487be0450eb2a4044fc969439b` | certaines sous-gammes copiées d'un canal, pas les21 moyennes natives | documentation architecture, pas oracle pixels BG2EE |

NI : [SpriteUtils lignes666–704](https://github.com/NearInfinityBrowser/NearInfinity/blob/50021b834e0360c6400a6a818626b50edabdd868/src/org/infinity/resource/cre/decoder/util/SpriteUtils.java#L666). GemRB : [SetupPaperdollColours ligne2930](https://github.com/gemrb/gemrb/blob/5552ade1d360fc487be0450eb2a4044fc969439b/gemrb/core/CharAnimations.cpp#L2930). Sources exactes téléchargées dans `source_reference/`, SHA256/URLs/révisions dans `references.json`; différences vérifiées aussi sur la version NI courante, pas uniquement un ancien fork.

## Solutions de développement, du moins intrusif au plus puissant

1. **Assets seuls, palettes natives** : conserver canal par pixel, reconstruire forme/valeur, quantifier séparément chaque canal, utiliser mélanges natifs uniquement quand une frontière entre ces deux matériaux le justifie; alpha/ombre séparés. Livrable natif avec tous choix joueur conservés. Ne peut changer la forme RGB des douze nuances.
2. **Gradients12 améliorés globaux** : modifier MPALETTE et sa copie d'aperçu; hues et chromas non-linéaires, progression perceptuelle; préserver identités des indices/choix. Effet global (autres personnages, équipements, effets utilisant les mêmes lignes). Hors périmètre CHF par défaut : variante expérimentale séparée uniquement.
3. **Canaux inutilisés d'équipement** : si histogramme de tous BAM de la famille confirme canal inutilisé, attribuer à ce canal un gradient fixe avec opcode7 sur ITM, à la location couche correcte. Fournit12 nuances constantes et8 mélanges50/50 par paire avec canal variable. Ancre blanche74/noire75 éventuelle. Ce n'est pas une case RGB libre; impose de vérifier héritage, tous items partageant la famille, absence de recoloration joueur attendue, effets. Éviter de sacrifier peau/cheveux/major/minor body.
4. **Palette runtime ciblée** : grâce hooks, pour resrefs explicitement CHF/équipements autorisés, substituer des rampes12 propres à la matière et à l'identifiant de gradient; conserver les choix joueur et recalculer les21 sous-gammes; faire tourner effets natifs dans l'ordre d'origine. Gain cohérent pour CHF sans redéfinir MPALETTE de tout le jeu. Attention caches par instance/layer, jamais modifier la ressource globale partagée.
5. **Sidecar HD paramétrique** : image de matériau/canal + coordonnée continue de nuance + masque alpha + ombre; composer à partir des palettes réellement calculées (y compris effets) ou des12 échantillons remontés. Des recettes d'interpolation de nuances permettent antialiasing/sous-nuances sans abandonner la sélection native; une texture RGBA finale peut dépasser256couleurs. Prototype comparé au natif obligatoire; les 12 points d'entrée restent le contrat de couleur.
6. **Rendu personnalisé complet** : shaders/truecolor + masques, nécessaire uniquement si la voie5 n'atteint pas la cible. Plus grande liberté mais responsabilité complète des occlusions, invisibilité, blur, teintes, ombres, lumière et différences de zoom. Ne pas commencer par réécrire ce qui fonctionne déjà.

L'option5 est une architecture proposée, pas une API EEex prête démontrée; inspecter le runtime natif existant du projet avant nouveau hook. Une nouvelle ramp12 perceptuelle peut maintenir le nombre de couleurs tout en améliorer sensiblement les matériaux; interpolation plus fine n'est pas obligatoire pour cette première étape.

## EEex : faits et limites

- [EEex README](https://github.com/Bubb13/EEex/blob/6c1f42b8184877d0222652a20c1ef89a1831db53/README.md) : patching en mémoire, exposition de fonctionnalités; branchemaster potentiellement en développement; compatibilité2.6/2.7 distincte. Utiliser la version installée et son profil binaire.
- [EEex_Assembly_x86-64.lua lignes654,819](https://github.com/Bubb13/EEex/blob/6c1f42b8184877d0222652a20c1ef89a1831db53/EEex/copy/EEex_scripts/EEex_Assembly_x86-64.lua#L654) : hooks avant/après appels et restauration des octets/instructions, watchdog d'intégrité. Preuve de mécanismes de hook, pas d'une extension palette automatique.
- [EEex_Sprite.lua ligne953](https://github.com/Bubb13/EEex/blob/6c1f42b8184877d0222652a20c1ef89a1831db53/EEex/copy/EEex_scripts/EEex_Sprite.lua#L953) : `CVidPalette.RANGE_COLORS` sert notamment à couleur de nom dérivée major. Ne pas la confondre avec les12 nuances d'un sprite.
- [Classes EE documentées](https://eeex-docs.readthedocs.io/en/latest/EE%20Game%20Classes%20%28x86%29/index.html) dérivées de PDB/reverse engineering; les pages x86 ne donnent pas les offsets x64 2.7.3.0. Ne pas copier les offsets d'une autre architecture.
- Fenêtre pratique : intercepter juste avant/juste après la réalisation de palette, ou réutiliser capture/composition déjà disponibles. Palette par couche et par créature, rafraîchie sur équipement/couleur/effet. Prototype de cache doit inclure toutes couleurs réalisées, resref, frame/cycle, échelle, version de traitement, flags utiles; vérifier le rendu avec deux personnages partageant le même BAM mais des couleurs différentes.

## Travaux existants utiles, sans les prendre pour preuve BG2EE2.7

- [1pp Extended palettes](https://gwendolynefreddy.github.io/docs/spellholdstudios/images/files/extpal_readme.html) : ajoute des **choix de gradients**, pas des nuances par gradient. Distingue MPALETTE/MPAL256 et RANGES12 de NI; utile comme antécédent. Les limites du BG2 original citées ne s'appliquent pas directement à l'EE actuelle.
- [1pp note modders](https://mods.shsforums.net/readmes/1pp/1pp-note-for-modders.html) : bibliothèque de couleurs/items et compatibilité; exemple de remplacements d'indices/item. Les256choix sont déjà présents dans les extractions de l'étude : ne pas proposer «installer 1pp pour obtenir256nuances».
- [Palette Generator, réponse du développeur Sam](https://www.shsforums.net/topic/34736-naming-new-paperdolls/page-3) : construit un aperçu/palette d'après MPALETTE BG2EE et paperdoll; outil d'édition, pas preuve d'une modification des gammes natives.
- NI reste préférable pour les inspections structurées, exports indexés, resrefs/cycles/centres/couches; conserver fichier source et métadonnées plutôt qu'un export RGB aplati unique.

## Expériences minimales qui tranchent les incertitudes

| Expérience | Critère |
|---|---|
| Mire BAM 16×16 affichant256indices sur animationfalse-color autorisée | capture runtime vs formule BG2EE, vérifie indices2/3 et21paires; ne pas utiliser aperçuNI comme oracle |
| Changer major seule, puis minor, peau, cheveux | seuls canaux concernés et leurs mélanges se modifient; aucune contamination artificielle |
| Deux créatures mêmeBAM, palettes opposées | absence fuite de cache instance→instance |
| Une gamme modifiée uniquement dans copie RANGES12, puis uniquement MPALETTE | confirme séparation aperçu/moteur sans extrapolation d'ancienne documentation |
| Désactiver/activer éclairage et effets sur mire | vérifie ordre transformation→mélanges et comportement cache |
| Prototype canal équipement fixé | inventaire de tous pixels de ce canal, rechargement, offhand, changement d'arme, effetscouleurs |
| Sidecar 12nuances vs interpolation | conserver le même indicecouleur joueur; comparer relief, visages, contours, coût, stabilitéanimation |

À réaliser dans environnement de test séparé et jeu fermé avant remplacement d'override; la présente recherche ne les a pas exécutées.
