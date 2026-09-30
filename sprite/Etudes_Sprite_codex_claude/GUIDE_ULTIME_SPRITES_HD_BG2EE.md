# Guide de référence — sprites HD jouables de BG2EE

## Femme humaine guerrière `0x6110`, fausses couleurs dynamiques, x2/x4, xBR et ReboutCX

**Version de synthèse :** 2026-09-29  
**Périmètre :** monde de jeu et équipement compatible `0x6110`; paperdolls distingués; BG2EE 2.7.3.0; runtime IEE/EEex du dépôt.  
**Livrable compagnon :** [`GUIDE_ULTIME_SPRITES_HD_BG2EE.html`](GUIDE_ULTIME_SPRITES_HD_BG2EE.html), autonome hors ligne, avec explorateur de palette et comparateurs d’images.  
**Nature :** guide canonique de décision et d’implémentation. Il consolide les études Claude Code et Codex, leurs artefacts, scripts, métriques et revues croisées sans modifier aucun original.

---

## 0. Résultat en une page

### Décision d’architecture

Le sprite HD ne doit pas être stocké comme une image RGBA peinte pour une palette unique. Il doit rester une **description sémantique recolorable** que le runtime reconstruit avec la palette effectivement réalisée par BG2EE pour chaque couche.

```text
BAM P8 + tables/cycles/centres
        │
        ├── indices natifs → classe matière + rampe + alpha/ombre
        ├── xBR x2/x4 → témoin déterministe de géométrie et de provenance
        └── ReboutCX x4 RGB → cible de détail, jamais source de sémantique
                                 │
                       apprentissage multi-palettes
                                 │
                Q3m : position fractionnaire dans une rampe
                                 │
        Q8 optionnel : mélange de deux classes autorisées aux frontières
                                 │
             format versionné + dépendances palette explicites
                                 │
       IEE : décodage avec la palette réalisée de chaque couche
                                 │
           composition native, géométrie écran inchangée (x1)
```

### Choix retenus

| Sujet | Décision | Niveau de preuve |
|---|---|---|
| Palette moteur | Lire/reproduire `MPALETTE.BMP`; `RANGES12.BMP` n’est pas la source runtime BG2EE | **CONFIRMÉ** |
| Couleurs dynamiques | Conserver les 7 gammes, les 21 paires et les palettes distinctes corps/arme/bouclier/casque | **CONFIRMÉ** |
| Master de recherche | ReboutCX x4 pour la cible RGB; xBR4 et source P8 comme témoins sémantiques | **CANDIDAT/PROTOTYPE** appuyé par expériences |
| Livraison initiale | x2 par défaut; x4 optionnel après validation du zoom et de la minification réels | **CANDIDAT/PROTOTYPE** |
| Recoloration HD | Q3m comme premier socle fractionnaire; ajouter Q8 seulement si sa contribution propre justifie coût et complexité | **CANDIDAT/PROTOTYPE** |
| Court terme | Q6 multi-palettes peut servir de verticale fonctionnelle si son contrat de dépendances est versionné | **CANDIDAT/PROTOTYPE** |
| Dithering | Aucun par défaut; ne rouvrir qu’un essai localisé sur banding résiduel | **VALIDÉ EXPÉRIMENTALEMENT** sur le corpus, pas loi universelle |
| Reconstruction | CPU dans le compositeur IEE existant d’abord; shader seulement si profilage le justifie | **CANDIDAT/PROTOTYPE** cohérent avec le runtime actuel |
| Composition | Garder l’ordre et la règle de composition actuels; traiter l’alpha doux séparément | **CONFIRMÉ** pour l’existant; évolution **NON RÉSOLUE** |
| Palette globale | Ne pas modifier `MPALETTE.BMP` globalement | **DÉCISION** de compatibilité |

### Ce qui n’est pas acquis

- Q8 est le meilleur résultat couleur observé, **pas** un format complet prêt à produire.
- Les métriques temporelles mesurent des changements de pixels alignés; elles ne prouvent ni absence de scintillement perçu, ni cohérence de surface.
- Le bénéfice x4 en jeu est rapporté comme léger dans un essai; la plage de zoom effective et le filtre de minification restent à mesurer.
- Les coûts annoncés à partir de plans partiels et de zlib ne remplacent pas une mesure XPRESS du format réellement packé.
- ReboutCX est un modèle RGB sans contrat temporel, alpha ou matière; provenance d’entraînement et licence restent à documenter avant distribution.

---

## 1. Échelle de preuve

Les mots suivants sont normatifs dans ce guide.

| Étiquette | Sens exact |
|---|---|
| **CONFIRMÉ** | Lu dans les ressources, la désassemblage ou le code du dépôt; reproductible sans appréciation visuelle. |
| **VALIDÉ EXPÉRIMENTALEMENT** | Mesuré sur le corpus décrit; la portée ne dépasse pas ce corpus et le protocole indiqué. |
| **CANDIDAT/PROTOTYPE** | Architecture ou paramètre prometteur à implémenter puis valider. |
| **NON RÉSOLU** | Information ou preuve manquante; aucune déduction de production autorisée. |

Une observation en jeu est nommée comme telle. Elle n’implique ni QA globale, ni installation, ni intégration release.

---

## 2. Audit des études sources

### 2.1 Couverture matérielle

L’arbre `sprite/Etudes_Sprite_codex_claude` a été inventorié récursivement et dédupliqué par SHA-256 avant synthèse.

| Mesure | Valeur |
|---|---:|
| Fichiers vus | 5 102 |
| Taille brute | 190 282 813 octets |
| Contenus SHA-256 uniques | 1 709 |
| Copies identiques | 3 393 |
| Taille des contenus uniques | 105 904 888 octets |
| BAM | 2 384 fichiers, dont beaucoup de copies de livraison |
| PNG | 1 968 |
| NPZ | 222 |
| JSON | 210 |
| Scripts Python | 81 |

La forte duplication vient surtout des annexes et dossiers de livraison Codex. Les affirmations ont été confrontées aux fichiers uniques, aux métriques JSON/CSV, aux scripts et aux sources du runtime; aucun fichier d’étude n’a été réécrit.

Contrôles d’intégrité ciblés :

- dossier Claude : 224 fichiers, 202 contenus uniques; 208 PNG et 2 GIF passent la vérification PIL; les 210 médias sont RGB sans canal alpha, donc ils ne prouvent ni alpha doux, ni halo, ni occlusion;
- dossier Codex palette/upscale : 60 NPZ au schéma homogène; 540 PNG recoupés contre leurs tableaux sans divergence; 120 métriques recoupées sans divergence;
- copies `palette/` et `upscale/` racine/étude/delivery identiques hors deux `.pyc` supplémentaires;
- delivery Codex : snapshot pré-revue Claude; son manifeste compte 1 559 fichiers parce qu’il s’exclut lui-même, et ne valide pas les affirmations moteur/ITM.

Les résultats sont auditables mais plusieurs scripts ne sont plus relançables depuis leur emplacement livré : calcul de racine via `parents[3]`, chemins absolus vers Desktop/polices/runtime chaiNNer, poids locaux et dépendance Node `marked`. Une reproduction doit d’abord paramétrer ces dépendances; elle ne doit pas confondre données intègres et recette portable.

Les six références moteur de `source_reference/` sont épinglées par commit et SHA-256 (Near Infinity `50021b834e03`, GemRB `5552ade1d360`, EEex `6c1f42b81848`). `sources_inventory/` n’a pas ce manifeste; `fetch_engine_sources_codex.py` relit le `master` courant et n’est donc pas une recette reproductible du snapshot.

### 2.2 Sources primaires de la synthèse

| Domaine | Sources locales principales |
|---|---|
| Rapport Claude initial/corrigé | [`GUIDE_ClaudeCode_HD_0x6110_palettes_dynamiques.md`](ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/GUIDE_ClaudeCode_HD_0x6110_palettes_dynamiques.md), [`PRESENTATION_ClaudeCode_0x6110.html`](ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/PRESENTATION_ClaudeCode_0x6110.html) |
| Revue croisée finale Claude | [`REVUE_CROISEE_Codex_ClaudeCode_0x6110.html`](ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/REVUE_CROISEE_Codex_ClaudeCode_0x6110.html), `donnees_v3/e5_table.json`, `donnees_v3/e5_results.json` |
| Guide Codex | [`GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md`](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md) |
| Inventaire | [`inventory_research.md`](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/inventory_research.md), `assets_inventory*.{csv,json,gz}` |
| Reverse engineering | [`engine_research.md`](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/engine_research.md), [`engine_disassembly_codex.txt`](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/engine_disassembly_codex.txt) |
| Upscaling et quantification | [`upscale_research.md`](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/upscale_research.md), [`COMPARAISON_CODEX_CLAUDE_0x6110.md`](CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/codex_palette_study_20260929/COMPARAISON_CODEX_CLAUDE_0x6110.md) |
| Runtime du dépôt | `engine/InfinityEngine-Enhancer/source-patchee/source/creature_sprite_x2.cpp`, docs `creature-sprite-0x1000.md` et `creature-sprite-msah-composite.md` |
| Doctrine xBR/ReboutCX | `sprite/XBR2X_RASTER_CONTRACT.md`, `docs/REBOUTCX_PIPELINE_BG2_CODEX.md`, `sprite/PROCESSING.md` |

### 2.3 Conflits résolus

| Ancienne affirmation | Résolution canonique |
|---|---|
| Le moteur charge `RANGES12.BMP` | Faux pour le chemin observé BG2EE : il charge `MPALETTE.BMP`. Les deux extractions vanilla étudiées sont identiques octet pour octet, ce qui explique pourquoi les expériences hors ligne restent valides. |
| Paperdolls équipement préfixés `WPM` | Préfixe observé : `WPN`; corps `CHFF1INV` à `CHFF4INV`; équipement `WPN*INV`/`WPN*OIN`. |
| `H6` et `ZW` sont des casques de production ordinaires | Non : `H6` correspond à des attaques de créatures; `ZW`/`WINGS01` est interdit aux humains. Les exclure du premier périmètre jouable. |
| Q8 prouve un gain temporel universel | Non. La métrique initiale avait un signe d’alignement erroné; la correction garde un gain sur poses alignées, mais l’attaque demeure non concluante. |
| Q8 utilise déjà un format 3 bits complet | Non. E3b a rendu Q3m/Q8 avec 4 bits; l’essai arrondi 3 bits change peu la couleur, mais masque de frontière, présence et métadonnées n’étaient pas packés/mesurés. |
| Un filtre linéaire suffit au x4 | Non. Le runtime fixe actuellement le même filtre MIN/MAG et `GL_TEXTURE_MAX_LEVEL=0`; la minification x4 demande une étude de filtre d’aire ou de mipmaps. |
| EEex fournit une solution pixel shader prête | Non. EEex apporte hooks, lecture d’état et QA; aucune solution de rendu complète prête n’a été identifiée. |

Le script `reboutcx_batch.py` contrôle encore une provenance nommée `RANGES12`. Tant que les octets sont identiques, les images restent cohérentes; le contrat à maintenir doit néanmoins devenir `MPALETTE` ou un alias explicitement vérifié.

---

## 3. Contrat moteur des fausses couleurs

### 3.1 Cible binaire

**CONFIRMÉ** pour l’exécutable étudié :

```text
BaldurReal.exe  2.7.3.0
SHA-256         B51093A49140B2B8A7C046B4652BB8E535BE24EBBC12B1D735E0B94217A14D57
Image base      0x140000000
SetRange RVA    0x4221C0
```

Le BAM V1 expose une palette de 256 indices. La limite de 12 couleurs est celle d’une rampe de fausse couleur, pas du format BAM.

### 3.2 Réalisation d’une palette de couche

`SetRange` copie douze pixels d’une ligne de `MPALETTE.BMP` vers la plage `4 + 12r`. Pour sept choix de gamme :

| Indices | Fonction |
|---:|---|
| `0` | transparent |
| `1` | ombre |
| `2–3` | noirs/réservés |
| `4–15` | métal |
| `16–27` | couleur mineure |
| `28–39` | couleur majeure |
| `40–51` | peau |
| `52–63` | cuir |
| `64–75` | armure |
| `76–87` | cheveux |
| `88–255` | 21 paires lexicographiques de gammes × 8 nuances |

Ce tableau est confirmé pour le chemin BAM V1 false-color étudié; il ne faut pas généraliser « index 0 transparent » à tous les formats et renderers Infinity Engine.

Pour une paire `(a,b)`, une nuance `j∈[0,7]` et ses rampes réalisées `B` :

```text
k(a,b) = rang lexicographique de la paire parmi C(7,2)
i      = 88 + 8*k(a,b) + j
P[i,c] = floor((B[a,j+2,c] + B[b,j+2,c]) / 2), c ∈ {R,G,B}
```

Conséquence : `88–255` ne sont pas des couleurs fixes libres. Ce sont des mélanges dépendants des choix de couleur du personnage.

### 3.3 Une palette par couche

| Couche | Emplacements de couleur |
|---|---|
| Corps | `0–6` |
| Arme | `16–22` |
| Bouclier | `32–38` |
| Casque | `48–54` |

La deuxième arme garde les sémantiques de l’arme même si elle est dessinée côté main gauche. Une reconstruction correcte doit donc utiliser la palette réalisée de la couche courante, pas une palette commune à l’acteur.

Maturité : les emplacements corps/arme/bouclier/casque sont une déduction concordante des sources et du contrat d’opcodes; ils ne constituent pas encore une validation par mire en jeu.

### 3.4 Effets et limites de la capture palette

Capturer les 256 couleurs après `CVidPalette::Realize` suffit pour reconstruire les couleurs résidentes dans la palette, y compris les altérations qui y sont déjà appliquées. Cela ne prouve pas la reproduction automatique de :

- modulation ou tint appliqué après la réalisation;
- alpha, blending ou shaders du renderer;
- cercle de sélection et overlays UI;
- ordre/occlusion des couches;
- effets dépendants du temps hors palette.

Ces éléments doivent être comparés séparément dans le rendu final.

### 3.5 Canaux fixes : exception équipement uniquement

Le corps n’a aucun espace fixe libre sans casser les fausses couleurs. Pour l’équipement, un canal réellement inutilisé peut en théorie être fixé par opcode ITM 7 vers une ligne constante de `MPALETTE` : `74` blanc, `75` noir, `76–78` primaires. Cette technique :

- modifie des ITM partagés;
- crée un risque de compatibilité avec les mods;
- exige une preuve de canal inutilisé sur toutes les frames de la famille;
- ne doit pas devenir la voie générale.

Statut : **CANDIDAT/PROTOTYPE optionnel**, à réserver à un besoin artistique précis.

---

## 4. Anatomie exacte de `0x6110`

### 4.1 Entrée d’animation

```text
id              0x6110
animation_type  6000
false_color     1
split_bams      1
equip_helmet    1
resref          CHFB
base/specific   B / F
armor_max       4
paperdoll       CHFF
height          WQN
```

Les 23 suffixes corps observés sont :

```text
A1 A2 A3 A4 A5 A6 A7 A8 A9 CA G1 G11 G12 G13 G14 G15 G16 G17 G18 G19 SA SS SX
```

Les BAM stockent 9 directions (`S` à `N`) et le moteur produit 7 orientations miroirs : 16 orientations visibles, pas « 9 + 5 ».

### 4.2 Rôle des groupes

| Groupe | Rôle pratique observé |
|---|---|
| `G11` | marche |
| `G1` | posture une main |
| `G12` | attente |
| `G13` | posture deux mains |
| `G14` | impact |
| `G15` | mort, avec chevauchements selon ressources |
| `G16` | sol/tressaillement |
| `G17`, `G18` | attentes |
| `G19` | sommeil/chute/relèvement |
| `CA` | quatre variantes de sort |
| `A7`, `A9` | double maniement |

Ne jamais supprimer un groupe parce que son libellé paraît redondant. Préserver tables, cycles, centres et séquences.

### 4.3 Inventaire réconcilié

Deux comptages répondent à deux questions différentes.

#### Index de production actuel du dépôt

| Couche | Familles | Ressources | Entrées de frame |
|---|---:|---:|---:|
| Corps | 4 | 92 | 41 294 |
| Casque | 19 | 252 | 46 625 |
| Bouclier | 12 | 60 | 16 632 |
| Arme | 31 | 252 | 73 809 |
| **Total** | **66** | **656** | **178 360** |

65 familles sont `pipeline_ready`; `YW` ne contient aucune ressource.

#### Inventaire vanilla exhaustif de l’étude

| Ensemble | BAM | Frames | Frames >1 px |
|---|---:|---:|---:|
| Corps monde | 92 | 41 294 | 11 090 |
| Paperdolls corps | 4 | 9 | 9 |
| Armes monde stock corrigées | 180 | 48 796 | 47 802 |
| Armes main gauche | 72 | 25 013 | 24 897 |
| Boucliers | 65 | 18 018 | 18 017 |
| Casques stock corrigés | 266 | 51 471 | 51 452 |
| Ailes optionnelles | 14 | 572 | 14 |
| Paperdolls équipement | 81 | 162 | 141 |
| **Total** | **774** | **185 335** | **153 422** |

Réconciliation : `656` ressources monde indexées + `85` paperdolls + `33` ressources stock supplémentaires (`D0=5`, `H3/H4=28`) = `774`. Le constructeur d’inventaire Codex classait à tort les 14 `WQNH6*` comme casques via un préfixe `H`; les sources ITM et l’index canonique les classent comme attaques internes de catégorie `FIST`/arme. Les totaux `180 armes monde / 266 casques stock` corrigent le rôle sans changer le total 774.

Paperdolls équipement stock : 30 armes normales `INV`, 1 H6 interne `INV`, 18 offhand `OIN`, 12 boucliers `INV`, 19 casques `INV` dont H3/H4, plus `WPNWMOIN` orphelin. Le lot normal en retient 77; le lot normal total avec 92 corps monde, 536 overlays et 4 paperdolls corps vaut donc 709 ressources. Une couverture étendue H6 vaut 724.

### 4.4 Premier périmètre réellement jouable

Le lot monde utile de départ est de **628 BAM**. Les 536 overlays expriment une politique « équipement joueur normal » : filtre catégorie/masques **plus exclusion explicite des 14 attaques H6**; un filtre littéral catégorie+masques donnerait 550.

```text
92 corps
+ 166 armes principales
+ 72 armes main gauche
+ 60 boucliers
+ 238 casques compatibles
= 628
```

Ce masque exprime la compatibilité technique humaine/guerrière, pas l’obtention en partie. Les restrictions de kit, alignement, caractéristiques, quête et mods restent extérieures.

Exclusions initiales :

- `H6` : attaques de créature, pas casque humain;
- `ZW`/`WINGS01` : interdit à l’humain;
- `D0` : aucune association ITM trouvée;
- `H3/H4` : aucune association casque ITM trouvée;
- paperdolls : pipeline UI séparé.

### 4.5 Partage et routage

- `CHFB1–3` est partagé avec d’autres femmes humaines prêtres et demi-orques.
- `CHFF4` est partagé avec la femme demi-orque guerrière.
- les overlays `WQN*` sont partagés par 13 INI.

Le runtime doit router par **propriétaire d’animation + couche + resref**, et non remplacer globalement un nom natif partagé.

### 4.6 Placeholders

Les frames `1×1` à index `2`, opaques mais visuellement noires, sont des placeholders fréquents. Politique :

```text
préserver frame, lookup, centre, cycle et durée;
ne sauter que l’inférence et le calcul HD lorsque le prédicat exact est vérifié.
```

---

## 5. Runtime HD existant : acquis et limites

### 5.1 Acquis

Le compositeur IEE existant :

- supporte une échelle physique 2 ou 4 tout en gardant la géométrie écran x1;
- reconstruit le RGBA sur CPU depuis les indices et la palette réalisée;
- charge V3 xN indexé, V4 monolithique de recettes AA strictement x2 et V5 indexé compressé XPRESS_HUFF par frame;
- met en cache et téléverse la texture produite;
- conserve l’ordre natif des couches;
- utilise l’alpha final au draw;
- vérifie les entrées de palette référencées par les données générées.

Le pipeline actuel xBR x2 est déterministe et constitue le repli robuste.

### 5.2 Ce que le runtime ne fait pas encore

- V4 refuse `scale != 2`; ses huit opérations séquentielles maximum n’exposent que cinq poids (`7:1`, `3:1`, `1:1`, `1:3`, `1:7`) et ne décrivent pas Q3m/Q8.
- Les anciennes recettes de blend exposent quelques poids, mais pas une courbe fractionnaire complète et versionnée.
- Une présence `representatives` ne suffit pas à exprimer tous les nouveaux indices dépendants de la palette.
- MIN et MAG partagent aujourd’hui le même mode; `GL_TEXTURE_MAX_LEVEL=0`; aucun mipmap.
- Seuls `NEAREST` et `LINEAR` sont implémentés dans ce chemin; Catmull–Rom reste une option documentée non implémentée.
- La règle de composition remplace le pixel par chaque couche non transparente; l’alpha doux inter-couches n’est pas une primitive générale validée.

### 5.3 Essai x4 déjà effectué

**VALIDÉ EXPÉRIMENTALEMENT comme observation de cet essai seulement** :

| Mesure | x2 | x4 | Delta |
|---|---:|---:|---:|
| Payload compressé | 195 904 865 o | 309 550 625 o | +58 %, ×1,58 |
| Performance rapportée | 59,1–60 FPS | même ordre | p95 16,8–17,3 ms |
| Appréciation utilisateur | référence | légèrement meilleur | non acceptation d’architecture |

Le runtime a été restauré en x2 après l’essai; aucune mutation de DLL n’est déduite comme état final.

---

## 6. Chaîne image recommandée

### 6.1 Séparer trois vérités

| Vérité | Source |
|---|---|
| Topologie/alpha/centre/cycle/classe native | BAM P8 original |
| Géométrie agrandie déterministe | xBR à la même échelle |
| Détail RGB souhaité | sortie ReboutCX sur couleurs réalisées |

ReboutCX ne doit jamais décider seul d’une classe matière. Son réseau RRDBNet observé comporte 64 features, 23 blocs et 16 697 987 paramètres; il reçoit du RGB, sans alpha, temps ou étiquette matière. Le hash du modèle étudié commence par `c36a…`; l’origine d’entraînement et la licence sont **NON RÉSOLUES**.

### 6.2 Préparation d’entrée

Pour chaque frame et couche :

1. décoder indices, alpha/ombre, centre et identité de cycle;
2. réaliser plusieurs palettes de couche plausibles;
3. remplir le RGB sous alpha nul par la couleur du plus proche pixel opaque afin d’éviter les halos d’inférence;
4. inférer ReboutCX en x4 sur RGB;
5. produire xBR4 depuis P8 comme témoin; produire xBR2 séparément pour la branche x2;
6. transférer masque, ombre et classes depuis la source/xBR, jamais depuis la couleur Rebout seule;
7. encoder une représentation recolorable commune aux palettes d’entraînement;
8. valider sur des palettes tenues à l’écart.

### 6.3 Master x4, sortie x2

Le master x4 permet de ne pas jeter le détail de recherche. Pour une livraison x2 :

```text
RGB Rebout x4 → réduction BOX/aire vers x2 → ré-encodage sémantique x2
```

Ne pas simplement réduire des plans Q3m/Q8 déjà quantifiés : la quantification et les frontières doivent être recalculées à la résolution livrée.

---

## 7. Méthodes de quantification évaluées

| Code | Description | Lecture canonique |
|---|---|---|
| xBR | géométrie et couleurs xBR | repli déterministe, pas cible ultime |
| Q0 | indices utilisés par la frame, sans dither | baseline runtime actuel |
| Q1 | tous les indices de la même classe | gain faible/inconstant |
| Q2 | Q0 + Bayer 4×4 | motif visible; parfois utile après réduction, pas défaut |
| Q6 | indices sélectionnés sur plusieurs palettes | verticale multi-palettes sans fraction |
| Q3 | position fractionnaire apprise sur une palette | excellente palette connue, généralisation faible |
| Q3m | position fractionnaire multi-palettes | socle continu le plus propre avant frontières |
| Q7 | diffusion d’erreur | instable temporellement; rejet par défaut |
| Q8 | Q3m + seconde classe/poids aux frontières | meilleur résultat couleur observé; contrat incomplet |

### 7.0 Corpus Codex initial et effets isolés

Le corpus initial contient 60 frames réelles : quatre corps représentatifs, les 14 frames d’attaque `CHFB1A1`, plus arme `WQNS0A1`, bouclier `WQNC0A1` et casque `WQNJ6A1`. Il représente 60 926 pixels visibles x2 et 243 735 x4.

| Mesure | x2 | x4 | Interprétation |
|---|---:|---:|---|
| xBR direct, temps 60 frames | 0,124 s | 0,141 s | xBR4 est direct, pas xBR2 agrandi |
| Erreur, indices source | 0,021585 | 0,022329 | baseline |
| Erreur, classe complète | 0,020319 | 0,020954 | gain 5,86 % / 6,16 %, sans fuite de classe/alpha |
| Pixels changés par classe complète | 4,21 % | 4,43 % | effet local |
| Interpolation : gain moyen par frame | 44,6 % | 41,8 % | 60/60 frames améliorées en OKLab |
| Interpolation : gain pondéré pixels | 35,9 % | 33,6 % | mesure plus conservatrice |

Le réseau se chargeait en 3,284 s sur RTX 5090; les 60 inférences x4, dont le x2 est dérivé par BOX, prenaient 2,606 s. Ce micro-benchmark décrit la machine et le corpus, pas un débit de production garanti. La distance Rebout→xBR de 0,03750 x2 / 0,03910 x4 mesure seulement la proximité de deux sorties; ce n’est pas une vérité HD.

Les figures confirment des gradients plus continus avec interpolation, parfois plus mous. Il s’agit d’une simulation hors moteur.

### 7.1 Couleur E3b x4 — corpus corrigé

Erreur moyenne OKLab ×1000; palettes `D` et `E` sont tenues à l’écart.

| Méthode | REF | B | C | D tenue à l’écart | E armure bleue tenue à l’écart |
|---|---:|---:|---:|---:|---:|
| Q0 | 26,54 | 35,98 | 47,07 | 44,15 | 56,62 |
| Q1 | 25,74 | 36,03 | 47,19 | 44,51 | 56,53 |
| Q6 | 32,53 | 29,90 | 31,41 | 42,48 | 49,58 |
| Q3 | 16,34 | 32,33 | 43,80 | 41,46 | 53,92 |
| Q3m | 27,12 | 25,41 | 25,29 | 39,53 | 47,01 |
| Q8 | 23,51 | 23,91 | 23,17 | **37,32** | **44,88** |

Q8 améliore ici les deux palettes inédites d’environ 15,5 % et 20,7 % face à Q0.

### 7.2 Revue croisée E5 — attaque complète, quatre couches

Entraînement `REF/B/C`; moyenne tenue à l’écart `D + CX-B + CX-C`; plus bas est meilleur.

| Méthode | x4 | x2 |
|---|---:|---:|
| xBR | 48,6 | 47,3 |
| Q0 | 49,4 | 47,5 |
| Q1 | 50,3 | 48,3 |
| Q6 | 45,1 | 43,4 |
| Q3 | 47,2 | 45,1 |
| interpolation Codex exacte | 47,0 | 44,9 |
| Bayer Codex | 52,5 | 50,6 |
| **Q8 sRGB** | **37,8** | **35,6** |
| Q8 sRGB exact | 37,9 | — |
| Q8 linéaire | 38,1 | — |

**VALIDÉ EXPÉRIMENTALEMENT :** Q8 est ~23 % meilleur que Q0 et ~20 % meilleur que l’interpolation mono-profil Codex sur cet ensemble tenu à l’écart. La différence sRGB/linéaire est négligeable ici; sRGB est le point de départ simple, pas une vérité universelle.

### 7.3 Temporel corrigé

Taux de pixels changeant au-delà du seuil après alignement de l’acteur, x4 :

| Méthode | Corps REF | Corps B | Moyenne 4 couches × 2 palettes |
|---|---:|---:|---:|
| Q0 | 9,86 % | 18,28 % | 13,62 % |
| Bayer | 6,72 % | 16,02 % | 14,08 % |
| Q6 | 8,29 % | 9,05 % | 12,75 % |
| Q3 | 0,74 % | 10,19 % | 9,23 % |
| Q3m | 5,86 % | 5,60 % | 11,82 % |
| Q8 | **4,80 %** | **4,85 %** | **9,99 %** |
| Diffusion d’erreur | 26,27 % | 30,87 % | 34,01 % |

Les scripts Claude E3/E3b/E5 d’origine conservent le signe erroné. Le tableau ci-dessus vient du second bloc de recalcul Codex, qui applique `ox = (centre_a - centre_b) × scale` et publie `temporal_corrected.csv`. Pour Q8, le corps passe en moyenne de 14,07 % à 4,82 % sur les deux palettes, mais l’agrégation non pondérée complète passe de 13,62 % à 9,99 %. Une agrégation pondérée par pixels donne 13,20 % à 4,90 %. Toujours publier le mode d’agrégation.

Limites : cette métrique ne suit pas une surface en mouvement, ignore perception, boucles, durées et disocclusions. Son masque `guide != 0` inclut ombre et indices réservés, identiques entre méthodes, ce qui dilue les gains et sous-estime les changements. Les 14 frames d’attaque n’offrent pas assez de pixels stationnaires pour une conclusion générale. La prochaine mesure doit publier séparément : tous visibles; recolorables `4..255`; ombre; agrégation pondérée et non pondérée.

### 7.4 Trois bits contre quatre

E3b a généré Q3m/Q8 avec 4 bits de position de rampe. Une réévaluation par arrondi à 3 bits donne en x4 pour Q8 :

```text
REF 23,705  B 24,045  C 23,426  D 37,465  E 45,025
```

La perte est faible face aux résultats 4 bits, donc 3 bits est un bon candidat. Le décodeur exact doit toutefois être optimisé avec l’encodeur C++/Python bit-identique avant gel du format.

### 7.5 Dithering

- Bayer dégrade l’erreur pixel et imprime un motif; après réduction d’aire il peut parfois améliorer une mesure floutée et certaines poses.
- La diffusion d’erreur augmente fortement l’instabilité temporelle.
- Un bruit variable par frame est interdit.

Décision : **aucun dithering par défaut**. Réouvrir seulement un test spatial fixe, localisé à une matière qui présente encore du banding après interpolation fractionnaire.

### 7.6 Étude des rampes

Les sept rampes ont des pas irréguliers. L’égalisation par longueur d’arc réduit leur coefficient de variation d’environ `0,15–0,47` à `0,013–0,027`, mais l’artefact expérimental global change 2 437 positions sur 3 072 — 79,3 %, y compris des lignes spéciales. Ce résultat est un diagnostic, pas un candidat à appliquer à `MPALETTE`.

Lignes non monotones signalées : `197, 198, 199, 204, 212, 213, 221, 253, 255`; doublons RGB : `74–78, 222, 225`. Aucun essai chiffré ne valide l’ajout de couleurs fixes. Toute expérimentation de gradient doit être ciblée, actor-specific et comparée aux mods/effets; jamais une réécriture globale.

---

## 8. Pourquoi Q8 n’est pas encore un format de production

Le prototype de frontière E3b choisit le premier voisin de classe différente dans une fenêtre 3×3. Cela crée quatre défauts :

1. choix non optimal;
2. biais directionnel et risque de dissymétrie au miroir;
3. contamination entre classes sans liste sémantique autorisée;
4. poids nul susceptible d’effacer la classe primaire.

Dans la reproduction Codex, 13,3 % des pixels de frontière pondérés impliquaient plus de deux canaux au total. Une paire arbitraire ne suffit donc pas à garantir une sémantique physique.

Les estimations de taille publiées étaient aussi partielles : le plan frontière, qui concerne environ 21 % des pixels opaques x4 et 32 % x2 dans les échantillons, n’était pas inclus; présence, masque et métadonnées non plus. zlib n’est pas XPRESS.

La mesure partielle `class + t8delta` de Q3m vaut environ ×1,98 la taille Q0 en x2 et ×2,26 en x4 sous zlib. La « taille Q8 » enregistrée est exactement celle de Q3m parce que classe secondaire, seconde position, poids, présence et métadonnées sont omis : elle ne doit jamais être citée comme coût Q8.

### Contrat minimal avant adoption

- liste explicite de paires matière autorisées;
- recherche du meilleur candidat plutôt que premier voisin;
- fallback sans frontière;
- classe primaire toujours valide;
- invariance miroir testée;
- frontière attribuée depuis la provenance source/xBR;
- vrai packing, masque et métadonnées mesurés sous XPRESS;
- golden tests Python/C++;
- test en mouvement et en minification réelle.

---

## 9. Format cible à prototyper

Le numéro de version et le packing ne sont pas gelés. Le contrat logique, lui, doit être explicite.

### 9.1 Enregistrement conceptuel par pixel opaque

```text
kind            transparent | shadow | semantic
primary_class   0..6 ou paire native reconnue
primary_pos     segment de rampe + fraction 3 bits
boundary?       présence optionnelle
secondary_class classe autorisée
secondary_pos   segment + fraction 3 bits
mix_weight      3 bits, borné pour préserver la primaire
```

Les indices natifs `88–255` doivent être reconnus comme courbes de paires existantes, pas aplatis en couleurs fixes. Il faut distinguer :

- une paire native portée par la sémantique du BAM;
- une seconde classe ajoutée par le modèle aux frontières.

### 9.2 Dépendances palette

Chaque frame ou bloc doit exposer exactement les entrées de palette dont dépend le décodage : bitmap 256 bits ou ensemble canonique dérivable des enregistrements. Le runtime :

1. calcule l’empreinte de ces couleurs réalisées;
2. réutilise la texture si l’empreinte est inchangée;
3. reconstruit et téléverse sinon;
4. rejette le format si le contrat de dépendances ne correspond pas.

Ne pas changer silencieusement la signification de `representatives` d’une ancienne version.

### 9.3 LUT de décodage

À partir de `P[256]` capturé pour la couche :

- construire les courbes des sept rampes;
- interpoler les deux nuances adjacentes avec la fraction 3 bits;
- construire, si nécessaire, la courbe des 21 paires natives à partir de leurs couleurs réalisées;
- pour une frontière autorisée, décoder primaire et secondaire puis mélanger selon `mix_weight`;
- commencer par l’interpolation byte sRGB, cohérente avec les résultats E5; comparer linéaire au décodeur exact avant gel.

Python et C++ doivent produire les mêmes octets pour tous les codes valides.

### 9.4 CPU d’abord

Le compositeur reconstruit déjà le RGBA sur CPU. Étendre ce chemin réduit le risque : pas de second hook, même cache, même upload, même ordre de couches. Migrer vers un shader seulement si les mesures CPU/upload/cache sur scène chargée montrent un goulot clair.

EEex reste utile pour instrumentation, lecture d’état, opcodes et QA. Il peut héberger un futur hook, mais n’est pas requis comme deuxième renderer.

---

## 10. x2, x4 et filtrage

### 10.1 Politique

- **Master de recherche :** x4.
- **Livraison initiale recommandée :** x2.
- **Option x4 :** uniquement après preuve au zoom réel avec minification correcte.

Il n’existe pas de seuil universel « zoom ≥ 3 ». Le résultat dépend du contenu fréquentiel, du ratio affiché et du filtre.

### 10.2 Expérience de filtrage minimale

Mesurer à 2560×1440 et aux zooms réellement accessibles :

| Variante | MAG | MIN | Mips | But |
|---|---|---|---|---|
| x2 témoin | nearest/linear | filtre actuel | non | référence actuelle |
| x4 actuel | idem | filtre actuel | non | isoler le coût sans correction |
| x4 aire | idem | BOX/aire explicite | non | qualité de réduction |
| x4 mips | idem | trilinear | oui | stabilité en déplacement/zoom |

Si des mips sont utilisés, ils doivent être régénérés lorsque la palette réalisée change. Séparer toujours les réglages MIN et MAG.

Critères : détail perçu, stabilité au déplacement caméra, halo, coût CPU/GPU/upload, mémoire, cache et FPS/p95. Une capture agrandie en nearest n’est pas une preuve de qualité affichée.

---

## 11. Plan de production `0x6110`

Ce plan décrit des dépendances techniques; ce n’est pas un workflow universel imposé au dépôt.

### Phase 0 — Figer les oracles

**Sorties :**

- lecteur BAM P8 conservant lookup/cycles/centres;
- réalisation Python de `MPALETTE` testée sur les 7 rampes et 21 paires;
- corpus de palettes de couche réelles;
- golden frames pour corps, arme, bouclier et casque;
- décodeur xBR déterministe à la même échelle.

**Passage :** octets de palette et frames natives reproduits exactement.  
**Preuve actuelle :** moteur/palette **CONFIRMÉS**; corpus complet encore **CANDIDAT**.

### Phase 1 — Verticale corps courte

Sélection : une armure, une direction stockée, une attente et quelques pas; inclure transparent, ombre, sept classes et paires natives présentes.

Comparer : Q0, Q6, Q3m, Q8 sans/avec frontière. Utiliser au moins `REF/B/C` pour l’optimisation et des profils `D/E` plus profils réels distincts pour le tenu à l’écart.

**Passage :** Q3m bat Q0 hors palette sans fuite de classe; le coût réel du format est mesuré.

### Phase 2 — Runtime Q3m versionné

- nouveau contrat de registre;
- bitmap/ensemble de dépendances palette;
- décodeur C++ bit-identique;
- cache invalidé seulement par dépendances réellement utilisées;
- fallback xBR x2;
- aucune modification de géométrie/save.

**Passage :** golden tests + scène en jeu corps seul, changements de couleurs répétés, aucune contamination d’une autre animation partageant les BAM.

### Phase 3 — Frontières Q8 isolées

- encodeur de paires autorisées;
- meilleur voisin/candidat, symétrie miroir;
- plan frontière packé;
- ablation `Q3m ↔ Q8` sur mêmes frames/palettes;
- attaque, marche, mort et boucle d’attente.

**Passage :** gain visuel et métrique propre à la frontière justifie taille, runtime et risque sémantique.

### Phase 4 — Quatre couches

Ajouter successivement arme, bouclier, casque. Chaque couche garde sa palette, son cache et son routage. Tester double maniement, deux mains, bouclier, casque visible/caché, changements d’objet et couleurs en temps réel.

**Passage :** parité de composition, centres et occlusion; aucun halo entre couches.

### Phase 5 — Actions et directions

Couvrir les 23 suffixes, 9 directions stockées et 7 miroirs. Tester les transitions, boucles, durées, placeholders et frames partagées. Ne pas se limiter aux frames non triviales pour valider les tables.

**Passage :** aucune frame/cycle manquant; invariance miroir; métrique temporelle par correspondance de mouvement plus inspection en jeu.

### Phase 6 — Extension au lot monde

Étendre au lot utile de 628 BAM, par famille et couche. Mesurer la compression XPRESS, le cache froid/chaud, mémoire et temps d’upload. Conserver l’identité propriétaire/couche/resref dans le registre.

### Phase 7 — Paperdolls

Pipeline séparé `CHFF*INV`, `WPN*INV` et `WPN*OIN`. Ne pas appliquer les hypothèses de zoom, centres ou composition du monde sans mesure UI.

### Phase 8 — Généralisation

Générer un graphe :

```text
animation owner → layer → family → resref → BAM → cycles/frames
                    ↘ ITM associations / restrictions / partage
```

Chaque nouvelle animation hérite des briques génériques, mais reçoit son propre masque de compatibilité et ses preuves. Aucune QA `0x6110` ne valide automatiquement une autre famille.

---

## 12. Palette d’apprentissage et généralisation

### 12.1 Baseline

Trois palettes d’optimisation ont déjà montré un bénéfice net face au mono-profil. Elles ne prouvent pas que `K=3` est optimal.

Le profil expérimental `REF = [30,47,57,12,39,21,3]` n’est pas la guerrière humaine par défaut, qui vaut `[30,91,93,12,23,93,2]`. Ce profil réel n’a pas été inclus dans E3/E5 : ne pas présenter `REF` comme un défaut de jeu.

Expérience à faire : `K=3/4/6`, mêmes frames, mêmes palettes tenues à l’écart, coût d’encodage et temps d’optimisation publiés. Les profils doivent venir de sélections réelles `RANDCOLR`, races et équipements, avec contrastes extrêmes et gammes proches.

### 12.2 Sensibilité observée

Selon la palette, 20–44 % des indices visibles changent lorsque l’inférence est refaite. Une clé de cache d’inférence doit donc inclure la palette; un encodage appris sous une seule palette n’est pas généralisable par construction.

### 12.3 Piste matériau-latent

Inférer en luminance ou représentation matière puis recolorer peut réduire la dépendance palette, mais risque de perdre les indices de matériau fournis par la couleur. Statut : **NON RÉSOLU**, à comparer à Q3m multi-palettes, pas à substituer par intuition.

---

## 13. QA ciblée

### 13.1 Tests hors ligne nécessaires au format

| Test | Invariant |
|---|---|
| `MPALETTE` | 7×12 copies et 21×8 mélanges exacts |
| encode/decode | déterministe; Python = C++ octet par octet |
| dépendances | modifier une couleur non référencée ne change ni hash ni texture |
| classes | aucun pixel hors classe/paires autorisées |
| miroir | résultat miroir identique à l’encodage de la direction réfléchie |
| alpha/ombre | indices spéciaux conservés; aucun halo RGB sous transparence |
| tables BAM | mêmes cycles, lookups, centres et placeholders |
| compression | taille XPRESS réelle, mémoire décompressée et latence mesurées |

### 13.2 Matrice en jeu minimale

```text
corps : armures 1..4
actions : G1, G11..G19, A1..A9, CA, SA, SS, SX
directions : 9 stockées + 7 miroirs
couches : corps seul, arme, main gauche, bouclier, casque
couleurs : profil connu, inédit, contrasté, proche, changements en temps réel
affichage : zoom min/moyen/max réel, mouvement caméra, pause et vitesse normale
effets : invisibilité/tint/dégâts/états applicables, sélection, ombres
performance : cache froid/chaud, foule, changements de palette, FPS/p95, mémoire
```

### 13.3 Validation temporelle correcte

Compléter la différence de pixels par :

- flot optique ou correspondance guidée par le mouvement;
- masques de disocclusion;
- comparaison des coutures de boucle;
- pondération par durée de frame;
- inspection des surfaces matière, pas seulement coordonnées écran;
- vidéo en jeu au ratio d’affichage réel.

### 13.4 Niveaux d’acceptation

Une preuve hors ligne valide l’encodeur. Une capture du runtime valide le décodage. Une session en jeu valide seulement les scènes testées. L’intégration installation/release doit rester un état séparé.

---

## 14. Alternatives écartées ou reportées

| Option | Décision | Motif |
|---|---|---|
| RGBA précoloré unique | Rejet | détruit la personnalisation dynamique |
| Quantification Q0 seule | Repli | limite à 12 niveaux et à l’ensemble source |
| Q1 full-class | Rejet comme solution | gain minime/inconstant |
| Q3 mono-palette | Rejet comme final | surapprentissage palette |
| Diffusion d’erreur | Rejet par défaut | instabilité temporelle majeure |
| Bayer global | Rejet par défaut | trame visible et erreur accrue |
| Palette globale modifiée | Rejet | compatibilité globale/mods |
| Canal fixe corps | Rejet | aucun canal libre |
| Canal fixe équipement | Reporté | possible mais intrusif et spécifique |
| Alpha doux/composition `over` | Reporté | change la sémantique native; expérience séparée |
| Shader complet immédiat | Reporté | CPU existant plus direct; profilage manquant |
| x4 obligatoire | Rejet | gain en jeu insuffisamment caractérisé |
| Mips implicites | Rejet | absents du runtime actuel; doivent être générés/invalidation testée |
| Near Infinity comme oracle runtime | Rejet | ses nuances de paire diffèrent |
| GemRB comme oracle BG2EE | Rejet | renderer différent |

---

## 15. Registre des questions ouvertes

| Priorité | Question | Expérience décisive |
|---:|---|---|
| P0 | Q3m 3 bits conserve-t-il son gain dans le décodeur exact ? | encodeur/décodeur Python+C++, palettes tenues à l’écart |
| P0 | Quelle contribution propre apporte la frontière Q8 ? | ablation Q3m/Q8, même packing et mêmes scènes |
| P0 | Quel est le vrai coût du format ? | plans complets + XPRESS + cache/upload |
| P0 | Les effets post-palette sont-ils reproduits ? | matrice d’effets en jeu, captures avant/après |
| P1 | x4 apporte-t-il un gain au zoom réel ? | MIN/MAG séparés, aire/mips, captures 2560×1440 |
| P1 | Q8 reste-t-il stable en mouvement ? | correspondance de surface + vidéo d’attaque/marche |
| P1 | Quelles paires de matière sont permises ? | règles source/xBR + audit visuel des frontières |
| P1 | `K=3`, `4` ou `6` palettes ? | validation croisée contrôlée |
| P2 | CPU ou shader ? | profil scène foule, palette churn et uploads |
| P2 | Pipeline paperdoll ? | inventaire UI, échelle/centres/filtrage propres |
| P2 | Provenance/licence ReboutCX ? | retrouver modèle, licence et données d’entraînement |

---

## 16. Décision finale

La voie techniquement défendable pour des sprites BG2EE HD jouables n’est ni « plus de couleurs fixes », ni « remplacer les BAM par des PNG ». C’est une représentation HD **matérielle et paramétrique** : géométrie détaillée issue de ReboutCX, sémantique verrouillée par la source P8/xBR, encodage entraîné sur plusieurs palettes, puis réalisation au runtime avec les couleurs exactes de chaque couche.

Le meilleur ordre de réduction du risque est :

```text
Q6 versionné pour prouver le chemin multi-palettes
→ Q3m 3 bits pour le socle continu
→ Q8 par ablation pour les seules frontières qui le justifient
→ x2 en livraison initiale
→ x4 après preuve de minification au zoom réel
```

Ce guide ne déclare donc pas la production terminée. Il fixe les faits moteur, réconcilie l’inventaire, corrige les métriques, élimine les raccourcis erronés et définit le plus petit chemin expérimental capable de transformer les résultats Claude/Codex en système maintenable et généralisable.

---

## Annexe A — Références locales utiles

- `sprite/index/` — index canonique courant du domaine sprite.
- `sprite/README.md` — états et périmètre du domaine.
- `sprite/PROCESSING.md` — conventions de traitement.
- `sprite/XBR2X_RASTER_CONTRACT.md` — oracle raster xBR x2.
- `docs/REBOUTCX_PIPELINE_BG2_CODEX.md` — pipeline ReboutCX du dépôt.
- `pipeline/runtime/README.md` — artefacts runtime.
- `engine/InfinityEngine-Enhancer/source-patchee/docs/creature-sprite-0x1000.md` — registre xN.
- `engine/InfinityEngine-Enhancer/source-patchee/docs/creature-sprite-msah-composite.md` — composition des couches.

## Annexe B — Formules et conventions

```text
indices gamme r      : 4 + 12r ... 15 + 12r
nombre de paires     : C(7,2) = 21
indice paire k,j     : 88 + 8k + j
nuances paire        : nuances 2..9 des deux rampes
mélange vanilla      : floor((A + B) / 2) composante par composante en sRGB entier
position fractionnée : segment de rampe + fraction q/7 pour 3 bits, définition finale à geler
```

## Annexe C — Règles de conservation

- Ne jamais modifier les études sources ni leurs preuves historiques.
- Ne jamais déduire une validation en jeu d’une métrique hors ligne.
- Ne jamais déduire installation ou release d’une production réussie.
- Ne jamais appliquer globalement un remplacement de resref partagé.
- Ne jamais changer `MPALETTE`, payload, staging, TP2, `content.json` ou release sans demande explicite.
- Fermer BG2EE et InfinityLoader avant tout remplacement installé.
