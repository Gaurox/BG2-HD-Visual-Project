# Lot de 14 assets — AR5502 + OH4210 + AR5201 + AR5503 (+ FLM2PUR déjà produit)

- Campagne : `ToB` (les 4 maps choisies ; `AR1008`, qui se complète gratuitement, est `SoA`)
- Demande : un nouveau lot de taille proche du précédent (14), maps complètes.
- Choix par couverture minimale (glouton, plus grand gain d'assets neufs par map) : `AR5502` (4) → `OH4210` (4, dont `AM5204C` déjà compté) → `AR5201` (3) → `AR5503` (3) = **14 resrefs `non-traité` uniques sur 4 maps**. Alternative à 5 maps (`+AR6005`, 2 assets) écartée : moins efficace (2 assets neufs pour 1 map de plus).
- **Bonus gratuit** : `AM5508C`/`AM5508D` (traités dans `AR5502`) sont **partagés avec 4 autres maps** — `AR5501`, `AR5506`, `AR5507`, `AR5508` — dont c'est la seule animation restante non validée : elles se complètent par extension de signature, sans travail supplémentaire. **9 maps deviennent donc complètes pour 14 assets traités.**
- Scan de travail antérieur : aucune trace pour 13 des 14 resrefs. **`FLM2PUR` fait exception** (voir plus bas).
- Sources : `animations/index/zones.csv`, `occurrences.csv`, `animation_upscale_registry.csv`, `ressources/<RESREF>/source.bam`, `animations/index/area-pack-lock.json`

## `FLM2PUR` — déjà produit et déjà installé sur `AR1008`, jamais finalisé

Trouvé par le scan de travail antérieur : `animations/batches/ar1008-twisted-rune-apo8-x4-30fps-spline-fit1-feather4-20260911/` (lot du 2026-09-11, avec `AM1008B` et `AM1008BL`, tous deux `validé-x4` depuis cette date). `FLM2PUR` a été produit dans le **même run** (SeedVR2 7B/LAB x4 → Apollo-8 15→30 → spline Fit 1 + feather 4) et **installé sur `AR1008`** (verrou : signature `d115feb89ea1`, 32 frames), mais son registre est resté `non-traité` : `finalize` exige la QA de **toutes** les zones d'inventaire, et `OH4210` (sa deuxième zone) n'avait jamais été traitée. Il n'a donc **aucun nouveau run à faire** : juste découper le pack existant, l'installer sur `OH4210` (fusionné avec `FIRE_3`/`FIRE_4` déjà là), puis QA + `finalize` sur les deux zones à la fois. Traiter `OH4210` complète donc `AR1008` (déjà QA validée le 2026-09-11 pour ses deux autres assets) en plus d'`OH4210` lui-même.

## `AR5508` — pas d'entrée dans `areas.csv`

`AR5508` porte 4 occurrences (`AM5508C`, `AM5508D`) mais n'a **aucune ligne** dans `areas.csv` (campagne, nom, statut d'upscale de carte inconnus). À vérifier avant de le compter comme « map complétée » : peut-être une zone de secours/débogage sans upscale x1 prévu. Les 3 autres maps gratuites (`AR5501`, `AR5506`, `AR5507`) sont bien `ToB`, `validated-installed`.

| Resref | Map(s) | Frames | Taille max x1 | Occ. | Flags ARE (principal) | Blended | Couvert par murs |
|---|---|---:|---:|---:|---|---|---|
| `AM5502D` | AR5502 | 12 | 23x17 | 1 | `0x1043` | oui | non |
| `AM5502F` | AR5502 | 12 | 63x59 | 1 | `0x1043` | oui | non |
| `AM5508C` | AR5501;AR5502;AR5506;AR5507;AR5508 | 12 | 20x26 | 19 (18× `0x1003`, 1× `0x1043`) | `0x1003` | oui | couvert (sauf 1 occ.) |
| `AM5508D` | AR5501;AR5502;AR5506;AR5507;AR5508 | 10 | 95x68 | 5 | `0x1103` | oui | couvert |
| `AM5204C` | AR5204;OH4210 | 12 | 53x37 | 2 | `0x1103` | oui | couvert |
| `FIREBRN` | OH4210 | 63 | 15x28 | 7 | `0x1043` | oui | non |
| `FIRE_4GS` | OH4210 | 14 | 16x32 | 17 | `0x1043` | oui | non |
| `FLM2PUR` | AR1008;OH4210 | 16 | 18x23 | 13 (mixte, voir ci-dessus) | `0x1043`/`0x1143`/`0x1103`/`0x1443` | oui | mixte |
| `AM5201A` | AR5201 | 8 | 109x166 | 2 | `0x1003` | oui | couvert |
| `AM5201B` | AR5201 | 14 | 106x122 | 6 | `0x1083` | oui | couvert |
| `AM5204D` | AR5201;AR5204 | 20 | 52x118 | 14 | `0x1003` | oui | couvert |
| `AM5503A` | AR5503 | 8 | 105x76 | 1 | `0x1003` | oui | couvert |
| `AM5503C` | AR5503 | 8 | 51x65 | 2 | `0x1103` | oui | couvert |
| `AM5503D` | AR5503 | 8 | 50x66 | 1 | `0x1103` | oui | couvert |

**Correction du 2026-09-22 :** le tableau ci-dessus marquait à tort `AM5508D`, `AM5204C`, `AM5201B`, `AM5503C`, `AM5503D` comme non-Blended (erreur de lecture du bit 1). Vérifié avec `flag & 0x2` en Python pour les 13 : **tous sont Blended**, sans exception.

Planche : [`review/LOT14-one-frame-per-animation.png`](review/LOT14-one-frame-per-animation.png). PNG x1 individuels : `review/representative-frames/`.

## Familles visuelles

- **Braises/cristal orange (bassin de feu ?)** : `AM5503A/C/D` — même géométrie de coupelle incandescente, 3 variantes (comme `AM4500A-E` du lot précédent).
- **Flamme haute** : `AM5204D` (52x118, forme de flamme classique) et `FIREBRN`/`FIRE_4GS` (colonnes fines) — analogues de la famille `FIRE_*`/`FLAME2*` déjà traitée.
- **Brume/fumée grise** : `AM5502D`, `AM5502F`, `AM5201B` — silhouettes diffuses sans bord net, à comparer aux fumées déjà validées (`CHIMSMK`, `SMOKE`, `STEAM2`).
- **Halo lumineux vertical** : `AM5508C` (colonne blanche à cœur brillant).
- **Éclat orange en croissant** : `AM5508D`, `AM5503A/C/D` (coupelle/segment courbe).
- **Braises tassées** : `AM5204C` (tas de charbons rougeoyants, ressemble à `FPIT1S`/`FPIT1M`/`FPIT1L`).
- **Ailes bleutées cristallines** : `AM5201A` (109x166, forme nette à facettes).
- **Cristal violet** : `FLM2PUR` (déjà produit, cf. ci-dessus).

## Points d'attention avant de choisir les recettes

- 9 des 14 sont `Blended` : neutralisation RGB par premultiply à prévoir.
- `AM5508C`/`AM5508D` et `AM5204C`/`AM5204D` sont chacun partagés entre 2+ maps : traiter une fois profite à toutes leurs zones (`AM5204C` complète aussi `OH4210`, `AM5204D` complète aussi `AR5204` — mais `AR5204` reste `non-traité` tant qu'`AM5204A`, non inclus dans ce lot, n'est pas traité, donc `AR5204` ne se complète pas gratuitement cette fois).
- La plupart des occurrences sont couvertes par les murs (Blended → pont d'occlusion natif sans effet, à surveiller en QA comme d'habitude).
- Aucune trace de travail antérieur hormis `FLM2PUR`, à ne pas retraiter comme un `non-traité` ordinaire.

## Recette analysée (2026-09-22)

Essais x1 sur les 13 assets à traiter (ReboutCX x4 pour tous, SeedVR2 7B/LAB x4 sur un représentant par famille + `FIREBRN`) : `review/<RESREF>-nearest-reboutcx-seedvr.png`. Runs conservés sous `animations/ressources/<RESREF>/runs/*-20260922`, réutilisables pour `AM5204D`/`AM5204C`/`AM5502D`/`AM5502F`/`AM5201B`/`AM5508C`/`AM5503C`/`AM5201A`/`FIREBRN` (déjà en ReboutCX et SeedVR) et les 4 autres (ReboutCX seul).

**SeedVR retenu sur 1 seul asset : `AM5204D`.** Flamme classique (sat 74,4 % / σ 63,9 / lum 78,8, proche du profil gagnant `FIRE_4` 77,0/67,6/71,5) : SeedVR donne des langues de flamme naturelles, ReboutCX est plus lisse/cireux. Tous les 12 autres → **ReboutCX**, avec des défauts SeedVR nets et variés :
- `AM5204C` (tas de braises) : SeedVR aplatit les blocs de charbon en galets lisses façon œuf, perdant toute la texture rocheuse (même défaut que `FPIT1M`/`FPIT1S`).
- `AM5502D`, `AM5502F`, `AM5201B` (fumées/brumes grises diffuses) : SeedVR hallucine un visage (f0 d'`AM5502D`), des lignes de circuit imprimé, des motifs capillaires fins — ReboutCX reste un nuage lisse fidèle au nearest.
- `AM5508C` (halo lumineux) : SeedVR invente un chandelier/motif de crâne à la base du halo.
- `FIREBRN` : SeedVR ajoute une éclosion en étoile (flare) absente de la source ; ReboutCX garde la silhouette ovale fidèle.
- `AM5503C` (coupelle incandescente) et `AM5201A` (ailes cristallines fragmentées) : pas d'hallucination nette des deux côtés, mais MAE/énergie haute fréquence de ReboutCX plus bas (cohérence temporelle) ; retenu par défaut, cohérent avec `AM4500A-E` du lot précédent.

**`FIRE_4GS` : alpha 100 % opaque sur fond noir** (comme `FIRE_3GS`/`FIRE_3GR`), contrairement à `FIREBRN` qui a une vraie silhouette (13-19 % de couverture). Même famille que `FLAMME-RECTANGLE-NOIR-REBOUTCX-APO8` : ReboutCX + Apollo-8 (`--base-runtime-only`, 4 cycles vides terminaux) + premultiply, rayon 8 au départ (à balayer 4/8/12 comme `FIRE_3GS`/`FIRE_3GR`).

| Resref | Recette | Modèle catalogue / analogue |
|---|---|---|
| `AM5204D` | SeedVR2 7B/LAB x4 → Apollo-8 (10→? phases, seul cycle 0 joué) → premultiply, rayon à balayer | proche `FLAMME-BRAISES-REBOUTCX-APO8-PREMUL` mais étage spatial SeedVR |
| `AM5204C` | ReboutCX x4 → Apollo-8 (cycle 0 seul joué, 6 frames) → `build_animation_contour_aura_pack.py`, rayon ≈ 0,13 × largeur canevas x4 | `BRASERO-REBOUTCX-APO8-AURA` (`FPIT1M`) |
| `FIREBRN` | ReboutCX x4 → Apollo-8 (cycle 0 seul joué, 9 frames) → premultiply, rayon à balayer | `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` |
| `FIRE_4GS` | ReboutCX x4 → Apollo-8 (`--base-runtime-only`) → premultiply rayon 8 (balayer 4/8/12) | `FLAMME-RECTANGLE-NOIR-REBOUTCX-APO8` |
| `AM5502D`, `AM5502F`, `AM5201B` | ReboutCX x4 → Apollo-8 direct → premultiply, rayon à balayer (probablement faible : pas d'anneau sombre net observé) | `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` |
| `AM5508C`, `AM5508D` | ReboutCX x4 → Apollo-8 direct → premultiply rayon 16 (départ) | `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` |
| `AM5201A` | ReboutCX x4 → Apollo-8 direct → premultiply ; alpha fragmentée (24 composants moy.) → **pas de spline**, alpha nearest conservée | `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` |
| `AM5201B` | ReboutCX x4 → Apollo-8 (cycle 0 = 8 frames, cycle 1 = 6 frames) → premultiply | `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` |
| `AM5503A`, `AM5503C`, `AM5503D` | ReboutCX x4 → Apollo-8 direct (8→16) → premultiply rayon 16 (départ) | `EFFET-BLENDED-REBOUTCX-APO8-PREMUL` (`AM4500A-E`) |
| `FLM2PUR` | **Déjà produit** (run `ar1008-twisted-rune-apo8-x4-30fps-spline-fit1-feather4-20260911`, SeedVR + Apollo-8 + spline fit1/feather4) : découpe sur `OH4210`, fusion avec `FIRE_3`/`FIRE_4`, installation, `finalize` sur `AR1008` + `OH4210` | — |

- Multi-cycles avec un seul cycle joué (`sequence=0` partout) : `AM5204C` (6+6), `AM5204D` (10+10), `AM5201B` (8+6), `FIREBRN` (9+12, indices 42-50 pour le cycle 0), `AM6200A/B` du lot précédent (précédent traité en entier, cycle 1 non joué installé quand même) — même convention à suivre ici.
- Aucun rayon balayé pour ce lot (analyse spatiale seulement) ; tous les rayons ci-dessus sont des points de départ hérités du catalogue, à confirmer par balayage {4,8,12,16} sur la sortie réelle comme pour le lot précédent (le critère cœur ≥ -5 % n'a pas discriminé sur `AM4500*`/`AM6200*`, donc prendre le plus grand rayon testé par prudence, pas le plus petit).

## Traitement et installation (2026-09-22)

**Correction majeure découverte en exécutant :** `FLM2PUR` sur `OH4210` porte une **palette externe** (`PLT_PURP`), contrairement à ses occurrences sur `AR1008` (palette embarquée). `split_animation_pack_by_area.py` l'exclut automatiquement de `OH4210` (`resource_kind != BAM or palette_mode == external or palette_resref` → ignoré), même précédent que `AM3000E`/`PLT_MAGE` : le chemin x4 ne reçoit jamais la palette réalisée, donc installer le pack d'`AR1008` sur `OH4210` aurait donné une couleur fausse. **`FLM2PUR` reste hors de ce lot, `non-traité`, `AR1008` ne se complète pas.** Les 12 autres assets ne sont pas concernés.

- Apollo-8 sur les 12 (13e = AM5204C en aura) : plan sans maintien ni doublon sur tous (`collapse_eligible=false` partout), audit du pack final : 100 % de frames distinctes, aucun pas nul, couture de boucle correcte (0,4 à 6,6 selon l'asset).
- Balayage 4/8/12/16 (silhouette uniquement) : 10/12 retenus à R16 (cœur quasi inchangé) ; `AM5502D`/`AM5502F` (fumées) retenus à R12, seuls à dépasser -35 % de lumière totale à R16.
- `AM5204C` : aura (`build_animation_contour_aura_pack.py`, sigma 5, gain 0,9, marge 14) balayée 8/12/16/20 → R16 (cœur -4,2 %, R20 dépasse -5 % à -10,5 %). Comparatif avant/après : coupure nette des braises devenue un halo doux, texture des braises intacte.
- `FIRE_4GS` : `--base-runtime-only` (4 cycles vides terminaux), retenu à R16 comme les autres (cœur -1,7 %, en dessous du seuil -5 %).
- Fusions : `AR5502` (4 nouveaux, zone vierge), `OH4210` (`FIRE_3`/`FIRE_4` inchangés + `AM5204C`/`FIREBRN`/`FIRE_4GS`), `AR5201` (3 nouveaux, zone vierge), `AR5503` (`FIRE_4` inchangé + `AM5503A/C/D`).
- Installé (AreaTest, sauvegardes `backups/animations/area-tests/{AR5502,OH4210,AR5201,AR5503}-20260922T1926*`) ; `status --deep` : 200/200 conformes. `AR5501`, `AR5506`, `AR5507`, `AR5508` restent non servies (leur seule animation, `AM5508C`/`AM5508D`, n'a pas encore été copiée dessus — extension par signature à faire lors du `finalize`, pas automatique à l'installation).
- Non fait : QA ingame, `finalize`/registre, commit.
