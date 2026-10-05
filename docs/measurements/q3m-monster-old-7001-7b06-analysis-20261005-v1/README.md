# Monster_old — ogrillon / loup d'ombre, analyse offline

- Demande : points noirs `QOLD7001`, transparence `QOLD7B06` ; aucun log récent disponible. Lecture KEY/BIF vanilla, catalogue/feuilles/DLL installés ; aucune installation, production, QA ou release modifiée.
- Reproduction : `config://chainner_python analyze.py` ; NumPy/Pillow, Unicorn acquis dans `sprite/.work/q3m-runtime-tools-20261003-v1`. Résultat `[analysis.json](analysis.json)` : SHA catalogue/DLL, huit feuilles cibles +quatre Half Ogre, sources canoniques, 1 068 frames. Lecture des frames indépendante des sentinelles des cycles inutilisés des BAM legacy.
- Comparaison : natif x2 nearest / Q3m installé ; mêmes palettes, centres/dimensions conservés ; agrandissement nearest pour inspection. Simulations CPU des palettes neutres, pas des captures ingame. [Détail](comparison-detail.png), [ogrillon dix poses](7001-comparison.png), [trois couleurs de cheveux](ogrillon-hair-palette-comparison.png), [loup dix poses](7B06-comparison.png), [Half Ogre](7000-comparison.png).

## Ogrillon — défaut natif rendu plus visible

- `MOGNG1/G1E/G2/G2E`, 384 frames. Faux-colors natifs : 76–87 = cheveux ; présents aussi sur dos/bras/jambes, hors tête. Exemple `MOGNG1 frame129` : `(x18,y16)=78`, `(x22,y16)=79`, `(x12,y25)=86` ; coordonnées BAM natives. Ils deviennent sombres, jaunes ou verts selon la couleur des cheveux ; même phénomène vanilla. Q3m lisse la peau autour, conservant ces îlots sémantiques : visibilité accrue des points.
- Zéro index noir réservé 2/3 dans les 384 frames natives et HD de l'ogrillon. Half Ogre `7000` contient déjà index2 noir en vanilla : 296 pixels natifs, 1 184 au nearest x2 contre 1 103 HD. Pas de génération accidentelle d'indices réservés dans l'ogrillon.
- Proposition : correction locale des îlots `hair` hors tête dans le guide HD MOGN, vers la matière voisine adéquate (peau/vêtement), toutes poses/directions ; encodage K6 Q3m x2 conservé. Garder cheveux/visage et détails voulus. Éviter un nettoyage RGB noir : dépend de la palette et supprimerait des détails légitimes. Il s'agit d'une retouche HD du contenu vanilla, avec nouvelle production/version et nouvelle QA ciblée.

## Wolf shadow — masque natif irrégulier, contours accentués

- `MWLSG1/G1E/G2/G2E`, 380 frames. La source vanilla contient index1 sur une large partie du corps, mélangé aux matières opaques : aspect moucheté/semi-transparent intrinsèque. Index1 RGB0 ; indices245/248/249 RGB10/7/6, presque noirs également. Ne pas transformer automatiquement le loup en modèle opaque.
- Oracle des instructions réelles `CVidPalette::Realize` : flags5 → transparent0, index1 alpha127, matières alpha255 ; flags7/alpha127 → index1 alpha63, matières alpha127. Le runtime Q3m conserve l'alpha primaire de la palette capturée ; aucune preuve offline d'une perte globale de transparence dans cette étape. Paramètres réels de la session non capturés.
- Guide actuel `q3m_family_witnesses.py:source_plan` : RGBA source alpha255 pour tous les indices non nuls, y compris index1 ; xBR fait donc ses choix de contour sans distinguer les deux opacités natives. Q3m préserve ensuite les classes du guide, mais ce guide a déplacé la frontière index1/matière : **13 555 pixels x2 opaque→semi-transparent, 11 527 semi-transparent→opaque**, cumul des 380 frames, pas une mesure temporelle ingame. **40 454** changements du masque index1 au total, dont échanges avec le fond ; 25 859 changements du masque0. Index1 total +0,30% seulement : redistribution spatiale plutôt qu'effacement global.
- Proposition : guide MWLS tenant compte de l'alpha natif (index1=127), avec contrôle des frontières des zones internes ; au besoin masque natif x2 conservé pour ces zones. Réencoder uniquement les quatre BAM MWLS, RGB Q3m amélioré x2 sans SDF, comparer toutes directions/poses. Conserver les paramètres de transparence réellement transmis par le jeu ; aucun changement global du shader ou de l'alpha de toutes les créatures.

## Limite et suite

- Les motifs signalés sont reproduits offline ; les nouvelles retouches sont proposées, non appliquées. Un log/capture récent serait nécessaire seulement pour rattacher un autre rendu ingame à ses flags/palettes exacts. QA Monster_old reste en attente ; autres familles et historiques inchangés.
