# Guide HD — Femme humaine guerrière `0x6110` — palettes dynamiques

> **Auteur : Claude Code (Claude Opus 5.5)** — 2026-09-29. Recherche **indépendante et parallèle à Codex** :
> ne pas fusionner sans comparaison. Hors dépôt : aucun fichier de `G:/AI/BG2_Upscale` modifié, aucune
> installation, aucun essai en jeu. Expériences offline dans un scratchpad, copiées dans `figures/`,
> `donnees/`, `outils/` à côté de ce fichier.

Niveaux de preuve utilisés : **[mesuré]** par ce travail · **[code]** lu dans le code du dépôt ·
**[audit]** hérité de l'audit P6.1 du dépôt (commit `00c667eb`), non refait ici · **[externe]**
IESDP/GemRB/iwd2-re · **[hyp.]** hypothèse à vérifier.

---

## 0. Décisions en bref

| # | Constat / décision | Preuve |
|---|---|---|
| D1 | La limite « 12 couleurs » ne vient **pas** du BAM (indices 8 bits libres) mais de `CVidPalette` : 7 gammes × 12 nuances copiées de `RANGES12.BMP`. | [audit] [mesuré] |
| D2 | Chemin Character `false_color=1` : **toute** la palette 4..255 est dynamique (84 nuances + 168 demi-mélanges de paires). Seules couleurs fixes : 0 transparent, 1 ombre, 2-3 noirs réservés. Aucune couleur fixe supplémentaire exploitable par les assets. | [audit] [mesuré] |
| D3 | Le runtime HD du projet (DLL IEE) reconstruit déjà chaque texture x2/x4 **sur CPU** à partir du snapshot `CVidPalette::Realize` de chaque calque. La contrainte 8 bits n'existe plus que dans le format du registre → levier principal. | [code] |
| D4 | **Encoder une position continue dans la gamme** (sous-nuance 3 bits) et laisser le DLL interpoler dans la palette réalisée du joueur (effets compris) : erreur de quantification −36 %, scintillement du corps (palette REF) ÷10. | [mesuré] |
| D5 | Ajustement **multi-palettes** (K palettes à l'inférence) + **mélange pondéré 2-gammes aux frontières** : erreur sur palettes jamais vues −15 à −22 %, scintillement moyen −50 à −63 %, taille compressée ×2,0 (x2) à ×2,3 (x4) hors plan frontière. | [mesuré] |
| D6 | **Pas de dithering** : Bayer et diffusion d'erreur dégradent toutes les métriques ; diffusion = scintillement ×3,5 ; Bayer x4 = aliasing maximal à l'affichage. | [mesuré] |
| D7 | Gain **immédiat sans toucher au DLL** : choix d'indice par consensus multi-palettes, classe complète, sans dithering (Q6) → palettes inédites −4 à −12 %, palettes contrastées −17 à −33 %, taille identique. | [mesuré] |
| D8 | x4 n'apporte un gain réel qu'avec **zoom ≥ ~3 px écran/px logique** ou une **minification filtrée** (mipmaps/aire/SSAA). En `NEAREST` à zoom 1,3-2, x4 est minifié → aliasing ; à zoom 2, x2 est exact et x4 non. | [mesuré] simulation |
| D9 | EEex : aucun levier pixel utile au rendu (Lua, pas de hook plus fin que le DLL IEE). Utile pour la **QA** (opcode 7/8/9 par calque, lecture couleurs) et comme base de symboles moteur. | [code] EEex installé |
| D10 | Méthode recommandée **RCX-FRAC-MP** (§5) ; repli immédiat **RCX-IDX-MP** (§5.4). | — |

---

## 1. Fonctionnement réel du système de palettes

### 1.1 Chaîne complète Character (`0x6110`, `6110.INI` : `false_color=1`, `split_bams=1`, `resref=CHFB`, `armor B/B/B/F`, `height_code=WQN`)

```text
CRE : 7 octets couleur (métal, mineure, majeure, peau, cuir, armure, cheveux)
  → 4 jeux par gamme : corps / arme / bouclier / casque (défaut = même valeur)          [externe][hyp.]
  → opcode 7 « Set color » : param1 = ligne RANGES12, param2 = 0xPR
       P = 0 corps, 1 arme, 2 bouclier, 3 casque ; R = gamme 0..6                        [mesuré ITM]
  → CVidPalette type RANGE, une par calque (le DLL capture un Realize par calque)       [code]
  → SetRange (RVA 0x4221C0) : ligne RANGES12 (12 px) → indices 4+12r..4+12r+11          [audit]
  → Realize (0x421430) : effets de gamme et globaux sur les 12 nuances
       (teinte, add, lumière+saturation, gris/pétrification, lueur pulsée)               [audit]
  → RealizeRange (0x421F7B) : 21 paires a<b × 8 :
       P[88+8k+t] = floor((B[a,t+2] + B[b,t+2]) / 2), t=0..7, par canal sRGB             [audit]
  → 0 transparent (forcé 0), 1 ombre noire alpha floor(128·transp/255), 2-3 noirs       [audit][code]
  → CVidCell : indices → couleurs réalisées ; Character : composition CPU des calques
       (tout pixel non transparent écrase le précédent) → 1 texture → draw GL
       (`fpDraw` : modulation vColor + uColorTone, blending alpha)                       [code]
```

Table des indices (identique corps/arme/bouclier/casque) :

| Indices | Classe | Remarque |
|---|---|---|
| 0 | transparent | singleton |
| 1 | ombre | noir, alpha partiel moteur |
| 2, 3 | réservés | noir fixe ; 2 = marqueur des frames nulles 1×1 des BAM scindés |
| 4-15 / 16-27 / 28-39 / 40-51 / 52-63 / 64-75 / 76-87 | métal / mineure / majeure / peau / cuir / armure / cheveux | nuance 0 = la plus claire |
| 88-255 | 21 paires × 8 | demi-mélange des nuances **2..9** seulement ; ordre lexicographique (métal-mineure, métal-majeure, …) |

Faux oracles écartés par l'audit : Near Infinity `interpolateColors` (niveaux 0,1,3,4,6,7,9,10) et GemRB
`SetupPaperdollColours` (copie de rampes). Implémentation de référence du dépôt :
`pipeline/scripts/reboutcx_quantize.py::character_chmb1_classes / character_chmb1_palette_rgb`.

### 1.2 Données couleur du jeu [mesuré]

| Ressource | Contenu utile |
|---|---|
| `RANGES12.BMP` = `MPALETTE.BMP` (octet pour octet, `Default.bif`, 12×256) | 256 gammes de 12 nuances |
| `RANDCOLR.2DA` | entrées 200-255 = tirage aléatoire (HairSet1, NobleMajorSet1, MetalNormal…) ; ex. `HELM01` cuir/armure = 202, `PLAT04` métal = 208 → couleurs variables par instance |
| `RACECOLR.2DA` | humain : cheveux 2, peau 12 |
| `CLASCOLR.2DA` | FIGHTER : métal 30, mineure 91, majeure 93, cuir 23, armure 93 |
| `MPAL256.BMP` (256×256) | palettes complètes des créatures non-Character ; **non utilisé** par 0x6110 |
| `UI.MENU` `CHARACTER_COLOR` | le joueur ne choisit que cheveux/peau/majeure/mineure (`Infinity_Set*Color`) ; métal/cuir/armure viennent classe + objets |

Objets (ITM, effets d'équipement) [mesuré] : 2 435 opcodes 7 (arme 1 549, corps 450, bouclier 270,
casque 166) ; opcodes 8/9 (lueur/pulsation) sur ~290 armes/corps ; 50/51/52 rares. Exemples QA :
`PLAT01` (armure 27, cuir 23, métal 30), `HELM01` (J6 : 202,202,28,14), `ISHLD03` (D3 : 100@armure, 70@métal),
`BDSW1H06` (S1 : 3 couleurs + **op 9 pulsée** sur l'arme), `SW1H01` (248 aléatoire), `CARSOMYR` (S2).

### 1.3 Géométrie perceptuelle des gammes [mesuré, OKLab]

| Mesure | Valeur | Conséquence |
|---|---|---|
| Sens | nuance 0 L̄=0,83 → nuance 11 L̄=0,21 | t croissant = plus sombre |
| Pas médian entre nuances voisines | ΔE_OK 0,055 (p10 0,025 ; p90 0,096) ≈ 2-5 seuils de discrimination | bandes visibles sur un dégradé HD |
| Non-uniformité (pas max/min par ligne) | médiane 2,8 ; p90 9,2 | ex. métal 30 : 0,10-0,13 dans les clairs, 0,03-0,05 dans les sombres |
| Monotonie | 247/256 lignes ; 9 lignes avec pas quasi nuls | projeter sur la polyligne, pas sur L seul |
| Dérive de teinte clair→sombre (gammes chromatiques) | médiane 20°, p90 113° | interpoler entre nuances voisines, jamais en teinte |

### 1.4 Usage réel des indices sur 0x6110 [mesuré, `donnees/usage_6110.json`]

| Élément | Constat |
|---|---|
| Corps `CHFB1-3`, `CHFF4` | ombre ≈ 18 % des pixels visibles ; 6-10 nuances/gamme par frame (médiane) ; mélanges 3-6 % |
| Frames nulles | BAM scindés : 6 804 à 7 551 frames `1×1, centre 0, indice 2` par corps (sur 10 323) |
| Casques | mélanges massifs : `HELM01` métal-armure 19 %, `BDHELM16` cuir-cheveux 23 %, `DHELM01` métal-cuir 26 % |
| Armes | armure + métal dominants ; 4-9 nuances/gamme par frame ; indice 2 utilisé par arcs/2 mains (cordes, liserés) |
| Boucliers | majeure/mineure fréquentes (couleurs du joueur si l'objet ne les fixe pas) |
| Contrainte actuelle ReboutCX | candidats = indices **présents dans la frame x1** ; élargir à la classe complète ne gagne que ~3 % (Q1) : la limite réelle est la discrétisation à 12 niveaux |

### 1.5 D'où viennent les limites

| Limite | Origine | Contournable par |
|---|---|---|
| 256 indices, 1 transparent, RLE | format BAM V1 | rien à gagner : le DLL ignore le BAM pour les pixels HD |
| 12 nuances par gamme, 7 gammes | moteur `CVidPalette` + `RANGES12` | DLL (sous-nuances) ; remplacer `RANGES12` = changer les couleurs vanilla (déconseillé) |
| Mélanges = moyenne ½, nuances 2..9 | moteur `RealizeRange` | DLL (mélanges pondérés, toutes nuances) |
| Pas de couleur fixe 4..255 | moteur (type RANGE) | aucune ; une couleur RGB littérale casserait teinte/gris/pétrification |
| Alpha binaire des sprites | contrat actuel du registre + compositeur « écrasement » | DLL (plan alpha + composition « over ») |
| Géométrie logique x1 | moteur | déjà contourné (backing x2/x4) |
| Taille/résidence | budgets DLL (x4 512 Mio par pack, cache index 128 Mio) | catalogue paresseux existant |
| Rendu minifié en `NEAREST` | choix QA actuel + zoom moteur | mipmaps/aire sur la texture composite |

BAM V2/PVRZ (RGBA) : incompatible avec la recoloration Character → exclu.

---

## 2. Solutions techniquement possibles

| Id | Solution | Niveau | Effet mesuré / attendu | Verdict |
|---|---|---|---|---|
| S1 | Candidats = classe complète au lieu des indices de la frame x1 | pipeline | −3 % erreur, scintillement armes → 0 | inclus dans S2 |
| S2 | Indice choisi par **consensus multi-palettes** (Q6) | pipeline | palettes B/C −17 à −33 %, inédites −4 à −12 %, REF +22 % | **phase A** |
| S3 | Dithering ordonné (Bayer 4×4 ancré au centre BAM) | pipeline | pire partout ; motif visible ; aliasing x4 max | **rejeté** |
| S4 | Diffusion d'erreur 1-D dans la gamme | pipeline | scintillement ×3,5 | **rejeté** |
| S5 | Dithering temporel | — | impossible proprement : une frame BAM tient plusieurs ticks ; alternance = scintillement | rejeté |
| S6 | **Sous-nuance fractionnaire** (t continu, 3 bits) interpolée dans la palette réalisée | DLL + pipeline | REF −36 %, scintillement corps ÷10 | **phase B** |
| S7 | **Mélange 2-gammes pondéré (k/8)** aux frontières | DLL + pipeline | pixels frontière −16 à −48 % | **phase B** |
| S8 | Ajustement multi-palettes de t (K palettes) | pipeline | robustesse recoloration (§4) | **phase B** |
| S9 | Re-estimation des classes à la résolution HD (Q5) | pipeline | faible vs S8 | option |
| S10 | Alpha doux silhouette + ombre douce | DLL + pipeline | bords anticrénelés ; non mesurable offline | **à tester (E7)** |
| S11 | Assombrissement recolorable : mélange vers l'indice 2 (noir réservé) | DLL | liseré/occlusion qui suit la recoloration | option (contours) |
| S12 | Minification filtrée (mipmaps prémultipliés sur la composite, ou échelle choisie selon le zoom) | DLL | condition du gain x4 | **phase B** |
| S13 | Remplacer `RANGES12` par des gammes perceptuellement uniformes | données | moins de bandes mais change toutes les couleurs vanilla/objets/mods | non (mod séparé éventuel) |
| S14 | Patch de `RealizeRange` (autres poids) | moteur | S7 fait mieux sans patch binaire | non |
| S15 | Couleurs RGB fixes littérales | DLL | cassent effets et recoloration | non |
| S16 | EEex pour le rendu | EEex | Lua trop lent, pas de hook pixel | non ; EEex = QA |

---

## 3. Expériences

### 3.1 Déjà réalisées ici (reproductibles)

| Id | Script (`outils/`) | Entrées | Sorties |
|---|---|---|---|
| E1 | `e1_ranges.py` | `RANGES12`, `MPALETTE`, `MPAL256` | `donnees/ranges12_stats.json` |
| E2 | `e2_usage.py` | 65 manifestes source 0x6110 | `donnees/usage_6110.json` |
| E3 | `e3_experiment.py` (Python chaiNNer) | CHFF4 G12 (idle sud, 12 frames) + G11 (marche sud, 10 frames) ; `WQNJ6G1`, `WQND3G1`, `WQNS1G1` mêmes cycles ; 5 palettes | `donnees/e3_results.json`, `figures/` |

```powershell
cd G:\AI\BG2_Upscale\pipeline\scripts
python <dossier>\outils\e1_ranges.py <out>
python <dossier>\outils\e2_usage.py <out>
& $chainnerPython <dossier>\outils\e3_experiment.py <out_e3> <out>\ranges12.npy   # $chainnerPython = config://chainner_python ; ~50 s sur RTX 5090
```

Protocole E3 : vérité = sortie ReboutCX (fp16, sans padding) du source rendu sous la palette X ;
x2 = BOX de la x4 (contrat production) ; guides xBR2/xBR4 = classes/transparence ; palettes
`REF (30,47,57,12,39,21,3)`, `B (21,57,47,8,66,30,0)`, `C (19,63,66,15,39,26,4)` = apprentissage ;
`D (67,68,47,84,25,57,2)` et `E armure bleue (…,68,3)` = **jamais vues** par l'encodeur.
Métrique = ΔE OKLab moyen ×1000 sur pixels opaques ; scintillement = % de pixels statiques
(Δvérité < 0,01) dont la sortie change de > 0,02 entre frames consécutives (alignées sur le centre BAM).

### 3.2 Résultats E3 [mesuré]

x4 (x2 dans `e3_results.json`, mêmes tendances) :

| Méthode | REF | B | C | **D inédite** | **E inédite** | Scint. corps REF/B % | Scint. moyen % | Taille zlib Ko |
|---|---|---|---|---|---|---|---|---|
| xBR x4 (référence de distance, pas de qualité) | 40.3 | 38.6 | 45.0 | 44.2 | 53.8 | 0.75 / 0.98 | 0.51 | 91 |
| **Q0 actuel** (indices de la frame, sans dither) | 26.8 | 36.4 | 47.3 | 44.6 | 56.9 | 0.97 / 2.01 | 0.54 | 120 |
| Q1 classe complète | 26.0 | 36.5 | 47.4 | 44.9 | 56.8 | 0.96 / 2.02 | 0.53 | 126 |
| Q2 Bayer 4×4 | 30.3 | 39.1 | 51.8 | 46.6 | 60.5 | 0.63 / 1.72 | 0.60 | 156 |
| Q7 diffusion d'erreur | 28.5 | 38.2 | 50.4 | 45.9 | 59.4 | 2.48 / 3.24 | **1.92** | 158 |
| **Q6 indices multi-palettes** (phase A) | 32.8 | 30.3 | 31.8 | **42.8** | **50.2** | 0.80 / 0.98 | 0.44 | 117 |
| Q3 fraction 4 bits (REF seule) | 16.7 | 32.8 | 44.0 | 41.9 | 54.2 | 0.08 / 1.17 | 0.22 | 281 |
| Q3 fraction 3 bits | 17.1 | 32.9 | 44.1 | 42.0 | 54.3 | 0.09 / 1.22 | 0.25 | 281 |
| Q3 fraction 2 bits | 17.9 | 33.1 | 44.5 | 42.1 | 54.6 | 0.18 / 1.36 | 0.41 | 243 |
| Q3m fraction multi-palettes | 27.5 | 25.8 | 25.7 | 39.9 | 47.5 | 0.61 / 0.69 | 0.32 | 272 |
| Q5 + re-classement HD | 24.8 | 24.7 | 24.2 | 40.1 | 47.7 | 0.57 / 0.66 | 0.29 | 274 |
| **Q8 fraction multi-palettes + frontières** (phase B) | 23.9 | 24.3 | 23.6 | **37.7** | **45.4** | 0.51 / 0.58 | 0.27 | 272* |

x2 Q8 : REF 22.0, B 22.8, C 21.9, D 36.0, E 42.6, scintillement 0,20 %, 96 Ko (Q0 x2 : 48 Ko).
\* taille = plan classe + plan t8 (3 bits, delta horizontal) ; **plan frontière non compté** :
21 % (x4) à 32 % (x2) des pixels opaques sont des pixels frontière ; erreur sur ces pixels sans/avec
mélange : x4 REF 36→19, D 65→54, E 67→56.

Lecture :
- l'erreur résiduelle sur palettes inédites (~0,04) est dominée par la **non-équivariance du modèle** :
  ReboutCX ne produit pas le même ombrage selon les couleurs d'entrée. Aucun encodage ne descend sous ce
  plancher ; l'ajustement multi-palettes vise le consensus, pas une palette unique ;
- 2-3 bits de fraction suffisent (4 bits n'apporte presque rien) ;
- `figures/idle_temporal_B_x4.gif` : Q0 / Bayer / diffusion / Q8 en mouvement (idle, palette B).

### 3.3 À faire (ordre suggéré ; cocher selon besoin)

| Id | But | Méthode | Critère de décision |
|---|---|---|---|
| E4 | Généraliser E3 | 9 directions (miroirs inclus), cycles G1-G19/A1-A9/CA/SA/SS/SX, 4 armures, tous calques | écarts Q0→Q8 du même signe sur ≥ 90 % des cycles |
| E5 | Choix des K palettes | K=3/4/6 ; plans « carré latin » (chaque gamme reçoit des teintes distinctes par palette, gammes voisines jamais proches) ; 20 palettes de validation tirées de `RANGES12` + `RANDCOLR` + défauts classe/race | ΔE validation vs coût GPU |
| E6 | Stockage réel | codec XPRESS du DLL sur plans (indice, t8 delta, frontière), budget 0x6110 complet | taille ≤ 2,5× l'actuel x4 (310 Mo) ou x2 |
| E7 | Alpha doux | alpha = ReboutCX sur masque blanc/noir (ou xBR4 + gaussienne σ 0,5-0,8 px x4) ; composite « over » ; ombre indice 1 × alpha | pas de halo, sélection/occlusion correctes (E9) |
| E8 | Zoom réel | relever min/max du zoom BG2EE à 2560×1440 (capture d'un sprite de hauteur connue ou lecture `CInfinity` via EEex) | fixe l'intérêt x4 et le filtrage |
| E9 | Prototype DLL V6 | lecteur V6 + LUT étendue + mélange frontière + mip ; test unitaire hôte : reconstruction bit-exacte vs encodeur Python | 60 fps, p95 frame ≤ actuel + 5 % |
| E10 | Robustesse palettes extrêmes | 256 lignes × gamme isolée (clair saturé, noir, gris) sur 20 frames | aucune inversion de luminance, aucun liseré de couleur étrangère |

---

## 4. Comparaison x2/x4 xBR vs x2/x4 ReboutCX

| Critère | xBR x2 | xBR x4 | ReboutCX x2 | ReboutCX x4 |
|---|---|---|---|---|
| Nature | contours reconstruits, aplats sources | idem, contours plus fins | ombrage/volumes réinventés (modèle x4 → BOX x2) | idem, pleine résolution modèle |
| Couleurs possibles | exactement celles du pixel source | idem | classes du guide xBR ; Q0 limité aux indices de la frame | idem |
| Distance au modèle (REF, ΔE×1000) | 38.9 | 40.3 | 26.4 (Q0) → 22.0 (Q8) | 26.8 (Q0) → 23.9 (Q8) |
| Scintillement moyen (idle) | 0.54 % | 0.51 % | 0.54 % (Q0) → 0.20 % (Q8) | 0.54 % → 0.27 % |
| Taille échantillon (zlib) | 45 Ko | 91 Ko | 48 Ko (Q0) / 96 Ko (Q8) | 120 Ko (Q0) / 272 Ko (Q8) |
| 0x6110 complet (registre compressé) | ~196 Mo (x2 actuel) | — | 196 Mo | 310 Mo (test x4 du 2026-09-26, +58 %) |
| Coût production | CPU seul, déterministe | CPU | GPU ~1 000 img/s (lots de 86) | idem + quantification 4× plus de pixels |
| Minification `NEAREST` (MAE vs filtre d'aire, zoom 1,3 / 2,0) | 3.7 / **0.0** | 3.6 / 2.0 | 3.5 / **0.0** | 3.3 / 2.1 (Q8 : 2.7 / 1.8) |
| Verdict | base canonique, repli | peu d'intérêt | **défaut installé** | **maître de production** ; installé seulement avec filtrage de minification ou zoom ≥ 3 |

Figures : `figures/sheet_{idle_s0,walk_s3}_{REF,B,D_heldout,E_armorblue_heldout}.png`
(10 variantes + vérité modèle), `figures/crop_*.png` (torse agrandi), `figures/display_z*.png`
(gauche `NEAREST`, droite filtre d'aire). Observation visuelle : Q0 sous palette B montre des **liserés
clairs** aux frontières de classes (mélanges 88-255 devenus clairs) ; Q6 les atténue, Q8 les supprime
presque.

Test utilisateur existant : x4 ReboutCX 0x6110 installé puis restauré le 2026-09-26, 59-60 fps,
« x4 légèrement meilleur que x2 » (`docs/measurements/reboutcx-x4-0x6110-visual-test-20260926-v1/result.json`).
Cohérent avec D8 : au zoom utilisé, x4 est minifié.

---

## 5. Méthode recommandée — **RCX-FRAC-MP**

### 5.1 Pipeline offline (par calque, par frame, jamais aplati)

1. **Sources** : BAM canoniques déjà matérialisés (`sprite/families/playable-characters/6110-human-female-fighter/*/source/`),
   frames nulles `1×1/indice 2` court-circuitées (prédicat exact existant `reboutcx_batch.is_null_frame`).
2. **Guide** : xBR4 (et xBR2 pour x2) sur RGBA auteur, provenance d'indice si RGB dupliqués
   (`xbr_provenance_indices`) → transparence, ombre, classe par pixel.
3. **Inférence multi-palettes** : K=4 palettes (REF + 3 carrés latins, §3.3 E5), source rendue par
   `character_chmb1_palette_rgb`, remplissage RGB sous transparence par plus proche opaque, ReboutCX
   fp16 x4. Cache P13 : clé = SHA frame **+ palette** (sinon collision).
4. **Encodage par pixel opaque non spécial** (OKLab, vecteur 3K) :
   - classe c = classe du guide ;
   - t ∈ [0, n−1] = projection sur la polyligne des nuances de c concaténée sur K palettes ; quantifier 1/8 ;
   - si un voisin 3×3 a une classe c2 ≠ c : t2 = projection sur c2, poids w = moindres carrés entre les
     deux points, quantifié 1/8 ; garder si w < 1 ;
   - ombre (1), réservés (2,3), transparent (0) : copiés du guide.
5. **Résolutions** : maître x4 ; x2 = BOX des sorties modèle puis ré-encodage à x2 (ne pas décimer l'encodage x4).
6. **Contrôles automatiques** : classes inchangées vs guide ; transparence exacte ; reconstruction
   bit-exacte Python ↔ DLL ; ΔE sur palettes de validation ; scintillement idle ; taille.

### 5.2 Format registre V6 (proposition, à valider E6/E9)

```text
frame V6 (paresseuse, XPRESS comme V5) :
  plan I : u8   indice de base (nuance plancher)
  plan F : u3   fraction vers successeur(I), 0..7   (stockage : t8 = 8·t, delta horizontal par classe)
  plan S : option pixel frontière : (I2 u8, F2 u3, W u3)  W = poids du primaire en 1/8
table successeur (profil character-bg2ee-2.7.3.0, fixe) :
  gamme : i → i+1 sauf dernière nuance ; paire : idem dans ses 8 ; 0..3 → soi-même
representatives : marquer présents I, successeur(I), I2, successeur(I2)
```

### 5.3 Runtime DLL IEE (modifs localisées dans `creature_sprite_x2.cpp`)

```text
à chaque snapshot Realize de calque (déjà capturé) :
  EXT[i*8+f] = arrondi(lerp_sRGB(P[i], P[succ[i]], f/8)), alpha = alpha(P[i])      # 2 048 entrées, une fois par empreinte
composition (upload_frame_locked / composite) :
  px = EXT[I*8+F] ; si S : px = lerp(EXT[I2*8+F2], px, W/8)
  composition des calques : écrasement actuel ; « over » seulement si E7 retient l'alpha doux
empreinte palette : couvrir successeurs et I2 (cache texture correct)
minification : si texels/px écran > 1 → mipmaps sur RGB prémultiplié (ou RGB étendu sous alpha 0),
  MIN = LINEAR_MIPMAP_LINEAR, MAG = NEAREST (aspect pixel conservé au zoom avant)
```

- Les codes de mélange V4 existants valent 1/8, 1/4, 1/2, 3/4, 7/8 : étendre à k/8 (ajout 3/8, 5/8) et
  accepter une source (indice, fraction).
- Tous les effets moteur (teinte, lueur pulsée op 8/9, gris pause, pétrification) arrivent déjà dans `P`
  → hérités sans code spécifique. Une palette pulsée change d'empreinte à chaque frame : coût = LUT +
  composition CPU (comme aujourd'hui).
- Coordonner avec le chantier shaders D4+ (`sprite/catmull-rom/`) : même texture composite.

### 5.4 Repli immédiat sans DLL — **RCX-IDX-MP**

Quantifieur v2 versionné (nouvel id, ancien intact) : classe du guide, candidats = **toute la classe**,
indice = argmin de la somme des ΔE OKLab sur K palettes, sans dithering. Adapter l'écrivain
de registre : `representatives` marqués pour les indices absents de la frame x1 (le DLL ne vérifie que
leur présence, [code] `creature_sprite_x2.cpp` l.1264/2158). Relâcher l'invariant
`unique(out) ⊆ used` en `⊆ classe`.

### 5.5 Paramètres par défaut et raisons

| Paramètre | Valeur | Raison |
|---|---|---|
| Fraction | 3 bits | 2 bits = +5 % d'erreur, 4 bits = +0 % utile |
| Poids frontière | 1/8 | aligné sur les codes V4 |
| K | 4 | E3 n'a testé que K=3 (gain net) ; +1 pour les défauts classe/race réels (30,91,93,12,23,93,2) ; à confirmer par E5 |
| Espace d'ajustement | OKLab | écart perceptuel ; rendu runtime en lerp sRGB 8 bits (déterministe) |
| Dithering | aucun | D6 |
| Échelle installée | x2 par défaut ; x4 si E8+S12 validés | D8 |

---

## 6. Inventaire 0x6110 à traiter

Totaux [code index + mesuré] : **65 composants, 656 BAM, 178 360 frames** ; x4 visuel existant
(local, hors Git) : `family-runs/reboutcx-x4-visual-catalog-v2/`.

### 6.1 Corps (4 composants, 92 BAM)

| Armure | Préfixe | BAM | Frames (dont non nulles) | Partagé avec |
|---|---|---|---|---|
| 1 sans armure | `CHFB1` | 23 | 10 323 (2 772) | 0x5010, 0x5110, 0x6010, 0x6015, 0x6115 |
| 2 cuir | `CHFB2` | 23 | 10 324 (3 520) | idem |
| 3 mailles | `CHFB3` | 23 | 10 324 (3 520) | idem |
| 4 plates | `CHFF4` | 23 | 10 323 (3 519) | 0x5110, 0x6115 |

Suffixes : `A1-A9, CA, G1, G11-G19, SA, SS, SX`. Découpage `split_bams` [mesuré CHFF4] : G11 = cycles 0-8
(10 f), G1 = 9-17 (12 f), G12 = 18-26 (56 f), G13 = 27-35 (12 f), G14/G15/G16 = 36-62, G17 = 63-71
(38 f), G18 = 72-80 (46 f), G19 = 81-98 (15 f) ; cases vides = frames nulles.

### 6.2 Équipements (préfixe `WQN`, partagé par 13 animations : 0x5010, 0x5110, 0x5210, 0x5310, 0x6010, 0x6015, 0x6110, 0x6115, 0x6210, 0x6215, 0x6310, 0x6315, 0x6510)

| Calque | Codes (BAM × frames) |
|---|---|
| Casques 18 | `H0 H1 H2 H5 J0 J1 J2 J3 J4 J5 J6 J7 J8 J9 JA JB JC` (14 BAM, 2 709 f chacun) ; `ZW` ailes (14, 572) ; `YW` sans BAM (bloqué) |
| Boucliers 12 | `C0-C7`, `D1-D4` (5 BAM `A1 A3 A5 G1 SS`, 1 386 f) |
| Armes 1 main 16 | `AX CL DD F0 F1 F3 FL M2 MC MS S0 S1 S3 SC SS WH` (11 BAM dont main gauche `OA7-9`, `OG1` ; 2 907 f) |
| Armes 1 main longues 2 | `F2`, `FS` (11 BAM, 5 377-5 378 f) |
| Armes 2 mains 8 | `GS HB Q2 Q3 Q4 QS S2 SP` (4 BAM `A2 A4 A6 G1`, 1 242 f) |
| Tir 4 | `BS BW CB` (2 BAM, 972 f), `SL` (2 BAM, 981 f) |
| Spécial 1 | `H6` (formes animales `BEARSPIR`… ; 14 BAM, 2 709 f) |

Objets par code : `sprite/index/sprite_families.csv` (colonne `item_resrefs`) et `sprite_items.csv`.

### 6.3 Hors runtime actuel (lot séparé)

Poupée d'inventaire `CHFF1INV-CHFF4INV` (`resref_paperdoll=CHFF`) et `WPM**INV` (armes/boucliers/casques) :
même logique de gammes, autre chemin de rendu (UI), non couvert par le hook Character.

---

## 7. Ordre de développement

| Phase | Contenu | Livrable | Dépend de |
|---|---|---|---|
| A0 | Captures de référence en jeu de l'état installé (xBR x2 / RCX P13) sur le personnage de test (§8) | planche avant/après | — |
| A1 | Quantifieur v2 **RCX-IDX-MP** + écrivain `representatives` étendu | nouveau job versionné CHFF4 | — |
| A2 | CHFF4 complet + `WQNJ6`, `WQND3`, `WQNS1` en v2 ; catalogue dérivé ; installation transactionnelle ; QA | décision QA | A1 |
| B1 | Spécification V6 + encodeur Python + test de reconstruction | `palette_frac` v1 | E4-E6 |
| B2 | DLL : lecteur V6, LUT étendue, frontières k/8, empreinte ; tests hôte | build DLL candidate | B1 |
| B3 | DLL : minification filtrée (S12) ; mesure E8 | option INI | B2 |
| B4 | (option) alpha doux + ombre douce (E7) | option INI | B2 |
| C1 | Inférence K=4 avec cache P13 sur les 65 composants | runs scellés | B1 |
| C2 | Encodage x4 maître + x2 dérivé ; catalogues | catalogues V6 | C1, B2 |
| D | QA en jeu (§8), décisions immuables `sprite/index/qa-decisions/` | acceptations | C2 |
| E | Généralisation (§9) | — | D |

Ordre interne des composants : `CHFF4` → `CHFB1-3` → armes les plus vues (`S1 S0 SS AX WH MC CL S2 BW`) →
boucliers → casques (mélanges lourds, gain frontière maximal) → reste.

---

## 8. Plan de tests en jeu

Préalables : jeu et InfinityLoader fermés pour installer/restaurer (installateurs transactionnels du dépôt) ;
`CreatureSpriteFilter = Nearest` pour la QA ; console Lua active (`Enable-BG2Debug.ps1`, `Baldur.lua`
effacé à la fermeture).

Mise en place :

```text
C:MoveToArea("AR0700")        # Promenade de Waukeen, jour, sol clair
C:MoveToArea("AR0602")        # zone sombre (contraste nuances sombres) — ou toute zone nuit
C:CreateItem("PLAT01")  C:CreateItem("CHAN01")  C:CreateItem("LEAT01")
C:CreateItem("HELM01")  C:CreateItem("HELM03")  C:CreateItem("ISHLD03")  C:CreateItem("SHLD05")
C:CreateItem("BDSW1H06") C:CreateItem("SW1H01") C:CreateItem("SW2H01") C:CreateItem("BOW01")
```

Couleurs imposées par calque (EEex, personnage sélectionné ; `dwFlags` = 0xPR, P : 0 corps, 1 arme,
2 bouclier, 3 casque ; R : 0 métal … 6 cheveux) :

```lua
EEex_GameObject_ApplyEffect(EEex_Sprite_GetSelected(), {["effectID"]=7, ["effectAmount"]=68, ["dwFlags"]=0x05, ["durationType"]=0, ["duration"]=600, ["sourceID"]=EEex_Sprite_GetSelectedID()})
```

| Bloc | Cas | Attendu |
|---|---|---|
| T1 recoloration | 4 couleurs joueur via le menu couleurs ; palettes REF/B/C/D/E ; lignes extrêmes (0 blanc-noir, 67 or saturé, 68 bleu, 208+ aléatoires) | aucune zone qui ne suit pas sa gamme, aucun liseré de couleur étrangère aux frontières |
| T2 calques | 4 armures × {sans/avec casque} × {bouclier, 2 mains, arc, deux armes} | composition complète (log : `layer n/n`), pas de retour natif hors premières frames de chargement |
| T3 animations | 9 directions (5 miroirs), marche, idle long G12, attaques A1-A9, sort CA, tir SA/SS/SX, dégâts, mort, sommeil | pas de saut de géométrie, pas de frame native isolée (log observé le 2026-09-26 : `CHFF4G12 sequence=20 slot=15` non résolue → à revérifier) |
| T4 effets | `BDSW1H06` (op 9 pulsée), pause grise, invisibilité (op 66), flou (op 65), pétrification, lumière de nuit | effets identiques au natif, pas de chute de fps |
| T5 temporel | idle 30 s immobile, marche lente horizontale, zoom avant/arrière | aucun grouillement dans les aplats ; comparer Q0/Q6/Q8 en A/B |
| T6 affichage | zoom min / 1 / max ; x2 vs x4 ; `Nearest` vs minification filtrée | x4 retenu seulement si net gain perçu au zoom joué |
| T7 intégration | sélection (contour `fpSELECT`), survol, occlusion par décor (pont d'occlusion), foule | contours et occlusion corrects, pas de halo |
| T8 perf | combat 6 personnages + effets | 59-60 fps, p95 ≤ actuel + 5 % |

Traçabilité : captures PNG par cas, log `InfinityEngine-Enhancer.log` (lignes `Composing creature sprite …`),
décision explicite de l'utilisateur seulement ; jamais déduire une validation d'une installation.

---

## 9. Automatisation et généralisation

| Élément | Automatisable | Détail |
|---|---|---|
| Profil de classes | oui | un profil par type moteur ; `character-bg2ee-2.7.3.0` couvre toutes les animations Character `false_color=1` ; auditer tout autre type (Monster false-color ≠ Character) |
| Sélection des composants | oui | `sprite/index/*.csv` ; dédoublonnage BAM (CHFB1-3 servent 6 animations, `WQN*` 13) |
| Plan de palettes K | oui | générateur carré latin + défauts `CLASCOLR`/`RACECOLR` par famille ; validation tirée de `RANGES12`/`RANDCOLR` |
| Inférence | oui | cache P13 étendu à la clé palette ; shards par cohortes de BAM ; VRAM ≥ 0,45 pour gros canevas |
| Encodage Q6/Q8 | oui | vectorisé NumPy ; 88 frames × 4 calques × 12 méthodes ≈ 25 s CPU ici |
| Contrôles | oui | invariants de classe/transparence, reconstruction bit-exacte, ΔE validation, scintillement idle, taille |
| Planches QA | oui | planches par palette + GIF temporels (repris de `e3_experiment.py`) |
| Ordre de QA | semi | priorité = fréquence en jeu × surface ; QA humaine obligatoire pour l'acceptation |
| Monstres palettés | partiel | même principe si palette par gammes ; sinon Q6 seul |

Scripts à créer (noms proposés, absents du dépôt) : `reboutcx_multipal.py` (inférence K palettes),
`palette_frac_encode.py` (Q6/Q8 + V6), `palette_eval.py` (métriques E3 généralisées), écrivain de
registre V6 dans la chaîne catalogue existante.

---

## Annexe — limites de ce travail

- Échantillon : 1 direction (sud), 2 cycles, 4 calques, 88 frames ; E4 nécessaire avant décision de production.
- Vérités = sorties ReboutCX ; aucune métrique perceptuelle humaine ; aucun rendu en jeu.
- `durationType`/`duration` EEex de l'exemple : à confirmer sur la version EEex installée.
- Héritage des couleurs corps → équipements sans opcode 7 : comportement GemRB/IESDP, non vérifié en jeu (T1).
- RVA moteur, formule des mélanges et rôle des indices 1-3 : repris de l'audit P6.1, non redésassemblés ici.
- Zoom min/max BG2EE non mesuré (E8) ; les conclusions x4 dépendent de ce chiffre.
