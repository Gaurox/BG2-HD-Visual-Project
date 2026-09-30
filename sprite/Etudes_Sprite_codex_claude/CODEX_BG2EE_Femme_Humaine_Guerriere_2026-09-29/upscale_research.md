# Codex — comparaison expérimentale xBR / ReboutCX

Date: 2026-09-29. Recherche indépendante: sources exécutables, KEY/BIF vanilla et source amont xBR; aucun audit externe/Claude Code lu. Sorties expérimentales uniquement; aucun asset installé, payload ou release changé.

## Reproduction et corpus

```powershell
& 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe' output/codex_palette_study_20260929/upscale/run_upscale_study.py
& 'C:/Users/Adrien/AppData/Roaming/chaiNNer/python/python/python.exe' output/codex_palette_study_20260929/upscale/probe_palette_sensitivity.py
```

- Runtimes/inputs résolus via `pipeline/scripts/workspace_paths.py`, `config://chainner_python`, `config://reboutcx_model`, `config://mmpx_scalepix`, `config://bg2ee_game_root`.
- Extraction vanilla directe KEY/BIF: `bg2lib.load_key/resolve_resource`, `bam_export.load_bam/decode_bam`; **override non utilisé**.
- Les essais décodent RANGES12; le volet moteur parallèle confirme que le moteur consulte **MPALETTE** et que les pixels RANGES12/MPALETTE locaux sont identiques. Pour développement production, nommer MPALETTE comme ressource moteur; RANGES12 ici = source RGB équivalente de l'expérience, pas preuve d'utilisation native.
- `6110.INI` extrait: animation_type=6000, false_color=1, split_bams=1, armor_max_code=4, resref=CHFB, base=B, specific=F, paperdoll=CHFF, height=WQN, helmet=WQN.
- 60 frames: `CHFB1A1/CHFB2A1/CHFB3A1/CHFF4A1` frame45 (cycle3 début); cycle0 complet de 14 frames `CHFB1A1`, épée `WQNS0A1`, petit bouclier `WQNC0A1`, casque `WQNJ6A1`.
- `G1` est scindé: nombre de frames et lookup corrects ne prouvent pas qu'un frame n'est pas un marqueur 1×1. Le script rejette les marqueurs; exemples définitifs pris dans A1.
- BIF, locator, SHA256 ressource compressée et BAM décompressé, frames/centres: `upscale/results.json`.
- Jeux de données pour essais palette: `upscale/samples/<RESREF>_<frame:04d>/data.npz`; clés `source_indices`, `source_palette`, `palette`, `ramps` (RANGES12 entier), `center`, `guide_x2/x4`, `target_rgb_x2/x4`, `quant_used_x2/x4`, `quant_full_x2/x4`.

## Implémentations effectivement exécutées

| Variante | Définition exacte | Contrainte importante |
|---|---|---|
| xBR x2 | `run_creature_sprite_x2.run_xbr(... direct_upscale_contract(2))` → adaptateur Node → xBRjs `xbr2x` | Une passe, `blendColors=false`, `scaleAlpha=true`; sélection de pixels source, aucune teinte inventée |
| xBR x4 | Même chemin `direct_upscale_contract(4)` → `xbr4x` | **Vrai xBR4x direct**, ni x2→nearest2, ni x2→x2 |
| ReboutCX x4 | Modèle local → Spandrel → PyTorch FP16/CUDA0 | ESRGAN RRDBNet, 64nf/23nb, 16 697 987 paramètres, RGB→RGB, scale=4, aucun canal alpha ni entrée temporelle |
| ReboutCX x2 | Même inférence native x4 → `chainner_ext.resize(... ResizeFilter.Box, False)` → arrondi uint8 | **Pas un modèle entraîné x2**; Box appliqué au float x4 avant arrondi |

- xBR amont: [joseprio/xBRjs](https://github.com/joseprio/xBRjs), [source](https://raw.githubusercontent.com/joseprio/xBRjs/master/src/index.js). La page locale `config://mmpx_scalepix` embarque cette implémentation; identité locale utilisée ci-dessous.
- SHA256 modèle local: `c36a14ddb51ae094324a53b67c345da2d6b6bbf6a2249726056d5b94bdedab05`.
- SHA256 scalepix local: `b8545f0ef97670fe5e077592738ce0faca00bb054dde6e55e23517e892c32598`.
- Environnement mesuré: RTX5090, Python3.11.5, numpy1.24.4, scipy1.9.3, torch2.7.0+cu128, spandrel0.4.1.
- Architecture constatée dans le modèle; dataset, auteur, licence et recette d'entraînement de ces poids locaux non établis par ces essais. Ne pas déduire une garantie sur sprites/animation du seul nom ReboutCX.

## Conditions de comparaison

1. xBR calcule sa géométrie sur le RGB **false-color original du BAM**; `map_output` vérifie l'identité exacte des indices. En cas d'indices RGB identiques, `xbr_provenance_indices` transporte le choix d'indice, pas un nearest-color ambigu.
2. Rebout reçoit un RGB réalisé avec RANGES12, sept couleurs `[30,47,57,12,39,21,3]`; les zones transparentes sont étendues depuis le plus proche pixel visible pour éviter une inférence contre le vert de transparence.
3. Rebout ne détermine pas l'alpha: alpha et classe de recoloration proviennent du guide xBR de **même échelle**. Comparatif de méthodes exploitables pour le moteur, pas benchmark isolant seulement les deux kernels.
4. Quantification RGB Rebout dans OKLab, distance euclidienne, sans dither. Deux branches: candidats limités aux indices présents dans le frame source; ou tous les 12 indices de sa plage / 8 indices de sa classe mixte. Transparent/ombre/réservés restent séparés.
5. Palette de visualisation: classes de 7×12 +21×8; mélanges `(rampA[2:10]+rampB[2:10])//2`. Formule à rattacher à la vérification moteur indépendante du guide global; la comparaison ne démontre pas seule sa conformité native.
6. Indice0 transparent; indice1 noir alpha128 pour la **prévisualisation**. Pas de simulation de lumière de zone, effets palette, profondeur, occultation moteur, ou shader jeu.
7. Panneaux `compare_four.png`: tous les résultats occupent **8 pixels écran par pixel logique source**, nearest uniquement pour affichage; x2 grossi×4 et x4 grossi×2. Marges hors image variables pour équipement, aucune mise à échelle forcée du sprite à une boîte identique.
8. Animation WEBP sans perte: ancres/centres BAM conservés, cycle0 CHFB1A1 complet, cadence comparative100ms/frame, non prétendue cadence native. Couches d'équipement testées séparément: aucun z-order manuel n'est présenté comme sortie moteur.

## Résultats observés

| Observation | xBR x2 | xBR x4 direct | ReboutCX x2 | ReboutCX x4 |
|---|---|---|---|---|
| Contours et silhouettes | Gain net vs nearest, marches restantes | Courbes mieux distribuées à grande taille | Identiques au masque xBR x2 par construction | Identiques au masque xBR x4 par construction |
| Modelé du corps / cheveux | Réorganise teintes source | Réorganise teintes source, petites facettes | Surfaces plus régulières; peut aplatir petits reflets | Transition plus fine, petits détails changés ou lissés |
| Armure et casque | Reflets source conservés | Détails métalliques plus fins | Lissage parfois utile, parfois perte du trait clair | Meilleur support pour shader/gradient futur; aucun détail nouveau certifié |
| Palette dynamique | Provenance exacte source | Provenance exacte source | Classes contrôlées; shading dépend du profil d'inférence | Même contrainte; plus de place spatiale pour nuances/dither |
| Mémoire indices vs vanilla | ×4 | ×16 | ×4 | ×16 |

Visuels inspectés: quatre corps `samples/CHFB*A1_0045/compare_four.png` et `CHFF4A1_0045/compare_four.png`; corps/casque frame6; RGB brut vs quantifié; recoloration contrastée et troisième profil. x4 apporte surtout de la précision spatiale et du modelé, pas une nouvelle information anatomique garantie. Les zones deviennent plus douces avec Rebout; les petites plages et mélanges du guide xBR redonnent une texture/transition dure après quantification. Les planches RGB brutes montrent qu'une part importante du gain est perdue dans ce retour aux classes.

### Chiffres (60 frames, moyenne pondérée par pixels visibles hors ombre)

| Mesure | ×2 | ×4 |
|---|---:|---:|
| Pixels visibles évalués | 60 926 | 243 735 |
| Erreur OKLab moyenne cible Rebout → quantification indices source | 0,021585 | 0,022329 |
| Même erreur → classes complètes | 0,020319 | 0,020954 |
| Réduction de cette erreur | 5,86% | 6,16% |
| Pixels visibles changeant d'indice entre les deux quantifications | 4,21% | 4,43% |
| Fuite de classe/alpha après quantification | 0 | 0 |
| Distance cible Rebout → xBR rendu | 0,037500 | 0,039104 |

- Ces erreurs mesurent l'approximation d'une **cible générée**; elles ne mesurent ni vérité HD, ni préférence utilisateur, ni qualité animation.
- Exemple corps CHFB1A1 frame45: source75 indices; classes complètes105 indices en×2 /117 en×4; Rebout brut2270 /8050 RGB distincts visibles. Indices ajoutés surtout dans les plages/mélanges déjà valides, pas des couleurs fixes indépendantes.
- Exemple casque frame6:44 indices source →58 /74; erreur source→classes0,0242→0,0202 en×2,0,0251→0,0209 en×4.
- Runtime existant `map_output` refuse les indices sans représentant source (`0xFFFF`). **Classes complètes = expérimentation hors installation** tant que cette restriction de représentation n'est pas levée. Un BAM palette modifié directement et un registre HD à représentants sont deux contrats distincts.
- Temps observés: batch60 xBR2=0,124s, xBR4=0,141s; remapping/provenance0,043/0,051s; chargement modèle3,284s; inférence60 frames pour x4+x2=2,606s. Micro-corpus/GPU5090, pas extrapolation garantie à un export complet; I/O PNG/quantification non incluses dans ces sous-mesures.

### Sensibilité aux couleurs d'inférence

`probe_palette_sensitivity.py` réinfère les mêmes frames sous deux autres palettes, sans changer guide alpha/classe. Compare indices optimisés sous profil référence puis recolorés, avec indices directement optimisés sous autre profil.

| Sample | Profil B `[30,63,3,12,39,21,57]`: indices visibles changés | Profil C `[30,55,30,0,39,30,0]`: indices visibles changés |
|---|---:|---:|
| CHFB1A1_0045 | 31,99% | 44,39% |
| CHFF4A1_0045 | 20,26% | 36,28% |
| WQNJ6A1_0006 | 30,91% | 37,04% |

- Écart moyen de couleur rendue OKLab0,014–0,030; pas seulement permutations d'indices RGB égaux.
- Tous les identifiants de couleur de ces profils sont `<0xC8`; aucun mécanisme couleur aléatoire RD/classe spéciale n'entre dans cette expérience.
- `palette_sensitivity.json` + `samples/*/sensitivity_*.png`. Le nom interne `pale` du profil C est arbitraire; la ligne12→0 de peau produit ici une peau sombre, donc ne pas décrire ce profil comme une carnation claire.
- Conséquence: conserver les classes préserve la commande de recoloration du joueur, mais ne garantit pas un modelé satisfaisant avec toutes ses couleurs. Ne pas figer une recette à partir d'une seule combinaison jolie. Test multi-profils obligatoire techniquement pour juger la méthode.

## Décision recommandée pour le guide général

- **Master de recherche: ReboutCX natif×4 RGB + classes/provenance séparées + éclairage latent / quantification multi-profils.** Conserver les cibles RGB avant palettisation; refaire uniquement palette/dither à chaque essai.
- **Candidat de livraison conservateur: xBR×2/xBR×4** selon zoom/mémoire, tant que le gain Rebout n'est pas confirmé sur autres profils et animation. Le xBR×4 n'ajoute pas de nuance; ne pas attendre de lui seul une forte richesse supplémentaire.
- **Rebout×2** doit rester dans la comparaison: plus compact, réduction Box peut atténuer les détails inutiles; son coût d'inférence reste celui du modèle×4.
- Lever «indices source-used» n'apporte qu'un gain limité (~6% erreur RGB cible), mais évite une restriction inutile de la palette. Accompagner de l'adaptation runtime nécessaire; ne pas promettre une révolution visuelle par ce seul changement.
- Séparer géométrie (alpha, zones, arêtes), luminosité continue, matériau, et palette choisie. Ajuster les frontières de classes sous contraintes multi-profils plutôt que remplacer librement une classe par l'indice RGB le plus proche.
- Pas de décision dithering tirée de ces résultats: ici **aucun dither**. Servir de bases identiques aux tests dither de l'étude principale.
- Animation: inférence frame-par-frame et quantification sont sans état temporel; **aucune stabilité temporelle démontrée** par le fait que l'algorithme soit déterministe. Utiliser `attack_comparison.webp` pour inspection puis mesurer erreur temporelle avec correspondances de mouvement, pas différence brute entre silhouettes mobiles.

## Fichiers utilisables directement

- `upscale/results.json`: provenance, timings, métriques120 cas scale/frame.
- `upscale/run_upscale_study.py`: extraction, deux xBR directs, inférence, quantifications, PNG et animation reproductibles.
- `upscale/probe_palette_sensitivity.py`, `upscale/palette_sensitivity.json`: stress multi-profils.
- `upscale/attack_comparison.webp`: animation cinq colonnes, origine ancrée.
- `upscale/recolor_reference.png`, `recolor_contrast.png`, `recolor_pale.png`: indices fixes sous autres choix joueur.
- `upscale/samples/*/compare_four.png`:8 planches corps/équipements représentatifs.
- `upscale/samples/*/compare_quantization.png`: branches source-used / classe complète / RGB cible, mêmes dimensions.
- `upscale/samples/*/data.npz`:60 paquets complets pour essais supplémentaires.

## Points non établis par ce sous-essai

Inventaire exhaustif, effets d'objet, z-order par direction, gestes de magie, marche, paperdolls, épées à deux mains, robes, glow/translucence, moteur réel de palette, tests ingame et débit du pipeline complet: à compléter par les autres volets. La comparaison couvre les quatre traitements demandés sur des exemples véritables et un cycle complet; elle ne vaut pas acceptation globale de la femme humaine guerrière.
