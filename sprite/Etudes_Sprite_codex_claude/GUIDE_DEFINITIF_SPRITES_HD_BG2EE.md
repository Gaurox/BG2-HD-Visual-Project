# Guide définitif — Sprites HD jouables de BG2EE

## Palettes dynamiques, xBR / ReboutCX, x2 / x4 — cas de référence `0x6110` (femme humaine guerrière), généralisable

| Champ | Valeur |
|---|---|
| Version | **2026-10-02** — consolidation P2/P3, décision P4, Q8c écarté et pilote P7 `CHFF1INV` accepté ; résultats historiques P0/P1 conservés |
| Rédaction | Claude Code (Claude Opus 5.5), mises à jour de développement Codex |
| Entrées relues intégralement | étude Claude (guide v1, présentation + erratum E3b, revue croisée E5) ; étude Codex (guide, notes moteur/inventaire/upscale, comparaison critique, recalcul temporel, arrondi 3 bits) ; synthèse Codex `GUIDE_ULTIME_SPRITES_HD_BG2EE.md` (29/09 21:16) |
| Vérifications refaites dans cette passe | binaire moteur, `MPALETTE`/`RANGES12`, routine des mélanges, code runtime IEE (`file:line`), quantifieur et cache de production, décisions QA du dépôt, mesure x4 du 26/09, run P13 `0x6110`, tables E3b/E5, recalcul temporel, arrondi 3 bits, inventaire CSV, lignes constantes 74–78, égalisation des rampes, recouvrement des palettes de validation |
| Mise à jour P1 | Run [`palette-q3m-p1-20260930-v1`](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-20260930-v1/README.md) (commit `a1a68a73`) relu : README, JSON, CSV, scripts et tests ; agrégats recalculés depuis `color-summary.csv` / `temporal-sequences.csv`. Résultats §7.14, P2+ ajustés ; chiffres historiques E3/E3b/E5 inchangés |
| Clôture P0 | Run [`palette-oracles-p0-20260930-v4`](../families/playable-characters/6110-human-female-fighter/research/palette-oracles-p0-20260930-v4/README.md) : oracle scalaire + boucle x64 native, lecteur BAM indépendant, provenance `MPALETTE`/alias, **E3b reproduit numériquement**, 30 tests verts (§7.15). Remplace l'état P0 partiel contenu dans P1 ; historiques/P1 immuables |
| Reprise après P4/P7 | **Monde `0x6110` : Q3m K6 x2 + BOX, sans mipmaps. UI `CHFF1INV` : Q3m K6 x2 + Nearest, accepté.** P3 validée par l'utilisateur ; Q8c écarté ; couverture monde déjà produite ; aucune généralisation UI ni release déduite (§10–11) |
| Autorité | Ce guide fait référence pour le développement. Les études sources restent intactes et historiques ; leurs erreurs sont listées au §16. |
| Compagnon visuel | [`PRESENTATION_ETUDE_SPRITES_HD_0x6110.html`](PRESENTATION_ETUDE_SPRITES_HD_0x6110.html) (hors ligne, explorateur de palette, comparateur, chiffres) ; version expliquée `PRESENTATION_PEDAGOGIQUE_SPRITES_HD_0x6110.html` et `…_EN.html`. Pages locales ignorées par Git, antérieures à P1 |
| Autorités d'état | Ce guide référence les acquis ; production = générations, QA = décisions immuables, installation = reçu actif, release = manifestes dédiés. Les installations d'essai P3/P4/P7 ne constituent pas une intégration release. |

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
| Résultats P1 : K = 6, régression REF, tailles XPRESS réelles | §7.14 |
| Spécification du format cible (registre V6) | §8 |
| Algorithme de l'encodeur | §9 |
| x2, x4, filtrage | §10 |
| BOX/Mipmaps réellement implémentés et mesures sans contrôle PC | §10.3–10.4 |
| Plan de développement et critères de passage | §11 |
| Contrat UI confirmé et pièges du pilote `CHFF1INV` | §11.1 |
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
| Encodage cible | **Q3m K6** : indice de base + fraction 3 bits vers la nuance suivante | P1 : −27,1 % x2, −25,4 % x4 sur 10 palettes disjointes ; P3 validée en jeu ; pilote UI `CHFF1INV` accepté (§11) |
| Frontières (Q8c) | **écartées par l'utilisateur le 2026-10-02** ; poursuivre Q3m sans essai Q8c | DÉCISION ; prototype historique ≠ implémentation validée |
| Espace d'interpolation au runtime | octets sRGB, arrondi entier défini (§8.4) | MESURÉ : sRGB ≈ linéaire (37,8 vs 38,1) |
| Espace d'optimisation | OKLab (distance au carré), contre les couleurs exactes du décodeur | MESURÉ (P1 ; recherche exhaustive contrôlée par une implémentation indépendante) |
| Palettes d'ajustement | **K = 6** : REF + défaut guerrière humaine + rotations LATIN1–4, poids égaux (§7.14) ; K = 4 à +2,7 % du meilleur score, hors du seuil de 2 % | MESURÉ (P1, x2 et x4) |
| Palette de production REF | régression P1 inchangée : +6,1 % x2, +11,6 % x4 face à Q0 ; P3 validée par l'utilisateur, aucune surpondération demandée | MESURÉ hors ligne + décision utilisateur P3 |
| Coût des plans I + F + masque | ×1,98 x2, ×2,11 x4 face à Q0 (XPRESS réel ; en-têtes V6 et `representatives` exclus) | MESURÉ (P1) |
| Tramage | aucun | MESURÉ sur le corpus |
| Échelle livrée | **x2 + BOX monde `0x6110`** ; x4 conservé comme master/option ; **UI pilote x2 + Nearest** | DÉCISION P4 ; QA UI indépendante (§11.1) |
| Reconstruction | CPU V6 dans `creature_sprite_x2.cpp` / `core/palette_fraction.h` ; UI dédiée `paperdoll_q3m.cpp` | IMPLÉMENTÉ ; tests P2 et décodages de palettes natives P7 |
| Composition | ordre natif, écrasement des pixels non transparents ; alpha doux reporté | CONFIRMÉ (existant) |
| Palette globale | ne jamais modifier `MPALETTE` pour ce chantier | DÉCISION |

### 1.3 Ordre de développement (détail §11)

```text
P0 oracles + banc d'évaluation corrigé (signe temporel, masques séparés, ≥ 10 palettes disjointes)
   → CLÔTURÉ HORS LIGNE 2026-09-30 : acquis P1 + run P0 dédié (§7.15) ; captures runtime en P3
P1 inférence multi-palettes + encodeur Q6/Q3m hors ligne ; K = 3/4/6
   → FAIT 2026-09-30 : Q3m K = 6, critères satisfaits x2 et x4 (§7.14)
P2 DLL : écrivain + lecteur V6 (masque de dépendances, plan F, LUT) + golden tests Python = C++
   → FAIT : preuve P2 PASS, format V6 réservé ; B/packing absents (§8)
P3 → VALIDÉE INTÉGRALEMENT PAR L'UTILISATEUR avant P4
P4 → DÉCIDÉE 2026-10-02 : x2 + BOX monde 0x6110, sans mipmaps
P5 → ÉCARTÉE par l'utilisateur : poursuivre Q3m, aucun essai Q8c
P6 → COUVERTURE MONDE DÉJÀ PRODUITE en P3 : 656 BAM / 178 360 frames x2
P7 → PILOTE CHFF1INV SEUL ACCEPTÉ ; autres corps/équipements UI non traités
P8 → autres animations Character : aucune QA transférée
```

### 1.4 Ce qui n'est pas acquis

- P3 est validée en jeu ; P7 accepte uniquement `CHFF1INV`. Les gains numériques P1 restent des distances aux cibles ReboutCX, pas des scores de préférence humaine.
- Généralisation hors ligne établie par P1 : 10 palettes sans identifiant ni rampe identique au même canal que l'ajustement, toutes améliorées (§7.14). Les palettes E3b/E5 (§7.2) restent partiellement vues.
- Consensus ≠ amélioration universelle : Q3m K6 dégrade REF, la palette de production actuelle (+6,1 % x2, +11,6 % x4).
- Zoom P4 mesuré dans le viewport **2528×1339** (§10.4) ; aucun seuil/résultat à transférer à une autre taille de fenêtre, scène ou interface.
- Plans/headers V6 et caches mesurés en P2/P3 ; coûts composition/upload de la scène P4 disponibles. VRAM sprites isolée, coût GPU isolé et profilage foule restent non établis ; plan frontière non implémenté.
- La stabilité temporelle n'est mesurée que sur pixels immobiles alignés par ancre, pas sur surfaces en mouvement (P1 compris).
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
| V6 Character implémenté : I/F, profil1/règle1, `dep_mask` exact ; brut/XPRESS par plan ; catalogue V2 mixte V5/V6 entre composants homogènes | `pipeline/PALETTE_Q3M_V6.md`, `pipeline/scripts/palette_registry.py`, `core/palette_fraction.h`, preuve P2 (§11) |
| V4 refusé si `scale != 2` ; ≤ 8 opérations ; 5 poids `7:1 3:1 1:1 1:3 1:7` | `creature_sprite_x2.cpp:2023`, `1396`, `creature_sprite_x2.h:183` |
| V3/V4/V5 : chaque indice du payload doit avoir `representatives[i] != 0xFFFF`. V6 : nuances/successeurs sans représentant autorisés, contrôlés par classes et `dep_mask` | `creature_sprite_x2.cpp`, contrat V6 |
| Cache V6 : FNV sur format/type, profil/règle et seules couleurs du `dep_mask` après normalisation transparent ; V3/V4/V5 conservent l'empreinte basée sur `representatives` | `core/palette_fraction.h`, `creature_sprite_x2.cpp`, contrat V6 |
| `representatives` ne sert pas d'offset d'échantillonnage : les 256 couleurs réalisées sont déjà en main | lecture `1446-1488` |
| `P[transparent] = 0` imposé après capture | `creature_sprite_x2.cpp:1368-1374` |
| Composition : tout pixel non nul écrase le précédent | `creature_sprite_x2.h:172` |
| Cellules Character : corps + arme + main gauche + casque, palette capturée par cellule | `hooks.cpp:2855-2858`, `2934-3009` |
| Routage : ID d'animation → memberships → composants ; un composant peut servir plusieurs animations | `creature-sprite-0x1000.md:178-186` |
| Modes : `Nearest`, `Linear`, `CatmullRom`, **`Box` x2/x4**, **`Mipmaps` x4 seulement** ; paramètre unique et portée par animation | `core/config.h`, `creature_sprite_filter.cpp::effective_mode`, §10.3 |
| `Box` : sampler MIN/MAG Nearest + intégration d'aire au shader, MAX_LEVEL0. `Mipmaps` : MIN trilinear/MAG Nearest + chaîne prémultipliée régénérée à chaque upload | `creature_sprite_filter.cpp`, `creature_sprite_x2.cpp`, `assets/override/fpSprite.glsl` |
| Catmull-Rom local ≠ filtre de réduction | `sprite/catmull-rom/README.md:342` |
| Historique au 2026-09-30 : `CreatureSpriteFilter = Nearest`. Décision P4 au 2026-10-02 : `Box`, portée `0x6110` ; `0x6100` reste Nearest | décision §10.1 ; état actif à lire dans le reçu d'installation |
| UI pilote : lecteur V6 brut dédié `CHFF1INV`, Realize corrélé à la cellule/slot, shader natif Bitmap6, sampler Nearest, géométrie x1/backing x2 | `paperdoll_q3m.cpp`, `hooks.cpp`, QA et invariants §11.1 |

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
| 2026-09-30 | P1 hors ligne `0x6110` : Q3m K6 retenu, critères satisfaits x2 et x4 ; aucun catalogue, DLL, installation, QA ni release modifiés | `sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-20260930-v1/` |
| 2026-10-01 | P2 V6 PASS ; P3 couverture monde `0x6110` produite (656 BAM/178 360 frames x2), P3 déclarée entièrement validée par l'utilisateur avant P4 | runs P2/P3 et état §11 |
| 2026-10-02 | P4 : x2+BOX monde `0x6110`, préférence x2 légère ; P5 Q8c écartée explicitement | décision §10.1 ; demande utilisateur §11 |
| 2026-10-02 | P7 : seul corps UI `CHFF1INV` Q3m K6 x2/Nearest accepté ; deux moitiés HD/CRC confirmées ; commit `d4fbd869` | `sprite/index/qa-decisions/paperdolls/2026-10-02-accepted-chff1inv-q3m-k6-x2-nearest-v1.json` |
| site public | installateur prévu : Auto / Full xBR / Full ReboutCX | `bg2-hd-website/fr/sprites.html` |

Conséquence produit : **xBR reste une voie de production/QA et un comparateur**. V6 sait porter xBR (plan I seul, F absent/0) ; l'échec du chemin HD conserve le **BAM natif**, sans deuxième feuille V5/xBR automatique.

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

Noyau P1 : étapes 2 et 7 `pipeline/scripts/palette_eval.py` ; 3 `reboutcx_batch.prepare_inference_rgb` ; 4–5 `reboutcx_multipal.py` (P12 N=86, canevas multiple de32, fp16 déterministe, cibles float32, répétition bit-exact) ; 6 `palette_frac_encode.py`. Écrivain V6 désormais implémenté dans `palette_registry.py` ; contrat livré `pipeline/PALETTE_Q3M_V6.md`. Plans I/F déjà valides réutilisables sans nouvelle inférence (pilote UI §11.1).

### 6.3 Master x4, livraison x2

```text
T_k x4 (float) → réduction BOX → T_k x2 (float) → encodage à x2 avec le guide xBR2
```

Ne jamais réduire des plans I/F déjà quantifiés : la quantification et les frontières se recalculent à l'échelle livrée. P1 applique ce schéma (BOX float32 `chainner_ext`, guides xBR2 et xBR4 directs).

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
| Défaut guerrière humaine | 30 91 93 12 23 93 2 | jamais testée en E3b/E5 ; palette d'ajustement `DEFAULT` de P1 | 2/7 |

Lecture : E, CX-B et CX-C sont partiellement vues. Seule D teste une vraie généralisation. Les gains s'y maintiennent (E3b x4 Q8 −15,5 %, E5 x4 Q8 −25 % face à Q0). Exigence pour la suite : ≥ 10 palettes de validation sans aucun canal commun avec l'entraînement → satisfaite par P1 (§7.14).

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

La « taille Q8 » publiée = celle de Q3m (plan frontière, masque, métadonnées omis). zlib ≠ XPRESS. Aucun budget ne se décide sur ces chiffres. Mesure XPRESS réelle des plans : §7.14.

### 7.13 Audit du prototype de frontière (Codex)

107 985 pixels frontière pondérés : 14 352 (13,3 %) impliquent plus de 2 canaux ; 9 062 (8,4 %) ont un poids primaire nul (la classe primaire disparaît). Le voisin est le premier d'un parcours 3×3 fixe, pas le meilleur.

### 7.14 P1 — Q3m multi-palettes sur 10 palettes disjointes (2026-09-30)

Run [`palette-q3m-p1-20260930-v1`](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-20260930-v1/README.md), commit `a1a68a73`. MESURÉ hors ligne ; aucune capture ni QA en jeu.

| Élément | Protocole |
|---|---|
| Corpus | 180 occurrences, 144 frames BAM uniques : E3b 120 (4 couches × repos sud 20 poses + marche sud 10) + Codex 60 (pose A1 des 4 armures `CHFB1–3`/`CHFF4` ; attaque 14 slots × `CHFB1`, `WQNS0`, `WQNC0`, `WQNJ6`) |
| Cibles | 18 palettes × 144 frames = 2 592 inférences ReboutCX x4 float32 ; x2 = BOX float32 du x4 ; réinférence de contrôle : écart max 0 |
| Métrique primaire | ΔE OKLab moyen ×1000 contre la cible **float**, pixels recolorables `4..255`, pondéré pixels × occurrences ; visibles et ombre publiés à part |
| Q0 | quantifieur de production sous REF, candidats = indices de la frame source |
| Q6 / Q3m | encodeur §9.3, poids égaux, sans tramage ni frontière ; K emboîtés dans l'ordre d'ajustement : K3 = REF, DEFAULT, LATIN1 ; K4 + LATIN2 ; K6 + LATIN3, LATIN4 |
| Choix de K | plus petit K qui améliore **chacune** des 10 validations et reste à ≤ 2 % du meilleur score |

Palettes, ordre métal, mineure, majeure, peau, cuir, armure, cheveux :

| Rôle | Nom | Valeurs | Origine |
|---|---|---|---|
| ajustement | REF | 30 47 57 12 39 21 3 | production |
| ajustement | DEFAULT | 30 91 93 12 23 93 2 | `CLASCOLR` FIGHTER + `RACECOLR` HUMAN, relus à l'exécution |
| ajustement | LATIN1 · LATIN2 · LATIN3 · LATIN4 | 21 57 46 83 55 67 44 · 3 54 60 84 45 68 20 · 58 50 69 0 33 19 71 · 73 71 18 15 67 56 66 | rotations teinte/clarté conçues |
| validation | VAL01 · VAL02 · VAL03 · VAL04 · VAL05 · VAL06 | 57 58 122 152 1 43 98 · 67 46 47 157 2 43 0 · 25 28 120 157 2 24 99 · 24 99 169 13 2 64 4 · 24 67 56 26 2 25 107 · 25 28 120 178 2 24 112 | défauts `CLASCOLR` d'autres classes × `RACECOLR` d'autres races ; ligne en collision remplacée par la plus proche autorisée en OKLab (VAL03–06) |
| validation | VAL07 · VAL08 | 119 125 155 153 142 39 143 · 52 161 120 171 54 51 134 | `RANDCOLR` résolu, graine 6110 |
| validation | VAL09 · VAL10 | 67 68 0 79 25 27 14 · 0 67 68 80 0 0 67 | extrêmes |
| diagnostic | LEGACY_D · LEGACY_E | D et E du §7.2 | partiellement vues ; hors choix de K |

Contrôle : 0 identifiant et 0 rampe RGB identique partagés au même canal avec l'union des 6 palettes d'ajustement.

Validation, moyenne des 10 palettes :

| Méthode | x2 | Δ vs Q0 | x4 | Δ vs Q0 |
|---|---:|---:|---:|---:|
| xBR | 35,47 | +6,5 % | 36,90 | +3,8 % |
| Q0 | 33,31 | — | 35,55 | — |
| Q6 K6 | 28,73 | −13,7 % | 30,64 | −13,8 % |
| Q3m K3 | 26,24 | −21,2 % | 28,53 | −19,8 % |
| Q3m K4 | 24,94 | −25,1 % | 27,22 | −23,4 % |
| **Q3m K6** | **24,28** | **−27,1 %** | **26,52** | **−25,4 %** |

- K4 est à +2,70 % x2 et +2,63 % x4 du meilleur score, K3 à +8,1 % et +7,6 % ⇒ **K6 aux deux échelles**. K3, K4 et K6 améliorent chacune des 10 validations.
- Gain Q3m K6 par palette : 19,1 % (VAL10) à 39,8 % (VAL05) en x2 ; 18,1 % à 37,3 % en x4.
- Par couche, chaque validation s'améliore aux deux échelles (recalculé depuis `color-frames.csv`). Gain minimal x2 / x4 : corps 20,9 / 19,8 %, casque 5,2 / 5,6 %, bouclier 12,1 / 13,4 %, arme 13,5 / 12,1 %. Le casque `WQNJ6` gagne le moins.
- xBR ne cherche pas à reproduire la cible ReboutCX : son écart mesure une différence de modelé, pas un défaut.

Palettes d'ajustement et de diagnostic, x2 / x4 :

| Palette | Q0 | Q6 K6 | Q3m K3 | Q3m K6 | Δ Q3m K6 vs Q0 |
|---|---:|---:|---:|---:|---:|
| REF | 20,91 / 21,55 | 27,52 / 29,19 | 19,75 / 21,47 | 22,18 / 24,04 | **+6,1 % / +11,6 %** |
| DEFAULT | 31,84 / 34,22 | 28,83 / 30,44 | 18,61 / 20,22 | 22,15 / 24,07 | −30,4 % / −29,6 % |
| LEGACY_D | 40,50 / 43,10 | 34,73 / 37,05 | 32,80 / 35,49 | 30,93 / 33,48 | −23,6 % / −22,3 % |
| LEGACY_E | 43,20 / 45,79 | 37,16 / 39,52 | 36,08 / 39,02 | 33,30 / 35,93 | −22,9 % / −21,5 % |

Lecture : le poids de REF fixe le compromis. En K3, REF pèse 1/3 et ne régresse pas (−5,5 % x2, −0,4 % x4), mais la validation perd 8 % ; en K6, REF pèse 1/6 et régresse. Q6 dégrade REF de +31,6 % / +35,5 %. Levier à tester si P3 juge la régression visible : surpondérer REF dans K6 (§9.2), dans un nouveau run.

Temporel, pixels recolorables immobiles qui changent (§7.6, signe corrigé), 10 validations, poses distinctes + couture de boucle :

| Méthode | pondéré pixels x2 | x4 | non pondéré x2 | x4 |
|---|---:|---:|---:|---:|
| xBR | 11,73 % | 11,96 % | 24,54 % | 23,98 % |
| Q0 | 20,28 % | 21,66 % | 29,63 % | 29,07 % |
| Q6 K6 | 12,03 % | 12,51 % | 25,99 % | 25,20 % |
| Q3m K3 | 9,97 % | 11,16 % | 25,81 % | 25,77 % |
| **Q3m K6** | **8,36 %** | **9,40 %** | **23,91 %** | **24,01 %** |

- Slots natifs répétés (durées relatives) : Q0 → Q3m K6 = 4,19 → 1,73 % x2 ; 4,31 → 1,87 % x4.
- Sous REF aussi : 11,22 → 7,06 % x2 ; 11,29 → 7,66 % x4. La régression de couleur de REF ne se double pas d'une régression temporelle.
- Par séquence, x2 pondéré : repos 18,91 → 6,88 % ; marche 26,94 → 13,78 % ; attaque 21,61 → 14,90 %.
- Non pondéré = moyenne sur palettes des moyennes par séquence.

Tailles, XPRESS_HUFF réel par plan, stockage min(brut, compressé), masque de dépendances 32 o par frame, somme sur les 180 occurrences ; en-têtes V6 et `representatives` exclus :

| Méthode | x2 (o) | × Q0 | x4 (o) | × Q0 |
|---|---:|---:|---:|---:|
| xBR, plan I | 166 872 | 0,96 | 338 122 | 0,83 |
| Q0, plan I | 173 704 | 1 | 407 818 | 1 |
| Q6 K6, I + masque | 179 765 | 1,03 | 405 054 | 0,99 |
| **Q3m K6, I + F + masque** | **343 620** | **1,98** | **859 646** | **2,11** |

- Plan F compressé : 0,94 × le plan I en x2, 1,13 × en x4. Décompressé, I + F = ×2 de Q0 ; la texture RGBA finale ne change pas à échelle égale.
- Q3m K6 x4 / x2 = ×2,50 (Q0 : ×2,35) sur ce corpus.

Coût et contrôles :

- Inférence de 2 592 cibles sur RTX 5090 : 2,55 s de calcul CUDA, 40,1 s de mur ; run complet 187 s. Cibles float locales : 188 Mo, ≈ 73 Ko par cible.
- Fuite de classe 0 ; spéciaux modifiés 0 ; `dep_mask` exact à chaque frame ; 1 935 241 pixels à fraction non nulle, cumul des variantes Q3m.
- Recherche indépendante : 1 584 cas pixel × méthode × K identiques, surcoût 0.
- 220 allers-retours XPRESS de plans réels ; 17 tests ciblés verts (README P1).

Limites :

- Nouveau protocole : cible float, masque recolorable, Q3 entier 3 bits, noyau P12. Ne pas comparer ces nombres aux tables §7.4–7.6, qui ne sont ni réécrites ni revendiquées reproduites.
- Temporel aligné par ancre, sans flot optique ; durées en slots relatifs, secondes réelles inconnues.
- Plans logiques seulement : aucun binaire V6, aucune DLL, aucune capture palette/effets, aucune QA en jeu.
- Planche `comparison-x2.png` (xBR/Q0/Q6 K6/Q3m K6 × REF, DEFAULT, VAL01, VAL09, VAL10, LEGACY_D) : illustration locale, ignorée par Git.

### 7.15 P0 : finalisation des oracles, 2026-09-30

Run [`palette-oracles-p0-20260930-v4`](../families/playable-characters/6110-human-female-fighter/research/palette-oracles-p0-20260930-v4/README.md). **PASS hors ligne** ; complète P1, sans réécrire ses résultats ni les études historiques.

| Contrôle | Mesure | Preuve du run P0 |
|---|---|---|
| RGB neutre 7×12 + 21×8 | NumPy production = oracle scalaire indépendant = boucle x64 native ; 530 palettes × 768 octets ; différences 0 | `audit.json`, `neutral-palette-golden.npz` |
| Arrondi des mélanges | 65 536 couples d'octets passés dans la boucle native ; `(a+b)>>1` exact, y compris sommes impaires et >255 | `audit.json` |
| BAM P8 indépendant | 836 BAM / 185 459 frames / 252 540 168 pixels / 18 903 cycles / 376 665 slots ; indices, centres, palette, lookup identiques au lecteur existant ; octets canoniques identiques aux BIF natifs | `audit.json`, `bam-resources.json` |
| E3b historique | **1 080 valeurs numériques et toutes les autres feuilles identiques**, écart maximal 0 ; simulation d'affichage incluse | `e3b-reproduction.json`, `e3_results.json` |
| Tests ciblés | **30 PASS** : BAM/BAMC, palettes, alias, JSON, recadrages 2D x2/x4 dans les deux sens, masques, agrégations | `tests.json` |

Décisions utiles à P2 et suite :

- **Provenance** : `MPALETTE` = locator **`0x0000012E`**, `RANGES12` = **`0x00000189`**, BMP type 1 dans `data/Default.bif`, même SHA §17.3. Nouveau job → `MPALETTE` + son locator ; changer seulement le nom est incorrect. `reboutcx_batch.load_palette_profiles` accepte désormais les deux sources et vérifie l'alias exact ; preuve/cache des jobs historiques inchangés. Aucun job scellé migré.
- **Périmètre de l'oracle** : `[RVA 0x421F7B,0x42201E)` exécuté dans le processus de test, EXE épinglé §17.3 ; shades 2..9, 21 paires. Vérifie le mélange RGB neutre avant effets et packing final. Ne valide pas évitement de clé verte, alpha, effets ou modulation post-palette. V6 doit consommer la **palette runtime réalisée**, pas cette reconstruction neutre ; captures nécessaires en P3. La fixture RGBA P1 reste à alpha synthétique (§8.6).
- **Lecture des sources BAM** : 679 BAMC ; 22 209 frames à centre négatif ; 31 933 frames 1×1. Conserver les centres i16 et la distinction frame réelle / marqueur nul. Fixtures synthétiques : dimensions nulles, cycle vide, lookup troué ; absents du corpus réel. L'oracle conserve la géométrie déclarée, le lecteur historique transforme les dimensions nulles en marqueur 1×1.
- **RLE natif** : 27 frames terminent par un run transparent dépassant `width*height` (ex. `WQNAXA5/106`, `WQNS1G1/730`) ; tronquer ce dernier run comme le lecteur existant. Liste exacte `audit.json:clipped_native_rle`, ressources vérifiées dans les BIF. Cette compatibilité concerne les **sources BAM** ; les bornes des plans V6 restent fail-closed.
- **Durées relatives** : 95 369 slots adjacents répétés dans le corpus ; idle E3b = 20 poses / 56 slots par couche, motif `[6,2,2,2,2]×4`. Le banc P1 conserve les slots et la couture. BAM V1 ne porte aucun FPS/temps : pondération relative acquise ; secondes, pause/vitesse et cadence effective à mesurer en P3.
- **Deux protocoles** : E3b reproduit reste batch1 fp16 sans padding, cibles RGB u8, fractions Q3m/Q8 4 bits et ancien signe temporel. P2/P3 utilisent le banc P1 corrigé (noyau P12, cibles float, Q3 entier 3 bits, masques séparés, signe d'ancre corrigé). Ne pas remplacer les critères P1 par les métriques temporelles historiques.

Scripts : `pipeline/scripts/palette_oracle.py`, `palette_p0.py`. Reproduction `audit` / `e3b`, empreintes, commandes et snapshots : README du run P0. Aucun changement de DLL, installation, QA ou release.

---

## 8. Format cible : registre V6 (spécification logique)

**Version6 réservée et implémentée en P2** ; magic `IEECSXN\0`, catalogue monde V2. Spécification binaire : [`pipeline/PALETTE_Q3M_V6.md`](../../pipeline/PALETTE_Q3M_V6.md). Profil1/règle1, plans I/F uniquement ; **B et packing absents**, extensions inconnues rejetées. F absent/0 reproduit les pixels indexés ; les octets du fichier/en-tête V6 diffèrent de V5. Le pilote UI utilise un sous-ensemble V6 brut autonome (§11.1).

### 8.1 Contenu par frame

```text
géométrie x1, centre, identité source            inchangés vs V5
representatives[256]                             conservé (provenance source), plus utilisé pour le cache
dep_mask[256 bits]                               entrées de P lues par le décodage ; fait autorité
plan I   u8[(W×scale)×(H×scale)]                  indice de base ; W/H en géométrie native
plan F   même taille, valeurs 0..7 (optionnel)   fraction vers succ(I) ; absent ⇒ 0
plan B                                          absent ; proposition Q8c non implémentée
compression                                      brut ou XPRESS_HUFF par plan indépendant
en-tête de registre                              profil de classes (ex. character-bg2ee-2.7.3.0)
                                                 + règle de décodage versionnée (ex. ramp-lerp-srgb8-v1)
```

Contrat P1 repris par l'écrivain/lecteur V6 :

- identifiants : `CLASS_PROFILE = character-bg2ee-2.7.3.0`, `DECODE_RULE = ramp-lerp-srgb8-v1`, `ENCODER_ID = character-exhaustive-oklab-squared-q3-integer-v1` ;
- `dep_mask` = `np.packbits(bits, bitorder="little")` : 32 octets, entrée `8k + b` = bit `b` (poids faible d'abord) de l'octet `k` ;
- plan F = u8 par pixel, valeurs 0..7, compressé comme I. Un empaquetage 3 bits n'a pas été mesuré.

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
```

Opère sur les octets du format natif (RGBA ou BGRA : les trois octets couleur sont indépendants, comme `xbr_blend_pixel`). `f = 0` ⇒ `C(i,0) = P[i]` exactement.

`P` = palette effective capturée au point de rendu, après réalisation et packing natifs. L'oracle RGB neutre P0 (§7.15) ne remplace pas cette palette ; effets, alpha et évitement de clé verte sont hors de sa preuve.

### 8.5 LUT et cache

```text
EXT[i·8 + f] = C(i, f)        2 048 dwords = 8 Kio par palette de couche
```

- Cache monde : empreinte = FNV sur format/type natifs, IDs profil/règle et `P[k]` pour `k ∈ dep_mask` ; LUT scratch ne remplit que les couples `(I,F)` utilisés.
- **`dep_mask = {I} ∪ {succ(I) : F>0}` exact** : manque comme excès rejetés. F0 ne lit aucun successeur ; nuance/successeur peuvent être absents des représentants source.
- Palette pulsée : recomposition seulement si une couleur effectivement dépendante change ; modifier une couleur hors masque conserve le cache. Pilote UI : comparaison exacte de ces couleurs, deux backings mutables protégés par flush (§11.1).

### 8.6 Tests d'identité du décodeur

1. V6 sans F ni B = V5 : textures identiques octet pour octet.
2. `F ≡ 0` : identique au chemin indexé.
3. Modifier une couleur hors `dep_mask` : ni empreinte ni texture ne changent.
4. Encodeur Python et décodeur C++ : mêmes octets pour tous les `(i, f)` valides ; alpha primaire et encodings natifs conservés.

Fixture P1 : `decoder-golden.npz` (SHA `12171974…62910e4b`) ; 18×256×4 palettes RGBA à alpha synthétique, 1 824 couples légaux `(I,F)`, attendu scalaire. **Reproduction C++ acquise en P2** : 32 832 couples, encodings RGBA/u8, BGRA/u8, BGRA/u32_8888_REV et cas alpha arbitraire. Preuve : [P2](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p2-20260930-v1/README.md). P7 ajoute 128 décodages sur palettes natives relevées ; Q8c et tests `(I2,F2,W)` écartés par décision utilisateur.

### 8.7 Cas particuliers

- **Q6** = V6 sans plan F ; seul le sens de `dep_mask` change. C'est la seule différence runtime.
- **xBR** = plan I seul, F absent.
- **Palettes fixes (monstres non false-color)** : le mélange générique de deux entrées via B reste une proposition ; il demanderait un contrat/lecteur explicites. Le V6 livré est réservé au profil Character et ne transporte aucun B.
- Ne jamais changer silencieusement le sens de `representatives` dans V3/V4/V5.

---

## 9. Encodeur de référence

### 9.1 Entrées par frame et couche

`source_indices`, guide `classe[H,W]`, `alpha`, `ombre`, `centre`, cibles `T_k` (float, x4 ou BOX x2), palettes réalisées `P_k` (sans éclairage), poids `w_k`.

### 9.2 Jeu de palettes

| Usage | Composition | Appliqué par P1 |
|---|---|---|
| Ajustement (K) | REF (production) + défaut guerrière humaine `30 91 93 12 23 93 2` + 1 à 4 palettes « carré latin » : chaque canal reçoit des familles de teinte distinctes d'une palette à l'autre, un clair et un sombre par canal sur l'ensemble, jamais deux canaux voisins quasi identiques dans une même palette | REF, DEFAULT, LATIN1–4 (§7.14) |
| Validation | ≥ 10 palettes, **aucun canal commun** avec l'ajustement : `RANDCOLR` résolus, défauts `CLASCOLR`/`RACECOLR` d'autres classes/races, valeurs opcode 7 fréquentes des ITM (`PLAT01` armure 27…), extrêmes (0, 67, 68) | VAL01–10 : 6 défauts d'autres classes et races, 2 `RANDCOLR`, 2 extrêmes ; aucune valeur opcode 7 d'ITM ; contrôle par identifiant **et** par rampe RGB identique |
| Poids | égaux par défaut ; option de surpondérer REF et les défauts | égaux ; REF régresse en K6 ⇒ surpondération à tester si P3 le demande |
| Choix de K | tester 3, 4, 6 ; retenir le plus petit K à ≤ 2 % du meilleur score de validation | K6 ; K4 à +2,7 % |

Coût : K inférences par frame. Pour `0x6110`, P13 = 94 010 inférences ⇒ ≈ 564 000 pour K = 6 retenu (≈ 282 000 pour K = 3). La clé de cache inclut déjà la palette. P1 : ≈ 1 ms de calcul CUDA par cible, mais ≈ 73 Ko par cible float32 conservée, soit ≈ 41 Go à l'échelle P6 par extrapolation linéaire ⇒ encoder en flux ou purger les cibles.

### 9.3 Recherche (Q3m et Q6)

Pour chaque pixel opaque non spécial de classe `c` :

```text
Π(c) = positions (i,f) de la classe : i ∈ c, f ∈ 0..7, f = 0 si succ(i) = i        (89 ou 57)
coût(i,f) = Σ_k w_k · ‖OKLab(C_k(i,f)) − OKLab(T_k)‖²        C_k = décodeur exact §8.4 sous P_k
(I,F) = argmin coût ; égalité ⇒ plus petit i puis plus petit f (déterminisme)
Q6 : même recherche avec f = 0
```

Recherche exhaustive, vectorisable : elle optimise directement ce que le runtime affichera. Elle remplace la projection sur une polyligne OKLab (Claude) et l'optimisation de poids en lumière linéaire (Codex), qui n'étaient pas alignées sur le décodeur.

Implémentée telle quelle par `palette_frac_encode.encode_variants` (P1). Calcul en float64 ; candidats triés + `argmin` = plus petit `i` puis plus petit `f` ; K emboîtés sur un seul calcul de coût, dans l'ordre de la liste d'ajustement. Une recherche indépendante donne les mêmes choix sur 1 584 cas, surcoût 0. La taille des blocs de pixels ne change pas les octets encodés (test).

### 9.4 Frontières contraintes (proposition historique Q8c, écartée)

Spécification exploratoire conservée pour mémoire ; **aucun travail Q8c demandé**, aucun plan B livré. Décision utilisateur du 2026-10-02 : poursuivre Q3m K6 (§11).

- Candidats `c2` : classes présentes dans le voisinage 3×3 **du guide** (matière réellement adjacente), toutes évaluées ; pas de premier voisin.
- Paire autorisée par défaut si `canaux(c) ∪ canaux(c2)` ≤ 2 ; paramètre d'ablation.
- Recherche : 8 meilleures positions mono-classe de `c` × 8 de `c2` × `W ∈ 1..7`.
- Accepter si le coût baisse d'au moins τ (départ 5 %) **et** aucune palette ne se dégrade de plus de δ (départ 2 %).
- Zones protégées configurables (fines arêtes, yeux) : sans frontière.

### 9.5 Contrôles automatiques de chaque run

| Contrôle | Seuil | État après P1 |
|---|---|---|
| Fuite de classe | 0 pixel hors classe du guide (+ `c2` autorisée) | 0, contrôlé à chaque frame (`check_contract`) |
| Alpha, ombre, spéciaux | identiques au guide | 0 spécial modifié (indices 0–3 copiés du guide, F = 0) |
| Dépendances | `dep_mask` exact (ni manque, ni excès) | exact |
| Reconstruction | Python = C++ octet pour octet | côté Python : fixture `decoder-golden.npz` ; comparaison C++ en P2 |
| Validation couleur | publier D et chaque palette disjointe séparément | 10 validations + REF, DEFAULT, LEGACY_D/E publiées séparément (`color-summary.csv`) |
| Temporel | métrique corrigée, agrégations séparées (§12.3) | signe corrigé ; visibles / recolorables / ombre ; pondéré et non pondéré ; poses distinctes et slots ; couture |
| Taille | XPRESS réel par plan, mémoire décompressée | XPRESS réel par plan (`sizes.csv`) ; mémoire runtime non mesurée |

---

## 10. x2, x4 et filtrage

### 10.1 Politique

- Master : x4. Livraison par défaut : x2 (mémoire ÷4, décodage ÷4).
- x4 : option qualité, décidée par mesure au zoom réel (OBSERVÉ : léger gain même en NEAREST).
- Aucun seuil de zoom universel.
- P1 : gains Q3m K6 quasi identiques aux deux échelles (−27,1 % x2, −25,4 % x4) ; plans Q3m K6 x4 = ×2,50 des plans x2 sur le corpus. La fraction ne tranche donc pas x2/x4 : la décision reste P4.
- **P4 décidée le 2026-10-02 : x2 + BOX, sans mipmaps, sur `0x6110`**. Viewport 2528×1339, habituel maximum −7 crans (zoom 2.480864/2.479630) ; préférence utilisateur BOX nette en dézoom, x2 légère/incertaine. CPU composition x2/x4 BOX : 0.148/0.280 ms/frame ; trafic upload base 11.082/44.269 MB/s ; FPS ≈60 (sessions indépendantes). [Décision datée et périmètre](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-box-x2-measurement-20261002-v1/decision.json) ; [mesures et limites](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-box-x2-measurement-20261002-v1/README.md). Master x4 conservé ; aucun choix/QA BOX transféré à `0x6100` ni intégration release.

### 10.2 Expérience de décision (2560×1440, zooms réellement accessibles)

| Variante | MAG | MIN | Mips | But |
|---|---|---|---|---|
| x2 témoin | NEAREST | NEAREST | non | référence QA |
| x2 Catmull-Rom | shader | shader | non | configuration acceptée pour xBR |
| x2 aire (P4 retenu, `0x6110`) | NEAREST | aire/BOX explicite | non | choix daté 2026-10-02 ; magnification Nearest au zoom habituel mesuré |
| x4 actuel | NEAREST | NEAREST | non | coût sans correction |
| x4 aire | NEAREST | aire/BOX explicite | non | qualité de réduction |
| x4 mips | NEAREST | LINEAR_MIPMAP_LINEAR | oui, sur RGBA prémultiplié, régénérés à chaque recomposition | stabilité en mouvement |

Mesures acquises au §10.4 ; pour une autre scène/taille de fenêtre, conserver le viewport et le zoom réels. Critères utiles : détail perçu, stabilité caméra, halo, CPU/upload, mémoire, FPS/p95. Une capture agrandie en nearest n'est pas une preuve ; aucun besoin de rejouer les essais déjà acquis à octets/contrat identiques.

MIN/MAG désormais séparés par `creature_sprite_filter::finish_texture_sampling` ; `MAX_LEVEL>0` uniquement si la chaîne mip a été générée. Catmull-Rom local n'est pas un filtre de réduction (`sprite/catmull-rom/README.md:342`).

### 10.3 Filtrage livré : sens et portée

| Opération | Moment / données | Contrat actuel |
|---|---|---|
| BOX de production | cible ReboutCX x4 **float** → cible x2, avant quantification | §6.3 ; aucun lien automatique avec le filtre d'affichage |
| `CreatureSpriteFilter=Box` | réduction à l'affichage des RGBA réalisés/composés | **x2 et x4** ; sampler Nearest, aire des texels intégrée au shader avec sommes prémultipliées ; magnification Nearest ; MAX_LEVEL0 |
| `CreatureSpriteFilter=Mipmaps` | upload RGBA prémultiplié puis chaîne mip et minification trilinear | **x4 seulement** ; MAG Nearest ; génération à chaque recomposition/upload, y compris branche masque ; x2 demandé ⇒ Nearest |
| UI `CHFF1INV` | backing x2 du corps, shader Bitmap natif | **Nearest sans mipmaps** ; configuration monde BOX non appliquée à cette UI (§11.1) |

- BOX/Mipmaps visent la **qualité en réduction** (détails, contours, scintillement), avec un coût à mesurer. Ce ne sont pas deux options de performance ni deux modes cumulés : l'INI choisit un mode unique. Un hybride serait un nouveau contrat ; il n'est pas livré/testé.
- Portée P4 : `CreatureSpriteFilterAnimation=0x6110`. Les autres routes du catalogue, notamment `0x6100`, restent Nearest ; un choix global (`0`) demanderait une nouvelle décision de périmètre.
- BOX n'agit que si l'empreinte écran dépasse un texel HD. Empreinte >16 texels/axe ⇒ repli Nearest borné, sans tronquer l'intégration. À zoom habituel ~2.48 : x2 ≈0.806 texel/pixel (magnification), x4 ≈1.61 (réduction) ; au minimum x2≈2.43 / x4≈4.86.
- Preuve BOX : mode3 + chemin shader/provenance valide ; **MIN=MAG=Nearest ne signifie pas BOX inactif**. Preuve Mipmaps : mode4 + MIN9987/MAG9728 et MAX_LEVEL8 (9 niveaux observés). La sonde distingue composite/masque ; une observation isolée d'un sampler ne décrit pas tout le pipeline.
- Essais réellement effectués : x4 Nearest → **x4 BOX → x4 Mipmaps → x2 BOX**. Mipmaps x2 non implémenté/testé. Avis initial Mips « je vois pas de difference ingame », puis préférence finale BOX nette en dézoom ; préférence x2 légère/incertaine.
- Au zoom habituel statique x4 : composition Mips/BOX **4.258/0.280 ms/frame**, upload inclus **4.124/0.174** ; cadence ~60 FPS dans les deux cas. [Bilan Mipmaps](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-mipmaps-measurement-20261001-v1/README.md). Pas de coût GPU isolé ni de comparaison mouvement contrôlée (zoom de retour différent).

### 10.4 Mesure sans contrôle PC : acquis et limites

- Sonde P4 : `core/sprite_p4_probe.*`, `EnableCreatureSpriteP4Probe`, CSV distinct par session ; [installation/protocole](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p4-probe-20261001-v1/README.md). Observe le dessin ; aucun input ni changement visuel. L'utilisateur lance, joue et quitte ; l'agent lit ensuite la session désignée.
- **Fenêtré accepté, plein écran non requis** : zoom = viewport GL / dimensions monde au dessin, pas taille nominale de l'écran ni capture agrandie. Garder une taille stable pendant la comparaison ; transitions taille/zoom/FBO marquées `view_mixed` et analysées séparément.
- Viewport mesuré **2528×1339**, FBO0 ; zoom X min≈0.8229 / max≈4.9472 ; zoom habituel confirmé = **maximum −7 crans**, X/Y=2.480864/2.479630. Le premier zoom « habituel » ~2.6865 n'était pas celui finalement confirmé ; ne pas comparer des étiquettes de phase sans leurs valeurs réelles.
- Protocole utile pour une nouvelle scène : arrêt min/max/habituel, puis déplacements/panoramiques manuels, idéalement ~20 s/palier ; ce n'est pas une obligation de rejouer P4 acquise. L'utilisateur seul juge le gain visuel.
- P4 mesure FPS scène, p95 **par fenêtre**, CPU imbriqué composition/pixels/upload (ne pas additionner), masque séparé, trafic RGBA **base**, WS/privé processus entier. Ni p95 global reconstitué, ni VRAM, ni octets mip GPU, ni coût GPU isolé. Cache pixels hit n'implique pas absence d'upload transitoire.
- Replis `CHFB1G11 slot=-1/10` : tables BAM/shard concordantes, cycles concernés limités à0–9 ; rejet avant filtre. Cause native/effet visible non établi ; warning une fois/processus ⇒ nombre réel inconnu. Ne pas attribuer ces replis au BOX/Mips ni altérer les tables pour les masquer.

---

## 11. Plan de développement `0x6110`

Dépendances techniques, pas un workflow imposé (doctrine `docs/PRODUCTION_RAPIDE.md`). Chaque phase produit de nouvelles versions ; aucun run historique réécrit.

| Phase | Travail | Critère de passage | État (base 2026-09-30 ; décisions ultérieures datées) |
|---|---|---|---|
| **P0** Oracles | lecteur BAM P8 complet ; réalisation RGB neutre Python `MPALETTE` (7×12 + 21×8) ; contrôle de provenance `MPALETTE` (alias vérifié `RANGES12`) ; banc corrigé : signe, masques séparés, agrégations pondérée/non pondérée, durées relatives en slots natifs | RGB neutre octet pour octet ; E3b reproduit ; signe testé par recadrage synthétique | **clôturé hors ligne** : acquis P1 + run P0 dédié (§7.15), 30 tests PASS. Captures palette RGBA/effets et cadence réelle : P3 |
| **P1** Multi-palettes hors ligne | inférence K palettes (cache existant) ; encodeur §9 (Q6, Q3m) ; corpus = E3b + attaque Codex + 4 armures ; ≥ 10 palettes disjointes ; K = 3/4/6 | Q3m bat Q0 sur **chaque** palette disjointe ; fuite 0 ; K choisi | **fait** : critères satisfaits x2 et x4 ; **K = 6** ; fuite 0 (§7.14) |
| **P2** DLL V6 | écrivain/lecteur V6 I/F/dep_mask/profil/règle ; LUT des couples utilisés ; B absent ; rejet fermé et repli BAM natif | golden Python/C++ ; géométrie/sauvegardes conservées | **fait, PASS** : [preuve P2](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p2-20260930-v1/README.md), 146 tests Python/4 suites CTest ; 32 832 couples P1 et reconstructions des 4 packs ; extensions P3 mixte V5/V6 et limites dans `pipeline/PALETTE_Q3M_V6.md` |
| **P3** Verticale en jeu | CHFF4 + `WQNJ6`, `WQND3`, `WQNS1` en Q3m K6 x2 ; memberships limitées à `0x6110` ; A/B contre Q0 sous REF, DEFAULT et au moins deux validations (ex. VAL05, gain maximal ; VAL10, gain minimal) | QA utilisateur explicite ; régression REF (+6,1 % x2 hors ligne) jugée acceptable, sinon nouveau run P1 avec REF surpondéré ; recoloration (§12.2 T1) sans liseré ; `layer n/n` dans le log | **validée intégralement par l'utilisateur avant P4** (déclaration dans le chat à l'ouverture de P4) ; bilans techniques historiques non réécrits |
| **P4** Échelle et filtre | mesure du zoom ; expérience §10.2 | décision x2/x4 + filtre, datée | **décidé 2026-10-02 : x2 + BOX, sans mipmaps, `0x6110`** (§10.1) ; préférence x2 légère/incertaine, BOX nette en dézoom ; QA/release hors périmètre non déduites |
| **P5** Frontières | Q8c vs Q3m K6 : d'abord sur le banc P1 étendu au plan B (mêmes occurrences et palettes), puis mêmes frames, palettes, packing et scènes en jeu (attaque, marche, mort, repos) | gain propre visible **et** mesuré ; coût XPRESS acceptable ; sinon Q8 abandonné | **écartée par l'utilisateur le 2026-10-02** : « je souhaite ne pas tester Q8c et j'assume cette decision » ; poursuivre Q3m K6, aucune implémentation/production/QA Q8c |
| **P6** 0x6110 complet | 628 BAM, par famille et couche ; ordre : CHFF4 → CHFB1–3 → armes fréquentes (S1 S0 SS AX WH MC CL S2 BW) → boucliers → casques ; K = 6 ⇒ ≈ 564 000 inférences, cibles float encodées en flux ou purgées | aucune frame manquante ; cache froid/chaud, mémoire, upload mesurés | **couverture monde déjà produite en P3** : 656 BAM / 178 360 frames Q3m K6 x2, [run complet](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p3-20261001-v3-full-6110/README.md) ; working set/éviction hors ligne vérifiés ; mesures ingame de la scène P4 (§10.1), aucun profilage exhaustif déduit. Paperdolls exclus ; aucune régénération demandée |
| **P7** Paperdolls | `CHFF*INV`, `WPN*INV`, `WPN*OIN` : pipeline UI séparé | mesures UI propres (échelle, centres, filtre) | **CHFF1INV seul validé par l'utilisateur le 2026-10-02** : [QA immuable](../index/qa-decisions/paperdolls/2026-10-02-accepted-chff1inv-q3m-k6-x2-nearest-v1.json), Q3m K6 x2, UI Nearest/Bitmap natif ; deux moitiés HD confirmées par journal/CRC. [Mesure native](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p7-ui-measurement-20261002-v1/README.md) compatible profil/alpha/placement (16 combinaisons, capture bornée) ; [installation pilote](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p7-chff1inv-ingame-20261002-v1/README.md), monde x2+BOX conservé ; autres corps/équipements paperdoll hors périmètre, P7 globale non achevée |
| **P8** Généralisation | §13 | preuves par famille ; aucune QA transférée | à faire |

Implémentations disponibles : `pipeline/scripts/reboutcx_multipal.py` (inférence K, cibles float32), `palette_frac_encode.py` (Q6/Q3m), `palette_eval.py` (banc P1), `palette_registry.py` (V6), `palette_p2.py` (fixtures/packs). Runtime : `core/palette_fraction.h`, `creature_sprite_x2.cpp`, `paperdoll_q3m.cpp` ; tests `iee_palette_fraction_tests` et `iee_paperdoll_q3m_tests`. Q8c non demandé ; aucun écrivain/lecteur V6 à refaire.

Références P0 pour P2 : `palette_oracle.read_bam_p8` (contrat BAM/centres/lookup et cas limites), `neutral-palette-golden.npz` (RGB neutre seulement), et fixture P1 `decoder-golden.npz` (contrat de décodage RGBA entier, alpha synthétique). Contrats et limites §7.15.

Un nouvel essai crée un nouveau dossier de run : `palette_eval.py --output <…/research/palette-…-vN>`. Un run terminé (`result.json` présent) est refusé ; `--resume` n'accepte qu'un run incomplet au contrat identique. Tests ciblés : `python pipeline/scripts/test_changed.py --targeted --path <fichier> --run`, avec le Python `config://chainner_python` ; C++ : commandes de `engine/InfinityEngine-Enhancer/source-patchee/AGENTS.md`.

### 11.1 P7 : contrat appris sur `CHFF1INV`, corps seul

Preuves : [rendu hors jeu](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p7-chff1inv-20261002-v1/README.md), [mesure UI native](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p7-ui-measurement-20261002-v1/README.md), [candidat/installation](../families/playable-characters/6110-human-female-fighter/research/palette-q3m-p7-chff1inv-ingame-20261002-v1/README.md), [QA acceptée](../index/qa-decisions/paperdolls/2026-10-02-accepted-chff1inv-q3m-k6-x2-nearest-v1.json).

| Élément | Contrat confirmé / implémenté |
|---|---|
| Source et portée | `CHFF1INV.BAM`, SHA `7362904c…da86d8a`, KEY `data/GUIIcon.bif` locator`0x004006FB` ; corps sans équipement **avec tenue native**, aucune couche arme/bouclier/casque |
| Haut / bas | 66×64, centre(−24,−16) / 65×75, centre(−25,0) ; canevas natif128×160, placements(24,16)/(25,80) ; aperçu x2=256×320 |
| Cycle et dessin | cycle0 `[0,0,1,1]` ; slots0/2 observés ; sources sans bordure ; render=clip128×160 ; flags`0x4005`, shader **Bitmap6** |
| Palette réalisée | CVidPalette type1, 256 entrées, BGRA`0x80E1`/UINT8888_REV`0x8367` ; 7×12 + 21×8 conformes au profil Character ; alpha index0=0, index1=128, autres255 |
| Production réutilisable | deux NPZ guide/I/F/dep_mask/géométrie déjà produits ; `build-pack.py` les assemble, **0 nouvelle inférence** ; paquet autonome V6 brut x2, 74 028 octets |
| Routage dédié | `EnablePaperdollQ3mTest`, `paperdoll_q3m.cpp` + scopes CVidCell dans `hooks.cpp` ; capture Realize de la même cellule/slot, palette recontrôlée au dessin ; sous-ensemble strict `CHFF1INV`, shader Bitmap/Nearest conservé |
| GPU / file native | descriptor logique x1, backing x2 ; **deux textures mutables**, flush natif validé **avant** modification de palette pour conserver les couleurs des dessins déjà soumis ; binding et unpack restaurés |
| Garde-fous | registre/SHA source déclaré/géométrie/cycle/profil/F/dep stricts ; SHA du BAM vivant non relu ; signatures centrales `build_manifest.*` ; contrat divergent ⇒ natif ; installateur refuse override`CHFF1INV`/`UI.MENU`, exécutable inconnu ou dérive ; remplacement jeu/InfinityLoader fermés |

- **Aperçu hors jeu ≠ affichage HD effectif** : la première session couleurs mesurait encore le rendu natif. `EnablePaperdollUIProbe` fonctionne sans activer le style D7 fpSprite/fpSELECT ; il fallait le routage UI dédié, pas le catalogue monde ni une seconde passe d'upscaling.
- Oracle de recoloration = palette **réalisée**, pas palette BAM brute : 0 différence des mélanges réalisés ; 168 entrées mixtes de la source brute diffèrent. La palette DEFAULT synthétique de l'aperçu n'est pas la palette live de l'acteur.
- Sonde native bornée : 64 palettes/128 dessins, 16 combinaisons/32 CRC ; limite atteinte rapidement dans le sélecteur. 128 décodages indépendants octet-exacts (64 palettes×2 parties) valident la compatibilité, pas toutes les couleurs/effets possibles.
- QA finale : déclaration utilisateur **« c'est propre je valide ! committe »**, 2026-10-02. Dernière session : `P7_Q3M_DRAW bound=true` pour les deux parties ; CRC pixels concordants aux plans, **une palette observée**, aucun élargissement aux autres corps/équipements. Décision indépendante du reçu/du manifeste candidat historiquement `ingame_qa=false`.
- [Manifeste runtime](../../pipeline/runtime/manifests/iee-sprite-p7-chff1inv-q3m-20261002-v1.json), DLL`5686D1FC…021B1` ; le reçu actif du pilote est sous `…/palette-q3m-p7-chff1inv-ingame-20261002-v1/ingame-installation/active-test.json`. `Restore` revient à la **sonde native P7v2**, pas directement au runtime pré-P7. Lire la chaîne de backups avant toute restauration ; preuves anciennes intactes.
- Suite possible **sur demande** : autre corps/armure ou couche équipement UI autonome. Ce pilote n'achève pas les 85 paperdolls ; Q8c, production monde déjà disponible et release ne sont pas relancés implicitement.

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
| T5 temporel | repos 30 s, marche lente horizontale, zoom avant/arrière | aucun grouillement ; A/B Q0 / Q3m ; Q8c écarté |
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
- **Palettes fixes** : une seule palette réelle ; Q0 sur la palette du BAM est déjà juste. Mélange générique à deux entrées (B, §8.7) = piste future, absente du V6 Character livré ; aucune extension autorisée par les essais `0x6110`.
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
| Q0 seul | comparateur / production historique | 12 niveaux, palette unique ; repli runtime sur BAM natif, pas seconde feuille Q0 automatique |
| Q1 classe complète | rejet comme solution | +0,3 % en validation |
| Q3 / interpolation mono-palette | rejet comme final | surapprentissage palette |
| Q8c / frontières entre classes | écarté par l'utilisateur le 2026-10-02 | décision assumée : poursuivre Q3m K6 ; aucun essai Q8c demandé |
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
| x4 par défaut | non retenu dans P4 `0x6110` | choix utilisateur x2+BOX ; master x4 conservé, aucune règle universelle |
| Carte de nuances grise (inférence indépendante de la palette) | à tester | pourrait remplacer K inférences ; risque de perdre les contrastes de matière ; comparer à Q3m |

---

## 15. Questions ouvertes

Acquis à ne pas rouvrir par défaut : **K6 et 10 palettes disjointes** (P1), **V6 sans B** (P2), **QA P3**, **zoom/choix x2+BOX `0x6110`** (P4), **QA UI `CHFF1INV` x2/Nearest** (P7). **Q8c explicitement écarté** ; autres paperdolls sur demande. Les mesures locales ne répondent pas aux généralisations ci-dessous.

| Priorité | Question | Expérience décisive |
|---:|---|---|
| P0 | Coût V6 dans une foule/autre scène, VRAM et temps GPU isolés ? | profilage de la scène demandée ; ne pas extrapoler WS/privé/CPU P4 |
| P0 | Effets post-palette d'un nouveau corps/équipement UI ? | palette/dessin natifs corrélés + QA limitée à cet asset |
| P1 | Échelle/filtre d'une autre animation, fenêtre ou UI ? | reprendre la mesure réelle à ce périmètre ; aucune QA P4/P7 transférée |
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

Nettoyage intégré au dépôt (`6032948a`) : copies exactes racine / étude / `delivery` fusionnées ; observations historiques conservées ; grands JSON remplacés par leur gzip exact. Visuels, HTML, BAM, archives et dépendances de recherche restent locaux, ignorés par Git. Runs de développement : `sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-20260930-v1/` et `palette-oracles-p0-20260930-v4/`.

### 17.2 Portabilité des scripts

Les données sont intègres ; les recettes ne sont pas relançables telles quelles :

- chemins absolus vers `C:/Users/Adrien/Desktop/…` (ex. `e5_cross.py:28`), vers le Python chaiNNer, polices, poids locaux ;
- racine calculée par `parents[3]` ; `render_guide.mjs` dépend de `marked` ;
- `fetch_engine_sources_codex.py` relit `master` : seuls les fichiers de `source_reference/` sont épinglés (Near Infinity `50021b83`, GemRB `5552ade1`, EEex `6c1f42b8`).

Pour rejouer : copier dans une nouvelle version d'étude, résoudre via `config://` (`chainner_python`, `reboutcx_model`, `bg2ee_game_root`), corriger le signe temporel, écrire hors des dossiers historiques.

Exception reproductible intégrée : `pipeline/scripts/palette_p0.py e3b --output <nouveau run>` épingle le script E3b et les poids, relit `MPALETTE` via KEY/BIF, conserve volontairement le protocole historique pour comparaison exacte et supprime seulement la sortie visuelle. Pour de nouvelles mesures corrigées : `palette_eval.py`, protocole P1.

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
| Q8 | Q3m + mélange de deux classes aux frontières (prototype E3b) | I + F + B | extension proposée, absente du V6 livré |
| Q8c | Q8 sous les contraintes §9.4 ; essai écarté par l'utilisateur | I + F + B | extension proposée, absente du V6 livré |

## Annexe C — Règles de conservation

- Ne jamais modifier les études sources ni leurs preuves historiques ; créer une nouvelle version.
- Préserver les **octets épinglés par SHA**, fins de ligne comprises : `.gitattributes` protège les runs P4/P7 et manifestes runtime P7 avec `-text`. Vérifier les octets indexés avant un commit de preuves ; ne pas reformater un JSON/CSV/log historique.
- Ne jamais déduire une validation en jeu d'une métrique hors ligne, ni une installation ou une release d'une production.
- Une QA finale s'ajoute dans `sprite/index/qa-decisions/` ; elle ne réécrit pas les manifestes/reçus pré-QA ni leurs anciens champs `ingame_qa=false`. Acceptation conservée tant que les octets de l'asset et son contrat runtime restent identiques.
- Ne jamais remplacer globalement un resref partagé ; router par memberships.
- Ne jamais modifier `MPALETTE`, payload, staging, TP2, `content.json` ou release sans demande explicite.
- Fermer BG2EE et InfinityLoader avant tout remplacement installé.
