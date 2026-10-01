# P7 — mesure UI native CHFF1INV

- Session utilisateur 2026-10-02 01:15:48.440 ; sonde v2, DLL `A7099657…E6B2A` ; aucun rendu HD dans cette session.
- Preuves immuables : `session.log`, `result.json`, `analyze.py` ; journal source/hashes dans `result.json`.
- Captures : 64 palettes / 128 dessins ; 32 CRC palettes, 16 combinaisons de gammes. Limites atteintes dans le sélecteur : couverture bornée, aucune exhaustivité des couleurs revendiquée.
- `CVidPalette` type1, 256 entrées ; BGRA `0x80E1` / UINT8888_REV `0x8367` ; alpha index0=0, index1=128, autres=255.
- Profil Character : 21×8 mélanges réalisés identiques à l'oracle scalaire sur les 7 gammes natives, 0 différence. La palette BAM brute n'est pas l'oracle de la réalisation native.
- Géométrie : cycle0, slots0/2 → parties0/1 ; sources 66×64 / 65×75 sans bordure ; canevas/clip128×160 ; offsets `(24,16)` / `(25,80)` ; flags`0x4005`, shader natif6.
- Réemploi des plans [pilote hors jeu](../palette-q3m-p7-chff1inv-20261002-v1/README.md) : 128 décodages (64 palettes×2 parties), comparaison octet par octet indépendante, 0 différence.
- Décision technique : profil/alpha/placement compatibles ; intégrer uniquement ce corps. QA visuelle HD encore absente ; installation ultérieure : [pilote runtime](../palette-q3m-p7-chff1inv-ingame-20261002-v1/README.md).
