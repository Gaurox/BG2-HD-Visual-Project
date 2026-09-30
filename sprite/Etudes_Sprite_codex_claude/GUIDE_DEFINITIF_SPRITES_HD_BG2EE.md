# Guide définitif — Sprites HD jouables de BG2EE

## Palettes dynamiques, xBR / ReboutCX, x2 / x4 — cas de référence `0x6110` (femme humaine guerrière), généralisable

| Champ | Valeur |
|---|---|
| Version | 2026-09-30 — relecture finale et consolidation |
| Rédaction | Claude Code (Claude Opus 5.5) |
| Entrées relues intégralement | étude Claude (guide v1, présentation + erratum E3b, revue croisée E5) ; étude Codex (guide, notes moteur/inventaire/upscale, comparaison critique, recalcul temporel, arrondi 3 bits) ; synthèse Codex `GUIDE_ULTIME_SPRITES_HD_BG2EE.md` (29/09 21:16) |
| Vérifications refaites dans cette passe | binaire moteur, `MPALETTE`/`RANGES12`, routine des mélanges, code runtime IEE (`file:line`), quantifieur et cache de production, décisions QA du dépôt, mesure x4 du 26/09, run P13 `0x6110`, tables E3b/E5, recalcul temporel, arrondi 3 bits, inventaire CSV, lignes constantes 74–78, égalisation des rampes, recouvrement des palettes de validation |
| Autorité | Ce guide fait référence pour le développement. Les études sources restent intactes et historiques ; leurs erreurs sont listées au §16. |
| Compagnon visuel | [`PRESENTATION_ETUDE_SPRITES_HD_0x6110.html`](PRESENTATION_ETUDE_SPRITES_HD_0x6110.html) (hors ligne, explorateur de palette, comparateur, chiffres) |
| Ce que ce guide n'est pas | Ni validation en jeu, ni état d'installation, ni intégration release. Aucun fichier du jeu, payload, catalogue, DLL ou manifeste n'a été modifié. |

---

## 0. Accès rapide

| Besoin | Section |
|---|---|
| La décision et la recette retenues | §1 |
| Ce que fait réellement le moteur (palette, mélanges, couches) | §3 |
| Ce que le runtime IEE du dépôt sait déjà faire, avec lignes de code | §4 |
| Quoi produire pour `0x6110` (inventaire, périmètre, pièges) | §5 |
| Chaîne image xBR / ReboutCX | §6 |
| Tous les chiffres consolidés et comment les lire | §7 |
| Spécification du format cible (registre V6) | §8 |
| Algorithme de l'encodeur | §9 |
| x2, x4, filtrage | §10 |
| Plan de développement et critères de passage | §11 |
| QA hors ligne et en jeu | §12 |
| Étendre à tous les sprites de BG2 | §13 |
| Pistes rejetées | §14 |
| Questions ouvertes | §15 |
| Registre des erreurs corrigées (toutes études) | §16 |
| Sources, scripts, reproduction | §17 |

---

## 1. Décision en une page

### 1.1 Architecture

Le sprite HD reste une **description sémantique recolorable**, décodée au runtime avec la palette que BG2EE a réellement calculée pour chaque couche. Jamais une image RGBA peinte pour une palette unique.

```text
BAM V1 P8 (indices, cycles, lookup, centres)                       ── vérité topologique
  ├─ xBR xN (même échelle) ─────────► alpha, ombre, classe par pixel ── vérité sémantique
  └─ ReboutCX x4 RGB sous K palettes ► cibles T_1..T_K              ── vérité de modelé (jamais de sémantique)
                    │
        encodeur multi-palettes, optimisé contre le décodeur exact
                    │
   registre V6 : plan I (u8, = V5) + plan F (fraction 0..7 vers la nuance suivante)
                 + masque de dépendances palette + plan frontière optionnel
                    │
   DLL IEE (CPU, compositeur existant) : P[256] capturée par couche après Realize
     → LUT 2 048 entrées → pixels → composition native → texture (géométrie x1)
```

### 1.2 Recette retenue

| Paramètre | Valeur | Niveau de preuve |
|---|---|---|
| Ressource palette moteur | `MPALETTE.BMP` (et non `RANGES12.BMP`) | CONFIRMÉ (binaire, xrefs) |
| Contrat de couleur | 7 gammes × 12 nuances + 21 paires × 8 ; une palette par couche | CONFIRMÉ |
| Source du modelé | ReboutCX natif x4 (RRDBNet 64nf/23nb, SHA-256 `c36a14dd…`) | MESURÉ ; licence NON RÉSOLUE |
| Source de la sémantique (classe, alpha, ombre) | guide xBR à la même échelle + provenance d'indice | CONFIRMÉ (pipeline actuel) |
| Encodage cible | **Q3m** : indice de base + fraction 3 bits vers la nuance suivante, ajusté sur K palettes | MESURÉ (hors jeu) |
| Frontières (Q8) | option, seulement après ablation contre Q3m, sous règles de paires autorisées | MESURÉ (prototype incomplet) |
| Espace d'interpolation au runtime | octets sRGB, arrondi entier défini (§8.4) | MESURÉ : sRGB ≈ linéaire (37,8 vs 38,1) |
| Espace d'optimisation | OKLab, contre les couleurs exactes du décodeur | CANDIDAT |
| Palettes d'ajustement | K = 3 minimum (REF/B/C mesurés), cible K = 4 avec les défauts réels ; K = 3/4/6 à trancher | MESURÉ pour K = 3 seulement |
| Tramage | aucun | MESURÉ sur le corpus |
| Échelle livrée | x2 par défaut ; x4 option qualité après étude de minification | OBSERVÉ EN JEU (x4 « légèrement meilleur ») + CANDIDAT |
| Reconstruction | CPU dans `creature_sprite_x2.cpp` ; shader seulement si profilage | CANDIDAT |
| Composition | ordre natif, écrasement des pixels non transparents ; alpha doux reporté | CONFIRMÉ (existant) |
| Palette globale | ne jamais modifier `MPALETTE` pour ce chantier | DÉCISION |

### 1.3 Ordre de développement (détail §11)

```text
P0 oracles + banc d'évaluation corrigé (signe temporel, masques séparés, ≥ 10 palettes disjointes)
P1 inférence multi-palettes + encodeur Q6/Q3m hors ligne ; K = 3/4/6
P2 DLL : lecteur V6 (masque de dépendances, plan F, LUT) + golden tests Python = C++
P3 verticale en jeu CHFF4 + un casque, un bouclier, une épée : Q0 vs Q3m
P4 décision x2/x4 + filtre de minification au zoom réel
P5 ablation Q3m ↔ Q8 contraint ; n'adopter Q8 que si le gain propre le justifie
P6 0x6110 complet (628 BAM monde) → P7 paperdolls → P8 autres animations Character
```

### 1.4 Ce qui n'est pas acquis

- Aucune de ces méthodes n'a été vue en jeu sous forme fractionnaire : les gains sont hors ligne, mesurés contre une cible ReboutCX, pas contre une préférence humaine.
- Les palettes « tenues à l'écart » partagent 1 à 6 canaux sur 7 avec l'entraînement (§7.2). Seule D est quasi indépendante ; les gains s'y maintiennent, mais sur une seule palette.
- La plage de zoom réelle de BG2EE à 2560×1440 n'a jamais été mesurée.
- Le coût réel du format (XPRESS, plan frontière, masque) n'est pas mesuré ; seuls des ordres de grandeur zlib partiels existent.
- La stabilité temporelle n'est mesurée que sur pixels immobiles alignés par ancre, pas sur surfaces en mouvement.
- ReboutCX : provenance d'entraînement et licence inconnues.

---

## 2. Échelle de preuve

| Étiquette | Sens |
|---|---|
| **CONFIRMÉ** | Lu dans le binaire, les ressources ou le code du dépôt ; reproductible sans appréciation visuelle. |
| **MESURÉ** | Chiffré hors jeu sur le corpus décrit ; ne vaut que pour ce corpus et ce protocole. |
| **OBSERVÉ EN JEU** | Constat utilisateur daté, sur une scène précise ; n'implique ni QA globale ni release. |
| **CANDIDAT** | Choix de conception à implémenter puis valider. |
| **NON RÉSOLU** | Preuve manquante ; aucune déduction de production autorisée. |

---

## 3. Contrat moteur BG2EE 2.7.3.0

### 3.1 Cible binaire — CONFIRMÉ (revérifié le 2026-09-30)

```text
Fichier       G:/SteamLibrary/steamapps/common/Baldur's Gate II Enhanced Edition/BaldurReal.exe
Version       2.7.3.0 (Baldur.exe = loader, ne pas confondre)
SHA-256       b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57
ImageBase     0x140000000
Chaînes       "MPALETTE" ×1 (offset fichier 0x59E158, RVA 0x59F758) ; "RANGES12" ×0 ; "CLOWNCLR" ×0
RVA           SetRange 0x4221C0 · mélanges 0x421F7B–0x42201E · xref MPALETTE 0x26BA53
```

Offsets valables pour ce binaire seulement. Tout autre build : retrouver les fonctions et revérifier les octets.

### 3.2 Table des indices (chemin BAM V1 false-color Character)

| Indices | Rôle | Canal CRE |
|---:|---|---|
| 0 | transparent (le runtime force `P[0] = 0`) | — |
| 1 | ombre, noir à alpha partiel | — |
| 2, 3 | noirs réservés ; 2 = marqueur des frames 1×1 | — |
| 4–15 | métal | 0 |
| 16–27 | mineure | 1 |
| 28–39 | majeure | 2 |
| 40–51 | peau | 3 |
| 52–63 | cuir | 4 |
| 64–75 | armure | 5 |
| 76–87 | cheveux | 6 |
| 88–255 | 21 paires × 8 mélanges | 2 canaux |

Nuance 0 = la plus claire. La limite « 12 » est celle d'une rampe false-color, pas du format BAM (256 indices).

### 3.3 Réalisation — CONFIRMÉ par lecture des instructions

```text
SetRange(r, ligne) : P[4+12r .. 15+12r] ← MPALETTE[ligne][0..11]
Realize            : effets de palette (teinte, lumière, gris, pétrification, lueur…) sur les 84 nuances,
                     PUIS calcul des 21 paires à partir des nuances déjà réalisées
paire (a,b), rang k lexicographique (0,1),(0,2)…(0,6),(1,2)…(5,6), nuance j ∈ 0..7 :
  i       = 88 + 8k + j
  P[i].c  = (P[4+12a+j+2].c + P[4+12b+j+2].c) >> 1        c ∈ {R,G,B}, entiers 8 bits
```

Lecture de la boucle `0x421F7B` : source `palette+0x18` (entrée 6 = canal 0 nuance 2), partenaire `+0x30` (12 entrées), 8 itérations, `add` puis `shr 1` sur trois octets, destination `palette+0x160` (entrée 88). Chemin court `0x421EE0` : recopie de 168 sous-couleurs en cache quand l'état le permet.

Conséquences :

- 88–255 ne sont pas des couleurs libres : chaque entrée suit deux choix de couleur du joueur.
- Les mélanges utilisent les nuances 2..9 seulement, poids 50/50, en octets sRGB (ni linéaire, ni OKLab).
- Une palette `P[256]` capturée après `Realize` contient déjà les effets de palette **et** les mélanges recalculés.

### 3.4 Une palette par couche

| Couche (cellule Character) | Locations opcode 7 | Encodage `param2` |
|---|---|---|
| Corps | 0–6 | `0x0R` |
| Arme | 16–22 | `0x1R` |
| Bouclier / main gauche | 32–38 | `0x2R` |
| Casque | 48–54 | `0x3R` |

`R` = canal 0..6. Le runtime du dépôt capture la palette de **chaque cellule** (corps, arme, main gauche, casque) au moment de son `Realize` (`hooks.cpp:2855-2858, 2934-3009`). Il décode donc correctement une arme en main gauche quelle que soit la location qui a alimenté sa palette.

NON RÉSOLU : la location qui recolore une **arme** tenue en main gauche (`0x1R` ou `0x2R`). Sans effet sur l'encodage ; à mesurer en jeu (§12.2) uniquement pour choisir les palettes d'entraînement de la main gauche.

### 3.5 Ressources couleur

| Ressource | Rôle vérifié | Règle |
|---|---|---|
| `MPALETTE.BMP` | 256 lignes × 12 nuances, lue par `SetRange` | seule ressource moteur ; changement = global |
| `RANGES12.BMP` | aperçu Near Infinity ; octets identiques à `MPALETTE` (SHA-256 `7a9a654d…`) | ne jamais modifier seule |
| `MPAL256.BMP` | gradients longs (PLT, autres chemins) | ne transforme pas 12 nuances en 256 |
| `RANDCOLR.2DA` | résolution des identifiants ≥ 200 (tirage) | ne pas traiter 200+ comme lignes littérales |
| `RACECOLR.2DA` / `CLASCOLR.2DA` | défauts race / classe (humain : cheveux 2, peau 12 ; guerrier : métal 30, mineure 91, majeure 93, cuir 23, armure 93) | source des palettes « réelles » |
| `CLOWNCLR.IDS` | noms d'identifiants | ni palette RGB, ni 2DA |
| CRE / ITM / EFF | choix et remplacements (opcodes 7/8/9/50/51/52) | le joueur choisit cheveux, peau, majeure, mineure ; métal/cuir/armure viennent classe + objets |

### 3.6 Couleurs fixes

- **Corps : aucune.** Tous les indices 4–255 suivent des choix de couleur.
- **Équipement : possible, par exception.** Lignes `MPALETTE` constantes (revérifié) : 74 blanc, 75 noir, 76 rouge, 77 vert, 78 bleu ; aucune autre ligne constante. Un canal réellement inutilisé par **toutes** les frames de la famille peut être fixé par opcode 7 dans l'ITM. Coûts : ITM partagés, conflits de mods, preuve d'inutilisation par famille. Statut CANDIDAT optionnel, hors premier prototype.
- Ces lignes « fixes » restent soumises aux effets de palette (lumière, teinte) : c'est souhaitable.

### 3.7 Ce que la capture `P[256]` couvre ou non

| Couvert | Non couvert, à tester séparément |
|---|---|
| choix CRE/ITM, `RANDCOLR` résolu, effets appliqués dans la palette, mélanges | modulation/teinte post-palette (`fpDraw`, `uColorTone`), alpha/blending, invisibilité, flou, sélection (`fpSELECT`), occlusion, ordre des couches, cercle de sélection |

### 3.8 Faux oracles

| Outil | Écart | Usage |
|---|---|---|
| Near Infinity `50021b83` | mélanges échantillonnés sur nuances 0,1,3,4,6,7,9,10 | inventaire, cycles, centres ; jamais étalon pixel |
| GemRB `5552ade1` | copie de sous-gammes, pas les 21 moyennes | architecture ; jamais étalon BG2EE |

---

## 4. Runtime IEE du dépôt : acquis vérifiés

Racine : `engine/InfinityEngine-Enhancer/source-patchee/src/iee/`.

| Fait | Preuve |
|---|---|
| Géométrie écran x1, texture physique x2 ou x4 | `creature_sprite_x2.cpp:865`, doc `creature-sprite-0x1000.md` |
| Registres V3 (xN indexé), V4 (recettes AA), V5 (XPRESS_HUFF par frame) | `creature_sprite_x2.cpp:76-78`, `1003`, `1255` |
| V4 refusé si `scale != 2` ; ≤ 8 opérations ; 5 poids `7:1 3:1 1:1 1:3 1:7` | `creature_sprite_x2.cpp:2023`, `1396`, `creature_sprite_x2.h:183` |
| Contrôle : chaque indice du payload doit avoir `representatives[i] != 0xFFFF` | `creature_sprite_x2.cpp:1264`, `2158` |
| Empreinte de cache = FNV sur `P[i]` pour les seuls `i` présents dans `representatives` | `creature_sprite_x2.cpp:1326-1344` |
| `representatives` ne sert pas d'offset d'échantillonnage : les 256 couleurs réalisées sont déjà en main | lecture `1446-1488` |
| `P[transparent] = 0` imposé après capture | `creature_sprite_x2.cpp:1368-1374` |
| Composition : tout pixel non nul écrase le précédent | `creature_sprite_x2.h:172` |
| Cellules Character : corps + arme + main gauche + casque, palette capturée par cellule | `hooks.cpp:2855-2858`, `2934-3009` |
| Routage : ID d'animation → memberships → composants ; un composant peut servir plusieurs animations | `creature-sprite-0x1000.md:178-186` |
| Échantillonnage : MIN = MAG, `GL_TEXTURE_MAX_LEVEL = 0`, aucun mipmap | `creature_sprite_x2.cpp:1534-1538` |
| Modes de filtre : `Nearest` (défaut, base QA), `Linear` (A/B), `CatmullRom` (shader 4×4 prémultiplié sur sampler NEAREST, texture propriétaire) | `core/config.h:131-133`, `creature_sprite_filter.cpp:61-69` |
| Catmull-Rom local ≠ filtre de réduction | `sprite/catmull-rom/README.md:342` |
| INI installé au 2026-09-30 : `CreatureSpriteFilter = Nearest` | fichier du jeu |

Chaîne de production ReboutCX actuelle :

| Fait | Preuve |
|---|---|
| Palette de référence unique `REF = (30,47,57,12,39,21,3)` | `pipeline/scripts/reboutcx_quantize.py:18` |
| Classes : 4 spéciales + 7 rampes + 21 paires ; paires sur nuances 2..9 | `reboutcx_quantize.py:23-80` |
| Candidats restreints aux indices présents dans la frame source (Q0) | `reboutcx_quantize.py:171-208` |
| Clé de cache d'inférence = contexte + frame + palette de référence | `reboutcx_cache_p12.py:33-39` |
| Contrôle de provenance nommé `RANGES12` (octets identiques à `MPALETTE`) | `reboutcx_batch.py:120-160` |

État du projet (daté, sans déduction d'installation) :

| Date | Fait | Source |
|---|---|---|
| 2026-09-11 | QA acceptée : ensemble des personnages jouables xBR x2, filtre **CatmullRom** | `sprite/index/qa-decisions/playable-characters/2026-09-11-…catmull-rom-v1.json` |
| 2026-09-14 | ReboutCX x2 `0x6100` : accepté pour Minsc (CHMB3+WQLS2) et Anomen (CHMB3+WQLWH/J6/C3) ; CHMB1+WQLS0 « non inférieur », préférence non tranchée | `…/2026-09-14-accepted-6100-*.json` |
| 2026-09-21 | P13 : `0x6110` ReboutCX x2 (Q0) produit, 65 composants, 178 360 frames, 146 084 logiques, 94 010 inférences (35,6 % de réutilisation) ; aucune décision QA `0x6110` enregistrée | `docs/measurements/reboutcx-p13-0x6110-20260921-v1/` |
| 2026-09-26 | Essai x4 `0x6110` (NEAREST) : registre compressé 195 904 865 → 309 550 625 o (×1,58) ; 59,1–60 FPS, p95 16,8–17,3 ms ; « x4 légèrement meilleur que x2 » ; restauré en x2 | `docs/measurements/reboutcx-x4-0x6110-visual-test-20260926-v1/result.json` |
| site public | installateur prévu : Auto / Full xBR / Full ReboutCX | `bg2-hd-website/fr/sprites.html` |

Conséquence produit : **xBR n'est pas un simple repli**. C'est la voie acceptée en QA à l'échelle des personnages jouables, et un choix d'installation. Le format V6 doit servir les deux (xBR = plan I seul, F = 0).

---

## 5. `0x6110` : anatomie, inventaire, périmètre

### 5.1 Entrée d'animation (`6110.INI`, `data/Patch2.bif`)

```ini
animation_type=6000   false_color=1   split_bams=1   equip_helmet=1   armor_max_code=4
resref=CHFB   resref_armor_base=B   resref_armor_specific=F   resref_paperdoll=CHFF
height_code=WQN   height_code_helmet=WQN   height_code_shield=   (repli WQN)
```

Niveaux : 1 `CHFB1` sans armure · 2 `CHFB2` cuir · 3 `CHFB3` mailles · 4 **`CHFF4`** plates (le préfixe change ; ne pas chercher `CHFB4`). Paperdolls `CHFF1INV`..`CHFF4INV`. Apparence ITM `0x22` : `2A→CHFB2`, `3A→CHFB3`, `4A→CHFF4` ; `2W/3W/4W` = robes, hors guerrière.

### 5.2 Séquences et directions

23 suffixes corps : `A1–A9 CA G1 G11–G19 SA SS SX`.

| Suffixe | Cycles utiles | Action |
|---|---|---|
| A1/A3/A5 · A2/A4/A6 | 0–8 | 1 main · 2 mains (taille, revers, estoc) |
| A7/A9 · A8 | 0–8 | deux armes · lancer/overhead |
| SA/SS/SX | 0–8 | arc / fronde / arbalète |
| CA | 0–71 (4 × 9) | sorts, 4 variantes |
| G11 · G1 · G12 · G13 | 0–8 · 9–17 · 18–26 · 27–35 | marche · garde 1 main · repos · garde 2 mains |
| G14 · G15 · G16 | 36–44 · 45–53 · 54–62 | touché · mort · au sol |
| G17 · G18 · G19 | 63–71 · 72–80 · 81–98 | repos · repos · sommeil/chute/relevé |

- 9 directions stockées (S, SSW, SW, WSW, W, WNW, NW, NNW, N) + **7 miroirs** = 16 orientations.
- Corps scindé (`split_bams`), overlays `WQN` non scindés : leur `G1` regroupe les états. Ne pas appliquer la découpe corps aux équipements.
- Armes 1 main : `G1 A1 A3 A5 A7 A8 A9` + main gauche `OG1 OA7 OA8 OA9` ; 2 mains `G1 A2 A4 A6` ; arc `G1 SA`, fronde `G1 SS`, arbalète `G1 SX`.
- G14/G15 partagent leurs premières poses : garder les deux.

### 5.3 Inventaires réconciliés (revérifiés sur le CSV Codex)

| Ensemble | BAM | Frames (table) | Frames > 1 px |
|---|---:|---:|---:|
| Index du dépôt (monde) | 656 | 178 360 | — |
| Stock vanilla complet (`assets_inventory.csv`) | 774 | 185 335 | 153 422 |
| dont monde | 689 | 185 164 | 153 272 |
| dont paperdolls (4 corps + 81 `WPN`) | 85 | — | — |

```text
774 = 656 index + 85 paperdolls + 33 stock monde (D0 : 5 ; H3/H4 : 28)
656 = 628 utiles + 14 ZW (ailes) + 14 H6 (attaques de créature)
628 = 92 corps + 166 armes + 72 main gauche + 60 boucliers + 238 casques
```

Index du dépôt : 66 familles (4 corps, 19 casques, 12 boucliers, 31 armes), 65 `pipeline_ready` (`YW` sans BAM).

### 5.4 Premier périmètre de production : 628 BAM monde

Exclus : `H6` (59 ITM = attaques de créature, pas des casques) · `ZW`/`WINGS01` (interdit aux humains) · `D0` (aucun ITM) · `H3/H4` (aucun casque ITM) · paperdolls (pipeline UI séparé). Le masque ITM humain/guerrier exprime une compatibilité technique, pas l'obtention en partie (kit, alignement, caractéristiques, quêtes restent à filtrer).

Paperdolls équipement (81) : 30 armes `INV`, 1 H6 `INV`, 18 main gauche `OIN`, 12 boucliers `INV`, 19 casques `INV` (dont H3/H4), `WPNWMOIN` orphelin. Lot normal 77 → total normal 709 (92 + 536 + 4 + 77) ; avec H6 : 724.

### 5.5 Placeholders

Tables `G1/G11..G19` de centaines d'entrées (ex. `CHFB1G11` : 846 entrées, 90 frames > 1 px), majoritairement des frames **1×1 à indice 2**. `A1..A9` : 135 frames dont 126 référencées.

```text
Préserver : frame, lookup, centre, cycle, durée.
Sauter : inférence et calcul HD seulement si le prédicat exact est vrai (reboutcx_batch.is_null_frame).
Ne jamais réindexer ni supprimer une frame « inutilisée ».
```

### 5.6 Partages

- `CHFB1–3` : aussi `0x5010, 0x5110, 0x6010, 0x6015, 0x6115` ; `CHFF4` : aussi `0x5110, 0x6115`.
- `WQN*` : 13 INI (`5010 5110 5210 5310 6010 6015 6110 6115 6210 6215 6310 6315 6510`).
- Le runtime route déjà par **ID d'animation → memberships → composant → resref**. Aucune substitution de BAM natif n'est nécessaire. Pour tester une nouvelle méthode sur `0x6110` seul, publier ses composants avec des memberships limités à `0x6110`. À vérifier au premier catalogue : deux composants de même resref avec memberships disjointes dans un même catalogue.

---

## 6. Chaîne image

### 6.1 Trois vérités séparées

| Vérité | Source | Jamais |
|---|---|---|
| Topologie : cycles, lookup, centres, placeholders | BAM P8 original | recalculée |
| Sémantique : alpha, ombre, classe par pixel | xBR à la même échelle + `xbr_provenance_indices` | déduite du RGB ReboutCX |
| Modelé | ReboutCX x4 RGB sous palettes réalisées | source de classe ou d'alpha |

### 6.2 Étapes par frame et par couche

1. Décoder indices, alpha/ombre, centre, identité de cycle ; filtrer les placeholders.
2. Réaliser K palettes de couche (`character_chmb1_palette_rgb`, §9.2).
3. Remplir le RGB sous alpha nul par le plus proche pixel opaque (évite les halos d'inférence).
4. Inférer ReboutCX x4 (fp16) pour chaque palette ; clé de cache = frame + palette (déjà le cas).
5. Guide xBR4 direct (pas 2 × xBR2) pour x4 ; xBR2 pour x2.
6. Encoder (§9) contre les K cibles ; transférer alpha, ombre et spéciaux depuis le guide.
7. Valider sur les palettes de validation (jamais vues).

### 6.3 Master x4, livraison x2

```text
T_k x4 (float) → réduction BOX → T_k x2 (float) → encodage à x2 avec le guide xBR2
```

Ne jamais réduire des plans I/F déjà quantifiés : la quantification et les frontières se recalculent à l'échelle livrée.

### 6.4 xBR ou ReboutCX par asset

- xBR : déterministe, net, couleurs source exactes, aucun modelé nouveau ; accepté en QA avec Catmull-Rom.
- ReboutCX : modelé plus riche ; dépend de la palette d'inférence ; accepté ponctuellement sur `0x6100`.
- Observation du site : xBR souvent meilleur sur petits sprites, ReboutCX sur grands.
- Le choix Auto / Full xBR / Full ReboutCX reste un choix de catalogue. Le format V6 porte les deux.

---

## 7. Résultats consolidés

Métrique couleur : ΔE OKLab moyen ×1000 sur pixels opaques, par rapport à la sortie ReboutCX recalculée sous la même palette. Plus bas = mieux. **C'est une fidélité à une cible générée, pas une qualité perçue.**

### 7.1 Corpus

| Essai | Contenu | Auteur |
|---|---|---|
| E3 (v1, remplacé) | 88 frames ; repos dilué (4 poses distinctes sur 12) | Claude |
| **E3b** | 4 couches (CHFF4, WQNJ6, WQND3, WQNS1) × (repos sud 20 poses + marche sud 10) = 120 occurrences ; 5 palettes | Claude, reproduit à l'identique par Codex (écart max 0) |
| Codex 60 frames | 4 corps A1 f45 + cycle d'attaque complet CHFB1A1/WQNS0A1/WQNC0A1/WQNJ6A1 (14 × 4) ; 60 926 px visibles x2, 243 735 x4 | Codex |
| **E5** | cycle d'attaque Codex, 4 couches ; méthodes Claude + fonctions Codex | Claude |

### 7.2 Palettes et recouvrement (nouveau contrôle)

Ordre : métal, mineure, majeure, peau, cuir, armure, cheveux.

| Palette | Valeurs | Rôle | Canaux identiques à une palette d'entraînement |
|---|---|---|---|
| REF | 30 47 57 12 39 21 3 | entraînement ; référence de production ; = Codex « A » | — |
| B | 21 57 47 8 66 30 0 | entraînement | — |
| C | 19 63 66 15 39 26 4 | entraînement | — |
| D | 67 68 47 84 25 57 2 | validation | **1/7** (majeure) |
| E « armure bleue » | 30 47 57 12 39 68 3 | validation | **6/7** (REF sauf armure) |
| CX-B « contrast » | 30 63 3 12 39 21 57 | validation E5 | **5/7** |
| CX-C « pale » (peau sombre) | 30 55 30 0 39 30 0 | validation E5 | **4/7** |
| Défaut guerrière humaine | 30 91 93 12 23 93 2 | jamais testée | 2/7 |

Lecture : E, CX-B et CX-C sont partiellement vues. Seule D teste une vraie généralisation. Les gains s'y maintiennent (E3b x4 Q8 −15,5 %, E5 x4 Q8 −25 % face à Q0). Exigence pour la suite : ≥ 10 palettes de validation sans aucun canal commun avec l'entraînement.

### 7.3 Candidats limités à la frame source (Codex, 60 frames, pondéré pixels)

| Mesure | x2 | x4 |
|---|---:|---:|
| Erreur, indices de la frame (Q0) | 0,021585 | 0,022329 |
| Erreur, classe complète | 0,020319 | 0,020954 |
| Gain | 5,86 % | 6,16 % |
| Pixels changés | 4,21 % | 4,43 % |
| Fuite de classe / alpha | 0 | 0 |

Le goulot n'est pas le choix des candidats : c'est la discrétisation à 12 niveaux.

### 7.4 E3b — couleur

x4 :

| Méthode | REF | B | C | D | E | Moy. entr. | Moy. valid. | Δ valid. vs Q0 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| xBR | 40,03 | 38,22 | 44,68 | 43,81 | 53,21 | 40,98 | 48,51 | −3,7 % |
| **Q0 actuel** | 26,54 | 35,98 | 47,07 | 44,15 | 56,62 | 36,53 | 50,38 | — |
| Q1 classe | 25,74 | 36,03 | 47,19 | 44,51 | 56,53 | 36,32 | 50,52 | +0,3 % |
| Q2 Bayer | 29,97 | 38,80 | 51,59 | 46,32 | 60,25 | 40,12 | 53,29 | +5,8 % |
| Q7 diffusion | 28,24 | 37,85 | 50,26 | 45,57 | 59,18 | 38,78 | 52,37 | +3,9 % |
| Q6 indices multi | 32,53 | 29,90 | 31,41 | 42,48 | 49,58 | 31,28 | 46,03 | −8,6 % |
| Q3 fraction mono | 16,34 | 32,33 | 43,80 | 41,46 | 53,92 | 30,82 | 47,69 | −5,4 % |
| **Q3m fraction multi** | 27,12 | 25,41 | 25,29 | 39,53 | 47,01 | 25,94 | 43,27 | **−14,1 %** |
| Q5 Q3m + reclassement | 24,42 | 24,31 | 23,77 | 39,61 | 47,21 | 24,16 | 43,41 | −13,8 % |
| **Q8 Q3m + frontières** | 23,51 | 23,91 | 23,17 | 37,32 | 44,88 | 23,53 | 41,10 | **−18,4 %** |

x2 (validation moyenne D/E) : Q0 48,02 · Q6 43,71 · Q3m 40,75 · Q8 38,81. D seule x2 : Q0 42,03 · Q3m 37,30 · Q8 35,50.

Décomposition (nouveau) : sur la validation x4, **Q3m apporte 77 % du gain de Q8** (−14,1 % sur −18,4 %) ; sur D seule, 68 % (−10,5 % sur −15,5 %). Le gros du bénéfice vient de la fraction ajustée sur plusieurs palettes ; la frontière ajoute ~5 %. Q5 (reclassement HD) n'apporte rien hors entraînement : rejeté. Q6 dégrade REF de +22,6 % : le consensus coûte sur la palette de production.

### 7.5 E5 — validation croisée sur le corpus Codex

Entraînement REF/B/C ; validation = moyenne D, CX-B, CX-C.

| Méthode | x4 | x2 | D seule x4 |
|---|---:|---:|---:|
| xBR | 48,6 | 47,3 | 55,0 |
| Q0 | 49,4 | 47,5 | 58,1 |
| Q1 | 50,3 | 48,3 | 59,2 |
| Q6 | 45,1 | 43,4 | 51,3 |
| Q3 | 47,2 | 45,1 | 56,8 |
| Interpolation Codex (mono-palette, linéaire) | 47,0 | 44,9 | 56,5 |
| Bayer Codex | 52,5 | 50,6 | 61,1 |
| **Q8 sRGB** | **37,8** | **35,6** | **43,6** |
| Q8 sRGB exact | 37,9 | 35,7 | 43,7 |
| Q8 linéaire exact | 38,1 | 36,0 | 43,9 |

- Q8 : −23 % vs Q0, −20 % vs interpolation Codex.
- Interpolation Codex = Q3 (même idée, mono-palette) : excellente sous sa palette, faible ailleurs.
- sRGB ≈ linéaire : choisir sRGB (plus simple, bit-exact).
- E5 ne contient pas Q3m : aucune ablation frontière sur ce corpus.

### 7.6 Temporel (signe d'alignement corrigé)

Erreur trouvée par Codex et revérifiée : les scripts E3b (`e3b_experiment.py:457-458`) et E5 (`e5_cross.py:237`) utilisent `ox = (centre_b − centre_a) × échelle`. Avec `monde = x − centre`, il faut `ox = (centre_a − centre_b) × échelle`. Test synthétique : 5/5 comparaisons fausses avant, 0/6 après.

Taux de pixels « statiques » (cible Δ < 0,01) dont la sortie change de > 0,02, x4 :

| Méthode | Corps REF | Corps B | 4 couches × 2 palettes, non pondéré | idem, pondéré pixels |
|---|---:|---:|---:|---:|
| Q0 | 9,86 % | 18,28 % | 13,62 % | 13,20 % |
| Bayer | 6,72 % | 16,02 % | 14,08 % | 11,21 % |
| Q6 | 8,29 % | 9,05 % | 12,75 % | 8,53 % |
| Q3 | 0,74 % | 10,19 % | 9,23 % | 5,30 % |
| Q3m | 5,86 % | 5,60 % | 11,82 % | 5,73 % |
| **Q8** | **4,80 %** | **4,85 %** | **9,99 %** | **4,90 %** |
| Diffusion d'erreur | 26,27 % | 30,87 % | 34,01 % | 30,00 % |

x2 pondéré : Q0 12,80 · Q6 8,19 · Q3m 4,81 · Q8 3,62 · Bayer 10,85 · diffusion 27,31.

- Corps : Q0 14,07 % → Q3m 5,73 % → Q8 4,82 %. Là aussi, Q3m porte l'essentiel.
- Toujours publier le mode d'agrégation.
- Limites : aucune correspondance de surface, masque incluant l'ombre (dilue), boucles et durées ignorées. Cycle d'attaque E5 : trop peu de pixels statiques, non concluant.

### 7.7 Précision de la fraction

| Bits | Q3 REF x4 (E3) | Taille zlib Q3 x4 |
|---|---:|---:|
| 4 | 16,7 | 281 Ko |
| 3 | 17,1 | 281 Ko |
| 2 | 17,9 | 243 Ko |

Q8 arrondi 4 → 3 bits (recalcul Codex, x4) : REF 23,51→23,70 · B 23,91→24,05 · C 23,17→23,43 · D 37,32→37,47 · E 44,88→45,03. ≈ 46 % des RGB changent d'un cran, l'erreur à peine. **3 bits retenus.** L'encodeur final optimisera directement les positions 3 bits (§9).

### 7.8 Tramage

| Mesure | Résultat |
|---|---|
| Bayer, erreur pixel (E3b validation x4) | +5,8 % vs Q0 ; motif visible |
| Bayer après flou σ 0,5 px logique (Codex, x2) | 0,01387 → 0,01248 (mieux qu'aucun tramage) ; interpolation 0,01143 (meilleure) |
| Bayer, stabilité sur frame répétée | 0 changement (phase fixe) ; bruit renouvelé : 30,06 % |
| Cycle réel 14 frames (Codex, 4 851 px) | Bayer 7,61 % · aucun 8,23 % · bruit 32,65 % |
| Diffusion d'erreur | ×2,0 à ×2,5 le temporel de Q0 |

Décision : aucun tramage. Bruit variable par frame interdit. Réouvrir seulement un Bayer faible, fixe et local si une matière garde des bandes **après** Q3m.

### 7.9 Rampes `MPALETTE`

- Mesures E1 (Claude, 256 lignes) : pas médian entre nuances voisines ΔE_OK 0,055 (p10 0,025 ; p90 0,096) ; non-uniformité médiane ×2,8 (p90 ×9,2) ; dérive de teinte clair→sombre médiane 20°.
- Égalisation par longueur d'arc (7 lignes) : CV 0,15–0,47 → 0,013–0,027 ; mais 2 437 / 3 072 positions changent (79,3 %, revérifié).
- Lignes non monotones : 197 198 199 204 212 213 221 253 255 ; RGB dupliqués : 74–78, 222, 225.
- Diagnostic, pas recette : ne pas réécrire `MPALETTE`. La fraction comble déjà les grands pas.

### 7.10 Sensibilité à la palette d'inférence (Codex)

Indices visibles différents entre « inféré sous A puis recoloré » et « inféré sous B/C » : corps 31,99 % / 44,39 % ; CHFF4 20,26 % / 36,28 % ; casque 30,91 % / 37,04 %. Écart rendu moyen ΔE 0,014–0,030. Masques identiques.

Conséquence : une recette apprise sous une seule palette ne généralise pas par construction. L'erreur résiduelle ~0,04 sur palettes nouvelles est celle **de ces méthodes sur ces palettes**, pas une borne démontrée.

### 7.11 Affichage simulé (E3b, écart NEAREST ↔ réduction d'aire, plus bas = moins de crénelage)

| Zoom | xBR x2 / x4 | Q0 x2 / x4 | Q8 x2 / x4 | Bayer x4 |
|---|---|---|---|---:|
| 1,0 | 2,67 / 1,98 | 3,29 / 2,74 | 3,07 / 2,40 | 4,69 |
| 1,3 | 3,71 / 3,64 | 3,45 / 3,32 | 3,02 / 2,73 | 4,22 |
| 2,0 | 0 / 1,97 | 0 / 2,05 | 0 / 1,84 | 2,94 |
| 3,0 | 1,09 / 0,39 | 1,32 / 0,75 | 1,23 / 0,68 | 1,37 |

Lecture corrigée : x4 n'est désavantagé qu'au zoom entier 2, où x2 est exact par construction. À 1,0, 1,3 et 3,0, x4 crénelle moins que x2. OBSERVÉ EN JEU : x4 « légèrement meilleur » en NEAREST. Le seuil « x4 utile seulement dès zoom 3 » est faux.

### 7.12 Tailles (zlib, E3b, indicatif seulement)

| Plan | x2 | x4 |
|---|---:|---:|
| Q0 (indices) | 67 724 o | 168 793 o |
| Q6 (indices) | 67 961 o | 164 379 o |
| Q3m classe + t8 delta 3 bits | 134 302 o (×1,98) | 382 275 o (×2,26) |
| Pixels frontière / opaques | 32 % | 21 % |

La « taille Q8 » publiée = celle de Q3m (plan frontière, masque, métadonnées omis). zlib ≠ XPRESS. Aucun budget ne se décide sur ces chiffres.

### 7.13 Audit du prototype de frontière (Codex)

107 985 pixels frontière pondérés : 14 352 (13,3 %) impliquent plus de 2 canaux ; 9 062 (8,4 %) ont un poids primaire nul (la classe primaire disparaît). Le voisin est le premier d'un parcours 3×3 fixe, pas le meilleur.

---

## 8. Format cible : registre V6 (spécification logique)

Numéro de version à confirmer au moment du code. Principe : **V6 = V5 + ajouts optionnels**. Sans plans optionnels, les octets de texture doivent être identiques à V5.

### 8.1 Contenu par frame

```text
géométrie x1, centre, identité source            inchangés vs V5
representatives[256]                             conservé (provenance source), plus utilisé pour le cache
dep_mask[256 bits]                               entrées de P lues par le décodage ; fait autorité
plan I   u8[W×H]                                 indice de base (sémantique V5)
plan F   u8[W×H], valeurs 0..7   (optionnel)     fraction vers succ(I) ; absent ⇒ 0
plan B   liste creuse (optionnel, Q8)            (pixel u32, I2 u8, F2 u8 0..7, W u8 1..7)
compression                                      XPRESS_HUFF par plan, comme V5
en-tête de registre                              profil de classes (ex. character-bg2ee-2.7.3.0)
                                                 + règle de décodage versionnée (ex. ramp-lerp-srgb8-v1)
```

### 8.2 Successeur

```text
succ(i) = i      si i ≤ 3
        = i      si 4 ≤ i ≤ 87  et (i−4) mod 12 = 11
        = i+1    si 4 ≤ i ≤ 87  sinon
        = i      si 88 ≤ i ≤ 255 et (i−88) mod 8 = 7
        = i+1    sinon
```

Positions par classe : 12 nuances → 89 positions (11 × 8 + 1) ; paire 8 nuances → 57.

### 8.3 Invariants d'encodage

- `I ≤ 3` ⇒ `F = 0` et pixel absent de B (transparent, ombre, réservés copiés du guide).
- `F > 0` interdit sur la dernière nuance d'une classe (succ(I) = I).
- `I` et `succ(I)` dans la classe du guide ; `I2` dans une classe autorisée (§9.4).
- `W ∈ 1..7` : la primaire contribue toujours.

### 8.4 Décodage bit-exact (Python = C++)

```text
lerp8(a, b, f) = (a·(8−f) + b·f + 4) >> 3                  par octet de couleur, f ∈ 0..7
C(i, f)        = RGB : lerp8(P[i], P[succ(i)], f) ; A : A(P[i])
pixel          = C(I, F)
si B           : RGB = (C(I,F)·W + C(I2,F2)·(8−W) + 4) >> 3 ; A = A(P[I])
```

Opère sur les octets du format natif (RGBA ou BGRA : les trois octets couleur sont indépendants, comme `xbr_blend_pixel`). `f = 0` ⇒ `C(i,0) = P[i]` exactement.

### 8.5 LUT et cache

```text
EXT[i·8 + f] = C(i, f)        2 048 dwords = 8 Kio par palette de couche
```

- Recalculée quand l'empreinte change ; empreinte = FNV sur (format natif, règle de décodage, `P[k]` pour `k ∈ dep_mask`).
- `dep_mask ⊇ {I} ∪ {succ(I) : F>0} ∪ {I2} ∪ {succ(I2) : F2>0}`. Tout indice lu hors masque ⇒ frame rejetée (fail-closed, comme aujourd'hui).
- Palette pulsée (opcodes 8/9) : empreinte différente à chaque frame ⇒ LUT + recomposition à chaque frame, comme aujourd'hui pour les indices.

### 8.6 Tests d'identité obligatoires

1. V6 sans F ni B = V5 : textures identiques octet pour octet.
2. `F ≡ 0` : identique au chemin indexé.
3. Modifier une couleur hors `dep_mask` : ni empreinte ni texture ne changent.
4. Encodeur Python et décodeur C++ : mêmes octets pour tous les `(i, f)` valides et un échantillon de `(I, F, I2, F2, W)`.

### 8.7 Cas particuliers

- **Q6** = V6 sans plan F ; seul le sens de `dep_mask` change. C'est la seule différence runtime.
- **xBR** = plan I seul, F absent.
- **Palettes fixes (monstres non false-color)** : le plan B avec `F2 = 0` donne un mélange générique de deux entrées quelconques (poids 1/8), utilisable plus tard sans nouveau format (§13.3).
- Ne jamais changer silencieusement le sens de `representatives` dans V3/V4/V5.

---

## 9. Encodeur de référence

### 9.1 Entrées par frame et couche

`source_indices`, guide `classe[H,W]`, `alpha`, `ombre`, `centre`, cibles `T_k` (float, x4 ou BOX x2), palettes réalisées `P_k` (sans éclairage), poids `w_k`.

### 9.2 Jeu de palettes

| Usage | Composition |
|---|---|
| Ajustement (K) | REF (production) + défaut guerrière humaine `30 91 93 12 23 93 2` + 1 à 4 palettes « carré latin » : chaque canal reçoit des familles de teinte distinctes d'une palette à l'autre, un clair et un sombre par canal sur l'ensemble, jamais deux canaux voisins quasi identiques dans une même palette |
| Validation | ≥ 10 palettes, **aucun canal commun** avec l'ajustement : `RANDCOLR` résolus, défauts `CLASCOLR`/`RACECOLR` d'autres classes/races, valeurs opcode 7 fréquentes des ITM (`PLAT01` armure 27…), extrêmes (0, 67, 68) |
| Poids | égaux par défaut ; option de surpondérer REF et les défauts |
| Choix de K | tester 3, 4, 6 ; retenir le plus petit K à ≤ 2 % du meilleur score de validation |

Coût : K inférences par frame. Pour `0x6110`, P13 = 94 010 inférences ⇒ ≈ 282 000 pour K = 3. La clé de cache inclut déjà la palette.

### 9.3 Recherche (Q3m et Q6)

Pour chaque pixel opaque non spécial de classe `c` :

```text
Π(c) = positions (i,f) de la classe : i ∈ c, f ∈ 0..7, f = 0 si succ(i) = i        (89 ou 57)
coût(i,f) = Σ_k w_k · ‖OKLab(C_k(i,f)) − OKLab(T_k)‖²        C_k = décodeur exact §8.4 sous P_k
(I,F) = argmin coût ; égalité ⇒ plus petit i puis plus petit f (déterminisme)
Q6 : même recherche avec f = 0
```

Recherche exhaustive, vectorisable : elle optimise directement ce que le runtime affichera. Elle remplace la projection sur une polyligne OKLab (Claude) et l'optimisation de poids en lumière linéaire (Codex), qui n'étaient pas alignées sur le décodeur.

### 9.4 Frontières contraintes (Q8c, après ablation)

- Candidats `c2` : classes présentes dans le voisinage 3×3 **du guide** (matière réellement adjacente), toutes évaluées ; pas de premier voisin.
- Paire autorisée par défaut si `canaux(c) ∪ canaux(c2)` ≤ 2 ; paramètre d'ablation.
- Recherche : 8 meilleures positions mono-classe de `c` × 8 de `c2` × `W ∈ 1..7`.
- Accepter si le coût baisse d'au moins τ (départ 5 %) **et** aucune palette ne se dégrade de plus de δ (départ 2 %).
- Zones protégées configurables (fines arêtes, yeux) : sans frontière.

### 9.5 Contrôles automatiques de chaque run

| Contrôle | Seuil |
|---|---|
| Fuite de classe | 0 pixel hors classe du guide (+ `c2` autorisée) |
| Alpha, ombre, spéciaux | identiques au guide |
| Dépendances | `dep_mask` exact (ni manque, ni excès) |
| Reconstruction | Python = C++ octet pour octet |
| Validation couleur | publier D et chaque palette disjointe séparément |
| Temporel | métrique corrigée, 4 agrégations (§12.4) |
| Taille | XPRESS réel par plan, mémoire décompressée |

---

## 10. x2, x4 et filtrage

### 10.1 Politique

- Master : x4. Livraison par défaut : x2 (mémoire ÷4, décodage ÷4).
- x4 : option qualité, décidée par mesure au zoom réel (OBSERVÉ : léger gain même en NEAREST).
- Aucun seuil de zoom universel.

### 10.2 Expérience de décision (2560×1440, zooms réellement accessibles)

| Variante | MAG | MIN | Mips | But |
|---|---|---|---|---|
| x2 témoin | NEAREST | NEAREST | non | référence QA |
| x2 Catmull-Rom | shader | shader | non | configuration acceptée pour xBR |
| x4 actuel | NEAREST | NEAREST | non | coût sans correction |
| x4 aire | NEAREST | aire/BOX explicite | non | qualité de réduction |
| x4 mips | NEAREST | LINEAR_MIPMAP_LINEAR | oui, sur RGBA prémultiplié, régénérés à chaque recomposition | stabilité en mouvement |

Pré-requis : mesurer d'abord zoom min/max (capture d'un sprite de hauteur connue, ou lecture de l'état via EEex). Critères : détail perçu, stabilité caméra, halo, CPU/upload, mémoire, FPS/p95. Une capture agrandie en nearest n'est pas une preuve.

Code concerné : séparer MIN et MAG dans `creature_sprite_x2.cpp:1534-1538` ; `MAX_LEVEL` > 0 seulement si mips générés. Catmull-Rom local n'est pas un filtre de réduction (`sprite/catmull-rom/README.md:342`).

---

## 11. Plan de développement `0x6110`

Dépendances techniques, pas un workflow imposé (doctrine `docs/PRODUCTION_RAPIDE.md`). Chaque phase produit de nouvelles versions ; aucun run historique réécrit.

| Phase | Travail | Critère de passage |
|---|---|---|
| **P0** Oracles | lecteur BAM P8 complet ; réalisation Python `MPALETTE` (7×12 + 21×8) ; renommer le contrôle de provenance en `MPALETTE` (alias vérifié `RANGES12`) ; banc d'évaluation corrigé : signe d'alignement, masques séparés (visibles / 4..255 / ombre), agrégations pondérée et non pondérée, durées natives | réalisation octet pour octet ; E3b reproduit ; signe testé par recadrage synthétique |
| **P1** Multi-palettes hors ligne | inférence K palettes (cache existant) ; encodeur §9 (Q6, Q3m) ; corpus = E3b + attaque Codex + 4 armures ; ≥ 10 palettes disjointes ; K = 3/4/6 | Q3m bat Q0 sur **chaque** palette disjointe ; fuite 0 ; K choisi |
| **P2** DLL V6 | lecteur V6 (dep_mask, plan F, LUT 2 048, plan B désactivable) ; fail-closed ; tests hôte golden Python/C++ ; fallback V5/xBR | tests §8.6 verts ; `ctest` ; aucune modification de géométrie ni de sauvegarde |
| **P3** Verticale en jeu | CHFF4 + `WQNJ6`, `WQND3`, `WQNS1` en Q3m x2 ; memberships limitées à `0x6110` ; A/B contre Q0 | QA utilisateur explicite ; recoloration (§12.2 T1) sans liseré ; `layer n/n` dans le log |
| **P4** Échelle et filtre | mesure du zoom ; expérience §10.2 | décision x2/x4 + filtre, datée |
| **P5** Frontières | Q8c vs Q3m, mêmes frames, palettes, packing, scènes (attaque, marche, mort, repos) | gain propre visible **et** mesuré ; coût XPRESS acceptable ; sinon Q8 abandonné |
| **P6** 0x6110 complet | 628 BAM, par famille et couche ; ordre : CHFF4 → CHFB1–3 → armes fréquentes (S1 S0 SS AX WH MC CL S2 BW) → boucliers → casques | aucune frame manquante ; cache froid/chaud, mémoire, upload mesurés |
| **P7** Paperdolls | `CHFF*INV`, `WPN*INV`, `WPN*OIN` : pipeline UI séparé | mesures UI propres (échelle, centres, filtre) |
| **P8** Généralisation | §13 | preuves par famille ; aucune QA transférée |

Scripts à créer (noms proposés, absents du dépôt) : `reboutcx_multipal.py` (inférence K), `palette_frac_encode.py` (Q6/Q3m/Q8c → V6), `palette_eval.py` (banc corrigé), écrivain V6 dans la chaîne catalogue. Tests ciblés : `python pipeline/scripts/test_changed.py --targeted --path <fichier> --run` ; C++ : commandes de `engine/InfinityEngine-Enhancer/source-patchee/AGENTS.md`.

---

## 12. QA

### 12.1 Hors ligne (format)

| Test | Invariant |
|---|---|
| `MPALETTE` | 7×12 copies et 21×8 mélanges exacts |
| Encodage / décodage | déterministe ; Python = C++ |
| Dépendances | couleur hors `dep_mask` modifiée ⇒ rien ne change |
| Classes | aucun pixel hors classe / paire autorisée |
| Recoloration canal par canal | modifier un seul canal ne change que ses pixels et ses paires |
| Alpha / ombre | spéciaux conservés ; aucun halo RGB sous transparence |
| Tables BAM | mêmes cycles, lookups, centres, placeholders |
| Compression | taille XPRESS, mémoire décompressée, latence |

### 12.2 En jeu

Préalables : jeu et InfinityLoader fermés pour installer/restaurer (installateurs transactionnels) ; `CreatureSpriteFilter = Nearest` pour la QA ; console Lua via `Enable-BG2Debug.ps1` (`Baldur.lua` est effacé à la fermeture).

```text
C:MoveToArea("AR0700")        # Promenade de Waukeen, jour, sol clair
                              # + une zone de nuit ou sombre au choix pour les nuances sombres
C:CreateItem("PLAT01")  C:CreateItem("CHAN01")  C:CreateItem("LEAT01")
C:CreateItem("HELM01")  C:CreateItem("HELM03")  C:CreateItem("ISHLD03")  C:CreateItem("SHLD05")
C:CreateItem("BDSW1H06") C:CreateItem("SW1H01") C:CreateItem("SW2H01")  C:CreateItem("BOW01")
```

Couleur imposée par couche (EEex ; `dwFlags` = location `0xPR` ; paramètres à confirmer sur la version EEex installée) :

```lua
EEex_GameObject_ApplyEffect(EEex_Sprite_GetSelected(), {["effectID"]=7, ["effectAmount"]=68, ["dwFlags"]=0x05, ["durationType"]=0, ["duration"]=600, ["sourceID"]=EEex_Sprite_GetSelectedID()})
```

| Bloc | Cas | Attendu |
|---|---|---|
| T0 mire | BAM 16×16 des 256 indices sur une animation false-color de test | formule des paires, indices 1–3, effets |
| T1 recoloration | 4 couleurs joueur au menu ; REF/B/C/D ; lignes extrêmes (0, 67, 68, 208+) ; un canal à la fois | aucun liseré étranger ; seuls les canaux concernés changent |
| T2 couches | 4 armures × {sans/avec casque} × {bouclier, 2 mains, arc, deux armes} ; arme en main gauche recolorée par `0x1R` puis `0x2R` | composition complète ; tranche la question §3.4 |
| T3 animations | 9 directions + 7 miroirs ; marche, repos long G12, A1–A9, CA, SA/SS/SX, touché, mort, sommeil | pas de frame native isolée, pas de saut ; revérifier `CHFF4G12 sequence=20 slot=15` (log 2026-09-26) |
| T4 effets | `BDSW1H06` (opcode 9 pulsé), pause grise, invisibilité, flou, pétrification, nuit | identique au natif, FPS stables |
| T5 temporel | repos 30 s, marche lente horizontale, zoom avant/arrière | aucun grouillement ; A/B Q0 / Q3m (/ Q8c) |
| T6 affichage | zoom min / 1 / max ; x2 / x4 ; filtres | x4 retenu seulement si gain au zoom joué |
| T7 intégration | sélection, survol, occlusion, foule, deux acteurs même BAM aux couleurs opposées, autre avatar `WQN` | pas de halo ; pas de fuite de cache entre instances |
| T8 transitions | changer équipement/couleur, sauvegarder/recharger, voyager, reset contexte GL | pas de texture périmée |
| T9 performance | combat 6 personnages + effets | 59–60 FPS, p95 ≤ actuel + 5 % |

Traçabilité : captures par cas, `InfinityEngine-Enhancer.log` (lignes `Composing creature sprite …`), décision explicite de l'utilisateur. Jamais de validation déduite d'une installation.

### 12.3 Mesure temporelle correcte

Publier séparément : tous visibles ; recolorables 4..255 ; ombre. Agrégations pondérée pixels et non pondérée. Ajouter : correspondance guidée par le mouvement (flot optique restreint à la classe), masques de disocclusion, couture de boucle, pondération par durée native, vidéo en jeu au ratio réel.

### 12.4 Niveaux d'acceptation

Hors ligne ⇒ encodeur. Capture runtime ⇒ décodeur. Session en jeu ⇒ scènes testées seulement. Installation et release restent des états séparés (`sprite/README.md`).

---

## 13. Généralisation à tous les sprites de BG2

### 13.1 Périmètre (index `sprite/index/sprite_animations.csv`, 2026-09-30)

| Profil runtime | Animations supportées | false_color | Problème multi-palettes |
|---|---:|---|---|
| `character-bg2ee-2.7.3.0` (types 5000, 6000) | 78 | 1 | **oui** : ce guide s'applique tel quel |
| `monster-bg2ee-2.7.3.0` (7000) | 102 | 0 | non |
| `monster-icewind-bg2ee-2.7.3.0` (E000) | 131 | non renseigné | à vérifier |
| `monster-quadrant` / `multi-new` (1000) | 9 / 10 | 0 | non |
| Non supportés false-color (character_old 6, monster_old 10, town_static 17, ambient 22, layered 2, large 1) | 58 | 1 | audit du profil de classes avant tout |

504 IDs indexés, 330 supportés. Site : 86 corps PJ/PNJ, 947 objets visuels, 2 238 278 frames.

### 13.2 Règles

- **Character false-color** : même profil de classes, même encodeur, même V6. Vérifier par INI (`false_color`, `split_bams`, préfixes, `height_code`). Les équipements `WQ*`/`WP*` sont partagés entre animations : produire par composant, router par memberships.
- **Autres false-color** : ne pas réutiliser le profil Character sans audit (disposition des gammes, indices spéciaux, couches).
- **Palettes fixes** : une seule palette réelle ; Q0 sur la palette du BAM est déjà juste. Gain possible plus tard par mélange générique à deux entrées (plan B, §8.7) contre le banding ; priorité basse.
- **Paperdolls** : pipeline UI séparé.
- **Effets, VVC, projectiles** : hors de ce chantier.
- Aucune QA d'une animation ne vaut pour une autre.

### 13.3 Graphe d'automatisation

```text
KEY/BIFF → INI (owner, type, false_color, préfixes) → BAM (cycles, frames, centres, placeholders)
         → ITM (apparence, catégorie, masques, opcodes 7/8/9) → partages (memberships)
         → jobs par composant → inférence K palettes (cache frame+palette) → encodage V6
         → catalogue → installation transactionnelle → QA par famille
```

Décisions qui restent humaines : visage, texture de peau, matières, niveau de lissage, préférence xBR/ReboutCX par asset, verdict au zoom réel.

---

## 14. Pistes rejetées ou reportées

| Option | Décision | Motif |
|---|---|---|
| RGBA précoloré unique / BAM V2-PVRZ | rejet | détruit la recoloration |
| Q0 seul | repli existant | 12 niveaux, palette unique |
| Q1 classe complète | rejet comme solution | +0,3 % en validation |
| Q3 / interpolation mono-palette | rejet comme final | surapprentissage palette |
| Q5 reclassement HD | rejet | aucun gain en validation |
| Diffusion d'erreur | rejet | temporel ×2,0–2,5 |
| Bayer global | rejet par défaut | motif, erreur pixel +6 à +10 % |
| Bruit temporel | interdit | 30 % de pixels changent sur frame fixe |
| Modifier `MPALETTE` / égaliser les rampes | rejet | global, change vanilla/objets/mods |
| Patch de `RealizeRange` | rejet | V6 fait mieux sans patch binaire |
| Couleurs RGB fixes littérales | rejet | cassent effets et recoloration |
| Canal fixe corps | rejet | aucun canal libre |
| Canal fixe équipement (lignes 74–78) | reporté | intrusif (ITM partagés, mods) |
| Gammes par acteur dans le DLL | reporté | seulement si bandes après Q3m |
| Alpha doux / composition « over » | reporté | change la sémantique ; expérience séparée |
| Shader complet immédiat | reporté | CPU existant plus direct ; profilage manquant |
| Second hook EEex | rejet | le point de capture IEE existe ; EEex = QA/instrumentation |
| x4 par défaut | reporté | décision P4 |
| Carte de nuances grise (inférence indépendante de la palette) | à tester | pourrait remplacer K inférences ; risque de perdre les contrastes de matière ; comparer à Q3m |

---

## 15. Questions ouvertes

| Priorité | Question | Expérience décisive |
|---:|---|---|
| P0 | Q3m tient-il sur ≥ 10 palettes entièrement disjointes ? | P1 |
| P0 | Coût réel V6 (XPRESS, F, B, masque) ? | P1–P2 |
| P0 | Effets post-palette reproduits ? | T4 |
| P1 | Zoom min/max réel à 2560×1440 ? | capture d'un sprite de hauteur connue |
| P1 | x4 + minification filtrée vaut-il la mémoire ? | §10.2 |
| P1 | Gain propre de Q8c ? paires autorisées ? | P5 |
| P1 | K = 3, 4 ou 6 ? | P1 |
| P1 | Location opcode 7 d'une arme en main gauche ? | T2 |
| P2 | Stabilité en mouvement réelle ? | §12.3 + vidéo |
| P2 | Carte de nuances grise ? | comparaison à Q3m |
| P2 | CPU ou shader ? | profil foule + palettes pulsées |
| P2 | Deux composants même resref, memberships disjointes, même catalogue ? | premier catalogue P3 |
| P2 | Provenance et licence ReboutCX ? | retrouver modèle et données |

---

## 16. Registre des corrections

### 16.1 Trouvées dans cette passe finale

| Affirmation | Où | Correction | Preuve |
|---|---|---|---|
| Catmull-Rom « option documentée non implémentée » ; « seuls NEAREST et LINEAR » | synthèse Codex §5.2 | mode `CatmullRom` implémenté (shader 4×4 prémultiplié, sampler NEAREST) ; QA xBR des personnages jouables acceptée sous CatmullRom le 2026-09-11 | `core/config.h:131-133`, `creature_sprite_filter.cpp`, décision QA 2026-09-11 |
| Fraction « q/7 » | synthèse Codex annexe B | fraction `f/8` vers `succ(I)`, 89 positions par rampe ; c'est ce qui a été mesuré | `e3b_experiment.py`, §8.2 |
| Palettes D/E et CX-B/CX-C « jamais vues » | toutes études | recouvrement 1/7, 6/7, 5/7, 4/7 canaux avec l'entraînement ; seule D quasi indépendante | §7.2 |
| « ReboutCX déjà installé et accepté en jeu sur `0x6100` » | revue croisée Claude | accepté pour 2 compositions + non-infériorité ; préférence non tranchée ; xBR + Catmull-Rom accepté à l'échelle | décisions QA 2026-09-11/14 |
| « x4 crénelle davantage que x2 au zoom habituel » ; « x4 utile dès zoom ≥ 3 » | guide et présentation Claude | données : x4 plus mauvais seulement au zoom 2 exact ; x4 « légèrement meilleur » en jeu en NEAREST | §7.11, mesure 26/09 |
| « La deuxième arme garde les sémantiques de l'arme » | synthèse Codex §3.3 | non démontré ; sans effet sur l'encodage (palette capturée par cellule) ; à trancher par T2 | `hooks.cpp:2855-3009` |
| « Clé de cache P13 à étendre à la palette » | guide Claude | déjà le cas | `reboutcx_cache_p12.py:33-39` |
| Gain Q8 attribué aux frontières | présentations | 77 % du gain vient de Q3m (fraction multi-palettes) ; frontière ≈ 5 % | §7.4 |
| E5 et son scintillement | revue croisée | même erreur de signe que E3b ; pas de Q3m dans E5 | `e5_cross.py:237` |

### 16.2 Déjà corrigées par les études, confirmées ici

| Affirmation initiale | Correction | Confirmation |
|---|---|---|
| Le moteur lit `RANGES12.BMP` | `MPALETTE.BMP` ; `RANGES12` absent du binaire ; fichiers identiques | chaînes et SHA-256 revérifiés |
| Paperdolls `WPM` | `WPN` (`INV`/`OIN`) | CSV |
| H6 et ZW à produire | hors périmètre | CSV : 536 overlays éligibles, 0 H6 |
| Aucune couleur fixe exploitable | vrai pour le corps ; lignes 74–78 constantes pour l'équipement | revérifié |
| « 9 directions (5 miroirs) » | 9 stockées + 7 miroirs | — |
| Scintillement Q8 −50 % puis −33 % | −26,7 % non pondéré, −62,9 % pondéré, corps −65,7 % | CSV recalculé |
| Bayer « pire sur toutes les métriques » | pire en erreur pixel ; meilleur après flou ; temporel variable | §7.8 |
| Q8 « 3 bits » | mesuré en 4 bits ; arrondi 3 bits ≈ sans perte | §7.7 |
| Taille Q8 ×2,0–×2,3 | taille de Q3m, frontière et masque omis ; zlib ≠ XPRESS | §7.12 |
| Plancher 0,04 infranchissable | résiduel de ces méthodes, pas une borne | — |
| « EEex n'apporte rien au rendu » | fournit des hooks ; inutile ici car le point IEE existe | — |
| `MPAL256` = palettes des créatures non-Character | trop général (PLT, autres chemins) | — |
| Q6 exige une nouvelle DLL (Codex) / sans aucune modification (Claude) | le rendu ne change pas ; le sens du champ de dépendances change ⇒ V6 avec `dep_mask` | `creature_sprite_x2.cpp:1264, 1326-1344` |
| xBR « candidat de livraison conservateur » seulement / « simple repli » | voie acceptée en QA et option d'installation | §4 |

---

## 17. Sources et reproduction

### 17.1 Carte des études (`sprite/Etudes_Sprite_codex_claude/`)

| Dossier / fichier | Contenu |
|---|---|
| `ClaudeCode_Guide_HD_0x6110_Femme_Humaine_Guerriere/GUIDE_ClaudeCode_HD_0x6110_palettes_dynamiques.md` | guide Claude v1 (historique, chiffres E3 dilués) |
| `…/PRESENTATION_ClaudeCode_0x6110.html` | présentation v1 + erratum E3b (remplacée par la page compagnon) |
| `…/REVUE_CROISEE_Codex_ClaudeCode_0x6110.html` | revue croisée + E5 |
| `…/donnees*/`, `figures*/`, `outils/` | mesures E1–E5, tuiles, planches, scripts |
| `CODEX_BG2EE_Femme_Humaine_Guerriere_2026-09-29/GUIDE_CODEX_BG2EE_FEMME_GUERRIERE.md` | guide Codex |
| `…/engine_research.md`, `engine_disassembly_codex.txt` | preuves moteur |
| `…/inventory_research.md`, `assets_inventory*.{csv,json.gz}` | inventaire 774 BAM / 870 ITM |
| `…/upscale_research.md`, `upscale/`, `palette/` | 4 upscales, 60 NPZ, tramage, gradients |
| `…/codex_palette_study_20260929/COMPARAISON_CODEX_CLAUDE_0x6110.md` + `comparaison_claude_20260929/` | comparaison critique, recalcul temporel, 3 bits |
| `GUIDE_ULTIME_SPRITES_HD_BG2EE.md` | synthèse Codex (historique ; corrigée par ce guide) |
| `GUIDE_DEFINITIF_SPRITES_HD_BG2EE.md` | **ce guide** |
| `PRESENTATION_ETUDE_SPRITES_HD_0x6110.html` | page compagnon |

Duplication : ~5 100 fichiers, ~1 700 contenus uniques (copies de livraison Codex). Copies racine / étude / `delivery` identiques hors `.pyc`.

### 17.2 Portabilité des scripts

Les données sont intègres ; les recettes ne sont pas relançables telles quelles :

- chemins absolus vers `C:/Users/Adrien/Desktop/…` (ex. `e5_cross.py:28`), vers le Python chaiNNer, polices, poids locaux ;
- racine calculée par `parents[3]` ; `render_guide.mjs` dépend de `marked` ;
- `fetch_engine_sources_codex.py` relit `master` : seuls les fichiers de `source_reference/` sont épinglés (Near Infinity `50021b83`, GemRB `5552ade1`, EEex `6c1f42b8`).

Pour rejouer : copier dans une nouvelle version d'étude, résoudre via `config://` (`chainner_python`, `reboutcx_model`, `bg2ee_game_root`), corriger le signe temporel, écrire hors des dossiers historiques.

### 17.3 Identités

```text
BaldurReal.exe 2.7.3.0      b51093a49140b2b8a7c046b4652bb8e535be24ebbc12b1d735e0b94217a14d57
MPALETTE.BMP = RANGES12.BMP 7a9a654d5cbc4cee0ca211be05d24fb54bf8298a781c074882000d5f829d66dd
ReboutCX (poids locaux)     c36a14ddb51ae094324a53b67c345da2d6b6bbf6a2249726056d5b94bdedab05
chitin.key                  1818ffebb2424992fb39fb13509e7f629ac819b08a553c2dd4ac25f2e40a979f
```

---

## Annexe A — Formules

```text
rampe r              : indices 4+12r … 15+12r
paire (a,b), rang k  : 88 + 8k + j, j ∈ 0..7 ; nuances 2..9 des deux rampes
mélange vanilla      : (A + B) >> 1 par octet sRGB
succ(i)              : §8.2
lerp8(a,b,f)         : (a·(8−f) + b·f + 4) >> 3
frontière            : (C(I,F)·W + C(I2,F2)·(8−W) + 4) >> 3, W ∈ 1..7
opcode 7 param2      : 0xPR, P = couche (0 corps, 1 arme, 2 bouclier/main gauche, 3 casque), R = canal 0..6
alignement temporel  : ox = (centre_a − centre_b) × échelle
```

## Annexe B — Codes de méthode

| Code | Définition | Stocke | Runtime |
|---|---|---|---|
| xBR | xBR direct, provenance d'indice | I | actuel |
| Q0 | nuance la plus proche parmi les indices de la frame source, palette REF | I | actuel (production) |
| Q1 | idem, classe complète | I | dep_mask |
| Q2 | Bayer 4×4 ancré au centre BAM | I | actuel |
| Q7 | diffusion d'erreur dans la gamme | I | actuel |
| Q6 | indice minimisant l'erreur sur K palettes, classe complète | I | V6 sans F |
| Q3 | fraction ajustée sur REF seule | I + F | V6 |
| Q3m | fraction ajustée sur K palettes | I + F | V6 |
| Q5 | Q3m + classe réestimée en HD | I + F | V6 (rejeté) |
| Q8 | Q3m + mélange de deux classes aux frontières (prototype E3b) | I + F + B | V6 |
| Q8c | Q8 sous les contraintes §9.4 | I + F + B | V6 |

## Annexe C — Règles de conservation

- Ne jamais modifier les études sources ni leurs preuves historiques ; créer une nouvelle version.
- Ne jamais déduire une validation en jeu d'une métrique hors ligne, ni une installation ou une release d'une production.
- Ne jamais remplacer globalement un resref partagé ; router par memberships.
- Ne jamais modifier `MPALETTE`, payload, staging, TP2, `content.json` ou release sans demande explicite.
- Fermer BG2EE et InfinityLoader avant tout remplacement installé.
