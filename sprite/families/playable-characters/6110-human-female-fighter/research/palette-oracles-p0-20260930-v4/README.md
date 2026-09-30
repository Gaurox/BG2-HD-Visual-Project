# P0 — oracles clôturés, 2026-09-30

Statut : **PASS hors ligne**. P0 complète les acquis P1 ; aucune QA ingame déduite.
P1 reste immuable : `../palette-q3m-p1-20260930-v1/`.

| Preuve | Résultat | Fichier |
|---|---|---|
| RGB neutre : production NumPy / oracle scalaire indépendant / boucle x64 native | 530 palettes × 768 octets ; différences 0 | `audit.json`, `neutral-palette-golden.npz` |
| Moyenne native `(a+b)>>1` | 65 536 couples d'octets, différences 0 ; sommes impaires et >255 incluses | `audit.json` |
| Ressources `MPALETTE` / `RANGES12` | octets identiques ; locators distincts `0x0000012E` / `0x00000189`, `data/Default.bif` | `audit.json` |
| Compatibilité jobs historiques | preuve/cache `RANGES12` inchangés ; profil `MPALETTE` = même RGB | `audit.json` |
| Lecteur BAM P8 indépendant / lecteur existant / BIF natif | 836 BAM, 185 459 frames, 252 540 168 pixels, 18 903 cycles, 376 665 slots ; écarts 0 | `bam-resources.json`, `audit.json` |
| E3b historique intégral, y compris simulation d'affichage | 1 080 valeurs numériques ; toutes les clés et feuilles identiques ; écart maximal 0 | `e3b-reproduction.json`, `e3_results.json` |
| Tests ciblés | 30 tests PASS | `tests.json` |

## Contrats utiles à P2

- `pipeline/scripts/palette_oracle.py:read_bam_p8` : BAM/BAMC V1, palette BGRA, indices P8, transparence distincte de l'alpha BMP, centres i16, RLE/raw, cycles et lookup répété ; offsets, signatures, troncatures, indices hors table et taille BAMC contrôlés.
- Corpus : 679 BAMC ; 145 995 frames RLE / 39 464 raw ; 22 209 frames à centre négatif ; 31 933 frames 1×1. Ne pas assimiler toutes les frames 1×1 à un marqueur nul.
- **RLE natif** : 27 frames ont un dernier run transparent dépassant `width*height`. Consommer le marqueur et tronquer ce run comme le lecteur existant ; exemples `WQNAXA5/106`, `WQNS1G1/730`. Liste exacte : `audit.json:clipped_native_rle`. Ces ressources sont vérifiées contre les BIF, pas traitées comme corrompues.
- Frames de dimension nulle et cycles vides absents de ce corpus ; couverts par fixtures synthétiques. Le nouvel oracle conserve leur géométrie déclarée. Le lecteur historique normalise les dimensions nulles en marqueur 1×1 : ne pas confondre métadonnées natives et représentation de calcul.
- **Provenance** : nouveaux jobs → `MPALETTE`, locator `0x0000012E`, type 1 ; alias `RANGES12` vérifié octet pour octet. `reboutcx_batch.load_palette_profiles` accepte les deux noms, refuse alias absent/ambigu/différent, conserve la forme de preuve des jobs historiques. Ne pas renommer seulement le nom en conservant le locator `0x189` ; ne pas réécrire les jobs/caches scellés.
- **Oracle RGB** : 18 palettes P1 + 512 rampes aléatoires, graine 6110. `NativeMix` exécute hors jeu la boucle autonome `[0x421F7B,0x42201E)` du seul EXE épinglé ; 7×12 nuances copiées, 21×8 mélanges calculés, nuances 2..9. SHA fragment `c8e05c9238f186aa07d72aac38cc793bfc74cdca588fcd691271a6a5ccc645b4`.
- Cette preuve précède effets, packing final/évitement de clé verte, alpha et modulation post-palette. Pour V6, décoder depuis la **palette RGBA runtime réalisée** ; ne pas reconstruire celle-ci avec l'oracle neutre. La fixture P1 `decoder-golden.npz` vérifie le contrat RGBA entier mais son alpha est synthétique.
- **E3b** : protocole inchangé (batch1 CUDA0 fp16 sans padding ; RGB u8 x4 / BOX u8 x2 ; fractions historiques 4 bits ; signe temporel historique). Seules les écritures PNG/GIF sont supprimées. Les tables historiques sont reproduites, pas corrigées rétroactivement. Pour P2/P3, utiliser le banc corrigé P1 (3 bits entiers, cibles float, signe d'ancre corrigé, masques séparés, deux agrégations, couture).
- **Durées** : répétitions natives conservées (95 369 slots adjacents répétés sur le corpus). Idle E3b : 20 poses / 56 slots par couche. BAM V1 n'a pas de champ FPS/temps ; poids en slots relatifs acquis. Mesure en secondes et validation pause/vitesse/effets : P3, avec horloge runtime/captures.

## Reproduction

Python : `config://chainner_python` ; modèle : `config://reboutcx_model` ; EXE/BIF/KEY : `config://bg2ee_game_root`.
E3b : `OPENBLAS_NUM_THREADS=1`, `OMP_NUM_THREADS=4`, `PYTHONDONTWRITEBYTECODE=1`.
Créer un nouveau run ; les commandes refusent leurs résultats existants.

```text
python -B pipeline/scripts/palette_p0.py audit --output sprite/families/playable-characters/6110-human-female-fighter/research/palette-oracles-p0-YYYYMMDD-vN
python -B pipeline/scripts/palette_p0.py e3b --output sprite/families/playable-characters/6110-human-female-fighter/research/palette-oracles-p0-YYYYMMDD-vN
python -B pipeline/scripts/test_changed.py --targeted --path pipeline/tests/test_palette_oracle.py --path pipeline/tests/test_palette_p0.py --path pipeline/tests/test_reboutcx_pipeline.py --path pipeline/tests/test_palette_eval.py --run
```

Sources exécutées : `provenance/`. Scripts historiques et run P1 inchangés. Identités/empreintes des résultats et scripts : `verification.json`. Les deux fixtures NPZ/NPY contiennent des tables RGB, aucun visuel/HTML ni asset du jeu livré. Pas de compilation DLL, installation, catalogue, payload ou release modifiés.
