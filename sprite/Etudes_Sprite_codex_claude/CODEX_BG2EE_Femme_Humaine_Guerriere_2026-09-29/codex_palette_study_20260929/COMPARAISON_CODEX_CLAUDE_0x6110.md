# CODEX — Comparaison critique avec l'étude Claude Code, avatar 0x6110

**29 septembre 2026 · Analyse après autorisation explicite de lire le rapport Claude.**

Les deux études initiales restent intactes. Ce document distingue les apports de Claude, les points où je corrige mon guide Codex, les erreurs constatées et la méthode que je recommande désormais. Les essais complémentaires sont hors jeu ; aucun asset installé, code de production ou manifeste release n'a été modifié.

## 1. Mon verdict

**Oui, le travail de Claude améliore substantiellement le mien. Sa proposition algorithmique est plus avancée expérimentalement. Je reprendrais ses essais multi-palettes, son encodage fractionnaire compact et son étude du filtrage à l'affichage.**

La direction principale était commune : conserver les palettes dynamiques et interpoler leurs nuances dans le runtime HD. Claude ne découvre donc pas une architecture opposée à celle de Codex ; il explore plus loin plusieurs étapes que mon guide proposait encore de développer. Ses résultats rendent cette direction plus convaincante.

**Je ne remplacerais toutefois pas mon guide par le sien sans corrections.** Mon étude est plus précise sur la ressource réellement consommée par le moteur et sur l'inventaire. La proposition Claude contient quelques erreurs techniques, une estimation de stockage incomplète et des conclusions trop générales sur le tramage et le x4. J'ai aussi trouvé une erreur de signe dans sa mesure temporelle, encore présente après son propre erratum.

La meilleure base de développement est donc : **faits moteur/inventaire Codex + expériences d'encodage Claude + corrections et protocole commun ci-dessous.**

| Domaine | Apport le plus utile | Décision |
|---|---|---|
| Moteur, MPALETTE, indices dynamiques | Codex : vérification indépendante du binaire | Conserver cette référence |
| Inventaire monde + équipements + paperdolls | Codex : ressources KEY/BIFF et distinction stock/équipable | Conserver le graphe complet et ses filtres |
| Optimisation multi-palettes et palettes de validation | Claude : implémentation et mesures | Intégrer directement au prochain prototype |
| Fraction de nuance et coûts de représentation | Claude : plusieurs précisions comparées | Tester 3 bits comme premier format compact |
| Mélanges aux frontières | Claude : prototype Q8 mesuré | Reprendre avec contraintes de matériaux et encodeur corrigé |
| Zoom et filtrage de réduction | Claude : simulations explicites | Ajouter tôt à mon plan de développement |
| Stabilité temporelle | Aucun résultat définitif ; mesure Claude corrigée ici | Employer les chiffres recalculés, puis tester en jeu |
| Solution sans nouvelle DLL | Claude identifie une possibilité que j'avais trop exclue | Corriger mon affirmation, encadrer le contrat de données |

## 2. Ce que j'ai effectivement lu et vérifié

Sources Claude :

- [Guide Markdown initial](<../../ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/GUIDE_ClaudeCode_HD_0x6110_palettes_dynamiques.md>).
- [Présentation HTML, avec erratum](<../../ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/PRESENTATION_ClaudeCode_0x6110.html>).
- Scripts `outils/e3_experiment.py`, `outils/e3b_experiment.py`, données `donnees/e3_results.json` et `donnees_v2/e3b_results.json` ; inspection des comparatifs visuels v2.
- Code local des palettes, des producteurs de registre et de `creature_sprite_x2.cpp`, limité aux divergences à trancher.

**La présentation HTML est plus récente que le guide Markdown.** Son erratum retire notamment les conclusions initiales « Bayer pire sur toutes les métriques » et « scintillement moyen divisé par deux ». E3b remplace les douze premières positions de repos, souvent répétées, par vingt positions de changement de pose. Avec dix positions de marche et quatre couches, le corpus corrigé comporte **120 occurrences de frames**, contre 88 dans E3.

J'ai relancé E3b dans un nouveau dossier Codex. Les erreurs couleur et les ratios temporels publiés sont **reproduits exactement** dans cette exécution : écart numérique maximal relevé **0**. J'ai ensuite recalculé l'alignement temporel et arrondi Q8 à la précision de 3 bits annoncée. Les originaux Claude n'ont pas été modifiés.

Preuves : [résumé des vérifications](comparaison_claude_20260929/verification_summary.json), [script de reproduction instrumentée](comparaison_claude_20260929/recheck_claude.py), [résultats E3b reproduits](comparaison_claude_20260929/reproduction_e3b/e3_results.json). Les hashes des documents et scripts Claude lus sont enregistrés dans le résumé.

## 3. Les apports Claude que je retiens

### 3.1 L'optimisation multi-palettes est maintenant testée, pas seulement proposée

Mon étude démontrait la sensibilité du réseau à la palette d'entrée et proposait de minimiser une erreur sur plusieurs palettes. Claude a implémenté cette étape : trois palettes d'ajustement, deux palettes de validation non utilisées par l'encodeur.

Définitions utiles :

| Méthode Claude | Contenu |
|---|---|
| Q0 | Quantification actuelle, indices présents dans la frame source |
| Q1 | Toute la classe palette, ajustement sous une seule palette |
| Q6 | Indices seuls, choix commun optimisé sur plusieurs palettes |
| Q3 | Nuance fractionnaire, ajustement sous une seule palette |
| Q3m | Nuance fractionnaire, ajustement multi-palettes |
| Q8 | Q3m + mélange avec une classe voisine aux frontières |

Résultats E3b x4 reproduits, **distance moyenne OKLab ×1 000** à la sortie du réseau :

| Méthode | REF | B, ajustement | C, ajustement | D, validation | E, validation |
|---|---:|---:|---:|---:|---:|
| Q0 | 26,54 | 35,98 | 47,07 | 44,15 | 56,62 |
| Q1 | 25,74 | 36,03 | 47,19 | 44,51 | 56,53 |
| Q6 | 32,53 | 29,90 | 31,41 | 42,48 | 49,58 |
| Q3 | 16,34 | 32,33 | 43,80 | 41,46 | 53,92 |
| Q3m | 27,12 | 25,41 | 25,29 | 39,53 | 47,01 |
| Q8 | 23,51 | 23,91 | 23,17 | 37,32 | 44,88 |

**Ce résultat est utile :** Q8 diminue l'erreur sur les deux palettes de validation d'environ **15,5 % et 20,7 %** face à Q0. Le gain ne se limite donc pas aux couleurs ayant servi à l'ajustement. Q6 fournit aussi un compromis sans interpolation, avec une perte sur REF explicitement visible.

Limites : deux palettes de validation, une armure, deux séquences et une direction ne couvrent pas les couleurs du jeu. La cible est toujours l'image inventée par ReboutCX, pas une vérité HD ou une préférence humaine. Les chiffres Codex initiaux ne sont pas directement comparables : corpus, profils et masques différents ; Claude inclut notamment l'ombre dans `guide != 0`, là où plusieurs mesures Codex excluaient les indices spéciaux.

### 3.2 Une fraction de nuance à 3 bits est un bon point de départ

Mon guide proposait deux indices et un poids sur un octet. Claude exploite l'ordre connu de chaque gamme : un indice de base, un successeur déterministe et une fraction de huitième. Sur une gamme de douze nuances, cela donne **89 positions** le long de la courbe, sans ajouter de couleur choisissable par le joueur.

L'idée est meilleure comme point de départ compact : les deux indices arbitraires ne sont pas nécessaires pour l'interpolation intérieure d'une gamme. La LUT proposée, 2 048 entrées pour `indice × 8 + fraction`, est simple à recalculer par empreinte de palette. Les dépendances des successeurs doivent entrer dans le cache.

Une réserve sur les mesures était nécessaire : E3b utilise `FRAC_BITS = 4`. Q3 possède des variantes explicitement arrondies à 3 et 2 bits ; **Q3m et Q8 sont évalués avec des fractions de nuance à 4 bits**, alors que le format recommandé en prévoit 3. Le poids de frontière, lui, est déjà au huitième.

J'ai arrondi les deux coordonnées de nuance de Q8 à 3 bits, sans réoptimiser ses poids. Résultat x4 :

| Palette | Q8 mesuré à 4 bits | Q8 arrondi à 3 bits |
|---|---:|---:|
| REF | 23,508 | 23,705 |
| B | 23,915 | 24,045 |
| C | 23,170 | 23,426 |
| D | 37,317 | 37,465 |
| E | 44,883 | 45,025 |

La différence est faible : cette vérification **renforce le choix de 3 bits**, sans faire passer les images initiales pour un rendu bit-exact du format proposé. [Données x2 et x4](comparaison_claude_20260929/precision_3bits.csv).

### 3.3 Les frontières entre classes méritent un traitement spécifique

Mon prototype conservait les classes et interpolait principalement leurs nuances intérieures. Claude montre que les transitions héritées du guide xBR restent un obstacle : une paire native 50/50 peut produire un liseré clair quand les deux matériaux sont recolorés autrement.

Son Q8 permet un poids différent de 50/50 et une nuance distincte de chaque côté. C'est un prolongement pertinent de ma proposition, **plus avancé sur le plan expérimental**. Les images inspectées montrent des jonctions plus douces ; une partie des marches de l'armure disparaît.

![Extrait Claude E3b : xBR, Q0, Bayer, Q6, Q8 et cible réseau sous la palette B](comparaison_claude_20260929/figures/claude_crop_idle_B.png)

*Image issue du dossier Claude `figures_v2/crop_idle_s0_B.png`, reproduite ici pour comparaison. Le dernier panneau est une cible réseau, pas une capture du jeu.*

Je reprends cette piste, mais pas encore son choix de voisin tel quel :

- `boundary_blend` choisit le **premier voisin d'une autre classe** dans un parcours fixe du voisinage 3×3. Il ne recherche pas le meilleur candidat parmi tous les voisins. Ce choix peut introduire un biais de direction ou de miroir.
- « Deux classes » ne signifie pas toujours « deux gammes ». Une classe peut déjà être un mélange natif de deux gammes. Dans la reproduction x2+x4, **13,3 % des pixels de frontière effectivement pondérés impliquent plus de deux canaux** au total.
- Des poids nuls remplacent entièrement la contribution de la classe principale. Conserver son étiquette ne suffit donc pas à affirmer que la dépendance aux couleurs est inchangée.

Ces observations ne rendent pas Q8 mauvais. Elles imposent de vérifier **quelles couleurs peuvent agir sur chaque pixel**, avec des tests de recoloration d'un canal à la fois, et de limiter les mélanges aux matériaux réellement voisins. L'encodeur final doit garder l'option sans mélange et n'accepter une frontière que si elle améliore le critère retenu sans contaminer une région protégée.

### 3.4 Le filtrage de réduction manquait de priorité dans mon guide

Claude a raison de séparer résolution de stockage et résolution réellement affichée. Une texture x4 peut être réduite à l'écran ; le `NEAREST` peut alors sélectionner quelques texels et perdre une partie de l'amélioration, ou rendre le tramage instable au zoom.

Vérification du code local : le runtime choisit `NEAREST` ou `LINEAR` pour les filtres MIN et MAG et fixe `GL_TEXTURE_MAX_LEVEL = 0`. Il ne suffit donc pas d'ajouter un nom de filtre mipmap : il faut générer les niveaux, autoriser leur lecture et gérer leur actualisation quand la palette change. Le principe MIN/MAG distinct est celui de l'API. [Khronos, glTexParameter](https://wikis.khronos.org/opengl/GLAPI/glTexParameter).

![Simulation Claude, Q8 x4 réduit : nearest à gauche, filtre d'aire à droite](comparaison_claude_20260929/figures/claude_display_z2_Q8.png)

Je place désormais l'essai de filtrage **avant le choix définitif x2/x4**, avec le rendu logique, les contours et l'alpha réels du projet. Le x4 reste un bon master ; son installation n'est pas automatiquement le meilleur compromis.

Je ne retiens pas en revanche un seuil universel « x4 utile seulement à partir d'un zoom 3 ». Pour une texture x4, il y a encore réduction à 3 pixels écran par pixel logique. Le seuil exact dépend des fréquences de l'image, des filtres et du rendu souhaité. L'erreur `NEAREST` contre `BOX` n'est pas une mesure de beauté. Au zoom 2, le zéro du x2 est en partie tautologique : il n'est plus réduit. Les propres chiffres Claude à zoom 1,3 ne montrent d'ailleurs pas systématiquement plus d'écart pour x4 que pour x2.

### 3.5 Autres apports à conserver

- Diffusion d'erreur testée : son mauvais comportement temporel sur ce corpus renforce son exclusion comme défaut.
- Palettes de validation distinctes de celles de l'ajustement ; comparaison K=3/4/6 à poursuivre.
- Clé de cache d'inférence incluant la palette : indispensable pour éviter de réutiliser une cible calculée avec d'autres couleurs.
- Exemples ITM concrets pour la QA, dont une arme avec pulsation opcode 9 ; à vérifier dans l'installation cible.
- Comparateur interactif et simulations d'affichage : utiles pour décider à échelle de jeu, en complément des agrandissements.
- Piste supplémentaire du HTML : inférer une carte de nuances en niveaux de gris, indépendante de la palette. Elle pourrait éliminer la dépendance chromatique par construction et réduire le nombre d'inférences. C'est une hypothèse intéressante, **non testée** : le réseau peut mal traiter ce nouveau signal et perdre les contrastes de matière. Garder classe, ombre et transparence séparées, puis comparer à Q3m.

## 4. Une correction supplémentaire de la mesure temporelle

### 4.1 L'erratum Claude était nécessaire mais incomplet

Claude corrige honnêtement la dilution due aux poses répétées dans E3. Il faut utiliser E3b et son erratum, pas reprendre les petits pourcentages du Markdown initial.

J'ai trouvé dans E3b une autre erreur, lignes 454–462 du script fourni :

```python
ox = (fb.center_x - fa.center_x) * scale
oy = (fb.center_y - fa.center_y) * scale
# puis comparaison de A[x,y] avec B[x-ox,y-oy]
```

Or les coordonnées monde satisfont :

```text
xa - centre_a = xb - centre_b
donc xb = xa + centre_b - centre_a
```

Avec les slices du script, il faut donc `ox = (centre_a - centre_b) * scale`, et de même pour y. Le signe actuel compare des positions différentes dès que les centres changent.

L'effet n'est pas théorique : sur les dix-neuf transitions de repos sélectionnées, les ancres changent 9 fois pour le corps, 15 pour le casque, 10 pour le bouclier et 19 pour l'arme. Un contrôle synthétique d'une même image recadrée compare 5 pixels faux sur 5 avec l'ancien signe, contre 0 sur 6 avec le signe corrigé. [Vérification reproductible](comparaison_claude_20260929/verification_summary.json).

### 4.2 Résultats après correction du signe

Même réseau, mêmes pixels reconstruits, mêmes seuils ; seul l'alignement de la métrique change. Ratios x4 :

| Méthode | Corps REF | Corps B | Moyenne des 4 couches × 2 palettes |
|---|---:|---:|---:|
| Q0 actuel | 9,86 % | 18,28 % | 13,62 % |
| Bayer | 6,72 % | 16,02 % | 14,08 % |
| Q6 indices multi-palettes | 8,29 % | 9,05 % | 12,75 % |
| Q3 fraction, REF seule | 0,74 % | 10,19 % | 9,23 % |
| Q3m fraction multi-palettes | 5,86 % | 5,60 % | 11,82 % |
| Q8 fraction + frontières | 4,80 % | 4,85 % | 9,99 % |
| Diffusion d'erreur | 26,27 % | 30,87 % | 34,01 % |

**La méthode Q8 conserve un bénéfice important.** Sur le corps, moyenne REF/B : **14,07 → 4,82 %**, soit environ **−65,7 %**. Sur la moyenne non pondérée des huit couples couche/palette : **13,62 → 9,99 %**, soit **−26,7 %**, et non les −33 % de l'erratum E3b. [CSV complet x2/x4](comparaison_claude_20260929/temporal_corrected.csv).

La moyenne pondérée par le nombre de pixels comparés donne encore un autre résultat : **13,20 → 4,90 %**. Il faut toujours préciser l'agrégation ; un casque avec très peu de pixels stables ne doit pas peser silencieusement autant que le corps.

Ces pourcentages ne sont pas des mesures de scintillement perçu en jeu. Ils comptent les variations au-dessus de 0,02 OKLab dans des pixels où la cible réseau varie de moins de 0,01. Même correctement alignés par l'acteur, les pixels ne suivent pas une surface articulée. Les ombres restent incluses. Il manque aussi la transition de bouclage et le rendu réel des poses maintenues dans le temps. Pour une prochaine étude, publier à la fois résultats sur changements de pose et résultats pondérés par leur durée native.

### 4.3 Le désaccord sur le tramage se réduit

Nous recommandons tous les deux **sans tramage par défaut**. Les divergences chiffrées ne justifient pas un verdict universel :

- Claude mesure surtout l'erreur pixel par pixel ; mon étude mesurait aussi l'erreur après un filtrage spatial. Le Bayer peut améliorer une moyenne locale tout en augmentant l'erreur des pixels individuels.
- Le Bayer testé par Claude peut réduire la métrique temporelle sur le corps, même s'il ajoute une trame et n'améliore pas la moyenne de toutes les couches.
- Ni étude ne teste toutes les intensités, tous les masques blue-noise, tous les repères de phase ou une compensation de mouvement complète.

Je garderais donc ma formulation prudente : **ne pas utiliser le tramage dans la recette par défaut ; n'en rouvrir l'étude que pour une surface présentant encore des bandes après les améliorations principales.** Dire qu'aucun tramage ne peut jamais aider dépasse les essais effectués.

## 5. Les points du rapport Claude à corriger avant développement

### 5.1 MPALETTE, pas RANGES12, pour le moteur

Le rapport et le HTML attribuent répétitivement `SetRange` à `RANGES12` et présentent sa modification comme un changement global ingame. **C'est inexact pour le binaire étudié.**

Les deux BMP extraits sont identiques, donc cela ne fausse pas les essais couleur. En revanche, le moteur charge **MPALETTE**, passé ensuite à `SetRange`. La vérification Codex des xrefs est dans [le désassemblage](../engine_disassembly_codex.txt), notamment RVA `0x26BA53` et appels via l'objet bitmap `+0x63D8`. Modifier seulement RANGES12 ne réalise pas la modification du moteur annoncée.

La description de MPAL256 comme palette complète des créatures non-Character est aussi trop générale et trompeuse : son usage documenté inclut les lookup de **PLT**, notamment les paperdolls ; ce n'est pas la solution aux douze nuances de ce sprite. [Format PLT, IESDP](https://gibberlings3.github.io/iesdp/file_formats/ie_formats/plt_v1.htm).

### 5.2 Paperdolls et périmètre des ressources

Claude indique `WPM**INV` pour les équipements d'inventaire. Pour l'humaine étudiée, le stock vérifié est **WPN**, avec `INV/OIN`. Employer WPM ferait travailler sur la mauvaise taille/famille.

Les nombres 656 et 774 ne représentent pas deux décomptes incompatibles :

```text
774 BAM Codex = 656 monde recensés par Claude
              + 85 paperdolls (4 corps +81 équipements)
              + 33 ressources de stock monde (D0 : 5 ; H3/H4 : 28)

656 monde Claude = 628 corps+overlays liés au filtre humain/guerrier
                 + 28 H6/ZW de stock particulier
```

`WINGS01/ZW` n'est pas utilisable par une humaine normale, et les ITM d'apparence H6 sont des attaques de créatures, pas des casques. Ces stocks ne doivent pas imposer du travail au premier personnage. Les restrictions de kit/alignement/caractéristiques restent à appliquer au sous-ensemble de base. Le CSV complet est utile pour l'exhaustivité ; le sous-ensemble filtré est utile pour produire.

Le plan de test Claude mentionne aussi « 9 directions (5 miroirs) » : pour cette famille, retenir **9 vues stockées +7 directions miroir**. [Inventaire et explications Codex](../inventory_research.md).

### 5.3 La taille de Q8 n'est pas encore celle d'un payload complet

Le Markdown précise bien que le plan frontière n'est pas compté. Cette réserve disparaît de certaines synthèses du HTML. Le ratio ×2/×2,3 est donc une **estimation partielle**, pas une taille de registre Q8 utilisable.

De plus, les pixels sont rendus avec des coordonnées à 4 bits alors que l'estimation alternative `class+t8delta` les arrondit à 3 bits pour compter les octets. La petite différence de précision a été vérifiée ici ; elle ne dispense pas de mesurer le format exact, **frontières, masque de présence, métadonnées et codec XPRESS compris**.

Ne pas décider le budget mémoire, la résidence du cache ou la taille de la famille complète à partir des seuls nombres zlib de l'échantillon.

### 5.4 Le « plancher 0,04 » n'est pas une borne démontrée

La dépendance de ReboutCX aux couleurs d'entrée est réelle dans les deux études. Elle justifie un compromis multi-palettes. Elle ne prouve pas qu'aucun encodeur ne peut dépasser une erreur donnée : recherche des voisins, choix des profils, modèle, représentation des frontières et espace d'optimisation peuvent changer.

La formulation défendable est « erreur résiduelle de ces méthodes sur ces palettes ». De même, affirmer que le joueur ne verra jamais REF ne justifie pas d'ignorer la dégradation de Q6 sur cette palette : aucune impossibilité d'obtenir ces combinaisons n'est démontrée, et plusieurs de ses couleurs sont communes.

### 5.5 Effets natifs, interpolation et EEex

Capturer `P[256]` préserve les **effets réalisés dans la palette**, pas automatiquement tous les effets du renderer. Alpha, sélection, occlusion, shaders, modulation et ordre de composition restent à conserver et à tester. Passer l'alpha doux au mode « over » est un changement de comportement, pas une simple extension de l'octet couleur.

Nous convergons sur le point pratique : étendre le C++ IEE déjà en place, plutôt que faire le travail de chaque pixel en Lua. La formulation « EEex ne peut rien apporter au rendu » est trop absolue, puisqu'il fournit aussi des mécanismes de hooks natifs. Ici, rien ne démontre qu'un second hook EEex apporte un avantage au point de capture existant.

## 6. Ce que je corrige dans ma propre proposition

### 6.1 J'avais présenté la modification DLL comme trop obligatoire pour Q1/Q6

Mon guide disait qu'autoriser des indices absents de la frame source exigeait une adaptation du producteur **et du runtime**. La lecture ciblée donne raison à une partie de l'observation Claude :

- Le code C++ actuel vérifie surtout `representatives[index] != 0xFFFF` pour la présence des indices.
- Il utilise également cette présence pour sélectionner les couleurs de l'empreinte de palette.
- Dans les chemins lus, il ne se sert pas de la valeur marquée comme d'un offset à échantillonner dans la frame x1 : il possède déjà les 256 couleurs réalisées.

**Une variante de producteur et de ses vérificateurs peut donc être compatible avec ce runtime sans nouvelle DLL**, à condition de déclarer toutes les dépendances nécessaires. C'est un raccourci de prototypage réel que mon guide excluait trop fortement.

Il reste à expliciter le changement de sens du champ : les vérificateurs Python actuels comparent encore cette table aux représentants réels de la source. Changer uniquement l'écrivain ferait échouer ces contrôles. Je recommande un profil/version de producteur distinct, une vérification du contrat sur le build ciblé et un test d'invalidation après changement de palette. Pour le futur format fractionnaire, un masque de dépendances explicite reste préférable à une table dont le nom suggère des positions source.

Sources locales : [creature_sprite_x2.cpp](G:/AI/BG2_Upscale/engine/InfinityEngine-Enhancer/source-patchee/src/iee/creature_sprite_x2.cpp), lignes 1264, 1337–1339, 2146–2158 ; [reboutcx_batch.py](G:/AI/BG2_Upscale/pipeline/scripts/reboutcx_batch.py), lignes 430–484 ; [reboutcx_cpu_p10.py](G:/AI/BG2_Upscale/pipeline/scripts/reboutcx_cpu_p10.py), lignes 92–111 et 165–167. Cela décrit le **code inspecté**, pas une validation de la DLL actuellement installée.

### 6.2 Je ne figerais plus le choix RGB linéaire sans comparaison au décodeur final

Mon prototype mélange en lumière linéaire ; Claude mélange les octets sRGB. Pour moyenner des couvertures, la lumière linéaire est une base physique cohérente. Pour interpoler une courbe de modelé artistique, elle ne garantit pas automatiquement la meilleure approximation de la cible.

Claude projette dans OKLab puis reconstruit en sRGB ; ces courbes ne sont pas identiques. Mon choix de segment dans OKLab puis de poids linéaire comporte aussi une approximation. **Le prochain encodeur doit optimiser contre le décodeur réellement livré** : pré-calculer les positions de nuance au huitième, les rendre selon la règle choisie, puis mesurer l'erreur multi-palettes sur ces valeurs exactes.

Tester sRGB et RGB linéaire sur un corpus identique devient une expérience simple, plutôt qu'une préférence théorique. Garder une règle bit-exacte entre Python et C++ ; ne pas prétendre que l'un des deux espaces gagne avec les deux études actuelles, qui ne partagent pas ce protocole.

### 6.3 Je réduirais la première extension avant de tout réunir

Je retiens l'encodage compact de Claude, mais commencerais par **Q3m sans mélange de classes**, puis mesurerais séparément l'ajout de Q8. Cela distingue le gain des sous-nuances du gain des frontières et facilite le diagnostic des couleurs étrangères.

Le V4 existant n'est pas une implémentation complète déjà prête : ses poids sont limités et le lecteur lu rejette V4 lorsque l'échelle n'est pas x2 (`creature_sprite_x2.cpp:2023`). Une nouvelle version fractionnaire reste un vrai développement, que son nom soit V6 ou autre.

## 7. Méthode fusionnée que je recommande maintenant

| Ordre | Travail limité et vérifiable | Décision obtenue |
|---:|---|---|
| 1 | Corpus commun : quatre armures Codex + repos/marche Claude + attaque ; poses et durées natives ; profils d'ajustement distincts des profils de validation | Comparaison homogène, métriques sans erreur d'ancre |
| 2 | Prototype Q6, d'abord compatible source-used puis classe complète sous contrat de dépendances documenté | Gain possible sans attendre le renderer fractionnaire |
| 3 | Q3m : indice + successeur + fraction 3 bits ; optimisation sur les valeurs exactes du décodeur ; effets palette courants | Gain intérieur des gammes, coût réel et cache correct |
| 4 | Comparer filtrage de réduction, zooms effectivement utilisés, x2 et x4 | Format de livraison et filtre choisis ensemble |
| 5 | Ajouter Q8 aux seules frontières validées ; choisir les voisins selon l'erreur et leur matière, tester chaque canal isolément et les miroirs | Gain des transitions sans contamination incontrôlée |
| 6 | Mesurer format complet, XPRESS, uploads et cache ; tester plusieurs acteurs aux couleurs opposées | Coût réel et absence de fuite entre instances |
| 7 | QA ingame puis couverture corps/équipements/paperdolls selon l'inventaire filtré | Personnage de référence complet |

Paramètres de départ : master ReboutCX x4 ; dérivé x2 par Box puis **réencodage** à x2 ; sans tramage ; fraction au huitième ; trois profils d'ajustement pour reproduire l'expérience, puis défauts réels classe/race/objets et validation plus large. Le choix K=4 est une hypothèse de développement, pas un optimum démontré.

Conserver xBR2/xBR4 comme témoins de géométrie et de provenance. Maintenir séparés le masque de silhouette, l'ombre et le modelé. Reporter l'alpha doux après la première validation opaque. Laisser les remplacements globaux MPALETTE et les astuces de canaux fixes d'équipement hors de ce premier prototype, sauf besoin identifié sur une pièce précise.

Une expérience latérale vaut la peine : carte de nuances grise ou autre représentation indépendante de la palette, confrontée à Q3m sur les mêmes profils. Si elle réussit, elle pourrait simplifier davantage le pipeline que l'augmentation de K. Si elle détruit les petits détails ou les contrastes entre matières, conserver le consensus RGB multi-palettes.

## 8. Conclusion de choix

**Pour lancer le prochain prototype de rendu, la proposition Claude est meilleure que mon premier guide sur l'encodeur : elle transforme plusieurs de mes pistes en expériences mesurées.** Je reprendrais ces résultats, avec l'alignement temporel corrigé, une vraie mesure du payload complet et des frontières mieux contrôlées.

**Pour décider quels fichiers traiter et comment le moteur les recolore, ma base Codex reste la référence la plus solide des deux sur ce cas.** MPALETTE, WPN, les partages et les ressources réellement équipables doivent être corrigés dans toute synthèse issue de Claude.

Le choix n'est donc pas de conserver une étude intacte au détriment de l'autre : le meilleur résultat est une architecture commune, rendue plus concrète par Claude et plus précisément bornée par ces vérifications. Les gains offline sont crédibles et reproductibles ; la supériorité visuelle finale reste à confirmer en mouvement dans BG2EE.

## Annexe — fichiers produits pour cette comparaison

- [Rapport de vérification et hashes](comparaison_claude_20260929/verification_summary.json).
- [Ratios temporels avant/après correction, x2/x4](comparaison_claude_20260929/temporal_corrected.csv).
- [Arrondi Q8 à trois bits](comparaison_claude_20260929/precision_3bits.csv).
- [Reproduction instrumentée](comparaison_claude_20260929/recheck_claude.py) et [agrégation](comparaison_claude_20260929/summarize_recheck.py).
- [Guide Codex initial, inchangé](../GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md).

Reproduction depuis le dépôt, dans une nouvelle copie du dossier d'expérience si les résultats présents doivent être conservés :

```powershell
$studyPython = 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe'
& $studyPython output/codex_palette_study_20260929/comparaison_claude_20260929/recheck_claude.py
& $studyPython output/codex_palette_study_20260929/comparaison_claude_20260929/summarize_recheck.py
```

Le script lit le E3b original sur le Bureau et les ressources locales ; il écrit uniquement dans le nouveau dossier de comparaison. Il ne modifie ni les documents Claude ni le guide Codex initial.
