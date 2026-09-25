# Eau x4 spatiale — chaîne standard, toutes familles

Étape A du [runbook](WATER_MAP_RUNBOOK.md). Généralise le lot témoin du 2026-09-23 (rendu spatial accepté
globalement : [QA](manifests/liquid-families-spatial-user-qa-20260923-v1.json)) à n'importe quelle WED d'eau.
Les producteurs du lot sont réutilisés **sans modification** ; seuls les plans et l'enchaînement sont standard.
Chaque famille garde son système : méthode, disposition, collier, contrat de composition.

## Ce que produit la chaîne pour une map

| Élément | Contrat |
|---|---|
| Overlays liquides | x4 périodique (contexte 3×3, crop central) ; SeedVR `none` ou bilinéaire selon la famille ; pavages A–D en motif 2×2 conjoint |
| Temporalité | lookup, vitesse et durée vanilla conservées (le 30 FPS est l'étape B) |
| Alpha overlay | masque natif (index 0 transparent seulement si clé verte), nearest x4 |
| Isolation | alias propre à la map (`YS…` sec, `…R` pluie) ; ressources `WT*` partagées jamais modifiées |
| WED | vanilla, seuls les resrefs des slots liquides changent (restauration inverse byte-exacte) |
| Bases | alpha effectif des centrales (ARE 0→128, 100/160 natifs), interfaces secondaires, greffe RGB si écart > 6/255 |
| Pluie | ressource `…R` du KEY traitée si présente ; routée nativement depuis l'alias sec |

## Familles — [`liquid-family-standard-v1.json`](liquid-family-standard-v1.json)

| Famille | Overlays | x4 | Témoin validé |
|---|---|---|---|
| lake | WTLAKE | seedvr | AR1600 |
| pool | WTPOOL | bilinear (SeedVR → quadrillage) | AR0408 + AR0703 (standard) ; AR1000 historique |
| swamp | WTSWAM | seedvr | AR0500 + AR0500N (standard) ; AR1607 historique |
| sewage | WTSEW | seedvr | AR2100 |
| oil | WTOIL | seedvr (A validé ; overlay remplacé par B) | AR0503 (A+B+C) ; AR0413 historique |
| lake_teal | WTLAKA–D (2×2) | seedvr, **construit seulement** sur AR6300 (aucune cellule d'eau pure ; WED remplacée par B) | AR6300 (B+C) ; AR3000 historique |
| brown_flow | WT5000A–D (2×2) | seedvr (A validé ; overlay remplacé par B) | AR5000 (A+B+C) ; AR5203 historique |
| lava | WTLAVA–D (2×2) | bilinear, **construit seulement** (contextes/topologie pour B `seedvr-torus` ; WED remplacée par B) | AR5200 (B+C) ; AR0011 historique |

Collier de bord : mode `compatible` pour tous ; appliqué seulement si un raccord est mesuré amplifié
par rapport au stock (règle du producteur, identique au lot témoin).

## Commandes

```powershell
$v = 'G:/AI/BG2_Vanilla_23534562'; $run = 'maps/water-batches/runs/<map>-water-x4-<date>-v1'
python -B pipeline/scripts/plan_water_map.py plan --area ARxxxx --vanilla-root $v --output $run
python -B pipeline/scripts/build_water_map_x4.py --run $run --stage all        # ComfyUI requis si famille seedvr
# jeu fermé :
& pipeline/scripts/Install-AreaOverrideAssets.ps1 -SourceRoot $run/override-candidate -BackupRoot backups/water/<run>
python -B pipeline/scripts/build_water_map_x4.py --run $run --stage verify-installed
python pipeline/scripts/record_water_decision.py install --area ARxxxx --kind spatial --run $run --override-backup backups/water/<run>/<override-backup-stamp>
```

`plan` écrit `request.json`, `overlays-plan.json`, `temporal-plan.json` (familles non bloquées),
`plan-report.json` (`stops`, `decisions_owed`, `notes`). `all` = overlays → select → bases → snapshot → assemble ;
chaque étape existe seule (`--stage`). Sorties immuables : nouveau run `-vN` pour tout nouvel essai.
Vérifié de bout en bout, sans installation, sur AR5200 (lave, bilinéaire, 4 slots) et AR2100 (égouts, SeedVR,
bases réparées) ; le `temporal-plan.json` produit est accepté par le producteur 30 FPS.

Réparation des interfaces primaire/secondaire (`build_liquid_base_x4_trial.py`) : voisins cherchés par famille
(tous les slots d'une famille tuilée), plus par slot seul. Avant le 2026-09-25 les pavages A–D n'avaient aucune
interface (voisins toujours sur un autre slot : AR5000 0 → 240) ; cartes multi-familles : un slot par groupe.

## Arrêts automatiques (`plan-report.json` → `stops`)

- overlay liquide inconnu du standard ; ressources d'une famille absentes du KEY ;
- base x4 de la map absente ;
- master x4 des tuiles secondaires introuvable ou ambigu (`--secondary-master` explicite) ; découverte :
  `maps/<map>/runs/*/tuiles-secondaires/03_assemble/*.png`, plus `01_upscale/*.png` des runs directs sans
  `03_assemble` (AR0503) ; runs `nuit`/`night` réservés aux variantes `N` ;
- traitement eau antérieur installé (resref d'overlay renommé, lookup re-temporisée, identité route2 dans la DLL) :
  le remplacer est une décision utilisateur ; chaîne standard déjà installée : restaurer avant de replanifier.

## Inventaire du 2026-09-23 — [`manifests/water-map-inventory-20260923-v1.json`](manifests/water-map-inventory-20260923-v1.json)

63 WED d'eau actives (vanilla), toutes de familles connues, toutes avec base x4 installée.
Relancer : `plan_water_map.py inventory --vanilla-root $v`.

| Famille | Prêtes (chaîne standard applicable) | Décision utilisateur (traitement antérieur) |
|---|---|---|
| lake | — | AR0046, AR0046N, AR0204, AR0300, AR0300N, AR0512, AR0900, AR0900N, AR1200, AR1600, AR1604, AR1700, AR1901, AR2300 |
| pool | AR0408, AR0506, AR0703, AR1003, AR1004, AR1100, AR1601, AR2000, AR2000N, AR2011, AR2012, AR5010 | AR1000 |
| swamp | AR0310, AR0500, AR0500N, AR0604, AR1100, AR1106, AR1201, AR1403, AR1500, AR2210, AR2500, AR2600, AR2602, AR2700, AR3025, AR6008 | AR1000N, AR1607, AR1800 |
| sewage | AR2100 | AR0404 |
| oil | AR0603, AR1203, AR2102, AR3024 (AR0503 fait) | AR0413 |
| lake_teal | — (AR6300 fait) | AR3000 |
| brown_flow | — (AR5000 fait) | AR5203 |
| lava | AR1401, AR2903, AR5200, AR5201, AR5204 | AR0011 |

### Validations par map

| Map | Famille | Run | Installation | QA en jeu |
|---|---|---|---|---|
| AR2100 | sewage | `ar2100-water-x4-20260923-v1` | `ar2100-spatial-installed-20260923-v1.json` | validée — `ar2100-spatial-user-qa-20260923-v1.json` |
| AR0408 | pool | `ar0408-water-x4-20260923-v2` | `ar0408-spatial-installed-20260923-v1.json` (WED remplacée par B) | validée — `ar0408-spatial-user-qa-20260923-v1.json` (`superseded_by` reçu B v2) |
| AR0703 | pool | `ar0703-water-x4-20260923-v2` | `ar0703-spatial-installed-20260923-v1.json` (WED remplacée par B) | validée — `ar0703-spatial-user-qa-20260923-v1.json` (`superseded_by` reçu B v1) |
| AR0500 | swamp | `ar0500-water-x4-20260924-v2` | `ar0500-spatial-installed-20260924-v1.json` (WED/pages remplacées par B+C) | validée utilisateur, jour ; reçu QA A non émis ; possible depuis `--superseded-by` répétable (B + C), sur citation utilisateur |
| AR0503 | oil | `ar0503-water-x4-20260924-v1` | `ar0503-spatial-installed-20260924-v1.json` (WED remplacée par B, 3 pages par C) | validée — `ar0503-spatial-user-qa-20260924-v1.json` (`superseded_by` B v2 + C) |
| AR5000 | brown_flow | `ar5000-water-x4-20260924-v1` + bases `ar5000-bases-x4-20260924-v2` | `ar5000-spatial-installed-20260924-v1.json` (WED par B, pages par bases v2 puis C) | validée — `ar5000-spatial-user-qa-20260925-v1.json` (`superseded_by` B + C) |
| AR5200 | lava | `ar5200-water-x4-20260924-v1` | reçu v1 retiré au rollback du 2026-09-24 ; A non installé, entrée de B | sans objet (B+C validés) |
| Lot swamp (14, liste : TEMPORAL_30FPS_PIPELINE) | swamp (+ pool AR1100) | `<map>-water-x4-20260925-v1` | `<map>-spatial-installed-20260925-v1.json` (WED par B, pages par C) | validées — `<map>-spatial-user-qa-20260925-v1.json` (`superseded_by` B + C) |
| AR0500N | swamp | `ar0500n-water-x4-20260924-v2` | `ar0500n-spatial-installed-20260924-v1.json` (WED/pages remplacées par B+C) | validée utilisateur, nuit ; reçu QA A non émis ; possible depuis `--superseded-by` répétable (B + C), sur citation utilisateur |

« Décision » : témoins du lot (déjà traités, alias `Q9*`/`QBLKV0`) et maps lac/marais à timeline 36 phases
validée historiquement (route2). Les maps prêtes utilisant une ressource partagée déjà surchargée (WTSWAM,
WTPOOL, WTSEW, WTLAVA–D, WTLAKA–D x4 installés) passent sur alias isolé ; la ressource partagée reste intacte.

## Limites

- Surfaces d'eau en ARE/BAM (cascades AR2300, bassins AR2804/5, AR3021) : pipeline d'animation, hors chaîne.
- QA en jeu par map ; la pluie n'est qualifiée que si l'utilisateur l'a observée.
- Pour une famille, l'amélioration du rendu (méthode, collier) se change dans le standard, pas par map.
