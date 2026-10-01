# 0x6100 — Q3m K6 x2/x4, série dédupliquée

- État final : `verification.json` = `passed-offline-ready-for-manual-game` ; producteur et contrôleur terminés, code de sortie 0.
- Animation : `FIGHTER_MALE_HUMAN`, `0x6100` ; 656 BAM, 180 337 frames natives par échelle.
- Périmètre : 4 corps/armures, 18 casques, 12 boucliers, 31 armes ; YW sans BAM natif, non inventé.
- Recette : Q3m K6, six fits P1, F=0..7 en octets, sans B/tramage ; x2 BOX du réseau x4, x4 direct.
- Producteur : `pipeline/scripts/palette_playable.py`, plan actif `sprite/index/palette-work-plan.json`.
- 95 124 tâches uniques/échelle ; 1 027 résultats repris de `0x6110`, 94 060 nouvelles tâches neurales, 37 cas spéciaux.
- Résultats persistants : `sprite/.work/palette-q3m-shared/x<scale>/<namespace>/work/encoded/` ; namespaces dans les preuves.
- Packs expérimentaux : `sprite/.work/q3m-6100-20261001-v1/x2/` et `x4/` ; fichiers V6 + catalogue V2, un composant/BAM.
- Production, contrôle hors jeu, QA et installation restent distincts ; aucune acceptation visuelle ni release déduite.

## Résultats mesurés — 2026-10-01

| Échelle | Pack runtime : 656 registres + catalogue | Génération | Contrôle hors jeu |
|---|---:|---:|---:|
| x2 | 301 955 168 octets (301,96 Mo) | 3 834,719 s | 888,266 s |
| x4 | 554 768 336 octets (554,77 Mo) | 4 239,815 s | 1 732,313 s |

- Total packs : 856 723 504 octets ; x4/x2 = 1,837. Mo décimaux ; hors cache de préparation, oracles et diagnostics.
- Durée génération : durée réelle des logs du producteur, comprenant calcul neural et fit/encodage ; contrôle x2 exécuté pendant la génération x4, ne pas sommer les colonnes pour estimer le temps mural.
- Par échelle : 180 337 frames complètes × 18 palettes ; working set = première frame des 656 BAM puis retour au premier BAM (657 frames).
- 3 257 892 décodages de référence/échelle ; 17 388 790 920 pixels comparés en x2, 69 555 163 680 en x4, hors working set.
- Caches natifs : I/F ≤ 134 217 728 octets ; métadonnées ≤ 134 217 728 octets ; working set atteint 134 211 424 octets de métadonnées aux deux échelles, avec éviction/rechargement.
- Chaque échelle : 94 097 nouveaux résultats persistants = 94 060 neuraux + 37 spéciaux ; 1 027 hits issus de la guerrière humaine ; 564 360 cibles neurales (= 94 060 × 6 fits).
- SHA des preuves liées dans `verification.json` revérifiés après fin ; SHA des catalogues contrôlés. Preuves finales immuables ; tout remplacement nécessite un nouveau run.

## Preuves et contrôle

- `scope.json`, `source-provenance.json` : périmètre et identités du code.
- `x2-production.json`, `x4-production.json` : compteurs réels du producteur partagé et SHA des logs.
- `x2-verification.json`, `x4-verification.json`, `verification.json` : preuves finales produites après succès complet.
- Chaque frame : SHA du BAM canonique, géométrie, centres, representatives, cycles, I/F/dep comparés au cache et au shard V6.
- Oracle : `palette_complete.Oracle`, LUT scalaire indépendante ; 18 palettes, toutes les frames, y compris hors cycles.
- Contrôle C++ : `prepare_native.py`, `native-control.json`, `provenance/` ; seule fonction `inspect_pack` du test hôte copiée est adaptée à `0x6100` et aux quatre noms d'équipement masculins. Sources moteur et DLL inchangées.
- Fixtures natives : `native-fixtures.json` ; 10 valides, 37 invalides, 32 832 décodages neutres, pulses/cache/reset/éviction.
- Limite : alpha d'oracle synthétique ; palettes/effets réels et rendu GL nécessitent encore la QA ingame.
- REF P1 : régression connue +6,10 % x2 / +11,59 % x4 ; paramètres conservés sur demande.

## Réutilisation ultérieure

- Avec `0x6110` déjà disponible : union de 188 045 tâches uniques sur 563 969 dans le plan actif (33,34 %) par échelle ; les résultats féminins hors sélection restent dans les anciens runs vérifiés et seront importés à la demande par le producteur partagé.
- `0x5100` guerrier humain LOW et `0x6105` guerrier demi-orque masculin : 95 124 tâches communes.
- `0x5000`, `0x6000`, `0x6005` clercs masculins : 92 804 tâches communes.
- Assemblage par modèle conserve l'identité, les centres et les cycles de ses sources ; aucun partage de pixels déjà colorés par acteur.
- Scripts locaux `continue_series.py`, `verify_offline.py` : pilotage et contrôle de ce run ; pas d'installation, de mutation release ou d'extinction.
