# Découpage SeedVR des cartes

`areas.csv` porte le choix courant dans `split_seedvr`. Ce document définit uniquement la règle de
calcul pour une zone nouvelle ou un maître x1 modifié.

| Surface du rendu x1 | Morceaux | Option `run_seedvr_comfyui.py` |
|---:|---:|---|
| ≤ 1,80 Mpx | 1 | aucune |
| ≤ 3,60 Mpx | 2 | `--split-rows` |
| ≤ 7,20 Mpx | 4 | `--split-grid 2 2` |
| ≤ 10,80 Mpx | 6 | `--split-grid 2 3` |
| ≤ 14,40 Mpx | 8 | `--split-grid 2 4` |
| > 14,40 Mpx | 10 | `--split-grid 2 5` |

Règles :

- ordre de `--split-grid` : colonnes puis lignes ;
- frontières alignées sur les tuiles de 64 px ;
- recouvrement x1 par défaut : 128 px, retiré après inférence ;
- même échelle et même découpe pour les variantes principale et secondaire ;
- dimensions assemblées exactement égales aux dimensions x1 multipliées par l'échelle.

Ne pas recopier ici l'inventaire des résolutions : `resolution_x1`, `resolution_x1_mpx` et
`split_seedvr` dans `areas.csv` en sont l'autorité. Toute modification des seuils impose une
décision puis une régénération cohérente du catalogue.
