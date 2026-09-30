# P1 — Q3m multi-palettes, 0x6110, 2026-09-30 v1

- État : **critères P1 hors ligne satisfaits**. Candidat retenu : Q3m, K=6, fractions 3 bits, poids égaux, sans tramage ni frontières.
- Corpus : 180 occurrences (E3b 120 + Codex 60), 144 frames BAM uniques ; CHFF4 repos/marche, attaque 4 couches, pose A1 des 4 armures.
- Inférence : 18 palettes × 144 frames = 2 592 cibles ; ReboutCX x4 FP16, kernel P12 N=86/q32 ; BOX float32 x2 avant encodage. Réinférence de contrôle : différence maximale 0.
- Validation : 10 palettes, aucun ID **ni rampe RGB identique** partagé au même canal avec l'union des 6 palettes d'ajustement. Défauts dérivés et RANDCOLR résolus : substitutions enregistrées dans `experiment.json`. LEGACY_D/E : diagnostics partiellement vus, exclus du choix de K.
- REF = `30 47 57 12 39 21 3` ; DEFAULT = `30 91 93 12 23 93 2` ; 4 rotations conçues : `experiment.json`.
- Score primaire : moyenne des 10 ΔE OKLab moyens, pondérés pixels recolorables `4..255`, vs **cible générée** ReboutCX float ; occurrences du corpus conservées. Aucun verdict de qualité perçue.

| Méthode | Score x2 ×1000 | Gain x2 vs Q0 | Score x4 ×1000 | Gain x4 vs Q0 |
|---|---:|---:|---:|---:|
| Q0 | 33,305 | — | 35,552 | — |
| Q6 K3 | 30,143 | 9,49 % | 32,160 | 9,54 % |
| Q6 K4 | 29,247 | 12,18 % | 31,231 | 12,16 % |
| Q6 K6 | 28,729 | 13,74 % | 30,636 | 13,83 % |
| Q3m K3 | 26,243 | 21,20 % | 28,530 | 19,75 % |
| Q3m K4 | 24,940 | 25,12 % | 27,220 | 23,44 % |
| **Q3m K6** | **24,285** | **27,08 %** | **26,523** | **25,40 %** |

K3/K4/K6 améliorent chacune des 10 validations. K4 reste à +2,70 % du meilleur score x2, +2,63 % x4 : seuil ≤2 % ⇒ **K6 aux deux échelles**.

| Palette | Gain Q3m K6 x2 | Gain x4 |
|---|---:|---:|
| VAL01 | 25,84 % | 24,19 % |
| VAL02 | 24,49 % | 23,46 % |
| VAL03 | 28,17 % | 25,88 % |
| VAL04 | 26,70 % | 25,01 % |
| VAL05 | 39,82 % | 37,31 % |
| VAL06 | 31,37 % | 28,78 % |
| VAL07 | 19,53 % | 18,66 % |
| VAL08 | 25,92 % | 24,82 % |
| VAL09 | 24,81 % | 23,28 % |
| VAL10 | 19,12 % | 18,14 % |

Contrôle par couche : amélioration sur chacune des 10 validations, corps/casque/bouclier/arme, aux deux échelles ; gain minimal x2 = 20,90 / 5,18 / 12,07 / 13,51 % respectivement.

## Compromis et limites

- **REF régresse** : erreur +6,10 % x2, +11,59 % x4. DEFAULT : −30,43 % / −29,64 %. Consensus ≠ amélioration universelle ; comparer REF en jeu avant adoption.
- Temporel, recolorables, 10 validations agrégées pondérées pixels, poses distinctes et couture de boucle : Q0→Q3m K6 = **20,28→8,36 % x2**, **21,66→9,40 % x4**. Agrégation non pondérée séquences/palettes : **29,63→23,91 % x2**, **29,07→24,01 % x4**.
- Lookups natifs répétés : 4,19→1,73 % x2 ; 4,31→1,87 % x4. Durées relatives par slots seulement ; timing réel en secondes non mesuré. Alignement par ancre, aucun flot optique : pas de preuve de stabilité des surfaces mobiles.
- Taille : compression **XPRESS_HUFF réelle**, plans séparés, stockage min(raw,compressed) + masque 32 octets/frame ; Q0→Q3m = **173 704→343 620 octets x2 (×1,98)** ; **407 818→859 646 x4 (×2,11)**, pondéré par les 180 occurrences. Exclut en-têtes V6 et representatives. Plans décompressés I+F : ×2 ; texture RGBA future inchangée à échelle égale.
- Nouveau protocole P12/float/Q3 entier : aucune prétention de reproduction numérique des anciennes tables E3b 4 bits. Études sources intactes.
- Planche : illustration hors ligne, ombre alpha 128 illustrative, agrandissement nearest ×3 ; aucune capture ni QA ingame.
- V6 binaire, lecteur DLL, performance runtime, captures palette/effets : **P2/P3 à réaliser**. Aucun catalogue courant, installation, QA ou release remplacé.

## Artefacts et vérification

- `experiment.json` : sources BAM/cycles/hashes, occurrences, palettes/résolutions, contrats et hashes code.
- `target-index.json` : cache frame+palette, versions, temps et contrôle de répétition ; `targets/`, `guides/`, `encoded/` : dérivés locaux.
- `result.json` : critères, K, tailles, limites ; `color-summary.csv` / `color-frames.csv` : masques visibles/recolorables/ombre et deux agrégations ; `temporal-summary.csv` / `temporal-sequences.csv` : supports, couture, slots/poses et deux agrégations ; `sizes.csv` : compression par frame/plan.
- `comparison-x2.png` : xBR/Q0/Q6 K6/Q3m K6, REF/DEFAULT/VAL01/VAL09/VAL10/LEGACY_D.
- `verification.json` : recherche indépendante, **1 584 choix identiques**, coût excédentaire 0 ; **220 roundtrips XPRESS** de plans réels.
- `decoder-golden.npz` : 18 palettes natives neutres, 1 824 couples légaux I/F, RGBA de référence calculé scalairement ; alpha synthétique, transparent forcé 0. Fixture P2 ; ne vaut pas comparaison C++.
- Tests ciblés : **17 verts**. Décodage scalaire indépendant : 1 824 couples légaux, 0 octet différent.

```powershell
$taskPython = (Get-Content config/workspace-paths.local.json -Raw | ConvertFrom-Json).paths.chainner_python
& $taskPython -B pipeline/scripts/test_changed.py --targeted --path pipeline/scripts/palette_frac_encode.py --path pipeline/scripts/palette_eval.py --path pipeline/scripts/reboutcx_multipal.py --run
# Nouveau run uniquement ; ne pas écraser v1 terminé. --resume accepte seulement un run incomplet au contrat identique.
& $taskPython -B pipeline/scripts/palette_eval.py --output sprite/families/playable-characters/6110-human-female-fighter/research/palette-q3m-p1-NEW-VERSION
```
