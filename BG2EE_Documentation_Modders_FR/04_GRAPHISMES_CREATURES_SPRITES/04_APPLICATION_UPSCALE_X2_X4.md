# Application au pipeline sprites x2 du projet

> **Statut :** Synthèse spécifique au projet, non officielle  
> **Dernière vérification :** 2026-09-14

## Architecture actuelle

Le projet ne reconstruit pas les BAM/PVRZ des créatures :

```text
BAM x1 intact
  -> inventaire + extraction des frames/indices
  -> production physique x2 (xBR ou ReboutCX)
  -> registre externe content-addressé
  -> palette active appliquée par le runtime IEE
  -> géométrie/cycles/centres logiques x1 conservés
```

| Mode | Rôle |
|---|---|
| xBR | base canonique déterministe et repli de tous les composants non remplacés |
| ReboutCX | remplacement explicite de composants xBR dans un catalogue dérivé complet |

ReboutCX infère en x4 puis réduit en BOX vers x2 avant quantification. Le x4 est intermédiaire ; la
cible runtime reste x2. Les deux modes utilisent le même registre et le même hook moteur.

## Invariants

- BAM, resrefs, cycles, lookup, dimensions et centres logiques inchangés ;
- dimensions physiques du registre exactement x2 ;
- transparence, ombre et classes de palette conservées ;
- Character : composition body/arme/bouclier/casque aux centres natifs et recoloration dynamique ;
- composant inconnu ou incomplet : repli natif, jamais résultat partiel ;
- catalogue ReboutCX : xBR conservé pour toute appartenance non ciblée.

## Production

Commandes et choix de mode : [`../../sprite/PROCESSING.md`](../../sprite/PROCESSING.md). Publication,
installation et rollback : [`../../sprite/FAMILY_APPEND.md`](../../sprite/FAMILY_APPEND.md).
Contrats raster : [`../../sprite/XBR2X_RASTER_CONTRACT.md`](../../sprite/XBR2X_RASTER_CONTRACT.md) et
[`../../docs/REBOUTCX_PIPELINE_BG2_CODEX.md`](../../docs/REBOUTCX_PIPELINE_BG2_CODEX.md).

## Validation ingame

Tester un petit ensemble représentatif : déplacement/attaque, directions, ombre, recoloration et,
pour Character, plusieurs couches équipées. La décision QA reste limitée aux composants réellement
vus ; elle ne vaut ni installation release ni validation de toute la famille.

## Sources format

- IESDP BAM V1: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v1.htm
- IESDP BAM V2: https://gibberlings3.github.io/iesdp/file_formats/ie_formats/bam_v2.htm
