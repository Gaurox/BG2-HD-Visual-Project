# Politique de découpage des maps — SeedVR2 7B

Ce document est la référence de production pour choisir le découpage d'un rendu maître x1 avant
son upscale SeedVR2 7B x4/LAB. Il remplace les termes imprécis « petite » et « grande » map dans
les autres procédures.

## Règle de décision

La limite validée pour une soumission directe est d'environ **1,80 Mpx x1**, soit l'ordre de
grandeur de **1 200 × 1 500 px**. La décision porte sur la surface du rendu source x1, pas sur
la surface x4 générée. Toutes les coupes restent alignées sur les tuiles de 64 px et conservent
128 px x1 de recouvrement interne.

| Surface x1 | Morceaux | Option de l'orchestrateur |
|---|---:|---|
| ≤ 1,80 Mpx | 1 | aucune option de découpe (direct) |
| > 1,80 à ≤ 3,60 Mpx | 2 | --split-rows |
| > 3,60 à ≤ 7,20 Mpx | 4 | --split-grid 2 2 |
| > 7,20 à ≤ 10,80 Mpx | 6 | --split-grid 2 3 |
| > 10,80 à ≤ 14,40 Mpx | 8 | --split-grid 2 4 |
| > 14,40 Mpx | **10** | --split-grid 2 5 |

Chaque palier conserve le même budget d'environ **1,80 Mpx x1 par morceau** ; la borne haute d'un
palier à N morceaux vaut donc N × 1,80 Mpx. Les deux variantes techniques d'une même zone
(tuiles-principales et tuiles-secondaires) reçoivent obligatoirement la même échelle et la même
découpe. Les plus grandes maps du catalogue passent donc en **dix morceaux** ; le maximum actuel
est 5 120 × 3 840 px (19,66 Mpx).

Pour une zone ajoutée ou dont le maître x1 a changé, appliquer directement le tableau ci-dessus.
Ne pas choisir le nombre de morceaux à l'intuition. --split-grid attend l'ordre
**colonnes lignes** ; --split-rows est le seul mode à deux morceaux.

> **Palier à dix morceaux validé sur AR0700** (5 120 × 3 840 px, 19,66 Mpx, le maximum du
> catalogue) : une grille 2×4 (huit morceaux) s'est bloquée sur le 4ᵉ morceau et a dû être
> annulée ; relancée en grille 2×5 (dix morceaux), les dix parties se sont terminées sans incident
> en 50 à 70 s chacune. Le run historique d'AR0602 en grille 2×5 avait déjà validé visuellement ce
> découpage ; ce n'est plus une exception, c'est désormais la règle pour ce palier de surface.

## Inventaire exhaustif des résolutions x1

> **Pour une zone du catalogue, ne pas parcourir ce tableau** : `areas.csv` porte déjà le résultat
> par zone dans `resolution_x1`, `resolution_x1_mpx` et `split_seedvr`. Ce tableau sert à réviser
> la règle ou à traiter une zone hors catalogue. Les deux doivent rester cohérents : toute
> modification des seuils impose de régénérer `split_seedvr`.

Relevé sur les 369 rendus maîtres tuiles-principales du catalogue : **150 résolutions distinctes**.
La colonne « Zones » est le nombre de zones utilisant cette résolution ; le total est 369. La
recommandation est calculée avec la règle ci-dessus.

| Résolution x1 | Mpx | Zones | Découpage recommandé |
|---|---:|---:|---|
| 640 × 448 | 0.29 | 1 | 1 — direct |
| 704 × 512 | 0.36 | 3 | 1 — direct |
| 832 × 640 | 0.53 | 47 | 1 — direct |
| 896 × 640 | 0.57 | 4 | 1 — direct |
| 832 × 704 | 0.59 | 5 | 1 — direct |
| 960 × 640 | 0.61 | 1 | 1 — direct |
| 896 × 704 | 0.63 | 7 | 1 — direct |
| 960 × 704 | 0.68 | 1 | 1 — direct |
| 960 × 768 | 0.74 | 18 | 1 — direct |
| 896 × 832 | 0.75 | 1 | 1 — direct |
| 1024 × 768 | 0.79 | 4 | 1 — direct |
| 832 × 960 | 0.80 | 1 | 1 — direct |
| 1088 × 768 | 0.84 | 1 | 1 — direct |
| 1024 × 832 | 0.85 | 3 | 1 — direct |
| 1152 × 768 | 0.88 | 1 | 1 — direct |
| 1088 × 832 | 0.91 | 4 | 1 — direct |
| 1088 × 896 | 0.97 | 1 | 1 — direct |
| 1216 × 832 | 1.01 | 1 | 1 — direct |
| 1152 × 896 | 1.03 | 1 | 1 — direct |
| 1088 × 960 | 1.04 | 1 | 1 — direct |
| 1216 × 896 | 1.09 | 3 | 1 — direct |
| 1152 × 960 | 1.11 | 4 | 1 — direct |
| 1344 × 896 | 1.20 | 4 | 1 — direct |
| 1280 × 960 | 1.23 | 32 | 1 — direct |
| 896 × 1408 | 1.26 | 1 | 1 — direct |
| 1280 × 1024 | 1.31 | 5 | 1 — direct |
| 1216 × 1088 | 1.32 | 4 | 1 — direct |
| 1152 × 1152 | 1.33 | 1 | 1 — direct |
| 1408 × 960 | 1.35 | 1 | 1 — direct |
| 1280 × 1088 | 1.39 | 2 | 1 — direct |
| 1408 × 1024 | 1.44 | 5 | 1 — direct |
| 1344 × 1088 | 1.46 | 4 | 1 — direct |
| 1472 × 1024 | 1.51 | 2 | 1 — direct |
| 1408 × 1088 | 1.53 | 1 | 1 — direct |
| 1280 × 1216 | 1.56 | 1 | 1 — direct |
| 1536 × 1024 | 1.57 | 2 | 1 — direct |
| 1280 × 1280 | 1.64 | 1 | 1 — direct |
| 1600 × 1024 | 1.64 | 1 | 1 — direct |
| 1472 × 1152 | 1.70 | 5 | 1 — direct |
| 1344 × 1280 | 1.72 | 1 | 1 — direct |
| 1536 × 1152 | 1.77 | 1 | 1 — direct |
| 1472 × 1216 | 1.79 | 2 | 1 — direct |
| 1664 × 1088 | 1.81 | 3 | 2 — --split-rows |
| 1600 × 1152 | 1.84 | 1 | 2 — --split-rows |
| 1920 × 960 | 1.84 | 1 | 2 — --split-rows |
| 1408 × 1344 | 1.89 | 1 | 2 — --split-rows |
| 1600 × 1216 | 1.95 | 1 | 2 — --split-rows |
| 1536 × 1344 | 2.06 | 1 | 2 — --split-rows |
| 1664 × 1280 | 2.13 | 1 | 2 — --split-rows |
| 1600 × 1344 | 2.15 | 6 | 2 — --split-rows |
| 1600 × 1408 | 2.25 | 1 | 2 — --split-rows |
| 1728 × 1344 | 2.32 | 1 | 2 — --split-rows |
| 1984 × 1216 | 2.41 | 1 | 2 — --split-rows |
| 1728 × 1408 | 2.43 | 1 | 2 — --split-rows |
| 1664 × 1472 | 2.45 | 2 | 2 — --split-rows |
| 1536 × 1600 | 2.46 | 1 | 2 — --split-rows |
| 1792 × 1408 | 2.52 | 2 | 2 — --split-rows |
| 1664 × 1536 | 2.56 | 1 | 2 — --split-rows |
| 1920 × 1344 | 2.58 | 1 | 2 — --split-rows |
| 1920 × 1408 | 2.70 | 3 | 2 — --split-rows |
| 1664 × 1664 | 2.77 | 3 | 2 — --split-rows |
| 1984 × 1408 | 2.79 | 1 | 2 — --split-rows |
| 2048 × 1408 | 2.88 | 1 | 2 — --split-rows |
| 2304 × 1280 | 2.95 | 1 | 2 — --split-rows |
| 2048 × 1536 | 3.15 | 1 | 2 — --split-rows |
| 1984 × 1600 | 3.17 | 2 | 2 — --split-rows |
| 1856 × 1728 | 3.21 | 1 | 2 — --split-rows |
| 2304 × 1408 | 3.24 | 1 | 2 — --split-rows |
| 2048 × 1600 | 3.28 | 1 | 2 — --split-rows |
| 1792 × 1856 | 3.33 | 1 | 2 — --split-rows |
| 2048 × 1728 | 3.54 | 1 | 2 — --split-rows |
| 2112 × 1728 | 3.65 | 1 | 4 — --split-grid 2 2 |
| 2176 × 1728 | 3.76 | 1 | 4 — --split-grid 2 2 |
| 2368 × 1664 | 3.94 | 1 | 4 — --split-grid 2 2 |
| 2240 × 1792 | 4.01 | 2 | 4 — --split-grid 2 2 |
| 2432 × 1664 | 4.05 | 2 | 4 — --split-grid 2 2 |
| 2368 × 1728 | 4.09 | 2 | 4 — --split-grid 2 2 |
| 1856 × 2240 | 4.16 | 1 | 4 — --split-grid 2 2 |
| 2432 × 1792 | 4.36 | 1 | 4 — --split-grid 2 2 |
| 2368 × 1856 | 4.40 | 2 | 4 — --split-grid 2 2 |
| 2880 × 1536 | 4.42 | 1 | 4 — --split-grid 2 2 |
| 2240 × 1984 | 4.44 | 1 | 4 — --split-grid 2 2 |
| 2176 × 2048 | 4.46 | 1 | 4 — --split-grid 2 2 |
| 3200 × 1408 | 4.51 | 1 | 4 — --split-grid 2 2 |
| 2432 × 1856 | 4.51 | 1 | 4 — --split-grid 2 2 |
| 2304 × 2048 | 4.72 | 1 | 4 — --split-grid 2 2 |
| 2496 × 1920 | 4.79 | 1 | 4 — --split-grid 2 2 |
| 2432 × 1984 | 4.83 | 1 | 4 — --split-grid 2 2 |
| 2560 × 1920 | 4.92 | 28 | 4 — --split-grid 2 2 |
| 3072 × 1600 | 4.92 | 1 | 4 — --split-grid 2 2 |
| 2432 × 2048 | 4.98 | 1 | 4 — --split-grid 2 2 |
| 2240 × 2304 | 5.16 | 1 | 4 — --split-grid 2 2 |
| 2304 × 2240 | 5.16 | 1 | 4 — --split-grid 2 2 |
| 2944 × 1792 | 5.28 | 1 | 4 — --split-grid 2 2 |
| 2688 × 2048 | 5.51 | 1 | 4 — --split-grid 2 2 |
| 2432 × 2304 | 5.60 | 1 | 4 — --split-grid 2 2 |
| 2816 × 2048 | 5.77 | 4 | 4 — --split-grid 2 2 |
| 2816 × 2112 | 5.95 | 1 | 4 — --split-grid 2 2 |
| 2880 × 2176 | 6.27 | 1 | 4 — --split-grid 2 2 |
| 2496 × 2560 | 6.39 | 1 | 4 — --split-grid 2 2 |
| 3072 × 2176 | 6.68 | 1 | 4 — --split-grid 2 2 |
| 2944 × 2304 | 6.78 | 1 | 4 — --split-grid 2 2 |
| 2880 × 2432 | 7.00 | 1 | 4 — --split-grid 2 2 |
| 3072 × 2368 | 7.27 | 1 | 6 — --split-grid 2 3 |
| 3584 × 2048 | 7.34 | 1 | 6 — --split-grid 2 3 |
| 2688 × 2816 | 7.57 | 1 | 6 — --split-grid 2 3 |
| 2304 × 3328 | 7.67 | 1 | 6 — --split-grid 2 3 |
| 3072 × 2560 | 7.86 | 1 | 6 — --split-grid 2 3 |
| 3264 × 2432 | 7.94 | 1 | 6 — --split-grid 2 3 |
| 3328 × 2432 | 8.09 | 1 | 6 — --split-grid 2 3 |
| 3264 × 2496 | 8.15 | 1 | 6 — --split-grid 2 3 |
| 3328 × 2496 | 8.31 | 2 | 6 — --split-grid 2 3 |
| 3712 × 2240 | 8.31 | 1 | 6 — --split-grid 2 3 |
| 3392 × 2560 | 8.68 | 2 | 6 — --split-grid 2 3 |
| 3904 × 2240 | 8.74 | 1 | 6 — --split-grid 2 3 |
| 3904 × 2304 | 8.99 | 1 | 6 — --split-grid 2 3 |
| 3264 × 2816 | 9.19 | 1 | 6 — --split-grid 2 3 |
| 3456 × 2688 | 9.29 | 1 | 6 — --split-grid 2 3 |
| 3520 × 2688 | 9.46 | 1 | 6 — --split-grid 2 3 |
| 3904 × 2496 | 9.74 | 1 | 6 — --split-grid 2 3 |
| 3392 × 2880 | 9.77 | 1 | 6 — --split-grid 2 3 |
| 3328 × 2944 | 9.80 | 1 | 6 — --split-grid 2 3 |
| 3264 × 3008 | 9.82 | 1 | 6 — --split-grid 2 3 |
| 3584 × 2816 | 10.09 | 1 | 6 — --split-grid 2 3 |
| 3200 × 3200 | 10.24 | 1 | 6 — --split-grid 2 3 |
| 3840 × 2688 | 10.32 | 2 | 6 — --split-grid 2 3 |
| 3584 × 3008 | 10.78 | 1 | 6 — --split-grid 2 3 |
| 3776 × 2880 | 10.87 | 1 | 8 — --split-grid 2 4 |
| 3520 × 3136 | 11.04 | 1 | 8 — --split-grid 2 4 |
| 3840 × 2880 | 11.06 | 1 | 8 — --split-grid 2 4 |
| 4160 × 2752 | 11.45 | 1 | 8 — --split-grid 2 4 |
| 3840 × 3072 | 11.80 | 1 | 8 — --split-grid 2 4 |
| 3776 × 3200 | 12.08 | 1 | 8 — --split-grid 2 4 |
| 3712 × 3264 | 12.12 | 1 | 8 — --split-grid 2 4 |
| 3968 × 3072 | 12.19 | 1 | 8 — --split-grid 2 4 |
| 5120 × 2432 | 12.45 | 2 | 8 — --split-grid 2 4 |
| 4160 × 3072 | 12.78 | 1 | 8 — --split-grid 2 4 |
| 3904 × 3328 | 12.99 | 1 | 8 — --split-grid 2 4 |
| 4672 × 2816 | 13.16 | 1 | 8 — --split-grid 2 4 |
| 3904 × 3392 | 13.24 | 1 | 8 — --split-grid 2 4 |
| 4160 × 3520 | 14.64 | 2 | 10 — --split-grid 2 5 |
| 5120 × 2880 | 14.75 | 1 | 10 — --split-grid 2 5 |
| 4096 × 3840 | 15.73 | 1 | 10 — --split-grid 2 5 |
| 5120 × 3200 | 16.38 | 1 | 10 — --split-grid 2 5 |
| 4480 × 3840 | 17.20 | 1 | 10 — --split-grid 2 5 |
| 4928 × 3584 | 17.66 | 1 | 10 — --split-grid 2 5 |
| 5120 × 3520 | 18.02 | 1 | 10 — --split-grid 2 5 |
| 5056 × 3584 | 18.12 | 1 | 10 — --split-grid 2 5 |
| 5120 × 3584 | 18.35 | 2 | 10 — --split-grid 2 5 |
| 5120 × 3840 | 19.66 | 19 | 10 — --split-grid 2 5 |

## Répartition du catalogue

| Découpage | Résolutions | Zones |
|---|---:|---:|
| 1 — direct | 42 | 189 |
| 2 — --split-rows | 29 | 43 |
| 4 — --split-grid 2 2 | 32 | 66 |
| 6 — --split-grid 2 3 | 24 | 27 |
| 8 — --split-grid 2 4 | 13 | 14 |
| 10 — --split-grid 2 5 | 10 | 30 |

Lorsqu'un seuil devra être réévalué après une validation matérielle, modifier ici la règle et
reclasser l'inventaire avant d'adapter les commandes des procédures.
